from sqlalchemy import Inspector
from sqlalchemy.ext.asyncio import create_async_engine

from Config import settings
from src.Entities import BaseEntity
from src.Logger import Logger

logger_factory = Logger('database')
logger = logger_factory.get_logger()


async def migrate_tables() -> None:
    logger.info('Syncing tables')
    engine = create_async_engine(settings.get_db_url())
    async with engine.begin() as conn:
        def get_table_names(sync_conn):
            inspector = Inspector.from_engine(sync_conn)
            return inspector.get_table_names()

        tables_before = await conn.run_sync(get_table_names)
        await conn.run_sync(BaseEntity.metadata.create_all)
        tables_after = await conn.run_sync(get_table_names)

    new_tables = set(tables_after) - set(tables_before)
    if new_tables:
        logger.info(f'New tables created: {", ".join(new_tables)}')
    else:
        logger.info('No new tables created')

    logger.info('Tables are synced')
