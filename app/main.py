from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.core.database import engine
from app.models import schema
from app.api import auth, manipulate, convert, history, services

# Create all database tables (for development/demo purposes without Alembic)
schema.Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="PDF Toolkit Service",
    description="A robust FastAPI backend service for PDF manipulation and conversion.",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Update this in production with specific domains
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(manipulate.router)
app.include_router(convert.router)
app.include_router(history.router)
app.include_router(services.router)

@app.get("/")
def read_root():
    return {"message": "Welcome to the PDF Toolkit Service"}
