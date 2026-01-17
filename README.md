# DocChat - AI-Powered Documentation Assistant

A local development tool that lets you chat with your project documentation using AI and semantic search. Ask questions in natural language and get real-time streaming responses with source citations.

## Features

- 🔍 **Semantic Search** - Find relevant documentation based on meaning, not just keywords
- 💬 **Real-time Streaming** - See responses as they're generated via WebSocket
- 📚 **Source Citations** - Know exactly which files informed each answer
- 🧠 **Conversation Memory** - Follow-up questions maintain context
- ⚡ **Smart Incremental Indexing** - MD5 hash tracking only re-indexes new/changed files
- 🔄 **WebSocket Indexing** - Real-time progress updates, no timeout issues on cloud platforms
- 🎨 **Clean UI** - Modern React interface with Tailwind CSS 4

## Architecture

```
┌─────────────────┐
│  React Frontend │
│   (TypeScript)  │
└────────┬────────┘
         │ WebSocket
         ↓
┌─────────────────┐      ┌──────────────┐
│  FastAPI Server │─────→│    FAISS     │
│    (Python)     │      │ (Vector DB)  │
└────────┬────────┘      └──────────────┘
         │
         ↓
┌─────────────────┐
│  Claude API     │
│  (Anthropic)    │
└─────────────────┘
```

### How It Works

1. **Indexing Phase** (via WebSocket)
   - User provides documentation directory path
   - Backend crawls directory for supported file types
   - Calculates MD5 hash for each file to detect changes
   - **Smart incremental indexing:**
     - New files: fully indexed
     - Modified files: old chunks marked deleted, re-indexed
     - Unchanged files: skipped entirely
     - Deleted files: chunks marked as deleted
   - Splits documents into ~1000 token chunks with overlap
   - Generates vector embeddings for semantic search
   - Stores in FAISS with metadata (file path, hash, deleted flag, etc.)
   - Real-time progress updates sent via WebSocket

2. **Query Phase** (via WebSocket)
   - User asks a question via the web UI
   - Query is converted to a vector embedding
   - FAISS finds the 5 most semantically similar chunks (excluding deleted)
   - Chunks are sent as context to Claude API
   - Response streams back in real-time via WebSocket

3. **Smart Updates**
   - File hashes stored in `file_hashes.pkl`
   - MD5 hash comparison detects file changes
   - Only new and modified files are re-indexed
   - Unchanged files skip processing entirely
   - Deleted chunks are soft-deleted (marked, not removed)

## Prerequisites

