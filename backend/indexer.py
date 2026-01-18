from pathlib import Path
from typing import Dict, Callable, Optional
import numpy as np
import faiss
from sentence_transformers import SentenceTransformer
from langchain.text_splitter import RecursiveCharacterTextSplitter
import hashlib
import pickle
import os


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
        print(f"{status_text}:{filepath.name} ({len(chunks)} chunks)")

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
                "data": {"total_chunks": len(documents)}
            })

        # Generate embeddings
        texts = [d["text"] for d in documents]
        embeddings = self.model.encode(texts, show_progress_bar=True)

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

    def _save(self):
        """Save index and metadata to disk"""
        faiss.write_index(self.index, str(self.index_file))
        with open(self.metadata_file, 'wb') as f:
            pickle.dump(self.metadata, f)
        with open(self.texts_file, 'wb') as f:
            pickle.dump(self.texts, f)
        with open(self.file_hashes_file, 'wb') as f:
            pickle.dump(self.file_hashes, f)

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
