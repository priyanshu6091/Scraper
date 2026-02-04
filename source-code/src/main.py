"""Crunchbase Funding Data Scraper - Production-Ready Apify Actor.

This Actor scrapes publicly accessible funding data from Crunchbase using a robust,
stealth-first approach that prioritizes API interception over DOM parsing.

Architecture:
- Network interception for XHR/GraphQL responses
- DOM fallback when API interception fails
- Stealth browser fingerprinting
- Apify Proxy with automatic rotation
- Content-based deduplication
- Human-like behavior simulation
- Structured error handling with retries

Author: Senior Python Scraping Engineer
Compatible with: Apify Playwright + Chrome Python template
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import random
import re
from dataclasses import asdict, dataclass, field
from datetime import datetime
from typing import Any, Optional
from urllib.parse import urljoin, urlparse

from apify import Actor
from dateutil import parser as date_parser
from fake_useragent import UserAgent
from playwright.async_api import (
    BrowserContext,
    Page,
    Route,
    async_playwright,
)

# ============================================================================
# CONFIGURATION CONSTANTS
# ============================================================================

# Default Crunchbase discovery URLs for recent funding rounds
DEFAULT_START_URLS = [
    'https://www.crunchbase.com/discover/funding-rounds',
    'https://www.crunchbase.com/hub/recent-funding-rounds',
]

# Stealth configuration for browser fingerprinting evasion
STEALTH_ARGS = [
    '--disable-blink-features=AutomationControlled',
    '--disable-dev-shm-usage',
    '--disable-gpu',
    '--no-sandbox',
    '--disable-setuid-sandbox',
    '--disable-web-security',
    '--disable-features=IsolateOrigins,site-per-process',
]

# Request timeout and retry configuration
NAVIGATION_TIMEOUT = 60000  # 60 seconds
REQUEST_TIMEOUT = 30000  # 30 seconds
MAX_RETRIES = 3
EXPONENTIAL_BACKOFF_BASE = 2

# Human-like behavior simulation ranges (in seconds)
SCROLL_DELAY_RANGE = (0.5, 1.5)
PAGE_LOAD_DELAY_RANGE = (2.0, 4.0)
ACTION_DELAY_RANGE = (0.3, 0.8)

# Pagination limits
MAX_PAGES_PER_RUN = 3
MAX_SCROLL_ATTEMPTS = 5

# API interception patterns
API_PATTERNS = [
    r'.*api\.crunchbase\.com.*',
    r'.*graphql.*',
    r'.*funding.*',
    r'.*search.*',
]


# ============================================================================
# DATA MODELS
# ============================================================================

@dataclass
class FundingRecord:
    """Normalized funding data structure with stable schema."""
    
    company_name: str
    company_url: str
    funding_round_type: Optional[str] = None
    funding_amount: Optional[str] = None
    funding_amount_usd: Optional[float] = None
    funding_date: Optional[str] = None
    funding_date_parsed: Optional[str] = None
    investors: list[str] = field(default_factory=list)
    source_url: str = ''
    scraped_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    record_hash: str = ''
    extraction_method: str = 'unknown'  # 'api' or 'dom'
    
    def __post_init__(self):
        """Generate content hash for deduplication."""
        # Create a deterministic hash from key fields
        hash_content = f"{self.company_name}|{self.funding_round_type}|{self.funding_date}|{self.funding_amount}"
        self.record_hash = hashlib.sha256(hash_content.encode()).hexdigest()[:16]
    
    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for Apify dataset."""
        return asdict(self)


@dataclass
class ScraperMetrics:
    """Metrics and diagnostics for monitoring scraper health."""
    
    pages_processed: int = 0
    records_extracted: int = 0
    records_deduplicated: int = 0
    api_responses_intercepted: int = 0
    dom_fallback_count: int = 0
    errors_encountered: int = 0
    captcha_detected: bool = False
    blocking_detected: bool = False
    start_time: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    end_time: Optional[str] = None


# ============================================================================
# NETWORK INTERCEPTION & API PARSING
# ============================================================================

