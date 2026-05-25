import pytest
from unittest.mock import patch, AsyncMock
from research_agent.tools.duckduckgo_tool import search_duckduckgo

@pytest.mark.asyncio
async def test_ddg_returns_string():
    t, u, s, e = await search_duckduckgo("погода")
    assert isinstance(t, str)

@pytest.mark.asyncio
async def test_ddg_non_blocking():
    """Проверка, что вызов не блокирует event loop: запускаем два запроса одновременно"""
    import asyncio
    start = asyncio.get_event_loop().time()
    results = await asyncio.gather(
        search_duckduckgo("погода"),
        search_duckduckgo("новости")
    )
    end = asyncio.get_event_loop().time()
    # Оба запроса выполняются конкурентно, общее время меньше суммы таймаутов
    assert end - start < 30  # каждый таймаут 15 сек, сумма 30, но конкурентно укладываемся в ~15-18
    for t, u, s, e in results:
        assert isinstance(t, str)

@pytest.mark.asyncio
async def test_ddg_retry_on_transient_error():
    """Проверка retry при временной ошибке"""
    with patch('research_agent.tools.duckduckgo_tool._sync_search') as mock_search:
        # Первые два вызова падают, третий успешен
        mock_search.side_effect = [
            Exception("Connection error"),
            Exception("Timeout"),
            # [{"body": "x" * 100, "href": "http://example.com"}]
            [{"body": "это очень длинный текст для проверки успешного поиска" * 10, "href": "http://example.com"}]
        ]
        text, urls, success, error = await search_duckduckgo("test")
        print(f"len(text)={len(text)}, text[:100]={text[:100]}, urls={urls}, error={error}")       # пусть выводит ошибку
        assert success is True
        # assert "text" in text
        assert len(text) >= 50
        assert mock_search.call_count == 3

@pytest.mark.asyncio
async def test_ddg_timeout():
    """Проверка таймаута 15 секунд"""
    with patch('research_agent.tools.duckduckgo_tool._sync_search') as mock_search:
        # Эмулируем долгий синхронный вызов
        import time
        def slow(query):
            time.sleep(20)
            return [{"body": "x" * 100, "href": "http://x.com"}]                    #Ошибка в test_ddg_retry_on_transient_error
        mock_search.side_effect = slow
        text, urls, success, error = await search_duckduckgo("test")
        assert success is False
        assert "Timeout" in error

# pytest research_agent/tests/test_duckduckgo_tool.py -v