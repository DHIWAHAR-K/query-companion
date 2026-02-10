"""Language detection tests"""
from app.core.agent.stages.language import detect_language


def test_detect_english():
    """Test English language detection"""
    text = "Show me all customers from last month"
    language = detect_language(text)
    assert language.code == "en"


def test_detect_spanish():
    """Test Spanish language detection"""
    text = "Muéstrame todos los clientes del mes pasado"
    language = detect_language(text)
    assert language.code == "es"


def test_detect_french():
    """Test French language detection"""
    text = "Montrez-moi tous les clients du mois dernier"
    language = detect_language(text)
    assert language.code == "fr"


def test_default_on_short_text():
    """Test default English for very short text"""
    text = "SQL"
    language = detect_language(text)
    # Should default to English
    assert language.code in ["en", "unknown"]
