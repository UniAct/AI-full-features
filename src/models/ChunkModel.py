"""
Chunk model module for managing data chunks in the database.
"""

from .BaseDataModel import BaseDataModel
from .db_schemes import DataChunk
from sqlalchemy.future import select
from sqlalchemy import func, delete
from typing import List, Optional, Any


class ChunkModel(BaseDataModel):
    """
    Model for performing database operations on DataChunk records.
    """

    def __init__(self, db_client: object):
        """
        Initializes the chunk model with a database client.
        """
        super().__init__(db_client=db_client)

    @classmethod
    async def create_instance(cls, db_client: object) -> "ChunkModel":
        """
        Factory method to create a new instance of ChunkModel.
        """
        return cls(db_client)

    async def create_chunk(self, chunk: DataChunk) -> DataChunk:
        """
        Creates a new data chunk record in the database.
        """
        async with self.db_client() as session:
            async with session.begin():
                session.add(chunk)
            await session.commit()
            await session.refresh(chunk)
        return chunk

    async def get_chunk(self, chunk_id: str) -> Optional[DataChunk]:
        """
        Retrieves a single data chunk by its primary key.
        """
        async with self.db_client() as session:
            result = await session.execute(select(DataChunk).where(DataChunk.chunk_id == chunk_id))
            chunk = result.scalar_one_or_none()
        return chunk

    async def insert_many_chunks(self, chunks: List[DataChunk], batch_size: int = 100) -> int:
        """
        Inserts multiple data chunks into the database using batch processing.
        
        Args:
            chunks (List[DataChunk]): List of chunk objects to insert.
            batch_size (int): Number of records per transaction batch.
            
        Returns:
            int: The number of records inserted.
        """
        async with self.db_client() as session:
            async with session.begin():
                for i in range(0, len(chunks), batch_size):
                    batch = chunks[i:i+batch_size]
                    session.add_all(batch)
            await session.commit()
        return len(chunks)

    async def delete_chunks_by_project_id(self, project_id: Any) -> int:
        """
        Deletes all chunks associated with a specific project.
        
        Returns:
            int: The number of deleted rows.
        """
        async with self.db_client() as session:
            stmt = delete(DataChunk).where(DataChunk.chunk_project_id == project_id)
            result = await session.execute(stmt)
            await session.commit()
        return result.rowcount
    
    async def get_project_chunks(self, project_id: Any, page_no: int = 1, page_size: int = 50) -> List[DataChunk]:
        """
        Retrieves a paginated list of chunks for a specific project.
        """
        async with self.db_client() as session:
            stmt = (
                select(DataChunk)
                .where(DataChunk.chunk_project_id == project_id)
                .offset((page_no - 1) * page_size)
                .limit(page_size)
            )
            result = await session.execute(stmt)
            records = result.scalars().all()
        return records
        
    async def get_project_chapters(self, project_id: Any) -> List[dict]:
        """
        Retrieves a list of unique chapters for a specific project.
        """
        from .db_schemes import Asset
        async with self.db_client() as session:
            stmt = (
                select(DataChunk.chunk_metadata["chapter_title"].astext.label("chapter_title"), DataChunk.chunk_asset_id, Asset.asset_name)
                .join(Asset, DataChunk.chunk_asset_id == Asset.asset_id)
                .where(DataChunk.chunk_project_id == project_id)
                .where(DataChunk.chunk_metadata["chapter_title"].astext.isnot(None))
                .distinct()
            )
            result = await session.execute(stmt)
            records = result.all()
            
        chapters = []
        for row in records:
            if not row.chapter_title:
                continue
            # If the chapter is just "Document", use the asset_name instead for clarity
            display_title = row.chapter_title
            if display_title == "Document" and row.asset_name:
                display_title = row.asset_name
            elif row.asset_name:
                display_title = f"[{row.asset_name}] {row.chapter_title}"
                
            chapters.append({
                "chapter_title": display_title,
                "original_title": row.chapter_title, 
                "asset_id": str(row.chunk_asset_id)
            })
            
        return chapters

    async def get_total_chunks_count(self, project_id: Any) -> int:
        """
        Retrieves the total count of chunks for a specific project.
        """
        async with self.db_client() as session:
            count_sql = select(func.count(DataChunk.chunk_id)).where(DataChunk.chunk_project_id == project_id)
            records_count = await session.execute(count_sql)
            total_count = records_count.scalar()
        
        return total_count if total_count else 0