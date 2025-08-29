# Integration script showing how to use the web scraper with the RAG system

import asyncio
import os
import sys
import traceback
from typing import List

# Add the parent directory to the path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from langchain.schema import Document
from langchain_community.vectorstores import FAISS
from langchain_openai import OpenAIEmbeddings

from rag.config import get_preset_config
from rag.scraper import WebScraper, get_odoo_documentation


class RAGKnowledgeBuilder:
    """
    Class to build a knowledge base for RAG using the web scraper.
    """
    
    def __init__(self, chunk_size: int = 1000, chunk_overlap: int = 200):
        """
        Initialize the knowledge builder.
        
        Args:
            chunk_size: Size of text chunks
            chunk_overlap: Overlap between chunks
        """
        self.scraper = WebScraper(chunk_size=chunk_size, chunk_overlap=chunk_overlap)
        self.embeddings = None
        self.vectorstore = None
        self.documents = []
    
    async def scrape_odoo_docs(self, version: str = "17.0", 
                              include_patterns: List[str] = None) -> List[Document]:
        """
        Scrape Odoo documentation for a specific version.
        
        Args:
            version: Odoo version to scrape
            include_patterns: URL patterns to include
            
        Returns:
            List of document chunks
        """
        print(f"🔍 Scraping Odoo {version} documentation...")
        
        # Define key documentation URLs
        odoo_urls = [
            f"https://www.odoo.com/documentation/{version}/developer/reference/backend/orm.html",
            f"https://www.odoo.com/documentation/{version}/developer/reference/backend/views.html",
            f"https://www.odoo.com/documentation/{version}/developer/reference/backend/actions.html",
            f"https://www.odoo.com/documentation/{version}/developer/tutorials/getting_started/",
            f"https://www.odoo.com/documentation/{version}/administration/install.html",
            f"https://www.odoo.com/documentation/{version}/applications/inventory_and_mrp/",
            f"https://www.odoo.com/documentation/{version}/applications/sales/",
            f"https://www.odoo.com/documentation/{version}/applications/accounting/",
        ]
        
        # Batch scrape the URLs
        documents = await self.scraper.batch_scrape(
            urls=odoo_urls,
            method='async',
            batch_size=3
        )
        
        print(f"✅ Scraped {len(documents)} document chunks from Odoo documentation")
        return documents
    
    async def scrape_custom_urls(self, urls: List[str]) -> List[Document]:
        """
        Scrape custom URLs.
        
        Args:
            urls: List of URLs to scrape
            
        Returns:
            List of document chunks
        """
        print(f"🔍 Scraping {len(urls)} custom URLs...")
        
        documents = await self.scraper.batch_scrape(
            urls=urls,
            method='async',
            batch_size=5
        )
        
        print(f"✅ Scraped {len(documents)} document chunks from custom URLs")
        return documents
    
    def add_documents(self, documents: List[Document]):
        """Add documents to the knowledge base."""
        self.documents.extend(documents)
        print(f"📚 Added {len(documents)} documents. Total: {len(self.documents)}")
    
    def create_vector_store(self) -> FAISS:
        """
        Create a vector store from the collected documents.
        
        Returns:
            FAISS vector store
        """
        if not self.documents:
            raise ValueError("No documents available. Please scrape some content first.")
        
        print(f"🧮 Creating vector store from {len(self.documents)} documents...")
        
        # Initialize embeddings
        self.embeddings = OpenAIEmbeddings()
        
        # Create vector store
        self.vectorstore = FAISS.from_documents(self.documents, self.embeddings)
        
        print("✅ Vector store created successfully")
        return self.vectorstore
    
    def save_vector_store(self, path: str):
        """Save the vector store to disk."""
        if not self.vectorstore:
            raise ValueError("No vector store to save. Create one first.")
        
        self.vectorstore.save_local(path)
        print(f"💾 Vector store saved to {path}")
    
    def load_vector_store(self, path: str):
        """Load a vector store from disk."""
        self.embeddings = OpenAIEmbeddings()
        self.vectorstore = FAISS.load_local(path, self.embeddings, allow_dangerous_deserialization=True)
        print(f"📂 Vector store loaded from {path}")
    
    def query_knowledge_base(self, query: str, k: int = 5) -> List[Document]:
        """
        Search the knowledge base for relevant documents.
        
        Args:
            query: Search query
            k: Number of results to return
            
        Returns:
            List of relevant documents
        """
        if not self.vectorstore:
            raise ValueError("No vector store available. Create one first.")
        
        results = self.vectorstore.similarity_search(query, k=k)
        return results
    
    def get_stats(self) -> dict:
        """Get statistics about the knowledge base."""
        stats = {
            "total_documents": len(self.documents),
            "sources": len(set(doc.metadata.get('source', 'unknown') for doc in self.documents)),
            "total_characters": sum(len(doc.page_content) for doc in self.documents),
            "average_chunk_size": sum(len(doc.page_content) for doc in self.documents) / len(self.documents) if self.documents else 0,
            "has_vector_store": self.vectorstore is not None
        }
        return stats


