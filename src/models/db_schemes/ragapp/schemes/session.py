from .ragapp_base import SQLAlchemyBase
from sqlalchemy import Column, DateTime, func, String, ForeignKey
from sqlalchemy.dialects.postgresql import UUID, JSONB
import uuid
from sqlalchemy.orm import relationship

class Session(SQLAlchemyBase):
    __tablename__ = "sessions"

    session_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id = Column(String, ForeignKey("projects.project_id"), nullable=False)
    title = Column(String, nullable=True)
    filters = Column(JSONB, nullable=True) # Will store the file_chapter_filters

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), nullable=True)

    project = relationship("Project", back_populates="sessions")
    chat_messages = relationship("ChatMessage", back_populates="session", cascade="all, delete-orphan")
