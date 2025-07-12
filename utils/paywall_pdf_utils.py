##################################### ------ {logins, and downloads top #num pdfs to the dir and saves a csv file detials} ------#####################################


import os
import time
import logging
import csv
from typing import List, Dict, Optional, Tuple
from pathlib import Path
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.common.exceptions import TimeoutException, NoSuchElementException, WebDriverException
from webdriver_manager.chrome import ChromeDriverManager
import requests
from urllib.parse import urljoin, urlparse
import re

# Setup logger with proper configuration
def setup_logger(name: str = "paywalled_pdf_scraper", level: int = logging.INFO) -> logging.Logger:
    """
    Setup a logger with proper formatting and handlers
    
    Args:
        name: Logger name
        level: Logging level
    
    Returns:
        Configured logger instance
    """
    logger = logging.getLogger(name)
    logger.setLevel(level)
    
    # Prevent duplicate handlers
    if not logger.hasHandlers():
        handler = logging.StreamHandler()
        formatter = logging.Formatter(
            "%(asctime)s [%(name)s] %(levelname)s: %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S"
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)
    
    return logger

# Initialize logger
logger = setup_logger()

class PaywalledPDFScraper:
    """
    A robust utility class for scraping PDFs from paywalled websites using Selenium.
    
    This class handles:
    - Automated login to paywalled sites
    - PDF link discovery and extraction
    - Authenticated PDF downloads
    - Error handling and logging
    - Session management
    """
    
    def __init__(self, download_dir: str = "./downloads", headless: bool = False, 
                 timeout: int = 30, max_retries: int = 3):
        """
        Initialize the scraper with configuration options
        
        Args:
            download_dir: Directory to save downloaded PDFs
            headless: Run browser in headless mode
            timeout: Default timeout for web operations
            max_retries: Maximum number of retry attempts
        """
        self.download_dir = Path(download_dir)
        self.download_dir.mkdir(parents=True, exist_ok=True)
        self.headless = headless
        self.timeout = timeout
        self.max_retries = max_retries
        self.driver = None
        self.session = None
        
        logger.info(f"Scraper initialized with download_dir: {self.download_dir}")
        
    def setup_driver(self) -> webdriver.Chrome:
        """
        Setup Chrome driver with comprehensive options for stability and security
        
        Returns:
            Configured Chrome WebDriver instance
        """
        logger.info("Setting up Chrome driver...")
        
        try:
            chrome_options = Options()
            
            # Headless mode configuration
            if self.headless:
                chrome_options.add_argument("--headless")
                logger.info("Running in headless mode")
            
            # Essential Chrome options for stability
            chrome_options.add_argument("--no-sandbox")
            chrome_options.add_argument("--disable-dev-shm-usage")
            chrome_options.add_argument("--disable-gpu")
            chrome_options.add_argument("--disable-blink-features=AutomationControlled")
            chrome_options.add_argument("--window-size=1920,1080")
            chrome_options.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
            
            # Additional options for anti-detection
            chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
            chrome_options.add_experimental_option('useAutomationExtension', False)
            
            # Download preferences
            prefs = {
                "download.default_directory": str(self.download_dir.absolute()),
                "download.prompt_for_download": False,
                "download.directory_upgrade": True,
                "safebrowsing.enabled": True,
                "plugins.always_open_pdf_externally": True,
                "profile.default_content_setting_values.notifications": 2,
                "profile.default_content_settings.popups": 0
            }
            chrome_options.add_experimental_option("prefs", prefs)
            
            # Install and setup driver
            service = Service(ChromeDriverManager().install())
            driver = webdriver.Chrome(service=service, options=chrome_options)
            
            # Execute script to hide automation flags
            driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
            
            logger.info("Chrome driver setup completed successfully")
            return driver
            
        except Exception as e:
            logger.error(f"Failed to setup Chrome driver: {str(e)}")
            raise
    
    def login_to_site(self, login_url: str, username: str, password: str, 
                     username_field: str = "user_login", password_field: str = "user_pass",
                     submit_button: str = "wp-submit") -> bool:
        """
        Login to a paywalled website with configurable field selectors
        
        Args:
            login_url: URL of the login page
            username: Username for login
            password: Password for login
            username_field: ID/name of username field
            password_field: ID/name of password field
            submit_button: ID/name of submit button
        
        Returns:
            bool: True if login successful, False otherwise
        """
        logger.info(f"Attempting to login to {login_url}")
        
        if not username or not password:
            logger.error("Username or password is empty")
            return False
        
        try:
            # Navigate to login page
            self.driver.get(login_url)
            wait = WebDriverWait(self.driver, self.timeout)
            
            # Wait for page to load
            wait.until(EC.presence_of_element_located((By.TAG_NAME, "body")))
            logger.info("Login page loaded successfully")
            
            # Find and fill username field
            username_element = self._find_element_by_multiple_strategies(
                wait, username_field, "username field"
            )
            if not username_element:
                return False
                
            username_element.clear()
            username_element.send_keys(username)
            logger.info("Username field filled")
            
            # Find and fill password field
            password_element = self._find_element_by_multiple_strategies(
                wait, password_field, "password field"
            )
            if not password_element:
                return False
                
            password_element.clear()
            password_element.send_keys(password)
            logger.info("Password field filled")
            
            # Find and click submit button
            submit_element = self._find_element_by_multiple_strategies(
                wait, submit_button, "submit button"
            )
            if not submit_element:
                return False
                
            submit_element.click()
            logger.info("Submit button clicked")
            
            # Wait for navigation and check login success
            time.sleep(3)
            
            if self.check_login_success():
                logger.info("Login successful")
                return True
            else:
                logger.error("Login failed - authentication unsuccessful")
                return False
                
        except TimeoutException:
            logger.error("Login timeout - page elements not found within timeout period")
            return False
        except Exception as e:
            logger.error(f"Error during login: {str(e)}")
            return False
    
    def _find_element_by_multiple_strategies(self, wait: WebDriverWait, 
                                           identifier: str, field_name: str):
        """
        Find element using multiple strategies (ID, name, CSS selector)
        
        Args:
            wait: WebDriverWait instance
            identifier: Element identifier
            field_name: Human-readable field name for logging
        
        Returns:
            WebElement or None
        """
        strategies = [
            (By.ID, identifier),
            (By.NAME, identifier),
            (By.CSS_SELECTOR, f'#{identifier}'),
            (By.CSS_SELECTOR, f'[name="{identifier}"]'),
            (By.XPATH, f'//input[@id="{identifier}"]'),
            (By.XPATH, f'//input[@name="{identifier}"]')
        ]
        
        for by, value in strategies:
            try:
                element = wait.until(EC.presence_of_element_located((by, value)))
                logger.debug(f"Found {field_name} using {by}: {value}")
                return element
            except TimeoutException:
                continue
        
        logger.error(f"Could not find {field_name} with identifier: {identifier}")
        return None
    
    def check_login_success(self) -> bool:
        """
        Check if login was successful by analyzing URL and page content
        
        Returns:
            bool: True if login successful
        """
        try:
            current_url = self.driver.current_url.lower()
            page_source = self.driver.page_source.lower()
            
            # Success indicators
            success_indicators = [
                "dashboard", "profile", "logout", "welcome", "account", 
                "member", "subscriber", "user", "home"
            ]
            
            # Failure indicators
            failure_indicators = [
                "login", "signin", "sign-in", "error", "invalid", "incorrect"
            ]
            
            # Check for success indicators
            for indicator in success_indicators:
                if indicator in current_url or indicator in page_source:
                    logger.debug(f"Login success indicator found: {indicator}")
                    return True
            
            # Check for failure indicators
            for indicator in failure_indicators:
                if indicator in current_url:
                    logger.debug(f"Login failure indicator found in URL: {indicator}")
                    return False
            
            # Check for error messages in page source
            error_patterns = [
                r'error.*login', r'invalid.*credentials', r'incorrect.*password',
                r'login.*failed', r'authentication.*failed'
            ]
            
            for pattern in error_patterns:
                if re.search(pattern, page_source):
                    logger.debug(f"Login error pattern found: {pattern}")
                    return False
            
            # If no clear indicators, assume success if we're not on login page
            return "login" not in current_url
            
        except Exception as e:
            logger.error(f"Error checking login success: {str(e)}")
            return False
    
    def find_pdf_links(self, base_url: str, max_articles: int = 3) -> List[Dict[str, str]]:
        """
        Find PDF links from top 3 newsletter articles (using original working logic)
        
        Args:
            base_url: Base URL for resolving relative links
            max_articles: Maximum number of articles to process
        
        Returns:
            List of dictionaries containing PDF link information
        """
        logger.info("Collecting top 3 PDF links from newsletter articles...")
        pdf_links = []

        try:
            # Step 1: Get article URLs from the archive page (original selector)
            articles = self.driver.find_elements(By.CSS_SELECTOR, "article.elementor-post")
            if not articles:
                logger.warning("No articles found with selector 'article.elementor-post'")
                return pdf_links
                
            article_urls = []
            for article in articles:
                try:
                    a_tag = article.find_element(By.CSS_SELECTOR, "h3.elementor-post__title a")
                    href = a_tag.get_attribute("href")
                    if href:
                        article_urls.append(href)
                except Exception as e:
                    logger.warning(f"Error extracting URL from article: {str(e)}")
                    continue

            logger.info(f"Found {len(article_urls)} article URLs, using top {max_articles}.")

            # Step 2: Visit top articles and extract PDF links and H1 heading
            for i, url in enumerate(article_urls, 1):
                try:
                    logger.info(f"Visiting article page {i}/{len(article_urls)}: {url}")
                    self.driver.get(url)
                    time.sleep(2)

                    # Get article <h1> title (original XPath)
                    try:
                        h1_element = self.driver.find_element(By.XPATH, "/html/body/div[1]/div/div/section/div/div/div/div[2]/div/h1")
                        article_title = h1_element.text.strip()
                        sanitized_title = re.sub(r'[^\w\s-]', '', article_title)
                        sanitized_title = re.sub(r'\s+', '_', sanitized_title)
                        filename = f"{sanitized_title}.pdf"
                        logger.info(f"Extracted title: {article_title}")
                    except Exception as e:
                        logger.warning(f"Could not extract H1 title: {e}")
                        filename = f"document_{int(time.time())}.pdf"

                    # Find PDF link in that article
                    links = self.driver.find_elements(By.TAG_NAME, "a")
                    for link in links:
                        href = link.get_attribute("href")
                        text = link.text.strip()

                        if not href:
                            continue

                        if self.is_pdf_link(href, text):
                            full_url = urljoin(base_url, href) if href.startswith("/") else href
                            pdf_info = {
                                "url": full_url,
                                "text": text,
                                "title": filename
                            }
                            pdf_links.append(pdf_info)
                            logger.info(f"Found PDF link: {pdf_info['title']}")
                            break  # Only take one PDF per article
                            
                except Exception as e:
                    logger.error(f"Error processing article {url}: {str(e)}")
                    continue

            logger.info(f"Total PDFs found: {len(pdf_links)}")
            self.save_pdf_links_to_csv(pdf_links,"total_pdf_links.csv")

            return pdf_links

        except Exception as e:
            logger.error(f"Error finding PDF links from articles: {e}")
            return []
    
    def _extract_article_title(self) -> str:
        """
        Extract article title using multiple strategies
        
        Returns:
            Article title or default name
        """
        title_selectors = [
            "h1",
            ".entry-title",
            ".post-title",
            ".article-title",
            "title",
            "[class*='title']"
        ]
        
        for selector in title_selectors:
            try:
                elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                if elements:
                    title = elements[0].text.strip()
                    if title:
                        logger.debug(f"Extracted title: {title}")
                        return title
            except Exception:
                continue
        
        # Fallback to page title
        try:
            title = self.driver.title
            if title:
                return title
        except Exception:
            pass
        
        # Final fallback
        return f"document_{int(time.time())}"
    
    def _sanitize_filename(self, title: str) -> str:
        """
        Sanitize filename for safe file system usage
        
        Args:
            title: Original title
        
        Returns:
            Sanitized filename
        """
        # Remove or replace invalid characters
        sanitized = re.sub(r'[<>:"/\\|?*]', '', title)
        sanitized = re.sub(r'[^\w\s-]', '', sanitized)
        sanitized = re.sub(r'\s+', '_', sanitized)
        sanitized = sanitized.strip('_')
        
        # Ensure filename isn't too long
        if len(sanitized) > 100:
            sanitized = sanitized[:100]
        
        return f"{sanitized}.pdf"
    
    def _find_pdf_in_article(self, base_url: str) -> Optional[Dict[str, str]]:
        """
        Find PDF link within an article
        
        Args:
            base_url: Base URL for resolving relative links
        
        Returns:
            Dictionary with PDF link info or None
        """
        try:
            links = self.driver.find_elements(By.TAG_NAME, "a")
            
            for link in links:
                href = link.get_attribute("href")
                text = link.text.strip()
                
                if not href:
                    continue
                
                if self.is_pdf_link(href, text):
                    full_url = urljoin(base_url, href) if href.startswith("/") else href
                    return {
                        "url": full_url,
                        "text": text or "PDF Download"
                    }
            
            return None
            
        except Exception as e:
            logger.error(f"Error finding PDF in article: {str(e)}")
            return None
    
    def is_pdf_link(self, href: str, text: str) -> bool:
        """
        Enhanced PDF link detection with multiple criteria
        
        Args:
            href: URL of the link
            text: Text content of the link
        
        Returns:
            bool: True if likely a PDF link
        """
        if not href:
            return False
        
        href_lower = href.lower()
        text_lower = text.lower()
        
        # Direct PDF URL
        if href_lower.endswith('.pdf'):
            return True
        
        # PDF URL patterns
        pdf_url_patterns = [
            r'\.pdf(\?|$)',
            r'/pdf/',
            r'/docs/',
            r'/documents/',
            r'/reports/',
            r'/files/',
            r'download.*pdf',
            r'pdf.*download'
        ]
        
        for pattern in pdf_url_patterns:
            if re.search(pattern, href_lower):
                return True
        
        # Text indicators
        pdf_text_indicators = [
            'pdf', 'download', 'report', 'document', 'analysis',
            'whitepaper', 'research', 'study', 'paper'
        ]
        
        for indicator in pdf_text_indicators:
            if indicator in text_lower:
                return True
        
        return False
    
    def download_pdf(self, pdf_url: str, filename: str) -> bool:
        """
        Download PDF with enhanced error handling and verification
        
        Args:
            pdf_url: URL of the PDF
            filename: Local filename to save as
        
        Returns:
            bool: True if download successful
        """
        logger.info(f"Downloading PDF: {filename}")
        
        try:
            # Navigate to PDF URL
            self.driver.get(pdf_url)
            
            # Wait for download to start/complete
            download_wait_time = 10
            start_time = time.time()
            
            while time.time() - start_time < download_wait_time:
                downloaded_file = self.download_dir / filename
                if downloaded_file.exists() and downloaded_file.stat().st_size > 0:
                    logger.info(f"Successfully downloaded: {filename} ({downloaded_file.stat().st_size} bytes)")
                    return True
                time.sleep(1)
            
            # If direct download didn't work, try alternative method
            logger.warning(f"Direct download failed for {filename}, attempting alternative method")
            return self._download_pdf_with_requests(pdf_url, filename)
            
        except Exception as e:
            logger.error(f"Error downloading PDF {filename}: {str(e)}")
            return False
    
    def _download_pdf_with_requests(self, pdf_url: str, filename: str) -> bool:
        """
        Alternative PDF download using requests with selenium cookies
        
        Args:
            pdf_url: URL of the PDF
            filename: Local filename to save as
        
        Returns:
            bool: True if download successful
        """
        try:
            # Get cookies from selenium
            cookies = self.driver.get_cookies()
            session = requests.Session()
            
            for cookie in cookies:
                session.cookies.set(cookie['name'], cookie['value'])
            
            # Set headers to mimic browser
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                'Accept': 'application/pdf,*/*',
                'Accept-Language': 'en-US,en;q=0.9',
                'Accept-Encoding': 'gzip, deflate, br',
                'Connection': 'keep-alive',
                'Upgrade-Insecure-Requests': '1',
            }
            
            response = session.get(pdf_url, headers=headers, stream=True)
            response.raise_for_status()
            
            # Save PDF
            file_path = self.download_dir / filename
            with open(file_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
            
            if file_path.exists() and file_path.stat().st_size > 0:
                logger.info(f"Successfully downloaded via requests: {filename}")
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"Error downloading PDF via requests: {str(e)}")
            return False
    
    def save_pdf_links_to_csv(self, pdf_links: List[Dict[str, str]], 
                             filename: str = "pdf_links.csv") -> bool:
        """
        Save PDF links information to CSV file
        
        Args:
            pdf_links: List of PDF link dictionaries
            filename: CSV filename
        
        Returns:
            bool: True if saved successfully
        """
        try:
            csv_path = self.download_dir / filename
            with open(csv_path, "w", newline='', encoding="utf-8") as csvfile:
                fieldnames = ["title", "url", "text"]
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                writer.writeheader()
                
                for pdf in pdf_links:
                    writer.writerow({
                        "title": pdf.get("title", ""),
                        "url": pdf.get("url", ""),
                        "text": pdf.get("text", "")
                    })
            
            logger.info(f"Saved PDF links to {csv_path}")
            return True
            
        except Exception as e:
            logger.error(f"Error saving PDF links to CSV: {str(e)}")
            return False
    
    def scrape_paywalled_pdfs(self, login_url: str, username: str, password: str,
                             content_url: Optional[str] = None, 
                             max_pdfs: int = 3) -> List[str]:
        """
        Main method to scrape PDFs from paywalled content
        
        Args:
            login_url: URL of login page
            username: Username for login
            password: Password for login
            content_url: URL of content page (optional)
            max_pdfs: Maximum number of PDFs to download
        
        Returns:
            List of successfully downloaded PDF filenames
        """
        logger.info("Starting paywalled PDF scraping process...")
        downloaded_files = []
        
        try:
            # Setup driver
            self.driver = self.setup_driver()
            
            # Login to the site
            if not self.login_to_site(login_url, username, password):
                logger.error("Login failed, cannot proceed with scraping")
                return downloaded_files
            
            # Navigate to content page if specified
            if content_url:
                logger.info(f"Navigating to content page: {content_url}")
                self.driver.get(content_url)
                
                # Wait for content page to load
                WebDriverWait(self.driver, self.timeout).until(
                    EC.presence_of_element_located((By.TAG_NAME, "body"))
                )
            
            # Use the original base_url logic
            base_url = "https"
            
            # Find PDF links
            pdf_links = self.find_pdf_links(base_url, max_pdfs)
            
            if not pdf_links:
                logger.warning("No PDF links found")
                return downloaded_files
            
            # Download PDFs
            for i, pdf_info in enumerate(pdf_links[:max_pdfs], 1):
                logger.info(f"Downloading PDF {i}/{max_pdfs}: {pdf_info['title']}")
                
                if self.download_pdf(pdf_info["url"], pdf_info["title"]):
                    downloaded_files.append(pdf_info["title"])
                else:
                    logger.error(f"Failed to download: {pdf_info['title']}")
            
            # Save PDF links to CSV
            self.save_pdf_links_to_csv(pdf_links[:max_pdfs],"downloaded_pdfs_links.csv")
            
            logger.info(f"Scraping completed. Successfully downloaded {len(downloaded_files)} PDFs")
            return downloaded_files
            
        except Exception as e:
            logger.error(f"Error during PDF scraping: {str(e)}")
            return downloaded_files
        
        finally:
            # Cleanup
            if self.driver:
                try:
                    self.driver.quit()
                    logger.info("Browser driver closed successfully")
                except Exception as e:
                    logger.warning(f"Error closing driver: {str(e)}")
    
    def __enter__(self):
        """Context manager entry"""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit with proper cleanup"""
        if self.driver:
            try:
                self.driver.quit()
                logger.info("Driver closed via context manager")
            except Exception as e:
                logger.warning(f"Error closing driver in context manager: {str(e)}")

# Convenience function for easy usage
def scrape_pdfs_from_paywalled_site(login_url: str, username: str, password: str,
                                   content_url: Optional[str] = None, 
                                   download_dir: str = "./downloads",
                                   max_pdfs: int = 3,
                                   headless: bool = False) -> List[str]:
    """
    Convenience function to scrape PDFs from a paywalled site
    
    Args:
        login_url: URL of the login page
        username: Username for authentication
        password: Password for authentication
        content_url: URL of content page (optional)
        download_dir: Directory to save PDFs
        max_pdfs: Maximum number of PDFs to download
        headless: Run browser in headless mode
    
    Returns:
        List of downloaded PDF filenames
    """
    with PaywalledPDFScraper(download_dir=download_dir, headless=headless) as scraper:
        return scraper.scrape_paywalled_pdfs(
            login_url=login_url,
            username=username,
            password=password,
            content_url=content_url,
            max_pdfs=max_pdfs
        )

# # Example usage and main execution
# if __name__ == "__main__":
#     # Configuration - Replace with actual values
#     LOGIN_URL = "https:/"
#     USERNAME = "an"
#     PASSWORD = ""
#     CONTENT_URL = "ve/"  # Optional
    
#     # Validate configuration
#     if not all([LOGIN_URL, USERNAME, PASSWORD]):
#         logger.error("Please provide valid login credentials and URL")
#         exit(1)
    
#     try:
#         # Execute scraping
#         downloaded_files = scrape_pdfs_from_paywalled_site(
#             login_url=LOGIN_URL,
#             username=USERNAME,
#             password=PASSWORD,
#             content_url=CONTENT_URL,
#             download_dir="../investment_research_outputs/paywalled_content/downloads", #"./downloaded_pdfs",
#             max_pdfs=3,
#             headless=False #True  # Set to False for debugging
#         )
        
#         # Report results
#         if downloaded_files:
#             logger.info(f"✅ Successfully downloaded {len(downloaded_files)} files:")
#             for file in downloaded_files:
#                 logger.info(f"  - {file}")
#         else:
#             logger.warning("⚠️ No files were downloaded")
            
#     except KeyboardInterrupt:
#         logger.info("Process interrupted by user")
#     except Exception as e:
#         logger.error(f"Unexpected error: {str(e)}")
#     finally:
#         logger.info("Script execution completed")