from enum import Enum


class VectorDBEnums(Enum):
    QDRANT = "QDRANT"
    PGVECTOR = "PGVECTOR"


class DistanceMethodEnums(Enum):
    COSINE = "cosine"
    DOT = "dot"


class PgVectorTableSchemeEnums(Enum):
    ID = "id"
    TEXT = "text"
    VECTOR = "vector"
    CHUNK_ID = "chunk_id"
    METADATA = "metadata"
    _PREFIX = "pgvector"


class PgVectorDistanceMethodEnums(Enum):
    COSINE = "vector_cosine_ops"
    DOT = "vector_l2_ops"


# indexing - fast search
class PgVectorIndexTypeEnums(Enum):
    HNSW = "hnsw"  # hierarchiacal navigable small world graphs to search fast in embedings. (qdrant defauld) (pgvector by deafult is flat or greedy search in the whole embdings whithout any heuristics).
    IVFFLAT = "ivfflat"  # fast.
