"""Unit tests for QAEngine and conversation store."""

import json
from unittest.mock import MagicMock

import pytest

from qa_engine.engine import DEFAULT_FALLBACK, QAEngine
from qa_engine.store import ConversationContext, InMemoryConversationStore


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_text_response(content: str) -> MagicMock:
    """Build a mock OpenAI completion response with a plain text message."""
    msg = MagicMock()
    msg.tool_calls = None
    msg.content = content

    choice = MagicMock()
    choice.message = msg

    response = MagicMock()
    response.choices = [choice]
    return response


def _make_tool_response(tool_name: str, args: dict, call_id: str = "tc_1") -> MagicMock:
    """Build a mock OpenAI completion response that requests a tool call."""
    tool_call = MagicMock()
    tool_call.id = call_id
    tool_call.function.name = tool_name
    tool_call.function.arguments = json.dumps(args)

    msg = MagicMock()
    msg.tool_calls = [tool_call]
    msg.content = None

    choice = MagicMock()
    choice.message = msg

    response = MagicMock()
    response.choices = [choice]
    return response


def _make_engine(store=None) -> tuple[QAEngine, MagicMock]:
    """Create a QAEngine with a mocked OpenAI client."""
    engine = QAEngine(openai_api_key="test-key", store=store)
    mock_client = MagicMock()
    engine._client = mock_client
    return engine, mock_client


# ---------------------------------------------------------------------------
# Store tests
# ---------------------------------------------------------------------------

@pytest.mark.unit
def test_store_creates_fresh_context_on_first_load():
    store = InMemoryConversationStore()
    ctx = store.load("session-1")
    assert ctx.history == []
    assert ctx.pending_escalation is False


@pytest.mark.unit
def test_store_returns_same_object_after_save():
    store = InMemoryConversationStore()
    ctx = store.load("session-1")
    ctx.history.append({"role": "user", "content": "hello"})
    ctx.pending_escalation = True
    store.save("session-1", ctx)

    loaded = store.load("session-1")
    assert loaded.history == [{"role": "user", "content": "hello"}]
    assert loaded.pending_escalation is True


@pytest.mark.unit
def test_store_isolates_sessions():
    store = InMemoryConversationStore()
    ctx_a = store.load("session-a")
    ctx_a.history.append({"role": "user", "content": "from A"})
    store.save("session-a", ctx_a)

    ctx_b = store.load("session-b")
    assert ctx_b.history == []


# ---------------------------------------------------------------------------
# Engine answer tests
# ---------------------------------------------------------------------------

@pytest.mark.unit
def test_answer_returns_text_reply():
    engine, mock_client = _make_engine()
    mock_client.chat.completions.create.return_value = _make_text_response("Hello there!")

    result = engine.answer("Hi", session_id="s1")
    assert result == "Hello there!"


@pytest.mark.unit
def test_answer_appends_to_history():
    store = InMemoryConversationStore()
    engine, mock_client = _make_engine(store=store)
    mock_client.chat.completions.create.return_value = _make_text_response("Hi back!")

    engine.answer("Hello", session_id="s1")

    ctx = store.load("s1")
    assert ctx.history[0] == {"role": "user", "content": "Hello"}
    assert ctx.history[1] == {"role": "assistant", "content": "Hi back!"}


@pytest.mark.unit
def test_history_is_trimmed_to_limit():
    from qa_engine.store import HISTORY_LIMIT

    store = InMemoryConversationStore()
    engine, mock_client = _make_engine(store=store)
    mock_client.chat.completions.create.return_value = _make_text_response("reply")

    # Send more messages than HISTORY_LIMIT
    for i in range(HISTORY_LIMIT + 3):
        engine.answer(f"message {i}", session_id="s1")

    ctx = store.load("s1")
    assert len(ctx.history) <= HISTORY_LIMIT


# ---------------------------------------------------------------------------
# State transition tests
# ---------------------------------------------------------------------------

@pytest.mark.unit
def test_offer_escalation_sets_pending_escalation():
    store = InMemoryConversationStore()
    engine, mock_client = _make_engine(store=store)

    # First call: tool call to offer_escalation; second call: text reply
    mock_client.chat.completions.create.side_effect = [
        _make_tool_response("offer_escalation", {}),
        _make_text_response("I couldn't answer. Would you like me to escalate?"),
    ]

    engine.answer("What is the prize money?", session_id="s1")

    ctx = store.load("s1")
    assert ctx.pending_escalation is True


@pytest.mark.unit
def test_confirm_escalation_clears_pending_escalation():
    store = InMemoryConversationStore()
    ctx = store.load("s1")
    ctx.pending_escalation = True
    store.save("s1", ctx)

    engine, mock_client = _make_engine(store=store)
    mock_client.chat.completions.create.side_effect = [
        _make_tool_response("confirm_escalation", {}),
        _make_text_response("I've escalated your question!"),
    ]

    engine.answer("Yes please", session_id="s1")

    ctx = store.load("s1")
    assert ctx.pending_escalation is False


@pytest.mark.unit
def test_retrieve_docs_clears_pending_escalation():
    store = InMemoryConversationStore()
    ctx = store.load("s1")
    ctx.pending_escalation = True
    store.save("s1", ctx)

    engine, mock_client = _make_engine(store=store)
    mock_client.chat.completions.create.side_effect = [
        _make_tool_response("retrieve_docs", {"query": "schedule"}),
        _make_text_response("The hackathon starts at 9am."),
        _make_text_response("Here is the schedule: 9am kickoff."),
    ]

    engine.answer("What is the schedule?", session_id="s1")

    ctx = store.load("s1")
    assert ctx.pending_escalation is False


# ---------------------------------------------------------------------------
# System prompt tests
# ---------------------------------------------------------------------------

@pytest.mark.unit
def test_system_prompt_includes_pending_escalation_flag():
    ctx = ConversationContext(history=[], pending_escalation=True)
    engine, _ = _make_engine()
    prompt = engine._build_system_prompt(ctx)
    assert "pending_escalation=True" in prompt


@pytest.mark.unit
def test_system_prompt_no_pending_flag_when_false():
    ctx = ConversationContext(history=[], pending_escalation=False)
    engine, _ = _make_engine()
    prompt = engine._build_system_prompt(ctx)
    assert "pending_escalation=True" not in prompt


# ---------------------------------------------------------------------------
# Fallback test
# ---------------------------------------------------------------------------

@pytest.mark.unit
def test_fallback_when_no_content_returned():
    engine, mock_client = _make_engine()
    mock_client.chat.completions.create.return_value = _make_text_response(None)

    result = engine.answer("Something", session_id="s1")
    assert result == DEFAULT_FALLBACK
