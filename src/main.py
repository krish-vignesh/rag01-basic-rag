from fastapi import FastAPI
from src.api.routes.health import router as health_router


app =  FastAPI(
    title ="Hybrid RAG API",
    version ="1.0.0",
)

app.include_router(health_router)