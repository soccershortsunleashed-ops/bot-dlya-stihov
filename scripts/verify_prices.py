import asyncio
import sys
import os

# Добавляем корень проекта в sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from unittest.mock import AsyncMock, MagicMock
from app.infra.db.session import async_session_factory
from app.infra.db.models import User, ProductConfig, Order, OrderStage, Payment
from app.infra.db.repositories.order_repo import OrderRepo
from app.infra.db.repositories.stage_repo import StageRepo
from app.infra.db.repositories.config_repo import ConfigRepo
from app.infra.db.repositories.payment_repo import PaymentRepo
from app.application.use_cases.create_order import CreateOrderUseCase
from app.application.use_cases.start_payment import StartPaymentUseCase
from app.infra.payments.yookassa import YooKassaClient
from sqlalchemy import select, delete

async def verify():
    print("--- Начинаем верификацию цен ---")
    
    async with async_session_factory() as session:
        # 1. Подготовка данных
        # Удаляем старые тестовые данные если есть
        await session.execute(delete(User).where(User.telegram_id == 999999))
        await session.execute(delete(ProductConfig).where(ProductConfig.key == "poem_test"))
        
        test_user = User(telegram_id=999999, username="test_user")
        session.add(test_user)
        
        poem_config = ProductConfig(
            key="poem_test", 
            value_json={"price": 4900, "enabled": True, "title": "Тестовый стих"}
        )
        session.add(poem_config)
        await session.commit()
        
        print(f"Подготовлен тестовый пользователь и конфиг (цена: 4900)")

        # 2. Проверка CreateOrderUseCase
        order_repo = OrderRepo(session)
        stage_repo = StageRepo(session)
        config_repo = ConfigRepo(session)
        
        # Мокаем get_product_config чтобы он вернул наш тестовый конфиг
        config_repo.get_product_config = AsyncMock(return_value=poem_config)
        
        uc_create = CreateOrderUseCase(order_repo, stage_repo, config_repo)
        stage = await uc_create.execute(user_id=test_user.id, context={"theme": "test"})
        
        print(f"Заказ создан. Цена этапа в БД: {stage.price}")
        assert stage.price == 4900, f"Ошибка: ожидалось 4900, получено {stage.price}"
        
        # 3. Проверка YooKassaClient и StartPaymentUseCase
        yoo_client = YooKassaClient()
        # Патчим Payment.create внутри yookassa (библиотека) через мок клиента или напрямую
        # Но проще проверить метод create_payment самого YooKassaClient
        
        original_create = yoo_client.create_payment
        
        # Мы хотим убедиться что в YooKassa улетает "49.00"
        # Для этого нам нужно посмотреть что делает create_payment
        # Так как YooKassaClient.create_payment вызывает Payment.create (из библиотеки), 
        # мы замокаем Payment.create
        
        import yookassa
        mock_response = MagicMock()
        mock_response.id = "test_pay_id"
        mock_response.confirmation = {"confirmation_url": "http://test.url"}
        mock_response.__dict__ = {"id": "test_pay_id", "confirmation": {"confirmation_url": "http://test.url"}}
        
        yookassa.Payment.create = MagicMock(return_value=mock_response)
        
        payment_repo = PaymentRepo(session)
        uc_payment = StartPaymentUseCase(payment_repo, stage_repo, yoo_client)
        
        result = await uc_payment.execute(stage.id)
        
        # Проверяем что было передано в yookassa.Payment.create
        args, kwargs = yookassa.Payment.create.call_args
        sent_amount = args[0]["amount"]["value"]
        print(f"Сумма, отправленная в ЮKassa: {sent_amount}")
        
        assert sent_amount == "49.00", f"Ошибка: ожидалось '49.00', получено {sent_amount}"
        
        # Проверяем запись в таблице payments
        db_payment = await session.scalar(select(Payment).where(Payment.stage_id == stage.id))
        print(f"Сумма в таблице payments: {db_payment.amount}")
        assert db_payment.amount == 4900, f"Ошибка: ожидалось 4900 в payments, получено {db_payment.amount}"

        print("--- Верификация прошла успешно! ---")

if __name__ == "__main__":
    try:
        asyncio.run(verify())
    except Exception as e:
        print(f"ОШИБКА ВЕРИФИКАЦИИ: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)