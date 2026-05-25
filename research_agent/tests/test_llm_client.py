import pytest
from unittest.mock import patch, AsyncMock
import asyncio
from llm_client import call_llm


@pytest.mark.asyncio
async def test_call_llm_remaining_time_less_than_timeout_plus_one():
    """Если оставшееся время меньше timeout+1, должно подняться TimeoutError."""
    with pytest.raises(TimeoutError) as exc_info:
        await call_llm(
            system_prompt="sys",
            user_prompt="user",
            timeout=10,
            remaining_time=5.0  # 5 < 11 => ошибка
        )
    assert "Оставшееся время" in str(exc_info.value)


@pytest.mark.asyncio
async def test_call_llm_remaining_time_sufficient():
    """Если времени достаточно, вызов происходит (проверяем мок клиента)."""
    with patch("llm_client._get_client") as mock_get_client:
        mock_client = AsyncMock()
        mock_response = AsyncMock()
        mock_response.choices = [AsyncMock()]
        mock_response.choices[0].message.content = "test response"
        mock_client.chat.completions.create.return_value = mock_response
        mock_get_client.return_value = mock_client

        result = await call_llm(
            system_prompt="sys",
            user_prompt="user",
            timeout=10,
            remaining_time=30.0
        )
        assert result == "test response"
        mock_client.chat.completions.create.assert_awaited_once()


@pytest.mark.asyncio
async def test_call_llm_client_initialized():
    """Проверка, что клиент инициализируется (лениво) через _get_client."""
    from llm_client import _get_client
    # При первом вызове создаётся клиент
    client1 = _get_client()
    assert client1 is not None
    # При втором возвращается тот же объект
    client2 = _get_client()
    assert client1 is client2