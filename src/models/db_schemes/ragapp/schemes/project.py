from .ragapp_base import SQLAlchemyBase
from sqlalchemy import Column, Integer, DateTime, func, String
from sqlalchemy.dialects.postgresql import UUID
import uuid
from sqlalchemy.orm import relationship

class Project(SQLAlchemyBase):

    __tablename__ = "projects" # table project 
    
    # columns naming - in real projects use just one of them.
    project_id = Column(String, primary_key=True) # primary key -> string for custom IDs
    project_uuid = Column(UUID(as_uuid=True), default=uuid.uuid4, unique=True, nullable=False) # like the mongodb id (random ex: #gjf934u3093gf...) user will see it and retrieve with it.

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False) # once a record created add it. 
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), nullable=True)

    chunks = relationship("DataChunk", back_populates="project")
    assets = relationship("Asset", back_populates="project")
    sessions = relationship("Session", back_populates="project")