class NetworkInterceptor:
    """Captures and parses internal API responses from Crunchbase."""
    
    def __init__(self):
        self.captured_responses: list[dict[str, Any]] = []
        self.api_data_found = False
    
    async def intercept_route(self, route: Route) -> None:
        """Intercept network requests and capture API responses."""
        url = route.request.url
        
        # Check if URL matches API patterns
        is_api_request = any(re.search(pattern, url, re.IGNORECASE) for pattern in API_PATTERNS)
        
        if is_api_request:
            try:
                # Continue the request and capture the response
                response = await route.fetch()
                
                # Only process JSON responses
                content_type = response.headers.get('content-type', '')
                if 'application/json' in content_type:
                    body = await response.json()
                    
                    self.captured_responses.append({
                        'url': url,
                        'status': response.status,
                        'data': body,
                        'timestamp': datetime.utcnow().isoformat(),
                    })
                    
                    self.api_data_found = True
                    Actor.log.info(f'📡 Intercepted API response from: {urlparse(url).path}')
                
                await route.fulfill(response=response)
            except Exception as e:
                Actor.log.warning(f'Failed to intercept API response: {e}')
                await route.continue_()
        else:
            await route.continue_()
    
    def extract_funding_records(self, source_url: str) -> list[FundingRecord]:
        """Parse funding records from captured API responses."""
        records = []
        
        for response_data in self.captured_responses:
            try:
                data = response_data.get('data', {})
                
                # Attempt to extract funding data from various response structures
                # Crunchbase API can have different schemas
                funding_items = self._find_funding_items(data)
                
                for item in funding_items:
                    record = self._parse_funding_item(item, source_url)
                    if record:
                        records.append(record)
            
            except Exception as e:
                Actor.log.warning(f'Failed to parse API response: {e}')
        
        return records
    
    def _find_funding_items(self, data: dict[str, Any]) -> list[dict[str, Any]]:
        """Recursively search for funding-related items in API response."""
        items = []
        
        # Common paths in Crunchbase API responses
        potential_paths = [
            data.get('entities', []),
            data.get('results', []),
            data.get('items', []),
            data.get('data', {}).get('entities', []),
            data.get('data', {}).get('results', []),
        ]
        
        for path in potential_paths:
            if isinstance(path, list) and path:
                items.extend(path)
        
        # If no items found, check if data itself is a list
        if not items and isinstance(data, list):
            items = data
        
        return items
    
    def _parse_funding_item(self, item: dict[str, Any], source_url: str) -> Optional[FundingRecord]:
        """Extract funding record fields from API item."""
        try:
            # Extract company information
            company_name = (
                item.get('properties', {}).get('organization_name') or
                item.get('organization', {}).get('name') or
                item.get('name') or
                'Unknown Company'
            )
            
            # Extract company URL
            company_identifier = (
                item.get('properties', {}).get('organization_identifier') or
                item.get('organization', {}).get('identifier') or
                item.get('identifier')
            )
            
            company_url = f'https://www.crunchbase.com/organization/{company_identifier}' if company_identifier else ''
            
            # Extract funding round type
            funding_round_type = (
                item.get('properties', {}).get('funding_round_type') or
                item.get('funding_type') or
                item.get('type')
            )
            
            # Extract funding amount
            funding_amount = item.get('properties', {}).get('money_raised') or item.get('money_raised')
            funding_amount_usd = None
            
            if isinstance(funding_amount, dict):
                funding_amount_usd = funding_amount.get('value')
                currency = funding_amount.get('currency', 'USD')
                funding_amount = f"{funding_amount_usd} {currency}" if funding_amount_usd else None
            
            # Extract funding date
            funding_date = (
                item.get('properties', {}).get('announced_on') or
                item.get('announced_on') or
                item.get('date')
            )
            
            funding_date_parsed = None
            if funding_date:
                try:
                    parsed = date_parser.parse(str(funding_date))
                    funding_date_parsed = parsed.strftime('%Y-%m-%d')
                except:
                    pass
            
            # Extract investors
            investors = []
            investor_data = (
                item.get('properties', {}).get('investors') or
                item.get('investors') or
                []
            )
            
            if isinstance(investor_data, list):
                for inv in investor_data:
                    if isinstance(inv, dict):
                        inv_name = inv.get('name') or inv.get('identifier')
                        if inv_name:
                            investors.append(inv_name)
                    elif isinstance(inv, str):
                        investors.append(inv)
            
            # Create record
            record = FundingRecord(
                company_name=company_name,
                company_url=company_url,
                funding_round_type=funding_round_type,
                funding_amount=funding_amount,
                funding_amount_usd=funding_amount_usd,
                funding_date=funding_date,
                funding_date_parsed=funding_date_parsed,
                investors=investors,
                source_url=source_url,
                extraction_method='api',
            )
            
            return record
        
        except Exception as e:
            Actor.log.warning(f'Failed to parse funding item: {e}')
            return None


