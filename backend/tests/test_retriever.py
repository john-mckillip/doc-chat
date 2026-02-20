"""
Tests for DocumentRetriever class and RAG functionality.
"""

import pytest
import json


class TestDocumentRetrieverInit:
    """Test DocumentRetriever initialization."""

    def test_init_with_existing_index(self, temp_dir, mock_ollama_client, mocker):
        """Test initialization when index files exist."""
        from retriever import DocumentRetriever
        import pickle

        persist_dir = temp_dir / "db"
        persist_dir.mkdir(parents=True, exist_ok=True)

        # Create dummy files
        (persist_dir / "index.faiss").touch()
        with open(persist_dir / "metadata.pkl", "wb") as f:
            pickle.dump([{"file": "test.md"}], f)
        with open(persist_dir / "texts.pkl", "wb") as f:
            pickle.dump(["test content"], f)

        retriever = DocumentRetriever(persist_directory=str(persist_dir))

        assert retriever.index is not None
        assert len(retriever.metadata) == 1
        assert len(retriever.texts) == 1

    def test_init_without_index(self, temp_dir, mock_ollama_client):
        """Test initialization when no index exists."""
        from retriever import DocumentRetriever

        persist_dir = temp_dir / "db"
        retriever = DocumentRetriever(persist_directory=str(persist_dir))

        assert retriever.index is None
        assert retriever.metadata == []
        assert retriever.texts == []

    def test_load_index_missing_metadata_file_resets_to_empty(
        self, temp_dir, mock_ollama_client
    ):
        """index.faiss present but metadata.pkl absent → safe empty reset, no crash."""
        from retriever import DocumentRetriever

        persist_dir = temp_dir / "db"
        persist_dir.mkdir(parents=True, exist_ok=True)
        (persist_dir / "index.faiss").touch()
        # metadata.pkl and texts.pkl deliberately absent

        retriever = DocumentRetriever(persist_directory=str(persist_dir))

        assert retriever.index is None
        assert retriever.metadata == []
        assert retriever.texts == []

    def test_load_index_missing_texts_file_resets_to_empty(
        self, temp_dir, mock_ollama_client
    ):
        """index.faiss + metadata.pkl present but texts.pkl absent → safe empty reset."""
        import pickle
        from retriever import DocumentRetriever

        persist_dir = temp_dir / "db"
        persist_dir.mkdir(parents=True, exist_ok=True)
        (persist_dir / "index.faiss").touch()
        with open(persist_dir / "metadata.pkl", "wb") as f:
            pickle.dump([{"file": "test.md"}], f)
        # texts.pkl deliberately absent

        retriever = DocumentRetriever(persist_directory=str(persist_dir))

        assert retriever.index is None
        assert retriever.metadata == []
        assert retriever.texts == []

    def test_load_index_corrupt_pickle_resets_to_empty(
        self, temp_dir, mock_ollama_client
    ):
        """Corrupt pickle files → safe empty reset rather than UnpicklingError crash."""
        from retriever import DocumentRetriever

        persist_dir = temp_dir / "db"
        persist_dir.mkdir(parents=True, exist_ok=True)
        (persist_dir / "index.faiss").touch()
        (persist_dir / "metadata.pkl").write_bytes(b"not valid pickle data!!!")
        (persist_dir / "texts.pkl").write_bytes(b"also garbage")

        retriever = DocumentRetriever(persist_directory=str(persist_dir))

        assert retriever.index is None
        assert retriever.metadata == []
        assert retriever.texts == []


class TestSearch:
    """Test vector similarity search."""

    def test_search_returns_results(self, retriever_with_index):
        """Test basic search functionality."""
        results = retriever_with_index.search("authentication", top_k=2)

        assert len(results) <= 2
        assert all("text" in r for r in results)
        assert all("metadata" in r for r in results)
        assert all("score" in r for r in results)

    def test_search_filters_deleted_chunks(self, temp_dir, mock_ollama_client):
        """Test that deleted chunks are filtered from search results."""
        from retriever import DocumentRetriever
        import faiss

        retriever = DocumentRetriever(persist_directory=str(temp_dir / "db"))
        retriever.index = faiss.IndexFlatL2(384)
        retriever.metadata = [
            {"file": "doc1.md", "deleted": False},
            {"file": "doc2.md", "deleted": True},
            {"file": "doc3.md", "deleted": False},
        ]
        retriever.texts = ["text1", "text2", "text3"]
        retriever.index.ntotal = 3

        results = retriever.search("test query", top_k=5)

        # Should only get non-deleted results
        assert len(results) <= 2
        assert all(not r["metadata"].get("deleted") for r in results)

    def test_search_with_no_index(self, temp_dir, mock_ollama_client):
        """Test search when index is None."""
        from retriever import DocumentRetriever

        retriever = DocumentRetriever(persist_directory=str(temp_dir / "db"))
        retriever.index = None

        results = retriever.search("test query")

        assert results == []

    def test_search_respects_top_k(self, retriever_with_index):
        """Test that search respects top_k parameter."""
        # Increase mock index size
        retriever_with_index.index.ntotal = 10

        results = retriever_with_index.search("test", top_k=3)

        assert len(results) <= 3

    def test_search_handles_empty_index(self, temp_dir, mock_ollama_client):
        """Test search with empty index."""
        from retriever import DocumentRetriever
        import faiss

        retriever = DocumentRetriever(persist_directory=str(temp_dir / "db"))
        retriever.index = faiss.IndexFlatL2(384)
        retriever.index.ntotal = 0

        results = retriever.search("test query")

        assert results == []

    def test_search_short_circuits_before_faiss_when_ntotal_zero(
        self, temp_dir, mock_ollama_client, mocker
    ):
        """FAISS search must NOT be called when the index is empty (ntotal==0).

        Passing k=0 to FAISS is undefined behaviour in some builds; the guard
        must short-circuit before that call.
        """
        from retriever import DocumentRetriever

        retriever = DocumentRetriever(persist_directory=str(temp_dir / "db"))
        retriever.index = mocker.MagicMock()
        retriever.index.ntotal = 0

        results = retriever.search("test query", top_k=5)

        retriever.index.search.assert_not_called()
        assert results == []

    def test_search_short_circuits_before_faiss_when_top_k_zero(
        self, temp_dir, mock_ollama_client, mocker
    ):
        """FAISS search must NOT be called when top_k <= 0."""
        from retriever import DocumentRetriever

        retriever = DocumentRetriever(persist_directory=str(temp_dir / "db"))
        retriever.index = mocker.MagicMock()
        retriever.index.ntotal = 10  # non-empty — guard must be top_k, not ntotal

        results = retriever.search("test query", top_k=0)

        retriever.index.search.assert_not_called()
        assert results == []


