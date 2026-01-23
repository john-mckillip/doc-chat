from pathlib import Path
from typing import Dict, Callable, Optional, List
import numpy as np
import faiss
from sentence_transformers import SentenceTransformer
from langchain.text_splitter import RecursiveCharacterTextSplitter
import hashlib
import pickle
import torch
import os

# Embedding configuration - can be overridden via environment variables
DEFAULT_BATCH_SIZE = int(os.environ.get("EMBEDDING_BATCH_SIZE", "64"))  # GPU batch size
CPU_BATCH_SIZE = int(os.environ.get("EMBEDDING_CPU_BATCH_SIZE", "32"))  # Smaller for CPU
MAX_CPU_WORKERS = int(os.environ.get("EMBEDDING_MAX_WORKERS", "4"))     # For CPU multiprocessing
FILE_IO_WORKERS = int(os.environ.get("FILE_IO_WORKERS", "8"))          # For parallel file reading
# CPU multiprocessing threshold - disabled by default (999999) because it causes
# noisy output on WSL2/Windows due to process spawning re-importing modules.
# Set to a lower value (e.g., 500) via env var to enable for large datasets on native Linux.
MIN_CHUNKS_FOR_MULTIPROCESS = int(os.environ.get("MIN_CHUNKS_FOR_MULTIPROCESS", "999999"))

# Directory and file exclusions for indexing
EXCLUDED_DIRS = {
    'node_modules', 'bin', 'obj', 'packages', 'dist', 'build',
    '.git', '.vs', '.vscode', '.idea', 'wwwroot',
    '__pycache__', '.pytest_cache', 'venv', 'env', '.env',
    'coverage', '.coverage', 'htmlcov',
    'TestResults', 'logs'
}

EXCLUDED_FILES = {
    'package-lock.json', 'yarn.lock', 'packages.lock.json',
    'pnpm-lock.yaml', '.DS_Store', 'Thumbs.db'
}


