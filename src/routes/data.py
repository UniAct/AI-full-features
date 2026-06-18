"""
Data routes module for handling file uploads and document processing.
"""

from fastapi import APIRouter, Depends, UploadFile, status, Request
from fastapi.responses import JSONResponse
from helpers.config import get_settings, Settings
from controllers import (
    DataController,
    ProjectController,
    ProcessController,
    NLPController,
)
import os
import aiofiles
import logging
from .schemes.data import ProcessRequest
from models.ProjectModel import ProjectModel
from models.db_schemes import DataChunk, Asset
from models.ChunkModel import ChunkModel
from models.AssetModel import AssetModel
from models.enums.AssetTypeEnum import AssetTypeEnum
from models import ResponseSignal

logger = logging.getLogger("uvicorn.error")

data_router = APIRouter(
    prefix="/api/v1/data",
    tags=["api_v1", "data"],
)


@data_router.post("/upload/{project_id}")
async def upload_data(
    request: Request,
    project_id: str,
    file: UploadFile,
    app_settings: Settings = Depends(get_settings),
):
    """
    Handles file uploads for a specific project.

    Args:
        request (Request): The incoming request object.
        project_id (str): The project identifier.
        file (UploadFile): The file being uploaded.
        app_settings (Settings): Application configuration.

    Returns:
        JSONResponse: Upload status and file metadata.
    """
    project_model = await ProjectModel.create_instance(db_client=request.app.db_client)
    project = await project_model.get_project_or_create_one(project_id=project_id)

    data_controller = DataController()
    print(
        f"[debug] upload_data start: project_id={project_id}, filename={getattr(file, 'filename', None)}"
    )
    is_valid, result_signal = data_controller.validate_uploaded_file(file=file)
    print(f"[debug] validate result: {is_valid}, signal={result_signal}")

    if not is_valid:
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST, content={"signal": result_signal}
        )

    # Generate paths and IDs
    file_path, file_id = data_controller.generate_unique_filepath(
        orig_file_name=file.filename, project_id=project_id
    )
    try:
        print(f"[debug] writing to {file_path}")
        async with aiofiles.open(file_path, "wb") as f:
            while chunk := await file.read(app_settings.FILE_DEFAULT_CHUNCK_SIZE):
                await f.write(chunk)
        print(
            f"[debug] finished writing {file_path}, size={os.path.getsize(file_path)}"
        )
    except Exception as e:
        logger.error(f"Failed to save uploaded file: {e}")
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={"signal": ResponseSignal.FILE_UPLOADED_FAILED.value},
        )

    # Record asset in database
    asset_model = await AssetModel.create_instance(db_client=request.app.db_client)
    asset_resource = Asset(
        asset_project_id=project.project_id,
        asset_type=AssetTypeEnum.FILE.value,
        asset_name=file_id,
        asset_size=os.path.getsize(file_path),
    )
    try:
        asset_record = await asset_model.create_asset(asset=asset_resource)
    except Exception as e:
        logger.exception(f"Failed to create asset record for {file_id}: {e}")
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "signal": ResponseSignal.FILE_UPLOADED_FAILED.value,
                "detail": str(e),
            },
        )

    if asset_record is None:
        logger.error(f"Asset model returned None for {file_id}")
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "signal": ResponseSignal.FILE_UPLOADED_FAILED.value,
                "detail": "asset_record is None",
            },
        )

    # Debug logging: confirm saved file and DB record
    try:
        logger.info(
            f"Uploaded file saved at {file_path}; asset_id={getattr(asset_record, 'asset_id', None)}; asset_name={getattr(asset_record, 'asset_name', None)}"
        )
    except Exception:
        logger.exception("Failed to log asset record info")

    return JSONResponse(
        content={
            "signal": ResponseSignal.FILE_UPLOAD_SUCCESS.value,
            "file_id": str(getattr(asset_record, "asset_id", "")),
        }
    )


@data_router.get("/files/{project_id}")
async def list_project_files(request: Request, project_id: str):
    """List files for a project from DB and filesystem for debugging."""
    project_model = await ProjectModel.create_instance(db_client=request.app.db_client)
    project = await project_model.get_project_or_create_one(project_id=project_id)

    asset_model = await AssetModel.create_instance(db_client=request.app.db_client)
    project_files = await asset_model.get_all_project_assets(
        asset_project_id=project.project_id, asset_type=AssetTypeEnum.FILE.value
    )

    assets = [
        {
            "asset_id": str(r.asset_id),
            "asset_name": r.asset_name,
            "asset_size": r.asset_size,
        }
        for r in project_files
    ]

    project_path = ProjectController().get_project_path(project_id=project_id)
    filesystem = []
    try:
        for fn in os.listdir(project_path):
            try:
                filesystem.append(
                    {
                        "name": fn,
                        "size": os.path.getsize(os.path.join(project_path, fn)),
                    }
                )
            except Exception:
                filesystem.append({"name": fn, "size": None})
    except Exception as e:
        logger.exception(f"Failed to list project directory {project_path}: {e}")

    return JSONResponse(
        content={
            "signal": "Project files retrieved.",
            "assets": assets,
            "filesystem": filesystem,
        }
    )


