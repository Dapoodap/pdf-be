import logging
from fastapi import APIRouter, Depends, UploadFile, File, Form, HTTPException
from sqlalchemy.orm import Session
from typing import List
import json
import uuid

from app.core.security import get_optional_current_user
from app.core.database import get_db
from app.core.limits import check_file_limits
from app.core.file_validator import validate_file_type
from app.models.schema import User
from app.services import modifier, storage
from app.services.db_helper import log_file_history

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/manipulate", tags=["manipulate"])

import os


def process_and_upload(db: Session, user_id: int | None, file_bytes: bytes, service_name: str, original_filename: str):
    base_name, ext = os.path.splitext(original_filename)
    file_id = str(uuid.uuid4())
    filename = f"{base_name}-{service_name}-{file_id}{ext}"
    gcs_path = storage.upload_file_to_gcs(file_bytes, service_name, filename)

    history_id = None
    if user_id is not None:
        history = log_file_history(db, user_id, service_name, gcs_path, filename, "pdf")
        history_id = history.id

    download_url = storage.generate_presigned_url(gcs_path)
    return {
        "message": "Success",
        "history_id": history_id,
        "file_path": gcs_path,
        "file_name": filename,
        "download_url": download_url
    }


@router.post("/merge")
async def merge_pdfs(
    files: List[UploadFile] = File(...),
    rotations: str = Form(None),
    db: Session = Depends(get_db),
    current_user: User | None = Depends(get_optional_current_user)
):
    check_file_limits(current_user, files, is_merge=True)

    if len(files) < 2:
        raise HTTPException(status_code=400, detail="At least two files are required for merging.")

    rotations_list = None
    if rotations:
        try:
            rotations_list = json.loads(rotations)
            if not isinstance(rotations_list, list):
                raise ValueError
        except Exception:
            raise HTTPException(status_code=400, detail="rotations must be a valid JSON list of integers.")

    contents = []
    for f in files:
        content = await f.read()
        # Validate magic bytes — not just extension
        validate_file_type(content, expected="pdf", filename=f.filename)
        contents.append(content)

    try:
        merged_bytes = modifier.merge_pdfs(contents, rotations_list)
    except Exception as e:
        logger.error(f"merge error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="An error occurred while merging the PDFs.")

    user_id = current_user.id if current_user else None
    return process_and_upload(db, user_id, merged_bytes, "merge", "merged.pdf")


@router.post("/rotate")
async def rotate_pdf(
    file: UploadFile = File(...),
    degrees: int = Form(...),
    pages: str = Form(None),
    db: Session = Depends(get_db),
    current_user: User | None = Depends(get_optional_current_user)
):
    check_file_limits(current_user, [file])

    content = await file.read()
    validate_file_type(content, expected="pdf", filename=file.filename)

    page_indices = None
    if pages:
        try:
            page_indices = json.loads(pages)
            if not isinstance(page_indices, list):
                raise ValueError
        except Exception:
            raise HTTPException(status_code=400, detail="Pages must be a valid JSON list of integers.")

    try:
        rotated_bytes = modifier.rotate_pdf_pages(content, degrees, page_indices)
    except Exception as e:
        logger.error(f"rotate error: {e}", exc_info=True)
        raise HTTPException(status_code=400, detail=str(e))

    user_id = current_user.id if current_user else None
    return process_and_upload(db, user_id, rotated_bytes, "rotate", f"rotated_{file.filename}")


@router.post("/order")
async def order_pdf(
    file: UploadFile = File(...),
    pages: str = Form(...),
    db: Session = Depends(get_db),
    current_user: User | None = Depends(get_optional_current_user)
):
    check_file_limits(current_user, [file])

    content = await file.read()
    validate_file_type(content, expected="pdf", filename=file.filename)

    try:
        page_indices = json.loads(pages)
        if not isinstance(page_indices, list):
            raise ValueError
    except Exception:
        raise HTTPException(status_code=400, detail="Pages must be a valid JSON list of integers.")

    try:
        ordered_bytes = modifier.reorder_pdf_pages(content, page_indices)
    except Exception as e:
        logger.error(f"reorder error: {e}", exc_info=True)
        raise HTTPException(status_code=400, detail=str(e))

    user_id = current_user.id if current_user else None
    return process_and_upload(db, user_id, ordered_bytes, "order", f"ordered_{file.filename}")


@router.post("/lock")
async def lock_pdf(
    file: UploadFile = File(...),
    password: str = Form(...),
    db: Session = Depends(get_db),
    current_user: User | None = Depends(get_optional_current_user)
):
    check_file_limits(current_user, [file])

    content = await file.read()
    validate_file_type(content, expected="pdf", filename=file.filename)

    try:
        locked_bytes = modifier.lock_pdf(content, password)
    except Exception as e:
        logger.error(f"lock error: {e}", exc_info=True)
        raise HTTPException(status_code=400, detail=str(e))

    user_id = current_user.id if current_user else None
    return process_and_upload(db, user_id, locked_bytes, "lock", f"locked_{file.filename}")


@router.post("/sign")
async def sign_pdf(
    file: UploadFile = File(...),
    signature: UploadFile = File(...),
    signature_details: str = Form(...),
    db: Session = Depends(get_db),
    current_user: User | None = Depends(get_optional_current_user)
):
    check_file_limits(current_user, [file])

    content = await file.read()
    validate_file_type(content, expected="pdf", filename=file.filename)
    
    sig_content = await signature.read()
    
    # Check signature file type (allow png and jpeg)
    ext = os.path.splitext(signature.filename)[1].lower()
    if ext == ".png":
        validate_file_type(sig_content, expected="png", filename=signature.filename)
    elif ext in [".jpg", ".jpeg"]:
        validate_file_type(sig_content, expected="jpeg", filename=signature.filename)
    else:
        raise HTTPException(status_code=400, detail="Signature must be a PNG or JPEG image.")

    try:
        details = json.loads(signature_details)
        page = details.get("page")
        x = details.get("x")
        y = details.get("y")
        width = details.get("width")
        height = details.get("height")
        
        if any(v is None for v in [page, x, y, width, height]):
            raise ValueError("Missing required fields in signature_details (page, x, y, width, height).")
            
        page = int(page)
        x = float(x)
        y = float(y)
        width = float(width)
        height = float(height)
    except Exception as e:
        logger.error(f"sign config error: {e}", exc_info=True)
        raise HTTPException(status_code=400, detail="signature_details must be a valid JSON with page, x, y, width, and height.")

    try:
        signed_bytes = modifier.sign_pdf(content, sig_content, page, x, y, width, height)
    except Exception as e:
        logger.error(f"sign error: {e}", exc_info=True)
        raise HTTPException(status_code=400, detail=str(e))

    user_id = current_user.id if current_user else None
    return process_and_upload(db, user_id, signed_bytes, "sign", f"signed_{file.filename}")
