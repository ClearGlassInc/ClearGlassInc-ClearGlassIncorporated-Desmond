import pytest

from clearglassinc_sdk.clients.base import CompletionResult, LLMClient
from clearglassinc_sdk.memory import Message


class _EchoClient(LLMClient):
    """Minimal concrete LLMClient that only implements `complete`, to
    exercise the default `acomplete`/`stream`/`astream` fallbacks."""

    def complete(self, messages, *, system=None, tools=None, model=None, temperature=0.7):
        last = messages[-1].content if messages else ""
        return CompletionResult(content=f"echo:{last}")


def test_default_stream_falls_back_to_single_chunk():
    client = _EchoClient()
    chunks = list(client.stream([Message(role="user", content="hi")]))
    assert len(chunks) == 1
    assert chunks[0].delta == "echo:hi"
    assert chunks[0].done is True


async def test_default_acomplete_falls_back_to_complete():
    client = _EchoClient()
    result = await client.acomplete([Message(role="user", content="async hi")])
    assert result.content == "echo:async hi"


async def test_default_astream_falls_back_to_single_chunk():
    client = _EchoClient()
    chunks = [chunk async for chunk in client.astream([Message(role="user", content="hi")])]
    assert len(chunks) == 1
    assert chunks[0].delta == "echo:hi"


def test_llm_client_cannot_be_instantiated_directly():
    with pytest.raises(TypeError):
        LLMClient()
