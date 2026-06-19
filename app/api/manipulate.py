from fastapi import APIRouter, Depends, UploadFile, File, Form, HTTPException
from sqlalchemy.orm import Session
from typing import List
import json
import uuid

from app.core.security import get_optional_current_user
from app.core.database import get_db
from app.core.limits import check_file_limits
from app.models.schema import User
from app.services import modifier, storage
from app.services.db_helper import log_file_history

router = APIRouter(prefix="/manipulate", tags=["manipulate"])

import os

def process_and_upload(db: Session, user_id: int | None, file_bytes: bytes, service_name: str, original_filename: str):
    base_name, ext = os.path.splitext(original_filename)
    file_id = str(uuid.uuid4())
    filename = f"{base_name}-{service_name}-{file_id}{ext}"
    gcs_path = storage.upload_file_to_gcs(file_bytes, service_name, filename)
    history = log_file_history(db, user_id, service_name, gcs_path, filename, "pdf")
    download_url = storage.generate_presigned_url(gcs_path)
    return {
        "message": "Success", 
        "history_id": history.id, 
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
        if not f.filename.endswith(".pdf"):
            raise HTTPException(status_code=400, detail="All files must be PDFs.")
        contents.append(await f.read())
        
    merged_bytes = modifier.merge_pdfs(contents, rotations_list)
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

    if not file.filename.endswith(".pdf"):
        raise HTTPException(status_code=400, detail="File must be a PDF.")
        
    content = await file.read()
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

    if not file.filename.endswith(".pdf"):
        raise HTTPException(status_code=400, detail="File must be a PDF.")
        
    content = await file.read()
    try:
        page_indices = json.loads(pages)
        if not isinstance(page_indices, list):
            raise ValueError
    except Exception:
        raise HTTPException(status_code=400, detail="Pages must be a valid JSON list of integers.")
        
    try:
        ordered_bytes = modifier.reorder_pdf_pages(content, page_indices)
    except Exception as e:
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

    if not file.filename.endswith(".pdf"):
        raise HTTPException(status_code=400, detail="File must be a PDF.")
        
    content = await file.read()
    try:
        locked_bytes = modifier.lock_pdf(content, password)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
        
    user_id = current_user.id if current_user else None
    return process_and_upload(db, user_id, locked_bytes, "lock", f"locked_{file.filename}")
