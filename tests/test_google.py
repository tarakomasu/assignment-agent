import json

import pytest

from assignment_agent.gemini import parse_stream
from assignment_agent.models import AgentError


def stream(result):
    return json.dumps({"event": "init", "tools": ["view_file"]}) + "\n" + json.dumps({"event": "result", "result": result})


def test_successful_stream():
    assert parse_stream(stream({"status": "SUCCESS", "response": '{"valid":true}'})) == {"valid": True}


@pytest.mark.parametrize("result", [
    {"status": "ERROR", "response": '{"valid":true}'},
    {"status": "SUCCESS", "denied_actions": ["view_file"], "response": '{"valid":true}'},
    {"status": "SUCCESS", "response": ""},
    {"status": "SUCCESS", "response": '{"valid":true}', "error": "quota exceeded"},
])
def test_incomplete_stream_is_not_success(result):
    with pytest.raises(AgentError):
        parse_stream(stream(result))


def test_missing_or_multiple_result_rejected():
    with pytest.raises(AgentError):
        parse_stream('{"event":"init"}')
    with pytest.raises(AgentError):
        parse_stream(stream({"status": "SUCCESS", "response": "{}"}) + "\n" + stream({"status": "SUCCESS", "response": "{}"}))
