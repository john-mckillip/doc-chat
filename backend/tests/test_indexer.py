"""
Tests for DocumentIndexer class and indexing functionality.
"""
import pytest
from pathlib import Path
import hashlib


class TestDocumentIndexerInit:
    """Test DocumentIndexer initialization."""

    def test_init_creates_directory(self, temp_dir):
        """Test that init creates the persist directory."""
        from indexer import DocumentIndexer

        persist_dir = temp_dir / "new_db"
        indexer = DocumentIndexer(persist_directory=str(persist_dir))

        assert persist_dir.exists()
        assert indexer.persist_directory == persist_dir

    def test_init_with_existing_index(self, temp_dir, mocker):
        """Test initialization when index files already exist."""
        from indexer import DocumentIndexer
        import pickle

        persist_dir = temp_dir / "existing_db"
        persist_dir.mkdir(parents=True, exist_ok=True)

        # Create dummy index files
        (persist_dir / "index.faiss").touch()
        with open(persist_dir / "metadata.pkl", 'wb') as f:
            pickle.dump([{"test": "metadata"}], f)
        with open(persist_dir / "texts.pkl", 'wb') as f:
            pickle.dump(["test text"], f)
        with open(persist_dir / "file_hashes.pkl", 'wb') as f:
            pickle.dump({"/test.md": "abc123"}, f)

        indexer = DocumentIndexer(persist_directory=str(persist_dir))

        assert len(indexer.metadata) == 1
        assert len(indexer.texts) == 1
        assert len(indexer.file_hashes) == 1

    def test_init_without_existing_index(self, temp_dir):
        """Test initialization when no index exists."""
        from indexer import DocumentIndexer

        persist_dir = temp_dir / "new_db"
        indexer = DocumentIndexer(persist_directory=str(persist_dir))

        assert indexer.metadata == []
        assert indexer.texts == []
        assert indexer.file_hashes == {}


class TestFileHashing:
    """Test file hash computation."""

    def test_get_file_hash(self, temp_dir):
        """Test MD5 hash calculation for files."""
        from indexer import DocumentIndexer

        indexer = DocumentIndexer(persist_directory=str(temp_dir / "db"))

        # Create a test file
        test_file = temp_dir / "test.txt"
        test_content = "Hello, World!"
        test_file.write_text(test_content)

        # Calculate expected hash
        expected_hash = hashlib.md5(test_content.encode()).hexdigest()

        # Test the method
        actual_hash = indexer._get_file_hash(test_file)

        assert actual_hash == expected_hash

    def test_get_file_hash_binary(self, temp_dir):
        """Test hash calculation for binary files."""
        from indexer import DocumentIndexer

        indexer = DocumentIndexer(persist_directory=str(temp_dir / "db"))

        # Create a binary file
        test_file = temp_dir / "test.bin"
        test_content = b"\x89PNG\r\n\x1a\n"
        test_file.write_bytes(test_content)

        # Calculate expected hash
        expected_hash = hashlib.md5(test_content).hexdigest()

        # Test the method
        actual_hash = indexer._get_file_hash(test_file)

        assert actual_hash == expected_hash


class TestFileFiltering:
    """Test file type filtering."""

    @pytest.mark.parametrize("filename,should_index", [
        ("test.md", True),
        ("test.txt", True),
        ("test.py", True),
        ("test.js", True),
        ("test.ts", True),
        ("test.tsx", True),
        ("test.cs", True),
        ("test.json", True),
        ("test.yaml", True),
        ("test.yml", True),
        ("test.MD", True),  # Case insensitive
        ("test.pdf", False),
        ("test.docx", False),
        ("test.exe", False),
        ("test.png", False),
        ("test", False),  # No extension
    ])
    def test_should_index_file(self, temp_dir, filename, should_index):
        """Test file type filtering for various extensions."""
        from indexer import DocumentIndexer

        indexer = DocumentIndexer(persist_directory=str(temp_dir / "db"))
        filepath = Path(filename)

        assert indexer._should_index_file(filepath) == should_index


class TestHashTracking:
    """Test file hash tracking for incremental indexing."""

    def test_get_existing_hash_found(self, temp_dir):
        """Test retrieving existing file hash."""
        from indexer import DocumentIndexer

        indexer = DocumentIndexer(persist_directory=str(temp_dir / "db"))
        indexer.file_hashes = {"/test/file.md": "abc123"}

        hash_value = indexer._get_existing_hash(Path("/test/file.md"))

        assert hash_value == "abc123"

    def test_get_existing_hash_not_found(self, temp_dir):
        """Test retrieving hash for non-indexed file."""
        from indexer import DocumentIndexer

        indexer = DocumentIndexer(persist_directory=str(temp_dir / "db"))
        indexer.file_hashes = {}

        hash_value = indexer._get_existing_hash(Path("/test/new_file.md"))

        assert hash_value is None


