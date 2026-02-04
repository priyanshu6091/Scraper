# Deployment & Testing Guide

## 📦 Pre-Deployment Checklist

### 1. Environment Setup

```bash
# Ensure you have Python 3.9+ installed
python --version

# Install Apify CLI
npm install -g apify-cli

# Login to Apify
apify login
```

### 2. Local Testing

```bash
# Navigate to project directory
cd source-code

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Install Playwright browsers
playwright install chromium --with-deps

# Copy environment template
cp .env.example .env
# Edit .env and add your APIFY_TOKEN

# Run locally
apify run
```

### 3. Test Input Validation

Create a test INPUT.json file:

```json
{
  "start_urls": [
    { "url": "https://www.crunchbase.com/discover/funding-rounds" }
  ],
  "max_pages": 1,
  "use_apify_proxy": false,
  "proxy_groups": ["RESIDENTIAL"]
}
```

Save to `apify_storage/key_value_stores/default/INPUT.json` for local testing.

## 🚀 Deployment to Apify

### Method 1: Using Apify CLI (Recommended)

```bash
# Initialize Apify project (if not already done)
apify init

# Build and push to Apify
apify push

# The Actor will be deployed to your Apify account
```

### Method 2: Using Git Integration

1. Push code to GitHub repository
2. In Apify Console:
   - Go to Actors → Create new
   - Select "Import from Git"
   - Enter repository URL
   - Set build tag to `latest`
   - Configure environment

### Method 3: Manual Upload

1. Zip the entire `source-code` directory
2. Upload to Apify Console
3. Configure build settings
4. Deploy

## 🧪 Testing Procedures

### Test 1: Basic Functionality

**Objective**: Verify Actor runs and extracts data

```json
{
  "start_urls": [
    { "url": "https://www.crunchbase.com/discover/funding-rounds" }
  ],
  "max_pages": 1,
  "use_apify_proxy": true,
  "proxy_groups": ["RESIDENTIAL"]
}
```

**Expected Results**:
- ✅ Actor completes successfully
- ✅ At least 10-20 funding records extracted
- ✅ No CAPTCHA detected
- ✅ Metrics stored in Key-Value Store

**Validation**:
```bash
# Check dataset
apify call <run-id> --dataset

# Check metrics
apify call <run-id> --key METRICS
```

### Test 2: API Interception

**Objective**: Verify API interception is working

**Check Logs For**:
```
📡 Intercepted API response from: /api/...
✅ Extracted N records via API interception
```

**Success Criteria**:
- `api_responses_intercepted > 0` in metrics
- `extraction_method: "api"` in most records

### Test 3: DOM Fallback

**Objective**: Test fallback mechanism

**Manual Test**:
1. Temporarily break API patterns in code
2. Run Actor
3. Verify DOM scraping activates

**Check Logs For**:
```
⚠️ No API data found, falling back to DOM scraping
✅ Extracted N records via DOM scraping
```

**Success Criteria**:
- `dom_fallback_count > 0` in metrics
- `extraction_method: "dom"` in records

### Test 4: Pagination

**Objective**: Verify pagination handling

```json
{
  "start_urls": [
    { "url": "https://www.crunchbase.com/discover/funding-rounds" }
  ],
  "max_pages": 3,
  "use_apify_proxy": true,
  "proxy_groups": ["RESIDENTIAL"]
}
```

**Expected Results**:
- ✅ Multiple pages processed (`pages_processed >= 2`)
- ✅ Increased record count
- ✅ No duplicate records

### Test 5: Deduplication

**Objective**: Verify duplicate detection

**Method**:
1. Run Actor twice with same URLs
2. Check metrics

**Expected Results**:
- `records_deduplicated > 0` in second run
- Unique `record_hash` values in dataset

### Test 6: Error Handling

**Objective**: Test resilience

**Test Cases**:

1. **Invalid URL**:
```json
{
  "start_urls": [
    { "url": "https://www.crunchbase.com/nonexistent-page" }
  ],
  "max_pages": 1
}
```
Expected: Graceful error handling, no crash

2. **Network Timeout**:
   - Simulate by setting very short timeouts
   - Expected: Retry mechanism activates

3. **Rate Limiting**:
   - Run multiple times rapidly
   - Expected: Detection and backoff

### Test 7: Proxy Rotation

**Objective**: Verify proxy functionality

```json
{
  "use_apify_proxy": true,
  "proxy_groups": ["RESIDENTIAL"]
}
```

**Check Logs For**:
```
✅ Apify Proxy configured with groups: ['RESIDENTIAL']
🎭 Using User-Agent: Mozilla/5.0...
```

**Validation**:
- No blocking detected
- Successful data extraction
- Different IPs used (check proxy stats in Apify)

## 📊 Performance Benchmarks

### Expected Metrics (Per Run)

| Metric | Target | Acceptable Range |
|--------|--------|------------------|
| Pages Processed | 3 | 1-3 |
| Records Extracted | 50-150 | 20-200 |
| API Interception Rate | >80% | 50-100% |
| DOM Fallback Rate | <20% | 0-50% |
| Error Rate | <5% | 0-10% |
| Execution Time | 2-5 min | 1-10 min |
| CAPTCHA Detection | 0% | 0-5% |

