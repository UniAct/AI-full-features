from .BaseDataModel import BaseDataModel
from .db_schemes import Session, ChatMessage
from sqlalchemy.sql import text, select
from typing import List, Optional
import uuid

class SessionModel(BaseDataModel):
    """
    Model for managing database interactions related to sessions and chat messages.
    """

    def __init__(self, db_client: object):
        """
        Initializes the Session model with a database client.
        """
        super().__init__(db_client)

    @classmethod
    async def create_instance(cls, db_client: object):
        """
        Creates and initializes an instance of SessionModel.
        """
        instance = cls(db_client)
        await instance.init()
        return instance

    async def create_session(self, project_id: str, title: Optional[str] = None, filters: Optional[list] = None) -> Session:
        """
        Creates a new chat session for a project.
        """
        async with self.db_client() as db_session:
            async with db_session.begin():
                session_obj = Session(
                    project_id=project_id,
                    title=title,
                    filters=filters
                )
                db_session.add(session_obj)
                await db_session.flush()
                await db_session.refresh(session_obj)
                return session_obj

    async def get_session(self, session_id: str) -> Optional[Session]:
        """
        Retrieves a session by its ID.
        """
        async with self.db_client() as db_session:
            async with db_session.begin():
                stmt = select(Session).where(Session.session_id == uuid.UUID(session_id))
                result = await db_session.execute(stmt)
                return result.scalar_one_or_none()

    async def list_sessions(self, project_id: str) -> List[Session]:
        """
        Retrieves all sessions for a specific project, ordered by creation date descending.
        """
        async with self.db_client() as db_session:
            async with db_session.begin():
                stmt = select(Session).where(Session.project_id == project_id).order_by(Session.created_at.desc())
                result = await db_session.execute(stmt)
                return result.scalars().all()

    async def get_session_history(self, session_id: str, limit: int = 50) -> List[ChatMessage]:
        """
        Retrieves the latest chat messages for a given session.
        """
        async with self.db_client() as db_session:
            async with db_session.begin():
                stmt = select(ChatMessage).where(
                    ChatMessage.session_id == uuid.UUID(session_id)
                ).order_by(ChatMessage.created_at.asc()).limit(limit)
                
                result = await db_session.execute(stmt)
                return list(result.scalars().all())

    async def add_chat_message(self, session_id: str, role: str, content: str) -> ChatMessage:
        """
        Inserts a new chat message into the session history.
        """
        async with self.db_client() as db_session:
            async with db_session.begin():
                message_obj = ChatMessage(
                    session_id=uuid.UUID(session_id),
                    role=role,
                    content=content
                )
                db_session.add(message_obj)
                await db_session.flush()
                await db_session.refresh(message_obj)
                return message_obj
