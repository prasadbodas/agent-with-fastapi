# Web scraping utilities for RAG using langchain

import os
import asyncio
import json
from typing import List, Dict, Optional, Union
from urllib.parse import urljoin, urlparse
import logging

from langchain_community.document_loaders import (
    WebBaseLoader,
    AsyncHtmlLoader,
    SeleniumURLLoader,
    PlaywrightURLLoader,
    RecursiveUrlLoader,
    SitemapLoader,
    PyPDFLoader,
    OnlinePDFLoader
)
from langchain_community.document_transformers import Html2TextTransformer
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.schema import Document

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class WebScraper:
    """
    A comprehensive web scraper using LangChain's web-based loaders.
    Supports multiple scraping methods and document processing.
    """
    
    def __init__(self, 
                 chunk_size: int = 1000,
                 chunk_overlap: int = 100,
                 use_async: bool = True):
        """
        Initialize the WebScraper.
        
        Args:
            chunk_size: Size of text chunks for splitting
            chunk_overlap: Overlap between chunks
            use_async: Whether to use async loading when possible
        """
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.use_async = use_async
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            add_start_index=True  # This adds start index to metadata for better retrieval
        )
        self.html2text = Html2TextTransformer()
    
    def scrape_basic_html(self, urls: Union[str, List[str]], 
                         headers: Optional[Dict] = None) -> List[Document]:
        """
        Basic HTML scraping using WebBaseLoader.
        
        Args:
            urls: Single URL or list of URLs to scrape
            headers: Optional HTTP headers
            
        Returns:
            List of Document objects
        """
        if isinstance(urls, str):
            urls = [urls]
        
        try:
            # Set default headers for better scraping
            default_headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            }
            if headers:
                default_headers.update(headers)
            
            loader = WebBaseLoader(
                web_paths=urls,
                header_template=default_headers
            )
            documents = loader.load()
            
            # Clean and split documents
            cleaned_docs = self._clean_documents(documents)
            split_docs = self.split_documents_with_metadata(cleaned_docs)
            
            logger.info(f"Successfully scraped {len(urls)} URLs, generated {len(split_docs)} chunks")
            return split_docs
            
        except Exception as e:
            logger.error(f"Error in basic HTML scraping: {str(e)}")
            return []
    
    async def scrape_async_html(self, urls: Union[str, List[str]], 
                               headers: Optional[Dict] = None) -> List[Document]:
        """
        Asynchronous HTML scraping using AsyncHtmlLoader.
        
        Args:
            urls: Single URL or list of URLs to scrape
            headers: Optional HTTP headers
            
        Returns:
            List of Document objects
        """
        if isinstance(urls, str):
            urls = [urls]
        
        try:
            # Set default headers
            default_headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }
            if headers:
                default_headers.update(headers)
            
            loader = AsyncHtmlLoader(urls, header_template=default_headers)
            docs = await loader.aload()
            
            # Transform HTML to text
            docs = self.html2text.transform_documents(docs)
            
            # Clean and split documents
            cleaned_docs = self._clean_documents(docs)
            split_docs = self.split_documents_with_metadata(cleaned_docs)
            
            logger.info(f"Successfully async scraped {len(urls)} URLs, generated {len(split_docs)} chunks")
            return split_docs
            
        except Exception as e:
            logger.error(f"Error in async HTML scraping: {str(e)}")
            return []
    
    def scrape_with_selenium(self, urls: Union[str, List[str]], 
                            headless: bool = True) -> List[Document]:
        """
        Scrape using Selenium for JavaScript-heavy sites.
        
        Args:
            urls: Single URL or list of URLs to scrape
            headless: Whether to run browser in headless mode
            
        Returns:
            List of Document objects
        """
        if isinstance(urls, str):
            urls = [urls]
        
        try:
            loader = SeleniumURLLoader(urls=urls, headless=headless)
            documents = loader.load()
            
            # Clean and split documents
            cleaned_docs = self._clean_documents(documents)
            split_docs = self.split_documents_with_metadata(cleaned_docs)
            
            logger.info(f"Successfully scraped with Selenium {len(urls)} URLs, generated {len(split_docs)} chunks")
            return split_docs
            
        except Exception as e:
            logger.error(f"Error in Selenium scraping: {str(e)}")
            logger.warning("Selenium scraping failed. Make sure you have selenium and a webdriver installed.")
            return []
    
    def scrape_recursive(self, base_url: str, 
                        max_depth: int = 2,
                        exclude_dirs: Optional[List[str]] = None,
                        include_patterns: Optional[List[str]] = None) -> List[Document]:
        """
        Recursively scrape a website starting from a base URL.
        
        Args:
            base_url: Base URL to start scraping from
            max_depth: Maximum depth to crawl
            exclude_dirs: Directories to exclude from crawling
            include_patterns: Patterns to include in crawling
            
        Returns:
            List of Document objects
        """
        try:
            exclude_dirs = exclude_dirs or []
            print(f"max_depth: {max_depth}")
            loader = RecursiveUrlLoader(
                url=base_url,
                max_depth=max_depth,
                extractor=lambda x: x,
                exclude_dirs=exclude_dirs
            )
            documents = loader.load()

            for d in documents:
                print(d.metadata)

            # Filter documents based on include patterns if provided
            if include_patterns:
                filtered_docs = []
                for doc in documents:
                    url = doc.metadata.get('source', '')
                    if any(pattern in url for pattern in include_patterns):
                        filtered_docs.append(doc)
                documents = filtered_docs
            
            # Clean and split documents
            cleaned_docs = self._clean_documents(documents)
            split_docs = self.split_documents_with_metadata(cleaned_docs)

            logger.info(f"Successfully recursively scraped from {base_url}, scraped {len(documents)} documents, generated {len(split_docs)} chunks")
            return split_docs
            
        except Exception as e:
            logger.error(f"Error in recursive scraping: {str(e)}")
            return []
    
    async def scrape_sitemap(self, sitemap_url: str, max_depth: int = 2, max_pages: int = None) -> List[Document]:
        try:
            loader = SitemapLoader(
                web_path=sitemap_url,
                max_depth=max_depth
            )
            
            # Run loader.load() in a thread to avoid asyncio.run clash
            loop = asyncio.get_event_loop()
            documents = await loop.run_in_executor(None, loader.load)

            if max_pages and len(documents) > max_pages:
                documents = documents[:max_pages]
                logger.info(f"Limited sitemap scraping to {max_pages} pages")

            cleaned_docs = self._clean_documents(documents)
            split_docs = self.split_documents_with_metadata(cleaned_docs)

            logger.info(
                f"Successfully scraped sitemap from {sitemap_url}, "
                f"scraped {len(documents)} documents, generated {len(split_docs)} chunks"
            )
            return split_docs

        except Exception as e:
            logger.error(f"Error in sitemap scraping: {str(e)}")
            return []

    def scrape_pdf_urls(self, urls: Union[str, List[str]]) -> List[Document]:
        """
        Scrape PDF documents from URLs.
        
        Args:
            urls: Single PDF URL or list of PDF URLs to scrape
            
        Returns:
            List of Document objects
        """
        if isinstance(urls, str):
            urls = [urls]
        
        all_documents = []
        
        for url in urls:
            try:
                logger.info(f"Loading PDF from: {url}")
                
                # Use OnlinePDFLoader for URLs
                loader = OnlinePDFLoader(url)
                documents = loader.load()
                
                # Clean and split documents
                cleaned_docs = self._clean_documents(documents)
                split_docs = self.text_splitter.split_documents(cleaned_docs)
                
                all_documents.extend(split_docs)
                logger.info(f"Successfully loaded PDF from {url}, generated {len(split_docs)} chunks")
                
            except Exception as e:
                logger.error(f"Error loading PDF from {url}: {str(e)}")
                continue
        
        logger.info(f"Total PDF documents processed: {len(all_documents)} chunks")
        return all_documents

    def scrape_local_pdf(self, file_path: str) -> List[Document]:
        """
        Scrape a local PDF file.
        
        Args:
            file_path: Path to the local PDF file
            
        Returns:
            List of Document objects
        """
        try:
            logger.info(f"Loading local PDF from: {file_path}")
            
            # Use PyPDFLoader for local files
            loader = PyPDFLoader(file_path)
            documents = loader.load()
            
            # Clean and split documents
            cleaned_docs = self._clean_documents(documents)
            split_docs = self.split_documents_with_metadata(cleaned_docs)
            
            logger.info(f"Successfully loaded local PDF, generated {len(split_docs)} chunks")
            return split_docs
            
        except Exception as e:
            logger.error(f"Error loading local PDF from {file_path}: {str(e)}")
            return []

    async def scrape_pdf_urls_async(self, urls: Union[str, List[str]]) -> List[Document]:
        """
        Async version of PDF scraping from URLs.
        
        Args:
            urls: Single PDF URL or list of PDF URLs to scrape
            
        Returns:
            List of Document objects
        """
        if isinstance(urls, str):
            urls = [urls]
        
        all_documents = []
        
        for url in urls:
            try:
                logger.info(f"Loading PDF from: {url}")
                
                # Download PDF content first
                import aiohttp
                import tempfile
                import os
                
                async with aiohttp.ClientSession() as session:
                    async with session.get(url) as response:
                        response.raise_for_status()
                        content = await response.read()
                
                # Save to temporary file and use PyPDFLoader
                with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as temp_file:
                    temp_file.write(content)
                    temp_path = temp_file.name
                
                try:
                    loader = PyPDFLoader(temp_path)
                    documents = loader.load()
                    
                    # Update metadata with original URL
                    for doc in documents:
                        doc.metadata['source'] = url
                        doc.metadata['original_source'] = url
                    
                    # Clean and split documents
                    cleaned_docs = self._clean_documents(documents)
                    split_docs = self.split_documents_with_metadata(cleaned_docs)
                    
                    all_documents.extend(split_docs)
                    logger.info(f"Successfully loaded PDF from {url}, generated {len(split_docs)} chunks")
                    
                finally:
                    # Clean up temporary file
                    os.unlink(temp_path)
                
            except Exception as e:
                logger.error(f"Error loading PDF from {url}: {str(e)}")
                continue
        
        logger.info(f"Total PDF documents processed: {len(all_documents)} chunks")
        return all_documents

    def scrape_local_csv(self, file_path: str) -> List[Document]:
        """
        Scrape text from a local CSV file using LangChain's CSVLoader.
        
        Args:
            file_path (str): Path to the local CSV file
            
        Returns:
            List of Document objects containing the extracted text
        """
        from langchain_community.document_loaders.csv_loader import CSVLoader
        
        try:
            logger.info(f"Loading CSV from local file: {file_path}")
            
            # Use CSVLoader - it automatically handles CSV parsing
            loader = CSVLoader(
                file_path=file_path,
                encoding='utf-8'
            )
            
            # Load all documents
            documents = loader.load()
            
            # Add file_type to metadata for all documents
            for doc in documents:
                doc.metadata['file_type'] = 'csv'
            
            logger.info(f"Successfully loaded {len(documents)} records from CSV: {file_path}")
            
            # Clean and split documents into chunks if they're too large
            cleaned_docs = self._clean_documents(documents)
            split_docs = self.split_documents_with_metadata(cleaned_docs)
            
            return split_docs
            
        except Exception as e:
            logger.error(f"Error loading local CSV {file_path}: {e}")
            return []

    def scrape_local_docx(self, file_path: str) -> List[Document]:
        """
        Scrape text from a local DOCX file using LangChain's Docx2txtLoader.
        
        Args:
            file_path (str): Path to the local DOCX file
            
        Returns:
            List of Document objects containing the extracted text
        """
        from langchain_community.document_loaders import Docx2txtLoader
        
        try:
            logger.info(f"Loading DOCX from local file: {file_path}")
            
            # Use Docx2txtLoader for DOCX files
            loader = Docx2txtLoader(file_path)
            
            # Load documents
            documents = loader.load()
            
            # Add file_type to metadata for all documents
            for doc in documents:
                doc.metadata['file_type'] = 'docx'
            
            logger.info(f"Successfully loaded {len(documents)} documents from DOCX: {file_path}")
            
            # Clean and split documents into chunks if they're too large
            cleaned_docs = self._clean_documents(documents)
            split_docs = self.split_documents_with_metadata(cleaned_docs)
            
            return split_docs
            
        except Exception as e:
            logger.error(f"Error loading local DOCX {file_path}: {e}")
            return []

    
    def scrape_odoo_documentation(self, version: str = "17.0") -> List[Document]:
        """
        Specialized method to scrape Odoo documentation.
        
        Args:
            version: Odoo version to scrape documentation for
            
        Returns:
            List of Document objects
        """
        base_urls = [
            f"https://www.odoo.com/documentation/{version}/",
            f"https://www.odoo.com/documentation/{version}/developer/",
            f"https://www.odoo.com/documentation/{version}/administration/",
            f"https://www.odoo.com/documentation/{version}/applications/"
        ]
        
        all_documents = []
        
        for base_url in base_urls:
            try:
                # Use recursive scraping for comprehensive coverage
                docs = self.scrape_recursive(
                    base_url=base_url,
                    max_depth=3,
                    include_patterns=['/documentation/', '/developer/', '/reference/']
                )
                all_documents.extend(docs)
                
            except Exception as e:
                logger.error(f"Error scraping {base_url}: {str(e)}")
                continue
        
        logger.info(f"Successfully scraped Odoo documentation, generated {len(all_documents)} chunks")
        return all_documents
    
    def _clean_documents(self, documents: List[Document]) -> List[Document]:
        """
        Clean and preprocess documents with enhanced metadata handling.
        
        Args:
            documents: List of raw documents
            
        Returns:
            List of cleaned documents with proper metadata
        """
        cleaned_docs = []
        
        for doc in documents:
            # Remove excessive whitespace
            content = ' '.join(doc.page_content.split())
            
            # Skip very short documents
            if not content or len(content) < 100:
                continue
            
            # Update document content
            doc.page_content = content
            
            # Clean and enhance metadata
            cleaned_metadata = self._clean_metadata(doc.metadata)
            doc.metadata = cleaned_metadata
            
            cleaned_docs.append(doc)
        
        return cleaned_docs
    
    def _clean_metadata(self, metadata: dict) -> dict:
        """
        Clean metadata to ensure compatibility with vector stores.
        Converts lists to strings and adds useful metadata fields.
        
        Args:
            metadata: Original metadata dictionary
            
        Returns:
            Cleaned metadata dictionary with only scalar values
        """
        cleaned_metadata = {}
        
        for key, value in metadata.items():
            if value is None:
                cleaned_metadata[key] = None
            elif isinstance(value, (str, int, float, bool)):
                cleaned_metadata[key] = value
            elif isinstance(value, list):
                # Convert lists to comma-separated strings
                cleaned_metadata[key] = ', '.join(str(item) for item in value if item is not None)
            elif isinstance(value, dict):
                # Convert dicts to JSON strings
                cleaned_metadata[key] = json.dumps(value)
            else:
                # Convert other types to strings
                cleaned_metadata[key] = str(value)
        
        # Ensure required metadata fields exist
        if 'source' not in cleaned_metadata:
            cleaned_metadata['source'] = 'unknown'
        
        # Add chunk metadata for better retrieval
        if 'chunk_id' not in cleaned_metadata:
            import hashlib
            content_hash = hashlib.md5(str(cleaned_metadata.get('source', '') + str(cleaned_metadata.get('page', ''))).encode()).hexdigest()[:8]
            cleaned_metadata['chunk_id'] = content_hash
        
        # Extract page number if available in source
        source = cleaned_metadata.get('source', '')
        if 'page' in cleaned_metadata:
            cleaned_metadata['page_number'] = cleaned_metadata['page']
        elif any(keyword in source.lower() for keyword in ['page', 'p.']):
            # Try to extract page number from source
            import re
            page_match = re.search(r'page[\s]*(\d+)', source.lower())
            if page_match:
                cleaned_metadata['page_number'] = int(page_match.group(1))
        
        # Add document type for better categorization
        if 'file_type' not in cleaned_metadata:
            source_lower = source.lower()
            if source_lower.endswith('.pdf'):
                cleaned_metadata['file_type'] = 'pdf'
            elif source_lower.endswith(('.doc', '.docx')):
                cleaned_metadata['file_type'] = 'docx'
            elif source_lower.endswith('.csv'):
                cleaned_metadata['file_type'] = 'csv'
            elif 'http' in source_lower:
                cleaned_metadata['file_type'] = 'web'
            else:
                cleaned_metadata['file_type'] = 'unknown'
        
        # Add content length for filtering
        cleaned_metadata['content_length'] = len(str(cleaned_metadata.get('content', '')))
        
        return cleaned_metadata

    def split_documents_with_metadata(self, documents: List[Document]) -> List[Document]:
        """
        Split documents with enhanced metadata for better retrieval.
        
        Args:
            documents: List of documents to split
            
        Returns:
            List of split documents with enhanced metadata
        """
        split_docs = self.text_splitter.split_documents(documents)
        
        # Enhance metadata for each chunk
        for i, doc in enumerate(split_docs):
            # Add chunk sequence number
            doc.metadata['chunk_index'] = i
            
            # Add chunk size information
            doc.metadata['chunk_size'] = len(doc.page_content)
            
            # Add total chunks count for this document source
            source = doc.metadata.get('source', '')
            total_chunks = len([d for d in split_docs if d.metadata.get('source') == source])
            doc.metadata['total_chunks'] = total_chunks
            
            # Add relative position in document
            if total_chunks > 1:
                source_chunks = [d for d in split_docs if d.metadata.get('source') == source]
                chunk_position = source_chunks.index(doc) if doc in source_chunks else 0
                doc.metadata['chunk_position'] = chunk_position
                doc.metadata['chunk_position_percent'] = round((chunk_position / total_chunks) * 100, 1)
            
            # Add section hint based on content
            content_lower = doc.page_content.lower()
            if any(keyword in content_lower for keyword in ['introduction', 'overview', 'summary']):
                doc.metadata['section_type'] = 'introduction'
            elif any(keyword in content_lower for keyword in ['conclusion', 'summary', 'end']):
                doc.metadata['section_type'] = 'conclusion'
            elif any(keyword in content_lower for keyword in ['example', 'demo', 'tutorial']):
                doc.metadata['section_type'] = 'example'
            elif any(keyword in content_lower for keyword in ['reference', 'api', 'function', 'method']):
                doc.metadata['section_type'] = 'reference'
            else:
                doc.metadata['section_type'] = 'content'
        
        return split_docs
    
    async def batch_scrape(self, urls: List[str], 
                          method: str = 'async',
                          batch_size: int = 5) -> List[Document]:
        """
        Scrape multiple URLs in batches.
        
        Args:
            urls: List of URLs to scrape
            method: Scraping method ('async', 'basic', 'selenium')
            batch_size: Number of URLs to process in each batch
            
        Returns:
            List of Document objects
        """
        all_documents = []
        
        for i in range(0, len(urls), batch_size):
            batch_urls = urls[i:i + batch_size]
            logger.info(f"Processing batch {i//batch_size + 1}: {len(batch_urls)} URLs")
            
            try:
                if method == 'async':
                    docs = await self.scrape_async_html(batch_urls)
                elif method == 'selenium':
                    docs = self.scrape_with_selenium(batch_urls)
                else:  # default to basic
                    docs = self.scrape_basic_html(batch_urls)
                
                all_documents.extend(docs)
                
                # Add a small delay between batches to be respectful
                await asyncio.sleep(1)
                
            except Exception as e:
                logger.error(f"Error processing batch {i//batch_size + 1}: {str(e)}")
                continue
        
        logger.info(f"Batch scraping completed. Total documents: {len(all_documents)}")
        return all_documents

