# Architecture & Design Decisions

## 🏛️ System Architecture

### High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        Apify Actor                              │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌──────────────────────────────────────────────────────┐    │
│  │              Entry Point (main.py)                    │    │
│  └──────────────────┬───────────────────────────────────┘    │
│                     │                                          │
│                     ▼                                          │
│  ┌──────────────────────────────────────────────────────┐    │
│  │         StealthBrowser Configuration                  │    │
│  │  - Browser launch with stealth args                   │    │
│  │  - User-agent rotation                                │    │
│  │  - Fingerprint evasion scripts                        │    │
│  └──────────────────┬───────────────────────────────────┘    │
│                     │                                          │
│                     ▼                                          │
│  ┌──────────────────────────────────────────────────────┐    │
│  │           Apify Proxy Integration                     │    │
│  │  - RESIDENTIAL/SHADER/GOOGLE_SERP                     │    │
│  │  - Automatic IP rotation                              │    │
│  └──────────────────┬───────────────────────────────────┘    │
│                     │                                          │
│                     ▼                                          │
│  ┌──────────────────────────────────────────────────────┐    │
│  │         Network Interception Layer                    │    │
│  │  ┌────────────────────────────────────────────┐     │    │
│  │  │  NetworkInterceptor                         │     │    │
│  │  │  - Route handler setup                      │     │    │
│  │  │  - Capture XHR/GraphQL responses            │     │    │
│  │  │  - Filter by API patterns                   │     │    │
│  │  └────────────────┬───────────────────────────┘     │    │
│  └───────────────────┼───────────────────────────────────┘    │
│                      │                                         │
│        ┌─────────────┴──────────────┐                         │
│        ▼                            ▼                         │
│  ┌──────────┐              ┌──────────────┐                  │
│  │   API    │              │     DOM      │                  │
│  │ Parsing  │  FALLBACK    │  Scraping    │                  │
│  │ (Primary)│─────────────▶│ (Secondary)  │                  │
│  └────┬─────┘              └──────┬───────┘                  │
│       │                           │                           │
│       └────────────┬──────────────┘                           │
│                    ▼                                          │
│  ┌──────────────────────────────────────────────────────┐    │
│  │         Data Processing Pipeline                      │    │
│  │  1. Extract raw data                                  │    │
│  │  2. Normalize fields                                  │    │
│  │  3. Parse dates & amounts                             │    │
│  │  4. Generate content hash                             │    │
│  └──────────────────┬───────────────────────────────────┘    │
│                     ▼                                          │
│  ┌──────────────────────────────────────────────────────┐    │
│  │         DeduplicationManager                          │    │
│  │  - Hash-based duplicate detection                     │    │
│  │  - In-memory seen set                                 │    │
│  └──────────────────┬───────────────────────────────────┘    │
│                     ▼                                          │
│  ┌──────────────────────────────────────────────────────┐    │
│  │         Apify Dataset Storage                         │    │
│  │  - Push unique records                                │    │
│  │  - Structured JSON output                             │    │
│  └──────────────────────────────────────────────────────┘    │
│                                                                 │
│  ┌──────────────────────────────────────────────────────┐    │
│  │         Monitoring & Metrics                          │    │
│  │  - ScraperMetrics tracking                            │    │
│  │  - Error logging                                      │    │
│  │  - Performance metrics                                │    │
│  └──────────────────────────────────────────────────────┘    │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

## 🧩 Component Design

### 1. NetworkInterceptor

**Purpose**: Primary data extraction via API interception

**Key Methods**:
- `intercept_route()`: Captures network requests matching API patterns
- `extract_funding_records()`: Parses captured JSON responses
- `_find_funding_items()`: Recursively searches for funding data in responses
- `_parse_funding_item()`: Extracts structured data from API items

**Design Decisions**:
- ✅ Non-blocking route interception
- ✅ Content-type validation (JSON only)
- ✅ Flexible path traversal for varying API schemas
- ✅ Graceful degradation if parsing fails

**Why This Approach?**:
- More reliable than DOM parsing
- Survives UI redesigns
- Faster extraction
- Already structured data

### 2. DOMScraper

**Purpose**: Fallback extraction when API interception fails

