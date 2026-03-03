import os
import json
from typing import List, Dict, Any
from datetime import datetime
import PyPDF2
from rag import rag


class PDFHandler:
    """Handles PDF uploads, extraction, and RAG integration with tech validation"""
    
    # Tech-related keywords for validation
    TECH_KEYWORDS = {
        # Programming & Development
        'python', 'javascript', 'java', 'c++', 'c#', 'ruby', 'php', 'swift', 
        'kotlin', 'golang', 'rust', 'typescript', 'scala', 'perl', 'r programming',
        'react', 'angular', 'vue', 'django', 'flask', 'spring', 'asp.net',
        'node.js', 'express', 'fastapi', 'nextjs', 'nuxt', 'svelte',
        
        # Web & Mobile
        'html', 'css', 'web development', 'frontend', 'backend', 'fullstack',
        'mobile app', 'ios', 'android', 'responsive design', 'api', 'rest',
        'graphql', 'websocket',
        
        # Data & AI
        'machine learning', 'deep learning', 'artificial intelligence', 'ai',
        'neural network', 'nlp', 'computer vision', 'data science', 'data analysis',
        'pytorch', 'tensorflow', 'keras', 'scikit-learn', 'pandas', 'numpy',
        'sql', 'database', 'mysql', 'postgresql', 'mongodb', 'redis',
        'big data', 'spark', 'hadoop', 'etl',
        
        # DevOps & Infrastructure
        'docker', 'kubernetes', 'devops', 'ci/cd', 'jenkins', 'gitlab',
        'aws', 'azure', 'google cloud', 'cloud computing', 'terraform',
        'linux', 'unix', 'bash', 'shell scripting', 'server', 'deployment',
        
        # Software Engineering
        'software engineering', 'oop', 'design pattern', 'algorithm', 'data structure',
        'testing', 'unit test', 'integration test', 'agile', 'scrum',
        'git', 'version control', 'debugging', 'refactoring',
        
        # Cybersecurity
        'cybersecurity', 'security', 'encryption', 'authentication', 'authorization',
        'penetration testing', 'vulnerability', 'ssl', 'tls', 'firewall',
        
        # Blockchain & Web3
        'blockchain', 'cryptocurrency', 'ethereum', 'smart contract', 'web3',
        'solidity', 'defi', 'nft',
        
        # Other Tech Domains
        'iot', 'internet of things', 'embedded systems', 'robotics', 'game development',
        'virtual reality', 'augmented reality', 'vr', 'ar', 'quantum computing',
        'microservices', 'architecture', 'scalability', 'performance optimization',
        'system design', 'network', 'tcp/ip', 'http', 'dns',
    }
    
    def __init__(self, upload_dir: str = 'uploads'):
        self.upload_dir = upload_dir
        self.metadata_file = os.path.join(upload_dir, 'pdf_metadata.json')
        self._ensure_upload_dir()
    
    def _ensure_upload_dir(self):
        """Create upload directory if it doesn't exist"""
        if not os.path.exists(self.upload_dir):
            os.makedirs(self.upload_dir)
    
    def is_tech_related(self, text: str, filename: str = "") -> Dict[str, Any]:
        """
        Check if PDF content is tech-related
        
        Args:
            text: Extracted text from PDF
            filename: PDF filename for additional context
            
        Returns:
            Dictionary with:
            - is_tech: Boolean indicating if content is tech-related
            - confidence: Confidence score (0-100)
            - tech_keywords_found: List of detected tech keywords
            - reason: Explanation message
        """
        text_lower = text.lower()
        filename_lower = filename.lower()
        
        # Search for tech keywords
        found_keywords = []
        keyword_count = 0
        
        for keyword in self.TECH_KEYWORDS:
            if keyword in text_lower or keyword in filename_lower:
                found_keywords.append(keyword)
                keyword_count += 1
        
        # Calculate confidence based on keyword density
        total_words = len(text.split())
        keyword_density = (keyword_count / total_words * 100) if total_words > 0 else 0
        
        # Determine if tech-related based on keyword count and density
        is_tech = keyword_count >= 3 or keyword_density > 0.5
        
        # Calculate confidence score
        if keyword_count >= 10:
            confidence = 95
        elif keyword_count >= 5:
            confidence = 85
        elif keyword_count >= 3:
            confidence = 70
        elif keyword_count >= 1:
            confidence = 50
        else:
            confidence = 0
        
        if is_tech:
            reason = f"✓ Tech-related content detected ({keyword_count} tech keywords found)"
        else:
            reason = "✗ This PDF doesn't appear to be tech-related. I only review tech documents (programming, AI, data science, cybersecurity, etc.)"
        
        return {
            "is_tech": is_tech,
            "confidence": confidence,
            "tech_keywords_found": found_keywords[:10],  # Return first 10 keywords
            "keyword_count": keyword_count,
            "reason": reason
        }
    
    def extract_text_from_pdf(self, pdf_path: str) -> str:
        """Extract text from PDF file"""
        try:
            text = ""
            with open(pdf_path, 'rb') as file:
                pdf_reader = PyPDF2.PdfReader(file)
                num_pages = len(pdf_reader.pages)
                
                for page_num in range(num_pages):
                    page = pdf_reader.pages[page_num]
                    text += f"\n--- Page {page_num + 1} ---\n"
                    text += page.extract_text()
            
            return text.strip()
        except Exception as e:
            raise Exception(f"Error extracting text from PDF: {str(e)}")
    
    def save_pdf(self, file, user_id: str) -> Dict[str, Any]:
        """Save uploaded PDF and extract its content"""
        try:
            filename = f"{user_id}_{datetime.now().timestamp()}.pdf"
            pdf_path = os.path.join(self.upload_dir, filename)
            
            file.save(pdf_path)
            extracted_text = self.extract_text_from_pdf(pdf_path)
            original_filename = file.filename
            
            metadata = {
                "pdf_id": filename.replace('.pdf', ''),
                "original_filename": original_filename,
                "user_id": user_id,
                "file_path": pdf_path,
                "uploaded_at": datetime.now().isoformat(),
                "text_length": len(extracted_text),
                "pages": extracted_text.count("--- Page")
            }
            
            self._save_metadata(metadata)
            
            return {
                "pdf_id": metadata["pdf_id"],
                "filename": original_filename,
                "text_preview": extracted_text[:500],
                "full_text": extracted_text,
                "metadata": metadata
            }
        
        except Exception as e:
            raise Exception(f"Error saving PDF: {str(e)}")
    
    def process_pdf_to_rag(self, pdf_id: str, extracted_text: str, original_filename: str) -> str:
        """Process extracted PDF text and add to RAG knowledge base"""
        try:
            chunks = self._chunk_text(extracted_text, chunk_size=500)
            
            for i, chunk in enumerate(chunks):
                doc_id = f"pdf_{pdf_id}_chunk_{i}"
                title = f"{original_filename} - Section {i + 1}"
                
                rag.add_document(
                    doc_id=doc_id,
                    title=title,
                    content=chunk,
                    category="user_pdf"
                )
            
            return f"Successfully processed {len(chunks)} sections from {original_filename}"
        
        except Exception as e:
            raise Exception(f"Error processing PDF to RAG: {str(e)}")
    
    def _chunk_text(self, text: str, chunk_size: int = 500, overlap: int = 50) -> List[str]:
        """Split text into overlapping chunks"""
        words = text.split()
        chunks = []
        
        for i in range(0, len(words), chunk_size - overlap):
            chunk = ' '.join(words[i:i + chunk_size])
            if chunk.strip():
                chunks.append(chunk)
        
        return chunks
    
    def get_user_pdfs(self, user_id: str) -> List[Dict[str, Any]]:
        """Get all PDFs uploaded by a user"""
        metadata = self._load_metadata()
        user_pdfs = [pdf for pdf in metadata if pdf.get('user_id') == user_id]
        return user_pdfs
    
    def _save_metadata(self, metadata: Dict[str, Any]):
        """Save PDF metadata"""
        all_metadata = self._load_metadata()
        all_metadata.append(metadata)
        
        try:
            with open(self.metadata_file, 'w') as f:
                json.dump(all_metadata, f, indent=2)
        except Exception as e:
            print(f"Error saving metadata: {e}")
    
    def _load_metadata(self) -> List[Dict[str, Any]]:
        """Load all PDF metadata"""
        if not os.path.exists(self.metadata_file):
            return []
        
        try:
            with open(self.metadata_file, 'r') as f:
                return json.load(f)
        except Exception as e:
            print(f"Error loading metadata: {e}")
            return []


pdf_handler = PDFHandler()