from __future__ import annotations

from io import BytesIO

from pypdf import PdfReader

MAX_PDF_PAGES = 500


def extract_pdf_text(pdf_bytes: bytes, max_pages: int = MAX_PDF_PAGES) -> str:
    reader = PdfReader(BytesIO(pdf_bytes))
    if len(reader.pages) > max_pages:
        raise ValueError(f"PDF has {len(reader.pages)} pages; limit is {max_pages}.")
    page_text: list[str] = []
    for index, page in enumerate(reader.pages, start=1):
        text = page.extract_text() or ""
        if text.strip():
            page_text.append(f"--- page {index} ---\n{text.strip()}")
    return "\n".join(page_text)
