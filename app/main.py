from fastapi import FastAPI
from app.ocr import router as ocr_router

app = FastAPI()

app.include_router(ocr_router)

