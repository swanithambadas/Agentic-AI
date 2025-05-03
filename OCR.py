import io
import cv2
import numpy as np
from google.cloud import vision
from google.oauth2 import service_account
import easyocr

# ——— CONFIG ———
KEY_PATH   = r"C:\Users\swani\Desktop\Agentic-AI\ai-agent-vision-a689d5283676.json"
LANGUAGES  = ["en"]
# ————————

# Initialize clients once
_creds   = service_account.Credentials.from_service_account_file(KEY_PATH)
_vclient = vision.ImageAnnotatorClient(credentials=_creds)
_reader  = easyocr.Reader(LANGUAGES, gpu=False)

def _preprocess(path):
    """Grayscale, invert if needed, upscale, despeckle, then threshold."""
    img  = cv2.imread(path, cv2.IMREAD_COLOR)
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

    # Invert if dark background
    if np.mean(gray) < 127:
        gray = cv2.bitwise_not(gray)

    # Upscale for small fonts
    h, w = gray.shape
    gray = cv2.resize(gray, (w*2, h*2), interpolation=cv2.INTER_LINEAR)

    # Contrast & denoise
    gray = cv2.equalizeHist(gray)
    gray = cv2.medianBlur(gray, 3)

    # Morphological opening to remove tiny blobs
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (3,3))
    gray   = cv2.morphologyEx(gray, cv2.MORPH_OPEN, kernel)

    # Adaptive threshold to B/W
    return cv2.adaptiveThreshold(
        gray, 255,
        cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        cv2.THRESH_BINARY,
        blockSize=15, C=5
    )

def ocr_event_image(path: str, fallback=True) -> str:
    """
    1) Preprocess image for clarity
    2) Use Vision DOCUMENT_TEXT_DETECTION + layout reassembly
    3) If output too short, fallback to EasyOCR
    """
    # 1. Preprocess
    proc = _preprocess(path)
    _, buf = cv2.imencode('.jpg', proc)
    img = vision.Image(content=buf.tobytes())

    # 2. Vision OCR with page-layout
    ctx  = vision.ImageContext(language_hints=LANGUAGES)
    resp = _vclient.document_text_detection(image=img, image_context=ctx)
    if resp.error.message:
        raise RuntimeError(resp.error.message)

    # Reassemble blocks in reading order
    blocks = []
    for page in resp.full_text_annotation.pages:
        for block in page.blocks:
            # collect all words in block
            words = []
            for para in block.paragraphs:
                for word in para.words:
                    words.append("".join(sym.text for sym in word.symbols))
            # vertical center for sorting
            vcenter = sum(v.y for v in block.bounding_box.vertices) / 4
            blocks.append((vcenter, " ".join(words)))
    blocks.sort(key=lambda x: x[0])
    text = "\n".join(b for _, b in blocks).strip()

    # 3. EasyOCR fallback if Vision missed most text
    if fallback and (len(text) < 30 or text.count("\n") < 3):
        alt_lines = _reader.readtext(path, detail=0)
        alt = "\n".join(alt_lines).strip()
        if len(alt) > len(text):
            text = alt

    return text

if __name__ == "__main__":
    result = ocr_event_image("event.jpeg")
    print("=== OCR’d text ===\n", result)
