import uuid
from datetime import datetime

from sqlalchemy import orm


class BaseEntity(orm.DeclarativeBase):
    pk: orm.Mapped[uuid.UUID] = orm.mapped_column(
        primary_key=True,
        default=uuid.uuid4)

    created_at: orm.Mapped[datetime] = orm.mapped_column(
        default=datetime.now)

    updated_at: orm.Mapped[datetime] = orm.mapped_column(
        default=datetime.now,
        onupdate=datetime.now)
