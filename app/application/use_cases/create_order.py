from typing import Dict, Any
from app.domain.enums import StageType, OrderStageStatus
from app.infra.db.models import Order, OrderStage
from app.infra.db.repositories.order_repo import OrderRepo
from app.infra.db.repositories.stage_repo import StageRepo
from app.infra.db.repositories.config_repo import ConfigRepo

class CreateOrderUseCase:
    def __init__(
        self,
        order_repo: OrderRepo,
        stage_repo: StageRepo,
        config_repo: ConfigRepo
    ):
        self.order_repo = order_repo
        self.stage_repo = stage_repo
        self.config_repo = config_repo

    async def execute(self, user_id: int, context: Dict[str, Any]) -> OrderStage:
        # 1. Создаем заказ
        order = Order(
            user_id=user_id,
            context_json=context,
            current_stage=StageType.POEM
        )
        await self.order_repo.add(order)
        await self.order_repo.session.flush()

        # 2. Получаем цену из конфига (или дефолтную)
        product_config = await self.config_repo.get_product_config("poem")
        price = 4900
        if product_config and "price" in product_config.value_json:
            price = product_config.value_json["price"]

        # 3. Создаем этап "Стих"
        stage = OrderStage(
            order_id=order.id,
            stage_type=StageType.POEM,
            status=OrderStageStatus.PENDING,
            price=price,
            input_json=context
        )
        await self.stage_repo.add(stage)
        await self.stage_repo.session.commit()
        
        return stage