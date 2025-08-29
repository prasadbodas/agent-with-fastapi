# Example usage of the web scraper for RAG system

import asyncio
import os
import sys
import traceback

# Add the parent directory to the path to import the scraper
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from rag.scraper import WebScraper, scrape_urls_basic, scrape_urls_async, get_odoo_documentation


async def example_basic_scraping():
    """Example of basic web scraping"""
    print("=== Basic Web Scraping Example ===")
    
    urls = [
        "https://www.odoo.com/documentation/17.0/",
        "https://www.odoo.com/page/about-us"
    ]
    
    # Use the quick function
    documents = scrape_urls_basic(urls, chunk_size=800)
    
    print(f"Scraped {len(documents)} document chunks")
    if documents:
        print(f"First document source: {documents[0].metadata.get('source', 'Unknown')}")
        print(f"First chunk preview: {documents[0].page_content[:300]}...")
    
    return documents


async def example_async_scraping():
    """Example of asynchronous web scraping"""
    print("\n=== Async Web Scraping Example ===")
    
    urls = [
        "https://www.odoo.com/documentation/17.0/developer/",
        "https://www.odoo.com/documentation/17.0/administration/",
    ]
    
    # Use async scraping for better performance
    documents = await scrape_urls_async(urls, chunk_size=1000)
    
    print(f"Async scraped {len(documents)} document chunks")
    if documents:
        print(f"Sample metadata: {documents[0].metadata}")
        print(f"Sample content: {documents[0].page_content[:200]}...")
    
    return documents


async def example_advanced_scraping():
    """Example of advanced scraping with custom configuration"""
    print("\n=== Advanced Web Scraping Example ===")
    
    # Create a scraper with custom settings
    scraper = WebScraper(
        chunk_size=1200,
        chunk_overlap=200,
        use_async=True
    )
    
    # Custom headers for better scraping
    headers = {
        'User-Agent': 'Mozilla/5.0 (compatible; RAG-Bot/1.0)',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8'
    }
    
    urls = ["https://www.odoo.com/documentation/17.0/developer/reference/backend/orm.html"]
    
    # Use async scraping with custom headers
    documents = await scraper.scrape_async_html(urls, headers=headers)
    
    print(f"Advanced scraped {len(documents)} document chunks")
    if documents:
        for i, doc in enumerate(documents[:3]):  # Show first 3 chunks
            print(f"Chunk {i+1} ({len(doc.page_content)} chars): {doc.page_content[:150]}...")
    
    return documents


async def example_batch_scraping():
    """Example of batch scraping multiple URLs"""
    print("\n=== Batch Web Scraping Example ===")
    
    scraper = WebScraper(chunk_size=800)
    
    # List of Odoo-related URLs to scrape
    urls = [
        "https://www.odoo.com/documentation/17.0/developer/reference/backend/orm.html",
        "https://www.odoo.com/documentation/17.0/developer/reference/backend/views.html",
        "https://www.odoo.com/documentation/17.0/developer/reference/backend/actions.html",
        "https://www.odoo.com/documentation/17.0/applications/",
        "https://www.odoo.com/documentation/17.0/administration/install.html"
    ]
    
    # Batch scrape with async method
    documents = await scraper.batch_scrape(
        urls=urls,
        method='async',
        batch_size=2  # Process 2 URLs at a time
    )
    
    print(f"Batch scraped {len(documents)} document chunks from {len(urls)} URLs")
    
    # Show statistics
    sources = {}
    for doc in documents:
        source = doc.metadata.get('source', 'unknown')
        sources[source] = sources.get(source, 0) + 1
    
    print("Documents per source:")
    for source, count in sources.items():
        print(f"  {source}: {count} chunks")
    
    return documents


def example_odoo_documentation():
    """Example of scraping Odoo documentation"""
    print("\n=== Odoo Documentation Scraping Example ===")
    
    # Note: This might take a while and scrape a lot of content
    # Uncomment the line below to actually run it
    # documents = get_odoo_documentation(version="17.0")
    
    # For demonstration, we'll just show how it would work
    print("This would scrape comprehensive Odoo documentation...")
    print("Commented out to avoid long execution time in demo")
    
    # If you want to actually run it:
    # print(f"Scraped {len(documents)} document chunks from Odoo documentation")
    
    return []


async def example_with_vector_store():
    """Example of how to use scraped documents with a vector store"""
    print("\n=== Integration with Vector Store Example ===")
    
    try:
        from langchain_community.vectorstores import FAISS
        from langchain_openai import OpenAIEmbeddings
        
        # Scrape some documents
        urls = ["https://www.odoo.com/documentation/17.0/developer/reference/backend/orm.html"]
        documents = await scrape_urls_async(urls, chunk_size=600)
        
        if not documents:
            print("No documents scraped, skipping vector store example")
            return
        
        print(f"Creating vector store from {len(documents)} document chunks...")
        
        # Create embeddings and vector store
        embeddings = OpenAIEmbeddings()
        vectorstore = FAISS.from_documents(documents, embeddings)
        
        # Example query
        query = "How to create a new model in Odoo?"
        similar_docs = vectorstore.similarity_search(query, k=3)
        
        print(f"Found {len(similar_docs)} similar documents for query: '{query}'")
        for i, doc in enumerate(similar_docs):
            print(f"Result {i+1}: {doc.page_content[:200]}...")
    
    except ImportError as e:
        print(f"Vector store example skipped due to missing dependencies: {e}")
    except Exception as e:
        print(f"Error in vector store example: {e}")


async def main():
    """Main function to run all examples"""
    print("🕷️  Web Scraper Examples for RAG System")
    print("=" * 50)
    
    try:
        # Run basic examples
        await example_basic_scraping()
        await example_async_scraping()
        await example_advanced_scraping()
        await example_batch_scraping()
        
        # Run Odoo documentation example (commented out by default)
        example_odoo_documentation()
        
        # Run vector store integration example
        await example_with_vector_store()
        
        print("\n✅ All examples completed successfully!")
        
    except Exception as e:
        print(f"❌ Error running examples: {e}")
        traceback.print_exc()


if __name__ == "__main__":
    # Run the examples
    asyncio.run(main())
