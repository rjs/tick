from unittest.mock import MagicMock, patch

import pytest

from tick.llm import OllamaError, send_command


def _make_tool_call(name, arguments):
    """Build a mock tool call matching ollama's response structure."""
    tc = MagicMock()
    tc.function.name = name
    tc.function.arguments = arguments
    return tc


def _mock_response(tool_calls=None):
    resp = MagicMock()
    resp.message.tool_calls = tool_calls
    return resp


class TestSendCommand:
    @patch("tick.llm.ollama.chat")
    def test_returns_tool_calls(self, mock_chat):
        mock_chat.return_value = _mock_response(
            tool_calls=[
                _make_tool_call("add_locale", {"name": "Brasil", "iana_tz": "America/Sao_Paulo"}),
            ]
        )
        result = send_command("add Brasil")
        assert result == [
            {"name": "add_locale", "arguments": {"name": "Brasil", "iana_tz": "America/Sao_Paulo"}},
        ]

    @patch("tick.llm.ollama.chat")
    def test_multiple_tool_calls(self, mock_chat):
        mock_chat.return_value = _mock_response(
            tool_calls=[
                _make_tool_call("set_time_window", {"date": "2026-02-12"}),
                _make_tool_call("add_locale", {"name": "Brasil", "iana_tz": "America/Sao_Paulo"}),
            ]
        )
        result = send_command("feb 12 in Brasil")
        assert len(result) == 2
        assert result[0]["name"] == "set_time_window"
        assert result[1]["name"] == "add_locale"

    @patch("tick.llm.ollama.chat")
    def test_no_tool_calls(self, mock_chat):
        mock_chat.return_value = _mock_response(tool_calls=None)
        assert send_command("hello") == []

    @patch("tick.llm.ollama.chat")
    def test_ollama_unavailable(self, mock_chat):
        mock_chat.side_effect = ConnectionError("connection refused")
        with pytest.raises(OllamaError):
            send_command("add Brasil")