# ============================================================================
# DOM FALLBACK SCRAPING
# ============================================================================

class DOMScraper:
    """Fallback scraper using semantic DOM selectors."""
    
    @staticmethod
    async def extract_funding_records(page: Page, source_url: str) -> list[FundingRecord]:
        """Extract funding records from DOM when API interception fails."""
        records = []
        
        try:
            # Wait for content to load
            await page.wait_for_load_state('networkidle', timeout=10000)
            
            # Use semantic selectors to find funding cards/rows
            # These selectors are intentionally flexible to survive UI changes
            potential_selectors = [
                '[data-testid*="funding"]',
                '[class*="funding-card"]',
                '[class*="FundingCard"]',
                '[class*="search-result"]',
                '[class*="SearchResult"]',
                'article',
                '[role="article"]',
            ]
            
            funding_elements = []
            for selector in potential_selectors:
                elements = await page.locator(selector).all()
                if elements:
                    funding_elements = elements
                    Actor.log.info(f'Found {len(elements)} elements using selector: {selector}')
                    break
            
            if not funding_elements:
                Actor.log.warning('No funding elements found via DOM selectors')
                return records
            
            # Extract data from each element
            for idx, element in enumerate(funding_elements[:50]):  # Limit to prevent excessive processing
                try:
                    record = await DOMScraper._extract_from_element(element, source_url)
                    if record:
                        records.append(record)
                except Exception as e:
                    Actor.log.warning(f'Failed to extract data from element {idx}: {e}')
        
        except Exception as e:
            Actor.log.error(f'DOM scraping failed: {e}')
        
        return records
    
    @staticmethod
    async def _extract_from_element(element, source_url: str) -> Optional[FundingRecord]:
        """Extract funding data from a single DOM element."""
        try:
            # Extract company name
            company_name = await DOMScraper._extract_text(element, [
                '[class*="company-name"]',
                '[class*="organization-name"]',
                'h2', 'h3', 'h4',
                'a[href*="/organization/"]',
            ])
            
            if not company_name:
                return None
            
            # Extract company URL
            company_url = ''
            link = await element.locator('a[href*="/organization/"]').first.get_attribute('href')
            if link:
                company_url = urljoin('https://www.crunchbase.com', link)
            
            # Extract funding round type
            funding_round_type = await DOMScraper._extract_text(element, [
                '[class*="round-type"]',
                '[class*="funding-type"]',
                '[class*="FundingType"]',
            ])
            
            # Extract funding amount
            funding_amount = await DOMScraper._extract_text(element, [
                '[class*="amount"]',
                '[class*="money"]',
                '[class*="raised"]',
            ])
            
            # Parse amount
            funding_amount_usd = None
            if funding_amount:
                match = re.search(r'[\$€£]?\s*([\d,\.]+)\s*([MBK])?', funding_amount, re.IGNORECASE)
                if match:
                    amount_str = match.group(1).replace(',', '')
                    multiplier_map = {'K': 1_000, 'M': 1_000_000, 'B': 1_000_000_000}
                    multiplier = multiplier_map.get(match.group(2).upper(), 1) if match.group(2) else 1
                    try:
                        funding_amount_usd = float(amount_str) * multiplier
                    except:
                        pass
            
            # Extract funding date
            funding_date = await DOMScraper._extract_text(element, [
                '[class*="date"]',
                '[class*="announced"]',
                'time',
            ])
            
            funding_date_parsed = None
            if funding_date:
                try:
                    parsed = date_parser.parse(funding_date, fuzzy=True)
                    funding_date_parsed = parsed.strftime('%Y-%m-%d')
                except:
                    pass
            
            # Extract investors
            investors = []
            investor_text = await DOMScraper._extract_text(element, [
                '[class*="investor"]',
                '[class*="lead"]',
            ])
            
            if investor_text:
                # Split on common delimiters
                investors = [inv.strip() for inv in re.split(r'[,;]|\band\b', investor_text) if inv.strip()]
            
            record = FundingRecord(
                company_name=company_name,
                company_url=company_url,
                funding_round_type=funding_round_type,
                funding_amount=funding_amount,
                funding_amount_usd=funding_amount_usd,
                funding_date=funding_date,
                funding_date_parsed=funding_date_parsed,
                investors=investors,
                source_url=source_url,
                extraction_method='dom',
            )
            
            return record
        
        except Exception as e:
            Actor.log.warning(f'Element extraction failed: {e}')
            return None
    
    @staticmethod
    async def _extract_text(element, selectors: list[str]) -> str:
        """Try multiple selectors to extract text."""
        for selector in selectors:
            try:
                locator = element.locator(selector).first
                text = await locator.text_content(timeout=1000)
                if text and text.strip():
                    return text.strip()
            except:
                continue
        return ''


