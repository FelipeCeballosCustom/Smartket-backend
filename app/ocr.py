
'''
#version 2 mejorada en preciision, reconoce textos como valores para corregir
from fastapi import APIRouter, UploadFile, File
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import List
import pandas as pd
import pytesseract
import cv2
import numpy as np
import re
from io import BytesIO
from PIL import Image
import os
import traceback
import unicodedata
from datetime import datetime
import json

router = APIRouter()

# CONFIGURACIÓN
ARCHIVO_EXCEL = "data/factura_ocr.xlsx"
TEMP_JSON = "data/factura_temp.json"
os.makedirs("data", exist_ok=True)

# CATEGORÍAS Y PROVEEDORES
PROVEEDORES = ["exito", "pricesmart", "carrefour", "jumbo", "olimpica",
               "alkosto", "makro", "la14", "surtimax", "metro", "colsubsidio", "la tienda de guille", "cafam", "pigasus"]

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
        "toallas húmedas", "lavaplatos", "ambientador", "limpiador de pisos", "cepillo de baño", "suavitel"
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
        "ponche", "refresco de cola", "aguapanela", "horchata", "bebida de cebada", "hatsu"
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
        "churrasco", "panceta", "hamburguesa de res", "albóndigas de res", "rabo de res", "lomo"
    ],
    "carnes blancas": [
        "pechuga de pollo", "muslo de pollo", "alitas de pollo", "pierna pernil", "pollo entero",
        "pollo despresado", "pollo sin piel", "pollo apanado", "pechuga en tiras", "chuleta de pollo",
        "hamburguesa de pollo", "albóndigas de pollo", "salchicha de pollo", "nuggets de pollo", "hígado de pollo",
        "molida de pollo", "garras de pollo", "espinazo de pollo", "pollo al vacío", "pollo marinado",
        "pez tilapia", "filete de tilapia", "mojarra roja", "trucha", "salmón fresco",
        "atún fresco", "bagre", "filete de pescado", "pescado apanado", "pescado entero",
        "bacalao", "sardina", "corvina", "camarones", "calamares", "filete",
        "pulpitos", "langostinos", "anillos de calamar", "pescado ahumado", "filete de salmón"
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
    "otros": []
}

FECHA_REGEX = r"(\d{2,4}[/-]\d{1,2}[/-]\d{1,2})"

# FUNCIONES AUXILIARES
def normalizar(texto):
    texto = texto.lower()
    texto = unicodedata.normalize('NFKD', texto).encode('ASCII', 'ignore').decode('utf-8')
    return re.sub(r'[^a-z0-9]', '', texto)

def clasificar_producto(nombre):
    nombre_normalizado = normalizar(nombre)
    for categoria, palabras in CATEGORIAS.items():
        for palabra in palabras:
            if normalizar(palabra) in nombre_normalizado:
                return categoria
    return "otros"

def detectar_proveedor(texto_ocr):
    texto_normalizado = normalizar(texto_ocr)
    for proveedor in PROVEEDORES:
        if proveedor in texto_normalizado:
            return proveedor.capitalize()
    return "por definir"


def normalizar_fecha(fecha_str):
    formatos = ["%d/%m/%Y", "%Y/%m/%d", "%d-%m-%Y", "%Y-%m-%d", "%d/%m/%y", "%d-%m-%y"]
    for formato in formatos:
        try:
            return datetime.strptime(fecha_str, formato).strftime("%d/%m/%Y")
        except:
            continue
    return fecha_str

# MODELO PARA EDICIÓN POSTERIOR
class ProductoEditado(BaseModel):
    producto: str
    cantidad: float
    precio_unitario: str
    precio_total: str
    categoria: str
    fecha: str
    proveedor: str

# ---------- 1. OCR: Procesa la factura y guarda temporalmente ----------
@router.post("/upload-factura")
async def procesar_factura(file: UploadFile = File(...)):
    try:
        image_bytes = await file.read()
        image = Image.open(BytesIO(image_bytes))
        image_np = np.array(image)
        gray = cv2.cvtColor(image_np, cv2.COLOR_RGB2GRAY)
        custom_config = r'--oem 3 --psm 6'
        texto = pytesseract.image_to_string(gray, config=custom_config)

        print("=== TEXTO OCR ===")
        print(texto)

        lineas = texto.split("\n")

        # Buscar en todas las líneas primero
        fecha_match = None
        for linea in lineas[::-1]:  # recorrer desde el final
            fecha_match = re.search(FECHA_REGEX, linea)
            if fecha_match:
                break

        # Resultado final
        if fecha_match:
            fecha_raw = fecha_match.group(0)
            fecha = normalizar_fecha(fecha_raw)
        else:
            fecha = "desconocida"
        proveedor = detectar_proveedor(texto)

        productos = []



        #bucle de productos


        IGNORAR_PALABRAS = ["TOTAL", "SUBTOTAL", "CAMBIO", "Items", "MASTERCARD", "Cuenta", "EXP", "Nro", "RESUMEN", "IVA", "IMPUESTO", "precio", "aut", "sugerencias", "servicio"]

        for linea in texto.split("\n"):
            linea = linea.strip()
            if not linea or any(pal in linea.upper() for pal in IGNORAR_PALABRAS):
                continue

            precios_raw = re.findall(r"\$?\s*[\dOo,.\s]{3,}", linea)
            if not precios_raw:
                continue

            try:
                precio_str = precios_raw[-1]
                precio_limpio = re.sub(r"[^\d.,]", "", precio_str)
                precio_num = float(precio_limpio.replace(".", "").replace(",", "."))

                cantidad_match = re.match(r"^\s*(\d+)", linea)
                cantidad = float(cantidad_match.group(1)) if cantidad_match else 1

                nombre = linea.replace(precio_str, "").strip()
                if cantidad_match:
                    nombre = nombre.replace(cantidad_match.group(1), "").strip()

                precio_unitario = precio_num / cantidad if cantidad != 0 else precio_num
                categoria = clasificar_producto(nombre)

                productos.append({
                    "producto": nombre,
                    "cantidad": cantidad,
                    "precio_unitario": str(int(precio_unitario)),
                    "precio_total": str(int(precio_num)),
                    "categoria": categoria,
                    "fecha": fecha,
                    "proveedor": proveedor
                })

            except Exception as e:
                print(f"❌ Error en línea: {linea} -> {e}")
                continue
        

        # Guardar temporalmente en JSON
        with open(TEMP_JSON, "w", encoding="utf-8") as f:
            json.dump(productos, f, ensure_ascii=False, indent=2)

        return {
            "mensaje": "OCR procesado. Edite los datos antes de guardar.",
            "items": productos
        }

    except Exception as e:
        traceback.print_exc()
        return {"error": "Error procesando la factura"}

# ---------- 2. Consulta los datos temporales para edición ----------
@router.get("/factura/actual")
def obtener_datos_ocr():
    if not os.path.exists(TEMP_JSON):
        return {"mensaje": "No hay datos OCR temporales"}
    with open(TEMP_JSON, "r", encoding="utf-8") as f:
        datos = json.load(f)
    return JSONResponse(content=datos)

# ---------- 3. Guarda la versión editada definitiva ----------
@router.post("/factura/guardar")
def guardar_edicion(items: List[ProductoEditado]):
    df_nuevo = pd.DataFrame([item.dict() for item in items])

    # Si el archivo ya existe, leerlo y concatenar
    if os.path.exists(ARCHIVO_EXCEL):
        try:
            df_existente = pd.read_excel(ARCHIVO_EXCEL)
            df_final = pd.concat([df_existente, df_nuevo], ignore_index=True)
        except Exception as e:
            return {"error": f"No se pudo leer el Excel existente: {e}"}
    else:
        df_final = df_nuevo

    try:
        df_final.to_excel(ARCHIVO_EXCEL, index=False)
    except Exception as e:
        return {"error": f"No se pudo guardar el archivo: {e}"}

    if os.path.exists(TEMP_JSON):
        os.remove(TEMP_JSON)

    return {"mensaje": f"{len(items)} ítems agregados al histórico de facturas"}
'''



