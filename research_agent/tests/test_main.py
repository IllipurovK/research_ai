import pytest
from unittest.mock import patch, AsyncMock, MagicMock
import sys
from pathlib import Path
import tempfile
import os
from main import main


@pytest.mark.asyncio
async def test_main_parser_args():
    """Проверка парсера аргументов через прямой вызов async_main с моком."""
    with patch("sys.argv", ["main.py", "тема", "--mode", "fast", "--output", "out.md"]), \
         patch("main.research_agent", new_callable=AsyncMock) as mock_ra, \
         patch("main.DEEPSEEK_API_KEY", "test_key"), \
         patch("main.Path.write_text") as mock_write, \
         patch("builtins.print"):

        mock_ra.return_value = (MagicMock(), "# Report")

        await main()

        mock_ra.assert_called_once_with("тема", "fast")
        mock_write.assert_called_once()

@pytest.mark.asyncio
async def test_main_no_api_key():
    """Проверка, что при отсутствии API ключа выводится ошибка и выход с кодом 1."""
    with patch("sys.argv", ["main.py", "тема"]), \
         patch("main.DEEPSEEK_API_KEY", ""), \
         patch("builtins.print") as mock_print, \
         patch("sys.exit", side_effect=SystemExit) as mock_exit:
        with pytest.raises(SystemExit):
            await main()

        mock_print.assert_any_call("❌ Ошибка: DEEPSEEK_API_KEY не найден. Проверьте файл .env", file=sys.stderr)
        mock_exit.assert_called_once_with(1)

@pytest.mark.asyncio
async def test_main_creates_reports_dir_default():
    """Проверка, что при отсутствии --output папка reports создаётся."""
    with patch("sys.argv", ["main.py", "тема", "--mode", "fast"]), \
         patch("main.research_agent", new_callable=AsyncMock) as mock_ra, \
         patch("main.DEEPSEEK_API_KEY", "test_key"), \
         patch("main.Path.write_text"), \
         patch("builtins.print"), \
         patch("main.Path.mkdir") as mock_mkdir:

        mock_ra.return_value = (MagicMock(), "# Report")

        await main()

        # Проверяем, что mkdir вызывался для reports (хотя бы один раз с exist_ok=True)
        mock_mkdir.assert_any_call(exist_ok=True)


@pytest.mark.asyncio
async def test_main_handles_timeout():
    """Проверка обработки TimeoutError."""
    with patch("sys.argv", ["main.py", "тема"]), \
         patch("main.research_agent", new_callable=AsyncMock) as mock_ra, \
         patch("main.DEEPSEEK_API_KEY", "test_key"), \
         patch("builtins.print") as mock_print, \
         patch("sys.exit") as mock_exit:

        mock_ra.side_effect = TimeoutError("тест таймаута")

        await main()

        mock_print.assert_any_call("\n❌ Ошибка: тест таймаута", file=sys.stderr)
        mock_exit.assert_called_once_with(1)


@pytest.mark.asyncio
async def test_main_handles_keyboard_interrupt():
    """Проверка обработки KeyboardInterrupt."""
    with patch("sys.argv", ["main.py", "тема"]), \
         patch("main.research_agent", new_callable=AsyncMock) as mock_ra, \
         patch("main.DEEPSEEK_API_KEY", "test_key"), \
         patch("builtins.print") as mock_print, \
         patch("sys.exit") as mock_exit:

        mock_ra.side_effect = KeyboardInterrupt()

        await main()

        mock_print.assert_any_call("\n⚠️ Прервано пользователем", file=sys.stderr)
        mock_exit.assert_called_once_with(130)


@pytest.mark.asyncio
async def test_main_output_file_encoding_utf8():
    """Проверка, что файл сохраняется с кодировкой UTF-8."""
    with tempfile.NamedTemporaryFile(mode="w", delete=False) as tmp:
        tmp_path = tmp.name
    try:
        with patch("sys.argv", ["main.py", "тема", "--output", tmp_path]), \
             patch("main.research_agent", new_callable=AsyncMock) as mock_ra, \
             patch("main.DEEPSEEK_API_KEY", "test_key"), \
             patch("builtins.print"):

            mock_ra.return_value = (MagicMock(), "# Отчёт с русским текстом")

            await main()

            with open(tmp_path, "r", encoding="utf-8") as f:
                content = f.read()
            assert content == "# Отчёт с русским текстом"
    finally:
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)

# pytest research_agent/tests/test_main.py -v
