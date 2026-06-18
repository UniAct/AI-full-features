"""
Response signals enum module for standardized API feedback.
"""

from enum import Enum


class ResponseSignal(Enum):
    """
    Enumeration of response signals and messages used across the application.
    """

    FILE_VALITADED_SUCCESS = "File validated successfully."
    FILE_TYPE_NOT_SUPPORTED = "File type not allowed."
    FILE_SIZE_EXCEEDED = "File size exceeds the maximum allowed size of 50MB."
    FILE_UPLOAD_SUCCESS = "File uploaded successfully."
    FILE_UPLOADED_FAILED = "File upload failed."
    PROCESSING_FAILED = "Processing failed."
    PROCESSING_SUCCESS = "Processing successfully."
    NO_FILES_ERROR = "No files found in the project."
    FILE_ID_ERROR = "No file found with this ID."

    PROJECT_NOT_FOUND_ERROR = "Project not found."
    INSERT_INTO_VECTORDB_ERROR = "Error-inserting into vector database."
    INSERT_INTO_VECTORDB_SUCCESS = "Successfully inserted into vector database."
    VECTORDB_COLLECTION_RETRIEVED = "Vector database collection retrieved."
    VECTORDB_SEARCH_ERROR = "Error during vector database search."
    VECTORDB_SEARCH_SUCCESS = "Vector database search successful."
    RAG_ANSWER_ERROR = "Error generating RAG answer."
    RAG_ANSWER_SUCCESS = "RAG answer generated successfully."
    RAG_EXAM_ERROR = "Error generating RAG exam."
    RAG_EXAM_SUCCESS = "RAG exam generated successfully."
