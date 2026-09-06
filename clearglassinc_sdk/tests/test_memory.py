from clearglassinc_sdk.memory import InMemoryLongTermStore, Memory, Message


def test_memory_add_and_history():
    memory = Memory()
    memory.add_user("hello")
    memory.add_assistant("hi there")
    history = memory.history()
    assert [m.role for m in history] == ["user", "assistant"]
    assert history[0].content == "hello"


def test_memory_trims_to_max_messages_keeping_system_prompt():
    memory = Memory(max_messages=3)
    memory.add(Message(role="system", content="system prompt"))
    for i in range(5):
        memory.add_user(f"turn {i}")

    history = memory.history()
    assert history[0].role == "system"
    assert history[0].content == "system prompt"
    # system + last 3 non-system messages retained
    assert len(history) == 4
    assert history[-1].content == "turn 4"


def test_memory_clear():
    memory = Memory()
    memory.add_user("hello")
    memory.clear()
    assert memory.history() == []


def test_long_term_store_search_ranks_by_keyword_overlap():
    store = InMemoryLongTermStore()
    store.add("k1", "the customer prefers dark mode UI")
    store.add("k2", "the customer's shipping address is in Ontario")
    results = store.search("customer shipping address")
    assert results[0] == "the customer's shipping address is in Ontario"


def test_memory_remember_and_recall():
    memory = Memory()
    memory.remember("k1", "clear glass ships e-commerce software")
    results = memory.recall("clear glass software")
    assert results
    assert "clear glass" in results[0]
