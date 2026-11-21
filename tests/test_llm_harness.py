import pytest
from unittest.mock import patch, MagicMock
from llm.harness import query_ollama, build_neutral_prompt

@patch("urllib.request.urlopen")
def test_query_ollama_parses_response(mock_urlopen):
    mock_response = MagicMock()
    mock_response.read.return_value = b'{"response": "class ProposedScheduler:\\n    pass"}'
    mock_urlopen.return_value.__enter__.return_value = mock_response
    
    result = query_ollama("qwen2.5-coder:3b", "test prompt")
    assert result == "class ProposedScheduler:\n    pass"

def test_neutral_prompt_contains_baseline():
    prompt = build_neutral_prompt("class Baseline: pass")
    assert "class Baseline: pass" in prompt
    assert "ProposedScheduler" in prompt
