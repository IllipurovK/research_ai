import pytest
from pydantic import ValidationError
from models import Step

def test_step_minimal_fields():
    """Создание Step только с обязательными полями"""
    step = Step(
        step_id=1,
        description="Test step",
        query="test query",
        normalized_query="test query"
    )
    assert step.step_id == 1
    assert step.description == "Test step"
    assert step.query == "test query"
    assert step.normalized_query == "test query"
    assert step.expected_keywords is None
    assert step.tool is None
    assert step.result_text == ""
    assert step.urls == []
    assert step.success is False
    assert step.error_msg is None
    assert step.retry_count == 0

def test_step_with_optional_fields():
    """Создание Step со всеми полями"""
    step = Step(
        step_id=2,
        description="Test with optional",
        expected_keywords=["wiki", "definition"],
        query="query",
        normalized_query="query",
        tool="wiki",
        result_text="Some result",
        urls=["https://example.com"],
        success=True,
        error_msg=None,
        retry_count=1,
        start_time=123.45,
        end_time=678.90
    )
    assert step.expected_keywords == ["wiki", "definition"]
    assert step.tool == "wiki"
    assert step.result_text == "Some result"
    assert step.success is True
    assert step.retry_count == 1

def test_step_validation_error():
    """Проверка валидации типов Pydantic"""
    with pytest.raises(ValidationError):
        Step(
            step_id="not_an_int",  # должно быть int
            description="Invalid",
            query="test",
            normalized_query="test"
        )