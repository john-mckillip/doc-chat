from typing import List, Dict, AsyncGenerator
import anthropic
import numpy as np
from sentence_transformers import SentenceTransformer
import faiss
import pickle
import os
import json
from pathlib import Path

class DocumentRetriever:
    def __init__(self, persist_directory: str = "./data/faiss_db"):
        self.persist_directory = Path(persist_directory)
        self.index_file = self.persist_directory / "index.faiss"
        self.metadata_file = self.persist_directory / "metadata.pkl"
        self.texts_file = self.persist_directory / "texts.pkl"

        # Check if index exists
        if self.index_file.exists():
            # Load FAISS index
            print("Loading FAISS index...")
            self.index = faiss.read_index(str(self.index_file))

            # Load metadata and texts
            with open(self.metadata_file, 'rb') as f:
                self.metadata = pickle.load(f)

            with open(self.texts_file, 'rb') as f:
                self.texts = pickle.load(f)

            print(f"✓ Loaded {len(self.texts)} document chunks")
        else:
            # No index yet - will be created when documents are indexed
            print("No index found - please index documents first")
            self.index = None
            self.metadata = []
            self.texts = []

        # Load embedding model
        print("Loading embedding model...")
        self.model = SentenceTransformer('all-MiniLM-L6-v2')

        # Initialize Anthropic client
        self.anthropic_client = anthropic.Anthropic(
            api_key=os.getenv("ANTHROPIC_API_KEY")
        )
    
    def search(self, query: str, top_k: int = 5) -> List[Dict]:
        """Search for relevant documents"""
        if self.index is None:
            return []

        # Generate query embedding
        query_embedding = self.model.encode([query])
        query_vector = np.array(query_embedding).astype('float32')

        # Search FAISS index - get more results to account for deleted chunks
        search_k = top_k * 3  # Get extra results to filter
        distances, indices = self.index.search(query_vector, min(search_k, self.index.ntotal))

        # Build results, filtering out deleted chunks
        sources = []
        for i, idx in enumerate(indices[0]):
            if idx < len(self.metadata):  # Valid index
                metadata = self.metadata[idx]
                # Skip deleted chunks
                if metadata.get('deleted', False):
                    continue

                sources.append({
                    "text": self.texts[idx],
                    "metadata": metadata,
                    "score": float(distances[0][i])
                })

                # Stop once we have enough non-deleted results
                if len(sources) >= top_k:
                    break

        return sources
    
    async def ask_streaming(
        self, 
        query: str, 
        conversation_history: List[Dict] = None
    ) -> AsyncGenerator[str, None]:
        """Ask question with streaming response"""
        
        # Retrieve relevant context
        sources = self.search(query, top_k=5)
        
        # Build context from sources
        context = "\n\n".join([
            f"Source: {s['metadata']['file_name']}\n{s['text']}"
            for s in sources
        ])
        
        # Build messages
        messages = conversation_history or []
        messages.append({
            "role": "user",
            "content": f"""Based on the following documentation context, please answer the question.

Context:
{context}

Question: {query}

Please cite which files you're referencing in your answer."""
        })
        
        # First yield the sources
        yield json.dumps({
            "type": "sources",
            "data": [
                {
                    "file": s['metadata']['file_name'],
                    "path": s['metadata']['file_path'],
                    "chunk": s['metadata']['chunk_index']
                }
                for s in sources
            ]
        }) + "\n"

        # Stream the response
        with self.anthropic_client.messages.stream(
            model="claude-sonnet-4-20250514",
            max_tokens=8192,
            messages=messages
        ) as stream:
            for text in stream.text_stream:
                yield json.dumps({
                    "type": "content",
                    "data": text
                }) + "\n"