"""V9: LangGraph Memory (STM + LTM) tests.

Tests cover:
- STM: Conversation continuity (same thread_id preserves messages).
- STM: Thread isolation (different thread_ids have independent state).
- STM: State survives checkpoint persistence.
- LTM: Cross-thread memory (store.put in thread_1, store.get in thread_2).
- LTM: Namespace isolation (student_1 memories invisible to student_2).
- LTM: Store accessible inside graph nodes via get_store().
- Module: Factory functions and singleton management.

All tests use a minimal graph with no LLM calls — they verify the
checkpointer and store infrastructure, not the agent logic.
"""

from __future__ import annotations

from typing import Annotated

import pytest
from langchain_core.messages import AIMessage, HumanMessage
from langgraph.graph import END, START, StateGraph
from langgraph.graph.message import add_messages
from typing_extensions import TypedDict


# ── Minimal graph for testing (no LLM needed) ────────────────────────────

class _MinimalState(TypedDict):
    """Lightweight state for checkpointer / store tests."""

    messages: Annotated[list, add_messages]
    counter: int


def _echo_node(state: _MinimalState) -> dict:
    """Increment counter and echo the last user message as an AI reply."""
    last_msg = state["messages"][-1].content if state.get("messages") else ""
    return {
        "messages": [AIMessage(content=f"Echo: {last_msg}")],
        "counter": state.get("counter", 0) + 1,
    }


def _build_test_graph(checkpointer=None, store=None):
    """Build and compile a minimal echo graph for testing."""
    builder = StateGraph(_MinimalState)
    builder.add_node("echo", _echo_node)
    builder.add_edge(START, "echo")
    builder.add_edge("echo", END)

    compile_kwargs = {}
    if checkpointer is not None:
        compile_kwargs["checkpointer"] = checkpointer
    if store is not None:
        compile_kwargs["store"] = store
    return builder.compile(**compile_kwargs)


# ═══════════════════════════════════════════════════════════════════════════
# STM Tests — SqliteSaver Checkpointer
# ═══════════════════════════════════════════════════════════════════════════


class TestSTMConversationContinuity:
    """Same thread_id preserves messages across invocations."""

    def test_messages_accumulate_across_turns(self, checkpointer):
        """Two invocations with the same thread_id should accumulate messages."""
        graph = _build_test_graph(checkpointer=checkpointer)
        config = {"configurable": {"thread_id": "test-thread-1"}}

        # Turn 1
        result1 = graph.invoke(
            {"messages": [HumanMessage(content="Hello")], "counter": 0},
            config=config,
        )
        assert result1["counter"] == 1
        assert len(result1["messages"]) == 2  # Human + AI

        # Turn 2 — only pass the NEW message
        result2 = graph.invoke(
            {"messages": [HumanMessage(content="How are you?")], "counter": 0},
            config=config,
        )
        # Counter should be 1 again (we passed 0 + node increments to 1)
        # But messages should have accumulated: 4 total (2 human + 2 AI)
        assert len(result2["messages"]) == 4

    def test_message_content_preserved(self, checkpointer):
        """The content of earlier messages is preserved in subsequent turns."""
        graph = _build_test_graph(checkpointer=checkpointer)
        config = {"configurable": {"thread_id": "test-content-check"}}

        graph.invoke(
            {"messages": [HumanMessage(content="first message")], "counter": 0},
            config=config,
        )
        result = graph.invoke(
            {"messages": [HumanMessage(content="second message")], "counter": 0},
            config=config,
        )

        contents = [m.content for m in result["messages"]]
        assert "first message" in contents
        assert "second message" in contents
        assert any("Echo: first message" in c for c in contents)