@data_router.post("/process/{project_id}")
async def process_endpoint(
    request: Request, project_id: str, process_request: ProcessRequest
):
    """
    Processes uploaded files (parsing and chunking) for the RAG pipeline.
    """
    project_model = await ProjectModel.create_instance(db_client=request.app.db_client)
    project = await project_model.get_project_or_create_one(project_id=project_id)

    nlp_controller = NLPController(
        vectordb_client=request.app.vectordb_client,
        generation_client=request.app.generation_client,
        embedding_client=request.app.embedding_client,
        template_parser=request.app.template_parser,
    )

    asset_model = await AssetModel.create_instance(db_client=request.app.db_client)
    project_files_ids = {}

    if process_request.file_id:
        asset_record = await asset_model.get_asset_record(
            asset_project_id=project.project_id, asset_name=process_request.file_id
        )

        if asset_record is None:
            return JSONResponse(
                status_code=status.HTTP_400_BAD_REQUEST,
                content={"signal": ResponseSignal.FILE_ID_ERROR.value},
            )

        project_files_ids = {asset_record.asset_id: asset_record.asset_name}
    else:
        project_files = await asset_model.get_all_project_assets(
            asset_project_id=project.project_id, asset_type=AssetTypeEnum.FILE.value
        )
        project_files_ids = {
            record.asset_id: record.asset_name for record in project_files
        }

    if not project_files_ids:
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={"signal": ResponseSignal.NO_FILES_ERROR.value},
        )

    process_controller = ProcessController(project_id=project_id)
    chunk_model = await ChunkModel.create_instance(db_client=request.app.db_client)

    # Debug: log discovered project files mapping
    try:
        logger.info(
            f"Processing request for project {project.project_id}; files: {project_files_ids}"
        )
    except Exception:
        logger.exception("Failed to log project files ids")

    if process_request.do_reset:
        # Clear existing vectors and chunks
        collection_name = nlp_controller.create_collection_name(
            project_id=project.project_id
        )
        await request.app.vectordb_client.delete_collection(
            collection_name=collection_name
        )
        await chunk_model.delete_chunks_by_project_id(project_id=project.project_id)

    no_records = 0
    no_files = 0

    for asset_id, file_id in project_files_ids.items():
        try:
            logger.info(f"Processing asset_id={asset_id} file_id={file_id}")
            file_content = process_controller.get_file_content(
                file_id=file_id, pdf_parser=process_request.pdf_parser
            )

            if file_content is None:
                # Log full path for debugging
                try:
                    fp = os.path.join(process_controller.project_path, file_id)
                    logger.error(
                        f"Skipping file due to loading error: {file_id}; path={fp}"
                    )
                except Exception:
                    logger.exception("Error while computing file path for missing file")
                continue

            file_chunks, chapters = process_controller.process_file_content(
                file_content=file_content,
                file_id=file_id,
                chunk_size=process_request.chunk_size,
                chunk_overlap=process_request.chunk_overlap,
                llm_provider=request.app.generation_client,
            )
        except Exception as e:
            logger.exception(f"Error processing file {file_id}: {e}")
            return JSONResponse(
                status_code=status.HTTP_400_BAD_REQUEST,
                content={
                    "signal": ResponseSignal.PROCESSING_FAILED.value,
                    "detail": str(e),
                },
            )

        if not file_chunks:
            return JSONResponse(
                status_code=status.HTTP_400_BAD_REQUEST,
                content={"signal": ResponseSignal.PROCESSING_FAILED.value},
            )

        # Convert to database models
        file_chunks_records = [
            DataChunk(
                chunk_text=chunk.page_content,
                chunk_metadata=chunk.metadata,
                chunk_order=i + 1,
                chunk_project_id=project.project_id,
                chunk_asset_id=asset_id,
            )
            for i, chunk in enumerate(file_chunks)
        ]

        no_records += await chunk_model.insert_many_chunks(chunks=file_chunks_records)
        no_files += 1

    return JSONResponse(
        content={
            "signal": ResponseSignal.PROCESSING_SUCCESS.value,
            "inserted_chunks": no_records,
            "processed_files": no_files,
            "chapters": chapters
            if no_files == 1
            else [],  # only output chapters if exact file targeted, otherwise empty
        }
    )

@data_router.get("/chapters/{project_id}")
async def list_project_chapters(request: Request, project_id: str):
    """List all extracted chapters from the chunks of a project."""
    project_model = await ProjectModel.create_instance(db_client=request.app.db_client)
    project = await project_model.get_project_or_create_one(project_id=project_id)

    chunk_model = await ChunkModel.create_instance(db_client=request.app.db_client)
    chapters = await chunk_model.get_project_chapters(project_id=project.project_id)

    return JSONResponse(
        content={
            "signal": "Chapters retrieved successfully.",
            "chapters": chapters,
        }
    )


