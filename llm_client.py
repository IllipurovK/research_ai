import asyncio
from openai import AsyncOpenAI
from config import DEEPSEEK_API_KEY, DEEPSEEK_BASE_URL, LLM_RETRIES
from logger import logger

# Глобальный клиент (инициализируется один раз)
_client: AsyncOpenAI = None


def _get_client() -> AsyncOpenAI:
    """Ленивая инициализация клиента AsyncOpenAI."""
    global _client
    if _client is None:
        _client = AsyncOpenAI(
            api_key=DEEPSEEK_API_KEY,
            base_url=DEEPSEEK_BASE_URL,
        )
    return _client


async def call_llm(
    system_prompt: str,
    user_prompt: str,
    timeout: int,
    temperature: float = 0.7,
    remaining_time: float | None = None,
) -> str:
    """
    Вызов DeepSeek API с retry-логикой и учётом оставшегося времени.
    """
    client = _get_client()
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt},
    ]

    for attempt in range(LLM_RETRIES):
        # Проверка оставшегося времени
        if remaining_time is not None and remaining_time < timeout + 1:
            raise TimeoutError(
                f"Оставшееся время ({remaining_time:.1f}с) меньше необходимого таймаута ({timeout}с + 1с)"
            )

        try:
            logger.debug(
                f"LLM вызов (попытка {attempt + 1}/{LLM_RETRIES}), timeout={timeout}с, temp={temperature}"
            )
            response = await asyncio.wait_for(
                client.chat.completions.create(
                    model="deepseek-chat",
                    messages=messages,
                    temperature=temperature,
                ),
                timeout=timeout,
            )
            content = response.choices[0].message.content
            logger.debug(f"LLM ответ получен, длина {len(content)} символов")
            return content
        except asyncio.TimeoutError:
            logger.warning(f"Таймаут LLM (попытка {attempt + 1}/{LLM_RETRIES})")
            if attempt == LLM_RETRIES - 1:
                raise TimeoutError(f"LLM вызов не удался после {LLM_RETRIES} попыток: таймаут")
        except Exception as e:
            logger.warning(f"Ошибка LLM (попытка {attempt + 1}/{LLM_RETRIES}): {e}")
            if attempt == LLM_RETRIES - 1:
                raise RuntimeError(f"LLM вызов не удался после {LLM_RETRIES} попыток: {e}")

        # Задержка перед повторной попыткой
        await asyncio.sleep(1)

    # На всякий случай (никогда не должно сюда попасть)
    raise RuntimeError("LLM вызов завершился без результата")