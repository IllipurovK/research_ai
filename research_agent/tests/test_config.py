import pytest
import config

def test_config_constants():
    """Проверка основных констант конфигурации"""
    assert config.MODES["fast"]["min_steps"] == 2
    assert config.MODES["fast"]["max_steps"] == 3
    assert config.MODES["deep"]["min_steps"] == 5
    assert config.MODES["deep"]["max_steps"] == 7
    assert config.MAX_RESULT_TEXT_LENGTH == 2000
    assert config.WIKI_TIMEOUT == 10
    assert config.WEB_TIMEOUT == 15
    assert config.LLM_RETRIES == 2
    assert config.WEB_RETRIES == 3
    assert config.WIKI_RETRIES == 1
    assert config.MIN_TEXT_LENGTH == 50
    assert isinstance(config.DEEPSEEK_API_KEY, str)  # может быть пустой строкой
    assert config.DEEPSEEK_BASE_URL == "https://api.deepseek.com/v1"
    assert "определение" in config.WIKI_KEYWORDS
    assert "история" in config.WIKI_KEYWORDS