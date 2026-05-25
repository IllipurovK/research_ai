import json
import os
from typing import List, Dict, Any, Optional
from llm_client import call_llm
from config import MODES, LLM_RETRIES
from models import Step
from logger import logger


def _load_prompt(filename: str) -> str:
    """Читает промпт из папки research_agent/prompts/."""
    base_dir = os.path.dirname(os.path.abspath(__file__))
    prompt_path = os.path.join(base_dir, "research_agent", "prompts", filename)
    # fallback
    if not os.path.exists(prompt_path):
        prompt_path = os.path.join(base_dir, "prompts", filename)
    with open(prompt_path, "r", encoding="utf-8") as f:
        return f.read()


async def generate_plan(
    topic: str,
    mode: str,
    remaining_time: Optional[float] = None
) -> List[Dict[str, Any]]:
    """
    Генерирует план исследования для заданной темы.
    Возвращает список словарей: [{"description": str, "expected_keywords": List[str]}, ...]
    """
    mode_config = MODES[mode]
    min_steps = mode_config["min_steps"]
    max_steps = mode_config["max_steps"]
    timeout = mode_config["llm_timeout"]

    system_prompt = _load_prompt("planner.txt")
    user_prompt = f"Тема: {topic}. Составь план из {min_steps}-{max_steps} шагов."

    # Две попытки: первая + один повтор при ошибке
    for attempt in range(LLM_RETRIES):  # LLM_RETRIES = 2
        try:
            response = await call_llm(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                timeout=timeout,
                remaining_time=remaining_time
            )
            # Извлечение JSON из ответа (может быть обёрнут в ```json ... ```)
            response = response.strip()
            if response.startswith("```json"):
                response = response[7:]
            if response.startswith("```"):
                response = response[3:]
            if response.endswith("```"):
                response = response[:-3]
            plan = json.loads(response.strip())
            if not isinstance(plan, list):
                raise ValueError("План должен быть списком")
            # Обрезаем до max_steps
            plan = plan[:max_steps]
            # Проверяем, что каждый элемент имеет description
            for item in plan:
                if "description" not in item:
                    raise ValueError("В элементе плана отсутствует поле description")
                if "expected_keywords" not in item:
                    item["expected_keywords"] = []  # опционально
            logger.info(f"Сгенерирован план из {len(plan)} шагов для темы '{topic}'")
            return plan
        except (json.JSONDecodeError, ValueError, KeyError) as e:
            logger.warning(f"Ошибка парсинга плана (попытка {attempt+1}): {e}")
            if attempt == LLM_RETRIES - 1:
                # Возвращаем план по умолчанию из одного шага
                logger.error("Не удалось сгенерировать план, возвращаю fallback")
                return [{"description": f"Найти информацию о {topic}", "expected_keywords": []}]
    # fallback на всякий случай
    return [{"description": f"Поиск информации о {topic}", "expected_keywords": []}]


async def replan(
    remaining_steps: List[Dict[str, Any]],
    last_step: Step,
    all_steps: List[Step],
    mode: str,
    remaining_time: Optional[float] = None
) -> List[Dict[str, Any]]:
    """
    Корректирует оставшиеся шаги на основе выполненного последнего шага и всех предыдущих.
    Возвращает новый список оставшихся шагов (в том же формате).
    При ошибке возвращает исходный remaining_steps.
    """
    mode_config = MODES[mode]
    timeout = mode_config["llm_timeout"]

    system_prompt = _load_prompt("replanner.txt")

    # Формируем контекст
    steps_context = "\n".join(
        f"Шаг {s.step_id}: {s.description} [успех={s.success}]\nРезультат: {s.result_text[:500]}..."
        for s in all_steps
    )
    last_step_info = f"Последний выполненный шаг #{last_step.step_id}: {last_step.description}\nРезультат: {last_step.result_text[:500]}..."
    remaining_steps_json = json.dumps(remaining_steps, ensure_ascii=False, indent=2)

    user_prompt = f"""
Контекст выполненных шагов:
{steps_context}

{last_step_info}

Оставшиеся шаги по плану:
{remaining_steps_json}

На основе результата последнего шага, может быть, нужно скорректировать оставшиеся шаги?
Верни обновлённый список оставшихся шагов в том же JSON-формате: список объектов с полями "description" и опционально "expected_keywords".
Если корректировка не нужна, верни исходный список без изменений.
"""

    try:
        response = await call_llm(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            timeout=timeout,
            remaining_time=remaining_time
        )
        # Очистка от маркеров JSON
        response = response.strip()
        if response.startswith("```json"):
            response = response[7:]
        if response.startswith("```"):
            response = response[3:]
        if response.endswith("```"):
            response = response[:-3]
        new_plan = json.loads(response.strip())
        if not isinstance(new_plan, list):
            raise ValueError("Новый план не является списком")
        # Валидация
        for item in new_plan:
            if "description" not in item:
                raise ValueError("Отсутствует description")
            if "expected_keywords" not in item:
                item["expected_keywords"] = []
        logger.info(f"Replan: количество шагов изменено с {len(remaining_steps)} на {len(new_plan)}")
        return new_plan
    except Exception as e:
        logger.warning(f"Ошибка при replan: {e}, возвращаю исходные оставшиеся шаги")
        return remaining_steps