class TestSTMThreadIsolation:
    """Different thread_ids have independent state."""

    def test_threads_do_not_share_messages(self, checkpointer):
        """Messages sent to thread_A should not appear in thread_B."""
        graph = _build_test_graph(checkpointer=checkpointer)
        config_a = {"configurable": {"thread_id": "thread-A"}}
        config_b = {"configurable": {"thread_id": "thread-B"}}

        # Send to thread A
        graph.invoke(
            {"messages": [HumanMessage(content="Only for A")], "counter": 0},
            config=config_a,
        )

        # Send to thread B
        result_b = graph.invoke(
            {"messages": [HumanMessage(content="Only for B")], "counter": 0},
            config=config_b,
        )

        # Thread B should only have its own messages
        contents_b = [m.content for m in result_b["messages"]]
        assert "Only for B" in contents_b
        assert "Only for A" not in contents_b
        assert len(result_b["messages"]) == 2  # 1 human + 1 AI

    def test_counters_are_independent(self, checkpointer):
        """Each thread maintains its own counter independently."""
        graph = _build_test_graph(checkpointer=checkpointer)
        config_a = {"configurable": {"thread_id": "counter-A"}}
        config_b = {"configurable": {"thread_id": "counter-B"}}

        # Send 3 messages to thread A
        for i in range(3):
            graph.invoke(
                {"messages": [HumanMessage(content=f"msg-{i}")], "counter": 0},
                config=config_a,
            )

        # Send 1 message to thread B
        result_b = graph.invoke(
            {"messages": [HumanMessage(content="single")], "counter": 0},
            config=config_b,
        )

        # Thread B should have only 2 messages (1 human + 1 AI)
        assert len(result_b["messages"]) == 2


class TestSTMPersistence:
    """State survives checkpoint persistence."""

    def test_state_recovered_from_checkpoint(self, checkpointer):
        """get_state() returns the state saved by a previous invocation."""
        graph = _build_test_graph(checkpointer=checkpointer)
        config = {"configurable": {"thread_id": "persist-test"}}

        graph.invoke(
            {"messages": [HumanMessage(content="persisted msg")], "counter": 0},
            config=config,
        )

        # Read state directly from the checkpoint
        snapshot = graph.get_state(config)
        assert snapshot.values is not None
        msgs = snapshot.values["messages"]
        assert len(msgs) == 2
        assert msgs[0].content == "persisted msg"
        assert "Echo: persisted msg" in msgs[1].content

    def test_empty_thread_returns_no_state(self, checkpointer):
        """get_state() for a never-used thread_id returns empty values."""
        graph = _build_test_graph(checkpointer=checkpointer)
        config = {"configurable": {"thread_id": "never-used"}}

        snapshot = graph.get_state(config)
        # Should return empty/no values
        assert not snapshot.values


# ═══════════════════════════════════════════════════════════════════════════
# LTM Tests — InMemoryStore
# ═══════════════════════════════════════════════════════════════════════════


class TestLTMCrossThreadMemory:
    """Memory written in one thread is accessible from another thread."""

    def test_store_put_and_get(self, memory_store):
        """Basic put/get on the store works."""
        ns = ("student_1", "memories")
        memory_store.put(ns, "learning_style", {"style": "visual"})

        item = memory_store.get(ns, "learning_style")
        assert item is not None
        assert item.value == {"style": "visual"}

    def test_cross_thread_via_store(self, checkpointer, memory_store):
        """Data written via store in thread_1 is readable in thread_2."""
        graph = _build_test_graph(
            checkpointer=checkpointer, store=memory_store
        )
        config_t1 = {"configurable": {"thread_id": "cross-t1"}}
        config_t2 = {"configurable": {"thread_id": "cross-t2"}}

        # Write to store (simulating what memory_saver does)
        ns = ("student_42", "memories")
        memory_store.put(ns, "weaknesses", {"topics": ["Integrals"]})

        # Invoke thread 1 (just to show graph works with store)
        graph.invoke(
            {"messages": [HumanMessage(content="t1")], "counter": 0},
            config=config_t1,
        )

        # Invoke thread 2
        graph.invoke(
            {"messages": [HumanMessage(content="t2")], "counter": 0},
            config=config_t2,
        )

        # The store data is still accessible (shared across threads)
        item = memory_store.get(ns, "weaknesses")
        assert item is not None
        assert item.value["topics"] == ["Integrals"]

    def test_store_overwrite(self, memory_store):
        """Writing to the same key overwrites the previous value."""
        ns = ("student_1", "memories")
        memory_store.put(ns, "learning_style", {"style": "visual"})
        memory_store.put(ns, "learning_style", {"style": "procedural"})

        item = memory_store.get(ns, "learning_style")
        assert item.value["style"] == "procedural"


class TestLTMNamespaceIsolation:
    """Student_1 memories are not visible to student_2."""

    def test_different_students_isolated(self, memory_store):
        """Memories written under student_1 namespace are not in student_2."""
        ns_1 = ("student_1", "memories")
        ns_2 = ("student_2", "memories")

        memory_store.put(ns_1, "learning_style", {"style": "visual"})

        # Student 2 should not see student 1's data
        item = memory_store.get(ns_2, "learning_style")
        assert item is None

    def test_same_key_different_students(self, memory_store):
        """Same key in different student namespaces stores independent values."""
        ns_1 = ("student_1", "memories")
        ns_2 = ("student_2", "memories")

        memory_store.put(ns_1, "weaknesses", {"topics": ["Calculus"]})
        memory_store.put(ns_2, "weaknesses", {"topics": ["Statistics"]})

        assert memory_store.get(ns_1, "weaknesses").value["topics"] == ["Calculus"]
        assert memory_store.get(ns_2, "weaknesses").value["topics"] == ["Statistics"]


