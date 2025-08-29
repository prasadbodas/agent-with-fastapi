# Web Scraper for RAG System

A comprehensive web scraping utility built with LangChain for extracting content to enhance RAG (Retrieval-Augmented Generation) systems. This scraper is specifically designed to work with Odoo documentation and other web sources.

## Features

### 🚀 Multiple Scraping Methods
- **Basic HTML Scraping**: Fast, lightweight scraping using WebBaseLoader
- **Async Scraping**: High-performance asynchronous scraping with AsyncHtmlLoader
- **Selenium Scraping**: JavaScript-heavy sites with SeleniumURLLoader
- **Recursive Scraping**: Crawl entire websites with RecursiveUrlLoader
- **Batch Processing**: Efficiently process multiple URLs in batches

### 🎯 Specialized Odoo Support
- Pre-configured for Odoo documentation scraping
- Support for multiple Odoo versions (15.0, 16.0, 17.0)
- Smart filtering for relevant documentation pages
- Optimized chunking for Odoo content structure

### ⚙️ Configurable and Extensible
- Flexible configuration system with presets
- Environment variable support
- Custom headers and request settings
- Content filtering and URL validation
- Configurable text chunking and overlap

### 🔧 Built-in Document Processing
- Automatic HTML-to-text conversion
- Intelligent text chunking with overlap
- Metadata preservation and enhancement
- Content cleaning and preprocessing

## Installation

Make sure you have the required dependencies installed:

```bash
# Core dependencies (already in requirements.txt)
pip install langchain langchain-community langchain-openai
pip install beautifulsoup4 lxml html2text
pip install aiohttp requests

# Optional: For Selenium scraping
pip install selenium
pip install webdriver-manager

# Optional: For enhanced async processing
pip install aiofiles
```

## Quick Start

### Basic Usage

```python
from rag.scraper import WebScraper, scrape_urls_basic

# Simple scraping
documents = scrape_urls_basic([
    "https://www.odoo.com/documentation/17.0/",
    "https://www.odoo.com/documentation/17.0/developer/"
])

print(f"Scraped {len(documents)} document chunks")
```

### Async Scraping

```python
import asyncio
from rag.scraper import scrape_urls_async

async def main():
    documents = await scrape_urls_async([
        "https://www.odoo.com/documentation/17.0/developer/reference/backend/orm.html",
        "https://www.odoo.com/documentation/17.0/developer/reference/backend/views.html"
    ], chunk_size=1000)
    
    print(f"Async scraped {len(documents)} chunks")

asyncio.run(main())
```

### Advanced Configuration

```python
from rag.scraper import WebScraper
from rag.config import get_preset_config

# Use preset configuration
config = get_preset_config("odoo_docs")
scraper = WebScraper(
    chunk_size=config.get("chunk_size"),
    chunk_overlap=config.get("chunk_overlap")
)

# Custom headers
headers = {
    'User-Agent': 'MyBot/1.0',
    'Accept': 'text/html,application/xhtml+xml'
}

documents = scraper.scrape_basic_html(urls, headers=headers)
```

## Configuration

### Preset Configurations

The scraper comes with several preset configurations:

- **`fast`**: Quick scraping with smaller chunks (800 chars)
- **`balanced`**: Default balanced settings (1000 chars)
- **`thorough`**: Comprehensive scraping with larger chunks (1500 chars)
- **`odoo_docs`**: Optimized for Odoo documentation

```python
from rag.config import get_preset_config

# Use a preset
config = get_preset_config("fast")
scraper = WebScraper(
    chunk_size=config.get("chunk_size"),
    batch_size=config.get("batch_size")
)
```

### Environment Variables

Configure the scraper using environment variables:

```bash
export SCRAPER_CHUNK_SIZE=1200
export SCRAPER_CHUNK_OVERLAP=200
export SCRAPER_BATCH_SIZE=5
export SCRAPER_MAX_DEPTH=2
export SCRAPER_DELAY=1.0
export SCRAPER_TIMEOUT=30
```

### Custom Configuration

```python
from rag.config import ScraperConfig

config = ScraperConfig({
    "chunk_size": 1500,
    "chunk_overlap": 300,
    "batch_size": 3,
    "max_depth": 4,
    "delay_between_requests": 2.0
})
```

## API Reference

### WebScraper Class

#### Methods

##### `scrape_basic_html(urls, headers=None)`
Basic HTML scraping using WebBaseLoader.

**Parameters:**
- `urls` (str|List[str]): URL(s) to scrape
- `headers` (Dict, optional): Custom HTTP headers

**Returns:** List[Document]

##### `scrape_async_html(urls, headers=None)`
Asynchronous HTML scraping using AsyncHtmlLoader.

**Parameters:**
- `urls` (str|List[str]): URL(s) to scrape
- `headers` (Dict, optional): Custom HTTP headers

**Returns:** List[Document]

##### `scrape_with_selenium(urls, headless=True)`
Scrape using Selenium for JavaScript-heavy sites.

**Parameters:**
- `urls` (str|List[str]): URL(s) to scrape
- `headless` (bool): Run browser in headless mode

**Returns:** List[Document]

##### `scrape_recursive(base_url, max_depth=2, exclude_dirs=None, include_patterns=None)`
Recursively scrape a website.

**Parameters:**
- `base_url` (str): Base URL to start crawling
- `max_depth` (int): Maximum crawl depth
- `exclude_dirs` (List[str]): Directories to exclude
- `include_patterns` (List[str]): URL patterns to include

