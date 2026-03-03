import os
import json
from typing import List, Dict, Any
from datetime import datetime


class RAGSystem:
    """Manages knowledge base and retrieval for RAG"""
    
    def __init__(self, kb_dir: str = 'knowledge_base'):
        self.kb_dir = kb_dir
        self._ensure_kb_dir()
    
    def _ensure_kb_dir(self):
        """Create knowledge base directory if it doesn't exist"""
        if not os.path.exists(self.kb_dir):
            os.makedirs(self.kb_dir)
    
    def add_document(self, doc_id: str, title: str, content: str, category: str = "general"):
        """Add a document to the knowledge base"""
        doc_path = os.path.join(self.kb_dir, f"{doc_id}.json")
        
        document = {
            "id": doc_id,
            "title": title,
            "content": content,
            "category": category,
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat()
        }
        
        with open(doc_path, 'w') as f:
            json.dump(document, f, indent=2)
    
    def retrieve_documents(self, query: str, category: str = None, limit: int = 3) -> List[Dict[str, Any]]:
        """Retrieve relevant documents based on query"""
        query_lower = query.lower()
        relevant_docs = []
        
        if not os.path.exists(self.kb_dir):
            return []
        
        for filename in os.listdir(self.kb_dir):
            if not filename.endswith('.json'):
                continue
            
            doc_path = os.path.join(self.kb_dir, filename)
            try:
                with open(doc_path, 'r') as f:
                    doc = json.load(f)
                
                if category and doc.get('category') != category:
                    continue
                
                title_lower = doc.get('title', '').lower()
                content_lower = doc.get('content', '').lower()
                
                score = 0
                query_words = query_lower.split()
                
                for word in query_words:
                    if len(word) > 3:
                        if word in title_lower:
                            score += 3
                        if word in content_lower:
                            score += 1
                
                if score > 0:
                    relevant_docs.append({
                        "score": score,
                        "document": doc
                    })
            
            except Exception as e:
                print(f"Error loading document {filename}: {e}")
                continue
        
        relevant_docs.sort(key=lambda x: x['score'], reverse=True)
        return [doc['document'] for doc in relevant_docs[:limit]]
    
    def format_context(self, documents: List[Dict[str, Any]]) -> str:
        """Format retrieved documents into context string"""
        if not documents:
            return ""
        
        context = "--- RELEVANT KNOWLEDGE BASE ---\n"
        for i, doc in enumerate(documents, 1):
            context += f"\n[{i}] {doc.get('title', 'Untitled')}\n"
            context += f"Category: {doc.get('category', 'general')}\n"
            context += f"Content: {doc.get('content', '')}\n"
        
        return context
    
    def get_all_documents(self, category: str = None) -> List[Dict[str, Any]]:
        """Get all documents, optionally filtered by category"""
        docs = []
        
        if not os.path.exists(self.kb_dir):
            return docs
        
        for filename in os.listdir(self.kb_dir):
            if not filename.endswith('.json'):
                continue
            
            doc_path = os.path.join(self.kb_dir, filename)
            try:
                with open(doc_path, 'r') as f:
                    doc = json.load(f)
                
                if category and doc.get('category') != category:
                    continue
                
                docs.append(doc)
            
            except Exception as e:
                print(f"Error loading document {filename}: {e}")
        
        return docs


rag = RAGSystem()
