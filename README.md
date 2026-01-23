# DocChat - AI-Powered Documentation Assistant

A local development tool that lets you chat with your project documentation using AI and semantic search. Ask questions in natural language and get real-time streaming responses with source citations.

## Features

- 🔍 **Semantic Search** - Find relevant documentation based on meaning, not just keywords
- 💬 **Real-time Streaming** - See responses as they're generated via WebSocket
- 📚 **Source Citations** - Know exactly which files informed each answer
- 🧠 **Conversation Memory** - Follow-up questions maintain context
- ⚡ **Smart Incremental Indexing** - MD5 hash tracking only re-indexes new/changed files
- 🚀 **GPU-Accelerated Indexing** - Automatic CUDA detection for 6-10x faster embedding generation
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

# Optional - Vector Database
FAISS_PERSIST_DIR=./data/faiss_db                    # Directory to persist FAISS index

# Optional - Text Chunking
CHUNK_SIZE=1000                                       # Size of text chunks for indexing
CHUNK_OVERLAP=200                                     # Overlap between consecutive chunks

# Optional - Embedding Model
SENTENCE_TRANSFORMER_MODEL=all-MiniLM-L6-v2          # Sentence transformer model name

# Optional - File Types
INDEX_FILE_TYPES=.md,.txt,.py,.cs,.js,.ts,.tsx,.json,.yaml,.yml  # Comma-separated file extensions to index

# Optional - AI Response Length
MAX_TOKENS=16384                                      # Maximum tokens in AI responses (default: 16384, max: 200000)

# Optional - Embedding Performance (see Performance Optimization section)
EMBEDDING_BATCH_SIZE=64        # Batch size for GPU encoding
EMBEDDING_CPU_BATCH_SIZE=32    # Batch size for CPU encoding
EMBEDDING_MAX_WORKERS=4        # Number of CPU workers for multiprocessing
FILE_IO_WORKERS=8              # Workers for parallel file reading
MIN_CHUNKS_FOR_MULTIPROCESS=999999  # Chunk threshold to enable CPU multiprocessing (default: disabled)
```

### Customizing File Types

You can customize which file types to index by setting the `INDEX_FILE_TYPES` environment variable in your `.env` file:

```bash
# Add more file extensions (comma-separated)
INDEX_FILE_TYPES=.md,.txt,.py,.cs,.js,.ts,.tsx,.json,.yaml,.yml,.java,.cpp,.go
```

Alternatively, you can edit `backend/indexer.py` directly:

```python
def _should_index_file(self, filepath: Path) -> bool:
    """Check if file should be indexed"""
    file_types = os.getenv("INDEX_FILE_TYPES", ".md,.txt,.py,.cs,.js,.ts,.tsx,.json,.yaml,.yml")
    extensions = {ext.strip() for ext in file_types.split(',')}
    return filepath.suffix.lower() in extensions
```

### Adjusting Chunk Size

Smaller chunks = more precise but less context
Larger chunks = more context but less precise

You can adjust chunk size and overlap via environment variables in your `.env` file:

```bash
# Smaller chunks for more precise results
CHUNK_SIZE=500
CHUNK_OVERLAP=100

# Larger chunks for more context
CHUNK_SIZE=2000
CHUNK_OVERLAP=400
```

Alternatively, you can edit `backend/indexer.py` directly:

```python
# In indexer.py
self.text_splitter = RecursiveCharacterTextSplitter(
    chunk_size=int(os.getenv("CHUNK_SIZE", 1000)),
    chunk_overlap=int(os.getenv("CHUNK_OVERLAP", 200)),
    separators=["\n\n", "\n", ". ", " ", ""]
)
```

### Adjusting AI Response Length

If AI responses are getting cut off, you can increase the maximum token limit via the `MAX_TOKENS` environment variable in your `.env` file:

```bash
# Default (approximately 12,000-16,000 words)
MAX_TOKENS=16384

# For longer responses (approximately 24,000-32,000 words)
MAX_TOKENS=32768