'''
#lee factura 10 pricesmart o factura 12 juan valdes


from fastapi import APIRouter, UploadFile, File
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import List
import pandas as pd
import pytesseract
import cv2
import numpy as np
import re
from io import BytesIO
from PIL import Image
import os
import traceback
import unicodedata
from datetime import datetime
import json

router = APIRouter()

ARCHIVO_EXCEL = "data/factura_ocr.xlsx"
TEMP_JSON = "data/factura_temp.json"
os.makedirs("data", exist_ok=True)

PROVEEDORES = ["exito", "pricesmart", "carrefour", "jumbo", "olimpica",
               "alkosto", "makro", "la14", "surtimax", "metro", "colsubsidio"]

CATEGORIAS = {
    "lácteos": ["leche", "yogur", "queso", "mantequilla", "kumis", "crema de leche", "quesito"],
    "aseo": ["jabón", "detergente", "cloro", "suavitel", "papel higiénico"],
    "bebida sin alcohol": ["agua", "jugo", "gaseosa", "hatsu"],
    "carnes blancas": ["pollo", "pechuga", "huevo", "filete de pescado", "pescado"],
    "carnes rojas": ["carne", "cerdo", "res", "lomo"],
    "cereales": ["arroz", "frijol", "lentejas", "fideos"],
    "otros": []
}

FECHA_REGEX = r"(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})"

class ProductoEditado(BaseModel):
    producto: str
    cantidad: float
    precio_unitario: str
    precio_total: str
    categoria: str
    fecha: str
    proveedor: str

def normalizar(texto):
    texto = texto.lower()
    texto = unicodedata.normalize('NFKD', texto).encode('ASCII', 'ignore').decode('utf-8')
    return re.sub(r'[^a-z0-9]', '', texto)

def clasificar_producto(nombre):
    nombre_normalizado = normalizar(nombre)
    for categoria, palabras in CATEGORIAS.items():
        for palabra in palabras:
            if normalizar(palabra) in nombre_normalizado:
                return categoria
    return "otros"

def detectar_proveedor(texto):
    texto_norm = normalizar(texto)
    for prov in PROVEEDORES:
        if prov in texto_norm:
            return prov.capitalize()
    return "por definir"

def normalizar_fecha(fecha_str):
    formatos = ["%d/%m/%Y", "%Y/%m/%d", "%d-%m-%Y", "%Y-%m-%d", "%d/%m/%y", "%d-%m-%y"]
    for fmt in formatos:
        try:
            return datetime.strptime(fecha_str, fmt).strftime("%d/%m/%Y")
        except:
            continue
    return fecha_str

@router.post("/upload-factura")
async def procesar_factura(file: UploadFile = File(...)):
    try:
        image_bytes = await file.read()
        image = Image.open(BytesIO(image_bytes))
        image_np = np.array(image)
        gray = cv2.cvtColor(image_np, cv2.COLOR_RGB2GRAY)
        texto = pytesseract.image_to_string(gray, lang='spa')

        print("=== TEXTO OCR ===")
        print(texto)

        proveedor = detectar_proveedor(texto)
        fecha_matches = re.findall(FECHA_REGEX, texto)
        fecha = normalizar_fecha(fecha_matches[-1]) if fecha_matches else "desconocida"

        productos = []
        for linea in texto.split("\n"):
            linea = linea.strip()
            if not linea or any(palabra in linea.lower() for palabra in ["total", "subtotal", "cambio", "cuenta", "recibo"]):
                continue

                
            ##########Juan valdes prueba 12##########

            partes = linea.split()
            if len(partes) < 4:
                continue
            try:
                cantidad = float(partes[-3].replace(",", "."))
                precio_unitario = float(partes[-2].replace(".", "").replace(",", "."))
                precio_total = float(partes[-1].replace(".", "").replace(",", "."))
                nombre = " ".join(partes[:-3])
                categoria = clasificar_producto(nombre)

                productos.append({
                    "producto": nombre.strip(),
                    "cantidad": cantidad,
                    "precio_unitario": str(int(precio_unitario)),
                    "precio_total": str(int(precio_total)),
                    "categoria": categoria,
                    "fecha": fecha,
                    "proveedor": proveedor
                })
                #############
                

                #### prueba10 pricesmart #####
                 partes = linea.split()
                if len(partes) < 3:
                    continue
                try:
                    cantidad = float(partes[0].replace(",", "."))
                    precio_str = partes[-1]
                    precio_total = float(precio_str.replace(".", "").replace(",", "."))
                    nombre = " ".join(partes[1:-1])
                    precio_unitario = precio_total / cantidad if cantidad != 0 else precio_total

                #########################
               

                ## combinacion prueba 10 y prueba 12
        productos = []

        for linea in texto.split("\n"):
            linea = linea.strip()
            if not linea or any(p in linea.lower() for p in ["total", "subtotal", "cambio", "recibo", "forma", "medio", "resumen", "valor", "base", "impuesto"]):
                continue

            partes = linea.split()

            try:
                # Intento 1: nombre + cantidad + precio_unit + precio_total
                if len(partes) >= 4:
                    cantidad = float(partes[-3].replace(",", "."))
                    precio_unitario = float(partes[-2].replace(".", "").replace(",", "."))
                    precio_total = float(partes[-1].replace(".", "").replace(",", "."))
                    nombre = " ".join(partes[:-3])
                    categoria = clasificar_producto(nombre)
                    productos.append({
                        "producto": nombre.strip(),
                        "cantidad": cantidad,
                        "precio_unitario": str(int(precio_unitario)),
                        "precio_total": str(int(precio_total)),
                        "categoria": categoria,
                        "fecha": fecha,
                        "proveedor": proveedor
                    })
                    continue

                # Intento 2: cantidad + nombre + precio_total
                if len(partes) >= 3:
                    cantidad = float(partes[0].replace(",", "."))
                    precio_total = float(partes[-1].replace(".", "").replace(",", "."))
                    nombre = " ".join(partes[1:-1])
                    precio_unitario = precio_total / cantidad if cantidad != 0 else precio_total
                    categoria = clasificar_producto(nombre)
                    productos.append({
                        "producto": nombre.strip(),
                        "cantidad": cantidad,
                        "precio_unitario": str(int(precio_unitario)),
                        "precio_total": str(int(precio_total)),
                        "categoria": categoria,
                        "fecha": fecha,
                        "proveedor": proveedor
                    })
                    continue

                # Intento 3: cantidad + código + nombre + precio_total
                if len(partes) >= 4:
                    cantidad = float(partes[0].replace(",", "."))
                    precio_total = float(partes[-1].replace(".", "").replace(",", "."))
                    nombre = " ".join(partes[2:-1])  # Ignorar código
                    precio_unitario = precio_total / cantidad if cantidad != 0 else precio_total
                    categoria = clasificar_producto(nombre)
                    productos.append({
                        "producto": nombre.strip(),
                        "cantidad": cantidad,
                        "precio_unitario": str(int(precio_unitario)),
                        "precio_total": str(int(precio_total)),
                        "categoria": categoria,
                        "fecha": fecha,
                        "proveedor": proveedor
                    })

            except Exception as e:
                print(f"❌ Error en línea: {linea} -> {e}")
                continue


        with open(TEMP_JSON, "w", encoding="utf-8") as f:
            json.dump(productos, f, ensure_ascii=False, indent=2)

        return {"mensaje": "OCR procesado. Edite los datos antes de guardar.", "items": productos}

    except Exception as e:
        traceback.print_exc()
        return {"error": "Error procesando la factura"}

@router.get("/factura/actual")
def obtener_datos_ocr():
    if not os.path.exists(TEMP_JSON):
        return {"mensaje": "No hay datos OCR temporales"}
    with open(TEMP_JSON, "r", encoding="utf-8") as f:
        datos = json.load(f)
    return JSONResponse(content=datos)

@router.post("/factura/guardar")
def guardar_edicion(items: List[ProductoEditado]):
    df_nuevo = pd.DataFrame([item.dict() for item in items])
    if os.path.exists(ARCHIVO_EXCEL):
        try:
            df_existente = pd.read_excel(ARCHIVO_EXCEL)
            df_final = pd.concat([df_existente, df_nuevo], ignore_index=True)
        except Exception as e:
            return {"error": f"No se pudo leer el Excel existente: {e}"}
    else:
        df_final = df_nuevo

    try:
        df_final.to_excel(ARCHIVO_EXCEL, index=False)
    except Exception as e:
        return {"error": f"No se pudo guardar el archivo: {e}"}

    if os.path.exists(TEMP_JSON):
        os.remove(TEMP_JSON)

    return {"mensaje": f"{len(items)} ítems agregados al histórico de facturas"}

    '''
                