# ============================================================================
# BROWSER STEALTH & FINGERPRINTING
# ============================================================================

class StealthBrowser:
    """Manages stealth browser configuration and human-like behavior."""
    
    def __init__(self):
        self.user_agent_generator = UserAgent()
    
    async def create_stealth_context(
        self,
        playwright,
        proxy_config: Optional[dict[str, Any]] = None
    ) -> BrowserContext:
        """Create a browser context with stealth configuration."""
        
        # Generate realistic user agent
        user_agent = self.user_agent_generator.random
        
        Actor.log.info(f'🎭 Using User-Agent: {user_agent[:50]}...')
        
        # Launch browser with stealth arguments
        browser = await playwright.chromium.launch(
            headless=Actor.configuration.headless,
            args=STEALTH_ARGS,
            proxy=proxy_config,
        )
        
        # Create context with realistic viewport and headers
        context = await browser.new_context(
            viewport={'width': 1920, 'height': 1080},
            user_agent=user_agent,
            locale='en-US',
            timezone_id='America/New_York',
            permissions=['geolocation'],
            geolocation={'latitude': 40.7128, 'longitude': -74.0060},  # New York
            color_scheme='light',
            device_scale_factor=1,
            has_touch=False,
            is_mobile=False,
            java_script_enabled=True,
        )
        
        # Inject stealth scripts to evade detection
        await context.add_init_script("""
            // Override navigator.webdriver
            Object.defineProperty(navigator, 'webdriver', {
                get: () => undefined
            });
            
            // Mock chrome object
            window.chrome = {
                runtime: {},
                loadTimes: function() {},
                csi: function() {},
                app: {}
            };
            
            // Mock permissions
            const originalQuery = window.navigator.permissions.query;
            window.navigator.permissions.query = (parameters) => (
                parameters.name === 'notifications' ?
                Promise.resolve({ state: Notification.permission }) :
                originalQuery(parameters)
            );
            
            // Mock plugins
            Object.defineProperty(navigator, 'plugins', {
                get: () => [1, 2, 3, 4, 5]
            });
            
            // Mock languages
            Object.defineProperty(navigator, 'languages', {
                get: () => ['en-US', 'en']
            });
        """)
        
        Actor.log.info('✅ Stealth browser context created')
        
        return context
    
    @staticmethod
    async def simulate_human_behavior(page: Page) -> None:
        """Simulate realistic human browsing patterns."""
        try:
            # Random initial delay
            await asyncio.sleep(random.uniform(*PAGE_LOAD_DELAY_RANGE))
            
            # Simulate realistic scrolling
            viewport_height = page.viewport_size['height']
            scroll_steps = random.randint(3, 6)
            
            for _ in range(scroll_steps):
                # Scroll by random amount
                scroll_amount = random.randint(int(viewport_height * 0.3), int(viewport_height * 0.8))
                await page.evaluate(f'window.scrollBy(0, {scroll_amount})')
                
                # Random delay between scrolls
                await asyncio.sleep(random.uniform(*SCROLL_DELAY_RANGE))
            
            # Random mouse movements (simulated via evaluate)
            await page.evaluate("""
                () => {
                    const event = new MouseEvent('mousemove', {
                        view: window,
                        bubbles: true,
                        cancelable: true,
                        clientX: Math.random() * window.innerWidth,
                        clientY: Math.random() * window.innerHeight
                    });
                    document.dispatchEvent(event);
                }
            """)
            
        except Exception as e:
            Actor.log.warning(f'Human behavior simulation failed: {e}')


# ============================================================================
# PAGINATION & INFINITE SCROLL HANDLER
# ============================================================================

