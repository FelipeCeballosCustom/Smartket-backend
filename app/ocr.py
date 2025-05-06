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
    "lácteos": [
        "leche", "yogur", "queso fresco", "queso doble crema", "queso costeño",
        "mantequilla", "crema de leche", "kumis", "leche deslactosada", "leche en polvo",
        "leche condensada", "queso mozzarella", "queso rallado", "leche vegetal",
        "queso paipa", "leche de almendras", "leche de soya", "queso campesino", "yogur griego", "leche saborizada"
    ],
    "aseo": [
        "jabón", "detergente", "suavizante", "cloro", "limpiavidrios",
        "desinfectante", "cepillo", "escoba", "trapeador", "esponja",
        "guantes", "limpiador multiusos", "desengrasante", "bolsas de basura", "papel higiénico",
        "toallas húmedas", "lavaplatos", "ambientador", "limpiador de pisos", "cepillo de baño"
    ],
    "licores": [
        "cerveza", "vino tinto", "vino blanco", "ron", "aguardiente",
        "tequila", "whisky", "vodka", "brandy", "champaña",
        "licor de café", "licor de hierbas", "anís", "cognac", "mezcal",
        "crema irlandesa", "vermouth", "aperitivo", "licor de manzana", "licor de durazno"
    ],
    "cosméticos": [
        "base líquida", "polvo compacto", "rímel", "delineador", "labial",
        "rubor", "crema facial", "desmaquillante", "sombra de ojos", "esmalte",
        "pintalabios", "loción corporal", "protector solar", "crema antiarrugas", "corrector",
        "serum", "gel limpiador", "kit de maquillaje", "bronceador", "acondicionador de pestañas"
    ],
    "bebida sin alcohol": [
        "agua", "jugo", "gaseosa", "té helado", "bebida energética",
        "agua saborizada", "limonada", "malteada", "bebida hidratante", "té verde",
        "café frío", "soda", "infusión de frutas", "bebida de avena", "bebida de coco",
        "ponche", "refresco de cola", "aguapanela", "horchata", "bebida de cebada"
    ],
    "frutas": [
        "manzana", "pera", "banano", "piña", "naranja",
        "mandarina", "uvas", "fresa", "sandía", "melón",
        "papaya", "kiwi", "limón", "mango", "granadilla",
        "guanábana", "ciruela", "maracuyá", "guayaba", "tamarindo"
    ],
    "verduras": [
        "lechuga", "tomate", "zanahoria", "papa", "cebolla",
        "pimentón", "espinaca", "acelga", "brócoli", "coliflor",
        "ají", "repollo", "pepino", "berenjena", "calabacín",
        "yuca", "ajo", "cebollín", "arveja", "habichuela"
    ],
    "carnes rojas": [
        "carne molida de res", "chuleta de cerdo", "lomo de res", "costilla de res", "bistec de res",
        "solomo", "morcilla", "salchichón cervecero", "longaniza", "jamón serrano",
        "jamón ahumado", "tocineta", "pierna de cerdo", "brazo de cerdo", "costilla de cerdo",
        "filete de res", "hígado de res", "riñón de res", "lengua de res", "salchicha de cerdo",
        "chorizo", "cabeza de cerdo", "manos de cerdo", "carne desmechada", "carne para sudar",
        "churrasco", "panceta", "hamburguesa de res", "albóndigas de res", "rabo de res"
    ],
    "carnes blancas": [
        "pechuga de pollo", "muslo de pollo", "alitas de pollo", "pierna pernil", "pollo entero",
        "pollo despresado", "pollo sin piel", "pollo apanado", "pechuga en tiras", "chuleta de pollo",
        "hamburguesa de pollo", "albóndigas de pollo", "salchicha de pollo", "nuggets de pollo", "hígado de pollo",
        "molida de pollo", "garras de pollo", "espinazo de pollo", "pollo al vacío", "pollo marinado",
        "pez tilapia", "filete de tilapia", "mojarra roja", "trucha", "salmón fresco",
        "atún fresco", "bagre", "filete de pescado", "pescado apanado", "pescado entero",
        "bacalao", "sardina", "corvina", "camarones", "calamares",
        "pulpitos", "langostinos", "anillas de calamar", "pescado ahumado", "filete de salmón"
    ],
    "ropa hombre": [
        "camisa", "camiseta", "pantalón", "chaqueta", "bóxer",
        "sudadera", "blazer", "jean", "short", "bermuda",
        "corbata", "chaleco", "gabán", "camiseta polo", "chaqueta deportiva",
        "buzo", "ropa interior", "calcetines", "zapatos formales", "tenis deportivos"
    ],
    "ropa mujer": [
        "blusa", "camiseta", "pantalón", "falda", "vestido",
        "chaqueta", "jean", "ropa interior", "brassier", "panty",
        "leggins", "buzo", "chaleco", "gabán", "camiseta ajustada",
        "ropa deportiva", "chaqueta de jean", "medias", "body", "top"
    ],
    "ropa infantil": [
        "camiseta niño", "camiseta niña", "pantalón niño", "pantalón niña", "vestido niña",
        "short niño", "short niña", "chaqueta niño", "chaqueta niña", "body bebé",
        "enterizo", "ropa interior niño", "ropa interior niña", "sudadera infantil", "zapatos niño",
        "zapatos niña", "pijama niño", "pijama niña", "medias niño", "medias niña"
    ],
    "accesorios": [
        "reloj", "pulsera", "collar", "aretes", "cinturón",
        "gafas", "bolso", "mochila", "billetera", "gorra",
        "bufanda", "pañuelo", "broche", "anillo", "llavero",
        "cartera", "diadema", "correa", "paraguas", "monedero"
    ],
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