# Maximum supported by Claude Sonnet 4
MAX_TOKENS=200000
```

The Claude Sonnet 4 model supports up to 200,000 output tokens, so you can set this as high as needed. Each token is roughly 3/4 of a word on average.

**Note:** Higher values may increase API costs and response times, but ensure complete responses for complex questions.

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

#### GET `/api/indexed-files`
Get detailed information about all indexed files.

**Response:**
```json
{
  "total_files": 42,
  "files": [
    {
      "file_path": "/path/to/docs/auth.md",
      "file_name": "auth.md",
      "extension": ".md",
      "chunk_count": 12,
      "hash": "5d41402abc4b2a76b9719d911017c592"
    },
    {
      "file_path": "/path/to/docs/api.md",
      "file_name": "api.md",
      "extension": ".md",
      "chunk_count": 8,
      "hash": "7d793037a0760186574b0282f2f435e7"
    }
  ]
}
```

**Use this endpoint to:**
- Debug indexing issues (verify expected files are indexed)
- View which files are in the vector database
- Check chunk counts per file
- Verify file hashes for change detection

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
    "total_chunks": 387,
    "device": "cuda:0",
    "batch_size": 64
  }
}
```

Embedding progress (batched):
```json
{
  "type": "embedding_progress",
  "data": {
    "processed": 128,
    "total": 387,
    "percent": 33
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

**Other message types:** `file_skipped`, `file_deleted`, `embedding_progress`, `embedding_info`, `embedding_complete`, `saving`, `save_complete`

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
- View which files are indexed: `GET /api/indexed-files`
- Verify file extensions are supported (check `INDEX_FILE_TYPES` in `.env`)
- Try re-indexing: Delete `data/faiss_db/` and re-index

### AI responses getting cut off
- Increase `MAX_TOKENS` in your `.env` file (default: 16384, max: 200000)
- See the "Adjusting AI Response Length" section for details
- Restart your backend server after changing `.env`

### Out of memory during indexing
- Reduce embedding batch size: `EMBEDDING_BATCH_SIZE=16` (for GPU) or `EMBEDDING_CPU_BATCH_SIZE=16` (for CPU)
- Reduce chunk size in `indexer.py`
- Process directories in smaller batches
- Increase system RAM or use swap space

### GPU not being used
- Verify CUDA is available: `python -c "import torch; print(torch.cuda.is_available())"`
- Install PyTorch with CUDA support: `pip install torch --index-url https://download.pytorch.org/whl/cu118`
- Check GPU memory: Large batch sizes may exceed VRAM, try `EMBEDDING_BATCH_SIZE=16`

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

### Automatic GPU/CPU Optimization

The indexer automatically detects and uses the best available hardware:

- **GPU (CUDA)**: If a CUDA-compatible GPU is available, embeddings are generated on the GPU with ~6-10x speedup
- **CPU Multiprocessing**: On CPU-only systems, embeddings are generated in parallel across multiple cores with ~3-4x speedup

You'll see the device being used in the console output:
```
Loading embedding model...
Using GPU: NVIDIA GeForce RTX 3080
```
or
```
Loading embedding model...
No GPU available, using CPU with multiprocessing
```

### Tuning Performance

Adjust embedding performance via environment variables:

| Variable | Default | Description |
|----------|---------|-------------|
| `EMBEDDING_BATCH_SIZE` | 64 | Batch size for GPU encoding. Reduce to 16-32 for GPUs with <4GB VRAM |
| `EMBEDDING_CPU_BATCH_SIZE` | 32 | Batch size for CPU encoding |
| `EMBEDDING_MAX_WORKERS` | 4 | Number of CPU processes for multiprocessing |
| `FILE_IO_WORKERS` | 8 | Workers for parallel file reading |
| `MIN_CHUNKS_FOR_MULTIPROCESS` | 999999 | Chunk threshold to enable CPU multiprocessing. Set to 500-1000 on native Linux for large datasets. Disabled by default due to noisy output on WSL2/Windows |

**Performance by dataset size:**

| Chunks | GPU Time | CPU Time (4 cores) |
|--------|----------|-------------------|
| 100 | ~1s | ~3s |
| 1,000 | ~5s | ~20s |
| 10,000 | ~50s | ~200s |

### For Large Documentation Sets (1000+ files)

The indexer handles large datasets efficiently with:

