from contextlib import asynccontextmanager
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import json
from dotenv import load_dotenv
from indexer import DocumentIndexer
from retriever import DocumentRetriever
import asyncio
from config import get_backend_settings

# Load environment variables
load_dotenv()
settings = get_backend_settings()


def _is_ready(app: FastAPI) -> bool:
    return (
        getattr(app.state, "startup_error", None) is None
        and getattr(app.state, "indexer", None) is not None
        and getattr(app.state, "retriever", None) is not None
    )


def _require_services(app: FastAPI) -> tuple[DocumentIndexer, DocumentRetriever]:
    if not _is_ready(app):
        startup_error = getattr(app.state, "startup_error", "Service not initialized")
        raise RuntimeError(startup_error)

    return app.state.indexer, app.state.retriever


async def _try_send_fatal_error(websocket: WebSocket, message: str) -> None:
    """Attempt to send a fatal_error message to the client; log if that also fails."""
    try:
        await websocket.send_text(
            json.dumps({"type": "fatal_error", "data": {"message": message}})
        )
    except Exception as send_exc:
        print(f"Failed to send error to client: {send_exc}")


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.settings = settings
    app.state.indexer = None
    app.state.retriever = None
    app.state.startup_error = None

    try:
        app.state.indexer = DocumentIndexer(settings=settings)
        app.state.retriever = DocumentRetriever(settings=settings)
    except Exception as exc:
        app.state.startup_error = str(exc)
        print(f"Startup initialization failed: {exc}")

    yield

    app.state.indexer = None
    app.state.retriever = None


app = FastAPI(lifespan=lifespan)

# CORS for React dev server
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class IndexRequest(BaseModel):
    directory: str


class Message(BaseModel):
    role: str
    content: str


@app.post("/api/index")
async def index_documents(request: IndexRequest):
    """Index documents from directory"""
    try:
        indexer, _ = _require_services(app)
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc))

    try:
        stats = indexer.index_directory(request.directory)
        return {"success": True, "stats": stats}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/stats")
async def get_stats():
    """Get indexing statistics"""
    try:
        indexer, _ = _require_services(app)
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc))

    return indexer.get_stats()


@app.get("/api/indexed-files")
async def get_indexed_files():
    """Get detailed information about indexed files"""
    try:
        indexer, _ = _require_services(app)
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc))

    return indexer.get_indexed_files()


@app.get("/api/health")
async def get_health():
    startup_error = getattr(app.state, "startup_error", None)
    return {
        "ready": _is_ready(app),
        "startup_error": startup_error,
    }


@app.websocket("/ws/index")
async def websocket_index(websocket: WebSocket):
    """WebSocket endpoint for real-time indexing with progress updates"""
    await websocket.accept()

    try:
        indexer, retriever = _require_services(websocket.app)
    except RuntimeError as exc:
        await websocket.send_text(
            json.dumps({"type": "fatal_error", "data": {"message": str(exc)}})
        )
        await websocket.close()
        return

    try:
        # Receive indexing request
        data = await websocket.receive_text()
        try:
            request_data = json.loads(data)
        except json.JSONDecodeError:
            await websocket.send_text(
                json.dumps(
                    {"type": "error", "data": {"message": "Invalid JSON in request"}}
                )
            )
            await websocket.close()
            return
        directory = request_data.get("directory")

        if not directory:
            await websocket.send_text(
                json.dumps(
                    {"type": "error", "data": {"message": "No directory provided"}}
                )
            )
            await websocket.close()
            return

        # Get the current event loop to pass to the thread
        loop = asyncio.get_event_loop()

        # Define progress callback to send updates via WebSocket
        async def send_progress(message):
            await websocket.send_text(json.dumps(message))

        # Run indexing in a thread to avoid blocking
        def run_indexing():
            def progress_callback(msg):
                # Schedule the coroutine on the main event loop
                asyncio.run_coroutine_threadsafe(send_progress(msg), loop)

            return indexer.index_directory(
                directory,
                progress_callback=progress_callback,
            )

        # Run in executor to avoid blocking
        stats = await asyncio.to_thread(run_indexing)

        # Reload the retriever so it picks up the new index
        retriever.reload()

        # Send completion signal
        await websocket.send_text(
            json.dumps({"type": "done", "data": {"stats": stats}})
        )

    except WebSocketDisconnect:
        print("Client disconnected from indexing")
    except Exception as e:
        print(f"Indexing error: {e}")
        await _try_send_fatal_error(websocket, str(e))
        await websocket.close()


@app.websocket("/ws/chat")
async def websocket_chat(websocket: WebSocket):
    """WebSocket endpoint for real-time chat"""
    await websocket.accept()
    conversation_history = []

    try:
        _, retriever = _require_services(websocket.app)
    except RuntimeError as exc:
        await websocket.send_text(
            json.dumps({"type": "fatal_error", "data": {"message": str(exc)}})
        )
        await websocket.close()
        return

    try:
        while True:
            # Receive message from client
            data = await websocket.receive_text()
            try:
                message_data = json.loads(data)
            except json.JSONDecodeError:
                await websocket.send_text(
                    json.dumps(
                        {
                            "type": "error",
                            "data": {"message": "Invalid JSON in request"},
                        }
                    )
                )
                continue

            query = message_data.get("query")
            if not query:
                continue

            # Add user message to history
            conversation_history.append({"role": "user", "content": query})

            # Stream response
            assistant_message = ""
            async for chunk in retriever.ask_streaming(
                query, conversation_history[:-1]
            ):
                await websocket.send_text(chunk)

                # Collect assistant message for history
                chunk_data = json.loads(chunk)
                if chunk_data["type"] == "content":
                    assistant_message += chunk_data["data"]

            # Add complete assistant message to history
            if assistant_message:
                conversation_history.append(
                    {"role": "assistant", "content": assistant_message}
                )

            # Send completion signal
            await websocket.send_text(json.dumps({"type": "done"}) + "\n")

    except WebSocketDisconnect:
        print("Client disconnected")
    except Exception as e:
        print(f"WebSocket error: {e}")
        await _try_send_fatal_error(websocket, str(e))
        await websocket.close()


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
