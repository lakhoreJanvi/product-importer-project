from fastapi import FastAPI, Request
from .database import engine, Base
from . import models
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse
from .routers import upload, events, products, webhooks
import os

app = FastAPI(title="Product Importer")

models.Base.metadata.create_all(bind=engine)

app.include_router(upload.router)
app.include_router(events.router)
app.include_router(products.router)
app.include_router(webhooks.router)

from fastapi.staticfiles import StaticFiles
app.mount("/", StaticFiles(directory="app/static", html=True), name="static")
templates = Jinja2Templates(directory="templates")

@app.get("/", response_class=HTMLResponse)
def index(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})
