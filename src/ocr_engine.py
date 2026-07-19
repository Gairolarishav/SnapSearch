import easyocr

_reader = None


def load_ocr():
    global _reader
    if _reader is None:
        _reader = easyocr.Reader(['en'], gpu=False)
    return _reader


def extract_text(image_path: str) -> str:
    reader = load_ocr()
    try:
        results = reader.readtext(image_path, detail=0)
        return " ".join(results).strip()
    except Exception:
        return ""
