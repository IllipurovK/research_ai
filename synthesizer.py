# synthesizer.py
import re
import llm_client
from typing import List, Optional
from memory import Memory
from config import MODES
from logger import logger
# ------------------------------------------------------------
# Вспомогательные функции для валидации ссылок
# ------------------------------------------------------------

def _extract_urls(text: str) -> List[str]:
    """Извлекает все URL из текста."""
    pattern = r'https?://[^\s<>"\')\]]+'
    return re.findall(pattern, text)

def _extract_step_refs(text: str) -> List[int]:
    """Извлекает номера шагов из ссылок вида [шаг N] или [шаг N]."""
    # Ищем [шаг 12] или [шаг 123] — цифры после пробела
    pattern = r'\[шаг\s+(\d+)\]'
    matches = re.findall(pattern, text, re.IGNORECASE)
    return [int(m) for m in matches]

def _validate_links(report: str, memory: Memory) -> bool:
    """
    Проверяет, что:
      - все URL в отчёте присутствуют в step.urls успешных шагов
      - все ссылки [шаг N] указывают на существующий шаг с success=True
    """
    # Собираем все реальные URL из успешных шагов
    real_urls = set()
    successful_steps = memory.get_successful_steps()
    for step in successful_steps:
        real_urls.update(step.urls)
    
    # 1. Проверка URL
    found_urls = set(_extract_urls(report))
    # Исключаем пустые строки, если вдруг попали
    found_urls = {u for u in found_urls if u}
    invalid_urls = found_urls - real_urls
    if invalid_urls:
        logger.warning(f"Валидация не пройдена: найдены несуществующие URL: {invalid_urls}")
        return False
    
    # 2. Проверка ссылок на шаги
    found_step_ids = set(_extract_step_refs(report))
    real_step_ids = {step.step_id for step in successful_steps}
    invalid_step_refs = found_step_ids - real_step_ids
    if invalid_step_refs:
        logger.warning(f"Валидация не пройдена: ссылки на несуществующие/неудачные шаги: {invalid_step_refs}")
        return False
    
    return True

def _add_partial_note(report: str, partial: bool) -> str:
    """
    Добавляет примечание после заголовка, если partial == True.
    Ожидает, что отчёт начинается с '# Отчёт по теме: ...'
    """
    if not partial:
        return report
    lines = report.splitlines()
    if not lines:
        return report
    # Ищем первую строку, которая является заголовком
    # Заголовок может быть вида '# Отчёт по теме: ...'
    insert_index = 0
    for i, line in enumerate(lines):
        if line.strip().startswith('# '):
            insert_index = i + 1
            break
    note = ""
    # Добавляем пустую строку и примечание
    # Если после заголовка уже есть пустая строка, аккуратно вставляем
    if insert_index < len(lines) and lines[insert_index].strip() == "":
        # Вставляем примечание после пустой строки
        note = f"> **Примечание:** Исследование выполнено не полностью (таймаут / ошибки). Результаты могут быть неполными.\n"
        lines.insert(insert_index, note)
    else:
        # Вставляем примечание и пустую строку после
        note = f"\n> **Примечание:** Исследование выполнено не полностью (таймаут / ошибки). Результаты могут быть неполными.\n"
        lines.insert(insert_index, note)
    return "\n".join(lines)

def _load_prompt(filename: str) -> str:
    """Загружает промпт из папки prompts/ (относительно расположения этого файла)."""
    import os
    base_dir = os.path.dirname(os.path.abspath(__file__))
    prompt_path = os.path.join(base_dir, "research_agent", "prompts", filename)
    if not os.path.exists(prompt_path):
        prompt_path = os.path.join(base_dir, "prompts", filename)
    with open(prompt_path, "r", encoding="utf-8") as f:
        return f.read()

# ------------------------------------------------------------
# Основная функция синтезатора
# ------------------------------------------------------------

async def synthesize_report(
    topic: str,
    memory: Memory,
    partial: bool,
    mode: str,
    remaining_time: Optional[float] = None
) -> str:
    """
    Генерирует итоговый Markdown-отчёт на основе успешных шагов.
    """
    successful_steps = memory.get_successful_steps()
    
    # Если нет успешных шагов – возвращаем шаблон без вызова LLM
    if not successful_steps:
        logger.warning("Нет успешных шагов, возвращаю шаблон-заглушку")
        note_block = ""
        if partial:
            note_block = f"\n> **Примечание:** Исследование выполнено не полностью (таймаут / ошибки). Результаты могут быть неполными.\n"
        report = f"""# Отчёт по теме: {topic}
{note_block}
## Введение
Не удалось получить достаточно информации по запросу.

## Ключевые факты
Нет успешных шагов для формирования отчёта.

## Выводы
Попробуйте изменить тему или повторить запрос позже.

## Источники
(отсутствуют)"""
        return report

    # Загружаем системный промпт
    system_prompt = _load_prompt("synthesizer.txt")
    
    # Формируем user_prompt
    user_prompt_lines = [f"Тема: {topic}\n", "Успешные шаги (только те, где success=True):"]
    for step in successful_steps:
        user_prompt_lines.append(f"\n--- Шаг {step.step_id} ---")
        user_prompt_lines.append(f"Описание: {step.description}")
        user_prompt_lines.append(f"Текст результата: {step.result_text}")
        user_prompt_lines.append(f"URL: {', '.join(step.urls)}")
    user_prompt = "\n".join(user_prompt_lines)
    
    timeout = MODES[mode]["llm_timeout"]
    
    # Первая попытка
    logger.info("Синтезатор: первый вызов LLM")
    try:
        report = await llm_client.call_llm(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            timeout=timeout,
            temperature=0.7,  # стандартная
            remaining_time=remaining_time
        )
    except Exception as e:
        logger.error(f"Ошибка при вызове LLM в синтезаторе: {e}")
        return f"# Отчёт по теме: {topic}\n\nОшибка генерации отчёта: {e}"
    
    # Валидация ссылок
    if _validate_links(report, memory):
        logger.info("Валидация ссылок пройдена успешно")
        return _add_partial_note(report, partial)
    
    # Повторная попытка с temperature=0.0 и добавленным предупреждением
    logger.warning("Валидация не пройдена, повторяем с temperature=0.0")
    system_prompt_retry = system_prompt + "\n\nВНИМАНИЕ: Предыдущая попытка содержала выдуманные ссылки. Используй ТОЛЬКО предоставленные URL и номера шагов."
    try:
        report = await llm_client.call_llm(
            system_prompt=system_prompt_retry,
            user_prompt=user_prompt,
            timeout=timeout,
            temperature=0.0,
            remaining_time=remaining_time
        )
    except Exception as e:
        logger.error(f"Ошибка при повторном вызове LLM: {e}")
        return "Ошибка генерации: LLM сгаллюцинировал ссылки"
    
    # Финальная проверка
    if _validate_links(report, memory):
        logger.info("Валидация после повторной попытки пройдена")
        return _add_partial_note(report, partial)
    else:
        logger.error("Валидация не пройдена после повторной попытки")
        return "Ошибка генерации: LLM сгаллюцинировал ссылки"