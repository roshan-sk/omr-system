import os
import uuid

import cv2
import numpy as np
from pdf2image import convert_from_bytes, convert_from_path


# ── Constants ──────────────────────────────────────────────────────────────────

RENDER_DPI   = 150
MAX_PDF_PAGES = 500
OUTPUT_EXT   = ".png"
JPEG_QUALITY = 95


# ── Helpers ────────────────────────────────────────────────────────────────────

def is_pdf_support_available() -> bool:
    """Return True if pdf2image is installed and importable."""
    try:
        from pdf2image import convert_from_bytes  # noqa: F401
        return True
    except Exception:
        return False


def _pil_to_bgr(pil_img) -> np.ndarray:
    """Convert a PIL image to an OpenCV BGR ndarray."""
    rgb = np.array(pil_img.convert("RGB"))
    return cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR)



def _save_bgr(bgr: np.ndarray, out_path: str) -> None:
    """Write a BGR image to disk as PNG or JPEG depending on OUTPUT_EXT."""
    if OUTPUT_EXT.lower() == ".png":
        cv2.imwrite(out_path, bgr)
    else:
        ok, buf = cv2.imencode(".jpg", bgr, [cv2.IMWRITE_JPEG_QUALITY, JPEG_QUALITY])
        if not ok:
            raise OSError(f"cv2.imencode failed for '{out_path}'")
        with open(out_path, "wb") as f:
            f.write(buf.tobytes())


def _pages_to_images(pages, output_dir: str, base_name: str) -> list[str]:
    """
    Convert a list of PIL pages to image files on disk.
    Shared by both pdf_bytes_to_images and pdf_path_to_images.
    """
    os.makedirs(output_dir, exist_ok=True)
    image_paths: list[str] = []

    for idx, pil_img in enumerate(pages):
        bgr = _pil_to_bgr(pil_img)
        unique = uuid.uuid4().hex[:8]
        filename = f"{base_name}_page{idx + 1:03d}_{unique}{OUTPUT_EXT}"
        out_path = os.path.join(output_dir, filename)
        _save_bgr(bgr, out_path)
        image_paths.append(out_path)

    return image_paths


def _validate_pages(pages) -> None:
    """Raise ValueError if page count is 0 or exceeds MAX_PDF_PAGES."""
    n = len(pages)
    if n == 0:
        raise ValueError("PDF has no pages.")
    if n > MAX_PDF_PAGES:
        raise ValueError(f"PDF has {n} pages; maximum allowed is {MAX_PDF_PAGES}.")



def pdf_bytes_to_images(
    pdf_bytes: bytes,
    output_dir: str,
    dpi: int = RENDER_DPI,
    base_name: str = "pdf",
) -> list[str]:
    """Convert PDF bytes to image files and return their paths."""
    try:
        pages = convert_from_bytes(pdf_bytes, dpi=dpi, fmt="png", thread_count=2)
    except Exception as exc:
        raise ValueError(f"Cannot open PDF: {exc}") from exc

    _validate_pages(pages)
    return _pages_to_images(pages, output_dir, base_name)


def pdf_path_to_images(
    pdf_path: str,
    output_dir: str,
    dpi: int = RENDER_DPI,
    base_name: str | None = None,
) -> list[str]:
    """Convert a PDF file to image files and return their paths."""
    if not os.path.isfile(pdf_path):
        raise ValueError(f"File not found: {pdf_path}")

    if base_name is None:
        base_name = os.path.splitext(os.path.basename(pdf_path))[0]

    try:
        pages = convert_from_path(pdf_path, dpi=dpi, fmt="png", thread_count=2)
    except Exception as exc:
        raise ValueError(f"Cannot open PDF: {exc}") from exc

    return _pages_to_images(pages, output_dir, base_name)