"""Vision analyzer — uses AI vision models to read drawings and verify equipment.

Supports two backends:
1. Ollama + LLaVA (FREE, runs locally, no API key needed)
2. Claude Vision via Anthropic API (paid, more accurate, needs API key)

Converts PDF pages to images and asks the vision model to:
- Read equipment nameplates and ratings from drawings
- Verify UL listing marks on cut sheets
- Check clearance dimensions on layout drawings
- Identify equipment on SLD pages
"""
import os
import base64
from io import BytesIO
from typing import Optional
from dataclasses import dataclass


@dataclass
class VisionResult:
    page_number: int
    question: str
    answer: str
    confidence: str  # "high", "medium", "low"
    backend: str  # "ollama" or "claude"


def _page_to_image(file_path: str, page_number: int, dpi: int = 150) -> Optional[bytes]:
    """Convert a single PDF page to a PNG image bytes."""
    try:
        from pdf2image import convert_from_path
        images = convert_from_path(file_path, first_page=page_number, last_page=page_number, dpi=dpi)
        if images:
            buf = BytesIO()
            images[0].save(buf, format="PNG")
            return buf.getvalue()
    except Exception:
        pass
    return None


def _ask_ollama(image_bytes: bytes, prompt: str, model: str = "llava") -> Optional[str]:
    """Send image + prompt to local Ollama instance."""
    try:
        import requests
        b64 = base64.b64encode(image_bytes).decode("utf-8")
        response = requests.post(
            "http://localhost:11434/api/generate",
            json={
                "model": model,
                "prompt": prompt,
                "images": [b64],
                "stream": False,
            },
            timeout=120,
        )
        if response.ok:
            return response.json().get("response", "")
    except Exception:
        pass
    return None


def _ask_claude(image_bytes: bytes, prompt: str, api_key: str) -> Optional[str]:
    """Send image + prompt to Claude Vision API."""
    try:
        import requests
        b64 = base64.b64encode(image_bytes).decode("utf-8")
        response = requests.post(
            "https://api.anthropic.com/v1/messages",
            headers={
                "x-api-key": api_key,
                "anthropic-version": "2023-06-01",
                "content-type": "application/json",
            },
            json={
                "model": "claude-sonnet-4-20250514",
                "max_tokens": 2000,
                "messages": [{
                    "role": "user",
                    "content": [
                        {
                            "type": "image",
                            "source": {
                                "type": "base64",
                                "media_type": "image/png",
                                "data": b64,
                            },
                        },
                        {"type": "text", "text": prompt},
                    ],
                }],
            },
            timeout=60,
        )
        if response.ok:
            data = response.json()
            return data.get("content", [{}])[0].get("text", "")
    except Exception:
        pass
    return None


def _get_backend():
    """Determine which vision backend to use."""
    # Check for Anthropic API key
    api_key = os.environ.get("ANTHROPIC_API_KEY", "")
    if api_key:
        return "claude", api_key

    # Check if Ollama is running locally
    try:
        import requests
        resp = requests.get("http://localhost:11434/api/tags", timeout=3)
        if resp.ok:
            models = [m["name"] for m in resp.json().get("models", [])]
            if any("llava" in m for m in models):
                return "ollama", None
    except Exception:
        pass

    return None, None


def is_vision_available() -> dict:
    """Check if any vision backend is available."""
    backend, key = _get_backend()
    return {
        "available": backend is not None,
        "backend": backend or "none",
        "details": {
            "ollama": "Install Ollama (https://ollama.ai) and run: ollama pull llava",
            "claude": "Set ANTHROPIC_API_KEY environment variable",
        }
    }


def analyze_page(file_path: str, page_number: int, prompt: str) -> Optional[VisionResult]:
    """Analyze a single PDF page with a vision model."""
    backend, api_key = _get_backend()
    if not backend:
        return None

    image_bytes = _page_to_image(file_path, page_number)
    if not image_bytes:
        return None

    if backend == "claude":
        answer = _ask_claude(image_bytes, prompt, api_key)
    else:
        answer = _ask_ollama(image_bytes, prompt)

    if not answer:
        return None

    return VisionResult(
        page_number=page_number,
        question=prompt,
        answer=answer,
        confidence="high" if backend == "claude" else "medium",
        backend=backend,
    )


# ---------------------------------------------------------------------------
#  Pre-built analysis prompts for common submittal review tasks
# ---------------------------------------------------------------------------

SLD_ANALYSIS_PROMPT = """You are an electrical engineer reviewing a single-line diagram (SLD).

List every piece of equipment shown on this drawing. For each item, provide:
1. Equipment designation (e.g., Q1, Q7, CB-1)
2. Equipment type (ACB, MCCB, transformer, bus, ATS, etc.)
3. Manufacturer and model if visible (e.g., ABB E6.2H, Eaton NRX)
4. Ratings: frame size, trip rating, poles, interrupting capacity (kAIC)
5. What it feeds (downstream equipment name)
6. What feeds it (upstream equipment name)

Format as a structured list. Include EVERY device visible on the drawing."""

UL_LISTING_PROMPT = """You are an electrical engineer reviewing a product data sheet / cut sheet.

Answer these questions about this page:
1. Is UL listed or UL recognized? (Yes/No/Not visible)
2. What is the UL file number if shown?
3. Is there a cUL (Canadian) listing?
4. Are there IEC certifications shown? Which ones?
5. Is there a CE marking?
6. What is the product name and model number?
7. What voltage and frequency is it rated for?

Be specific. If you cannot see something clearly, say so."""

CLEARANCE_PROMPT = """You are an electrical engineer reviewing a layout/GA drawing.

Answer these questions:
1. What are the clearances shown in front of the electrical equipment? (in inches or feet)
2. What are the clearances behind the equipment?
3. What is the overall width and depth of the equipment?
4. Are there any dimensions that appear to violate NEC 110.26 minimum working clearances?
   (For 480V equipment: 36" minimum Condition 1, 42" minimum Condition 2)
5. Are cable entry/exit points shown? Where are they?
6. Are there any shipping splits or modular joints visible?

Provide all dimensions you can read from the drawing."""

NAMEPLATE_PROMPT = """You are reading an equipment nameplate or rating plate.

Extract every piece of information visible:
1. Manufacturer
2. Model/catalog number
3. Serial number
4. Voltage rating
5. Current/ampere rating
6. Frequency
7. Phase configuration
8. Short circuit rating (kAIC)
9. Enclosure type (NEMA/IP)
10. UL file number
11. Any other certifications or ratings

List each item clearly. If something is not legible, note it."""


def analyze_sld_page(file_path: str, page_number: int) -> Optional[VisionResult]:
    """Analyze an SLD page for equipment identification."""
    return analyze_page(file_path, page_number, SLD_ANALYSIS_PROMPT)


def analyze_cutsheet_for_ul(file_path: str, page_number: int) -> Optional[VisionResult]:
    """Analyze a cut sheet page for UL listing status."""
    return analyze_page(file_path, page_number, UL_LISTING_PROMPT)


def analyze_clearances(file_path: str, page_number: int) -> Optional[VisionResult]:
    """Analyze a layout drawing for clearance verification."""
    return analyze_page(file_path, page_number, CLEARANCE_PROMPT)


def analyze_nameplate(file_path: str, page_number: int) -> Optional[VisionResult]:
    """Read a nameplate or rating plate from a drawing page."""
    return analyze_page(file_path, page_number, NAMEPLATE_PROMPT)
