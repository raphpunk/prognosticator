#!/usr/bin/env python3
"""
PROGNOSTICATOR - Unified Event Forecasting Console
A complete geopolitical forecasting system with multi-agent analysis,
local threat monitoring, and trending feeds integration.

Single entry point: streamlit run scripts/app_complete.py
All configuration done through GUI.
All data persisted in SQLite.
"""

import sqlite3
import json
import time
import sys
import logging
import re
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional

# Setup paths
PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_PATH = PROJECT_ROOT / "src"
SOURCES_PATH = PROJECT_ROOT / "sources"
for p in [str(SRC_PATH), str(SOURCES_PATH)]:
    if p not in sys.path:
        sys.path.insert(0, p)

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(PROJECT_ROOT / "logs" / "app.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Initialize database on startup
try:
    from forecasting.database_manager import ensure_database_ready, DataRetentionManager
    if not ensure_database_ready():
        logger.error("Failed to initialize database")
except Exception as e:
    logger.warning(f"Database initialization error: {e}")

# Initialize config system
try:
    from forecasting.config_manager import UnifiedConfigManager, initialize_config_system
    config_mgr = initialize_config_system()
except Exception as e:
    logger.warning(f"Config system error: {e}")
    config_mgr = None

# Optional imports
try:
    import requests
except ImportError:
    requests = None

try:
    import pandas as pd
except ImportError:
    pd = None

try:
    import streamlit as st
except ImportError:
    print("ERROR: Streamlit not installed. Run: pip install streamlit")
    sys.exit(1)

# Import Prognosticator modules
from forecasting.agents import run_conversation, load_agent_profiles
from forecasting.ollama_utils import list_models_http, pull_model_http, test_ollama_connection

# ============================================================================
# CONFIGURATION DEFAULTS
# ============================================================================

DEFAULT_CONFIG = {
    "app": {"name": "Prognosticator", "version": "2.0"},
    "ollama": {"host": "http://localhost", "port": 11434},
    "feeds": {
        "rss": [
            {"name": "BBC World", "url": "https://feeds.bbci.co.uk/news/world/rss.xml"},
            {"name": "NYT World", "url": "https://rss.nytimes.com/services/xml/rss/nyt/World.xml"},
            {"name": "Reuters", "url": "https://www.reutersagency.com/feed/?best-topics=world"},
            {"name": "Al Jazeera", "url": "https://www.aljazeera.com/xml/rss/all.xml"},
            {"name": "Guardian", "url": "https://www.theguardian.com/world/rss"},
            {"name": "CNN", "url": "https://rss.cnn.com/rss/edition_world.rss"},
        ]
    },
    "local_threats": {"enabled": True, "min_severity": 3},
}


def load_app_config() -> Dict[str, Any]:
    """Load unified application configuration."""
    config_file = Path("prognosticator.json")
    
    if config_file.exists():
        try:
            with open(config_file) as f:
                return json.load(f)
        except Exception as e:
            logger.warning(f"Failed to load config: {e}")
    
    return DEFAULT_CONFIG


def save_app_config(config: Dict[str, Any]) -> bool:
    """Save application configuration."""
    try:
        with open("prognosticator.json", "w") as f:
            json.dump(config, f, indent=2)
        return True
    except Exception as e:
        logger.error(f"Failed to save config: {e}")
        return False


# ============================================================================
# STREAMLIT PAGE SETUP
# ============================================================================

st.set_page_config(
    page_title="Prognosticator",
    layout="wide",
    page_icon="🔮",
    initial_sidebar_state="expanded"
)

hide_streamlit_style = """
<style>
#MainMenu {visibility: hidden;}
footer {visibility: hidden;}
.stTabs [data-baseweb="tab-list"] {gap: 0;}
.stTabs [data-baseweb="tab"] {padding: 0.5rem 0.75rem; font-size: 0.9rem;}
</style>
"""
st.markdown(hide_streamlit_style, unsafe_allow_html=True)

# ============================================================================
# SESSION STATE
# ============================================================================

if "config" not in st.session_state:
    st.session_state.config = load_app_config()

if "last_analysis_time" not in st.session_state:
    st.session_state.last_analysis_time = 0

if "scenario_result" not in st.session_state:
    st.session_state.scenario_result = None


# ============================================================================
# HEADER
# ============================================================================

def render_header():
    """Render header with status."""
    col1, col2, col3, col4 = st.columns([2, 1, 1, 1])
    
    with col1:
        st.title("🔮 Prognosticator")
        st.caption("Multi-Agent Geopolitical Forecasting")
    
    with col2:
        cfg = st.session_state.config
        host = cfg.get("ollama", {}).get("host", "localhost")
        port = cfg.get("ollama", {}).get("port", 11434)
        
        try:
            if requests:
                resp = requests.head(f"{host}:{port}/api/models", timeout=2)
                st.success("✅ Ollama")
            else:
                st.warning("⚠️ Ollama")
        except:
            st.error("❌ Ollama")
    
    with col3:
        try:
            agents = load_agent_profiles()
            st.metric("Experts", len(agents) if agents else 0)
        except:
            st.metric("Experts", "?")
    
    with col4:
        st.caption(datetime.now().strftime("%H:%M:%S"))


# ============================================================================
# SIDEBAR CONFIGURATION
# ============================================================================

def render_sidebar() -> str:
    """Render sidebar navigation."""
    with st.sidebar:
        st.title("⚙️ Configuration")
        
        tab = st.selectbox(
            "Settings",
            ["🎯 Quick Start", "🤖 AI Models", "📡 Feeds", "🚨 Threats", "⚡ Advanced"]
        )
        
        st.markdown("---")
        
        # Database stats
        st.subheader("📊 Status")
        try:
            conn = sqlite3.connect("data/live.db")
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM articles")
            articles = cursor.fetchone()[0]
            conn.close()
            st.metric("Articles", f"{articles:,}")
        except:
            st.metric("Articles", "—")
        
        st.markdown("---")
        
        if st.button("💾 Save Config", use_container_width=True):
            if save_app_config(st.session_state.config):
                st.success("✅ Saved!")
            else:
                st.error("❌ Failed")
        
        return tab


# ============================================================================
# CONFIGURATION PANELS
# ============================================================================

def render_quick_start():
    """Render quick start guide."""
    st.header("🎯 Quick Start")
    
    st.subheader("Step 1: Install Ollama")
    st.code("# Download from https://ollama.ai\n# Run: ollama serve")
    
    st.subheader("Step 2: Pull Models")
    st.code("""
ollama pull llama2
ollama pull gemma:2b
ollama pull qwen2.5:0.5b
    """)
    
    st.subheader("Step 3: Verify Connection")
    if st.button("🧪 Test Ollama"):
        cfg = st.session_state.config
        host = cfg.get("ollama", {}).get("host", "localhost")
        port = cfg.get("ollama", {}).get("port", 11434)
        
        result = test_ollama_connection(host, port, None)
        if result["success"]:
            st.success(f"✅ Connected! {result['details']}")
        else:
            st.error(f"❌ {result['status']}")


def render_ai_models():
    """Render AI models configuration."""
    st.header("🤖 AI Models")
    
    cfg = st.session_state.config
    ollama_cfg = cfg.get("ollama", {})
    
    st.subheader("Connection Settings")
    
    col1, col2 = st.columns([2, 1])
    with col1:
        host = st.text_input("Host", value=ollama_cfg.get("host", "http://localhost"))
        cfg["ollama"]["host"] = host
    with col2:
        port = st.number_input("Port", value=int(ollama_cfg.get("port", 11434)))
        cfg["ollama"]["port"] = port
    
    if st.button("🧪 Test Connection"):
        result = test_ollama_connection(host, port, None)
        if result["success"]:
            st.success(f"✅ {result['details']}")
        else:
            st.error(f"❌ {result['status']}")
    
    st.markdown("---")
    
    st.subheader("Available Models")
    try:
        models = list_models_http(host, port, None)
        if models:
            st.success(f"Found {len(models)} models:")
            for m in models:
                st.caption(f"✓ {m}")
        else:
            st.warning("No models installed")
    except Exception as e:
        st.error(f"Cannot reach Ollama: {e}")
    
    st.markdown("---")
    
    st.subheader("Pull New Model")
    model_name = st.text_input("Model name", placeholder="e.g., mistral")
    if st.button("📥 Pull Model"):
        with st.spinner("Pulling..."):
            result = pull_model_http(host, port, model_name, None)
            if result["success"]:
                st.success(f"✅ {result['details']}")
            else:
                st.error(f"❌ {result['status']}")


def render_feeds():
    """Render feed configuration."""
    st.header("📡 Data Sources")
    
    cfg = st.session_state.config
    
    st.subheader("RSS Feeds")
    
    feeds = cfg.get("feeds", {}).get("rss", [])
    st.caption(f"Configured {len(feeds)} feeds")
    
    for idx, feed in enumerate(feeds):
        with st.expander(f"📌 {feed.get('name', f'Feed {idx}')}"):
            name = st.text_input(f"Name {idx}", value=feed.get("name", ""), key=f"feed_name_{idx}")
            url = st.text_input(f"URL {idx}", value=feed.get("url", ""), key=f"feed_url_{idx}")
            
            feed["name"] = name
            feed["url"] = url
    
    st.markdown("---")
    
    if st.button("🔄 Fetch All Feeds"):
        with st.spinner("Fetching..."):
            try:
                from forecasting.ingest import fetch_multiple_feeds, default_public_feeds
                from forecasting.storage import insert_articles
                
                urls = [f["url"] for f in feeds if f.get("url")]
                items = fetch_multiple_feeds(urls)
                inserted = insert_articles(items)
                
                st.success(f"✅ Fetched {inserted} articles")
            except Exception as e:
                st.error(f"❌ {e}")


def render_threats():
    """Render local threats configuration."""
    st.header("🚨 Local Threats")
    
    cfg = st.session_state.config
    threats = cfg.get("local_threats", {})
    
    enabled = st.checkbox("Enable", value=threats.get("enabled", True))
    cfg["local_threats"]["enabled"] = enabled
    
    if enabled:
        min_severity = st.slider("Min Severity", 1, 5, threats.get("min_severity", 3))
        cfg["local_threats"]["min_severity"] = min_severity
        
        st.info("Configure jurisdictions in advanced settings")


def render_advanced():
    """Render advanced configuration."""
    st.header("⚡ Advanced")
    
    cfg = st.session_state.config
    
    st.subheader("Database")
    
    try:
        conn = sqlite3.connect("data/live.db")
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM articles")
        count = cursor.fetchone()[0]
        conn.close()
        
        st.metric("Articles", f"{count:,}")
        
        if st.button("🧹 Optimize DB"):
            conn = sqlite3.connect("data/live.db")
            conn.execute("VACUUM")
            conn.close()
            st.success("✅ Optimized")
    except Exception as e:
        st.warning(f"DB access failed: {e}")


# ============================================================================
# MAIN TABS
# ============================================================================

def render_dashboard():
    """Render dashboard tab."""
    st.header("📊 Dashboard")
    
    try:
        conn = sqlite3.connect("data/live.db")
        cursor = conn.cursor()
        
        cursor.execute("SELECT COUNT(*) FROM articles")
        articles = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(DISTINCT source_url) FROM articles")
        sources = cursor.fetchone()[0]
        
        cursor.execute("SELECT MAX(published) FROM articles")
        latest = cursor.fetchone()[0]
        
        conn.close()
        
        col1, col2, col3 = st.columns(3)
        col1.metric("📚 Articles", f"{articles:,}")
        col2.metric("🌐 Sources", sources)
        col3.metric("🕐 Latest", latest[:10] if latest else "—")
        
        st.markdown("---")
        
        st.subheader("Top Sources")
        try:
            df = pd.read_sql_query(
                "SELECT source_url, COUNT(*) as count FROM articles GROUP BY source_url ORDER BY count DESC LIMIT 10",
                conn
            )
            if not df.empty:
                st.bar_chart(df.set_index('source_url')['count'])
        except:
            st.info("No data yet")
    
    except Exception as e:
        st.error(f"Dashboard error: {e}")


def render_predictions():
    """Render predictions tab."""
    st.header("🔮 Multi-Agent Analysis")
    
    st.markdown("""
    Ask the AI experts to analyze recent events and predict outcomes.
    """)
    
    try:
        agents = load_agent_profiles()
        if not agents:
            st.warning("No agents configured")
            return
    except Exception as e:
        st.error(f"Failed to load agents: {e}")
        return
    
    time_since = time.time() - st.session_state.last_analysis_time
    can_analyze = time_since >= 5
    
    if not can_analyze:
        st.info(f"⏱️ Wait {int(5 - time_since)}s before next analysis")
    
    with st.form("analysis_form"):
        question = st.text_area(
            "Your Question",
            value="What geopolitical disruptions are emerging?",
            height=80
        )
        
        col1, col2 = st.columns(2)
        with col1:
            days = st.slider("Days", 1, 90, 14)
        with col2:
            topk = st.slider("Articles", 3, 20, 5)
        
        submit = st.form_submit_button("🚀 Analyze", disabled=not can_analyze, type="primary")
    
    if submit and can_analyze and question.strip():
        st.session_state.last_analysis_time = time.time()
        
        with st.spinner("Running analysis... (1-3 minutes)"):
            try:
                result = run_conversation(
                    question=question.strip(),
                    db_path="data/live.db",
                    topk=topk,
                    days=days,
                    enabled_agents=[a["name"] for a in agents],
                )
                
                st.session_state.scenario_result = result
                st.success("✅ Analysis complete!")
                st.balloons()
            except Exception as e:
                st.error(f"Analysis failed: {e}")
    
    result = st.session_state.scenario_result
    if result:
        st.markdown("---")
        st.subheader("Results")
        
        summary = result.get("summary", {})
        prob = summary.get("probability")
        
        col1, col2, col3 = st.columns(3)
        col1.metric("Probability", f"{prob:.0%}" if prob else "—")
        col2.metric("Experts", len(result.get("agents", [])))
        col3.metric("Sources", len(result.get("context_items", [])))
        
        if prob and prob > 0.7:
            st.error(f"🚨 HIGH LIKELIHOOD: {summary.get('verdict', '—')}")
        elif prob and prob > 0.4:
            st.warning(f"⚠️ MODERATE: {summary.get('verdict', '—')}")
        else:
            st.info(f"ℹ️ LOW: {summary.get('verdict', '—')}")


def render_threats_tab():
    """Render threats monitoring tab."""
    st.header("🚨 Local Threat Monitoring")
    
    cfg = st.session_state.config
    if not cfg.get("local_threats", {}).get("enabled", False):
        st.info("Local threat monitoring disabled")
        return
    
    location = st.text_input("Location (ZIP or District)", placeholder="23112")
    
    if st.button("🔍 Fetch Threats"):
        with st.spinner("Scraping..."):
            try:
                from forecasting.local_threat_integration import fetch_local_threat_feeds_with_health_tracking
                
                threats = fetch_local_threat_feeds_with_health_tracking(
                    zip_code=location,
                    lookback_hours=6,
                    min_severity=cfg.get("local_threats", {}).get("min_severity", 3),
                    tracker_db_path="data/local_threats.db",
                    health_db_path="data/feed_health.db"
                )
                
                if threats:
                    st.success(f"✅ Found {len(threats)} calls")
                    for t in threats:
                        st.write(f"**{t['title']}** - {t['jurisdiction']}")
                else:
                    st.info("No threats found")
            except Exception as e:
                st.error(f"Error: {e}")


# ============================================================================
# MAIN APPLICATION
# ============================================================================

def main():
    """Main application."""
    render_header()
    st.markdown("---")
    
    # Sidebar
    settings_tab = render_sidebar()
    
    # Main tabs
    main_tab = st.selectbox(
        "View",
        ["📊 Dashboard", "🔮 Analysis", "🚨 Threats"],
        label_visibility="collapsed"
    )
    
    if main_tab == "📊 Dashboard":
        render_dashboard()
    elif main_tab == "🔮 Analysis":
        render_predictions()
    elif main_tab == "🚨 Threats":
        render_threats_tab()
    
    # Settings
    if settings_tab == "🎯 Quick Start":
        render_quick_start()
    elif settings_tab == "🤖 AI Models":
        render_ai_models()
    elif settings_tab == "📡 Feeds":
        render_feeds()
    elif settings_tab == "🚨 Threats":
        render_threats()
    elif settings_tab == "⚡ Advanced":
        render_advanced()


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        st.error(f"Application error: {e}")
        logger.exception("Unhandled error")
