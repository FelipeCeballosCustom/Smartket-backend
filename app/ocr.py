from fastapi import APIRouter, UploadFile, File
import pytesseract
import cv2
import numpy as np
import re
from io import BytesIO
from PIL import Image
import traceback

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
import unicodedata
import re

def normalizar(texto):
    texto = texto.lower()
    texto = unicodedata.normalize('NFKD', texto).encode('ASCII', 'ignore').decode('utf-8')
    texto = re.sub(r'[^a-z0-9]', '', texto)  # Elimina todo lo que no sea letra o número
    return texto

def clasificar_producto(nombre):
    nombre_normalizado = normalizar(nombre)
    for categoria, palabras in CATEGORIAS.items():
        for palabra in palabras:
            palabra_normalizada = normalizar(palabra)
            if palabra_normalizada in nombre_normalizado:
                return categoria
    return "otros"

FECHA_REGEX = r"(\d{2,4}[/-]\d{1,2}[/-]\d{1,2})"

@router.post("/upload-factura")
async def procesar_factura(file: UploadFile = File(...)):
    try:
        image_bytes = await file.read()
        image = Image.open(BytesIO(image_bytes))
        image_np = np.array(image)
        gray = cv2.cvtColor(image_np, cv2.COLOR_RGB2GRAY)
        texto = pytesseract.image_to_string(gray)

        print("=== OCR DETECTADO ===\n", texto)

        fecha_match = re.search(FECHA_REGEX, texto)
        fecha = fecha_match.group(0) if fecha_match else "desconocida"

        productos = []
        total = 0

        for linea in texto.split("\n"):
            linea = linea.strip()
            partes = linea.split()
            if len(partes) < 4:
                continue

            try:
                cantidad_str = partes[0]
                nombre = " ".join(partes[2:-1])
                precio_str = partes[-1]

                cantidad = float(cantidad_str.replace(",", "."))
                precio = float(precio_str.replace(".", "").replace(",", "."))
                precio_unitario = precio / cantidad if cantidad != 0 else precio
                categoria = clasificar_producto(nombre)

                productos.append({
                    "producto": nombre.strip(),
                    "cantidad": cantidad,
                    "precio_unitario": round(precio_unitario, 2),
                    "precio_total": round(precio, 2),
                    "categoria": categoria
                })
                total += precio
            except Exception as e:
                print(f"❌ Error analizando línea: {linea} -> {e}")
                continue

        return {
            "factura": {
                "fecha": fecha,
                "total": round(total, 2),
                "proveedor": "por definir"
            },
            "items": productos
        }

    except Exception as e:
        print("❌ ERROR GENERAL:", e)
        traceback.print_exc()
        return {"error": "Error procesando la factura"}
