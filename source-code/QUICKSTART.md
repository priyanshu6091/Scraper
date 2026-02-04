# 🚀 Quick Start Guide

Get the Crunchbase Funding Scraper running in 5 minutes.

## Prerequisites

- Python 3.9 or higher
- Apify account (free tier works)
- npm (for Apify CLI)

## Installation

### Step 1: Install Apify CLI

```bash
npm install -g apify-cli
```

### Step 2: Login to Apify

```bash
apify login
```

### Step 3: Clone or Create Project

```bash
# If creating from scratch
apify create crunchbase-scraper --template python-playwright

# Or navigate to existing project
cd source-code
```

### Step 4: Install Dependencies

```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install packages
pip install -r requirements.txt

# Install Playwright browsers
playwright install chromium --with-deps
```

## Running the Scraper

### Local Test Run

```bash
# Run with default settings
apify run

# Or with custom input
cat > apify_storage/key_value_stores/default/INPUT.json << EOF
{
  "start_urls": [
    { "url": "https://www.crunchbase.com/discover/funding-rounds" }
  ],
  "max_pages": 1,
  "use_apify_proxy": false
}
EOF

apify run
```

### Deploy to Apify Cloud

```bash
# Build and push
apify push

# Run on Apify
apify call
```

## First Run

### Input Configuration

Use this minimal config for testing:

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

### Expected Output

After 2-3 minutes, you should see:

```
🚀 Starting Crunchbase Funding Scraper
✅ Apify Proxy configured with groups: ['RESIDENTIAL']
✅ Stealth browser context created
🔍 Scraping: https://www.crunchbase.com/discover/funding-rounds
📡 Intercepted API response from: /api/...
✅ Extracted 42 records via API interception
💾 Stored 42 unique records
📊 ============ SCRAPING SUMMARY ============
Pages processed: 1
Records extracted: 42
✅ Scraper completed successfully
```

### Viewing Results

**Dataset** (extracted records):
```bash
apify call <run-id> --dataset
```

**Metrics** (performance data):
```bash
apify call <run-id> --key METRICS
```

**Via Web UI**:
1. Go to https://console.apify.com
2. Navigate to Actors → Your Actor → Runs
3. Click latest run → Dataset tab

## Sample Output Record

```json
{
  "company_name": "Example AI Corp",
  "company_url": "https://www.crunchbase.com/organization/example-ai",
  "funding_round_type": "Series B",
  "funding_amount": "50000000 USD",
  "funding_amount_usd": 50000000.0,
  "funding_date_parsed": "2026-01-15",
  "investors": ["Sequoia Capital", "a16z"],
  "source_url": "https://www.crunchbase.com/discover/funding-rounds",
  "extraction_method": "api",
  "scraped_at": "2026-02-03T10:30:00.000Z"
}
```

## Common Issues

### Issue: "Playwright browsers not found"

**Solution**:
```bash
playwright install chromium --with-deps
```

### Issue: "CAPTCHA detected"

**Solution**: Enable Apify Proxy (RESIDENTIAL)
```json
{
  "use_apify_proxy": true,
  "proxy_groups": ["RESIDENTIAL"]
}
```

### Issue: "No records extracted"

**Solutions**:
1. Check logs for errors
2. Verify URL is accessible
3. Try with DOM fallback
4. Check if Crunchbase changed UI

### Issue: "Rate limited"

**Solution**: Reduce frequency
```json
{
  "max_pages": 1
}
```

Wait 10-15 minutes between runs.

## Next Steps

1. **Read Full Documentation**: See `README_SCRAPER.md`
2. **Test Different URLs**: Try different Crunchbase pages
3. **Schedule Runs**: Set up daily/weekly schedules in Apify
4. **Export Data**: Use Apify integrations (Google Sheets, etc.)
5. **Monitor Performance**: Check metrics after each run

## Customization

### Change Pagination Limit

```json
{
  "max_pages": 5
}
```

### Disable Proxy (Local Testing Only)

```json
{
  "use_apify_proxy": false
}
```

### Use Different URLs

```json
{
  "start_urls": [
    { "url": "https://www.crunchbase.com/hub/venture-capital-investments" },
    { "url": "https://www.crunchbase.com/hub/recent-acquisitions" }
  ]
}
```

## Production Settings

For scheduled production runs:

```json
{
  "start_urls": [
    { "url": "https://www.crunchbase.com/discover/funding-rounds" }
  ],
  "max_pages": 2,
  "use_apify_proxy": true,
  "proxy_groups": ["RESIDENTIAL"]
}
```

**Recommended Schedule**: Daily at 3 AM UTC

## Support

- **Documentation**: `README_SCRAPER.md`
- **Deployment Guide**: `DEPLOYMENT.md`
- **Apify Docs**: https://docs.apify.com
- **Playwright Docs**: https://playwright.dev

## Cost Estimate

**Free Tier** (sufficient for testing):
- 5-10 test runs per month
- 100-500 records
- SHADER proxies

**Paid Tier** (recommended for production):
- Daily runs
- 1000+ records/month
- RESIDENTIAL proxies
- ~$10-30/month depending on volume

---

**Quick Start Version**: 1.0.0  
**Last Updated**: February 2026

Happy Scraping! 🎉
