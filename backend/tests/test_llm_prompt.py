import json
from types import SimpleNamespace

import pytest


def test_bid_prompt_requires_structured_table_extraction(monkeypatch):
    from app.services import llm

    captured = {}

    class FakeCompletions:
        def create(self, **kwargs):
            captured.update(kwargs)
            content = json.dumps(
                {
                    "project_name": "脱敏项目",
                    "procurement_requirements": [],
                    "risk": [],
                },
                ensure_ascii=False,
            )
            return SimpleNamespace(
                choices=[SimpleNamespace(message=SimpleNamespace(content=content))]
            )

    fake_client = SimpleNamespace(
        chat=SimpleNamespace(completions=FakeCompletions())
    )
    monkeypatch.setattr(llm, "get_deepseek_client", lambda: fake_client)

    result = llm.analyze_bid("【第1页】\n脱敏表格内容")

    prompt = captured["messages"][1]["content"]
    assert result["procurement_requirements"] == []
    assert "必须逐页检查表格、清单和合并单元格" in prompt
    assert '"procurement_requirements"' in prompt
    assert '"item_name"' in prompt
    assert '"quantity"' in prompt
    assert '"page"' in prompt


def test_bid_model_can_be_overridden(monkeypatch):
    from app.services import llm

    captured = {}

    class FakeCompletions:
        def create(self, **kwargs):
            captured.update(kwargs)
            content = json.dumps({"risk": []}, ensure_ascii=False)
            return SimpleNamespace(
                choices=[SimpleNamespace(message=SimpleNamespace(content=content))]
            )

    fake_client = SimpleNamespace(
        chat=SimpleNamespace(completions=FakeCompletions())
    )
    monkeypatch.setattr(llm, "get_deepseek_client", lambda: fake_client)
    monkeypatch.setattr(
        llm,
        "get_deepseek_model",
        lambda _default: "deployment-model",
    )

    llm.analyze_bid("【第1页】\n脱敏内容")

    assert captured["model"] == "deployment-model"


def test_deepseek_client_uses_configured_endpoint_and_timeout(monkeypatch):
    from app.services import llm

    captured = {}

    def fake_openai(**kwargs):
        captured.update(kwargs)
        return object()

    monkeypatch.setattr(llm, "OpenAI", fake_openai)
    monkeypatch.setattr(llm, "get_deepseek_api_key", lambda: "test-placeholder")
    monkeypatch.setattr(
        llm,
        "get_deepseek_base_url",
        lambda: "https://provider.example.test",
    )
    monkeypatch.setattr(llm, "get_deepseek_timeout_seconds", lambda: 12.5)

    llm.get_deepseek_client()

    assert captured == {
        "api_key": "test-placeholder",
        "base_url": "https://provider.example.test",
        "timeout": 12.5,
    }


def test_deepseek_client_still_requires_api_key(monkeypatch):
    from app.services import llm
    from app.services.ai_errors import AIConfigurationError

    monkeypatch.setattr(llm, "get_deepseek_api_key", lambda: "")

    with pytest.raises(AIConfigurationError):
        llm.get_deepseek_client()
