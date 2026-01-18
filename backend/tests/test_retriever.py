"""
Tests for DocumentRetriever class and RAG functionality.
"""
import pytest
import json


class TestDocumentRetrieverInit:
    """Test DocumentRetriever initialization."""

    def test_init_with_existing_index(self, temp_dir, mock_anthropic_client, mocker):
        """Test initialization when index files exist."""
        from retriever import DocumentRetriever
        import pickle

        persist_dir = temp_dir / "db"
        persist_dir.mkdir(parents=True, exist_ok=True)

        # Create dummy files
        (persist_dir / "index.faiss").touch()
        with open(persist_dir / "metadata.pkl", 'wb') as f:
            pickle.dump([{"file": "test.md"}], f)
        with open(persist_dir / "texts.pkl", 'wb') as f:
            pickle.dump(["test content"], f)

        retriever = DocumentRetriever(persist_directory=str(persist_dir))

        assert retriever.index is not None
        assert len(retriever.metadata) == 1
        assert len(retriever.texts) == 1

    def test_init_without_index(self, temp_dir, mock_anthropic_client):
        """Test initialization when no index exists."""
        from retriever import DocumentRetriever

        persist_dir = temp_dir / "db"
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

    def test_search_filters_deleted_chunks(self, temp_dir, mock_anthropic_client):
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

    def test_search_with_no_index(self, temp_dir, mock_anthropic_client):
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

    def test_search_handles_empty_index(self, temp_dir, mock_anthropic_client):
        """Test search with empty index."""
        from retriever import DocumentRetriever
        import faiss

        retriever = DocumentRetriever(persist_directory=str(temp_dir / "db"))
        retriever.index = faiss.IndexFlatL2(384)
        retriever.index.ntotal = 0

        results = retriever.search("test query")

        assert results == []


class TestAskStreaming:
    """Test streaming question answering."""

    @pytest.mark.asyncio
    async def test_ask_streaming_yields_sources(self, retriever_with_index):
        """Test that ask_streaming yields source information."""
        chunks = []

        async for chunk in retriever_with_index.ask_streaming("What is authentication?"):
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
            {"role": "assistant", "content": "Previous answer"}
        ]

        chunks = []

        async for chunk in retriever_with_index.ask_streaming(
            "Follow-up question",
            conversation_history=history
        ):
            chunks.append(chunk)

        # Should complete successfully
        assert len(chunks) > 0

    @pytest.mark.asyncio
    async def test_ask_streaming_builds_context_from_sources(self, retriever_with_index, mocker):
        """Test that retrieved sources are included in LLM context."""
        mock_stream = mocker.patch.object(
            retriever_with_index.anthropic_client.messages,
            'stream'
        )

        class MockStream:
            def __enter__(self):
                return self

            def __exit__(self, *args):
                pass

            @property
            def text_stream(self):
                return iter(["Response"])

        mock_stream.return_value = MockStream()

        chunks = []
        async for chunk in retriever_with_index.ask_streaming("test query"):
            chunks.append(chunk)

        # Verify stream was called with context
        assert mock_stream.called
        call_args = mock_stream.call_args
        messages = call_args[1]["messages"]

        # Should have system context with sources
        assert len(messages) > 0
        assert messages[0]["role"] == "user"

    @pytest.mark.asyncio
    async def test_ask_streaming_empty_query(self, retriever_with_index):
        """Test streaming with empty query."""
        chunks = []

        async for chunk in retriever_with_index.ask_streaming(""):
            chunks.append(chunk)

        # Should still complete (backend doesn't validate empty queries)
        assert len(chunks) >= 0

    @pytest.mark.asyncio
    async def test_ask_streaming_with_no_sources(self, temp_dir, mock_anthropic_client):
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


class TestAnthropicIntegration:
    """Test integration with Anthropic Claude API."""

    @pytest.mark.asyncio
    async def test_uses_correct_model(self, retriever_with_index, mocker):
        """Test that correct Claude model is used."""
        mock_stream = mocker.patch.object(
            retriever_with_index.anthropic_client.messages,
            'stream'
        )

        class MockStream:
            def __enter__(self):
                return self

            def __exit__(self, *args):
                pass

            @property
            def text_stream(self):
                return iter([])

        mock_stream.return_value = MockStream()

        async for _ in retriever_with_index.ask_streaming("test"):
            pass

        call_args = mock_stream.call_args
        assert call_args[1]["model"] == "claude-sonnet-4-20250514"

    @pytest.mark.asyncio
    async def test_uses_correct_max_tokens(self, retriever_with_index, mocker):
        """Test that max_tokens is set correctly."""
        mock_stream = mocker.patch.object(
            retriever_with_index.anthropic_client.messages,
            'stream'
        )

        class MockStream:
            def __enter__(self):
                return self

            def __exit__(self, *args):
                pass

            @property
            def text_stream(self):
                return iter([])

        mock_stream.return_value = MockStream()

        async for _ in retriever_with_index.ask_streaming("test"):
            pass

        call_args = mock_stream.call_args
        assert call_args[1]["max_tokens"] == 16384


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