class TestLTMStoreInGraphNode:
    """Verify get_store() works inside a graph node execution context."""

    def test_node_can_read_store(self, checkpointer, memory_store):
        """A graph node can access the store via get_store()."""

        class _StoreReadState(TypedDict):
            messages: Annotated[list, add_messages]
            store_result: str | None

        def _reader_node(state: _StoreReadState) -> dict:
            from langgraph.config import get_store

            store = get_store()
            item = store.get(("test_ns",), "greeting")
            val = item.value["text"] if item else "not found"
            return {
                "messages": [AIMessage(content=val)],
                "store_result": val,
            }

        # Pre-populate store
        memory_store.put(("test_ns",), "greeting", {"text": "hello from store"})

        builder = StateGraph(_StoreReadState)
        builder.add_node("reader", _reader_node)
        builder.add_edge(START, "reader")
        builder.add_edge("reader", END)
        graph = builder.compile(checkpointer=checkpointer, store=memory_store)

        result = graph.invoke(
            {"messages": [HumanMessage(content="read it")], "store_result": None},
            config={"configurable": {"thread_id": "store-read-test"}},
        )
        assert result["store_result"] == "hello from store"

    def test_node_can_write_store(self, checkpointer, memory_store):
        """A graph node can write to the store via get_store()."""

        def _writer_node(state: _MinimalState) -> dict:
            from langgraph.config import get_store

            store = get_store()
            store.put(("written_ns",), "data", {"written": True})
            return {
                "messages": [AIMessage(content="wrote it")],
                "counter": 1,
            }

        builder = StateGraph(_MinimalState)
        builder.add_node("writer", _writer_node)
        builder.add_edge(START, "writer")
        builder.add_edge("writer", END)
        graph = builder.compile(checkpointer=checkpointer, store=memory_store)

        graph.invoke(
            {"messages": [HumanMessage(content="write")], "counter": 0},
            config={"configurable": {"thread_id": "store-write-test"}},
        )

        # Verify the write landed in the store
        item = memory_store.get(("written_ns",), "data")
        assert item is not None
        assert item.value["written"] is True


# ═══════════════════════════════════════════════════════════════════════════
# Module Tests — checkpointer.py factories
# ═══════════════════════════════════════════════════════════════════════════


class TestCheckpointerModule:
    """Tests for the checkpointer factory module."""

    def test_create_test_checkpointer_type(self):
        from backend.app.agents.checkpointer import create_test_checkpointer
        from langgraph.checkpoint.sqlite import SqliteSaver

        cp = create_test_checkpointer()
        assert isinstance(cp, SqliteSaver)
        cp.conn.close()

    def test_create_test_store_type(self):
        from backend.app.agents.checkpointer import create_test_store
        from langgraph.store.memory import InMemoryStore

        st = create_test_store()
        assert isinstance(st, InMemoryStore)

    def test_each_call_returns_fresh_instance(self):
        from backend.app.agents.checkpointer import (
            create_test_checkpointer,
            create_test_store,
        )

        cp1 = create_test_checkpointer()
        cp2 = create_test_checkpointer()
        assert cp1 is not cp2
        cp1.conn.close()
        cp2.conn.close()

        st1 = create_test_store()
        st2 = create_test_store()
        assert st1 is not st2

    def test_reset_singletons(self):
        from backend.app.agents.checkpointer import (
            get_checkpointer,
            get_memory_store,
            reset_singletons,
        )
        import backend.app.agents.checkpointer as mod

        # Force singletons to be created
        _ = get_checkpointer()
        _ = get_memory_store()
        assert mod._checkpointer is not None
        assert mod._store is not None

        # Reset
        reset_singletons()
        assert mod._checkpointer is None
        assert mod._store is None


# ═══════════════════════════════════════════════════════════════════════════
# Message Trimming Tests
# ═══════════════════════════════════════════════════════════════════════════