async def build_odoo_knowledge_base():
    """Example: Build a comprehensive Odoo knowledge base."""
    print("🚀 Building Odoo Knowledge Base")
    print("=" * 50)
    
    # Initialize the knowledge builder
    kb = RAGKnowledgeBuilder(chunk_size=1000, chunk_overlap=200)
    
    # Scrape Odoo documentation
    odoo_docs = await kb.scrape_odoo_docs(version="17.0")
    kb.add_documents(odoo_docs)
    
    # Add some additional useful URLs
    additional_urls = [
        "https://www.odoo.com/documentation/17.0/",
        "https://www.odoo.com/page/tour",
    ]
    
    additional_docs = await kb.scrape_custom_urls(additional_urls)
    kb.add_documents(additional_docs)
    
    # Create vector store
    vectorstore = kb.create_vector_store()
    
    # Show statistics
    stats = kb.get_stats()
    print("\n📊 Knowledge Base Statistics:")
    for key, value in stats.items():
        print(f"  {key}: {value}")
    
    # Test the knowledge base
    print("\n🔍 Testing Knowledge Base:")
    test_queries = [
        "How to create a new model in Odoo?",
        "What are Odoo views?",
        "How to install Odoo?",
        "Odoo inventory management",
        "Odoo sales process"
    ]
    
    for query in test_queries:
        print(f"\nQuery: {query}")
        results = kb.query_knowledge_base(query, k=2)
        for i, doc in enumerate(results):
            print(f"  Result {i+1}: {doc.page_content[:150]}...")
    
    # Save the knowledge base
    save_path = "odoo_knowledge_base"
    kb.save_vector_store(save_path)
    
    return kb


async def demonstrate_rag_integration():
    """Demonstrate integration with the existing RAG system."""
    print("\n🔗 RAG System Integration Demo")
    print("=" * 50)
    
    try:
        # Build knowledge base
        kb = await build_odoo_knowledge_base()
        
        # Simulate RAG query processing
        query = "How to create a Many2one field in Odoo?"
        print(f"\n❓ User Query: {query}")
        
        # Get relevant context from knowledge base
        relevant_docs = kb.query_knowledge_base(query, k=3)
        context = "\n\n".join([doc.page_content for doc in relevant_docs])
        
        print(f"\n📚 Retrieved Context ({len(context)} characters):")
        print(context[:500] + "..." if context and len(context) > 500 else context)
        
        # This context would normally be fed into the language model
        print("\n💭 This context would be used to enhance the LLM response...")
        
        return True
        
    except Exception as e:
        print(f"❌ Error in RAG integration demo: {e}")
        return False


async def quick_test():
    """Quick test of the web scraper functionality."""
    print("⚡ Quick Test")
    print("=" * 30)
    
    try:
        # Test basic scraping
        kb = RAGKnowledgeBuilder(chunk_size=800)
        
        # Use a simple, reliable test URL
        test_urls = ["https://httpbin.org/html"]
        docs = await kb.scrape_custom_urls(test_urls)
        
        if docs:
            print(f"✅ Quick test successful: {len(docs)} documents scraped")
            return True
        else:
            print("❌ Quick test failed: No documents scraped")
            return False
            
    except Exception as e:
        print(f"❌ Quick test error: {e}")
        return False


async def main():
    """Main function to run demonstrations."""
    print("🕷️ Web Scraper + RAG Integration")
    print("=" * 60)
    
    # Run quick test first
    if not await quick_test():
        print("⚠️ Quick test failed. Check your internet connection and dependencies.")
        return
    
    # Ask user what to run
    print("\nWhat would you like to run?")
    print("1. Quick test only (already completed)")
    print("2. Build Odoo knowledge base")
    print("3. Full RAG integration demo")
    print("4. Exit")
    
    # For automated demo, we'll run option 3
    choice = "3"
    
    if choice == "2":
        await build_odoo_knowledge_base()
    elif choice == "3":
        await demonstrate_rag_integration()
    else:
        print("👋 Exiting...")


if __name__ == "__main__":
    # Set environment variable to avoid OpenAI API calls in demo
    os.environ["OPENAI_API_KEY"] = os.environ.get("OPENAI_API_KEY", "demo-key")
    
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n👋 Demo interrupted by user")
    except Exception as e:
        print(f"\n❌ Demo failed with error: {e}")
        traceback.print_exc()
