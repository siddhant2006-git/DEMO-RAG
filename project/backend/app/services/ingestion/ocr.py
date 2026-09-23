from dataclasses import dataclass, field

import cv2
import numpy as np
import pymupdf
import pytesseract
from pytesseract import Output

from app.config import get_settings
from app.services.ingestion.pdf_loader import WordBox

# Tesseract's mean word confidence (0-100) below which a page is flagged
# LOW_CONFIDENCE instead of being trusted silently.
LOW_CONFIDENCE_THRESHOLD = 40.0

# Render at higher DPI than the PDF's native 72 DPI — sharper input, better OCR.
RENDER_ZOOM = 2.0

_settings = get_settings()
if _settings.tesseract_cmd:
    pytesseract.pytesseract.tesseract_cmd = _settings.tesseract_cmd


@dataclass
class OcrResult:
    text: str
    layout: list[WordBox] = field(default_factory=list)
    confidence: float = 0.0
    low_confidence: bool = True


def _render_page(path: str, page_number: int, zoom: float = RENDER_ZOOM) -> np.ndarray:
    with pymupdf.open(path) as doc:
        page = doc[page_number - 1]
        pix = page.get_pixmap(matrix=pymupdf.Matrix(zoom, zoom))
        img = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.height, pix.width, pix.n)
        if pix.n == 4:
            return cv2.cvtColor(img, cv2.COLOR_RGBA2BGR)
        if pix.n == 3:
            return cv2.cvtColor(img, cv2.COLOR_RGB2BGR)
        return cv2.cvtColor(img, cv2.COLOR_GRAY2BGR)


def _deskew(gray: np.ndarray) -> np.ndarray:
    """Rotate the image so text baselines are horizontal, based on the minimum
    bounding rectangle of dark (ink) pixels."""
    ink = np.column_stack(np.where(gray < 250))
    if ink.shape[0] < 20:
        return gray

    angle = cv2.minAreaRect(ink.astype(np.float32))[-1]
    if angle < -45:
        angle = -(90 + angle)
    else:
        angle = -angle

    if abs(angle) < 0.1:
        return gray

    (h, w) = gray.shape[:2]
    center = (w // 2, h // 2)
    matrix = cv2.getRotationMatrix2D(center, angle, 1.0)
    return cv2.warpAffine(gray, matrix, (w, h), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REPLICATE)


def _preprocess(img: np.ndarray) -> np.ndarray:
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    denoised = cv2.fastNlMeansDenoising(gray, h=10)
    deskewed = _deskew(denoised)
    return cv2.adaptiveThreshold(
        deskewed, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 31, 15
    )


def ocr_page(path: str, page_number: int) -> OcrResult:
    """OCR fallback for a page whose embedded text layer was too sparse to trust.

    Word bounding boxes are returned in PDF point space (i.e. divided back down
    by RENDER_ZOOM) so they line up with the boxes pdf_loader produces for
    digital pages — evidence highlighting doesn't need to know which path a
    page took.
    """
    image = _render_page(path, page_number)
    processed = _preprocess(image)

    data = pytesseract.image_to_data(processed, output_type=Output.DICT)

    words: list[WordBox] = []
    confidences: list[float] = []
    texts: list[str] = []

    for i in range(len(data["text"])):
        word = data["text"][i].strip()
        conf = float(data["conf"][i])
        if not word or conf < 0:
            continue

        x, y, w, h = data["left"][i], data["top"][i], data["width"][i], data["height"][i]
        bbox = [
            round(x / RENDER_ZOOM, 2),
            round(y / RENDER_ZOOM, 2),
            round((x + w) / RENDER_ZOOM, 2),
            round((y + h) / RENDER_ZOOM, 2),
        ]
        words.append(WordBox(text=word, bbox=bbox))
        confidences.append(conf)
        texts.append(word)

    mean_confidence = sum(confidences) / len(confidences) if confidences else 0.0

    return OcrResult(
        text=" ".join(texts),
        layout=words,
        confidence=round(mean_confidence, 1),
        low_confidence=mean_confidence < LOW_CONFIDENCE_THRESHOLD,
    )
