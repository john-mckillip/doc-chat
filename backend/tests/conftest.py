"""
Shared pytest fixtures for testing the DocChat backend.

This file sets up mocks for heavy dependencies (sentence-transformers, faiss, anthropic)
BEFORE they are imported, to avoid slow initialization during tests.
"""
import sys
import pytest
import numpy as np
from pathlib import Path
from unittest.mock import Mock
import tempfile
import shutil


# ============================================================================
# Mock heavy dependencies BEFORE importing application code
# ============================================================================

# Mock sentence_transformers module
class MockSentenceTransformer:
    """Mock SentenceTransformer class."""
    def __init__(self, *args, **kwargs):
        pass

    def encode(self, texts, show_progress_bar=False, convert_to_numpy=True):
        """Return fixed embeddings (384 dimensions)."""
        if isinstance(texts, str):
            texts = [texts]
        return np.random.rand(len(texts), 384).astype('float32')


# Mock faiss module
class MockFaissIndex:
    """Mock FAISS index."""
    def __init__(self):
        self.ntotal = 0
        self.d = 384
        self._vectors = []

    def add(self, vectors):
        """Mock adding vectors to index."""
        self._vectors.extend(vectors)
        self.ntotal = len(self._vectors)

    def search(self, query_vector, k):
        """Mock search returning dummy results."""
        n = min(k, self.ntotal) if self.ntotal > 0 else 0
        distances = np.array([[0.1] * n])
        indices = np.array([[i for i in range(n)]])
        return distances, indices


class MockFaiss:
    """Mock faiss module."""
    METRIC_L2 = 0

    @staticmethod
    def IndexFlatL2(d):
        """Create a mock flat L2 index."""
        index = MockFaissIndex()
        index.d = d
        return index

    @staticmethod
    def read_index(filename):
        """Mock reading an index from disk."""
        index = MockFaissIndex()
        index.ntotal = 0
        return index

    @staticmethod
    def write_index(index, filename):
        """Mock writing an index to disk."""
        pass


# Install mocks in sys.modules BEFORE any imports
mock_st_module = type(sys)('sentence_transformers')
mock_st_module.SentenceTransformer = MockSentenceTransformer
sys.modules['sentence_transformers'] = mock_st_module

mock_faiss_module = type(sys)('faiss')
for attr in dir(MockFaiss):
    if not attr.startswith('_'):
        setattr(mock_faiss_module, attr, getattr(MockFaiss, attr))
sys.modules['faiss'] = mock_faiss_module


# ============================================================================
# Pytest Fixtures
# ============================================================================

@pytest.fixture
def temp_dir():
    """Create a temporary directory for testing."""
    tmp = tempfile.mkdtemp()
    yield Path(tmp)
    shutil.rmtree(tmp)


@pytest.fixture
def sample_docs(temp_dir):
    """Create sample documentation files for testing."""
    docs = {
        "readme.md": "# Test Project\n\nThis is a test project for documentation.",
        "api.md": "# API Documentation\n\n## Endpoints\n\n### GET /api/test\n\nReturns test data.",
        "guide.txt": "Installation Guide\n\n1. Install Python\n2. Run pip install",
        "code.py": "def hello():\n    return 'Hello, World!'\n\nprint(hello())",
        "config.json": '{"name": "test", "version": "1.0.0"}',
        "empty.md": "",
        "binary.png": b"\x89PNG\r\n\x1a\n",  # Binary file (should be skipped)
    }

    for filename, content in docs.items():
        filepath = temp_dir / filename
        if isinstance(content, bytes):
            filepath.write_bytes(content)
        else:
            filepath.write_text(content, encoding='utf-8')

    return temp_dir


@pytest.fixture
def mock_anthropic_client(mocker):
    """Mock Anthropic client for LLM interactions."""
    mock_client = Mock()

    # Mock streaming response
    class MockStream:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            pass

        @property
        def text_stream(self):
            return iter(["Hello", " ", "world", "!"])

    mock_client.messages.stream = Mock(return_value=MockStream())

    mocker.patch('anthropic.Anthropic', return_value=mock_client)

    return mock_client


@pytest.fixture
def mock_env_vars(mocker):
    """Mock environment variables."""
    mocker.patch.dict('os.environ', {
        'ANTHROPIC_API_KEY': 'test-api-key-123',
        'FAISS_PERSIST_DIR': './test_data/faiss_db'
    })


@pytest.fixture
def indexer_with_data(temp_dir):
    """Create an indexer with pre-indexed sample data."""
    from indexer import DocumentIndexer

    indexer = DocumentIndexer(persist_directory=str(temp_dir / "faiss_db"))

    # Simulate some indexed data
    indexer.metadata = [
        {
            "file_path": "/test/doc1.md",
            "file_name": "doc1.md",
            "chunk_index": 0,
            "hash": "abc123",
            "extension": ".md",
            "deleted": False
        },
        {
            "file_path": "/test/doc2.md",
            "file_name": "doc2.md",
            "chunk_index": 0,
            "hash": "def456",
            "extension": ".md",
            "deleted": True  # Deleted chunk
        }
    ]
    indexer.texts = ["First document text", "Second document text (deleted)"]
    indexer.file_hashes = {
        "/test/doc1.md": "abc123",
        "/test/doc2.md": "def456"
    }
    indexer.index.ntotal = 2

    return indexer


@pytest.fixture
def retriever_with_index(temp_dir, mock_anthropic_client):
    """Create a retriever with a pre-loaded index."""
    import pickle
    from retriever import DocumentRetriever

    # Create index directory
    faiss_dir = temp_dir / "faiss_db"
    faiss_dir.mkdir(parents=True, exist_ok=True)

    # Create test metadata and texts
    metadata = [
        {
            "file_path": "/test/auth.md",
            "file_name": "auth.md",
            "chunk_index": 0,
            "deleted": False
        },
        {
            "file_path": "/test/api.md",
            "file_name": "api.md",
            "chunk_index": 0,
            "deleted": False
        }
    ]
    texts = [
        "Authentication uses JWT tokens for secure access.",
        "API endpoints are available at /api/v1/"
    ]

    # Since faiss is mocked, manually create dummy index file
    (faiss_dir / "index.faiss").touch()

    with open(faiss_dir / "metadata.pkl", 'wb') as f:
        pickle.dump(metadata, f)

    with open(faiss_dir / "texts.pkl", 'wb') as f:
        pickle.dump(texts, f)

    # Now create retriever - it will load the files we just created
    retriever = DocumentRetriever(persist_directory=str(faiss_dir))

    return retriever