class PaginationHandler:
    """Handles cursor-based pagination and infinite scrolling."""
    
    @staticmethod
    async def handle_pagination(page: Page, max_pages: int) -> list[str]:
        """Detect and navigate through pagination."""
        page_urls = [page.url]
        
        for page_num in range(1, max_pages):
            try:
                # Look for "Next" button or pagination link
                next_selectors = [
                    'a[rel="next"]',
                    'button:has-text("Next")',
                    '[aria-label*="next" i]',
                    '[class*="next"]',
                    'a:has-text("Next")',
                ]
                
                next_button = None
                for selector in next_selectors:
                    try:
                        next_button = page.locator(selector).first
                        if await next_button.is_visible(timeout=2000):
                            break
                    except:
                        continue
                
                if not next_button:
                    Actor.log.info('No more pages to paginate')
                    break
                
                # Click next and wait for navigation
                Actor.log.info(f'Navigating to page {page_num + 1}')
                await next_button.click()
                await page.wait_for_load_state('networkidle', timeout=NAVIGATION_TIMEOUT)
                
                # Simulate human behavior
                await StealthBrowser.simulate_human_behavior(page)
                
                page_urls.append(page.url)
            
            except Exception as e:
                Actor.log.warning(f'Pagination failed at page {page_num + 1}: {e}')
                break
        
        return page_urls
    
    @staticmethod
    async def handle_infinite_scroll(page: Page, max_scrolls: int = MAX_SCROLL_ATTEMPTS) -> int:
        """Handle infinite scroll to load more content."""
        previous_height = await page.evaluate('document.body.scrollHeight')
        scroll_attempts = 0
        
        for attempt in range(max_scrolls):
            try:
                # Scroll to bottom
                await page.evaluate('window.scrollTo(0, document.body.scrollHeight)')
                await asyncio.sleep(random.uniform(*SCROLL_DELAY_RANGE))
                
                # Wait for new content to load
                await page.wait_for_timeout(2000)
                
                # Check if new content loaded
                new_height = await page.evaluate('document.body.scrollHeight')
                
                if new_height == previous_height:
                    Actor.log.info('No more content to load')
                    break
                
                previous_height = new_height
                scroll_attempts += 1
                
                Actor.log.info(f'Scrolled {scroll_attempts} times, new height: {new_height}')
            
            except Exception as e:
                Actor.log.warning(f'Infinite scroll failed: {e}')
                break
        
        return scroll_attempts


# ============================================================================
# DEDUPLICATION MANAGER
# ============================================================================

class DeduplicationManager:
    """Manages record deduplication using content hashing."""
    
    def __init__(self):
        self.seen_hashes: set[str] = set()
        self.duplicate_count = 0
    
    def is_duplicate(self, record: FundingRecord) -> bool:
        """Check if record is a duplicate."""
        if record.record_hash in self.seen_hashes:
            self.duplicate_count += 1
            return True
        
        self.seen_hashes.add(record.record_hash)
        return False
    
    def get_unique_records(self, records: list[FundingRecord]) -> list[FundingRecord]:
        """Filter out duplicate records."""
        unique_records = []
        
        for record in records:
            if not self.is_duplicate(record):
                unique_records.append(record)
        
        return unique_records


# ============================================================================
# RETRY & ERROR HANDLING
# ============================================================================

async def retry_with_exponential_backoff(
    func,
    max_retries: int = MAX_RETRIES,
    *args,
    **kwargs
) -> Any:
    """Execute function with exponential backoff retry logic."""
    
    for attempt in range(max_retries):
        try:
            return await func(*args, **kwargs)
        
        except Exception as e:
            if attempt == max_retries - 1:
                Actor.log.error(f'Failed after {max_retries} attempts: {e}')
                raise
            
            wait_time = EXPONENTIAL_BACKOFF_BASE ** attempt + random.uniform(0, 1)
            Actor.log.warning(f'Attempt {attempt + 1} failed: {e}. Retrying in {wait_time:.2f}s...')
            await asyncio.sleep(wait_time)


# ============================================================================
# DETECTION & BLOCKING HANDLERS
# ============================================================================

