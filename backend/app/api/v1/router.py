"""Main API v1 router aggregator"""
from fastapi import APIRouter
from app.api.v1 import auth, chat, connections, schema

api_router = APIRouter()

# Include sub-routers
api_router.include_router(auth.router, tags=["auth"])
api_router.include_router(chat.router, tags=["chat"])
api_router.include_router(connections.router, tags=["connections"])
api_router.include_router(schema.router, tags=["schema"])