# Utility functions for common scraping tasks

async def scrape_urls_async(urls: Union[str, List[str]], 
                           chunk_size: int = 1000) -> List[Document]:
    """
    Quick async scraping function for immediate use.
    
    Args:
        urls: URL(s) to scrape
        chunk_size: Size of text chunks
        
    Returns:
        List of Document objects
    """
    scraper = WebScraper(chunk_size=chunk_size)
    return await scraper.scrape_async_html(urls)


def scrape_urls_basic(urls: Union[str, List[str]], 
                     chunk_size: int = 1000) -> List[Document]:
    """
    Quick basic scraping function for immediate use.
    
    Args:
        urls: URL(s) to scrape
        chunk_size: Size of text chunks
        
    Returns:
        List of Document objects
    """
    scraper = WebScraper(chunk_size=chunk_size)
    return scraper.scrape_basic_html(urls)


def get_odoo_documentation(version: str = "17.0") -> List[Document]:
    """
    Get Odoo documentation for a specific version.
    
    Args:
        version: Odoo version
        
    Returns:
        List of Document objects
    """
    scraper = WebScraper()
    return scraper.scrape_odoo_documentation(version)


# Example usage
if __name__ == "__main__":
    # Example 1: Basic scraping
    scraper = WebScraper()
    
    # Example URLs for testing
    test_urls = [
        "https://www.odoo.com/documentation/17.0/",
        "https://www.odoo.com/documentation/17.0/developer/reference/backend/orm.html"
    ]
    
    # Async scraping example
    async def main():
        print("Starting async scraping...")
        docs = await scraper.scrape_async_html(test_urls)
        print(f"Scraped {len(docs)} document chunks")
        
        if docs:
            print(f"First chunk preview: {docs[0].page_content[:200]}...")
    
    # Run the example
    # asyncio.run(main())