class TestChunkDeletion:
    """Test marking chunks as deleted."""

    def test_mark_file_chunks_deleted(self, temp_dir):
        """Test marking all chunks from a file as deleted."""
        from indexer import DocumentIndexer

        indexer = DocumentIndexer(persist_directory=str(temp_dir / "db"))
        indexer.metadata = [
            {"file_path": "/test/doc1.md", "deleted": False},
            {"file_path": "/test/doc2.md", "deleted": False},
            {"file_path": "/test/doc1.md", "deleted": False},  # Multiple chunks from same file
        ]

        indexer._mark_file_chunks_deleted(Path("/test/doc1.md"))

        assert indexer.metadata[0]["deleted"] is True
        assert indexer.metadata[1]["deleted"] is False
        assert indexer.metadata[2]["deleted"] is True

    def test_mark_file_chunks_deleted_already_deleted(self, temp_dir):
        """Test that already deleted chunks remain deleted."""
        from indexer import DocumentIndexer

        indexer = DocumentIndexer(persist_directory=str(temp_dir / "db"))
        indexer.metadata = [
            {"file_path": "/test/doc1.md", "deleted": True},
        ]

        indexer._mark_file_chunks_deleted(Path("/test/doc1.md"))

        # Should still be deleted
        assert indexer.metadata[0]["deleted"] is True


class TestIndexPersistence:
    """Test saving and loading index data."""

    def test_save_creates_files(self, temp_dir, mocker):
        """Test that _save calls FAISS write and creates pickle files."""
        from indexer import DocumentIndexer
        import faiss

        # Mock write_index since we want to verify it's called
        mock_write = mocker.patch.object(faiss, 'write_index')

        persist_dir = temp_dir / "db"
        indexer = DocumentIndexer(persist_directory=str(persist_dir))

        indexer.metadata = [{"test": "data"}]
        indexer.texts = ["test text"]
        indexer.file_hashes = {"/test.md": "hash123"}

        indexer._save()

        # Verify FAISS write was called
        assert mock_write.called

        # Verify pickle files were created
        assert (persist_dir / "metadata.pkl").exists()
        assert (persist_dir / "texts.pkl").exists()
        assert (persist_dir / "file_hashes.pkl").exists()


class TestDirectoryIndexing:
    """Test full directory indexing workflow."""

    def test_index_directory_new_files(self, sample_docs, temp_dir):
        """Test indexing a directory with all new files."""
        from indexer import DocumentIndexer

        indexer = DocumentIndexer(persist_directory=str(temp_dir / "db"))
        stats = indexer.index_directory(str(sample_docs))

        assert stats["files"] > 0
        assert stats["chunks"] > 0
        assert stats["new"] == stats["files"]
        assert stats["modified"] == 0
        assert stats["unchanged"] == 0

    def test_index_directory_with_progress_callback(self, sample_docs, temp_dir):
        """Test that progress callbacks are called during indexing."""
        from indexer import DocumentIndexer

        indexer = DocumentIndexer(persist_directory=str(temp_dir / "db"))
        messages = []

        def progress_callback(msg):
            messages.append(msg)

        stats = indexer.index_directory(str(sample_docs), progress_callback=progress_callback)

        # Should receive various progress messages
        assert stats["files"] > 0
        message_types = [msg["type"] for msg in messages]
        assert "scan_start" in message_types
        assert "file_processing" in message_types or "file_skipped" in message_types
        assert "stats" in message_types

    def test_index_directory_unchanged_files(self, sample_docs, temp_dir):
        """Test re-indexing with no changes."""
        from indexer import DocumentIndexer

        indexer = DocumentIndexer(persist_directory=str(temp_dir / "db"))

        # First index
        indexer.index_directory(str(sample_docs))

        # Second index (no changes)
        stats = indexer.index_directory(str(sample_docs))

        assert stats["new"] == 0
        assert stats["modified"] == 0
        assert stats["unchanged"] > 0

    def test_index_directory_modified_files(self, sample_docs, temp_dir):
        """Test indexing with modified files."""
        from indexer import DocumentIndexer

        indexer = DocumentIndexer(persist_directory=str(temp_dir / "db"))

        # First index
        indexer.index_directory(str(sample_docs))

        # Modify a file
        (sample_docs / "readme.md").write_text("# Modified Content\n\nThis has changed.")

        # Re-index
        stats = indexer.index_directory(str(sample_docs))

        assert stats["modified"] >= 1

    def test_index_directory_deleted_files(self, sample_docs, temp_dir):
        """Test handling of deleted files."""
        from indexer import DocumentIndexer

        indexer = DocumentIndexer(persist_directory=str(temp_dir / "db"))

        # First index
        indexer.index_directory(str(sample_docs))

        # Delete a file
        (sample_docs / "readme.md").unlink()

        # Re-index
        stats = indexer.index_directory(str(sample_docs))

        assert stats["deleted"] >= 1

    def test_index_directory_skips_empty_files(self, temp_dir):
        """Test that empty files are skipped."""
        from indexer import DocumentIndexer

        # Create directory with empty file
        docs_dir = temp_dir / "docs"
        docs_dir.mkdir()
        (docs_dir / "empty.md").write_text("")
        (docs_dir / "content.md").write_text("# Has content")

        indexer = DocumentIndexer(persist_directory=str(temp_dir / "db"))
        stats = indexer.index_directory(str(docs_dir))

        # Should only index the file with content
        assert stats["files"] == 1

    def test_index_directory_handles_encoding_errors(self, temp_dir):
        """Test handling of files with encoding issues."""
        from indexer import DocumentIndexer

        docs_dir = temp_dir / "docs"
        docs_dir.mkdir()

        # Create a file with invalid UTF-8
        (docs_dir / "bad.txt").write_bytes(b"\xff\xfe Invalid UTF-8")
        (docs_dir / "good.md").write_text("# Valid content")

        indexer = DocumentIndexer(persist_directory=str(temp_dir / "db"))

        messages = []

        def progress_callback(msg):
            messages.append(msg)

        stats = indexer.index_directory(str(docs_dir), progress_callback=progress_callback)

        # Should have at least one error message
        error_messages = [msg for msg in messages if msg["type"] == "error"]
        assert len(error_messages) >= 1

        # Assert stats - the good file should be indexed, bad file should error
        assert stats["files"] == 1  # Only good.md should be successfully indexed
        assert stats["chunks"] > 0  # Should have some chunks from good.md
        assert stats["new"] == 1    # Good file is new


