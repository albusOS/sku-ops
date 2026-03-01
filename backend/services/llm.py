"""
LLM client: Google Gemini. Set LLM_API_KEY to enable.
"""
import io
import logging
from typing import Optional

from config import GEMINI_AVAILABLE, GEMINI_MODEL, LLM_API_KEY

logger = logging.getLogger(__name__)


def _get_model(system_instruction: Optional[str] = None):
    """Return configured GenerativeModel, or None if not configured."""
    if not GEMINI_AVAILABLE:
        return None
    try:
        import google.generativeai as genai
        genai.configure(api_key=LLM_API_KEY)
        try:
            if system_instruction:
                return genai.GenerativeModel(GEMINI_MODEL, system_instruction=system_instruction)
            return genai.GenerativeModel(GEMINI_MODEL)
        except TypeError:
            return genai.GenerativeModel(GEMINI_MODEL)
    except ImportError:
        logger.warning("google-generativeai not installed")
        return None


def _extract_text(response) -> str:
    """Extract text from Gemini response. Raises ValueError on blocked/empty."""
    if not response:
        raise ValueError("No response from model")
    text = getattr(response, "text", None)
    if text and str(text).strip():
        return str(text)
    prompt_feedback = getattr(response, "prompt_feedback", None)
    if prompt_feedback and getattr(prompt_feedback, "block_reason", None):
        raise ValueError(f"Content blocked: {prompt_feedback.block_reason}")
    candidates = getattr(response, "candidates", None) or []
    for c in candidates:
        parts = getattr(c, "content", None) and getattr(c.content, "parts", None) or []
        for p in parts:
            if hasattr(p, "text") and p.text:
                return p.text
    raise ValueError("Model returned no extractable text")


def generate_text(prompt: str, system_instruction: Optional[str] = None) -> Optional[str]:
    """Generate text. Returns None if Gemini is not configured."""
    model = _get_model(system_instruction)
    if not model:
        return None
    try:
        response = model.generate_content(prompt)
        return _extract_text(response)
    except Exception as e:
        logger.warning(f"Gemini generate_text failed: {e}")
        return None


def generate_with_image(
    prompt: str,
    image_bytes: bytes,
    system_instruction: Optional[str] = None,
) -> str:
    """Generate from image. Raises ValueError on failure or if not configured."""
    model = _get_model(system_instruction)
    if not model:
        raise ValueError(f"LLM not configured. Set LLM_API_KEY. Get a free key at https://aistudio.google.com/app/apikey")
    import PIL.Image
    img = PIL.Image.open(io.BytesIO(image_bytes))
    try:
        response = model.generate_content([prompt, img])
        return _extract_text(response)
    except Exception as e:
        err = str(e).lower()
        if "quota" in err or "rate" in err or "429" in err:
            raise ValueError("Gemini rate limit hit. Try again in a minute.") from e
        if "invalid" in err and "key" in err:
            raise ValueError("Invalid LLM_API_KEY. Check backend/.env") from e
        raise


def generate_with_pdf(
    prompt: str,
    pdf_path: str,
    system_instruction: Optional[str] = None,
) -> str:
    """Generate from PDF via Gemini native PDF support. Raises ValueError on failure."""
    model = _get_model(system_instruction)
    if not model:
        raise ValueError(f"LLM not configured. Set LLM_API_KEY. Get a free key at https://aistudio.google.com/app/apikey")
    try:
        import google.generativeai as genai
        genai.configure(api_key=LLM_API_KEY)
        pdf_file = genai.upload_file(path=pdf_path, mime_type="application/pdf")
        response = model.generate_content([prompt, pdf_file])
        return _extract_text(response)
    except Exception as e:
        err = str(e).lower()
        if "quota" in err or "rate" in err or "429" in err:
            raise ValueError("Gemini rate limit hit. Try again in a minute.") from e
        raise
