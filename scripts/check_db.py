import asyncio
from sqlalchemy import select
from app.infra.db.session import async_session_factory
from app.infra.db.models import Order, OrderStage

async def check():
    async with async_session_factory() as session:
        from app.infra.db.models import User
        result = await session.execute(select(User))
        users = result.scalars().all()
        print(f"Found {len(users)} users")
        for u in users:
            print(f"User ID: {u.id}, TG ID: {u.telegram_id}, Username: {u.username}")

        result = await session.execute(select(Order).order_by(Order.created_at.desc()).limit(5))
        orders = result.scalars().all()
        print(f"Found {len(orders)} orders")
        for o in orders:
            print(f"Order ID: {o.id}, User ID: {o.user_id}, Stage: {o.current_stage}, Created: {o.created_at}")
            
        result = await session.execute(select(OrderStage).order_by(OrderStage.id.desc()).limit(5))
        stages = result.scalars().all()
        print(f"\nFound {len(stages)} stages")
        for s in stages:
            print(f"Stage ID: {s.id}, Order ID: {s.order_id}, Status: {s.status}, Price: {s.price}")

if __name__ == "__main__":
    asyncio.run(check())