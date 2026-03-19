"""
Unit tests for src/agent.py

The ADK and google-generativeai packages are mocked so these tests run
without a live Gemini API key.
"""

import sys
import types
from unittest.mock import MagicMock, patch

import pytest


# ---------------------------------------------------------------------------
# Helpers to create lightweight mock modules
# ---------------------------------------------------------------------------

def _make_adk_mocks():
    """Return (mock_agent_class, mock_runner_class, mock_session_service_class)."""
    mock_agent_cls = MagicMock(name="Agent")
    mock_runner_cls = MagicMock(name="InMemoryRunner")
    mock_session_svc_cls = MagicMock(name="InMemorySessionService")
    return mock_agent_cls, mock_runner_cls, mock_session_svc_cls


def _inject_fake_adk():
    """Inject fake google.adk and google.generativeai into sys.modules."""
    # google namespace
    google_mod = types.ModuleType("google")
    sys.modules.setdefault("google", google_mod)

    # google.generativeai
    genai_mod = types.ModuleType("google.generativeai")
    genai_mod.configure = MagicMock()
    sys.modules["google.generativeai"] = genai_mod

    # google.adk
    adk_mod = types.ModuleType("google.adk")
    sys.modules["google.adk"] = adk_mod

    # google.adk.agents
    mock_agent_cls = MagicMock(name="Agent")
    agents_mod = types.ModuleType("google.adk.agents")
    agents_mod.Agent = mock_agent_cls
    sys.modules["google.adk.agents"] = agents_mod

    # google.adk.runners
    mock_runner_cls = MagicMock(name="InMemoryRunner")
    runners_mod = types.ModuleType("google.adk.runners")
    runners_mod.InMemoryRunner = mock_runner_cls
    sys.modules["google.adk.runners"] = runners_mod

    # google.adk.sessions
    mock_session_svc_cls = MagicMock(name="InMemorySessionService")
    sessions_mod = types.ModuleType("google.adk.sessions")
    sessions_mod.InMemorySessionService = mock_session_svc_cls
    sys.modules["google.adk.sessions"] = sessions_mod

    # google.genai.types
    genai_types_mod = types.ModuleType("google.genai")
    sys.modules["google.genai"] = genai_types_mod
    types_mod = types.ModuleType("google.genai.types")
    types_mod.Content = MagicMock(name="Content")
    types_mod.Part = MagicMock(name="Part")
    sys.modules["google.genai.types"] = types_mod

    return mock_agent_cls, mock_runner_cls, mock_session_svc_cls


# Inject mocks before importing src.agent
_mock_agent_cls, _mock_runner_cls, _mock_session_svc_cls = _inject_fake_adk()

# Now we can safely import
import src.agent as agent_module  # noqa: E402


# ---------------------------------------------------------------------------
# Tests for create_agent
# ---------------------------------------------------------------------------


class TestCreateAgent:
    def setup_method(self):
        # Reset module-level flag so tests are independent
        agent_module._ADK_AVAILABLE = True
        _mock_agent_cls.reset_mock()

    def test_raises_runtime_error_when_adk_unavailable(self, monkeypatch):
        monkeypatch.setattr(agent_module, "_ADK_AVAILABLE", False)
        with pytest.raises(RuntimeError, match="google-adk is not installed"):
            agent_module.create_agent()

    def test_raises_value_error_when_api_key_missing(self, monkeypatch):
        monkeypatch.setattr(agent_module, "_ADK_AVAILABLE", True)
        monkeypatch.setattr(agent_module, "GOOGLE_API_KEY", None)
        with pytest.raises(ValueError, match="GOOGLE_API_KEY"):
            agent_module.create_agent()

    def test_returns_agent_instance(self, monkeypatch):
        monkeypatch.setattr(agent_module, "_ADK_AVAILABLE", True)
        monkeypatch.setattr(agent_module, "GOOGLE_API_KEY", "fake-key")
        monkeypatch.setattr(agent_module, "Agent", _mock_agent_cls)
        agent_obj = agent_module.create_agent()
        assert agent_obj is not None
        _mock_agent_cls.assert_called_once()

    def test_agent_created_with_tools(self, monkeypatch):
        monkeypatch.setattr(agent_module, "_ADK_AVAILABLE", True)
        monkeypatch.setattr(agent_module, "GOOGLE_API_KEY", "fake-key")
        monkeypatch.setattr(agent_module, "Agent", _mock_agent_cls)
        agent_module.create_agent()
        call_kwargs = _mock_agent_cls.call_args.kwargs
        tools = call_kwargs.get("tools", [])
        assert len(tools) == 2  # summarize_text + get_text_statistics


