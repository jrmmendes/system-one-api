import os
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.routes.classify import router as classify_router
from app.services.laya_service import LayaService


@asynccontextmanager
async def lifespan(app: FastAPI):
    device = os.getenv("LAYA_DEVICE", "cpu")
    print("Loading Laya model into memory...")
    service = LayaService()
    service.initialize(device=device)
    print("Laya ready for inference.")
    yield


app = FastAPI(title="System One API", version="0.1.0", lifespan=lifespan)
app.include_router(classify_router)
