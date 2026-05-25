import os
import tempfile
import pytest
from loguru import logger

def test_logger_creates_file_and_writes():
    """Проверяет, что логгер создаёт файл и увеличивает его размер при записи"""
    with tempfile.NamedTemporaryFile(delete=False) as tmp:
        log_file = tmp.name

    # Запоминаем все существующие sinks, чтобы потом восстановить (но для теста необязательно)
    # Удаляем все текущие sinks
    logger.remove()
    
    # Добавляем sink во временный файл и запоминаем его ID для последующего закрытия
    sink_id = logger.add(log_file, level="DEBUG", format="{message}")
    
    # Записываем сообщение
    test_msg = "Test log message"
    logger.info(test_msg)
    
    # Закрываем sink (освобождаем файл)
    logger.remove(sink_id)
    
    # Проверяем, что файл создан и содержит сообщение
    assert os.path.exists(log_file)
    with open(log_file, "r", encoding="utf-8") as f:
        content = f.read()
    assert test_msg in content
    
    # Удаляем временный файл (теперь он не занят)
    os.unlink(log_file)