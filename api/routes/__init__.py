"""
API routes package.

Available routers:
- pipeline: UGC video generation pipeline endpoints
"""

from api.routes.pipeline import router as pipeline_router

__all__ = ["pipeline_router"]
