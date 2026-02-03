import uuid
from datetime import datetime
from sqlalchemy import String, DateTime
from sqlalchemy.orm import Mapped, mapped_column

def uuid4_str() -> str:
    return str(uuid.uuid4())

class HasId:
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid4_str)

class HasCreatedAt:
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