@data_router.post("/ingest/{project_id}")
async def ingest_file(
    request: Request,
    project_id: str,
    file: UploadFile,
    app_settings: Settings = Depends(get_settings),
):
    """
    Unified endpoint: Upload + Process + Push in a single call.
    Accepts a file, saves it, chunks it, embeds it, and indexes it into the vector DB.
    """
    # ── Step 1: Upload ──────────────────────────────────────────────────────
    project_model = await ProjectModel.create_instance(db_client=request.app.db_client)
    project = await project_model.get_project_or_create_one(project_id=project_id)

    data_controller = DataController()
    is_valid, result_signal = data_controller.validate_uploaded_file(file=file)

    if not is_valid:
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST, content={"signal": result_signal}
        )

    file_path, file_id = data_controller.generate_unique_filepath(
        orig_file_name=file.filename, project_id=project_id
    )

    try:
        async with aiofiles.open(file_path, "wb") as f:
            while chunk := await file.read(app_settings.FILE_DEFAULT_CHUNCK_SIZE):
                await f.write(chunk)
    except Exception as e:
        logger.error(f"Ingest upload failed: {e}")
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={"signal": ResponseSignal.FILE_UPLOADED_FAILED.value, "step": "upload"},
        )

    asset_model = await AssetModel.create_instance(db_client=request.app.db_client)
    asset_resource = Asset(
        asset_project_id=project.project_id,
        asset_type=AssetTypeEnum.FILE.value,
        asset_name=file_id,
        asset_size=os.path.getsize(file_path),
    )
    try:
        asset_record = await asset_model.create_asset(asset=asset_resource)
    except Exception as e:
        logger.exception(f"Ingest asset creation failed: {e}")
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"signal": ResponseSignal.FILE_UPLOADED_FAILED.value, "step": "upload"},
        )

    asset_id = asset_record.asset_id
    logger.info(f"Ingest: uploaded {file_id}, asset_id={asset_id}")

    # ── Step 2: Process (chunk) ─────────────────────────────────────────────
    process_controller = ProcessController(project_id=project_id)
    chunk_model = await ChunkModel.create_instance(db_client=request.app.db_client)

    try:
        file_content = process_controller.get_file_content(file_id=file_id)
        if file_content is None:
            return JSONResponse(
                status_code=status.HTTP_400_BAD_REQUEST,
                content={"signal": "Failed to read uploaded file.", "step": "process"},
            )

        file_chunks, chapters = process_controller.process_file_content(
            file_content=file_content,
            file_id=file_id,
            chunk_size=200,
            chunk_overlap=20,
            llm_provider=request.app.generation_client,
        )
    except Exception as e:
        logger.exception(f"Ingest processing failed: {e}")
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={"signal": ResponseSignal.PROCESSING_FAILED.value, "step": "process", "detail": str(e)},
        )

    if not file_chunks:
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={"signal": ResponseSignal.PROCESSING_FAILED.value, "step": "process"},
        )

    file_chunks_records = [
        DataChunk(
            chunk_text=chunk.page_content,
            chunk_metadata=chunk.metadata,
            chunk_order=i + 1,
            chunk_project_id=project.project_id,
            chunk_asset_id=asset_id,
        )
        for i, chunk in enumerate(file_chunks)
    ]

    inserted_chunks = await chunk_model.insert_many_chunks(chunks=file_chunks_records)
    logger.info(f"Ingest: processed {inserted_chunks} chunks from {file_id}")

    # ── Step 3: Push (embed + index) ────────────────────────────────────────
    nlp_controller = NLPController(
        vectordb_client=request.app.vectordb_client,
        generation_client=request.app.generation_client,
        embedding_client=request.app.embedding_client,
        template_parser=request.app.template_parser,
    )

    collection_name = nlp_controller.create_collection_name(
        project_id=project.project_id
    )
    await request.app.vectordb_client.create_collection(
        collection_name=collection_name,
        embedding_size=request.app.embedding_client.embedding_size,
        do_reset=0,  # never reset on single-file ingest
    )

    # Re-fetch the chunks we just inserted to get their DB IDs
    page_no = 1
    indexed_count = 0
    has_records = True

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
                content={"signal": ResponseSignal.INSERT_INTO_VECTORDB_ERROR.value, "step": "index"},
            )

        indexed_count += len(page_chunks)

    logger.info(f"Ingest: indexed {indexed_count} vectors for {file_id}")

    return JSONResponse(
        content={
            "signal": "File ingested successfully.",
            "file_id": str(asset_id),
            "file_name": file_id,
            "inserted_chunks": inserted_chunks,
            "indexed_vectors": indexed_count,
            "chapters": chapters,
        }
    )

