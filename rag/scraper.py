# Web scraping utilities for RAG using langchain

import os
import asyncio
from typing import List, Dict, Optional, Union
from urllib.parse import urljoin, urlparse
import logging

from langchain_community.document_loaders import (
    WebBaseLoader,
    AsyncHtmlLoader,
    SeleniumURLLoader,
    PlaywrightURLLoader,
    RecursiveUrlLoader
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
                 chunk_overlap: int = 200,
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
            chunk_overlap=chunk_overlap
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
            split_docs = self.text_splitter.split_documents(cleaned_docs)
            
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
            split_docs = self.text_splitter.split_documents(cleaned_docs)
            
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
            split_docs = self.text_splitter.split_documents(cleaned_docs)
            
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
            split_docs = self.text_splitter.split_documents(cleaned_docs)

            logger.info(f"Successfully recursively scraped from {base_url}, scraped {len(documents)} documents, generated {len(split_docs)} chunks")
            return split_docs
            
        except Exception as e:
            logger.error(f"Error in recursive scraping: {str(e)}")
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
        Clean and preprocess documents.
        
        Args:
            documents: List of raw documents
            
        Returns:
            List of cleaned documents
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
            
            # Ensure metadata includes useful information
            if 'source' not in doc.metadata:
                doc.metadata['source'] = 'unknown'
            
            cleaned_docs.append(doc)
        
        return cleaned_docs
    
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