"""
Session routes module for creating and managing chat sessions.

Route map (prefix: /api/v1/sessions):
  POST   /{project_id}             → create a new session for a project
  GET    /{project_id}/{session_id} → get session info (optional)
  POST   /{session_id}/chat        → send a message in an existing session
"""

from fastapi import APIRouter, Request, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import Optional
from models.ProjectModel import ProjectModel
from models.SessionModel import SessionModel
from controllers import NLPController
from models import ResponseSignal


session_router = APIRouter(
    prefix="/api/v1/sessions",
    tags=["api_v1", "sessions"],
)


class CreateSessionRequest(BaseModel):
    title: Optional[str] = "New Chat"
    filters: Optional[list] = None


class ChatMessageRequest(BaseModel):
    text: str
    limit: Optional[int] = 5


@session_router.post("/project/{project_id}")
async def create_session(
    request: Request, project_id: str, payload: CreateSessionRequest = None
):
    """
    Creates a new chat session for a project.
    Accepts an optional JSON body with title and filters.
    """
    if payload is None:
        payload = CreateSessionRequest()

    project_model = await ProjectModel.create_instance(db_client=request.app.db_client)
    project = await project_model.get_project_or_create_one(project_id=project_id)

    session_model = await SessionModel.create_instance(db_client=request.app.db_client)
    session = await session_model.create_session(
        project_id=project.project_id, title=payload.title, filters=payload.filters
    )

    return JSONResponse(
        content={
            "signal": "Session created successfully.",
            "session_id": str(session.session_id),
        }
    )


@session_router.get("/project/{project_id}/list")
async def list_sessions(request: Request, project_id: str):
    """
    Retrieves all sessions for a specific project.
    """
    session_model = await SessionModel.create_instance(db_client=request.app.db_client)
    sessions = await session_model.list_sessions(project_id=project_id)
    
    return JSONResponse(
        content={
            "signal": "Sessions retrieved.",
            "sessions": [
                {
                    "session_id": str(s.session_id),
                    "title": s.title,
                    "created_at": str(s.created_at) if s.created_at else None,
                    "filters": s.filters
                } for s in sessions
            ]
        }
    )

@session_router.get("/project/{project_id}/{session_id}")
async def get_session(request: Request, project_id: str, session_id: str):
    """
    Retrieves information about a specific session.
    """
    session_model = await SessionModel.create_instance(db_client=request.app.db_client)
    session = await session_model.get_session(session_id=session_id)

    if not session:
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={"signal": "Session not found."},
        )

    return JSONResponse(
        content={
            "signal": "Session retrieved.",
            "session_id": str(session.session_id),
            "title": session.title if hasattr(session, "title") else None,
            "filters": session.filters,
        }
    )

@session_router.get("/{session_id}/history")
async def get_session_history(request: Request, session_id: str):
    """
    Retrieves the chat history for a session.
    """
    session_model = await SessionModel.create_instance(db_client=request.app.db_client)
    messages = await session_model.get_session_history(session_id=session_id, limit=50)
    
    return JSONResponse(
        content={
            "signal": "History retrieved.",
            "history": [
                {
                    "role": m.role,
                    "content": m.content,
                    "created_at": str(m.created_at)
                } for m in messages
            ]
        }
    )


@session_router.post("/{session_id}/chat")
async def chat_with_session(
    request: Request, session_id: str, payload: ChatMessageRequest
):
    """
    Continues a chat session, leveraging stored filters and persisting chat history.
    """
    session_model = await SessionModel.create_instance(db_client=request.app.db_client)
    session = await session_model.get_session(session_id=session_id)

    if not session:
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={"signal": "Session not found."},
        )

    project_model = await ProjectModel.create_instance(db_client=request.app.db_client)
    project = await project_model.get_project_or_create_one(
        project_id=session.project_id
    )

    nlp_controller = NLPController(
        vectordb_client=request.app.vectordb_client,
        generation_client=request.app.generation_client,
        embedding_client=request.app.embedding_client,
        template_parser=request.app.template_parser,
    )

    # Pass filters stored in the session
    file_chapter_filters = session.filters if session.filters else None

    # Load recent history from DB
    history_messages = await session_model.get_session_history(
        session_id=session_id, limit=20
    )
    
    # Reverse to get chronological order (oldest first)
    history_messages = list(reversed(history_messages))

    # Build chat history for the generation client
    formatted_history = []
    system_prompt_str = nlp_controller.template_parser.get("rag", "system_prompt")
    formatted_history.append(
        nlp_controller.generation_client.construct_prompt(
            prompt=system_prompt_str,
            role=nlp_controller.generation_client.enums.SYSTEM.value,
        )
    )

    for msg in history_messages:
        role_enum = (
            nlp_controller.generation_client.enums.USER.value
            if msg.role == "user"
            else nlp_controller.generation_client.enums.ASSISTANT.value
        )
        formatted_history.append(
            nlp_controller.generation_client.construct_prompt(
                prompt=msg.content, role=role_enum
            )
        )

    answer, full_prompt, _ = await nlp_controller.answer_rag_question(
        project=project,
        query=payload.text,
        limit=payload.limit,
        file_chapter_filters=file_chapter_filters,
        inject_history=formatted_history,
    )

    if not answer:
        detail = (
            getattr(request.app.generation_client, "last_error", None)
            or getattr(request.app.embedding_client, "last_error", None)
            or "LLM returned no content."
        )
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={"signal": ResponseSignal.RAG_ANSWER_ERROR.value, "detail": detail},
        )

    # Persist the exchange to DB
    await session_model.add_chat_message(
        session_id=session_id, role="user", content=payload.text
    )
    await session_model.add_chat_message(
        session_id=session_id, role="assistant", content=answer
    )

    return JSONResponse(content={"signal": "Message successful.", "answer": answer})