class TestAskStreaming:
    """Test streaming question answering."""

    @pytest.mark.asyncio
    async def test_ask_streaming_yields_sources(self, retriever_with_index):
        """Test that ask_streaming yields source information."""
        chunks = []

        async for chunk in retriever_with_index.ask_streaming(
            "What is authentication?"
        ):
            chunks.append(chunk)

        # Should have at least sources message
        messages = [json.loads(c.strip()) for c in chunks if c.strip()]
        assert any(msg["type"] == "sources" for msg in messages)

    @pytest.mark.asyncio
    async def test_ask_streaming_yields_content(self, retriever_with_index):
        """Test that ask_streaming yields content chunks."""
        chunks = []

        async for chunk in retriever_with_index.ask_streaming("How does the API work?"):
            chunks.append(chunk)

        # Should have content messages
        messages = [json.loads(c.strip()) for c in chunks if c.strip()]
        content_msgs = [msg for msg in messages if msg["type"] == "content"]
        assert len(content_msgs) > 0

    @pytest.mark.asyncio
    async def test_ask_streaming_with_conversation_history(self, retriever_with_index):
        """Test streaming with conversation history."""
        history = [
            {"role": "user", "content": "Previous question"},
            {"role": "assistant", "content": "Previous answer"},
        ]

        chunks = []

        async for chunk in retriever_with_index.ask_streaming(
            "Follow-up question", conversation_history=history
        ):
            chunks.append(chunk)

        # Should complete successfully
        assert len(chunks) > 0

    @pytest.mark.asyncio
    async def test_ask_streaming_builds_context_from_sources(
        self, retriever_with_index
    ):
        """Test that retrieved sources are included in LLM context."""
        from unittest.mock import Mock, AsyncMock

        captured_kwargs = {}

        class MockChunk:
            def __init__(self, content, done=False, done_reason=None):
                self.message = Mock()
                self.message.content = content
                self.done = done
                self.done_reason = done_reason

        async def _stream():
            yield MockChunk("Response", done=True, done_reason="stop")

        def chat_impl(**kwargs):
            captured_kwargs.update(kwargs)
            return _stream()

        retriever_with_index.ollama_client.chat = AsyncMock(side_effect=chat_impl)

        chunks = []
        async for chunk in retriever_with_index.ask_streaming("test query"):
            chunks.append(chunk)

        # Verify chat was called with context in messages
        assert "messages" in captured_kwargs
        messages = captured_kwargs["messages"]
        assert len(messages) > 0
        assert messages[0]["role"] == "user"

    @pytest.mark.asyncio
    async def test_ask_streaming_empty_query(self, retriever_with_index):
        """Test streaming with empty query."""
        chunks = []

        async for chunk in retriever_with_index.ask_streaming(""):
            chunks.append(chunk)

        # Should still complete (backend doesn't validate empty queries)

    @pytest.mark.asyncio
    async def test_ask_streaming_yields_error_on_ollama_failure(
        self, retriever_with_index
    ):
        """When Ollama raises an exception the generator must yield an error JSON
        message rather than propagating the exception to the caller."""
        from unittest.mock import AsyncMock

        retriever_with_index.ollama_client.chat = AsyncMock(
            side_effect=Exception("network error")
        )
        # Ensure the index has entries so search() runs (ntotal is 0 from mock by
        # default; set it so the guard doesn't short-circuit before Ollama is called).
        retriever_with_index.index.ntotal = 2

        chunks = []
        async for chunk in retriever_with_index.ask_streaming("test query"):
            chunks.append(chunk)

        messages = [json.loads(c.strip()) for c in chunks if c.strip()]
        error_messages = [msg for msg in messages if msg["type"] == "error"]

        assert len(error_messages) >= 1
        assert "network error" in error_messages[0]["data"]["message"]

    @pytest.mark.asyncio
    async def test_ask_streaming_with_no_sources(self, temp_dir, mock_ollama_client):
        """Test streaming when no relevant sources found."""
        from retriever import DocumentRetriever
        import faiss

        retriever = DocumentRetriever(persist_directory=str(temp_dir / "db"))
        retriever.index = faiss.IndexFlatL2(384)
        retriever.index.ntotal = 0

        chunks = []

        async for chunk in retriever.ask_streaming("test query"):
            chunks.append(chunk)

        # Should still return response even with no sources
        messages = [json.loads(c.strip()) for c in chunks if c.strip()]
        sources_msgs = [msg for msg in messages if msg["type"] == "sources"]

        if sources_msgs:
            # If sources message is sent, it should have empty array
            assert sources_msgs[0]["data"] == []