class BlockingDetector:
    """Detects CAPTCHAs, rate limiting, and blocking."""
    
    @staticmethod
    async def check_for_blocking(page: Page) -> dict[str, bool]:
        """Check if page shows signs of blocking or CAPTCHA."""
        status = {
            'captcha_detected': False,
            'rate_limited': False,
            'access_denied': False,
        }
        
        try:
            content = await page.content()
            title = await page.title()
            url = page.url
            
            # Check for CAPTCHA
            captcha_indicators = [
                'captcha',
                'recaptcha',
                'hcaptcha',
                'verify you are human',
                'security check',
            ]
            
            content_lower = content.lower()
            title_lower = title.lower()
            
            for indicator in captcha_indicators:
                if indicator in content_lower or indicator in title_lower:
                    status['captcha_detected'] = True
                    Actor.log.error(f'🚫 CAPTCHA detected: {indicator}')
                    break
            
            # Check for rate limiting
            rate_limit_indicators = [
                'rate limit',
                'too many requests',
                '429',
                'slow down',
            ]
            
            for indicator in rate_limit_indicators:
                if indicator in content_lower:
                    status['rate_limited'] = True
                    Actor.log.error(f'⚠️ Rate limiting detected: {indicator}')
                    break
            
            # Check for access denied
            access_denied_indicators = [
                'access denied',
                'forbidden',
                '403',
                'blocked',
            ]
            
            for indicator in access_denied_indicators:
                if indicator in content_lower or indicator in title_lower:
                    status['access_denied'] = True
                    Actor.log.error(f'🚫 Access denied: {indicator}')
                    break
        
        except Exception as e:
            Actor.log.warning(f'Blocking detection failed: {e}')
        
        return status


# ============================================================================
# MAIN ACTOR LOGIC
# ============================================================================

async def scrape_crunchbase_page(
    page: Page,
    url: str,
    dedup_manager: DeduplicationManager,
    metrics: ScraperMetrics,
) -> list[FundingRecord]:
    """Scrape a single Crunchbase page for funding data."""
    
    all_records = []
    
    try:
        Actor.log.info(f'🔍 Scraping: {url}')
        
        # Navigate to page with timeout
        await page.goto(url, wait_until='domcontentloaded', timeout=NAVIGATION_TIMEOUT)
        
        # Check for blocking
        blocking_status = await BlockingDetector.check_for_blocking(page)
        
        if blocking_status['captcha_detected']:
            metrics.captcha_detected = True
            raise Exception('CAPTCHA detected - aborting')
        
        if blocking_status['rate_limited']:
            Actor.log.warning('Rate limited - waiting before retry')
            await asyncio.sleep(10)
        
        if blocking_status['access_denied']:
            metrics.blocking_detected = True
            raise Exception('Access denied - aborting')
        
        # Simulate human behavior
        await StealthBrowser.simulate_human_behavior(page)
        
        # Set up network interception
        interceptor = NetworkInterceptor()
        await page.route('**/*', interceptor.intercept_route)
        
        # Wait for API calls to complete
        await page.wait_for_load_state('networkidle', timeout=REQUEST_TIMEOUT)
        
        # Additional wait to capture late API calls
        await asyncio.sleep(3)
        
        # Try to handle infinite scroll to load more content
        scrolls = await PaginationHandler.handle_infinite_scroll(page)
        Actor.log.info(f'Performed {scrolls} scroll attempts')
        
        # Extract records from API responses
        api_records = interceptor.extract_funding_records(url)
        
        if api_records:
            Actor.log.info(f'✅ Extracted {len(api_records)} records via API interception')
            metrics.api_responses_intercepted += 1
            all_records.extend(api_records)
        else:
            Actor.log.warning('No API data found, falling back to DOM scraping')
            metrics.dom_fallback_count += 1
            
            # Fallback to DOM scraping
            dom_records = await DOMScraper.extract_funding_records(page, url)
            
            if dom_records:
                Actor.log.info(f'✅ Extracted {len(dom_records)} records via DOM scraping')
                all_records.extend(dom_records)
            else:
                Actor.log.warning('No records found via DOM scraping either')
        
        # Remove route handler
        await page.unroute('**/*')
        
        # Deduplicate records
        unique_records = dedup_manager.get_unique_records(all_records)
        
        duplicates_removed = len(all_records) - len(unique_records)
        if duplicates_removed > 0:
            Actor.log.info(f'🔄 Removed {duplicates_removed} duplicate records')
            metrics.records_deduplicated += duplicates_removed
        
        metrics.records_extracted += len(unique_records)
        metrics.pages_processed += 1
        
        return unique_records
    
    except Exception as e:
        Actor.log.error(f'Failed to scrape page {url}: {e}')
        metrics.errors_encountered += 1
        raise