**Returns:** List[Document]

##### `batch_scrape(urls, method='async', batch_size=5)`
Scrape multiple URLs in batches.

**Parameters:**
- `urls` (List[str]): URLs to scrape
- `method` (str): Scraping method ('async', 'basic', 'selenium')
- `batch_size` (int): URLs per batch

**Returns:** List[Document]

##### `scrape_odoo_documentation(version='17.0')`
Specialized method for Odoo documentation.

**Parameters:**
- `version` (str): Odoo version to scrape

**Returns:** List[Document]

### Utility Functions

##### `scrape_urls_async(urls, chunk_size=1000)`
Quick async scraping function.

##### `scrape_urls_basic(urls, chunk_size=1000)`
Quick basic scraping function.

##### `get_odoo_documentation(version='17.0')`
Get Odoo documentation for a specific version.

## Examples

### Scraping Odoo Documentation

```python
import asyncio
from rag.scraper import WebScraper

async def scrape_odoo():
    scraper = WebScraper(chunk_size=1200)
    
    # Scrape specific Odoo pages
    urls = [
        "https://www.odoo.com/documentation/17.0/developer/reference/backend/orm.html",
        "https://www.odoo.com/documentation/17.0/developer/reference/backend/views.html",
        "https://www.odoo.com/documentation/17.0/developer/tutorials/"
    ]
    
    documents = await scraper.batch_scrape(urls, method='async', batch_size=2)
    
    # Show results
    for i, doc in enumerate(documents[:3]):
        print(f"Document {i+1}:")
        print(f"Source: {doc.metadata.get('source', 'Unknown')}")
        print(f"Content: {doc.page_content[:200]}...")
        print("-" * 50)

asyncio.run(scrape_odoo())
```

### Integration with Vector Store

```python
import asyncio
from langchain_openai import OpenAIEmbeddings
from langchain_community.vectorstores import FAISS
from rag.scraper import scrape_urls_async

async def create_knowledge_base():
    # Scrape documentation
    urls = [
        "https://www.odoo.com/documentation/17.0/developer/reference/backend/orm.html",
        "https://www.odoo.com/documentation/17.0/applications/"
    ]
    
    documents = await scrape_urls_async(urls, chunk_size=800)
    
    # Create vector store
    embeddings = OpenAIEmbeddings()
    vectorstore = FAISS.from_documents(documents, embeddings)
    
    # Query the knowledge base
    query = "How to create a new model in Odoo?"
    results = vectorstore.similarity_search(query, k=3)
    
    print(f"Found {len(results)} relevant documents:")
    for doc in results:
        print(f"- {doc.page_content[:150]}...")

asyncio.run(create_knowledge_base())
```

### Custom Content Processing

```python
from rag.scraper import WebScraper

class CustomScraper(WebScraper):
    def _clean_documents(self, documents):
        """Custom document cleaning"""
        cleaned_docs = super()._clean_documents(documents)
        
        # Add custom processing
        for doc in cleaned_docs:
            # Remove specific patterns
            content = doc.page_content
            content = content.replace("© Odoo", "")
            content = content.replace("Edit on GitHub", "")
            
            # Add custom metadata
            doc.metadata['processed_by'] = 'CustomScraper'
            doc.metadata['content_length'] = len(content)
            doc.page_content = content
        
        return cleaned_docs

# Use custom scraper
scraper = CustomScraper()
documents = scraper.scrape_basic_html(["https://www.odoo.com/documentation/17.0/"])
```

## Best Practices

### 1. Respectful Scraping
- Use appropriate delays between requests
- Respect robots.txt files
- Don't overload servers with too many concurrent requests

### 2. Error Handling
- Always wrap scraping calls in try-catch blocks
- Implement retry logic for failed requests
- Log errors for debugging

### 3. Content Quality
- Filter out low-quality or irrelevant content
- Use appropriate chunk sizes for your use case
- Maintain metadata for source tracking

### 4. Performance Optimization
- Use async scraping for better performance
- Batch process URLs to avoid overwhelming the system
- Consider caching frequently accessed content

## Troubleshooting

### Common Issues

1. **SSL Certificate Errors**
   ```python
   # Add SSL verification skip for problematic sites
   headers = {'User-Agent': 'Mozilla/5.0...'}
   # Use basic scraping instead of async for SSL issues
   ```

2. **JavaScript-Heavy Sites**
   ```python
   # Use Selenium for sites requiring JavaScript
   documents = scraper.scrape_with_selenium(urls, headless=True)
   ```

3. **Rate Limiting**
   ```python
   # Increase delays between requests
   config = ScraperConfig({"delay_between_requests": 3.0})
   ```

4. **Memory Issues with Large Sites**
   ```python
   # Use smaller chunk sizes and batch processing
   scraper = WebScraper(chunk_size=500)
   documents = await scraper.batch_scrape(urls, batch_size=2)
   ```

### Dependencies Issues

If you encounter import errors:

```bash
# Install missing dependencies
pip install beautifulsoup4 lxml html2text aiohttp

# For Selenium support
pip install selenium webdriver-manager

# For enhanced processing
pip install aiofiles
```

## Contributing

To extend the scraper:

1. Add new loader methods to the `WebScraper` class
2. Update configuration options in `config.py`
3. Add examples to `example_usage.py`
4. Update this README with new features

## License

This project is part of the agent-for-odoo repository. Please refer to the main repository license.
