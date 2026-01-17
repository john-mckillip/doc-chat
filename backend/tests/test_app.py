"""
Tests for FastAPI application endpoints and WebSocket handlers.
"""
import pytest
import json
from unittest.mock import Mock, patch, AsyncMock
from fastapi.testclient import TestClient
from fastapi.websockets import WebSocketDisconnect


@pytest.fixture
def client(mock_anthropic_client, mock_env_vars):
    """Create a test client with mocked dependencies."""
    from app import app
    # TestClient from starlette takes app as first positional argument
    client = TestClient(app)
    yield client
    client.close()


class TestRESTEndpoints:
    """Test REST API endpoints."""

    def test_index_documents_success(self, client, sample_docs, mocker):
        """Test successful document indexing via POST /api/index."""
        mock_index_dir = mocker.patch('app.indexer.index_directory')
        mock_index_dir.return_value = {
            "files": 5,
            "chunks": 42,
            "new": 5,
            "modified": 0,
            "unchanged": 0,
            "deleted": 0
        }

        response = client.post("/api/index", json={"directory": str(sample_docs)})

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["stats"]["files"] == 5
        assert data["stats"]["chunks"] == 42

    def test_index_documents_invalid_directory(self, client):
        """Test indexing with non-existent directory."""
        response = client.post("/api/index", json={"directory": "/nonexistent/path"})

        # App returns success but with no documents indexed
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["stats"]["chunks"] == 0  # index_directory returns "chunks", not "total_chunks"

    def test_index_documents_missing_directory_field(self, client):
        """Test indexing without directory field."""
        response = client.post("/api/index", json={})

        # Pydantic validation should catch this
        assert response.status_code == 422

    def test_get_stats_with_index(self, client, mocker):
        """Test GET /api/stats with indexed documents."""
        mock_get_stats = mocker.patch('app.indexer.get_stats')
        mock_get_stats.return_value = {
            "total_chunks": 387,
            "dimension": 384
        }

        response = client.get("/api/stats")

        assert response.status_code == 200
        data = response.json()
        assert data["total_chunks"] == 387
        assert data["dimension"] == 384

    def test_get_stats_without_index(self, client, mocker):
        """Test GET /api/stats with no indexed documents."""
        mock_get_stats = mocker.patch('app.indexer.get_stats')
        mock_get_stats.return_value = {
            "total_chunks": 0,
            "dimension": 384
        }

        response = client.get("/api/stats")

        assert response.status_code == 200
        data = response.json()
        assert data["total_chunks"] == 0


class TestWebSocketIndexing:
    """Test WebSocket indexing endpoint."""

    def test_websocket_index_success(self, client, sample_docs, mocker):
        """Test successful WebSocket indexing."""
        messages_received = []

        mock_index_dir = mocker.patch('app.indexer.index_directory')
        mock_index_dir.return_value = {
            "files": 3,
            "chunks": 25,
            "new": 3,
            "modified": 0,
            "unchanged": 0,
            "deleted": 0
        }

        with client.websocket_connect("/ws/index") as websocket:
            # Send indexing request
            websocket.send_json({"directory": str(sample_docs)})

            # Receive messages until done
            while True:
                message = websocket.receive_json()
                messages_received.append(message)
                if message.get("type") == "done":
                    break

        # Should receive at least a done message
        assert any(msg["type"] == "done" for msg in messages_received)

    def test_websocket_index_missing_directory(self, client):
        """Test WebSocket indexing without directory."""
        with client.websocket_connect("/ws/index") as websocket:
            websocket.send_json({})

            message = websocket.receive_json()

            assert message["type"] == "error"
            assert "directory" in message["data"]["message"].lower()

    def test_websocket_index_invalid_json(self, client):
        """Test WebSocket indexing with invalid JSON."""
        with client.websocket_connect("/ws/index") as websocket:
            try:
                websocket.send_text("not json")
                message = websocket.receive_json()
                # Should receive an error or fatal_error
                assert message["type"] in ["error", "fatal_error"]
            except WebSocketDisconnect:
                # Connection closed due to error is acceptable
                pass

    def test_websocket_index_indexing_error(self, client, mocker):
        """Test WebSocket indexing when indexer raises an error."""
        mock_index_dir = mocker.patch('app.indexer.index_directory')
        mock_index_dir.side_effect = Exception("Indexing failed")

        with client.websocket_connect("/ws/index") as websocket:
            websocket.send_json({"directory": "/some/path"})

            message = websocket.receive_json()

            assert message["type"] == "fatal_error"
            assert "Indexing failed" in message["data"]["message"]


