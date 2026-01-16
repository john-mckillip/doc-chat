import os
from pathlib import Path
from typing import List, Dict
import chromadb
from chromadb.config import Settings
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.schema import Document
import hashlib

class DocumentIndexer:
    def __init__(self, persist_directory: str = "./data/chroma_db"):
        self.client = chromadb.PersistentClient(path=persist_directory)
        self.collection = self.client.get_or_create_collection(
            name="docs",
            metadata={"hnsw:space": "cosine"}
        )
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000,
            chunk_overlap=200,
            separators=["\n\n", "\n", ". ", " ", ""]
        )
    
    def _get_file_hash(self, filepath: Path) -> str:
        """Generate hash of file content for change detection"""
        with open(filepath, 'rb') as f:
            return hashlib.md5(f.read()).hexdigest()
    
    def _should_index_file(self, filepath: Path) -> bool:
        """Check if file should be indexed"""
        extensions = {'.md', '.txt', '.py', '.cs', '.js', '.ts', '.tsx', '.json'}
        return filepath.suffix.lower() in extensions
    
    def index_directory(self, directory: str) -> Dict[str, int]:
        """Index all documents in directory"""
        docs_path = Path(directory)
        documents = []
        stats = {"files": 0, "chunks": 0}
        
        for filepath in docs_path.rglob("*"):
            if filepath.is_file() and self._should_index_file(filepath):
                try:
                    with open(filepath, 'r', encoding='utf-8') as f:
                        content = f.read()
                    
                    file_hash = self._get_file_hash(filepath)
                    
                    # Check if already indexed with same hash
                    existing = self.collection.get(
                        where={"file_path": str(filepath)}
                    )
                    
                    if existing['ids'] and existing['metadatas'][0].get('hash') == file_hash:
                        continue  # Skip unchanged files
                    
                    # Delete old chunks if file changed
                    if existing['ids']:
                        self.collection.delete(where={"file_path": str(filepath)})
                    
                    # Create chunks
                    chunks = self.text_splitter.split_text(content)
                    
                    for i, chunk in enumerate(chunks):
                        doc_id = f"{filepath.stem}_{file_hash}_{i}"
                        documents.append({
                            "id": doc_id,
                            "text": chunk,
                            "metadata": {
                                "file_path": str(filepath),
                                "file_name": filepath.name,
                                "chunk_index": i,
                                "hash": file_hash,
                                "extension": filepath.suffix
                            }
                        })
                    
                    stats["files"] += 1
                    stats["chunks"] += len(chunks)
                    
                except Exception as e:
                    print(f"Error indexing {filepath}: {e}")
        
        # Batch insert
        if documents:
            self.collection.add(
                ids=[d["id"] for d in documents],
                documents=[d["text"] for d in documents],
                metadatas=[d["metadata"] for d in documents]
            )
        
        return stats
    
    def get_stats(self) -> Dict:
        """Get collection statistics"""
        count = self.collection.count()
        return {
            "total_chunks": count,
            "collection_name": self.collection.name
        }