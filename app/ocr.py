# app/ocr.py

from fastapi import APIRouter, UploadFile, File
from typing import List
import pytesseract
import pandas as pd
import cv2
import numpy as np
import re
from io import BytesIO
from PIL import Image

router = APIRouter()

# Diccionario de categorias para clasificar los productos
CATEGORIAS = {
    "víveres": ["lechuga", "tomate", "leche", "arroz", "huevo", "pan", "sal", "azúcar"],
    "tecnología": ["computador", "portátil", "celular", "cargador", "usb"],
    "textil": ["camiseta", "pantalón", "accesorio", "zapatos", "chaqueta"],
    "bebidas": ["agua", "gaseosa", "jugo", "cerveza", "vino"],
    "otros": []  # catch-all
}

# Función auxiliar para clasificar un producto por nombre
def clasificar_producto(nombre):
    nombre = nombre.lower()
    for categoria, palabras in CATEGORIAS.items():
        for palabra in palabras:
            if palabra in nombre:
                return categoria
    return "otros"

# Extraer fecha con expresiones regulares
FECHA_REGEX = r"(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})"

@router.post("/upload-factura")
async def procesar_factura(file: UploadFile = File(...)):
    # Leer imagen
    image_bytes = await file.read()
    image = Image.open(BytesIO(image_bytes))
    image_np = np.array(image)

    # Convertir a escala de grises y aplicar OCR
    gray = cv2.cvtColor(image_np, cv2.COLOR_RGB2GRAY)
    texto = pytesseract.image_to_string(gray, lang='spa')

    # Buscar fecha
    fecha_match = re.search(FECHA_REGEX, texto)
    fecha = fecha_match.group(0) if fecha_match else "desconocida"

    # Simular extracción de productos (en proyecto real usarías regexs o NLP)
    lineas = texto.split("\n")
    productos = []
    for linea in lineas:
        partes = linea.split()
        if len(partes) >= 3:
            try:
                nombre = " ".join(partes[:-2])
                cantidad = int(partes[-2])
                precio_unitario = float(partes[-1].replace("$", "").replace(",", ""))
                categoria = clasificar_producto(nombre)
                productos.append({
                    "producto": nombre,
                    "cantidad": cantidad,
                    "precio_unitario": precio_unitario,
                    "precio_total": cantidad * precio_unitario,
                    "categoria": categoria
                })
            except:
                continue

    return {
        "factura": {
            "fecha": fecha,
            "proveedor": "por definir"  # Podrías inferirlo si detectas marcas como "Éxito", etc.
        },
        "items": productos
    }
