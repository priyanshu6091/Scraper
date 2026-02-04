# Crunchbase Funding Data Scraper

A production-ready web scraper that collects publicly accessible funding data from Crunchbase using Python and Playwright.

## 🚀 Quick Start

### Prerequisites

- **Python 3.9+** installed on your system
- **npm** (for Apify CLI)
- **Apify account** (free tier available at [apify.com](https://apify.com))

### Installation

1. **Clone the repository**:
   ```bash
   git clone https://github.com/priyanshu6091/Scraper.git
   cd Scraper/source-code
   ```

2. **Install Apify CLI**:
   ```bash
   npm install -g apify-cli
   apify login
   ```

3. **Install Python dependencies**:
   ```bash
   # Create and activate virtual environment (recommended)
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   
   # Install dependencies
   pip install -r requirements.txt
   
   # Install Playwright browser
   playwright install chromium --with-deps
   ```

### Running the Scraper

#### Option 1: Run Locally

```bash
cd source-code
apify run
```

This will:
- Use the default configuration from `.actor/INPUT.example.json`
- Scrape funding data from Crunchbase
- Save results to `apify_storage/datasets/default/`
- Complete in approximately 2-5 minutes

#### Option 2: Deploy to Apify Cloud

```bash
cd source-code
apify push        # Upload to Apify
apify call        # Run on Apify platform
```

### Configuration

Create or modify `apify_storage/key_value_stores/default/INPUT.json`:

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

**Configuration options**:
- `start_urls`: Array of Crunchbase URLs to scrape
- `max_pages`: Maximum number of pages to scrape (default: 3)
- `use_apify_proxy`: Enable/disable proxy rotation (default: true)
- `proxy_groups`: Proxy types to use (`["RESIDENTIAL"]` or `["SHADER"]`)

## 📊 Output Format

The scraper extracts funding records in JSON format:

```json
{
  "company_name": "Example Corp",
  "company_url": "https://www.crunchbase.com/organization/example-corp",
  "funding_round_type": "Series A",
  "funding_amount": "10000000 USD",
  "funding_amount_usd": 10000000.0,
  "funding_date_parsed": "2026-01-15",
  "investors": ["Sequoia Capital", "Andreessen Horowitz"],
  "extraction_method": "api",
  "scraped_at": "2026-02-03T12:34:56.789Z"
}
```

Results are saved to:
- **Local runs**: `apify_storage/datasets/default/`
- **Cloud runs**: Apify Console → Actors → Runs → Dataset

## 🔧 Troubleshooting

### "Playwright browsers not found"
```bash
playwright install chromium --with-deps
```

### "CAPTCHA detected"
Enable Apify Proxy with RESIDENTIAL proxies in your configuration.

### "No records extracted"
1. Check logs for error messages
2. Verify the URL is accessible
3. Ensure you're not rate-limited (wait 10-15 minutes between runs)

## 📚 Documentation

For detailed documentation, see the `source-code` directory:

- **[QUICKSTART.md](source-code/QUICKSTART.md)** - 5-minute setup guide
- **[README.md](source-code/README.md)** - Complete overview and features
- **[README_SCRAPER.md](source-code/README_SCRAPER.md)** - Detailed usage guide
- **[DEPLOYMENT.md](source-code/DEPLOYMENT.md)** - Deployment procedures
- **[ARCHITECTURE.md](source-code/ARCHITECTURE.md)** - Technical architecture

## ✨ Key Features

- 🎯 **API Interception**: Captures internal GraphQL/XHR responses for reliable data
- 🔄 **Smart Fallback**: Automatic DOM parsing when API data unavailable
- 🥷 **Stealth Mode**: Browser fingerprinting evasion and anti-detection
- 🌐 **Proxy Support**: Automatic IP rotation with Apify Proxy
- 🔒 **Deduplication**: SHA-256 hashing prevents duplicate records
- ♻️ **Retry Logic**: Exponential backoff for resilience
- 🛡️ **CAPTCHA Detection**: Automatic detection and graceful handling

## 📈 Performance

- **Execution Time**: 2-5 minutes per run
- **Records per Run**: 50-150 funding records
- **API Success Rate**: >80%
- **Memory Usage**: <500MB

## 🛡️ Compliance & Ethics

- ✅ Scrapes only publicly accessible data
- ✅ No authentication required
- ✅ Respects rate limits
- ✅ No paywalled content accessed
- ⚠️ Users must review and comply with Crunchbase Terms of Service

## 💡 Usage Examples

### Basic Local Run
```bash
cd source-code
apify run
```

### Custom Configuration
```bash
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

### View Results
```bash
# View extracted data
cat apify_storage/datasets/default/*.json | jq

# View metrics
cat apify_storage/key_value_stores/default/METRICS.json
```

## 📞 Support

For issues or questions:
1. Check the [detailed documentation](source-code/README.md)
2. Review logs for error details
3. Verify configuration settings
4. Test with default settings first

## 📄 License

Provided for educational and legitimate business intelligence purposes. Users are responsible for ensuring compliance with all applicable laws and terms of service.

---

**Version**: 1.0.0  
**Built with**: Python 3.9+ | Playwright | Apify  
**Status**: Production Ready ✅