# app/ocr.py

from fastapi import APIRouter, UploadFile, File
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import List
import pandas as pd
import pytesseract
import cv2
import numpy as np
import re
from io import BytesIO
from PIL import Image
import os
import traceback
import unicodedata
from datetime import datetime
import json

router = APIRouter()

ARCHIVO_EXCEL = "data/factura_ocr.xlsx"
TEMP_JSON = "data/factura_temp.json"
os.makedirs("data", exist_ok=True)

PROVEEDORES = ["exito", "pricesmart", "carrefour", "jumbo", "olimpica",
               "alkosto", "makro", "la14", "surtimax", "metro", "colsubsidio"]

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
        "toallas húmedas", "lavaplatos", "ambientador", "limpiador de pisos", "cepillo de baño", "suavitel"
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
        "ponche", "refresco de cola", "aguapanela", "horchata", "bebida de cebada", "hatsu"
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
        "churrasco", "panceta", "hamburguesa de res", "albóndigas de res", "rabo de res", "lomo"
    ],
    "carnes blancas": [
        "pechuga de pollo", "muslo de pollo", "alitas de pollo", "pierna pernil", "pollo entero",
        "pollo despresado", "pollo sin piel", "pollo apanado", "pechuga en tiras", "chuleta de pollo",
        "hamburguesa de pollo", "albóndigas de pollo", "salchicha de pollo", "nuggets de pollo", "hígado de pollo",
        "molida de pollo", "garras de pollo", "espinazo de pollo", "pollo al vacío", "pollo marinado",
        "pez tilapia", "filete de tilapia", "mojarra roja", "trucha", "salmón fresco",
        "atún fresco", "bagre", "filete de pescado", "pescado apanado", "pescado entero",
        "bacalao", "sardina", "corvina", "camarones", "calamares", "filete",
        "pulpitos", "langostinos", "anillos de calamar", "pescado ahumado", "filete de salmón"
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
    "otros": []
}


