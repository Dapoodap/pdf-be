from fastapi import UploadFile, HTTPException
from typing import List
from app.models.schema import User

MAX_FILE_SIZE_BYTES = 100 * 1024 * 1024 # 100 MB
MAX_MERGE_FILES = 3

def check_file_limits(current_user: User | None, files: List[UploadFile], is_merge: bool = False):
    # Premium users have no limits
    if current_user and current_user.membership_status == "premium":
        return
        
    user_type = "Free users" if current_user else "Guests"
        
    if is_merge and len(files) > MAX_MERGE_FILES:
        raise HTTPException(
            status_code=413, 
            detail=f"{user_type} can only merge up to {MAX_MERGE_FILES} files. Please upgrade to Premium for unlimited access."
        )
        
    for file in files:
        if file.size and file.size > MAX_FILE_SIZE_BYTES:
            raise HTTPException(
                status_code=413, 
                detail=f"File '{file.filename}' exceeds the 100MB limit for {user_type.lower()}. Please upgrade to Premium to upload larger files."
            )
