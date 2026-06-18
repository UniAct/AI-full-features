"""
NLP routes module for handling indexing, searching, and RAG operations.
"""

from fastapi import APIRouter, status, Request
from fastapi.responses import JSONResponse
from routes.schemes.nlp import PushRequest, SearchRequest, ExamRequest, EvaluateRequest, SummarizeContextRequest
from models.ProjectModel import ProjectModel
from models.ChunkModel import ChunkModel
from controllers import NLPController
from models import ResponseSignal
from tqdm.auto import tqdm
import logging

logger = logging.getLogger("uvicorn.error")

nlp_router = APIRouter(
    prefix="/api/v1/nlp",
    tags=["api_v1", "nlp"],
)


@nlp_router.post("/index/push/{project_id}")
async def index_project(request: Request, project_id: str, push_request: PushRequest):
    """
    Indexes project data into the vector database.

    Args:
        request (Request): The incoming request object.
        project_id (str): The ID of the project to index.
        push_request (PushRequest): Configuration for the indexing operation.

    Returns:
        JSONResponse: Status of the indexing operation.
    """
    project_model = await ProjectModel.create_instance(db_client=request.app.db_client)
    chunk_model = await ChunkModel.create_instance(db_client=request.app.db_client)

    project = await project_model.get_project_or_create_one(project_id=project_id)

    if not project:
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={"signal": ResponseSignal.PROJECT_NOT_FOUND_ERROR.value},
        )

    nlp_controller = NLPController(
        vectordb_client=request.app.vectordb_client,
        generation_client=request.app.generation_client,
        embedding_client=request.app.embedding_client,
        template_parser=request.app.template_parser,
    )

    page_no = 1
    inserted_items_count = 0
    has_records = True

    # Initialize collection
    collection_name = nlp_controller.create_collection_name(
        project_id=project.project_id
    )
    await request.app.vectordb_client.create_collection(
        collection_name=collection_name,
        embedding_size=request.app.embedding_client.embedding_size,
        do_reset=push_request.do_reset,
    )

    # Setup progress bar
    total_chunks_count = await chunk_model.get_total_chunks_count(
        project_id=project.project_id
    )
    pbar = tqdm(total=total_chunks_count, desc="Vector Indexing", position=0)

    while has_records:
        page_chunks = await chunk_model.get_project_chunks(
            project_id=project.project_id, page_no=page_no
        )

        if not page_chunks:
            has_records = False
            break

        page_no += 1
        chunks_ids = [c.chunk_id for c in page_chunks]

        is_inserted = await nlp_controller.index_into_vector_db(
            project=project, chunks=page_chunks, chunks_ids=chunks_ids
        )

        if not is_inserted:
            return JSONResponse(
                status_code=status.HTTP_400_BAD_REQUEST,
                content={"signal": ResponseSignal.INSERT_INTO_VECTORDB_ERROR.value},
            )

        pbar.update(len(page_chunks))
        inserted_items_count += len(page_chunks)

    return JSONResponse(
        content={
            "signal": ResponseSignal.INSERT_INTO_VECTORDB_SUCCESS.value,
            "inserted_items_count": inserted_items_count,
        }
    )


@nlp_router.get("/index/info/{project_id}")
async def get_project_index_info(request: Request, project_id: str):
    """
    Retrieves information about the project's vector database index.
    """
    project_model = await ProjectModel.create_instance(db_client=request.app.db_client)
    project = await project_model.get_project_or_create_one(project_id=project_id)

    nlp_controller = NLPController(
        vectordb_client=request.app.vectordb_client,
        generation_client=request.app.generation_client,
        embedding_client=request.app.embedding_client,
        template_parser=request.app.template_parser,
    )

    collection_info = await nlp_controller.get_vector_db_collection_info(
        project=project
    )

    return JSONResponse(
        content={
            "signal": ResponseSignal.VECTORDB_COLLECTION_RETRIEVED.value,
            "collection_info": collection_info,
        }
    )


@nlp_router.post("/index/search/{project_id}")
async def search_index(
    request: Request, project_id: str, search_request: SearchRequest
):
    """
    Performs a semantic search against the project's index.
    """
    project_model = await ProjectModel.create_instance(db_client=request.app.db_client)
    project = await project_model.get_project_or_create_one(project_id=project_id)

    nlp_controller = NLPController(
        vectordb_client=request.app.vectordb_client,
        generation_client=request.app.generation_client,
        embedding_client=request.app.embedding_client,
        template_parser=request.app.template_parser,
    )

    results = await nlp_controller.search_vector_db_collection(
        project=project,
        text=search_request.text,
        limit=search_request.limit,
        file_chapter_filters=search_request.file_chapter_filters,
    )

    if results is False:
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={"signal": ResponseSignal.VECTORDB_SEARCH_ERROR.value},
        )

    return JSONResponse(
        content={
            "signal": ResponseSignal.VECTORDB_SEARCH_SUCCESS.value,
            "results": [result.dict() for result in results],
        }
    )


@nlp_router.post("/index/answer/{project_id}")
async def answer_rag(request: Request, project_id: str, search_request: SearchRequest):
    """
    Generates a RAG-based answer for a given query and project.
    """
    project_model = await ProjectModel.create_instance(db_client=request.app.db_client)
    project = await project_model.get_project_or_create_one(project_id=project_id)

    nlp_controller = NLPController(
        vectordb_client=request.app.vectordb_client,
        generation_client=request.app.generation_client,
        embedding_client=request.app.embedding_client,
        template_parser=request.app.template_parser,
    )

    answer, full_prompt, chat_history = await nlp_controller.answer_rag_question(
        project=project,
        query=search_request.text,
        limit=search_request.limit,
        file_chapter_filters=search_request.file_chapter_filters,
    )

    if not answer:
        detail = (
            getattr(request.app.generation_client, "last_error", None)
            or getattr(request.app.embedding_client, "last_error", None)
            or "LLM returned no content."
        )
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={
                "signal": ResponseSignal.RAG_ANSWER_ERROR.value,
                "detail": detail,
            },
        )

    return JSONResponse(
        content={
            "signal": ResponseSignal.RAG_ANSWER_SUCCESS.value,
            "answer": answer,
            "full_prompt": full_prompt,
            "chat_history": chat_history,
        }
    )


