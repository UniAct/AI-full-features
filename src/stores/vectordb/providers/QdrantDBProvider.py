"""
Qdrant database provider module for handling vector storage and semantic search.
This module integrates with the Qdrant vector database.
"""

from qdrant_client import models, QdrantClient
from ..VectorDBInterface import VectorDBInterface
from ..VectorDBEnums import DistanceMethodEnums
import logging
from typing import List, Optional, Any
from models.db_schemes import RetrievedDocument


class QdrantDBProvider(VectorDBInterface):
    """
    Provider implementation for Qdrant vector database.
    """

    def __init__(
        self,
        db_client: str,
        default_vector_size: int = 786,
        distance_method: Optional[str] = None,
        index_threshold: int = 100,
        qdrant_url: Optional[str] = None,
        qdrant_api_key: Optional[str] = None,
    ):
        """
        Initializes the Qdrant provider.

        Args:
            db_client (str): Connection path or URL for Qdrant.
            default_vector_size (int): Default dimension size for vectors.
            distance_method (Optional[str]): Distance metric (COSINE or DOT).
            index_threshold (int): Threshold for indexing optimization.
            qdrant_url (Optional[str]): Qdrant Cloud URL.
            qdrant_api_key (Optional[str]): Qdrant Cloud API key.
        """
        self.client = None
        self.db_client = db_client
        self.distance_method = None
        self.default_vector_size = default_vector_size
        self.qdrant_url = qdrant_url
        self.qdrant_api_key = qdrant_api_key

        if distance_method == DistanceMethodEnums.COSINE.value:
            self.distance_method = models.Distance.COSINE
        elif distance_method == DistanceMethodEnums.DOT.value:
            self.distance_method = models.Distance.DOT

        self.logger = logging.getLogger("uvicorn")

    async def connect(self):
        """
        Establishes a connection to the Qdrant client.
        Supports both local path and cloud URL (with optional API key).
        """
        import os
        # Prefer URL passed from settings; fall back to os.getenv as last resort
        qdrant_url = self.qdrant_url or os.getenv("QDRANT_URL")
        qdrant_api_key = self.qdrant_api_key or os.getenv("QDRANT_API_KEY")

        if qdrant_url:
            self.logger.info(f"Connecting to Qdrant Cloud: {qdrant_url}")
            self.client = QdrantClient(url=qdrant_url, api_key=qdrant_api_key or None)
        else:
            self.logger.info(f"Connecting to Qdrant local path: {self.db_client}")
            self.client = QdrantClient(path=self.db_client)

    async def disconnect(self):
        """
        Closes the connection to the Qdrant client.
        """
        self.client = None

    async def is_collection_existed(self, collection_name: str) -> bool:
        """
        Checks if a specific collection exists in the vector database.
        """
        collections = self.client.get_collections()
        if not collections or not hasattr(collections, "collections"):
            return False
        return any(c.name == collection_name for c in collections.collections)

    async def list_all_collections(self) -> List:
        """
        Lists all available collections in the database.
        """
        collections = self.client.get_collections()
        if not collections or not hasattr(collections, "collections"):
            return []
        return collections.collections

    async def get_collection_info(self, collection_name: str) -> dict:
        """
        Retrieves metadata and statistics for a specific collection.
        """
        return self.client.get_collection(collection_name=collection_name)

    async def delete_collection(self, collection_name: str):
        """
        Deletes a collection from the database if it exists.
        """
        if await self.is_collection_existed(collection_name):
            self.logger.info(f"Deleting collection: {collection_name}")
            return self.client.delete_collection(collection_name=collection_name)

    async def create_collection(
        self, collection_name: str, embedding_size: int, do_reset: bool = False
    ) -> bool:
        """
        Creates a new collection in the database.

        Args:
            collection_name (str): Name of the collection.
            embedding_size (int): Dimension of the embedding vectors.
            do_reset (bool): If True, delete existing collection first.

        Returns:
            bool: True if created, False otherwise.
        """
        if do_reset:
            await self.delete_collection(collection_name=collection_name)

        if not await self.is_collection_existed(collection_name):
            self.logger.info(f"Creating new Qdrant collection: {collection_name}")

            self.client.create_collection(
                collection_name=collection_name,
                vectors_config=models.VectorParams(
                    size=embedding_size, distance=self.distance_method
                ),
            )
            try:
                self.client.create_payload_index(
                    collection_name=collection_name,
                    field_name="text",
                    field_schema=models.TextIndexParams(
                        type=models.TextIndexType.TEXT,
                        lowercase=True,
                    ),
                )
                self.client.create_payload_index(
                    collection_name=collection_name,
                    field_name="metadata.chapter_title",
                    field_schema=models.PayloadSchemaType.KEYWORD,
                )
                self.client.create_payload_index(
                    collection_name=collection_name,
                    field_name="metadata.file_id",
                    field_schema=models.PayloadSchemaType.KEYWORD,
                )
            except Exception as e:
                self.logger.warning(
                    f"Failed to create text payload index for keyword search: {e}"
                )
            return True

        return False

    async def insert_one(
        self,
        collection_name: str,
        text: str,
        vector: list,
        metadata: Optional[dict] = None,
        record_id: Optional[Any] = None,
    ) -> bool:
        """
        Inserts a single record into the specified collection.
        """
        if not await self.is_collection_existed(collection_name):
            self.logger.error(
                f"Cannot insert into non-existent collection: {collection_name}"
            )
            return False

        try:
            self.client.upsert(
                collection_name=collection_name,
                points=[
                    models.PointStruct(
                        id=record_id,
                        vector=vector,
                        payload={"text": text, "metadata": metadata},
                    )
                ],
            )
        except Exception as e:
            self.logger.error(f"Error during single record insertion: {e}")
            return False

        return True

    async def insert_many(
        self,
        collection_name: str,
        texts: list,
        vectors: list,
        metadata: Optional[list] = None,
        record_ids: Optional[list] = None,
        batch_size: int = 50,
    ) -> bool:
        """
        Inserts multiple records into the specified collection in batches.
        """
        if metadata is None:
            metadata = [None] * len(texts)

        if record_ids is None:
            record_ids = list(range(0, len(texts)))

        for i in range(0, len(texts), batch_size):
            batch_end = i + batch_size

            batch_texts = texts[i:batch_end]
            batch_vectors = vectors[i:batch_end]
            batch_metadata = metadata[i:batch_end]
            batch_record_ids = record_ids[i:batch_end]

            batch_records = [
                models.PointStruct(
                    id=batch_record_ids[x],
                    vector=batch_vectors[x],
                    payload={"text": batch_texts[x], "metadata": batch_metadata[x]},
                )
                for x in range(len(batch_texts))
            ]

            try:
                self.client.upsert(
                    collection_name=collection_name,
                    points=batch_records,
                )
            except Exception as e:
                self.logger.error(f"Error during batch insertion: {e}")
                return False

        return True

    def _build_filter(
        self,
        chapters: list = None,
        file_chapter_filters: list = None,
        keyword_query: str = None,
    ) -> Optional[models.Filter]:
        """
        Builds a Qdrant Filter from chapter/file filters and an optional keyword match.

        Args:
            chapters: List of chapter title strings to filter by.
            file_chapter_filters: List of dicts with optional 'file_id' and 'chapter_title' keys.
            keyword_query: Optional keyword string to add as a text MUST condition.

        Returns:
            A models.Filter instance or None if no conditions are present.
        """
        must_conditions = []

        if file_chapter_filters:
            file_ids = []
            chapter_titles = []
            for item in file_chapter_filters:
                fid = item.get("file_id")
                ch = item.get("chapter_title")
                if fid is not None:
                    file_ids.append(fid)
                if ch is not None:
                    chapter_titles.append(ch)

            if file_ids:
                must_conditions.append(
                    models.FieldCondition(
                        key="metadata.file_id",
                        match=models.MatchAny(any=file_ids),
                    )
                )
            if chapter_titles:
                must_conditions.append(
                    models.FieldCondition(
                        key="metadata.chapter_title",
                        match=models.MatchAny(any=chapter_titles),
                    )
                )
        elif chapters:
            must_conditions.append(
                models.FieldCondition(
                    key="metadata.chapter_title",
                    match=models.MatchAny(any=chapters),
                )
            )


        if keyword_query:
            must_conditions.append(
                models.FieldCondition(
                    key="text",
                    match=models.MatchText(text=keyword_query),
                )
            )

        if not must_conditions:
            return None
        return models.Filter(must=must_conditions)

    async def search_by_vector(
        self,
        collection_name: str,
        vector: list,
        limit: int = 5,
        chapters: list = None,
        file_chapter_filters: list = None,
    ) -> Optional[List[RetrievedDocument]]:
        """
        Performs dense semantic search using a query embedding vector.

        Args:
            collection_name: Target Qdrant collection.
            vector: Query embedding vector.
            limit: Maximum results to return.
            chapters: Optional chapter title filter.
            file_chapter_filters: Optional list of file/chapter filter dicts.

        Returns:
            List of RetrievedDocument ranked by cosine/dot similarity score.
        """
        self.logger.info(
            f"Qdrant vector search: collection={collection_name}; limit={limit}; "
            f"file_chapter_filters={file_chapter_filters}; chapters={chapters}"
        )

        query_filter = self._build_filter(
            chapters=chapters,
            file_chapter_filters=file_chapter_filters,
        )

        try:
            response = self.client.query_points(
                collection_name=collection_name,
                query=vector,
                limit=limit,
                query_filter=query_filter,
            )
            results = response.points
        except Exception as e:
            self.logger.error(f"Qdrant vector search failed: {e}")
            return []

        if not results:
            self.logger.info("Qdrant vector search returned no results")
            return []

        self.logger.info(f"Qdrant vector search returned {len(results)} results")
        return [
            RetrievedDocument(
                document_id=str(r.id),
                score=r.score,
                text=r.payload.get("text", ""),
            )
            for r in results
        ]

    async def search_by_keyword(
        self,
        collection_name: str,
        keyword_query: str,
        limit: int = 5,
        chapters: list = None,
        file_chapter_filters: list = None,
    ) -> Optional[List[RetrievedDocument]]:
        """
        Performs pure keyword/text search using Qdrant scroll with a MatchText filter.
        Results are ranked by their position (rank-based score) for RRF fusion.

        Args:
            collection_name: Target Qdrant collection.
            keyword_query: Raw keyword string to match in the 'text' payload field.
            limit: Maximum results to return.
            chapters: Optional chapter title filter.
            file_chapter_filters: Optional list of file/chapter filter dicts.

        Returns:
            List of RetrievedDocument with rank-based scores (1/(rank+1)).
        """
        self.logger.info(
            f"Qdrant keyword search: collection={collection_name}; keyword='{keyword_query}'; limit={limit}"
        )

        query_filter = self._build_filter(
            chapters=chapters,
            file_chapter_filters=file_chapter_filters,
            keyword_query=keyword_query,
        )

        try:
            scroll_results, _ = self.client.scroll(
                collection_name=collection_name,
                scroll_filter=query_filter,
                limit=limit,
                with_payload=True,
                with_vectors=False,
            )
        except Exception as e:
            self.logger.error(f"Qdrant keyword search (scroll) failed: {e}")
            return []

        if not scroll_results:
            self.logger.info("Qdrant keyword search returned no results")
            return []

        self.logger.info(f"Qdrant keyword search returned {len(scroll_results)} results")
        # Assign rank-based scores so RRF can fuse with vector results correctly
        return [
            RetrievedDocument(
                document_id=str(r.id),
                score=1.0 / (rank + 1),
                text=r.payload.get("text", ""),
            )
            for rank, r in enumerate(scroll_results)
        ]

    async def get_random_documents(
        self,
        collection_name: str,
        limit: int,
        chapters: list = None,
        file_chapter_filters: list = None,
    ) -> Optional[List[RetrievedDocument]]:
        """Fetches sequential documents matching the filters using scroll."""
        query_filter = self._build_filter(
            chapters=chapters,
            file_chapter_filters=file_chapter_filters,
        )

        try:
            scroll_results, _ = self.client.scroll(
                collection_name=collection_name,
                scroll_filter=query_filter,
                limit=limit,
                with_payload=True,
                with_vectors=False,
            )
        except Exception as e:
            self.logger.error(f"Qdrant fetch random failed: {e}")
            return []

        if not scroll_results:
            return []

        return [
            RetrievedDocument(
                document_id=str(r.id),
                score=1.0,
                text=r.payload.get("text", ""),
            )
            for r in scroll_results
        ]