### Performance Optimization

**If extraction is slow**:
- Reduce `max_pages`
- Disable unnecessary waits
- Optimize selectors

**If hitting rate limits**:
- Increase delays
- Use RESIDENTIAL proxies
- Reduce frequency

**If getting blocked**:
- Check stealth configuration
- Rotate user agents more
- Use better proxies

## 🔍 Debugging Guide

### Debug Logs

Enable detailed logging:

```python
# Add to main.py
import logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
```

### Common Issues & Solutions

**Issue**: No records extracted
**Solutions**:
1. Check if URL is accessible
2. Verify API patterns are current
3. Test DOM selectors manually
4. Check for blocking

**Issue**: CAPTCHA detected
**Solutions**:
1. Switch to RESIDENTIAL proxy
2. Increase human-like delays
3. Reduce crawl rate
4. Update stealth configuration

**Issue**: Duplicate records
**Solutions**:
1. Check deduplication logic
2. Verify hash generation
3. Clear dataset between runs

**Issue**: Timeout errors
**Solutions**:
1. Increase timeout values
2. Check network connectivity
3. Verify proxy is working
4. Test with `use_apify_proxy: false` locally

### Log Analysis

**Successful Run Pattern**:
```
🚀 Starting Crunchbase Funding Scraper
✅ Apify Proxy configured
✅ Stealth browser context created
🔍 Scraping: https://...
📡 Intercepted API response
✅ Extracted N records via API interception
💾 Stored N unique records
📊 ============ SCRAPING SUMMARY ============
✅ Scraper completed successfully
```

**Failed Run Pattern** (with recovery):
```
⚠️ Attempt 1 failed: timeout. Retrying in 2.00s...
✅ Extracted N records via DOM scraping
⚠️ Rate limiting detected: too many requests
```

## 🎯 Production Readiness Checklist

### Before Going Live

- [ ] Test with all proxy groups
- [ ] Verify data quality manually
- [ ] Check deduplication works
- [ ] Test error handling paths
- [ ] Review rate limiting behavior
- [ ] Validate output schema
- [ ] Set up monitoring alerts
- [ ] Document any custom configurations
- [ ] Test scheduled runs
- [ ] Review costs (proxy usage, compute)

### Monitoring Setup

1. **Create Alerts**:
   - CAPTCHA detection
   - High error rate (>10%)
   - Zero records extracted
   - Execution time >10 minutes

2. **Regular Checks**:
   - Weekly data quality review
   - Monthly selector validation
   - Quarterly dependency updates
   - Annual full regression test

3. **Maintenance Schedule**:
   - Check Crunchbase for UI changes
   - Update API patterns if needed
   - Review and optimize selectors
   - Test with latest Playwright version

## 📈 Scaling Considerations

### Horizontal Scaling

For higher volume:
- Use Apify Scheduler for distributed runs
- Split URLs across multiple Actor runs
- Implement request queue for large crawls

### Vertical Scaling

For deeper scraping:
- Increase memory allocation
- Use faster proxy groups
- Optimize data processing pipeline

### Cost Optimization

- Use SHADER proxies for initial testing
- Switch to RESIDENTIAL for production
- Batch runs during off-peak hours
- Monitor compute usage

## 🔐 Security Best Practices

1. **Never commit**:
   - APIFY_TOKEN
   - Proxy credentials
   - Personal data

2. **Use environment variables**:
   - Store tokens in Apify Secrets
   - Use .env for local development
   - Rotate tokens regularly

3. **Access Control**:
   - Limit Actor permissions
   - Use read-only tokens where possible
   - Audit access logs

## 📝 Version Control

### Branching Strategy

```
main (production)
├── develop (staging)
└── feature/* (development)
```

### Release Process

1. Develop in feature branch
2. Test in develop branch
3. Merge to main when stable
4. Tag releases (v1.0.0, v1.1.0, etc.)
5. Deploy to Apify

### Changelog

Maintain CHANGELOG.md:
```markdown
## [1.0.0] - 2026-02-03
### Added
- Initial release
- API interception
- DOM fallback
- Stealth configuration

### Changed
- N/A

### Fixed
- N/A
```

## 🆘 Support & Troubleshooting

### Getting Help

1. Check logs first
2. Review metrics
3. Test with minimal input
4. Check Apify status page
5. Review recent Crunchbase changes

### Emergency Procedures

**If Actor stops working**:
1. Check if Crunchbase is accessible
2. Test with `use_apify_proxy: false`
3. Verify selectors haven't changed
4. Roll back to last working version
5. Enable debug logging

**If getting blocked**:
1. Switch to RESIDENTIAL proxies
2. Reduce crawl rate
3. Update stealth configuration
4. Wait 24h before retrying

---

**Deployment Guide Version**: 1.0.0  
**Last Updated**: February 2026  
**Maintainer**: Senior Python Scraping Engineer
