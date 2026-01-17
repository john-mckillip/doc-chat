from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Dict
import json
import os
from dotenv import load_dotenv
from indexer import DocumentIndexer
from retriever import DocumentRetriever
import asyncio

# Load environment variables
load_dotenv()

app = FastAPI()

# CORS for React dev server
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173"
    ],  # Vite default port (both localhost and 127.0.0.1)
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

indexer = DocumentIndexer()
retriever = DocumentRetriever()

class IndexRequest(BaseModel):
    directory: str

class Message(BaseModel):
    role: str
    content: str

@app.post("/api/index")
async def index_documents(request: IndexRequest):
    """Index documents from directory"""
    try:
        stats = indexer.index_directory(request.directory)
        return {"success": True, "stats": stats}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/stats")
async def get_stats():
    """Get indexing statistics"""
    return indexer.get_stats()

@app.websocket("/ws/index")
async def websocket_index(websocket: WebSocket):
    """WebSocket endpoint for real-time indexing with progress updates"""
    await websocket.accept()

    try:
        # Receive indexing request
        data = await websocket.receive_text()
        request_data = json.loads(data)
        directory = request_data.get("directory")

        if not directory:
            await websocket.send_text(json.dumps({
                "type": "error",
                "data": {"message": "No directory provided"}
            }))
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

            return indexer.index_directory(directory, progress_callback=progress_callback)

        # Run in executor to avoid blocking
        stats = await asyncio.to_thread(run_indexing)

        # Send completion signal
        await websocket.send_text(json.dumps({
            "type": "done",
            "data": {}
        }))

    except WebSocketDisconnect:
        print("Client disconnected from indexing")
    except Exception as e:
        error_msg = f"Indexing error: {e}"
        print(error_msg)
        try:
            await websocket.send_text(json.dumps({
                "type": "fatal_error",
                "data": {"message": str(e)}
            }))
        except:
            pass
        await websocket.close()

@app.websocket("/ws/chat")
async def websocket_chat(websocket: WebSocket):
    """WebSocket endpoint for real-time chat"""
    await websocket.accept()
    conversation_history = []
    
    try:
        while True:
            # Receive message from client
            data = await websocket.receive_text()
            message_data = json.loads(data)
            
            query = message_data.get("query")
            if not query:
                continue
            
            # Add user message to history
            conversation_history.append({
                "role": "user",
                "content": query
            })
            
            # Stream response
            assistant_message = ""
            async for chunk in retriever.ask_streaming(query, conversation_history[:-1]):
                await websocket.send_text(chunk)
                
                # Collect assistant message for history
                chunk_data = json.loads(chunk)
                if chunk_data["type"] == "content":
                    assistant_message += chunk_data["data"]
            
            # Add complete assistant message to history
            if assistant_message:
                conversation_history.append({
                    "role": "assistant",
                    "content": assistant_message
                })
            
            # Send completion signal
            await websocket.send_text(json.dumps({
                "type": "done"
            }) + "\n")
            
    except WebSocketDisconnect:
        print("Client disconnected")
    except Exception as e:
        print(f"WebSocket error: {e}")
        await websocket.close()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)