"""Stage 1: Language Detection"""
import langdetect
from langdetect import detect_langs
import structlog

from app.models.domain import Language

logger = structlog.get_logger()

# Language code to name mapping
LANGUAGE_NAMES = {
    "en": "English",
    "es": "Spanish",
    "fr": "French",
    "de": "German",
    "it": "Italian",
    "pt": "Portuguese",
    "ru": "Russian",
    "ja": "Japanese",
    "ko": "Korean",
    "zh-cn": "Chinese (Simplified)",
    "zh-tw": "Chinese (Traditional)",
    "ar": "Arabic",
    "hi": "Hindi",
    "nl": "Dutch",
    "sv": "Swedish",
    "no": "Norwegian",
    "da": "Danish",
    "fi": "Finnish",
    "pl": "Polish",
    "tr": "Turkish",
}


def detect_language(text: str) -> Language:
    """
    Detect the language of input text.
    
    Args:
        text: Input text to analyze
        
    Returns:
        Language object with code, name, and confidence
    """
    try:
        # Use langdetect to detect language
        results = detect_langs(text)
        
        if results:
            primary = results[0]
            code = primary.lang
            confidence = primary.prob
            
            # Get language name
            name = LANGUAGE_NAMES.get(code, code.upper())
            
            logger.debug(
                "Language detected",
                code=code,
                name=name,
                confidence=confidence
            )
            
            return Language(
                code=code,
                name=name,
                confidence=confidence
            )
        else:
            # Default to English if detection fails
            logger.warning("Language detection failed, defaulting to English")
            return Language(code="en", name="English", confidence=0.5)
            
    except Exception as e:
        logger.error("Language detection error", error=str(e))
        # Default to English on error
        return Language(code="en", name="English", confidence=0.5)
