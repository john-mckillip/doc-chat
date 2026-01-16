from pathlib import Path
from typing import Dict
import numpy as np
import faiss
from sentence_transformers import SentenceTransformer
from langchain.text_splitter import RecursiveCharacterTextSplitter
import hashlib
import pickle

class DocumentIndexer:
    def __init__(self, persist_directory: str = "./data/faiss_db"):
        self.persist_directory = Path(persist_directory)
        self.persist_directory.mkdir(parents=True, exist_ok=True)
        
        self.index_file = self.persist_directory / "index.faiss"
        self.metadata_file = self.persist_directory / "metadata.pkl"
        self.texts_file = self.persist_directory / "texts.pkl"
        
        # Load embedding model
        print("Loading embedding model...")
        self.model = SentenceTransformer('all-MiniLM-L6-v2')
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
        
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000,
            chunk_overlap=200,
            separators=["\n\n", "\n", ". ", " ", ""]
        )
    
    def _get_file_hash(self, filepath: Path) -> str:
        with open(filepath, 'rb') as f:
            return hashlib.md5(f.read()).hexdigest()
    
    def _should_index_file(self, filepath: Path) -> bool:
        extensions = {'.md', '.txt', '.py', '.cs', '.js', '.ts', '.tsx', '.json', '.yaml', '.yml'}
        return filepath.suffix.lower() in extensions
    
    def _save(self):
        """Save index and metadata to disk"""
        faiss.write_index(self.index, str(self.index_file))
        with open(self.metadata_file, 'wb') as f:
            pickle.dump(self.metadata, f)
        with open(self.texts_file, 'wb') as f:
            pickle.dump(self.texts, f)
    
    def index_directory(self, directory: str) -> Dict[str, int]:
        docs_path = Path(directory)
        documents = []
        stats = {"files": 0, "chunks": 0}
        
        print(f"Indexing directory: {directory}")
        
        # Clear existing index
        self.index = faiss.IndexFlatL2(self.dimension)
        self.metadata = []
        self.texts = []
        
        for filepath in docs_path.rglob("*"):
            if filepath.is_file() and self._should_index_file(filepath):
                try:
                    with open(filepath, 'r', encoding='utf-8') as f:
                        content = f.read()
                    
                    if not content.strip():
                        continue
                    
                    file_hash = self._get_file_hash(filepath)
                    chunks = self.text_splitter.split_text(content)
                    
                    for i, chunk in enumerate(chunks):
                        documents.append({
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
                    print(f"Indexed: {filepath.name} ({len(chunks)} chunks)")
                    
                except Exception as e:
                    print(f"Error indexing {filepath}: {e}")
        
        if documents:
            print(f"\nGenerating embeddings for {len(documents)} chunks...")
            # Generate embeddings
            texts = [d["text"] for d in documents]
            embeddings = self.model.encode(texts, show_progress_bar=True)
            
            # Add to FAISS index
            self.index.add(np.array(embeddings).astype('float32'))
            self.metadata = [d["metadata"] for d in documents]
            self.texts = texts
            
            # Save to disk
            self._save()
            print(f"✓ Indexed {stats['files']} files with {stats['chunks']} chunks")
        else:
            print("No documents found to index")
        
        return stats
    
    def get_stats(self) -> Dict:
        return {
            "total_chunks": self.index.ntotal,
            "dimension": self.dimension
        }