class TestSourceMetadataExtraction:
    """Test source metadata formatting."""

    @pytest.mark.asyncio
    async def test_source_includes_file_info(self, retriever_with_index):
        """Test that source metadata includes file information."""
        chunks = []

        async for chunk in retriever_with_index.ask_streaming("test"):
            chunks.append(chunk)

        messages = [json.loads(c.strip()) for c in chunks if c.strip()]
        sources_msg = next((msg for msg in messages if msg["type"] == "sources"), None)

        if sources_msg and len(sources_msg["data"]) > 0:
            source = sources_msg["data"][0]
            assert "file" in source
            assert "path" in source
            assert "chunk" in source

    @pytest.mark.asyncio
    async def test_sources_formatted_correctly(self, retriever_with_index):
        """Test that sources are formatted in expected structure."""
        chunks = []

        async for chunk in retriever_with_index.ask_streaming("authentication"):
            chunks.append(chunk)

        messages = [json.loads(c.strip()) for c in chunks if c.strip()]
        sources_msg = next((msg for msg in messages if msg["type"] == "sources"), None)

        assert sources_msg is not None
        assert "type" in sources_msg
        assert "data" in sources_msg
        assert isinstance(sources_msg["data"], list)


class TestOllamaIntegration:
    """Test integration with Ollama API."""

    @pytest.mark.asyncio
    async def test_uses_correct_model(self, retriever_with_index):
        """Test that correct Ollama model is used."""
        from unittest.mock import Mock, AsyncMock

        captured_kwargs = {}

        class MockChunk:
            def __init__(self, content, done=False, done_reason=None):
                self.message = Mock()
                self.message.content = content
                self.done = done
                self.done_reason = done_reason

        async def _stream():
            yield MockChunk("", done=True, done_reason="stop")

        def chat_impl(**kwargs):
            captured_kwargs.update(kwargs)
            return _stream()

        retriever_with_index.ollama_client.chat = AsyncMock(side_effect=chat_impl)

        [chunk async for chunk in retriever_with_index.ask_streaming("test")]

        assert captured_kwargs["model"] == "llama3.1:8b"

    @pytest.mark.asyncio
    async def test_uses_correct_num_predict(self, retriever_with_index):
        """Test that num_predict is set correctly from MAX_TOKENS env var."""
        from unittest.mock import Mock, AsyncMock

        captured_kwargs = {}

        class MockChunk:
            def __init__(self, content, done=False, done_reason=None):
                self.message = Mock()
                self.message.content = content
                self.done = done
                self.done_reason = done_reason

        async def _stream():
            yield MockChunk("", done=True, done_reason="stop")

        def chat_impl(**kwargs):
            captured_kwargs.update(kwargs)
            return _stream()

        retriever_with_index.ollama_client.chat = AsyncMock(side_effect=chat_impl)

        [chunk async for chunk in retriever_with_index.ask_streaming("test")]

        assert (
            captured_kwargs["options"]["num_predict"]
            == retriever_with_index.settings.max_tokens
        )


class TestJSONSerialization:
    """Test JSON serialization of responses."""

    @pytest.mark.asyncio
    async def test_all_messages_are_valid_json(self, retriever_with_index):
        """Test that all streamed chunks are valid JSON."""
        chunks = []

        async for chunk in retriever_with_index.ask_streaming("test"):
            chunks.append(chunk)

        # All chunks should be parseable JSON
        for chunk in chunks:
            if chunk.strip():
                try:
                    json.loads(chunk.strip())
                except json.JSONDecodeError:
                    pytest.fail(f"Invalid JSON chunk: {chunk}")

    @pytest.mark.asyncio
    async def test_message_structure(self, retriever_with_index):
        """Test that messages have correct structure."""
        chunks = []

        async for chunk in retriever_with_index.ask_streaming("test"):
            chunks.append(chunk)

        messages = [json.loads(c.strip()) for c in chunks if c.strip()]

        for msg in messages:
            assert "type" in msg
            assert msg["type"] in ["sources", "content"]
            assert "data" in msg