FECHA_REGEX = r"(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})"

class ProductoEditado(BaseModel):
    producto: str
    cantidad: float
    precio_unitario: str
    precio_total: str
    categoria: str
    fecha: str
    proveedor: str

def normalizar(texto):
    texto = texto.lower()
    texto = unicodedata.normalize('NFKD', texto).encode('ASCII', 'ignore').decode('utf-8')
    return re.sub(r'[^a-z0-9]', '', texto)

def clasificar_producto(nombre):
    nombre_normalizado = normalizar(nombre)
    for categoria, palabras in CATEGORIAS.items():
        for palabra in palabras:
            if normalizar(palabra) in nombre_normalizado:
                return categoria
    return "otros"

def detectar_proveedor(texto):
    texto_norm = normalizar(texto)
    for prov in PROVEEDORES:
        if prov in texto_norm:
            return prov.capitalize()
    return "por definir"

def normalizar_fecha(fecha_str):
    formatos = ["%d/%m/%Y", "%Y/%m/%d", "%d-%m-%Y", "%Y-%m-%d", "%d/%m/%y", "%d-%m-%y"]
    for fmt in formatos:
        try:
            return datetime.strptime(fecha_str, fmt).strftime("%d/%m/%Y")
        except:
            continue
    return fecha_str

@router.post("/upload-factura")
async def procesar_factura(file: UploadFile = File(...)):
    try:
        image_bytes = await file.read()
        image = Image.open(BytesIO(image_bytes))
        image_np = np.array(image)
        gray = cv2.cvtColor(image_np, cv2.COLOR_RGB2GRAY)
        texto = pytesseract.image_to_string(gray, lang='spa')

        print("=== TEXTO OCR ===")
        print(texto)

        proveedor = detectar_proveedor(texto)
        fecha_matches = re.findall(FECHA_REGEX, texto)
        fecha = normalizar_fecha(fecha_matches[-1]) if fecha_matches else "desconocida"

        productos = []
        for linea in texto.split("\n"):
            linea = linea.strip()
            if not linea or any(p in linea.lower() for p in ["total", "subtotal", "cambio", "cuenta", "recibo", "forma", "medio", "resumen", "valor", "base", "impuesto"]):
                continue

            partes = linea.split()
            try:
                # Caso 1: Formato tipo "1 354969 Hatsu 43,900"
                if len(partes) >= 4 and partes[0].isdigit() and partes[1].isdigit():
                    cantidad = float(partes[0])
                    precio_raw = partes[-1]
                    precio_total = float(precio_raw.replace(".", "").replace(",", "."))
                    nombre = " ".join(partes[2:-1])
                    precio_unitario = precio_total / cantidad if cantidad != 0 else precio_total

                # Caso 2: Formato tipo "1 Hatsu 43,900"
                elif len(partes) >= 3 and partes[0].isdigit():
                    cantidad = float(partes[0])
                    precio_raw = partes[-1]
                    precio_total = float(precio_raw.replace(".", "").replace(",", "."))
                    nombre = " ".join(partes[1:-1])
                    precio_unitario = precio_total / cantidad if cantidad != 0 else precio_total

                # Caso 3: Formato tipo "Hatsu 43,900"
                elif len(partes) >= 2 and re.match(r"^[\d,.]+$", partes[-1]):
                    cantidad = 1
                    precio_raw = partes[-1]
                    precio_total = float(precio_raw.replace(".", "").replace(",", "."))
                    nombre = " ".join(partes[:-1])
                    precio_unitario = precio_total

                else:
                    continue

                categoria = clasificar_producto(nombre)

                productos.append({
                    "producto": nombre.strip(),
                    "cantidad": cantidad,
                    "precio_unitario": str(round(precio_unitario)),
                    "precio_total": str(round(precio_total)),
                    "categoria": categoria,
                    "fecha": fecha,
                    "proveedor": proveedor
                })

            except Exception as e:
                print(f"❌ Error en línea: {linea} -> {e}")
                continue


        with open(TEMP_JSON, "w", encoding="utf-8") as f:
            json.dump(productos, f, ensure_ascii=False, indent=2)

        return {"mensaje": "OCR procesado. Edite los datos antes de guardar.", "items": productos}

    except Exception as e:
        traceback.print_exc()
        return {"error": "Error procesando la factura"}

@router.get("/factura/actual")
def obtener_datos_ocr():
    if not os.path.exists(TEMP_JSON):
        return {"mensaje": "No hay datos OCR temporales"}
    with open(TEMP_JSON, "r", encoding="utf-8") as f:
        datos = json.load(f)
    return JSONResponse(content=datos)

@router.post("/factura/guardar")
def guardar_edicion(items: List[ProductoEditado]):
    df_nuevo = pd.DataFrame([item.dict() for item in items])
    if os.path.exists(ARCHIVO_EXCEL):
        try:
            df_existente = pd.read_excel(ARCHIVO_EXCEL)
            df_final = pd.concat([df_existente, df_nuevo], ignore_index=True)
        except Exception as e:
            return {"error": f"No se pudo leer el Excel existente: {e}"}
    else:
        df_final = df_nuevo

    try:
        df_final.to_excel(ARCHIVO_EXCEL, index=False)
    except Exception as e:
        return {"error": f"No se pudo guardar el archivo: {e}"}

    if os.path.exists(TEMP_JSON):
        os.remove(TEMP_JSON)

    return {"mensaje": f"{len(items)} ítems agregados al histórico de facturas"}
