from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .routers import upload, events, products, webhooks
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from .database import engine, Base
from . import models

Base.metadata.create_all(bind=engine)
app = FastAPI(title="Product Importer API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(upload.router)
app.include_router(events.router)
app.include_router(products.router)
app.include_router(webhooks.router)

app.mount("/static", StaticFiles(directory="app/static"), name="static")

@app.get("/", include_in_schema=False)
def root():
    return FileResponse("app/static/index.html")

@app.get("/health")
def health_check():
    return {"status": "healthy"}

