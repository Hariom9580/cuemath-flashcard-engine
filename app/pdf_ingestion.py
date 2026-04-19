import re
from io import BytesIO

from pypdf import PdfReader


def extract_text_from_pdf(file_bytes: bytes) -> str:
    reader = PdfReader(BytesIO(file_bytes))
    pages: list[str] = []

    for page in reader.pages:
        page_text = page.extract_text() or ""
        if page_text:
            pages.append(page_text)

    combined = "\n".join(pages)
    normalized = re.sub(r"\s+", " ", combined).strip()
    return normalized