**Key Methods**:
- `extract_funding_records()`: Main entry point for DOM scraping
- `_extract_from_element()`: Extracts data from single DOM element
- `_extract_text()`: Multi-selector text extraction with fallback

**Design Decisions**:
- ✅ Semantic selectors (flexible, not brittle)
- ✅ Multiple selector attempts with priority
- ✅ Regex-based amount/date parsing
- ✅ Graceful handling of missing elements

**Selector Strategy**:
```python
# Priority order: most specific → most generic
[
    '[data-testid*="funding"]',  # Test IDs
    '[class*="funding-card"]',   # Semantic classes
    'article',                    # HTML5 semantic elements
    '[role="article"]'            # ARIA roles
]
```

### 3. StealthBrowser

**Purpose**: Evade bot detection and fingerprinting

**Key Methods**:
- `create_stealth_context()`: Configures stealth browser
- `simulate_human_behavior()`: Realistic user actions

**Anti-Detection Techniques**:

| Technique | Implementation | Why |
|-----------|----------------|-----|
| Navigator Override | Mask `navigator.webdriver` | Primary bot detection signal |
| Chrome Object | Inject fake `window.chrome` | Missing in automation browsers |
| Plugin Spoofing | Mock `navigator.plugins` | Automation has empty list |
| Permissions | Override permission queries | Realistic browser behavior |
| Viewport | 1920x1080 standard desktop | Most common resolution |
| Geolocation | New York coordinates | Believable US location |
| User-Agent | Rotate realistic UAs | Avoids static fingerprinting |

**Human Behavior Simulation**:
```python
# Random scroll patterns
scroll_steps = random.randint(3, 6)
scroll_amount = random.randint(300, 800)

# Variable delays
await asyncio.sleep(random.uniform(0.5, 1.5))

# Mouse movements
simulate via JavaScript events
```

### 4. PaginationHandler

**Purpose**: Handle infinite scroll and pagination

**Key Methods**:
- `handle_pagination()`: Detect and click "Next" buttons
- `handle_infinite_scroll()`: Trigger dynamic content loading

**Strategy**:
```
1. Try multiple "Next" selectors (flexible)
2. Wait for network idle after navigation
3. Simulate human behavior after each page
4. Track URLs to avoid loops
5. Respect max_pages limit
```

### 5. DeduplicationManager

**Purpose**: Prevent duplicate records across runs

**Key Methods**:
- `is_duplicate()`: Check hash against seen set
- `get_unique_records()`: Filter duplicates from batch

**Hashing Strategy**:
```python
# Deterministic hash from key fields
hash_content = f"{company_name}|{round_type}|{date}|{amount}"
hash_value = hashlib.sha256(hash_content.encode()).hexdigest()[:16]
```

**Why SHA-256**:
- Collision-resistant
- Fast computation
- Deterministic output
- Short hash (16 chars sufficient)

### 6. BlockingDetector

**Purpose**: Identify blocking, CAPTCHAs, rate limiting

**Detection Patterns**:
```python
CAPTCHA: ['captcha', 'recaptcha', 'verify you are human']
RATE_LIMIT: ['rate limit', 'too many requests', '429']
ACCESS_DENIED: ['access denied', 'forbidden', '403']
```

**Actions on Detection**:
- CAPTCHA → Abort run (graceful failure)
- Rate Limit → Wait 10s, then retry
- Access Denied → Abort run

## 🔄 Data Flow

### Extraction Pipeline

```
Raw Data (API/DOM)
    ↓
Parse & Extract Fields
    ↓
Normalize Data Types
    ├── Parse dates → ISO format
    ├── Parse amounts → Float USD
    └── Clean text → Strip whitespace
    ↓
Generate Content Hash
    ↓
Check Deduplication
    ├── Is Duplicate? → Skip
    └── Is Unique? → Continue
    ↓
Create FundingRecord Object
    ↓
Convert to Dictionary
    ↓
Push to Apify Dataset
    ↓
Update Metrics
```

### Error Handling Flow

```
Function Call
    ↓
Try Execute
    ↓
    ├─ Success → Return Result
    │
    └─ Error → Check Retry Count
              ↓
              ├─ Retries Left?
              │  ↓
              │  Calculate Backoff: 2^attempt + random(0,1)
              │  ↓
              │  Wait (exponential backoff)
              │  ↓
              │  Retry
              │
              └─ No Retries → Log Error & Raise
```

