from fastapi import APIRouter, FastAPI, Depends
from helpers.config import get_settings


base_router = APIRouter(
    prefix="/api/v1",
)

@base_router.get('/')
async def welcome(app_settings = Depends(get_settings)):
    
    project_name = app_settings.GROQ_API_KEY
    groq_api_key = app_settings.GROQ_API_KEY

    return {
        "message": "Welcome to the RAG",
        "project_name": project_name
    }