- Python 3.10+ (3.11 or 3.12 recommended)
- Node.js 18+
- Anthropic API key ([get one here](https://console.anthropic.com/))
- **Windows ARM64 users**: Use WSL2 for best compatibility (see below)

## Windows ARM64 Setup

If you're on Windows ARM64 (Snapdragon/Copilot+ PC), we **strongly recommend using WSL2**:

```bash
# Install WSL2 (PowerShell as Administrator)
wsl --install

# After restart, open Ubuntu and navigate to project
cd /mnt/c/Users/YourUsername/path/to/doc-chat/backend

# Follow the backend setup instructions below
```

**Why WSL2?** Python data science packages (numpy, faiss-cpu, sentence-transformers) have better pre-built wheel support on Linux ARM64 than Windows ARM64. This avoids compilation errors and missing compiler issues.

## Installation

### Backend Setup

```bash
# Clone the repository
git clone https://github.com/yourusername/doc-chat.git
cd doc-chat/backend

# Create virtual environment
python3 -m venv venv

# Activate (Linux/Mac/WSL2)
source venv/bin/activate

# Or activate (Windows CMD - not recommended for ARM64)
venv\Scripts\activate

# Install dependencies
pip install --upgrade pip
pip install -r requirements.txt

# Set up environment variables
cp .env.example .env
# Edit .env and add your ANTHROPIC_API_KEY
```

**requirements.txt:**
```txt
fastapi==0.104.1
uvicorn[standard]==0.24.0
websockets==12.0
anthropic==0.7.8
python-dotenv==1.0.0
tiktoken>=0.7.0
langchain==0.1.0
langchain-community==0.0.10
faiss-cpu==1.13.2
sentence-transformers==2.2.2
numpy>=1.25.0,<2.0
```

### Frontend Setup

```bash
cd ../frontend

# Install dependencies
npm install

# Start development server
npm run dev
```

## Usage

### 1. Start the Backend

```bash
cd backend
source venv/bin/activate  # or venv\Scripts\activate on Windows
python app.py
```

The API server will start on `http://localhost:8000`

### 2. Start the Frontend

```bash
cd frontend
npm run dev
```

The web UI will be available at `http://localhost:5173`

### 3. Index Your Documentation

On first launch, you'll see the indexing screen. Enter the path to your project documentation:

```
/path/to/your/project/docs
```

Or use relative paths:
```
../my-project
./docs
```

The indexer will process:
- Markdown files (`.md`)
- Text files (`.txt`)
- Code files (`.py`, `.js`, `.ts`, `.tsx`, `.cs`)
- JSON files (`.json`)

### 4. Start Chatting

Example queries to try:

- "How does authentication work?"
- "Explain the payment processing flow"
- "What API endpoints are available for user management?"
- "Show me examples of error handling"
- "What's the database schema for orders?"

## Configuration

### Backend Environment Variables

Create a `.env` file in the `backend/` directory:

```bash
# Required
ANTHROPIC_API_KEY=sk-ant-...

# Optional
FAISS_PERSIST_DIR=./data/faiss_db
MAX_CHUNKS_PER_FILE=50
CHUNK_SIZE=1000
CHUNK_OVERLAP=200
```

### Customizing File Types

Edit `backend/indexer.py`:

```python
def _should_index_file(self, filepath: Path) -> bool:
    """Check if file should be indexed"""
    extensions = {
        '.md', '.txt', '.py', '.cs', '.js', '.ts', 
        '.tsx', '.json', '.yaml', '.yml'  # Add more here
    }
    return filepath.suffix.lower() in extensions
```

### Adjusting Chunk Size

Smaller chunks = more precise but less context
Larger chunks = more context but less precise

```python
# In indexer.py
self.text_splitter = RecursiveCharacterTextSplitter(
    chunk_size=1000,      # Adjust this
    chunk_overlap=200,    # And this
    separators=["\n\n", "\n", ". ", " ", ""]
)
```

## Tailwind CSS 4 Note

This project uses **Tailwind CSS 4** with the Vite plugin. No `tailwind.config.js` is needed for basic usage.

**src/index.css:**
```css
@import "tailwindcss";
```

**vite.config.ts:**
```typescript
import tailwindcss from '@tailwindcss/vite'

export default defineConfig({
  plugins: [react(), tailwindcss()],
  // ...
})
```

For custom configuration (optional), create `tailwind.config.ts`:
```typescript
import type { Config } from 'tailwindcss'

export default {
  content: ['./index.html', './src/**/*.{js,ts,jsx,tsx}'],
  theme: {
    extend: {
      colors: {
        primary: '#3b82f6',
      },
    },
  },
} satisfies Config
```

## API Reference

### REST Endpoints

#### POST `/api/index`
Index documents from a directory (legacy endpoint).

**Note:** For long-running indexing operations, use the WebSocket endpoint `/ws/index` instead. This endpoint may timeout on cloud platforms with connection time limits (e.g., Azure's 3.5 minute limit).

**Request:**
```json
{
  "directory": "/path/to/docs"
}
```

**Response:**
```json
{
  "success": true,
  "stats": {
    "files": 42,
    "chunks": 387,
    "new": 10,
    "modified": 5,
    "unchanged": 27,
    "deleted": 2
  }
}
```

#### GET `/api/stats`
Get indexing statistics.

**Response:**
```json
{
  "total_chunks": 387,
  "dimension": 384
}
```

### WebSocket Endpoints

#### WS `/ws/index`
Real-time document indexing with progress updates. Recommended for production use to avoid timeout issues on cloud platforms.

**Send:**
```json
{
  "directory": "/path/to/docs"
}
```

**Receive (multiple progress messages):**

Scan start:
```json
{
  "type": "scan_start",
  "data": {
    "directory": "/path/to/docs"
  }
}
```

File processing:
```json
{
  "type": "file_processing",
  "data": {
    "file": "auth.md",
    "status": "new"
  }
}
```

File processed:
```json
{
  "type": "file_processed",
  "data": {
    "file": "auth.md",
    "chunks": 12
  }
}
```

Embedding generation:
```json
{
  "type": "embedding_start",
  "data": {
    "total_chunks": 387
  }
}
```

Final statistics:
```json
{
  "type": "stats",
  "data": {
    "files": 42,
    "chunks": 387,
    "new": 10,
    "modified": 5,
    "unchanged": 27,
    "deleted": 2
  }
}
```

Completion:
```json
{
  "type": "done",
  "data": {}
}
```

Error (non-fatal):
```json
{
  "type": "error",
  "data": {
    "message": "Failed to process file.txt"
  }
}
```

Fatal error:
```json
{
  "type": "fatal_error",
  "data": {
    "message": "Invalid directory path"
  }
}
```

**Other message types:** `file_skipped`, `file_deleted`, `embedding_complete`, `saving`, `save_complete`

#### WS `/ws/chat`
Real-time chat with streaming responses.

**Send:**
```json
{
  "query": "How does authentication work?"
}
```

**Receive (multiple messages):**

Sources message:
```json
{
  "type": "sources",
  "data": [
    {
      "file": "auth.md",
      "path": "/docs/auth.md",
      "chunk": 0
    }
  ]
}
```

Content chunks (streamed):
```json
{
  "type": "content",
  "data": "Authentication in this system uses..."
}
```

Completion signal:
```json
{
  "type": "done"
}
```

## Project Structure

```
doc-chat/
├── backend/
│   ├── app.py                # FastAPI application & WebSocket
│   ├── indexer.py            # Document ingestion & chunking
│   ├── retriever.py          # Vector search & Claude integration
│   ├── requirements.txt
│   ├── .env.example
│   └── data/
│       └── faiss_db/         # Vector database (auto-created)
├── frontend/
│   ├── src/
│   │   ├── App.tsx           # Main application component
│   │   ├── components/
│   │   │   ├── Chat.tsx      # Chat interface
│   │   │   ├── MessageList.tsx
│   │   │   ├── SourcePanel.tsx
│   │   │   └── IndexStatus.tsx
│   │   ├── hooks/
│   │   │   └── useWebSocket.ts  # WebSocket state management
│   │   └── types/
│   │       └── index.ts      # TypeScript type definitions
│   ├── package.json
│   ├── tailwind.config.js
│   └── vite.config.ts
├── docs/                      # Your documentation (example)
└── README.md
```

## Technology Stack

### Backend
- **FastAPI** - Modern Python web framework
- **FAISS** - Vector database for semantic search
- **LangChain** - Text splitting and document processing
- **Anthropic SDK** - Claude API integration
- **Sentence Transformers** - Embedding generation
- **WebSockets** - Real-time streaming communication

### Frontend
- **React 19** - UI framework
- **TypeScript** - Type-safe JavaScript
- **Vite** - Fast build tool and dev server
- **Tailwind CSS 4** - Modern utility-first styling with Vite plugin
- **Native WebSocket API** - Real-time updates

## Development

### Running Tests

```bash
# Backend tests
cd backend
pytest

# Frontend tests
cd frontend
npm test
```

### Building for Production

```bash
# Frontend production build
cd frontend
npm run build

# Serve with backend
cd ../backend
uvicorn app:app --host 0.0.0.0 --port 8000
```

### Code Quality

```bash
# Python linting
cd backend
flake8 .
black .

# TypeScript linting
cd frontend
npm run lint
npm run format
```

## Troubleshooting

### "No module named 'chromadb'" or similar import errors
```bash
# Make sure you're in the virtual environment
source venv/bin/activate  # Linux/Mac/WSL2
venv\Scripts\activate     # Windows

# Reinstall dependencies
pip install -r requirements.txt
```

### WebSocket connection fails
- Ensure backend is running on port 8000
- Check CORS settings in `app.py`
- Verify frontend is using correct WebSocket URL (`ws://localhost:8000/ws/chat`)

### Empty search results
- Check that documents were indexed: `GET /api/stats`
- Verify file extensions are supported in `indexer.py`
- Try re-indexing: Delete `data/faiss_db/` and re-index

### Out of memory during indexing
- Reduce chunk size in `indexer.py`
- Process directories in smaller batches
- Increase system RAM or use swap space

### Claude API errors
- Verify `ANTHROPIC_API_KEY` is set correctly in `.env`
- Check API usage limits in Anthropic console
- Ensure you're using a supported model name (`claude-sonnet-4-20250514`)

### Windows ARM64 compilation errors
If you get errors about missing compilers or "can't find Rust compiler":
- **Use WSL2** (strongly recommended - see setup section above)
- Or install Visual Studio Build Tools with C++ support (not recommended for this project)
- The WSL2 approach avoids all compilation issues

### Tiktoken Rust compiler error
If you see "can't find Rust compiler" for tiktoken:
- Update to `tiktoken>=0.7.0` which has pre-built wheels
- Or use WSL2 where all packages have proper wheels

## Performance Optimization

### For Large Documentation Sets (1000+ files)

1. **Batch Processing**
```python
# In indexer.py, process in batches
BATCH_SIZE = 100
for i in range(0, len(documents), BATCH_SIZE):
    batch = documents[i:i + BATCH_SIZE]
    # Process batch
```

2. **Parallel Processing**
```python
from concurrent.futures import ThreadPoolExecutor

with ThreadPoolExecutor(max_workers=4) as executor:
    executor.map(self._index_file, filepaths)
```

3. **Metadata Filtering**
```python
# Search only specific file types
results = self.store.search(
    query,
    # Add filtering logic for specific extensions
)
```

## Advanced Features

### Custom Embedding Models

Replace sentence-transformers default model:

```python
# In indexer.py and retriever.py
self.model = SentenceTransformer('all-mpnet-base-v2')  # Larger, more accurate
# or
self.model = SentenceTransformer('paraphrase-MiniLM-L3-v2')  # Smaller, faster
```

### File Watching

Auto-reindex on file changes:

```python
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

class DocChangeHandler(FileSystemEventHandler):
    def on_modified(self, event):
        if event.is_directory:
            return
        # Re-index changed file
        indexer.index_file(event.src_path)

observer = Observer()
observer.schedule(handler, path='./docs', recursive=True)
observer.start()
```

## Security Considerations

- **API Keys**: Never commit `.env` files. Use environment variables in production.
- **Input Validation**: The backend validates file paths to prevent directory traversal.
- **Rate Limiting**: Consider adding rate limits to API endpoints for production use.
- **CORS**: Update `allow_origins` in production to specific domains only.
- **Sandboxing**: Consider running indexing in a sandboxed environment for untrusted documents.

## Roadmap

- [ ] Multi-project support (switch between indexed projects)
- [ ] Export conversation history
- [ ] Support for images/diagrams in documentation
- [ ] Advanced filtering (date ranges, file types, directories)
- [ ] API authentication (JWT tokens)
- [ ] Docker deployment configuration
- [ ] Slack/Discord bot integration
- [ ] VS Code extension

## Contributing

Contributions are welcome! Please:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## License

MIT License - see [LICENSE](LICENSE) file for details

## Acknowledgments

- [Anthropic](https://www.anthropic.com/) for Claude API
- [FAISS](https://github.com/facebookresearch/faiss) for vector similarity search
- [LangChain](https://www.langchain.com/) for document processing utilities
- [FastAPI](https://fastapi.tiangolo.com/) for the excellent web framework
- [Sentence Transformers](https://www.sbert.net/) for embedding generation

## Support

- 📧 Email: hello@iceninemedia.com
- 🐛 Issues: [GitHub Issues](https://github.com/john-mckillip/doc-chat/issues)
- 💬 Discussions: [GitHub Discussions](https://github.com/john-mckillip/doc-chat/discussions)

## Changelog

### v1.0.0 (2025-01-17)
- Initial release
- Basic indexing and chat functionality
- WebSocket streaming support
- Source citation panel
- FAISS vector database integration
- React 19 + TypeScript frontend
- Tailwind CSS 4 styling

---

Made with ❤️ by John McKillip | Ice Nine Media