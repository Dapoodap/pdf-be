"""
File type validator using magic bytes (file signatures).
This prevents malicious files from being uploaded with a fake extension.
"""
from fastapi import HTTPException

# Magic byte signatures for supported file types
MAGIC_BYTES: dict[str, list[bytes]] = {
    "pdf":  [b"%PDF"],
    "png":  [b"\x89PNG\r\n\x1a\n"],
    "jpeg": [b"\xff\xd8\xff"],
    "docx": [b"PK\x03\x04"],   # ZIP-based (Office Open XML)
    "xlsx": [b"PK\x03\x04"],
    "pptx": [b"PK\x03\x04"],
}


def validate_file_type(content: bytes, expected: str, filename: str) -> None:
    """
    Validates a file's actual type against its expected type using magic bytes.
    Raises HTTP 400 if the content does not match the expected signature.
    """
    signatures = MAGIC_BYTES.get(expected)
    if not signatures:
        return  # No signature registered — skip validation

    for sig in signatures:
        if content[:len(sig)] == sig:
            return  # Signature matched — file is valid

    raise HTTPException(
        status_code=400,
        detail=f"File '{filename}' does not appear to be a valid {expected.upper()} file. "
               f"Please upload a genuine {expected.upper()} file."
    )
