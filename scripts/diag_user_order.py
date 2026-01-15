import asyncio
from uuid import UUID
from sqlalchemy import select
from app.infra.db.session import async_session_factory
from app.infra.db.models import User, Order

async def diagnose():
    target_tg_id = 878047002
    target_order_id = UUID("078fed8f-fa48-4c1f-9a06-c7601a74aab0")
    
    async with async_session_factory() as session:
        print(f"--- Диагностика для TG ID: {target_tg_id} ---")
        
        # 1. Проверка пользователя
        user_stmt = select(User).where(User.telegram_id == target_tg_id)
        user_result = await session.execute(user_stmt)
        user = user_result.scalar_one_or_none()
        
        if user:
            print(f"Пользователь найден: ID={user.id}, Username={user.username}")
            internal_user_id = user.id
        else:
            print("Пользователь НЕ найден в таблице users.")
            internal_user_id = None

        print(f"\n--- Проверка заказа: {target_order_id} ---")
        
        # 2. Проверка заказа
        order_stmt = select(Order).where(Order.id == target_order_id)
        order_result = await session.execute(order_stmt)
        order = order_result.scalar_one_or_none()
        
        if order:
            print(f"Заказ найден: ID={order.id}, User_ID={order.user_id}, Stage={order.current_stage}")
            # 3. Совпадение user_id
            if internal_user_id and order.user_id == internal_user_id:
                print("SUCCESS: User_ID в заказе совпадает с ID пользователя.")
            else:
                print(f"MISMATCH: User_ID в заказе ({order.user_id}) НЕ совпадает с ID пользователя ({internal_user_id}).")
        else:
            print("Заказ НЕ найден в таблице orders (возможна проблема с коммитом транзакции).")

if __name__ == "__main__":
    asyncio.run(diagnose())