import asyncio
from qdrant_client import QdrantClient, models

async def patch_qdrant():
    client = QdrantClient(
        url="https://60e9e867-4466-4a41-9bbb-7b2c6b808e16.eu-west-1-0.aws.cloud.qdrant.io",
        api_key="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJhY2Nlc3MiOiJtIiwic3ViamVjdCI6ImFwaS1rZXk6NDNmZmRmMDMtOWQwNi00NjYyLWEwODUtNGUyZmNlZmRhNTU4In0.b15UmvQMR48BlKp3FxUEql4_YongBNXuWEhPyHV8Tpg"
    )
    collection_name = "collection_1024_my-project"
    
    print(f"Creating payload indexes on {collection_name}...")
    try:
        client.create_payload_index(
            collection_name=collection_name,
            field_name="metadata.chapter_title",
            field_schema=models.PayloadSchemaType.KEYWORD,
        )
        print("Successfully created metadata.chapter_title index.")
    except Exception as e:
        print(f"Error creating chapter_title index: {e}")

    try:
        client.create_payload_index(
            collection_name=collection_name,
            field_name="metadata.file_id",
            field_schema=models.PayloadSchemaType.KEYWORD,
        )
        print("Successfully created metadata.file_id index.")
    except Exception as e:
        print(f"Error creating file_id index: {e}")

if __name__ == "__main__":
    asyncio.run(patch_qdrant())
