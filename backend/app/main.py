from fastapi import FastAPI
from app.api.endpoints import factura

app = FastAPI()

app.include_router(factura.router, prefix="/factura", tags=["Factura"])

@app.get("/")
def root():
    return {"message": "Bienvenido a Smarket API"}
