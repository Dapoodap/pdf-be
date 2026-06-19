import io
from typing import List
from pypdf import PdfReader, PdfWriter

def merge_pdfs(files_content: List[bytes], rotations: List[int] = None) -> bytes:
    writer = PdfWriter()
    for idx, content in enumerate(files_content):
        reader = PdfReader(io.BytesIO(content))
        rotation = rotations[idx] if rotations and idx < len(rotations) else 0
        
        for page in reader.pages:
            if rotation:
                page.rotate(rotation)
            writer.add_page(page)
            
    output = io.BytesIO()
    writer.write(output)
    return output.getvalue()

def rotate_pdf_pages(file_content: bytes, rotation_degrees: int, page_indices: List[int] = None) -> bytes:
    reader = PdfReader(io.BytesIO(file_content))
    writer = PdfWriter()
    
    if rotation_degrees % 90 != 0:
        raise ValueError("Rotation must be a multiple of 90 degrees")

    for i, page in enumerate(reader.pages):
        if page_indices is None or i in page_indices:
            page.rotate(rotation_degrees)
        writer.add_page(page)
        
    output = io.BytesIO()
    writer.write(output)
    return output.getvalue()

def reorder_pdf_pages(file_content: bytes, page_indices: List[int]) -> bytes:
    reader = PdfReader(io.BytesIO(file_content))
    writer = PdfWriter()
    
    total_pages = len(reader.pages)
    for idx in page_indices:
        if 0 <= idx < total_pages:
            writer.add_page(reader.pages[idx])
        else:
            raise ValueError(f"Page index {idx} is out of bounds")
            
    output = io.BytesIO()
    writer.write(output)
    return output.getvalue()

def lock_pdf(file_content: bytes, password: str) -> bytes:
    reader = PdfReader(io.BytesIO(file_content))
    writer = PdfWriter()
    
    for page in reader.pages:
        writer.add_page(page)
        
    writer.encrypt(password)
    
    output = io.BytesIO()
    writer.write(output)
    return output.getvalue()
