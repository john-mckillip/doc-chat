from dataclasses import dataclass
from typing import List
import os


def _parse_csv(value: str) -> List[str]:
    return [item.strip() for item in value.split(",") if item.strip()]


@dataclass(frozen=True)
class BackendSettings:
    ollama_host: str
    ollama_model: str
    faiss_persist_dir: str
    sentence_transformer_model: str
    max_tokens: int
    chunk_size: int
    chunk_overlap: int
    embedding_batch_size: int
    embedding_cpu_batch_size: int
    embedding_max_workers: int
    file_io_workers: int
    min_chunks_for_multiprocess: int
    index_file_types: List[str]
    cors_origins: List[str]


def get_backend_settings() -> BackendSettings:
    cors_origins = _parse_csv(
        os.getenv("CORS_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173")
    )

    return BackendSettings(
        ollama_host=os.getenv("OLLAMA_HOST", "http://localhost:11434"),
        ollama_model=os.getenv("OLLAMA_MODEL", "llama3.1:8b"),
        faiss_persist_dir=os.getenv("FAISS_PERSIST_DIR", "./data/faiss_db"),
        sentence_transformer_model=os.getenv(
            "SENTENCE_TRANSFORMER_MODEL",
            "all-MiniLM-L6-v2",
        ),
        max_tokens=int(os.getenv("MAX_TOKENS", "4096")),
        chunk_size=int(os.getenv("CHUNK_SIZE", "1000")),
        chunk_overlap=int(os.getenv("CHUNK_OVERLAP", "200")),
        embedding_batch_size=int(os.getenv("EMBEDDING_BATCH_SIZE", "64")),
        embedding_cpu_batch_size=int(os.getenv("EMBEDDING_CPU_BATCH_SIZE", "32")),
        embedding_max_workers=int(os.getenv("EMBEDDING_MAX_WORKERS", "4")),
        file_io_workers=int(os.getenv("FILE_IO_WORKERS", "8")),
        min_chunks_for_multiprocess=int(
            os.getenv("MIN_CHUNKS_FOR_MULTIPROCESS", "999999")
        ),
        index_file_types=_parse_csv(
            os.getenv(
                "INDEX_FILE_TYPES",
                ".md,.txt,.py,.cs,.js,.ts,.tsx,.json,.yaml,.yml",
            )
        ),
        cors_origins=cors_origins,
    )
