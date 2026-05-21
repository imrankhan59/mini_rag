from fastapi import FastAPI
from contextlib import asynccontextmanager
from motor.motor_asyncio import AsyncIOMotorClient

from routes import base, data, nlp
from helpers.config import get_settings
from stores.llm.LLMProviderFactory import LLMProviderFactory
from stores.vectordb.VectorDBProviderFactory import VectorDBProviderFactory
from stores.llm.templates.template_parser import TemplateParser


@asynccontextmanager
async def lifespan(app: FastAPI):

    # -------------------
    # STARTUP
    # -------------------
    setting = get_settings()

    app.mongo_conn = AsyncIOMotorClient(setting.MONGODB_URL)
    app.db_client = app.mongo_conn[setting.MONGODB_DATABASE]

    llm_provider_factory = LLMProviderFactory(setting)
    vectordb_provider_factory = VectorDBProviderFactory(setting)

    app.generation_client = llm_provider_factory.create(
        provider=setting.GENERATION_BACKEND
    )

    app.embedding_client = llm_provider_factory.create(
        provider=setting.EMBEDDING_BACKEND
    )

    app.generation_client.set_generation_model(
        model_id=setting.GENERATION_MODEL_ID
    )

    app.embedding_client.set_embedding_model(
        model_id=setting.EMBEDDING_MODEL_ID,
        embedding_size=setting.EMBEDDING_MODEL_SIZE
    )

    app.vectordb_client = vectordb_provider_factory.create(
        provider=setting.VECTOR_DB_BACKEND
    )

    await app.vectordb_client.connect()

    app.template_parser = TemplateParser(
        language=setting.PRIMARY_LANG,
        default_language=setting.DEFAULT_LANG
    )

    # -------------------
    # APP RUNNING
    # -------------------
    yield

    # -------------------
    # SHUTDOWN
    # -------------------
    app.mongo_conn.close()
    app.vectordb_client.disconnect()


app = FastAPI(lifespan=lifespan)

app.include_router(base.base_router)
app.include_router(data.data_router)
app.include_router(nlp.nlp_router)


