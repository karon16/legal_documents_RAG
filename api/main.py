import os
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.routes import ask, search, documents, stats, feedback
from pipeline.embedder import get_model

logging.basicConfig(
    level  = logging.INFO,
    format = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Loading embedding model on startup...")
    get_model()
    logger.info("Embedding model ready.")
    yield
    logger.info("Shutting down.")

app = FastAPI(
    title       = "JusticeCongo AI",
    description = "Assistant juridique basé sur l'IA pour le droit congolais.",
    version     = "1.0.0",
    lifespan    = lifespan,
)

_origins_env = os.getenv("ALLOWED_ORIGINS", "*")
origins = [o.strip() for o in _origins_env.split(",")]

app.add_middleware(
    CORSMiddleware,
    allow_origins     = origins,
    allow_credentials = True,
    allow_methods     = ["*"],
    allow_headers     = ["*"],
)

app.include_router(ask.router,       prefix="/api", tags=["Q&A"])
app.include_router(search.router,    prefix="/api", tags=["Search"])
app.include_router(documents.router, prefix="/api", tags=["Documents"])
app.include_router(stats.router,     prefix="/api", tags=["Stats"])
app.include_router(feedback.router,  prefix="/api", tags=["Feedback"])

@app.get("/", tags=["Health"])
def root():
    return {
        "name":    "JusticeCongo AI",
        "status":  "running",
        "version": "1.0.0",
        "docs":    "/docs",
    }

@app.get("/health", tags=["Health"])
def health():
    return {"status": "ok"}
