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

def sign_pdf(file_content: bytes, signature_content: bytes, page_number: int, x: float, y: float, width: float, height: float) -> bytes:
    import fitz  # PyMuPDF

    # Open the PDF document from bytes
    doc = fitz.open(stream=file_content, filetype="pdf")
    
    # Ensure the requested page exists
    if page_number < 0 or page_number >= len(doc):
        raise ValueError(f"Invalid page number. Document has {len(doc)} pages.")
        
    page = doc.load_page(page_number)
    
    # Jika nilainya berupa pecahan (<= 1.0), berarti FE mengirim dalam bentuk persentase
    if width <= 1.0 and height <= 1.0 and x <= 1.0 and y <= 1.0:
        actual_x = x * page.rect.width
        actual_y = y * page.rect.height
        actual_width = width * page.rect.width
        actual_height = height * page.rect.height
    else:
        actual_x = x
        actual_y = y
        actual_width = width
        actual_height = height
    
    # Define the rectangle where the signature will be placed
    rect = fitz.Rect(actual_x, actual_y, actual_x + actual_width, actual_y + actual_height)
    
    # Insert the signature image
    page.insert_image(rect, stream=signature_content)
    
    # Save the modified document to a byte stream
    output = io.BytesIO()
    doc.save(output)
    doc.close()
    
    return output.getvalue()
