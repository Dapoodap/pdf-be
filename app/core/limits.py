from fastapi import UploadFile, HTTPException
from typing import List
from app.models.schema import User

MAX_FILE_SIZE_BYTES = 100 * 1024 * 1024 # 100 MB
MAX_MERGE_FILES = 3

def check_file_limits(current_user: User | None, files: List[UploadFile], is_merge: bool = False):
    # If API key is present and valid, skip limits
    if current_user:
        return
        
    if is_merge and len(files) > MAX_MERGE_FILES:
        raise HTTPException(
            status_code=400, 
            detail=f"Anonymous users can only merge up to {MAX_MERGE_FILES} files. Please login for unlimited access."
        )
        
    for file in files:
        if file.size and file.size > MAX_FILE_SIZE_BYTES:
            raise HTTPException(
                status_code=400, 
                detail=f"File '{file.filename}' exceeds the 100MB limit for anonymous users. Please login to upload larger files."
            )