1. **Batched Embedding Generation** - Processes chunks in configurable batches to control memory usage
2. **Progress Callbacks** - Real-time updates during embedding generation via WebSocket
3. **Smart Change Detection** - Only re-indexes new/modified files using MD5 hashes

### Metadata Filtering
```python
# Search only specific file types
results = self.store.search(
    query,
    # Add filtering logic for specific extensions
)
```

## Advanced Features

### Custom Embedding Models

You can use different sentence transformer models by setting the `SENTENCE_TRANSFORMER_MODEL` environment variable in your `.env` file:

```bash
# Larger, more accurate model
SENTENCE_TRANSFORMER_MODEL=all-mpnet-base-v2

# Smaller, faster model
SENTENCE_TRANSFORMER_MODEL=paraphrase-MiniLM-L3-v2

# Default model (if not set)
SENTENCE_TRANSFORMER_MODEL=all-MiniLM-L6-v2
```

**Note:** When changing the embedding model, you'll need to re-index your documents as different models produce embeddings of different dimensions and characteristics.

Alternatively, you can edit `backend/indexer.py` and `backend/retriever.py` directly:

```python
# In indexer.py and retriever.py
self.model = SentenceTransformer(os.getenv("SENTENCE_TRANSFORMER_MODEL", "all-MiniLM-L6-v2"))
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

### v1.2.0 (2025-01-22)
**Performance Optimization**
- Automatic GPU detection and CUDA acceleration for embedding generation (6-10x speedup)
- CPU multiprocessing for embedding generation on systems without GPU (3-4x speedup)
- Batched embedding with configurable batch sizes and real-time progress updates
- New environment variables for tuning embedding performance (`EMBEDDING_BATCH_SIZE`, `EMBEDDING_MAX_WORKERS`, etc.)
- Added directory/file exclusions for indexing (node_modules, bin, obj, etc.)

### v1.1.0 (2025-01-18)
**Configuration & Debugging Improvements**
- Added configurable `MAX_TOKENS` environment variable for AI response length (fixes response cutoff issues)
- Increased default max tokens from 8,192 to 16,384 (can be set up to 200,000)
- Added `/api/indexed-files` REST endpoint for debugging indexing issues
- Made indexer fully configurable via environment variables:
  - `CHUNK_SIZE` - Size of text chunks for indexing (default: 1000)
  - `CHUNK_OVERLAP` - Overlap between chunks (default: 200)
  - `SENTENCE_TRANSFORMER_MODEL` - Embedding model selection (default: all-MiniLM-L6-v2)
  - `INDEX_FILE_TYPES` - File extensions to index (default: .md,.txt,.py,.cs,.js,.ts,.tsx,.json,.yaml,.yml)
  - `FAISS_PERSIST_DIR` - Vector database location (default: ./data/faiss_db)

**Code Quality**
- Refactored `indexer.py` to reduce cyclomatic complexity from 28 to under 10
- Added 6 new helper methods with single-responsibility design:
  - `_get_file_status()` - Determine if file is new, modified, or unchanged
  - `_process_single_file()` - Process individual file and create chunks
  - `_process_deleted_files()` - Handle deleted file tracking
  - `_add_documents_to_index()` - Generate embeddings and index documents
  - `_scan_and_process_files()` - Scan directory for eligible files
  - `_finalize_indexing()` - Complete indexing and print summary
- Fixed all flake8 errors (E722, E501, C901)
- Added flake8 configuration file with project-specific rules
- Fixed bare `except` clause in app.py (now catches `Exception`)

**Testing**
- Added comprehensive test coverage for refactored helper methods (11 new tests)
- Added tests for `/api/indexed-files` endpoint
- Removed coverage files from git tracking (.coverage, htmlcov/, coverage.xml)
- Updated CI/CD pipeline to trigger on feature branches
- Achieved 97% test coverage on indexer.py

**Documentation**
- Enhanced README with:
  - Configuration examples for all environment variables
  - Troubleshooting section for AI response cutoffs
  - Documentation of new `/api/indexed-files` endpoint
  - "Adjusting AI Response Length" section with usage examples
- Updated `.env.example` with all configurable options and helpful comments

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