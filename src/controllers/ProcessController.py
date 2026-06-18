"""
Process controller module for handling document loading and text splitting.
"""

from .BaseController import BaseController
from .ProjectController import ProjectController
import os
from langchain_community.document_loaders import PyMuPDFLoader, TextLoader
from types import SimpleNamespace
from utils.docling_converter import convert_to_markdown, extract_markdown_chapters
from utils.PDFChapterParser import PDFChapterParser
from models import ProcessingEnum
from typing import List, Optional, Tuple
from dataclasses import dataclass
import logging

logger = logging.getLogger("uvicorn.error")
@dataclass
class Document:
    """
    Data class representing a processed document chunk.
    """

    page_content: str
    metadata: dict


class ProcessController(BaseController):
    """
    Controller for processing files, including loading content and splitting into chunks.
    """

    def __init__(self, project_id: str):
        """
        Initializes the process controller for a specific project.
        """
        super().__init__()
        self.project_id = project_id
        self.project_path = ProjectController().get_project_path(project_id=project_id)

    def get_file_extension(self, file_id: str) -> str:
        """
        Retrieves the file extension from a file ID.
        """
        return os.path.splitext(file_id)[-1]

    def get_file_loader(self, file_id: str, pdf_parser: str = "fitz"):
        """
        Returns the appropriate LangChain loader based on the file extension.

        Args:
            file_id (str): The ID/name of the file to load.
            pdf_parser (str): "fitz" or "docling" to determine PDF parsing strategy.

        Returns:
            Loader: A LangChain document loader or None if not supported.
        """
        file_ext = self.get_file_extension(file_id=file_id)
        file_path = os.path.join(self.project_path, file_id)

        if not os.path.exists(file_path):
            return None

        if file_ext == ProcessingEnum.TXT.value:
            return TextLoader(file_path, encoding="utf-8")

        if file_ext == ProcessingEnum.PDF.value:
            if pdf_parser == "fitz":
                return PyMuPDFLoader(file_path)
            elif pdf_parser == "docling":
                return None  # Returning None triggers the Docling fallback

        return None

    def get_file_content(self, file_id: str, pdf_parser: str = "fitz") -> Optional[List]:
        """
        Loads the content of a file using the detected loader.
        """
        file_ext = self.get_file_extension(file_id=file_id)
        file_path = os.path.join(self.project_path, file_id)

        # Prefer file-specific loaders (PyMuPDF for PDF, TextLoader for TXT)
        loader = self.get_file_loader(file_id=file_id, pdf_parser=pdf_parser)
        if loader is None:
            # Fallback to Docling conversion
            try:
                md = convert_to_markdown(file_path, do_ocr=True)
                return [SimpleNamespace(page_content=md, metadata={"page": 0})]
            except Exception:
                logger.exception(f"Docling conversion failed for {file_path}")
                return None

        try:
            # LangChain loaders typically expose a `load()` method returning documents
            docs = loader.load()
            return docs
        except Exception:
            logger.exception(f"Loader failed for {file_path}, falling back to Docling")
            try:
                md = convert_to_markdown(file_path, do_ocr=True)
                return [SimpleNamespace(page_content=md, metadata={"page": 0})]
            except Exception:
                logger.exception(f"Docling fallback failed for {file_path}")
                return None

    def process_file_content(
        self,
        file_content: list,
        file_id: str,
        chunk_size: int = 100,
        chunk_overlap: int = 20,
        llm_provider=None,
    ) -> Tuple[List[Document], List[dict]]:
        """
        Processes raw file content into structured data chunks, extracting chapter mapping.

        Args:
            file_content (list): Content list from the loader.
            file_id (str): The ID of the file being processed.
            chunk_size (int): Target size for each chunk.
            chunk_overlap (int): Overlap between chunks (currently not used in simpler splitter).

        Returns:
            Tuple[List[Document], List[dict]]: A tuple containing structured chunk items and an array of Chapter maps.
        """
        file_content_texts = [rec.page_content for rec in file_content]
        file_content_metadata = [
            rec.metadata.copy() if isinstance(rec.metadata, dict) else {}
            for rec in file_content
        ]

        for metadata in file_content_metadata:
            metadata["file_id"] = file_id
            metadata["page"] = metadata.get("page", 0) + 1

        detected_chapters = []
        if file_content_texts:
            # If this is a PDF, prefer the PDFChapterParser (fitz-based) to extract chapters
            if (
                self.get_file_extension(file_id=file_id).lower()
                == ProcessingEnum.PDF.value
            ):
                try:
                    # PDFChapterParser returns chapters with start_page/end_page (1-based)
                    page_chapters = PDFChapterParser.extract_chapters(
                        os.path.join(self.project_path, file_id)
                    )
                    # Map page-based chapters to character offsets within the joined text
                    # Build cumulative lengths per page
                    page_lengths = [len(p) for p in file_content_texts]
                    cum_lengths = [0]
                    for l in page_lengths:
                        cum_lengths.append(cum_lengths[-1] + l)

                    mapped = []
                    for c in page_chapters:
                        try:
                            start_page = int(c.get("start_page", 1))
                            end_page = int(c.get("end_page", start_page))
                            start_offset = cum_lengths[max(0, start_page - 1)]
                            end_offset = cum_lengths[min(len(page_lengths), end_page)]
                            mapped.append(
                                {
                                    "title": c.get("title", "Document"),
                                    "start_offset": start_offset,
                                    "end_offset": end_offset,
                                }
                            )
                        except Exception:
                            continue

                    if mapped:
                        detected_chapters = mapped
                    else:
                        detected_chapters = extract_markdown_chapters(
                            file_content_texts[0]
                        )
                except Exception:
                    logger.exception(
                        "PDFChapterParser failed; falling back to markdown chapter extraction"
                    )
                    detected_chapters = extract_markdown_chapters(file_content_texts[0])
            else:
                detected_chapters = extract_markdown_chapters(file_content_texts[0])

        chunks = self.process_simpler_splitter(
            texts=file_content_texts,
            metadatas=file_content_metadata,
            chunk_size=chunk_size,
            chapters=detected_chapters,
        )
        return chunks, detected_chapters

    def process_simpler_splitter(
        self,
        texts: List[str],
        metadatas: List[dict],
        chunk_size: int,
        splitter_tag: str = "\n",
        chapters: Optional[List[dict]] = None,
    ) -> List[Document]:
        """
        An optimized text splitting strategy that groups lines into chunks of a target size.

        Args:
            texts (List[str]): List of texts to split.
            metadatas (List[dict]): List of metadata dictionaries.
            chunk_size (int): Minimum character size for each chunk.
            splitter_tag (str): Tag used for joining and splitting lines.

        Returns:
            List[Document]: A list of chunked Document objects.
        """
        full_text = " ".join(texts)

        # Split into lines and filter out empty ones
        lines = [
            doc.strip() for doc in full_text.split(splitter_tag) if len(doc.strip()) > 1
        ]

        chunks = []
        current_chunk = ""
        current_offset = 0
        current_metadata = metadatas[0] if metadatas else {}

        def _chapter_title_for_offset(offset: int) -> Optional[str]:
            if not chapters:
                return None
            for chapter in reversed(chapters):
                if offset >= chapter["start_offset"]:
                    return chapter["title"]
            return chapters[0]["title"]

        for line in lines:
            if current_chunk == "":
                chunk_start_offset = current_offset

            current_chunk += line + splitter_tag
            current_offset += len(line) + len(splitter_tag)

            if len(current_chunk) >= chunk_size:
                chunk_metadata = current_metadata.copy()
                chapter_title = _chapter_title_for_offset(chunk_start_offset)
                if chapter_title:
                    chunk_metadata["chapter_title"] = chapter_title
                chunks.append(
                    Document(
                        page_content=current_chunk.strip(),
                        metadata=chunk_metadata,
                    )
                )
                current_chunk = ""

        # Handle any remaining text
        if current_chunk.strip():
            chunk_metadata = current_metadata.copy()
            chapter_title = _chapter_title_for_offset(chunk_start_offset)
            if chapter_title:
                chunk_metadata["chapter_title"] = chapter_title
            chunks.append(
                Document(page_content=current_chunk.strip(), metadata=chunk_metadata)
            )

        return chunks
