import uuid
from datetime import datetime

from pydantic import BaseModel


class Message(BaseModel):
    pk: uuid.UUID
    member_id: int
    channel_id: int
    msg_id: int
    created_at: datetime

    class Config:
        from_attributes = True


class MessagePayload(BaseModel):
    member_id: int
    channel_id: int
    msg_id: int
    created_at: datetime
