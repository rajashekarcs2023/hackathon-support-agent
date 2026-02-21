"""Unit tests for QAEngine and conversation store."""

import json
from unittest.mock import MagicMock

import pytest

from qa_engine.engine import DEFAULT_FALLBACK, QAEngine
from qa_engine.store import InMemoryConversationStore


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
    """
    Story: When we load a conversation for a session that has never been used before,
    the store gives us a brand-new context: no message history and no pending
    escalation. We can start a clean conversation.
    """
    store = InMemoryConversationStore()
    ctx = store.load("session-1")
    assert ctx.history == []
    assert ctx.pending_escalation is False


@pytest.mark.unit
def test_store_returns_same_object_after_save():
    """
    Story: We load a session, add a user message and set pending escalation to True,
    then save. When we load the same session again, we get back exactly what we
    saved: the same history and the same pending-escalation flag. Persistence works.
    """
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
    """
    Story: We add a message to session A and save it. When we load session B,
    its history is empty. Sessions do not share data; each has its own context.
    """
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
    """
    Story: The user asks "Hi" and the model returns a plain text reply "Hello there!".
    The engine returns that text directly to the caller with no tool calls involved.
    """
    engine, mock_client = _make_engine()
    mock_client.chat.completions.create.return_value = _make_text_response("Hello there!")

    result = engine.answer("Hi", session_id="s1")
    assert result == "Hello there!"


@pytest.mark.unit
def test_answer_appends_to_history():
    """
    Story: The user says "Hello" and the engine gets a reply "Hi back!". After the
    answer call, the store for that session contains the user message and the
    assistant reply in order, so conversation history is correctly recorded.
    """
    store = InMemoryConversationStore()
    engine, mock_client = _make_engine(store=store)
    mock_client.chat.completions.create.return_value = _make_text_response("Hi back!")

    engine.answer("Hello", session_id="s1")

    ctx = store.load("s1")
    assert ctx.history[0] == {"role": "user", "content": "Hello"}
    assert ctx.history[1] == {"role": "assistant", "content": "Hi back!"}


@pytest.mark.unit
def test_history_is_trimmed_to_limit():
    """
    Story: We send more messages than HISTORY_LIMIT allows. The store never keeps
    more than HISTORY_LIMIT messages; older ones are dropped so we do not grow
    unbounded and blow context windows.
    """
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
    """
    Story: The user asks something the model cannot answer (e.g. prize money), so
    the model calls the offer_escalation tool. After handling that, the session's
    pending_escalation flag is set to True so the next turn knows we are waiting
    for the user to confirm or decline escalation.
    """
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
    """
    Story: The session already has pending_escalation True (we offered escalation).
    The user says "Yes please" and the model calls confirm_escalation. After that,
    pending_escalation is cleared to False so we are no longer waiting for a
    confirmation.
    """
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
    """
    Story: The session had pending escalation, but the user asks a new question
    (e.g. "What is the schedule?") and the model decides to retrieve docs instead.
    After running retrieve_docs and answering, pending_escalation is cleared so
    we do not keep showing escalation UI when the user has moved on.
    """
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
# Fallback test
# ---------------------------------------------------------------------------

@pytest.mark.unit
def test_fallback_when_no_content_returned():
    """
    Story: The model returns a response with no text content (e.g. empty or null).
    Instead of returning nothing or failing, the engine returns the default
    fallback message so the user always gets a sensible reply.
    """
    engine, mock_client = _make_engine()
    mock_client.chat.completions.create.return_value = _make_text_response(None)

    result = engine.answer("Something", session_id="s1")
    assert result == DEFAULT_FALLBACK