@nlp_router.post("/index/exam/{project_id}")
async def generate_exam(request: Request, project_id: str, exam_request: ExamRequest):
    """
    Generates an exam from the project's indexed content.
    """
    project_model = await ProjectModel.create_instance(db_client=request.app.db_client)
    project = await project_model.get_project_or_create_one(project_id=project_id)

    nlp_controller = NLPController(
        vectordb_client=request.app.vectordb_client,
        generation_client=request.app.generation_client,
        embedding_client=request.app.embedding_client,
        template_parser=request.app.template_parser,
    )

    exam = await nlp_controller.generate_exam_from_context(
        project=project,
        content=exam_request.content,
        difficulty=exam_request.difficulty,
        num_mcq=exam_request.num_mcq,
        num_written=exam_request.num_written,
        chapters=exam_request.chapters,
        file_chapter_filters=exam_request.file_chapter_filters,
    )

    if exam is False:
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={
                "signal": ResponseSignal.RAG_EXAM_ERROR.value,
                "error": "Unexpected exam generation failure. Verify the vector DB and LLM backends.",
            },
        )

    # Only treat as an error if there are no usable questions at all
    has_questions = isinstance(exam, dict) and (
        exam.get("mcq_questions") or exam.get("written_questions")
    )

    if isinstance(exam, dict) and exam.get("error") and not has_questions:
        response_content = {
            "signal": ResponseSignal.RAG_EXAM_ERROR.value,
            "error": exam.get("error"),
        }
        if exam.get("detail"):
            response_content["detail"] = exam.get("detail")
        if exam.get("raw_output"):
            response_content["raw_output"] = exam.get("raw_output")
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content=response_content,
        )

    return JSONResponse(
        content={
            "signal": ResponseSignal.RAG_EXAM_SUCCESS.value,
            "exam": exam,
        }
    )


@nlp_router.post("/index/evaluate/{project_id}")
async def evaluate_rag_route(request: Request, project_id: str, evaluate_request: EvaluateRequest):
    """
    Evaluates the RAG pipeline using RAGAS for a given set of questions.
    """
    project_model = await ProjectModel.create_instance(db_client=request.app.db_client)
    project = await project_model.get_project_or_create_one(project_id=project_id)

    if not project:
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={"signal": ResponseSignal.PROJECT_NOT_FOUND_ERROR.value},
        )

    nlp_controller = NLPController(
        vectordb_client=request.app.vectordb_client,
        generation_client=request.app.generation_client,
        embedding_client=request.app.embedding_client,
        template_parser=request.app.template_parser,
    )

    questions_data = [q.dict() for q in evaluate_request.questions]

    results = await nlp_controller.evaluate_rag(
        project=project,
        questions=questions_data,
    )

    if "error" in results:
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={"signal": "RAGAS evaluation failed.", "detail": results["error"]},
        )

    return JSONResponse(
        content={
            "signal": "RAGAS evaluation successful.",
            "avg_scores": results["avg_scores"],
            "per_question_scores": results["per_question_scores"],
        }
    )

# ==========================================
# New Route: Document Summarization
# ==========================================

from pydantic import BaseModel

# 1. Define the request scheme for summarization
class SummarizeRequest(BaseModel):
    text: str

@nlp_router.post("/index/summarize/{project_id}")
async def summarize_context(request: Request, project_id: str, summarize_request: SummarizeContextRequest):
    """
    Summarizes content directly from the vector database, optionally filtered by chapter.
    """
    project_model = await ProjectModel.create_instance(db_client=request.app.db_client)
    project = await project_model.get_project_or_create_one(project_id=project_id)

    nlp_controller = NLPController(
        vectordb_client=request.app.vectordb_client,
        generation_client=request.app.generation_client,
        embedding_client=request.app.embedding_client,
        template_parser=request.app.template_parser,
    )

    result = await nlp_controller.summarize_from_context(
        project=project,
        content=summarize_request.content,
        file_chapter_filters=summarize_request.file_chapter_filters,
    )

    if "error" in result:
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={
                "signal": ResponseSignal.RAG_ANSWER_ERROR.value,
                "error": result["error"],
            },
        )

    return JSONResponse(
        content={
            "signal": ResponseSignal.RAG_ANSWER_SUCCESS.value,
            "summary": result["summary"],
        }
    )


@nlp_router.post("/summarize")
async def summarize_document_route(request: Request, summarize_request: SummarizeRequest):
    """
    Summarizes a given text using the dedicated Modal Summarization API.
    """
    # Initialize the controller (no project ID needed for pure summarization)
    nlp_controller = NLPController(
        vectordb_client=request.app.vectordb_client,
        generation_client=request.app.generation_client,
        embedding_client=request.app.embedding_client,
        template_parser=request.app.template_parser,
    )

    # Call the new summarize_document function we added to the controller
    result = await nlp_controller.summarize_document(text=summarize_request.text)

    if "error" in result:
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={
                "signal": "SUMMARIZATION_ERROR",
                "error": result["error"],
                "detail": result.get("detail", "")
            },
        )

    return JSONResponse(
        content={
            "signal": "SUMMARIZATION_SUCCESS",
            "summary": result["summary"],
        }
    )