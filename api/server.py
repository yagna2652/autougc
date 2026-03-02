"""
FastAPI server for AutoUGC video generation.

POST /api/v1/generate — O3 reference-to-video (SSE stream)
"""

from dotenv import load_dotenv

load_dotenv()

import logging
import sys

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    datefmt="%H:%M:%S",
    handlers=[logging.StreamHandler(sys.stdout)],
    force=True,
)

for logger_name in ["src.pipeline", "api", "uvicorn"]:
    logging.getLogger(logger_name).setLevel(logging.INFO)

logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("httpcore").setLevel(logging.WARNING)

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(
    title="AutoUGC API",
    description="O3 reference-to-video generation",
    version="3.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
async def health_check():
    return {"status": "ok", "service": "AutoUGC API", "version": "3.0.0"}


@app.get("/")
async def root():
    return {
        "service": "AutoUGC API",
        "version": "3.0.0",
        "endpoints": {
            "health": "/health",
            "generate": "POST /api/v1/generate",
            "prompts": "GET/POST /api/v1/prompts",
            "traces": "PUT /api/v1/traces/:id",
        },
    }


from src.prompt_store import PromptStore
from api.routes.generate import router as generate_router
from api.routes import prompts as prompts_module
from api.routes.prompts import router as prompts_router

# Shared prompt store
_prompt_store = PromptStore()
prompts_module.store = _prompt_store

app.include_router(generate_router, prefix="/api/v1", tags=["generate"])
app.include_router(prompts_router, prefix="/api/v1", tags=["prompts"])


if __name__ == "__main__":
    uvicorn.run(
        "api.server:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
    )