class TestGetStats:
    """Test statistics retrieval."""

    def test_get_stats_counts_active_chunks(self, temp_dir):
        """Test that get_stats only counts non-deleted chunks."""
        from indexer import DocumentIndexer

        indexer = DocumentIndexer(persist_directory=str(temp_dir / "db"))
        indexer.metadata = [
            {"deleted": False},
            {"deleted": False},
            {"deleted": True},
            {"deleted": False},
        ]

        stats = indexer.get_stats()

        assert stats["total_chunks"] == 3
        assert stats["dimension"] == 384

    def test_get_stats_empty_index(self, temp_dir):
        """Test get_stats with empty index."""
        from indexer import DocumentIndexer

        indexer = DocumentIndexer(persist_directory=str(temp_dir / "db"))

        stats = indexer.get_stats()

        assert stats["total_chunks"] == 0
        assert stats["dimension"] == 384


class TestHelperMethods:
    """Test the helper methods."""

    def test_get_file_status_new_file(self, temp_dir):
        """Test _get_file_status with a new file."""
        from indexer import DocumentIndexer
        from pathlib import Path

        indexer = DocumentIndexer(persist_directory=str(temp_dir / "db"))
        test_file = Path("/test/new_file.md")
        file_hash = "abc123"

        status, should_skip = indexer._get_file_status(test_file, file_hash)

        assert status == "new"
        assert should_skip is False

    def test_get_file_status_modified_file(self, temp_dir):
        """Test _get_file_status with a modified file."""
        from indexer import DocumentIndexer
        from pathlib import Path

        indexer = DocumentIndexer(persist_directory=str(temp_dir / "db"))
        test_file = Path("/test/modified_file.md")

        # Set up existing hash
        indexer.file_hashes[str(test_file)] = "old_hash"
        indexer.metadata = [
            {"file_path": str(test_file), "deleted": False}
        ]

        status, should_skip = indexer._get_file_status(
            test_file,
            "new_hash"
        )

        assert status == "modified"
        assert should_skip is False
        # Verify chunks were marked deleted
        assert indexer.metadata[0]["deleted"] is True

    def test_get_file_status_unchanged_file(self, temp_dir):
        """Test _get_file_status with an unchanged file."""
        from indexer import DocumentIndexer
        from pathlib import Path

        indexer = DocumentIndexer(persist_directory=str(temp_dir / "db"))
        test_file = Path("/test/unchanged_file.md")
        file_hash = "same_hash"

        # Set up existing hash
        indexer.file_hashes[str(test_file)] = file_hash

        status, should_skip = indexer._get_file_status(test_file, file_hash)

        assert status == "unchanged"
        assert should_skip is True

    def test_process_single_file(self, temp_dir):
        """Test _process_single_file creates documents correctly."""
        from indexer import DocumentIndexer
        from pathlib import Path

        indexer = DocumentIndexer(persist_directory=str(temp_dir / "db"))
        test_file = Path("/test/sample.md")
        content = "# Test\n\nThis is test content."
        file_hash = "test_hash"

        documents = indexer._process_single_file(
            test_file,
            content,
            file_hash,
            "new"
        )

        assert len(documents) > 0
        assert all("text" in doc for doc in documents)
        assert all("metadata" in doc for doc in documents)
        assert documents[0]["metadata"]["file_path"] == str(test_file)
        assert documents[0]["metadata"]["hash"] == file_hash
        assert indexer.file_hashes[str(test_file)] == file_hash

    def test_process_single_file_with_callback(self, temp_dir):
        """Test _process_single_file calls progress callback."""
        from indexer import DocumentIndexer
        from pathlib import Path

        indexer = DocumentIndexer(persist_directory=str(temp_dir / "db"))
        test_file = Path("/test/sample.md")
        content = "# Test Content"
        file_hash = "test_hash"

        messages = []

        def callback(msg):
            messages.append(msg)

        indexer._process_single_file(
            test_file,
            content,
            file_hash,
            "new",
            callback
        )

        message_types = [msg["type"] for msg in messages]
        assert "file_processing" in message_types
        assert "file_processed" in message_types

    def test_process_deleted_files(self, temp_dir):
        """Test _process_deleted_files marks chunks and returns count."""
        from indexer import DocumentIndexer

        indexer = DocumentIndexer(persist_directory=str(temp_dir / "db"))

        # Set up some tracked files
        indexer.file_hashes = {
            "/test/file1.md": "hash1",
            "/test/file2.md": "hash2",
            "/test/file3.md": "hash3",
        }
        indexer.metadata = [
            {"file_path": "/test/file1.md", "deleted": False},
            {"file_path": "/test/file2.md", "deleted": False},
            {"file_path": "/test/file3.md", "deleted": False},
        ]

        # Only file1 still exists
        current_files = {"/test/file1.md"}

        deleted_count = indexer._process_deleted_files(current_files)

        assert deleted_count == 2
        assert "/test/file1.md" in indexer.file_hashes
        assert "/test/file2.md" not in indexer.file_hashes
        assert "/test/file3.md" not in indexer.file_hashes
        assert indexer.metadata[0]["deleted"] is False
        assert indexer.metadata[1]["deleted"] is True
        assert indexer.metadata[2]["deleted"] is True

    def test_process_deleted_files_with_callback(self, temp_dir):
        """Test _process_deleted_files calls progress callback."""
        from indexer import DocumentIndexer

        indexer = DocumentIndexer(persist_directory=str(temp_dir / "db"))
        indexer.file_hashes = {"/test/deleted.md": "hash"}
        indexer.metadata = [
            {"file_path": "/test/deleted.md", "deleted": False}
        ]

        messages = []

        def callback(msg):
            messages.append(msg)

        indexer._process_deleted_files(set(), callback)

        message_types = [msg["type"] for msg in messages]
        assert "file_deleted" in message_types

    def test_add_documents_to_index(self, temp_dir, mocker):
        """Test _add_documents_to_index adds documents to FAISS."""
        from indexer import DocumentIndexer

        indexer = DocumentIndexer(persist_directory=str(temp_dir / "db"))

        documents = [
            {
                "text": "Test chunk 1",
                "metadata": {"file_path": "/test.md", "chunk_index": 0}
            },
            {
                "text": "Test chunk 2",
                "metadata": {"file_path": "/test.md", "chunk_index": 1}
            }
        ]

        initial_count = indexer.index.ntotal

        indexer._add_documents_to_index(documents)

        assert len(indexer.metadata) == 2
        assert len(indexer.texts) == 2
        assert indexer.index.ntotal == initial_count + 2

    def test_add_documents_to_index_empty_list(self, temp_dir):
        """Test _add_documents_to_index handles empty list."""
        from indexer import DocumentIndexer

        indexer = DocumentIndexer(persist_directory=str(temp_dir / "db"))
        initial_count = indexer.index.ntotal

        indexer._add_documents_to_index([])

        # Should not add anything
        assert indexer.index.ntotal == initial_count

    def test_add_documents_to_index_with_callback(self, temp_dir):
        """Test _add_documents_to_index calls progress callbacks."""
        from indexer import DocumentIndexer

        indexer = DocumentIndexer(persist_directory=str(temp_dir / "db"))

        documents = [
            {
                "text": "Test chunk",
                "metadata": {"file_path": "/test.md", "chunk_index": 0}
            }
        ]

        messages = []

        def callback(msg):
            messages.append(msg)

        indexer._add_documents_to_index(documents, callback)

        message_types = [msg["type"] for msg in messages]
        assert "embedding_start" in message_types
        assert "embedding_complete" in message_types
        assert "saving" in message_types
        assert "save_complete" in message_types
