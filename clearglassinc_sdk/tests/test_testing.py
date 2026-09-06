from clearglassinc_sdk.memory import Message
from clearglassinc_sdk.testing import FakeLLMClient, text_response, tool_call_response


def test_fake_client_consumes_scripted_responses_in_order():
    client = FakeLLMClient(responses=[text_response("first"), text_response("second")])
    assert client.complete([Message(role="user", content="a")]).content == "first"
    assert client.complete([Message(role="user", content="b")]).content == "second"


def test_fake_client_falls_back_to_default_response():
    client = FakeLLMClient(default_response=text_response("fallback"))
    client.complete([Message(role="user", content="a")])
    result = client.complete([Message(role="user", content="b")])
    assert result.content == "fallback"


def test_fake_client_echoes_last_user_message_with_no_scripting():
    client = FakeLLMClient()
    result = client.complete([Message(role="user", content="ping")])
    assert result.content == "echo: ping"


def test_fake_client_records_calls():
    client = FakeLLMClient(responses=[text_response("ok")])
    messages = [Message(role="user", content="hi")]
    client.complete(messages)
    assert client.calls == [messages]


def test_tool_call_response_builder():
    result = tool_call_response("id1", "my_tool", {"x": 1})
    assert result.has_tool_calls
    assert result.tool_calls[0].name == "my_tool"
    assert result.tool_calls[0].arguments == {"x": 1}
