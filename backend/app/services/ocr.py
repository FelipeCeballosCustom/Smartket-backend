import pytesseract
import cv2
import numpy as np
from fastapi import UploadFile

async def leer_imagen(file: UploadFile):
    contents = await file.read()
    nparr = np.frombuffer(contents, np.uint8)
    img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    texto = pytesseract.image_to_string(img)
    return texto
