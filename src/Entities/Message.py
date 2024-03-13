from sqlalchemy import Integer
from sqlalchemy.orm import mapped_column, Mapped
from pgvector.sqlalchemy import Vector

from src.Entities.BaseEntity import BaseEntity


class Message(BaseEntity):
    __tablename__ = "message"

    member_id: Mapped[int] = mapped_column(Integer, nullable=False)
    channel_id: Mapped[int] = mapped_column(Integer, nullable=False)
    msg_id: Mapped[int] = mapped_column(Integer, nullable=False)
    embedding = mapped_column(Vector(1536), nullable=True)
