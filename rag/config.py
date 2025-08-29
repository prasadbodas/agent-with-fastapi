# Configuration file for web scraper

import os
from typing import Dict, List, Optional

# Default scraping configuration
DEFAULT_CONFIG = {
    "chunk_size": 1000,
    "chunk_overlap": 200,
    "use_async": True,
    "batch_size": 5,
    "max_depth": 2,
    "delay_between_requests": 1.0,  # seconds
    "timeout": 30,  # seconds
    "max_retries": 3,
}

# Default headers for web requests
DEFAULT_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.5",
    "Accept-Encoding": "gzip, deflate",
    "DNT": "1",
    "Connection": "keep-alive",
    "Upgrade-Insecure-Requests": "1",
}

# Odoo-specific scraping configuration
ODOO_CONFIG = {
    "base_urls": {
        "17.0": [
            "https://www.odoo.com/documentation/17.0/",
            "https://www.odoo.com/documentation/17.0/developer/",
            "https://www.odoo.com/documentation/17.0/administration/",
            "https://www.odoo.com/documentation/17.0/applications/",
        ],
        "16.0": [
            "https://www.odoo.com/documentation/16.0/",
            "https://www.odoo.com/documentation/16.0/developer/",
            "https://www.odoo.com/documentation/16.0/administration/",
            "https://www.odoo.com/documentation/16.0/applications/",
        ],
        "15.0": [
            "https://www.odoo.com/documentation/15.0/",
            "https://www.odoo.com/documentation/15.0/developer/",
            "https://www.odoo.com/documentation/15.0/administration/",
            "https://www.odoo.com/documentation/15.0/applications/",
        ],
    },
    "include_patterns": [
        "/documentation/",
        "/developer/",
        "/reference/",
        "/tutorials/",
        "/howtos/",
    ],
    "exclude_patterns": [
        "/genindex",
        "/search",
        "/_static/",
        "/_images/",
        ".pdf",
        ".zip",
        "/download/",
    ],
    "max_depth": 3,
    "chunk_size": 1200,
    "chunk_overlap": 200,
}

# Selenium-specific configuration
SELENIUM_CONFIG = {
    "headless": True,
    "window_size": (1920, 1080),
    "page_load_timeout": 30,
    "implicit_wait": 10,
    "chrome_options": [
        "--no-sandbox",
        "--disable-dev-shm-usage",
        "--disable-gpu",
        "--disable-web-security",
        "--allow-running-insecure-content",
        "--disable-extensions",
        "--disable-plugins",
        "--disable-images",  # Faster loading
        "--disable-javascript",  # If JS is not needed
    ]
}

# Allowed domains for scraping (for security)
ALLOWED_DOMAINS = [
    "odoo.com",
    "www.odoo.com",
    "docs.odoo.com",
    "github.com",
    "stackoverflow.com",
    "python.org",
    "docs.python.org",
]

# File extensions to skip
SKIP_EXTENSIONS = [
    ".pdf", ".doc", ".docx", ".xls", ".xlsx", ".ppt", ".pptx",
    ".zip", ".rar", ".tar", ".gz", ".7z",
    ".jpg", ".jpeg", ".png", ".gif", ".bmp", ".svg",
    ".mp4", ".avi", ".mov", ".wmv", ".mp3", ".wav",
    ".exe", ".msi", ".dmg", ".app"
]

# Content type filters
ALLOWED_CONTENT_TYPES = [
    "text/html",
    "application/xhtml+xml",
    "text/plain",
    "application/xml",
    "text/xml"
]


