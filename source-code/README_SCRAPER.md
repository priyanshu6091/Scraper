# Crunchbase Funding Data Scraper - Production Actor

## 🎯 Overview

A production-ready Apify Actor built with Python and Playwright that scrapes publicly accessible funding data from Crunchbase. This scraper uses enterprise-grade techniques including:

- **API Interception**: Captures internal XHR/GraphQL responses for reliable data extraction
- **DOM Fallback**: Automatic fallback to semantic DOM parsing when API data is unavailable
- **Stealth Configuration**: Advanced browser fingerprinting evasion and anti-detection measures
- **Proxy Rotation**: Built-in Apify Proxy support with automatic IP rotation
- **Human Behavior Simulation**: Realistic scrolling, delays, and interaction patterns
- **Smart Deduplication**: Content-based hashing to prevent duplicate records
- **Retry Logic**: Exponential backoff retry mechanism for resilient operation
- **CAPTCHA Detection**: Automatic detection of blocking, rate limiting, and CAPTCHAs

## 🏗️ Architecture

### Key Components

1. **NetworkInterceptor**: Captures and parses API responses from Crunchbase's internal endpoints
2. **DOMScraper**: Fallback scraper using flexible, semantic selectors
3. **StealthBrowser**: Manages browser fingerprinting evasion and realistic user-agent rotation
4. **PaginationHandler**: Handles both cursor-based pagination and infinite scrolling
5. **DeduplicationManager**: Prevents duplicate records using SHA-256 content hashing
6. **BlockingDetector**: Identifies CAPTCHAs, rate limiting, and access restrictions

### Data Flow

```
Start URLs → Stealth Browser → API Interception → Parse JSON
                                      ↓ (if fails)
                                 DOM Scraping → Parse HTML
                                      ↓
                              Deduplication → Dataset Storage
```

## 📊 Output Schema

Each funding record includes:

```json
{
  "company_name": "Example Corp",
  "company_url": "https://www.crunchbase.com/organization/example-corp",
  "funding_round_type": "Series A",
  "funding_amount": "10000000 USD",
  "funding_amount_usd": 10000000.0,
  "funding_date": "2026-01-15",
  "funding_date_parsed": "2026-01-15",
  "investors": ["Sequoia Capital", "Andreessen Horowitz"],
  "source_url": "https://www.crunchbase.com/discover/funding-rounds",
  "scraped_at": "2026-02-03T12:34:56.789Z",
  "record_hash": "a1b2c3d4e5f6g7h8",
  "extraction_method": "api"
}
```

## ⚙️ Configuration

### Input Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `start_urls` | array | Funding rounds pages | URLs to scrape |
| `max_pages` | integer | 3 | Maximum pages to scrape per URL |
| `use_apify_proxy` | boolean | true | Enable Apify Proxy rotation |
| `proxy_groups` | array | ["RESIDENTIAL"] | Proxy groups to use |

### Example Input

```json
{
  "start_urls": [
    { "url": "https://www.crunchbase.com/discover/funding-rounds" },
    { "url": "https://www.crunchbase.com/hub/recent-funding-rounds" }
  ],
  "max_pages": 3,
  "use_apify_proxy": true,
  "proxy_groups": ["RESIDENTIAL"]
}
```

## 🚀 Running the Actor

### On Apify Platform

1. **Create Actor**:
   ```bash
   apify push
   ```

2. **Configure Input**:
   - Go to Actor's input tab
   - Adjust settings as needed
   - Run the Actor

3. **View Results**:
   - Check the Dataset for extracted records
   - Review logs for execution details
   - Inspect Key-Value Store for metrics

### Local Development

1. **Install Dependencies**:
   ```bash
   pip install -r requirements.txt
   playwright install chromium --with-deps
   ```

2. **Set Environment Variables**:
   ```bash
   export APIFY_TOKEN=your_token_here
   export APIFY_HEADLESS=1
   ```

3. **Run Locally**:
   ```bash
   apify run
   ```

## 🔧 Technical Details

### Stealth Configuration

The Actor implements multiple anti-detection techniques:

- **Browser Arguments**: Disables automation flags and fingerprinting features
- **Navigator Overrides**: Masks webdriver property and injects realistic chrome object
- **User-Agent Rotation**: Uses fake-useragent for realistic UA strings
- **Viewport Randomization**: Simulates real desktop browsers (1920x1080)
- **Geolocation**: Sets realistic location (New York, USA)
- **Permissions**: Configures realistic browser permissions

### API Interception Strategy

The scraper prioritizes API interception using the following patterns:

```python
API_PATTERNS = [
    r'.*api\.crunchbase\.com.*',
    r'.*graphql.*',
    r'.*funding.*',
    r'.*search.*',
]
```

**Why API Interception?**
- More reliable than DOM parsing
- Survives UI changes and redesigns
- Provides structured JSON data
- Faster extraction and processing

