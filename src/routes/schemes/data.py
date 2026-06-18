from pydantic import BaseModel
from typing import Optional


class ProcessRequest(BaseModel):
    file_id: str = None  # optional
    chunk_size: Optional[int] = 100  # use 100 if it is not get from the user
    chunk_overlap: Optional[int] = 20
    do_reset: Optional[int] = 0  # 0 for no reset (default)
    pdf_parser: Optional[str] = "fitz"  # 'fitz' or 'docling'
