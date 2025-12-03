# app/ocr.py
from PIL import Image
import pytesseract
import os
from typing import Optional

# -------------------------------
# Configurar Tesseract para Windows
# -------------------------------
if os.name == "nt":  # Windows
    tesseract_path = r"C:\Users\DELL\AppData\Local\Programs\Tesseract-OCR\tesseract.exe"
    if not os.path.exists(tesseract_path):
        raise FileNotFoundError(f"Tesseract no encontrado en {tesseract_path}")
    pytesseract.pytesseract.tesseract_cmd = tesseract_path

# -------------------------------
# Función para imagen a texto
# -------------------------------
def image_to_text(image_path: str) -> str:
    """
    Convierte una imagen a texto usando Tesseract OCR.
    """
    img = Image.open(image_path)
    text = pytesseract.image_to_string(img, lang='spa+eng')
    return text

# -------------------------------
# Función para PDF a texto
# -------------------------------
def pdf_to_text(pdf_path: str, tmp_image_path: Optional[str] = None) -> str:
    """
    Convierte un PDF a texto.
    Si el PDF es escaneado, convierte páginas a imágenes y aplica OCR.
    """
    try:
        from pdf2image import convert_from_path
    except ImportError:
        raise RuntimeError(
            "pdf2image requerido para PDF -> imagen. "
            "Instala con `pip install pdf2image` y asegúrate de tener Poppler instalado."
        )

    # Ruta temporal para imágenes de las páginas
    tmp_image_path = tmp_image_path or os.path.join(os.getcwd(), "tmp_invoice_page.png")

    pages = convert_from_path(pdf_path, dpi=300)
    text_pages = []
    for i, page in enumerate(pages):
        page_path = tmp_image_path if len(pages) == 1 else tmp_image_path.replace(".png", f"_{i}.png")
        page.save(page_path, "PNG")
        text_pages.append(image_to_text(page_path))
        os.remove(page_path)  # limpiar temporal
    return "\n".join(text_pages)