### DOM Fallback Strategy

When API interception fails, the scraper uses flexible semantic selectors:

```python
# Example selectors (intentionally broad)
'[data-testid*="funding"]'
'[class*="funding-card"]'
'article'
'[role="article"]'
```

**Benefits**:
- Resilient to CSS class name changes
- Focuses on semantic HTML structure
- Adaptable to UI variations

### Human Behavior Simulation

Realistic patterns to avoid detection:

- **Scroll Simulation**: 3-6 random scrolls with variable distances
- **Random Delays**: 0.5-1.5s between actions
- **Mouse Movements**: Simulated via JavaScript events
- **Page Load Delays**: 2-4s initial wait time

### Error Handling

The Actor implements comprehensive error handling:

1. **Exponential Backoff**: Retries failed requests with increasing delays
2. **Timeout Management**: Separate timeouts for navigation (60s) and requests (30s)
3. **CAPTCHA Detection**: Automatic detection and graceful failure
4. **Rate Limit Detection**: Identifies 429 responses and throttles accordingly
5. **Blocking Detection**: Recognizes access denied and 403 errors

## 📈 Monitoring & Metrics

The Actor stores detailed metrics in the Key-Value Store:

```json
{
  "pages_processed": 5,
  "records_extracted": 127,
  "records_deduplicated": 8,
  "api_responses_intercepted": 4,
  "dom_fallback_count": 1,
  "errors_encountered": 0,
  "captcha_detected": false,
  "blocking_detected": false,
  "start_time": "2026-02-03T10:00:00.000Z",
  "end_time": "2026-02-03T10:05:23.456Z"
}
```

**Access Metrics**:
```bash
# Via CLI
apify call --key METRICS

# In logs
Check final summary section
```

## 🛡️ Best Practices

### Rate Limiting
- Limit runs to 2-3 pages per execution
- Use delays between requests (built-in)
- Enable Apify Proxy for IP rotation
- Run on schedule rather than continuous crawling

### Data Quality
- Records are automatically deduplicated
- Dates are parsed into ISO format (YYYY-MM-DD)
- Amounts are normalized to USD when possible
- Missing fields are set to `null` (not omitted)

### Monitoring
- Check logs for warnings and errors
- Review metrics after each run
- Monitor for CAPTCHA/blocking detection
- Track extraction method ratio (API vs DOM)

## 🔍 Debugging

### Common Issues

**No Records Extracted**:
- Check if URL is accessible without login
- Review logs for blocking detection
- Verify API patterns are still valid
- Try enabling DOM fallback explicitly

**CAPTCHA Detected**:
- Increase delays between requests
- Switch to RESIDENTIAL proxy group
- Reduce max_pages parameter
- Add more human-like behaviors

**Rate Limited**:
- Decrease crawl frequency
- Use longer delays
- Rotate proxies more frequently
- Limit concurrent requests

### Debug Mode

Enable verbose logging by modifying the Actor input:

```python
# In main.py, add at the start:
import logging
logging.basicConfig(level=logging.DEBUG)
```

## 📝 Maintenance

### Updating Selectors

If DOM selectors break:

1. Inspect Crunchbase's new HTML structure
2. Update selectors in `DOMScraper._extract_from_element()`
3. Test locally before deploying
4. Keep selectors semantic and flexible

### API Changes

If API interception breaks:

1. Check browser DevTools Network tab
2. Update `API_PATTERNS` in configuration
3. Verify response structure in `NetworkInterceptor._parse_funding_item()`
4. Test with sample responses

## 🚨 Limitations & Compliance

### Legal & Ethical
- ✅ Only scrapes publicly accessible data
- ✅ Does not require login or authentication
- ✅ Respects reasonable crawl rates
- ✅ Does not access paywalled content
- ⚠️ Review Crunchbase's Terms of Service
- ⚠️ Use responsibly and ethically

### Technical
- Limited to 2-3 pages per run (by design)
- May require updates if Crunchbase changes UI/API
- CAPTCHA detection causes graceful failure
- Not designed for massive data extraction

## 📚 Dependencies

```
apify >= 2.0.0, < 4.0.0
playwright >= 1.40.0
playwright-stealth >= 1.0.5
fake-useragent >= 1.4.0
python-dateutil >= 2.8.2
```

## 🤝 Support

For issues or questions:
1. Check logs for error details
2. Review metrics in Key-Value Store
3. Verify input configuration
4. Test with default settings first

## 📄 License

This Actor is provided as-is for educational and legitimate business intelligence purposes. Users are responsible for ensuring compliance with all applicable laws and terms of service.

---

**Built by**: Senior Python Scraping Engineer  
**Compatible with**: Apify Playwright + Chrome Python template  
**Last Updated**: February 2026  
**Version**: 1.0.0
