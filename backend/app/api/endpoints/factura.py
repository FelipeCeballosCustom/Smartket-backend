from fastapi import APIRouter, UploadFile, File
from app.services import ocr

router = APIRouter()

@router.post("/leer")
async def leer_factura(file: UploadFile = File(...)):
    texto = await ocr.leer_imagen(file)
    return {"texto": texto}
