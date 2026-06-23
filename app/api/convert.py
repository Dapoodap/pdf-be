import logging
from fastapi import APIRouter, Depends, UploadFile, File, HTTPException
from sqlalchemy.orm import Session
import os
import zipfile
import io
import uuid

from app.core.security import get_optional_current_user
from app.core.database import get_db
from app.core.limits import check_file_limits
from app.core.file_validator import validate_file_type
from app.models.schema import User
from app.services import converter, storage
from app.services.db_helper import log_file_history

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/convert", tags=["convert"])


def process_and_upload(db: Session, user_id: int | None, file_bytes: bytes, service_name: str, original_filename: str, ext_arg: str):
    base_name, ext = os.path.splitext(original_filename)
    file_id = str(uuid.uuid4())
    filename = f"{base_name}-{service_name}-{file_id}{ext}"
    gcs_path = storage.upload_file_to_gcs(file_bytes, service_name, filename)

    history_id = None
    if user_id is not None:
        history = log_file_history(db, user_id, service_name, gcs_path, filename, ext_arg)
        history_id = history.id

    download_url = storage.generate_presigned_url(gcs_path)
    return {
        "message": "Success",
        "history_id": history_id,
        "file_path": gcs_path,
        "file_name": filename,
        "download_url": download_url
    }


@router.post("/pdf-to-images")
async def convert_pdf_to_images(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User | None = Depends(get_optional_current_user)
):
    check_file_limits(current_user, [file])

    content = await file.read()
    validate_file_type(content, expected="pdf", filename=file.filename)

    user_id = current_user.id if current_user else None
    try:
        images_bytes = converter.pdf_to_images(content)

        if len(images_bytes) > 1:
            zip_buffer = io.BytesIO()
            with zipfile.ZipFile(zip_buffer, "a", zipfile.ZIP_DEFLATED, False) as zip_file:
                for i, img_bytes in enumerate(images_bytes):
                    zip_file.writestr(f"page_{i+1}.png", img_bytes)
            return process_and_upload(db, user_id, zip_buffer.getvalue(), "pdf-to-images", f"images_{file.filename.replace('.pdf', '')}.zip", "zip")
        elif len(images_bytes) == 1:
            return process_and_upload(db, user_id, images_bytes[0], "pdf-to-images", f"page_1_{file.filename.replace('.pdf', '.png')}", "png")
        else:
            raise HTTPException(status_code=400, detail="PDF has no pages to convert.")

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"pdf-to-images error for user {user_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="An error occurred while converting the PDF to images.")


@router.post("/pdf-to-docx")
async def convert_pdf_to_docx(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User | None = Depends(get_optional_current_user)
):
    check_file_limits(current_user, [file])

    content = await file.read()
    validate_file_type(content, expected="pdf", filename=file.filename)

    user_id = current_user.id if current_user else None
    try:
        docx_bytes = converter.pdf_to_docx(content)
        base_name = os.path.splitext(file.filename)[0]
        return process_and_upload(db, user_id, docx_bytes, "pdf-to-docx", f"{base_name}.docx", "docx")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"pdf-to-docx error for user {user_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="An error occurred while converting the PDF to Word.")


@router.post("/pdf-to-xlsx")
async def convert_pdf_to_xlsx(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User | None = Depends(get_optional_current_user)
):
    check_file_limits(current_user, [file])

    content = await file.read()
    validate_file_type(content, expected="pdf", filename=file.filename)

    user_id = current_user.id if current_user else None
    try:
        xlsx_bytes = converter.pdf_to_xlsx(content)
        base_name = os.path.splitext(file.filename)[0]
        return process_and_upload(db, user_id, xlsx_bytes, "pdf-to-xlsx", f"{base_name}.xlsx", "xlsx")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"pdf-to-xlsx error for user {user_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="An error occurred while converting the PDF to Excel.")


@router.post("/pdf-to-pptx")
async def convert_pdf_to_pptx(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User | None = Depends(get_optional_current_user)
):
    check_file_limits(current_user, [file])

    content = await file.read()
    validate_file_type(content, expected="pdf", filename=file.filename)

    user_id = current_user.id if current_user else None
    try:
        pptx_bytes = converter.pdf_to_pptx(content)
        base_name = os.path.splitext(file.filename)[0]
        return process_and_upload(db, user_id, pptx_bytes, "pdf-to-pptx", f"{base_name}.pptx", "pptx")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"pdf-to-pptx error for user {user_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="An error occurred while converting the PDF to PowerPoint.")


@router.post("/to-pdf")
async def convert_to_pdf(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User | None = Depends(get_optional_current_user)
):
    check_file_limits(current_user, [file])

    ext = os.path.splitext(file.filename)[1].lower()
    allowed_exts = [".png", ".jpg", ".jpeg", ".docx", ".xlsx", ".pptx"]
    if ext not in allowed_exts:
        raise HTTPException(status_code=400, detail=f"Unsupported file format. Allowed formats: {', '.join(allowed_exts)}")

    content = await file.read()
    # Validate magic bytes based on extension
    ext_to_type = {
        ".png": "png", ".jpg": "jpeg", ".jpeg": "jpeg",
        ".docx": "docx", ".xlsx": "xlsx", ".pptx": "pptx"
    }
    validate_file_type(content, expected=ext_to_type[ext], filename=file.filename)

    user_id = current_user.id if current_user else None
    try:
        pdf_bytes = converter.x_to_pdf(content, ext)
        base_name = os.path.splitext(file.filename)[0]
        return process_and_upload(db, user_id, pdf_bytes, "to-pdf", f"{base_name}.pdf", "pdf")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"to-pdf error for user {user_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="An error occurred while converting the file to PDF.")
