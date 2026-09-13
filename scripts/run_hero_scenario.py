"""Run Relay's deterministic synthetic end-to-end rescue scenario."""

import asyncio
import json
from pathlib import Path

from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.models import Base
from app.repositories.network import NetworkStore
from app.repositories.uow import SqlAlchemyUnitOfWork
from app.services.demo_network import seed_demo_network
from app.workflows.hero import run_hero_scenario


async def main() -> None:
    database_path = Path("relay_hero_demo.db")
    if database_path.exists():
        database_path.unlink()
    engine = create_async_engine(f"sqlite+aiosqlite:///{database_path}")
    factory = async_sessionmaker(engine, expire_on_commit=False)
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    await seed_demo_network(factory)
    summary = await run_hero_scenario(NetworkStore(factory), lambda: SqlAlchemyUnitOfWork(factory))
    print(json.dumps(summary.model_dump(mode="json"), indent=2))
    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