class TestMessageTrimming:
    """Verify that RemoveMessage correctly trims old messages."""

    def test_remove_message_trims_old_messages(self, checkpointer):
        """Sending RemoveMessage objects drops the targeted messages."""
        from langchain_core.messages import RemoveMessage

        graph = _build_test_graph(checkpointer=checkpointer)
        config = {"configurable": {"thread_id": "trim-test"}}

        # Send 6 messages (12 total with AI echoes)
        for i in range(6):
            graph.invoke(
                {"messages": [HumanMessage(content=f"msg-{i}")], "counter": 0},
                config=config,
            )

        snap = graph.get_state(config)
        all_msgs = snap.values["messages"]
        assert len(all_msgs) == 12  # 6 human + 6 AI

        # Trim: keep only the last 4 messages, remove the first 8
        msgs_to_remove = all_msgs[:-4]
        removals = [RemoveMessage(id=m.id) for m in msgs_to_remove]

        # Send removals + a new message in one invoke
        result = graph.invoke(
            {"messages": removals + [HumanMessage(content="after-trim")],
             "counter": 0},
            config=config,
        )

        # After trimming: 4 kept + 1 new human + 1 new AI = 6
        assert len(result["messages"]) == 6

        # The oldest messages should be gone
        contents = [m.content for m in result["messages"]]
        assert "msg-0" not in contents
        assert "msg-1" not in contents
        assert "after-trim" in contents

    def test_no_trimming_under_limit(self, checkpointer):
        """When under the limit, no RemoveMessage is needed."""
        graph = _build_test_graph(checkpointer=checkpointer)
        config = {"configurable": {"thread_id": "no-trim"}}

        # Send 2 messages — well under any reasonable limit
        graph.invoke(
            {"messages": [HumanMessage(content="first")], "counter": 0},
            config=config,
        )
        result = graph.invoke(
            {"messages": [HumanMessage(content="second")], "counter": 0},
            config=config,
        )

        # All 4 messages should be present (2 human + 2 AI)
        assert len(result["messages"]) == 4
        contents = [m.content for m in result["messages"]]
        assert "first" in contents
        assert "second" in contents

    def test_trimmed_checkpoint_persists(self, checkpointer):
        """After trimming, the checkpoint reflects the trimmed state."""
        from langchain_core.messages import RemoveMessage

        graph = _build_test_graph(checkpointer=checkpointer)
        config = {"configurable": {"thread_id": "trim-persist"}}

        # Send 4 messages (8 total)
        for i in range(4):
            graph.invoke(
                {"messages": [HumanMessage(content=f"m-{i}")], "counter": 0},
                config=config,
            )

        snap = graph.get_state(config)
        all_msgs = snap.values["messages"]
        assert len(all_msgs) == 8

        # Remove the first 4 messages
        removals = [RemoveMessage(id=m.id) for m in all_msgs[:4]]
        graph.invoke(
            {"messages": removals + [HumanMessage(content="post-trim")],
             "counter": 0},
            config=config,
        )

        # Verify the checkpoint reflects trimming
        snap2 = graph.get_state(config)
        trimmed_msgs = snap2.values["messages"]
        assert len(trimmed_msgs) == 6  # 4 kept + 1 human + 1 AI
        contents = [m.content for m in trimmed_msgs]
        assert "m-0" not in contents  # oldest removed
        assert "post-trim" in contents  # newest present


# ═══════════════════════════════════════════════════════════════════════════
# Reset Creates Fresh Thread Tests
# ═══════════════════════════════════════════════════════════════════════════


class TestResetCreatesNewThread:
    """Reset clears the active thread so the next request starts fresh."""

    def test_reset_clears_active_thread(self):
        """After reset, the student's active thread is removed."""
        from backend.app.routers.chat import _active_threads

        # Simulate an existing active thread
        _active_threads[9999] = 42

        # Import app and use TestClient
        from fastapi.testclient import TestClient
        from backend.app.main import app

        client = TestClient(app)
        response = client.post(
            "/api/chat",
            json={"student_id": 9999, "message": "", "reset": True},
        )

        assert response.status_code == 200
        assert response.json()["response"] == "Memory cleared. Ready for a new session!"
        assert 9999 not in _active_threads

    def test_reset_is_idempotent(self):
        """Resetting a student with no active thread doesn't crash."""
        from backend.app.routers.chat import _active_threads
        from fastapi.testclient import TestClient
        from backend.app.main import app

        # Ensure no active thread
        _active_threads.pop(8888, None)

        client = TestClient(app)
        response = client.post(
            "/api/chat",
            json={"student_id": 8888, "message": "", "reset": True},
        )

        assert response.status_code == 200
        assert 8888 not in _active_threads
