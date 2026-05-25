# пока заглушка, чтобы избежать ошибок импорта

# synthesizer.py
from memory import Memory
from typing import Tuple, Optional 


async def synthesize_report(
    topic: str,
    memory: Memory,
    partial: bool,
    mode: str,
    remaining_time: Optional[float] = None
) -> str:
    """
    Заглушка для синтезатора отчёта.
    Будет реализована позже.
    """
    return f"# Отчёт по теме: {topic}\n\n> **Примечание:** Отчёт временно недоступен. Синтезатор будет реализован позже.\n\n## Введение\n\n## Ключевые факты\n\n## Выводы\n\n## Источники"