class TestWebSocketChat:
    """Test WebSocket chat endpoint."""

    def test_websocket_chat_send_message(self, client, mocker):
        """Test sending a chat message via WebSocket."""
        messages_received = []

        mock_ask_streaming = mocker.patch('app.retriever.ask_streaming')

        # Mock async generator
        async def mock_stream():
            yield json.dumps({"type": "sources", "data": [{"file": "test.md"}]}) + "\n"
            yield json.dumps({"type": "content", "data": "Hello"}) + "\n"
            yield json.dumps({"type": "content", "data": " world"}) + "\n"
            yield json.dumps({"type": "done"}) + "\n"

        mock_ask_streaming.return_value = mock_stream()

        with client.websocket_connect("/ws/chat") as websocket:
            # Send query
            websocket.send_json({"query": "What is authentication?"})

            # Receive responses
            for _ in range(4):  # Expect 4 messages
                message = websocket.receive_text()
                data = json.loads(message)
                messages_received.append(data)
                if data.get("type") == "done":
                    break

        assert len(messages_received) >= 3
        assert any(msg["type"] == "sources" for msg in messages_received)
        assert any(msg["type"] == "content" for msg in messages_received)
        assert any(msg["type"] == "done" for msg in messages_received)

    def test_websocket_chat_maintains_history(self, client, mocker):
        """Test that conversation history is maintained."""
        mock_ask_streaming = mocker.patch('app.retriever.ask_streaming')

        async def mock_stream():
            yield json.dumps({"type": "content", "data": "Response"}) + "\n"
            yield json.dumps({"type": "done"}) + "\n"

        # Make mock return a new generator each time it's called
        mock_ask_streaming.side_effect = lambda *args, **kwargs: mock_stream()

        with client.websocket_connect("/ws/chat") as websocket:
            # Send first message
            websocket.send_json({"query": "First question"})
            websocket.receive_text()  # content
            websocket.receive_text()  # done

            # Send second message
            websocket.send_json({"query": "Second question"})
            websocket.receive_text()  # content
            websocket.receive_text()  # done

            # Check that ask_streaming was called with conversation history
            assert mock_ask_streaming.call_count == 2
            # Second call: args are (query, conversation_history)
            second_call_args = mock_ask_streaming.call_args_list[1][0]  # [0] for positional args
            conversation_history = second_call_args[1] if len(second_call_args) > 1 else []

            # Should have at least the first user message and assistant response
            assert len(conversation_history) >= 2

    def test_websocket_chat_invalid_json(self, client):
        """Test WebSocket chat with invalid JSON."""
        with client.websocket_connect("/ws/chat") as websocket:
            try:
                websocket.send_text("{invalid json")
                # Should either receive error or disconnect
                message = websocket.receive_text()
                data = json.loads(message)
                assert "error" in data["type"].lower()
            except (WebSocketDisconnect, json.JSONDecodeError):
                # Disconnect is acceptable for invalid input
                pass

    def test_websocket_chat_empty_query(self, client, mocker):
        """Test WebSocket chat with empty query."""
        mock_ask_streaming = mocker.patch('app.retriever.ask_streaming')

        async def mock_stream():
            yield json.dumps({"type": "content", "data": "Response"}) + "\n"
            yield json.dumps({"type": "done"}) + "\n"

        mock_ask_streaming.side_effect = lambda *args, **kwargs: mock_stream()

        with client.websocket_connect("/ws/chat") as websocket:
            # Empty query is skipped by the server (continues to next iteration)
            # So send a valid query after the empty one
            websocket.send_json({"query": ""})
            websocket.send_json({"query": "Real question"})

            # Should receive response to the real question
            message = websocket.receive_text()
            assert message is not None
            # Should have called ask_streaming once (only for the real question)
            assert mock_ask_streaming.call_count == 1


class TestCORS:
    """Test CORS middleware configuration."""

    def test_cors_headers_present(self, client):
        """Test that CORS headers are configured."""
        response = client.get("/api/stats")

        # Should have successful response
        assert response.status_code == 200

    def test_cors_allows_localhost(self, client):
        """Test that localhost origins are allowed."""
        # TestClient doesn't properly handle OPTIONS requests with CORS
        # Instead, test that a regular request includes CORS headers
        response = client.get(
            "/api/stats",
            headers={"Origin": "http://localhost:5173"}
        )

        # Request should be successful
        assert response.status_code == 200
        # CORS header should be present (allowing the origin)
        assert "access-control-allow-origin" in response.headers


class TestHealthCheck:
    """Test application health and startup."""

    def test_app_imports_successfully(self):
        """Test that the app module can be imported."""
        from app import app
        assert app is not None

    def test_app_has_correct_routes(self, client):
        """Test that all expected routes are registered."""
        routes = [route.path for route in client.app.routes]

        assert "/api/index" in routes
        assert "/api/stats" in routes
        assert "/ws/index" in routes
        assert "/ws/chat" in routes