## 🎯 Design Patterns

### 1. Strategy Pattern
**Where**: Data extraction (API vs DOM)
**Why**: Easy to switch between strategies based on availability

### 2. Observer Pattern
**Where**: Network interception
**Why**: Non-blocking response capture

### 3. Factory Pattern
**Where**: FundingRecord creation
**Why**: Consistent object instantiation with validation

### 4. Template Method Pattern
**Where**: Scraping workflow
**Why**: Standard flow with customizable steps

### 5. Singleton Pattern
**Where**: DeduplicationManager, ScraperMetrics
**Why**: Single source of truth for state

## 🔐 Security Considerations

### 1. Data Privacy
- ✅ No personal data collection
- ✅ No authentication/login required
- ✅ Public data only
- ✅ Respects robots.txt (when configured)

### 2. API Keys
- ✅ Environment variables for tokens
- ✅ Never commit credentials
- ✅ Use Apify Secrets in production

### 3. Rate Limiting
- ✅ Human-like delays
- ✅ Configurable page limits
- ✅ Exponential backoff on errors
- ✅ Proxy rotation

## 📊 Performance Optimization

### 1. Memory Management
```python
# Efficient data structures
seen_hashes: set[str]  # O(1) lookup
captured_responses: list[dict]  # Limited by page count

# Clear after processing
del interceptor
await page.close()
```

### 2. Network Optimization
```python
# Parallel tasks where possible
await asyncio.gather(
    page.wait_for_load_state('networkidle'),
    page.wait_for_selector('selector', timeout=5000)
)

# Timeout management
page.set_default_timeout(30000)
page.set_default_navigation_timeout(60000)
```

### 3. Resource Usage
- Browser instances limited to 1 per run
- Context reused across pages
- Automatic cleanup via async context managers

## 🧪 Testing Strategy

### Unit Tests (Recommended)
```python
# Test individual components
test_parse_funding_item()
test_deduplication()
test_hash_generation()
test_date_parsing()
test_amount_parsing()
```

### Integration Tests
```python
# Test component interactions
test_api_to_dataset_flow()
test_dom_fallback_trigger()
test_retry_mechanism()
```

### End-to-End Tests
```python
# Test complete scraping flow
test_full_scrape_with_api()
test_full_scrape_with_dom()
test_pagination_handling()
test_error_recovery()
```

## 🔄 Maintenance & Evolution

### Monitoring Points
1. **API Pattern Changes**: Check if interception still works
2. **DOM Structure Changes**: Verify selectors still match
3. **Blocking Increases**: Adjust stealth configuration
4. **Performance Degradation**: Optimize slow components

### Update Procedures
1. **API Patterns**: Update `API_PATTERNS` list
2. **Selectors**: Update in `DOMScraper` methods
3. **Field Parsing**: Update `_parse_funding_item()` logic
4. **Schema**: Update `FundingRecord` dataclass

### Version Control
```
v1.0.0 - Initial release
v1.1.0 - Add new data fields
v1.2.0 - Improve stealth config
v2.0.0 - Major API changes
```

## 📈 Scalability

### Horizontal Scaling
```python
# Multiple Actor instances
- Split URLs across runs
- Use Apify Request Queue
- Implement distributed deduplication
```

### Vertical Scaling
```python
# Optimize single instance
- Increase memory allocation
- Use faster proxies
- Parallelize page processing
```

## 🎓 Key Learnings & Best Practices

### 1. Prioritize API Interception
- More stable than DOM parsing
- Faster and more reliable
- Better data quality

### 2. Flexible Selectors
- Use semantic HTML/ARIA
- Multiple fallback options
- Avoid brittle class names

### 3. Human-Like Behavior
- Random delays essential
- Scroll patterns matter
- Mouse movements help

### 4. Error Recovery
- Exponential backoff works
- Graceful degradation important
- Log everything for debugging

### 5. Deduplication
- Hash key fields only
- Use fast data structures (sets)
- Clear state between runs

---

**Architecture Document Version**: 1.0.0  
**Last Updated**: February 2026  
**Author**: Senior Python Scraping Engineer