# ---------------------------------------------------------------------------
# Tests for run_agent
# ---------------------------------------------------------------------------


class TestRunAgent:
    def _make_fake_event(self, text: str):
        part = MagicMock()
        part.text = text
        content = MagicMock()
        content.parts = [part]
        event = MagicMock()
        event.is_final_response.return_value = True
        event.content = content
        return event

    def test_returns_response_text(self, monkeypatch):
        monkeypatch.setattr(agent_module, "_ADK_AVAILABLE", True)
        monkeypatch.setattr(agent_module, "GOOGLE_API_KEY", "fake-key")
        monkeypatch.setattr(agent_module, "Agent", _mock_agent_cls)

        fake_session = MagicMock()
        fake_session.id = "sess-1"
        _mock_session_svc_cls.return_value.create_session.return_value = fake_session
        monkeypatch.setattr(agent_module, "InMemorySessionService", _mock_session_svc_cls)
        monkeypatch.setattr(agent_module, "InMemoryRunner", _mock_runner_cls)

        fake_event = self._make_fake_event("Test summary result")
        _mock_runner_cls.return_value.run.return_value = [fake_event]

        result = agent_module.run_agent("Summarize this text.", session_id="sess-1")
        assert result == "Test summary result"

    def test_concatenates_multiple_parts(self, monkeypatch):
        monkeypatch.setattr(agent_module, "_ADK_AVAILABLE", True)
        monkeypatch.setattr(agent_module, "GOOGLE_API_KEY", "fake-key")
        monkeypatch.setattr(agent_module, "Agent", _mock_agent_cls)

        fake_session = MagicMock()
        fake_session.id = "sess-2"
        _mock_session_svc_cls.return_value.create_session.return_value = fake_session
        monkeypatch.setattr(agent_module, "InMemorySessionService", _mock_session_svc_cls)
        monkeypatch.setattr(agent_module, "InMemoryRunner", _mock_runner_cls)

        part_a = MagicMock()
        part_a.text = "Hello "
        part_b = MagicMock()
        part_b.text = "World"
        content = MagicMock()
        content.parts = [part_a, part_b]
        event = MagicMock()
        event.is_final_response.return_value = True
        event.content = content
        _mock_runner_cls.return_value.run.return_value = [event]

        result = agent_module.run_agent("Hi", session_id="sess-2")
        assert result == "Hello World"

    def test_empty_response_when_no_final_event(self, monkeypatch):
        monkeypatch.setattr(agent_module, "_ADK_AVAILABLE", True)
        monkeypatch.setattr(agent_module, "GOOGLE_API_KEY", "fake-key")
        monkeypatch.setattr(agent_module, "Agent", _mock_agent_cls)

        fake_session = MagicMock()
        fake_session.id = "sess-3"
        _mock_session_svc_cls.return_value.create_session.return_value = fake_session
        monkeypatch.setattr(agent_module, "InMemorySessionService", _mock_session_svc_cls)
        monkeypatch.setattr(agent_module, "InMemoryRunner", _mock_runner_cls)

        non_final_event = MagicMock()
        non_final_event.is_final_response.return_value = False
        _mock_runner_cls.return_value.run.return_value = [non_final_event]

        result = agent_module.run_agent("Any message", session_id="sess-3")
        assert result == ""
