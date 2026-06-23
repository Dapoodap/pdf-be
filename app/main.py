from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.core.database import engine
from app.models import schema
from app.api import auth, manipulate, convert, history, services, transaction, pricing
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException

# Create all database tables (for development/demo purposes without Alembic)
schema.Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="PDF Toolkit Service",
    description="A robust FastAPI backend service for PDF manipulation and conversion.",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in settings.ALLOWED_ORIGINS.split(",")],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(manipulate.router)
app.include_router(convert.router)
app.include_router(history.router)
app.include_router(services.router)
app.include_router(transaction.router)
app.include_router(pricing.router)

@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request, exc):
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": exc.detail},
    )

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request, exc):
    return JSONResponse(
        status_code=422,
        content={"error": "Validation error", "details": exc.errors()},
    )

@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    return JSONResponse(
        status_code=500,
        content={"error": "Internal server error", "details": str(exc)},
    )

@app.get("/")
def read_root():
    return {"message": "Welcome to the PDF Toolkit Service"}
