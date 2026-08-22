import json

from app.sse import format_sse, make_event


def test_sse_format_is_structured_json() -> None:
    event = make_event("script_delta", "info", "Script token", {"delta": "Hello"})
    formatted = format_sse(event)
    assert formatted["event"] == "script_delta"
    decoded = json.loads(formatted["data"])
    assert decoded["payload"]["delta"] == "Hello"
    assert set(decoded) == {"stage", "level", "message", "payload", "timestamp"}
