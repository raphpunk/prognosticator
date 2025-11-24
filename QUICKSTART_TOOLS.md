# Quick Start: Multi-Agent Forecasting Console

This guide covers the main application and tools for the multi-agent geopolitical forecasting system.

## Main Application

The primary Streamlit interface with full multi-agent forecasting capabilities:

```bash
source .venv/bin/activate
streamlit run scripts/app.py --server.address=127.0.0.1 --server.port=8501
```

Opens at `http://127.0.0.1:8501` with:
- **📊 Dashboard**: View ingested articles, source statistics, and data freshness
- **🔮 Prediction Lab**: Analyze questions using 16 expert AI agents
- **📡 Feeds**: Manage RSS feed sources (add/remove/toggle active)
- **🧠 Model Config**: Configure Ollama connection and expert agents
- **📥 Install Model**: Download new Ollama models
- **⚙️ Settings**: Edit raw configuration JSON

### Expert Agents (16 total)
- Macro Risk Forecaster, Logistics, Financial Markets, Energy
- Time-Series Specialist, Military Strategy, Historical Trends
- Technology/Cyber, Climate, Societal Dynamics, Policy/Governance
- Intelligence/OSINT, Industrial, Health/Biosecurity, Infrastructure
- **🎲 Chaos Agent** (contrarian perspectives)

---

## Alternative Dashboards

### Admin UI (Feeds Management)
Lightweight feed configuration interface:

```bash
streamlit run scripts/admin_ui.py --server.port=8502
```

### Dashboard (View & Analyze)
Read-only article viewer:

```bash
streamlit run scripts/dashboard.py --server.port=8503
```

---

## RSS Feed Ingestion

Fetch articles from configured RSS feeds and store in `data/live.db`:

```bash
python scripts/ollama_feed.py
```

This script:
- Fetches from all active feeds in `feeds.json`
- Deduplicates by content hash (SHA256)
- Respects per-feed cooldown periods
- Logs to `logs/ollama_feed.log`

**Recommended**: Run as cron job or systemd timer for continuous ingestion

---

## Multi-Agent Forecasting

### Using the Prediction Lab

1. Navigate to **🔮 Prediction** tab
2. Enter your question (max 2000 chars)
3. Click **🔮 Run Multi-Agent Analysis**
4. View individual agent responses and consensus summary

### Agent Configuration

In the **🧠 Model Config** tab:
- **Enable/Disable** specific experts
- **Adjust weights** (0.1-2.0) for voting influence
- **Customize system prompts** per expert
- **Toggle Chaos Agent** for contrarian views
- **Download models** with one-click install

### Rate Limiting
5-second cooldown between analyses to prevent resource exhaustion

---

## Ollama Configuration

### Connection Setup

Edit `feeds.json`:

```json
{
  "ollama": {
    "mode": "http",
    "host": "http://localhost",
    "port": 11434
  }
}
```

For remote Ollama servers, change host to your server IP (e.g., `http://192.168.1.100`)

### Install Required Models

```bash
ollama pull llama2
ollama pull gemma:2b
ollama pull qwen2.5:0.5b-instruct
ollama pull deepseek-r1:1.3b
ollama pull phi3:mini
ollama pull mistral:7b
```

Or use the **📥 Install Model** tab in the app for one-click downloads with progress tracking

---

## Security Features

The system implements multiple security layers:

1. **Input Validation**
   - Question length limit (2000 chars)
   - Model name regex validation (`^[a-zA-Z0-9._:-]+$`)
   - URL/domain sanitization for RSS feeds

2. **SQL Injection Prevention**
   - Parameterized queries throughout
   - No string concatenation in SQL statements

3. **Rate Limiting**
   - 5-second cooldown between analyses
   - Per-feed cooldown for RSS ingestion
   - Session state tracking for enforcement

4. **Network Security**
   - Binds to 127.0.0.1 only (localhost) by default
   - No external API keys or credentials in code
   - Ollama connection configurable (local or remote)

5. **Data Integrity**
   - Content hash deduplication (SHA256)
   - Response caching to reduce redundant API calls

---

## File Structure

```
work/
├── scripts/
│   ├── app.py              # Main multi-agent forecasting console
│   ├── admin_ui.py         # Feed management UI
│   ├── dashboard.py        # Article viewer dashboard
│   └── ollama_feed.py      # RSS ingestion script
├── src/
│   └── forecasting/
│       ├── agents.py       # Multi-agent orchestration
│       ├── config.py       # Configuration management
│       ├── ollama_utils.py # Ollama HTTP client
│       └── storage.py      # SQLite database layer
├── data/
│   ├── live.db            # Article database (gitignored)
│   └── agent_cache.db     # Response cache (gitignored)
├── logs/                  # Application logs (gitignored)
├── feeds.json            # Configuration (gitignored)
├── feeds.example.json    # Configuration template
└── requirements.txt      # Python dependencies
```

---

## Typical Workflow

1. **Initial Setup**
   ```bash
   python -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   cp feeds.example.json feeds.json
   ```

2. **Install Ollama & Models**
   ```bash
   # Install Ollama: https://ollama.ai
   ollama pull llama2
   ollama pull gemma:2b
   ollama pull qwen2.5:0.5b-instruct
   ```

3. **Configure Ollama Connection**
   Edit `feeds.json` to set your Ollama host (if not localhost)

4. **Start Application**
   ```bash
   streamlit run scripts/app.py
   ```

5. **Configure Expert Agents**
   - Navigate to **🧠 Model Config** tab
   - Download required models
   - Enable/disable experts
   - Customize prompts and weights

6. **Run RSS Ingestion** (optional, for data context)
   ```bash
   python scripts/ollama_feed.py
   ```

7. **Perform Analysis**
   - Go to **🔮 Prediction** tab
   - Enter your forecasting question
   - Review multi-agent consensus

---

## Troubleshooting

**Ollama Connection Failed**
- Verify Ollama is running: `ollama list`
- Check host/port in `feeds.json`
- For remote servers, ensure firewall allows port 11434

**Models Not Found**
- Download via **📥 Install Model** tab
- Or manually: `ollama pull <model-name>`

**Rate Limit Exceeded**
- Wait 5 seconds between analyses
- Check session state in browser console

**No Articles in Dashboard**
- Run `python scripts/ollama_feed.py` to ingest RSS feeds
- Verify feeds are active in `feeds.json`

---

## Performance Tips

- Use smaller models for faster inference (gemma:2b, qwen2.5:0.5b)
- Reduce number of active experts for quicker consensus
- Enable response caching (automatic via `agent_cache.db`)
- For production: run Ollama on dedicated GPU server

---

## Next Steps

- Add custom expert agents with specialized prompts
- Integrate external data sources (APIs, databases)
- Export predictions to CSV/JSON for analysis
- Deploy with Docker/Kubernetes for production
- Add authentication/authorization layer
