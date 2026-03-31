"""Vision analyzer — uses AI vision models to read drawings and verify equipment.

Supports three backends (checked in priority order):
1. Claude Vision via Anthropic API (paid, most accurate, needs ANTHROPIC_API_KEY)
2. Google Gemini Vision API (paid, accurate, needs GEMINI_API_KEY)
3. Ollama + LLaVA (FREE, runs locally, no API key needed)

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
import logging

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


@dataclass
class VisionResult:
    page_number: int
    question: str
    answer: str
    confidence: str  # "high", "medium", "low"
    backend: str  # "claude", "gemini", or "ollama"


def _page_to_image(file_path: str, page_number: int, dpi: int = 150) -> Optional[bytes]:
    """Convert a single PDF page to a PNG image bytes."""
    try:
        from pdf2image import convert_from_path
        images = convert_from_path(file_path, first_page=page_number, last_page=page_number, dpi=dpi)
        if images:
            buf = BytesIO()
            images[0].save(buf, format="PNG")
            logger.info("[vision] Page %d converted to image (%d bytes)", page_number, buf.tell())
            print(f"[vision] Page {page_number} converted to image ({buf.tell()} bytes)")
            return buf.getvalue()
        logger.warning("[vision] Page %d: convert_from_path returned no images", page_number)
        print(f"[vision] Page {page_number}: no images returned")
    except Exception as e:
        logger.error("[vision] Page %d image conversion failed: %s", page_number, e)
        print(f"[vision] Page {page_number} image conversion FAILED: {e}")
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
            answer = data.get("content", [{}])[0].get("text", "")
            print(f"[vision] Claude response ({len(answer)} chars): {answer[:100]}")
            return answer
        else:
            print(f"[vision] Claude API error {response.status_code}: {response.text[:200]}")
    except Exception as e:
        print(f"[vision] Claude API call FAILED: {e}")
    return None


def _ask_gemini(image_bytes: bytes, prompt: str, api_key: str) -> Optional[str]:
    """Send image + prompt to Google Gemini Vision API."""
    try:
        import requests
        b64 = base64.b64encode(image_bytes).decode("utf-8")
        response = requests.post(
            f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={api_key}",
            headers={"content-type": "application/json"},
            json={
                "contents": [{
                    "parts": [
                        {
                            "inline_data": {
                                "mime_type": "image/png",
                                "data": b64,
                            },
                        },
                        {"text": prompt},
                    ],
                }],
                "generationConfig": {
                    "maxOutputTokens": 2000,
                    "temperature": 0.2,
                },
            },
            timeout=60,
        )
        if response.ok:
            data = response.json()
            candidates = data.get("candidates", [])
            if candidates:
                parts = candidates[0].get("content", {}).get("parts", [])
                if parts:
                    answer = parts[0].get("text", "")
                    print(f"[vision] Gemini response ({len(answer)} chars): {answer[:100]}")
                    return answer
        else:
            print(f"[vision] Gemini API error {response.status_code}: {response.text[:200]}")
    except Exception as e:
        print(f"[vision] Gemini API call FAILED: {e}")
    return None


def _get_backend():
    """Determine which vision backend to use. Priority: Claude > Gemini > Ollama."""
    # Check for Anthropic API key
    api_key = os.environ.get("ANTHROPIC_API_KEY", "")
    if api_key:
        return "claude", api_key

    # Check for Gemini API key
    gemini_key = os.environ.get("GEMINI_API_KEY", "")
    if gemini_key:
        return "gemini", gemini_key

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
            "gemini": "Set GEMINI_API_KEY environment variable",
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
    elif backend == "gemini":
        answer = _ask_gemini(image_bytes, prompt, api_key)
    else:
        answer = _ask_ollama(image_bytes, prompt)

    if not answer:
        return None

    confidence = "high" if backend in ("claude", "gemini") else "medium"

    return VisionResult(
        page_number=page_number,
        question=prompt,
        answer=answer,
        confidence=confidence,
        backend=backend,
    )


# ---------------------------------------------------------------------------
#  Pre-built analysis prompts for common submittal review tasks
# ---------------------------------------------------------------------------

SLD_ANALYSIS_PROMPT = """You are a senior electrical engineer performing a detailed review of this single-line diagram (SLD) for a data center. Your job is to FIND PROBLEMS.

