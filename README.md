# Multi-Agent Geopolitical Forecasting Console

A Streamlit-based application that ingests RSS feeds from global news sources and analyzes them using multiple specialized AI agents running on Ollama for geopolitical forecasting and risk assessment.

## Features

- **📰 RSS Feed Ingestion**: Automated collection from major news outlets (BBC, NYT, Reuters, Al Jazeera, etc.)
- **🤖 Multi-Agent Analysis**: 16 specialized expert agents including:
  - Macro Risk Forecaster, Financial Markets, Military Strategy
  - Climate & Environmental, Intelligence/OSINT, Cybersecurity
  - Chaos Agent for contrarian perspectives
- **🔮 Predictive Forecasting**: Consensus-based predictions with configurable expert weights
- **⚡ Local AI**: Runs on Ollama (no cloud API costs)
- **🔒 Security**: Input validation, SQL injection protection, rate limiting

### Production Hardening ✨ NEW

- **🎯 Reputation System**: Track agent accuracy over time with domain-specific performance metrics
- **🔄 Circuit Breakers**: Automatic failover when Ollama API is unavailable (prevents cascade failures)
- **⏱️ Retry Logic**: Exponential backoff on transient failures (3 attempts with 30s timeout)
- **📊 Domain Expertise Matrix**: Agents weighted by domain relevance (e.g., Military Expert gets 1.0x on military questions, 0.5x on others)
- **🛡️ Feed Health Monitoring**: Automatic detection of:
  - Volume anomalies (sudden spikes/drops)
  - Topic shifts (coordinated messaging)
  - Content truncation
  - Repeated failures (skip after 5 errors or reputation < 0.3)
- **⚖️ Reputation-Weighted Consensus**: Agent votes weighted by historical accuracy in relevant domain
- **🚨 Dissent Detection**: Predictions with >40% agent disagreement flagged for manual review

## Quick Start

### 1. Prerequisites

- Python 3.13+
- [Ollama](https://ollama.ai) installed and running
- Recommended models: `llama2`, `gemma:2b`, `qwen2.5:0.5b-instruct`

### 2. Setup

```bash
# Clone repository
git clone <your-repo-url>
cd work

# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Copy configuration template
cp feeds.example.json feeds.json
cp .env.example .env

# Edit feeds.json to configure your Ollama host (if not localhost)
```

### 3. Run Application

```bash
streamlit run scripts/app.py
```

Access at: http://127.0.0.1:8501

## Configuration

Edit `feeds.json` to set your Ollama host:

```json
{
  "ollama": {
    "mode": "http",
    "host": "http://localhost",
    "port": 11434
  }
}
```

## Security Notes

⚠️ **Before committing:**
- `feeds.json` is gitignored (contains your Ollama host)
- `data/` and `logs/` are gitignored
- Use `feeds.example.json` as template

## License

MIT License