class ScraperConfig:
    """Configuration class for web scraper settings."""
    
    def __init__(self, config_dict: Optional[Dict] = None):
        """
        Initialize configuration.
        
        Args:
            config_dict: Optional dictionary to override default settings
        """
        self.config = DEFAULT_CONFIG.copy()
        if config_dict:
            self.config.update(config_dict)
    
    def get(self, key: str, default=None):
        """Get configuration value."""
        return self.config.get(key, default)
    
    def set(self, key: str, value):
        """Set configuration value."""
        self.config[key] = value
    
    def update(self, config_dict: Dict):
        """Update multiple configuration values."""
        self.config.update(config_dict)
    
    def get_headers(self, custom_headers: Optional[Dict] = None) -> Dict:
        """Get headers with optional custom additions."""
        headers = DEFAULT_HEADERS.copy()
        if custom_headers:
            headers.update(custom_headers)
        return headers
    
    def get_odoo_config(self, version: str = "17.0") -> Dict:
        """Get Odoo-specific configuration."""
        config = ODOO_CONFIG.copy()
        config["version"] = version
        config["base_urls"] = ODOO_CONFIG["base_urls"].get(version, ODOO_CONFIG["base_urls"]["17.0"])
        return config
    
    def get_selenium_config(self) -> Dict:
        """Get Selenium-specific configuration."""
        return SELENIUM_CONFIG.copy()
    
    def is_url_allowed(self, url: str) -> bool:
        """Check if URL domain is allowed for scraping."""
        from urllib.parse import urlparse
        domain = urlparse(url).netloc.lower()
        
        # Remove www. prefix for comparison
        if domain.startswith('www.'):
            domain = domain[4:]
        
        return any(allowed in domain for allowed in ALLOWED_DOMAINS)
    
    def should_skip_url(self, url: str) -> bool:
        """Check if URL should be skipped based on extension or patterns."""
        url_lower = url.lower()
        
        # Check file extensions
        if any(url_lower.endswith(ext) for ext in SKIP_EXTENSIONS):
            return True
        
        # Check exclude patterns for Odoo
        if any(pattern in url_lower for pattern in ODOO_CONFIG["exclude_patterns"]):
            return True
        
        return False


# Environment-based configuration
def get_config_from_env() -> ScraperConfig:
    """Create configuration from environment variables."""
    config_dict = {}
    
    # Check for environment variables
    if chunk_size := os.getenv("SCRAPER_CHUNK_SIZE"):
        config_dict["chunk_size"] = int(chunk_size)
    
    if chunk_overlap := os.getenv("SCRAPER_CHUNK_OVERLAP"):
        config_dict["chunk_overlap"] = int(chunk_overlap)
    
    if batch_size := os.getenv("SCRAPER_BATCH_SIZE"):
        config_dict["batch_size"] = int(batch_size)
    
    if max_depth := os.getenv("SCRAPER_MAX_DEPTH"):
        config_dict["max_depth"] = int(max_depth)
    
    if delay := os.getenv("SCRAPER_DELAY"):
        config_dict["delay_between_requests"] = float(delay)
    
    if timeout := os.getenv("SCRAPER_TIMEOUT"):
        config_dict["timeout"] = int(timeout)
    
    return ScraperConfig(config_dict)


# Predefined configurations for different use cases
CONFIGS = {
    "fast": {
        "chunk_size": 800,
        "chunk_overlap": 100,
        "batch_size": 10,
        "max_depth": 1,
        "delay_between_requests": 0.5,
    },
    "thorough": {
        "chunk_size": 1500,
        "chunk_overlap": 300,
        "batch_size": 3,
        "max_depth": 4,
        "delay_between_requests": 2.0,
    },
    "balanced": {
        "chunk_size": 1000,
        "chunk_overlap": 200,
        "batch_size": 5,
        "max_depth": 2,
        "delay_between_requests": 1.0,
    },
    "odoo_docs": {
        **ODOO_CONFIG,
        "delay_between_requests": 1.5,
        "max_retries": 5,
    }
}


def get_preset_config(preset_name: str) -> ScraperConfig:
    """Get a preset configuration."""
    if preset_name not in CONFIGS:
        raise ValueError(f"Unknown preset: {preset_name}. Available presets: {list(CONFIGS.keys())}")
    
    return ScraperConfig(CONFIGS[preset_name])


# Usage examples
if __name__ == "__main__":
    # Example usage of configuration
    
    # Default configuration
    config = ScraperConfig()
    print(f"Default chunk size: {config.get('chunk_size')}")
    
    # Custom configuration
    custom_config = ScraperConfig({"chunk_size": 1500, "batch_size": 10})
    print(f"Custom chunk size: {custom_config.get('chunk_size')}")
    
    # Preset configuration
    fast_config = get_preset_config("fast")
    print(f"Fast config chunk size: {fast_config.get('chunk_size')}")
    
    # Environment-based configuration
    env_config = get_config_from_env()
    print(f"Environment config: {env_config.config}")
    
    # URL validation
    print(f"odoo.com allowed: {config.is_url_allowed('https://www.odoo.com/documentation')}")
    print(f"example.com allowed: {config.is_url_allowed('https://example.com')}")
    print(f"Skip PDF: {config.should_skip_url('https://odoo.com/file.pdf')}")