First, identify every piece of equipment visible (breakers, transformers, buses, ATS, UPS, generators, PDUs). Note their designations and ratings.

Then check for these specific issues and flag every one you find:
- MISSING RATINGS: Any breaker or device without a visible frame size, trip rating, or interrupting capacity
- COORDINATION CONCERNS: A downstream breaker rated higher than its upstream breaker
- TOPOLOGY ISSUES: Any bus section with no visible tie breaker or isolation means
- SINGLE POINTS OF FAILURE: Any critical path without redundancy
- LABELING ERRORS: Inconsistent or unclear equipment designations
- MISSING GROUND FAULT: 480Y/277V systems >1000A without ground fault protection shown
- ARC FLASH: Breakers ≥1200A without arc energy reduction noted (NEC 240.87)

For EVERY issue found, state: "ISSUE: [description] — [relevant NEC code if applicable]"
If no issues found for a check, skip it. Do NOT say "no issues found" — only report actual problems.
If you cannot read something clearly, report: 'ISSUE: [item] rating is not legible - verify in field'"""

UL_LISTING_PROMPT = """You are a senior electrical engineer checking this equipment data sheet for US code compliance.

Look carefully at this page and answer:
1. Is there a UL listing mark visible? (the circled UL symbol, or "UL Listed" text)
2. Are there ONLY IEC/CE markings with NO UL listing? If so, this is a MAJOR ISSUE — equipment cannot be legally installed in the US without UL listing per NEC 110.2.
3. What is the voltage rating shown? Is it 480V/60Hz (US standard) or 400V/50Hz (IEC standard)?
4. What is the short-circuit current rating (SCCR or kAIC)?

Report issues in this format:
"ISSUE: [description]"

Specifically flag:
- "ISSUE: No UL listing visible — IEC/CE only. Not acceptable for US installation per NEC 110.2, 110.3(B)"
- "ISSUE: Equipment rated 400V/50Hz — verify compatibility with 480V/60Hz US system"
- "ISSUE: SCCR not visible — must be verified against available fault current per NEC 110.9"

If UL listing IS clearly visible, state: "UL Listed confirmed — [UL file number if visible]"."""

CLEARANCE_PROMPT = """You are a senior electrical engineer reviewing this layout/GA drawing for NEC compliance.

Check for these specific issues:
1. WORKING CLEARANCE (NEC 110.26): For 480V equipment, minimum 36" (Condition 1) or 42" (Condition 2) in front. Measure any dimensions shown. Flag if less than required.
2. DEDICATED SPACE (NEC 110.26(F)): Equipment width and depth extending to ceiling — any pipes, ducts, or other equipment directly above the panelboard/switchgear?
3. DOOR SWING: Do equipment doors have room to open 90° minimum? Does a door swing conflict with adjacent equipment?
4. CABLE ENTRY: Are cable entry points (top/bottom) shown? Is there adequate space for cable bending radius?
5. EGRESS: Can a person exit the working space without reaching past the equipment? (NEC 110.26(C) — two exits required for >1200A equipment or >6ft long)

For EVERY issue found, state: "ISSUE: [description with dimension if visible] — [NEC reference]"
If you cannot read dimensions clearly, state: "ISSUE: Clearance dimension not legible — field verification required"."""

NAMEPLATE_PROMPT = """You are a senior electrical engineer reading this equipment nameplate, rating plate, or data sheet page.

Extract every piece of information you can read:
- Manufacturer and model/catalog number
- Voltage rating, current rating, frequency
- Short-circuit rating (kAIC or SCCR)
- UL file number or listing mark
- Enclosure type (NEMA or IP rating)
- Any other certifications (CE, IEC, CSA, etc.)

Then check for issues:
- "ISSUE: No UL listing visible" if no UL mark found
- "ISSUE: Rated [voltage] — verify compatibility" if not standard US voltage (480V, 208V, 120V)
- "ISSUE: kAIC rating of [X] may be insufficient" if interrupting rating appears low (<42kA for main equipment)
- "ISSUE: [field] not legible" for any critical rating you cannot read

Report what you find. Be specific with numbers and ratings."""


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