class DocumentIndexer:
    def __init__(self, persist_directory: str = "./data/faiss_db"):
        self.persist_directory = Path(persist_directory)
        self.persist_directory.mkdir(parents=True, exist_ok=True)
        self.index_file = self.persist_directory / "index.faiss"
        self.metadata_file = self.persist_directory / "metadata.pkl"
        self.texts_file = self.persist_directory / "texts.pkl"
        self.file_hashes_file = self.persist_directory / "file_hashes.pkl"

        # Load embedding model
        print("Loading embedding model...")
        self.model = SentenceTransformer(
            os.getenv("SENTENCE_TRANSFORMER_MODEL", "all-MiniLM-L6-v2"))
        self.dimension = 384  # all-MiniLM-L6-v2 dimension

        # Detect optimal device and configure for performance
        self.device = self._detect_device()
        if self.device != "cpu":
            self.model.to(self.device)

        # Configure batch size based on device
        self.batch_size = DEFAULT_BATCH_SIZE if self.device.startswith('cuda') else CPU_BATCH_SIZE
        self.use_multiprocess = self.device == "cpu"

        # Load or create FAISS index
        if self.index_file.exists():
            self.index = faiss.read_index(str(self.index_file))
            with open(self.metadata_file, 'rb') as f:
                self.metadata = pickle.load(f)
            with open(self.texts_file, 'rb') as f:
                self.texts = pickle.load(f)
        else:
            self.index = faiss.IndexFlatL2(self.dimension)
            self.metadata = []
            self.texts = []

        # Load file hashes for incremental indexing
        if self.file_hashes_file.exists():
            with open(self.file_hashes_file, 'rb') as f:
                self.file_hashes = pickle.load(f)
        else:
            self.file_hashes = {}

        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=int(os.getenv("CHUNK_SIZE", 1000)),
            chunk_overlap=int(os.getenv("CHUNK_OVERLAP", 200)),
            separators=["\n\n", "\n", ". ", " ", ""]
        )

    def _get_file_hash(self, filepath: Path) -> str:
        with open(filepath, 'rb') as f:
            return hashlib.md5(f.read()).hexdigest()

    def _should_index_file(self, filepath: Path) -> bool:
        """Check if a file should be indexed based on extension and exclusions."""
        # Check if file is in excluded files list
        if filepath.name in EXCLUDED_FILES:
            return False

        # Check if any parent directory is excluded
        for part in filepath.parts:
            if part in EXCLUDED_DIRS:
                return False

        # Check extension (configurable via INDEX_FILE_TYPES env var)
        file_types = os.getenv("INDEX_FILE_TYPES", ".md,.txt,.py,.cs,.js,.ts,.tsx,.json,.yaml,.yml")
        extensions = {ext.strip() for ext in file_types.split(',')}
        return filepath.suffix.lower() in extensions

    def _get_existing_hash(self, filepath: Path) -> str:
        """Get stored hash for a file, or None if not indexed"""
        return self.file_hashes.get(str(filepath))

    def _mark_file_chunks_deleted(self, filepath: Path):
        """Mark all chunks from a file as deleted"""
        filepath_str = str(filepath)
        for metadata in self.metadata:
            if metadata.get('file_path') == filepath_str and not metadata.get('deleted', False):
                metadata['deleted'] = True

    def _save(self):
        """Save index and metadata to disk"""
        faiss.write_index(self.index, str(self.index_file))
        with open(self.metadata_file, 'wb') as f:
            pickle.dump(self.metadata, f)
        with open(self.texts_file, 'wb') as f:
            pickle.dump(self.texts, f)
        with open(self.file_hashes_file, 'wb') as f:
            pickle.dump(self.file_hashes, f)

    def _detect_device(self) -> str:
        """Detect the optimal device for embedding computation."""
        if torch.cuda.is_available():
            device = "cuda:0"
            print(f"Using GPU: {torch.cuda.get_device_name(0)}")
            return device
        else:
            print("No GPU available, using CPU with multiprocessing")
            return "cpu"

    def _encode_in_batches(
        self,
        texts: List[str],
        progress_callback: Optional[Callable] = None
    ) -> np.ndarray:
        """
        Encode texts in batches with progress reporting.

        Uses GPU if available, otherwise falls back to multiprocessing on CPU.
        """
        total_texts = len(texts)

        # Use multiprocessing for large datasets on CPU
        if self.use_multiprocess and total_texts >= MIN_CHUNKS_FOR_MULTIPROCESS:
            return self._encode_multiprocess(texts, progress_callback)

        # Single-process batched encoding (GPU or small CPU workloads)
        all_embeddings = []
        processed = 0

        for i in range(0, total_texts, self.batch_size):
            batch = texts[i:i + self.batch_size]

            batch_embeddings = self.model.encode(
                batch,
                batch_size=self.batch_size,
                show_progress_bar=False,
                convert_to_numpy=True,
                device=self.device
            )

            all_embeddings.append(batch_embeddings)
            processed += len(batch)

            if progress_callback:
                progress_callback({
                    "type": "embedding_progress",
                    "data": {
                        "processed": processed,
                        "total": total_texts,
                        "percent": int((processed / total_texts) * 100)
                    }
                })

        return np.vstack(all_embeddings)

    def _encode_multiprocess(
        self,
        texts: List[str],
        progress_callback: Optional[Callable] = None
    ) -> np.ndarray:
        """
        Encode texts using multiple CPU processes.

        Uses sentence-transformers built-in multiprocessing support for
        significant speedup on CPU-only systems.
        """
        import multiprocessing

        # Determine number of workers (leave one core for main process)
        num_workers = min(MAX_CPU_WORKERS, max(1, multiprocessing.cpu_count() - 1))

        if progress_callback:
            progress_callback({
                "type": "embedding_info",
                "data": {"message": f"Using {num_workers} CPU workers for parallel encoding"}
            })

        # Create pool and encode
        pool = self.model.start_multi_process_pool(target_devices=["cpu"] * num_workers)

        try:
            embeddings = self.model.encode_multi_process(
                texts,
                pool,
                batch_size=self.batch_size
            )

            if progress_callback:
                progress_callback({
                    "type": "embedding_progress",
                    "data": {
                        "processed": len(texts),
                        "total": len(texts),
                        "percent": 100
                    }
                })

            return embeddings

        finally:
            self.model.stop_multi_process_pool(pool)

    def _get_file_status(self, filepath: Path, file_hash: str) -> tuple[str, bool]:
        """
        Determine if a file is new, modified, or unchanged.

        Args:
            filepath: Path to the file
            file_hash: Current hash of the file

        Returns:
            Tuple of (status, should_skip) where:
            - status is "new", "modified", or "unchanged"
            - should_skip is True if file should be skipped (unchanged)
        """
        existing_hash = self._get_existing_hash(filepath)

        if existing_hash is None:
            return ("new", False)
        elif existing_hash != file_hash:
            self._mark_file_chunks_deleted(filepath)
            return ("modified", False)
        else:
            return ("unchanged", True)

    def _process_single_file(
        self,
        filepath: Path,
        content: str,
        file_hash: str,
        file_status: str,
        progress_callback: Optional[Callable] = None
    ) -> list[Dict]:
        """
        Process a single file and create document chunks.

        Args:
            filepath: Path to the file
            content: File content
            file_hash: Hash of the file
            file_status: Status of the file ("new" or "modified")
            progress_callback: Optional callback for progress updates

        Returns:
            List of document dictionaries with text and metadata
        """
        filepath_str = str(filepath)

        # Notify about file processing
        if progress_callback:
            progress_callback({
                "type": "file_processing",
                "data": {"file": filepath.name, "status": file_status}
            })

        # Split text into chunks
        chunks = self.text_splitter.split_text(content)

        # Create documents
        documents = []
        for i, chunk in enumerate(chunks):
            documents.append({
                "text": chunk,
                "metadata": {
                    "file_path": filepath_str,
                    "file_name": filepath.name,
                    "chunk_index": i,
                    "hash": file_hash,
                    "extension": filepath.suffix,
                    "deleted": False
                }
            })

        # Update hash in tracking
        self.file_hashes[filepath_str] = file_hash

        # Log and notify completion
        status_text = 'Added' if file_status == 'new' else 'Updated'
        print(f"{status_text}: {filepath.name} ({len(chunks)} chunks)")

        if progress_callback:
            progress_callback({
                "type": "file_processed",
                "data": {
                    "file": filepath.name,
                    "chunks": len(chunks),
                    "status": file_status
                }
            })

        return documents

    def _process_deleted_files(
        self,
        current_files: set,
        progress_callback: Optional[Callable] = None
    ) -> int:
        """
        Mark chunks from deleted files and remove from tracking.

        Args:
            current_files: Set of current file paths as strings
            progress_callback: Optional callback for progress updates

        Returns:
            Number of files deleted
        """
        deleted_count = 0

        for filepath_str in list(self.file_hashes.keys()):
            if filepath_str not in current_files:
                self._mark_file_chunks_deleted(Path(filepath_str))
                del self.file_hashes[filepath_str]
                deleted_count += 1
                print(f"Removed: {Path(filepath_str).name}")

                if progress_callback:
                    progress_callback({
                        "type": "file_deleted",
                        "data": {"file": Path(filepath_str).name}
                    })

        return deleted_count

    def _add_documents_to_index(
        self,
        documents: list[Dict],
        progress_callback: Optional[Callable] = None
    ):
        """
        Generate embeddings and add documents to the FAISS index.

        Args:
            documents: List of document dictionaries with text and metadata
            progress_callback: Optional callback for progress updates
        """
        if not documents:
            return

        print(f"\nGenerating embeddings for {len(documents)} chunks...")
        if progress_callback:
            progress_callback({
                "type": "embedding_start",
                "data": {
                    "total_chunks": len(documents),
                    "device": self.device,
                    "batch_size": self.batch_size
                }
            })

        # Generate embeddings using optimized batched encoding
        texts = [d["text"] for d in documents]
        embeddings = self._encode_in_batches(texts, progress_callback)

        if progress_callback:
            progress_callback({
                "type": "embedding_complete",
                "data": {"total_chunks": len(documents)}
            })

        # Add to index
        if progress_callback:
            progress_callback({"type": "saving", "data": {}})

        self.index.add(np.array(embeddings).astype('float32'))
        self.metadata.extend([d["metadata"] for d in documents])
        self.texts.extend(texts)

        # Save to disk
        self._save()

        if progress_callback:
            progress_callback({"type": "save_complete", "data": {}})

    def _scan_and_process_files(
        self,
        docs_path: Path,
        current_files: set,
        stats: Dict[str, int],
        progress_callback: Optional[Callable] = None
    ) -> list[Dict]:
        """
        Scan directory and process all eligible files.

        Args:
            docs_path: Path to directory to scan
            current_files: Set to populate with current file paths
            stats: Statistics dictionary to update
            progress_callback: Optional callback for progress updates

        Returns:
            List of all document chunks from processed files
        """
        documents = []

        for filepath in docs_path.rglob("*"):
            if not (filepath.is_file() and self._should_index_file(filepath)):
                continue

            filepath_str = str(filepath)
            current_files.add(filepath_str)

            try:
                # Read file content
                with open(filepath, 'r', encoding='utf-8') as f:
                    content = f.read()

                if not content.strip():
                    continue

                # Determine file status
                file_hash = self._get_file_hash(filepath)
                file_status, should_skip = self._get_file_status(
                    filepath,
                    file_hash
                )

                # Update stats
                stats[file_status] += 1

                # Skip unchanged files
                if should_skip:
                    if progress_callback:
                        progress_callback({
                            "type": "file_skipped",
                            "data": {
                                "file": filepath.name,
                                "status": "unchanged"
                            }
                        })
                    continue

                # Process file and collect documents
                file_docs = self._process_single_file(
                    filepath,
                    content,
                    file_hash,
                    file_status,
                    progress_callback
                )
                documents.extend(file_docs)

                # Update stats
                stats["files"] += 1
                stats["chunks"] += len(file_docs)

            except Exception as e:
                print(f"Error indexing {filepath}: {e}")
                if progress_callback:
                    progress_callback({
                        "type": "error",
                        "data": {
                            "file": filepath.name,
                            "message": str(e)
                        }
                    })

        return documents

    def _finalize_indexing(
        self,
        documents: list[Dict],
        stats: Dict[str, int],
        progress_callback: Optional[Callable] = None
    ):
        """
        Add documents to index and print summary.

        Args:
            documents: List of documents to add
            stats: Statistics dictionary
            progress_callback: Optional callback for progress updates
        """
        if documents:
            self._add_documents_to_index(documents, progress_callback)
            print(
                f"✓ Processed {stats['files']} files "
                f"({stats['new']} new, {stats['modified']} modified, "
                f"{stats['unchanged']} unchanged)"
            )
            if stats['deleted'] > 0:
                print(f"  Removed {stats['deleted']} deleted files")
        else:
            if stats['unchanged'] > 0:
                print(
                    f"✓ No changes detected "
                    f"({stats['unchanged']} files unchanged)"
                )
            else:
                print("No documents found to index")

            # Still save to persist any deletions
            if stats['deleted'] > 0:
                if progress_callback:
                    progress_callback({"type": "saving", "data": {}})
                self._save()
                if progress_callback:
                    progress_callback({"type": "save_complete", "data": {}})

    def index_directory(
        self,
        directory: str,
        progress_callback: Optional[Callable] = None
    ) -> Dict[str, int]:
        """
        Index all eligible files in a directory.

        Args:
            directory: Path to directory to index
            progress_callback: Optional callback for progress updates

        Returns:
            Dictionary with indexing statistics
        """
        docs_path = Path(directory)
        stats = {
            "files": 0,
            "chunks": 0,
            "new": 0,
            "modified": 0,
            "unchanged": 0,
            "deleted": 0
        }

        print(f"Smart indexing directory: {directory}")
        if progress_callback:
            progress_callback({
                "type": "scan_start",
                "data": {"directory": directory}
            })

        # Track which files we've seen
        current_files = set()

        # Scan and process all files
        documents = self._scan_and_process_files(
            docs_path,
            current_files,
            stats,
            progress_callback
        )

        # Handle deleted files
        stats["deleted"] = self._process_deleted_files(
            current_files,
            progress_callback
        )

        # Add documents to index and report
        self._finalize_indexing(documents, stats, progress_callback)

        # Send final stats
        if progress_callback:
            progress_callback({"type": "stats", "data": stats})

        return stats

    def get_stats(self) -> Dict:
        # Count only non-deleted chunks
        active_chunks = sum(1 for m in self.metadata if not m.get('deleted', False))
        return {
            "total_chunks": active_chunks,
            "dimension": self.dimension
        }

    def get_indexed_files(self) -> Dict:
        """Get detailed information about indexed files."""
        # Group chunks by file
        files_info = {}

        for metadata in self.metadata:
            if metadata.get('deleted', False):
                continue

            file_path = metadata.get('file_path')
            if file_path not in files_info:
                files_info[file_path] = {
                    "file_path": file_path,
                    "file_name": metadata.get('file_name'),
                    "extension": metadata.get('extension'),
                    "chunk_count": 0,
                    "hash": metadata.get('hash')
                }
            files_info[file_path]["chunk_count"] += 1

        return {
            "total_files": len(files_info),
            "files": list(files_info.values())
        }
