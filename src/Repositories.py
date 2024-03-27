import uuid
from typing import TypeVar, Generic

from sqlalchemy.ext.asyncio import AsyncSession

from src.Entities import BaseEntity

Model = TypeVar('Model', bound=BaseEntity)


class MessageRepository(Generic[Model]):
    def __init__(self, model: type[Model], session: AsyncSession) -> None:
        self.model = model
        self.session = session

    async def create(self, data: dict) -> Model:
        instance = self.model(**data)
        self.session.add(instance)
        await self.session.commit()
        await self.session.refresh(instance)
        return instance

    async def get(self, pk: uuid.UUID) -> Model | None:
        return await self.session.get(self.model, pk)
