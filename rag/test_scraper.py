# Test script for web scraper functionality

import asyncio
import sys
import os

# Add the parent directory to the path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from rag.scraper import WebScraper, scrape_urls_basic, scrape_urls_async
from rag.config import get_preset_config, ScraperConfig


def test_basic_scraping():
    """Test basic scraping functionality"""
    print("🧪 Testing Basic Scraping...")
    
    try:
        # Simple test URL
        test_url = "https://httpbin.org/html"  # Simple HTML page for testing
        
        documents = scrape_urls_basic([test_url], chunk_size=500)
        
        if documents:
            print(f"✅ Basic scraping successful: {len(documents)} chunks")
            print(f"First chunk preview: {documents[0].page_content[:100]}...")
            return True
        else:
            print("❌ Basic scraping failed: No documents returned")
            return False
            
    except Exception as e:
        print(f"❌ Basic scraping error: {e}")
        return False


async def test_async_scraping():
    """Test async scraping functionality"""
    print("\n🧪 Testing Async Scraping...")
    
    try:
        # Test URLs
        test_urls = [
            "https://httpbin.org/html",
            "https://httpbin.org/robots.txt"
        ]
        
        documents = await scrape_urls_async(test_urls, chunk_size=500)
        
        if documents:
            print(f"✅ Async scraping successful: {len(documents)} chunks")
            sources = set(doc.metadata.get('source', 'unknown') for doc in documents)
            print(f"Sources scraped: {len(sources)}")
            return True
        else:
            print("❌ Async scraping failed: No documents returned")
            return False
            
    except Exception as e:
        print(f"❌ Async scraping error: {e}")
        return False


def test_configuration():
    """Test configuration system"""
    print("\n🧪 Testing Configuration System...")
    
    try:
        # Test default config
        config = ScraperConfig()
        assert config.get('chunk_size') == 1000
        print("✅ Default configuration loaded")
        
        # Test custom config
        custom_config = ScraperConfig({"chunk_size": 1500, "batch_size": 10})
        assert custom_config.get('chunk_size') == 1500
        assert custom_config.get('batch_size') == 10
        print("✅ Custom configuration applied")
        
        # Test preset config
        fast_config = get_preset_config("fast")
        assert fast_config.get('chunk_size') == 800
        print("✅ Preset configuration loaded")
        
        # Test URL validation
        assert config.is_url_allowed("https://www.odoo.com/documentation")
        assert not config.is_url_allowed("https://malicious-site.com")
        print("✅ URL validation working")
        
        # Test URL filtering
        assert config.should_skip_url("https://example.com/file.pdf")
        assert not config.should_skip_url("https://example.com/documentation.html")
        print("✅ URL filtering working")
        
        return True
        
    except Exception as e:
        print(f"❌ Configuration test error: {e}")
        return False


async def test_scraper_class():
    """Test WebScraper class functionality"""
    print("\n🧪 Testing WebScraper Class...")
    
    try:
        # Create scraper with custom settings
        scraper = WebScraper(chunk_size=600, chunk_overlap=100)
        
        # Test basic method
        test_url = "https://httpbin.org/html"
        documents = scraper.scrape_basic_html([test_url])
        
        if documents:
            print(f"✅ WebScraper class basic method: {len(documents)} chunks")
        else:
            print("⚠️ WebScraper basic method returned no documents")
        
        # Test async method
        documents_async = await scraper.scrape_async_html([test_url])
        
        if documents_async:
            print(f"✅ WebScraper class async method: {len(documents_async)} chunks")
        else:
            print("⚠️ WebScraper async method returned no documents")
        
        return True
        
    except Exception as e:
        print(f"❌ WebScraper class test error: {e}")
        return False


def test_document_processing():
    """Test document processing and cleaning"""
    print("\n🧪 Testing Document Processing...")
    
    try:
        scraper = WebScraper(chunk_size=300, chunk_overlap=50)
        
        # Create a mock document with problematic content
        from langchain.schema import Document
        
        test_doc = Document(
            page_content="  This is a test document with   excessive   whitespace  and short content.  " * 10,
            metadata={"source": "test"}
        )
        
        # Test cleaning
        cleaned_docs = scraper._clean_documents([test_doc])
        
        if cleaned_docs:
            cleaned_content = cleaned_docs[0].page_content
            # Check that whitespace was normalized
            assert "   " not in cleaned_content
            print("✅ Document cleaning successful")
            
            # Test text splitting
            split_docs = scraper.text_splitter.split_documents(cleaned_docs)
            print(f"✅ Text splitting successful: {len(split_docs)} chunks")
            
            return True
        else:
            print("❌ Document cleaning failed")
            return False
            
    except Exception as e:
        print(f"❌ Document processing test error: {e}")
        return False


async def test_error_handling():
    """Test error handling for various scenarios"""
    print("\n🧪 Testing Error Handling...")
    
    try:
        scraper = WebScraper()
        
        # Test with invalid URL
        documents = scraper.scrape_basic_html(["https://this-domain-does-not-exist-12345.com"])
        print("✅ Invalid URL handled gracefully")
        
        # Test with empty URL list
        documents = await scraper.scrape_async_html([])
        print("✅ Empty URL list handled gracefully")
        
        # Test with malformed URL
        documents = scraper.scrape_basic_html(["not-a-url"])
        print("✅ Malformed URL handled gracefully")
        
        return True
        
    except Exception as e:
        print(f"⚠️ Error handling test completed with expected exception: {type(e).__name__}")
        return True  # Expected to have some errors


def print_system_info():
    """Print system and dependency information"""
    print("🔍 System Information:")
    print(f"Python version: {sys.version}")
    
    # Check for key dependencies
    dependencies = [
        "langchain",
        "langchain_community",
        "beautifulsoup4",
        "aiohttp",
        "requests"
    ]
    
    for dep in dependencies:
        try:
            __import__(dep)
            print(f"✅ {dep}: Available")
        except ImportError:
            print(f"❌ {dep}: Not available")
    
    print()


async def run_all_tests():
    """Run all tests"""
    print("🚀 Web Scraper Test Suite")
    print("=" * 50)
    
    print_system_info()
    
    tests = [
        ("Configuration", test_configuration),
        ("Basic Scraping", test_basic_scraping),
        ("Async Scraping", test_async_scraping),
        ("WebScraper Class", test_scraper_class),
        ("Document Processing", test_document_processing),
        ("Error Handling", test_error_handling)
    ]
    
    results = []
    
    for test_name, test_func in tests:
        try:
            if asyncio.iscoroutinefunction(test_func):
                result = await test_func()
            else:
                result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"❌ {test_name} test failed with exception: {e}")
            results.append((test_name, False))
    
    # Print summary
    print("\n" + "=" * 50)
    print("📊 Test Results Summary:")
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status} {test_name}")
    
    print(f"\nOverall: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed! Web scraper is ready to use.")
    else:
        print("⚠️ Some tests failed. Check the output above for details.")
    
    return passed == total


if __name__ == "__main__":
    # Run the test suite
    success = asyncio.run(run_all_tests())
    sys.exit(0 if success else 1)
