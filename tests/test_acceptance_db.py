import asyncio
import os
import sys

# Add project root to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.infra.db.session import async_session_factory, engine
from app.infra.db.repositories.user_repo import UserRepo
from app.infra.db.repositories.order_repo import OrderRepo
from app.infra.db.repositories.stage_repo import StageRepo
from app.domain.enums import StageType, OrderStageStatus


async def main():
    print("Starting acceptance test...")

    async with async_session_factory() as session:
        user_repo = UserRepo(session)
        order_repo = OrderRepo(session)
        stage_repo = StageRepo(session)

        # 1. Create User
        print("Creating User...")
        user = await user_repo.create(telegram_id=123456789, username="test_user")
        print(f"User created: {user.id}, {user.username}")

        # 2. Create Order
        print("Creating Order...")
        order = await order_repo.create(user_id=user.id)
        print(f"Order created: {order.id}")

        # 3. Create Stage
        print("Creating Stage...")
        stage = await stage_repo.create(
            order_id=order.id,
            stage_type=StageType.POEM,
            status=OrderStageStatus.PENDING,
            price=100
        )
        print(f"Stage created: {stage.id}, {stage.status}")

        # 4. Verify Reading
        print("Verifying data...")
        read_user = await user_repo.get_by_id(user.id)
        assert read_user.telegram_id == 123456789

        read_order = await order_repo.get_by_id(order.id)
        assert read_order.user_id == user.id

        # Check relationships (need to eager load or use select with options in real app, but lazy load might fail in async without explicit handling if session closed. However, here session is open)
        # For this simple test, we just check IDs.

        print("Acceptance test passed successfully!")

    await engine.dispose()


if __name__ == "__main__":
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(main())