from collections.abc import AsyncGenerator

from sqlalchemy import exc
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from Config import settings


async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    engine = create_async_engine(settings.get_db_url())
    factory = async_sessionmaker(engine)
    async with factory() as session:
        try:
            yield session
            await session.commit()
        except exc.SQLAlchemyError as error:
            await session.rollback()
            raise
