from .BaseController import BaseController
from models.db_schemes import Project
from typing import List
from models.db_schemes import DataChunk
from stores.llm.LLMEnums import DocumentTypeEnum
import json

class NLPController(BaseController):

    def __init__(self, vectordb_client, generation_client, 
                 embedding_client, template_parser):
        super().__init__()

        self.vectordb_client = vectordb_client
        self.generation_client = generation_client
        self.embedding_client = embedding_client
        self.template_parser  = template_parser

    def create_collection_name(self, project_id: str):
        return f"collection_{project_id}".strip()

    async def reset_vector_db_collection(self, project: Project):
        collection_name = self.create_collection_name(project_id=project.project_id)
        return await self.vectordb_client.delete_collection(collection_name=collection_name)
    
    async def get_vector_db_collection_info(self, project: Project):
        collection_name = self.create_collection_name(project_id=project.project_id)
        collection_info = await self.vectordb_client.get_collection_info(collection_name=collection_name)
        return json.loads(
            json.dumps(collection_info, default=lambda x: x.__dict__)
        )


    async def index_into_vector_db(self, project: Project, chunks: List[DataChunk],
                                   chunks_ids: List[int], 
                                   do_reset: bool = False):
        
        # step1: get collection name
        collection_name = self.create_collection_name(project_id=project.project_id)

        # step2: manage items
        texts = [ c.chunk_text for c in chunks ]
        metadata = [ c.chunk_metadata for c in  chunks]
        vectors = self.embedding_client.embed_text(text=texts, 
                                                  document_type=DocumentTypeEnum.DOCUMENT.value)

                # step3: create collection if not exists
        _ = await self.vectordb_client.create_collection(
            collection_name=collection_name,
            embedding_size=self.embedding_client.embedding_size,
            do_reset=do_reset,
        )

        # step4: insert into vector db
        _ = await self.vectordb_client.insert_many(
            collection_name=collection_name,
            texts=texts,
            metadata=metadata,
            vectors=vectors,
            record_ids=chunks_ids,
        )

        return True


    async def search_vector_db_collection(
        self,
        project: Project,
        text: str,
        limit: int = 10
    ):
        # step 1: get collection name
        collection_name = self.create_collection_name(
            project_id=project.project_id
        )

        # step 2: get embedding vector
        vectors = self.embedding_client.embed_text(
            text=text,
            document_type=DocumentTypeEnum.QUERY.value
        )

        if not vectors or len(vectors) == 0:
            return []

        query_vector = vectors[0]

        if not isinstance(query_vector, list):
            return []

        # step 3: semantic search
        results = await self.vectordb_client.search_by_vector(
            collection_name=collection_name,
            vector=query_vector,
            limit=limit
        )

        if not results:
            return []

        return results


    async def answer_rag_question(self, project: Project, query: str, limit: int = 10):
        answer, full_prompt, chat_history = None, None, None

        # step1: retrieve related documents
        try:
            retrieved_documents = await self.search_vector_db_collection(
                project=project,
                text=query,
                limit=limit,
            )
            print(f"DEBUG retrieved_documents: {retrieved_documents}")
        except Exception as e:
            print(f"ERROR in search_vector_db_collection: {e}")
            raise

        if not retrieved_documents or len(retrieved_documents) == 0:
            print("DEBUG: No documents retrieved, returning early")
            return answer, full_prompt, chat_history

        # step2: Construct LLM prompt
        try:
            system_prompt = self.template_parser.get("rag", "system_prompt")
            print(f"DEBUG system_prompt OK")

            documents_prompts = "\n".join([
                self.template_parser.get("rag", "document_prompt", {
                    "doc_num": idx + 1,
                    "chunk_text": self.generation_client.process_text(doc.text),
                })
                for idx, doc in enumerate(retrieved_documents)
            ])
            print(f"DEBUG documents_prompts OK")

            footer_prompt = self.template_parser.get("rag", "footer_prompt", {
                "query": query
            })
            print(f"DEBUG footer_prompt OK")
        except Exception as e:
            print(f"ERROR building prompts: {e}")
            raise

        # step3: Construct Generation Client Prompts
        try:
            chat_history = [
                self.generation_client.construct_prompt(
                    prompt=system_prompt,
                    role=self.generation_client.enums.SYSTEM.value,
                )
            ]
            full_prompt = "\n\n".join([documents_prompts, footer_prompt])
            print(f"DEBUG full_prompt OK")
        except Exception as e:
            print(f"ERROR constructing chat history: {e}")
            raise

        # step4: Retrieve the Answer
        try:
            answer = self.generation_client.generate_text(
                prompt=full_prompt,
                chat_history=chat_history
            )
            print(f"DEBUG answer: {answer}")
        except Exception as e:
            print(f"ERROR in generate_text: {e}")
            raise

        return answer, full_prompt, chat_history