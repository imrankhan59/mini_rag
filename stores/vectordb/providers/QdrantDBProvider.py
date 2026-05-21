from qdrant_client import models, AsyncQdrantClient
from typing import List, Dict, Optional
import uuid
import logging
from models.db_schemes import RetrievedDocument


class QdrantDBProvider:

    def __init__(
        self,
        db_client: str,
        default_vector_size: int = 1536,
        distance_method=models.Distance.COSINE,
    ):

        self.db_path = db_client
        self.default_vector_size = default_vector_size
        self.distance_method = distance_method

        self.client: Optional[AsyncQdrantClient] = None
        self.logger = logging.getLogger("uvicorn")

    # -------------------------------------------------------
    # CONNECT / DISCONNECT
    # -------------------------------------------------------

    async def connect(self):
        """
        CHANGE: switched to AsyncQdrantClient
        """
        self.client = AsyncQdrantClient(path=self.db_path)

    async def disconnect(self):
        self.client = None

    # -------------------------------------------------------
    # COLLECTION CHECK
    # -------------------------------------------------------

    async def is_collection_existed(self, collection_name: str) -> bool:
        """
        CHANGE: async-safe call (no blocking sync client)
        """
        collections = await self.client.get_collections()
        return any(c.name == collection_name for c in collections.collections)

    # -------------------------------------------------------
    # CREATE COLLECTION
    # -------------------------------------------------------

    async def create_collection(
        self,
        collection_name: str,
        embedding_size: int,
        do_reset: bool = False
    ):

        """
        CHANGE:
        - removed sync client usage
        - made fully async
        - safer lifecycle (no accidental repeated deletion recommended)
        """

        if do_reset:
            await self.delete_collection(collection_name)

        exists = await self.is_collection_existed(collection_name)

        if not exists:
            self.logger.info(f"Creating collection: {collection_name}")

            await self.client.create_collection(
                collection_name=collection_name,
                vectors_config=models.VectorParams(
                    size=embedding_size,
                    distance=self.distance_method
                )
            )

            return True

        return False

    # -------------------------------------------------------
    # DELETE COLLECTION
    # -------------------------------------------------------

    async def delete_collection(self, collection_name: str):

        """
        CHANGE: async delete (no sync blocking)
        """

        exists = await self.is_collection_existed(collection_name)

        if not exists:
            return False

        self.logger.info(f"Deleting collection: {collection_name}")

        await self.client.delete_collection(collection_name)

        return True

    # -------------------------------------------------------
    # INSERT ONE
    # -------------------------------------------------------

    async def insert_one(
        self,
        collection_name: str,
        text: str,
        vector: list,
        metadata: Dict = None,
        record_id: str = None
    ):

        """
        CHANGE:
        - FIXED: removed upload_records (deprecated/wrong)
        - FIXED: correct PointStruct usage
        - FULL async insert
        """

        if not await self.is_collection_existed(collection_name):
            self.logger.error("Collection does not exist")
            return False

        record_id = record_id or str(uuid.uuid4())

        point = models.PointStruct(
            id=record_id,
            vector=vector,
            payload={
                "text": text,
                "metadata": metadata or {}
            }
        )

        await self.client.upsert(
            collection_name=collection_name,
            points=[point],
            wait=True
        )

        return True

    # -------------------------------------------------------
    # INSERT MANY (BATCH)
    # -------------------------------------------------------

    async def insert_many(
        self,
        collection_name: str,
        texts: List[str],
        vectors: List[list],
        metadata: List[Dict] = None,
        record_ids: List[str] = None,
        batch_size: int = 50
    ):

        """
        CHANGE:
        - fully async (no asyncio.to_thread needed)
        - safer validation
        - UUID fallback
        """

        if len(texts) != len(vectors):
            raise ValueError("texts and vectors length mismatch")

        if metadata is None:
            metadata = [{} for _ in texts]

        if len(metadata) != len(texts):
            raise ValueError("metadata length mismatch")

        if record_ids is None:
            record_ids = [str(uuid.uuid4()) for _ in texts]

        if len(record_ids) != len(texts):
            raise ValueError("record_ids length mismatch")

        for i in range(0, len(texts), batch_size):

            batch_texts = texts[i:i + batch_size]
            batch_vectors = vectors[i:i + batch_size]
            batch_metadata = metadata[i:i + batch_size]
            batch_ids = record_ids[i:i + batch_size]

            points = [
                models.PointStruct(
                    id=rid,
                    vector=vec,
                    payload={
                        "text": txt,
                        "metadata": meta
                    }
                )
                for txt, vec, meta, rid in zip(
                    batch_texts,
                    batch_vectors,
                    batch_metadata,
                    batch_ids
                )
            ]

            try:
                result = await self.client.upsert(
                    collection_name=collection_name,
                    points=points,
                    wait=True
                )

                self.logger.info(
                    f"Inserted batch {i}-{i+len(points)} | status={result.status}"
                )

            except Exception as e:
                self.logger.exception(f"Batch insert failed at {i}: {e}")
                raise

        return True

    # -------------------------------------------------------
    # SEARCH
    # -------------------------------------------------------

    async def search_by_vector(
        self,
        collection_name: str,
        vector: list,
        limit: int = 5
    ):

        """
        CHANGE:
        - FIXED: added return
        - fully async search
        """

        response = await self.client.query_points(
            collection_name=collection_name,
            query=vector,
            limit=limit
        )
        if not response.points or len(response.points)== 0:
            return None
        
        return [
            RetrievedDocument(**{
                "score": res.score,
                "text": res.payload["text"]
            })
            for res in response.points
        ]

    # -------------------------------------------------------
    # COLLECTION INFO
    # -------------------------------------------------------

    async def get_collection_info(self, collection_name: str) -> dict:
        return await self.client.get_collection(collection_name=collection_name)