from typing import List
from models import Step

class Memory:
    def __init__(self):
        self.steps: List[Step] = []

    def normalize_query(self, query: str) -> str:
        """Приводит строку запроса к нормализованному виду (нижний регистр, без пробелов по краям)."""
        return query.lower().strip()

    def is_duplicate(self, normalized_query: str) -> bool:
        """Проверяет, есть ли уже шаг с таким нормализованным запросом."""
        return any(step.normalized_query == normalized_query for step in self.steps)

    def add_step(self, step: Step) -> None:
        """Добавляет шаг в память."""
        self.steps.append(step)

    def get_successful_steps(self) -> List[Step]:
        """Возвращает список успешных шагов (success == True)."""
        return [step for step in self.steps if step.success]