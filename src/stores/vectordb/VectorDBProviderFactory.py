"""
Vector database provider factory module for creating specific VectorDB provider instances.
"""

from .providers import QdrantDBProvider, PGVectorProvider
from .VectorDBEnums import VectorDBEnums
from controllers.BaseController import BaseController
from sqlalchemy.orm import sessionmaker
from typing import Optional, Union, Any


class VectorDBProviderFactory:
    """
    Factory class to instantiate VectorDB providers based on configuration.
    """

    def __init__(self, config: Any, db_client: Optional[sessionmaker] = None):
        """
        Initializes the factory with application configuration and database client.
        """
        self.config = config
        self.base_controller = BaseController()
        self.db_client = db_client

    def create(self, provider: str) -> Optional[Union[QdrantDBProvider, PGVectorProvider]]:
        """
        Creates an instance of the specified VectorDB provider.
        
        Args:
            provider (str): The name/ID of the provider to create.
            
        Returns:
            Optional[Union[QdrantDBProvider, PGVectorProvider]]: The provider instance or None if not supported.
        """
        if provider == VectorDBEnums.QDRANT.value:
            qdrant_db_path = self.base_controller.get_database_path(db_name=self.config.VECTOR_DB_PATH)

            return QdrantDBProvider(
                db_client=qdrant_db_path,
                distance_method=self.config.VECTOR_DB_DISTANCE_METHOD,
                default_vector_size=self.config.EMBEDDING_MODEL_SIZE,
                index_threshold=self.config.VECTOR_DB_PGVEC_INDEX_THRESHOLD,
                qdrant_url=getattr(self.config, 'QDRANT_URL', None),
                qdrant_api_key=getattr(self.config, 'QDRANT_API_KEY', None),
            )
        
        if provider == VectorDBEnums.PGVECTOR.value:
            return PGVectorProvider(
                db_client=self.db_client,
                distance_method=self.config.VECTOR_DB_DISTANCE_METHOD,
                default_vector_size=self.config.EMBEDDING_MODEL_SIZE,
                index_threshold=self.config.VECTOR_DB_PGVEC_INDEX_THRESHOLD,
            )
        
        return None