async def main() -> None:
    """Main entry point for the Crunchbase Funding Scraper Actor."""
    
    async with Actor:
        # Initialize metrics
        metrics = ScraperMetrics()
        dedup_manager = DeduplicationManager()
        
        # Get Actor input
        actor_input = await Actor.get_input() or {}
        start_urls = actor_input.get('start_urls', [{'url': url} for url in DEFAULT_START_URLS])
        max_pages = actor_input.get('max_pages', MAX_PAGES_PER_RUN)
        use_proxy = actor_input.get('use_apify_proxy', True)
        proxy_groups = actor_input.get('proxy_groups', ['RESIDENTIAL'])
        
        Actor.log.info('🚀 Starting Crunchbase Funding Scraper')
        Actor.log.info(f'📊 Configuration: max_pages={max_pages}, use_proxy={use_proxy}')
        
        # Configure Apify Proxy
        proxy_config = None
        if use_proxy:
            proxy_config = await Actor.create_proxy_configuration(
                groups=proxy_groups,
            )
            Actor.log.info(f'✅ Apify Proxy configured with groups: {proxy_groups}')
        
        # Launch Playwright with stealth configuration
        async with async_playwright() as playwright:
            stealth_browser = StealthBrowser()
            
            # Get proxy URL if enabled
            proxy_url = None
            if proxy_config:
                proxy_url = await proxy_config.new_url()
                proxy_dict = {
                    'server': proxy_url,
                }
            else:
                proxy_dict = None
            
            context = await stealth_browser.create_stealth_context(
                playwright,
                proxy_config=proxy_dict,
            )
            
            try:
                # Process each start URL
                for url_obj in start_urls:
                    url = url_obj.get('url')
                    
                    if not url:
                        continue
                    
                    try:
                        # Create new page for each URL
                        page = await context.new_page()
                        page.set_default_timeout(REQUEST_TIMEOUT)
                        page.set_default_navigation_timeout(NAVIGATION_TIMEOUT)
                        
                        # Scrape page with retry logic
                        records = await retry_with_exponential_backoff(
                            scrape_crunchbase_page,
                            page=page,
                            url=url,
                            dedup_manager=dedup_manager,
                            metrics=metrics,
                        )
                        
                        # Store records in Apify Dataset
                        if records:
                            for record in records:
                                await Actor.push_data(record.to_dict())
                            
                            Actor.log.info(f'💾 Stored {len(records)} unique records')
                        
                        # Handle pagination (limit to max_pages)
                        if max_pages > 1:
                            Actor.log.info(f'Checking for pagination (max {max_pages} pages)...')
                            page_urls = await PaginationHandler.handle_pagination(page, max_pages)
                            
                            # Scrape additional pages
                            for page_url in page_urls[1:]:  # Skip first URL (already scraped)
                                try:
                                    records = await retry_with_exponential_backoff(
                                        scrape_crunchbase_page,
                                        page=page,
                                        url=page_url,
                                        dedup_manager=dedup_manager,
                                        metrics=metrics,
                                    )
                                    
                                    if records:
                                        for record in records:
                                            await Actor.push_data(record.to_dict())
                                        
                                        Actor.log.info(f'💾 Stored {len(records)} unique records from page {page_url}')
                                
                                except Exception as e:
                                    Actor.log.error(f'Failed to scrape paginated page: {e}')
                        
                        await page.close()
                    
                    except Exception as e:
                        Actor.log.error(f'Failed to process URL {url}: {e}')
                        metrics.errors_encountered += 1
            
            finally:
                await context.close()
        
        # Finalize metrics
        metrics.end_time = datetime.utcnow().isoformat()
        
        # Log final statistics
        Actor.log.info('📊 ============ SCRAPING SUMMARY ============')
        Actor.log.info(f'Pages processed: {metrics.pages_processed}')
        Actor.log.info(f'Records extracted: {metrics.records_extracted}')
        Actor.log.info(f'Records deduplicated: {metrics.records_deduplicated}')
        Actor.log.info(f'API responses intercepted: {metrics.api_responses_intercepted}')
        Actor.log.info(f'DOM fallback count: {metrics.dom_fallback_count}')
        Actor.log.info(f'Errors encountered: {metrics.errors_encountered}')
        Actor.log.info(f'CAPTCHA detected: {metrics.captcha_detected}')
        Actor.log.info(f'Blocking detected: {metrics.blocking_detected}')
        Actor.log.info('============================================')
        
        # Store metrics as key-value store
        await Actor.set_value('METRICS', asdict(metrics))
        
        Actor.log.info('✅ Scraper completed successfully')
