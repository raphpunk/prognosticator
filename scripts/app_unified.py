#!/usr/bin/env python3
"""
PROGNOSTICATOR - Unified Event Forecasting Console
A complete geopolitical forecasting system with multi-agent analysis,
local threat monitoring, and trending feeds integration.

Single entry point: streamlit run scripts/app.py
All configuration done through GUI.
"""

import sqlite3
import json
import time
import logging
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
import sys
import re
from datetime import datetime, timedelta
from collections import Counter

# Add src to path
PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_PATH = PROJECT_ROOT / "src"
SOURCES_PATH = PROJECT_ROOT / "sources"
if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))
if str(SOURCES_PATH) not in sys.path:
    sys.path.insert(0, str(SOURCES_PATH))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(PROJECT_ROOT / "logs" / "app.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

try:
    import requests
except ImportError:
    requests = None

import pandas as pd
import streamlit as st

# Import Prognosticator modules
from forecasting.agents import run_conversation, load_agent_profiles
from forecasting.ollama_utils import list_models_http, pull_model_http, test_ollama_connection
from forecasting.dispatch_discovery import load_model_config, is_model_globally_enabled
from forecasting.local_threats import get_available_zip_codes, get_jurisdictions, get_jurisdiction_for_zip
from forecasting.local_threat_integration import fetch_local_threat_feeds_with_health_tracking

# ============================================================================
# CONFIG MANAGEMENT - Unified configuration system
# ============================================================================

def load_app_config(config_path: str = "prognosticator.json") -> Dict[str, Any]:
    """Load unified application configuration."""
    config_file = Path(config_path)
    
    default_config = {
        "app": {
            "name": "Prognosticator",
            "theme": "dark",
            "auto_refresh_interval": 300,
        },
        "ollama": {
            "host": "http://localhost",
            "port": 11434,
            "mode": "http",
        },
        "feeds": {
            "rss": {
                "enabled": True,
                "sources": [
                    {"name": "BBC World", "url": "https://feeds.bbci.co.uk/news/world/rss.xml", "active": True},
                    {"name": "NYT World", "url": "https://rss.nytimes.com/services/xml/rss/nyt/World.xml", "active": True},
                    {"name": "Reuters", "url": "https://www.reutersagency.com/feed/?best-topics=world", "active": True},
                    {"name": "Al Jazeera", "url": "https://www.aljazeera.com/xml/rss/all.xml", "active": True},
                    {"name": "Guardian", "url": "https://www.theguardian.com/world/rss", "active": True},
                    {"name": "CNN", "url": "https://rss.cnn.com/rss/edition_world.rss", "active": True},
                ]
            },
            "trending": {
                "enabled": True,
                "max_items_per_feed": 50,
                "google_trends_enabled": False,
                "exploding_topics_enabled": False,
            }
        },
        "local_threats": {
            "enabled": True,
            "scrape_interval_seconds": 600,
            "min_severity": 3,
        },
        "agents": {
            "enabled_agents": [],  # All enabled by default
            "auto_weight_by_domain": True,
            "consensus_threshold": 0.4,
        },
        "advanced": {
            "cache_ttl_seconds": 900,
            "max_retries": 3,
            "rate_limit_requests_per_minute": 30,
            "log_level": "INFO",
        }
    }
    
    if config_file.exists():
        try:
            with open(config_file, 'r') as f:
                loaded = json.load(f)
                # Deep merge with defaults
                return {**default_config, **loaded}
        except Exception as e:
            logger.warning(f"Failed to load config: {e}. Using defaults.")
    
    return default_config


def save_app_config(config: Dict[str, Any], config_path: str = "prognosticator.json") -> bool:
    """Save application configuration."""
    try:
        Path(config_path).parent.mkdir(parents=True, exist_ok=True)
        with open(config_path, 'w') as f:
            json.dump(config, f, indent=2)
        logger.info(f"Config saved to {config_path}")
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

# Hide Streamlit UI chrome
hide_streamlit_style = """
<style>
#MainMenu {visibility: hidden;}
footer {visibility: hidden;}
header {visibility: hidden;}

/* Responsive scaling */
.stMetric {min-width: 100px;}
.stTabs [data-baseweb="tab-list"] {gap: 0;}
.stTabs [data-baseweb="tab"] {padding: 0.5rem 0.75rem; font-size: 0.9rem;}

/* Mobile-friendly expander */
.streamlit-expanderHeader {flex-wrap: wrap;}

/* Better table scaling */
.stDataFrame {max-width: 100%; overflow-x: auto;}

@media (max-width: 768px) {
    .stMetric {font-size: 0.8rem;}
    .stTabs [data-baseweb="tab"] {padding: 0.4rem 0.5rem; font-size: 0.75rem;}
    .stForm {padding: 0.5rem;}
}
</style>
"""
st.markdown(hide_streamlit_style, unsafe_allow_html=True)

# ============================================================================
# SESSION STATE & CONFIG INITIALIZATION
# ============================================================================

if "config" not in st.session_state:
    st.session_state.config = load_app_config()
    logger.info("Config loaded into session state")

if "ollama_models" not in st.session_state:
    st.session_state.ollama_models = []

if "last_analysis_time" not in st.session_state:
    st.session_state.last_analysis_time = 0

if "scenario_result" not in st.session_state:
    st.session_state.scenario_result = None

# ============================================================================
# HEADER WITH STATUS
# ============================================================================

def render_header():
    """Render application header with status indicators."""
    col1, col2, col3, col4 = st.columns([2, 1, 1, 1])
    
    with col1:
        st.title("🔮 Prognosticator")
        st.caption("Multi-Agent Geopolitical Forecasting Console")
    
    with col2:
        # Ollama status
        cfg = st.session_state.config
        host = cfg.get("ollama", {}).get("host", "localhost")
        port = cfg.get("ollama", {}).get("port", 11434)
        
        try:
            resp = requests.head(f"{host}:{port}/api/models", timeout=2)
            st.success("✅ Ollama")
        except:
            st.error("❌ Ollama")
    
    with col3:
        # Model status
        try:
            model_cfg = load_model_config()
            if is_model_globally_enabled():
                st.info("🧠 GPT-5")
            else:
                st.warning("⚙️ Local")
        except:
            st.warning("⚙️ Config")
    
    with col4:
        # Time
        st.caption(datetime.now().strftime("%H:%M:%S"))


# ============================================================================
# SIDEBAR NAVIGATION
# ============================================================================

def render_sidebar():
    """Render sidebar with navigation and quick settings."""
    with st.sidebar:
        st.title("⚙️ Settings")
        
        # Quick tabs
        settings_tab = st.selectbox(
            "Configuration",
            [
                "🎯 Quick Start",
                "🤖 AI Models",
                "📡 Data Sources",
                "🚨 Local Threats",
                "⚡ Advanced",
            ]
        )
        
        st.markdown("---")
        
        # Quick status
        st.subheader("📊 Status")
        
        col1, col2 = st.columns(2)
        with col1:
            try:
                conn = sqlite3.connect("data/live.db")
                cursor = conn.cursor()
                cursor.execute("SELECT COUNT(*) FROM articles")
                count = cursor.fetchone()[0]
                conn.close()
                st.metric("Articles", f"{count:,}")
            except:
                st.metric("Articles", "—")
        
        with col2:
            try:
                agents = load_agent_profiles()
                st.metric("Agents", len(agents) if agents else 0)
            except:
                st.metric("Agents", "—")
        
        st.markdown("---")
        
        # Save config button
        if st.button("💾 Save Configuration", use_container_width=True):
            if save_app_config(st.session_state.config):
                st.success("✅ Configuration saved!")
                st.rerun()
            else:
                st.error("❌ Failed to save configuration")
        
        return settings_tab


# ============================================================================
# CONFIGURATION PANELS
# ============================================================================

def render_quick_start():
    """Render quick start guide."""
    st.header("🎯 Quick Start Guide")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("1️⃣ Ollama Setup")
        st.code("""
# Install Ollama from https://ollama.ai

# Start Ollama service
ollama serve

# In another terminal, pull models:
ollama pull llama2
ollama pull gemma:2b
ollama pull qwen2.5:0.5b
        """)
    
    with col2:
        st.subheader("2️⃣ Verify Connection")
        if st.button("🧪 Test Ollama Connection"):
            cfg = st.session_state.config
            host = cfg.get("ollama", {}).get("host", "localhost")
            port = cfg.get("ollama", {}).get("port", 11434)
            
            result = test_ollama_connection(host, port, None)
            if result["success"]:
                st.success(f"✅ Connected! {result['details']}")
            else:
                st.error(f"❌ {result['status']}: {result['details']}")
    
    st.markdown("---")
    
    st.subheader("3️⃣ Configure Settings")
    st.info("""
    ✅ **RSS Feeds**: Pre-configured with major news sources
    ✅ **AI Models**: Auto-selects available Ollama models
    ✅ **Local Threats**: Configurable jurisdictions and filters
    ✅ **Trending Feeds**: Optional trending topic integration
    
    Use tabs below to customize each component.
    """)


def render_ai_models_config():
    """Render AI models configuration panel."""
    st.header("🤖 AI Models Configuration")
    
    cfg = st.session_state.config
    ollama_cfg = cfg.get("ollama", {})
    
    st.subheader("🔌 Ollama Connection")
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        host = st.text_input(
            "Ollama Host",
            value=ollama_cfg.get("host", "http://localhost"),
            help="e.g., http://192.168.1.140"
        )
        cfg["ollama"]["host"] = host
    
    with col2:
        port = st.number_input(
            "Port",
            value=int(ollama_cfg.get("port", 11434)),
            min_value=1,
            max_value=65535
        )
        cfg["ollama"]["port"] = port
    
    st.markdown("---")
    
    # Test connection
    if st.button("🧪 Test Connection", use_container_width=True):
        with st.spinner("Testing..."):
            result = test_ollama_connection(host, port, None)
            if result["success"]:
                st.success(f"✅ {result['details']}")
            else:
                st.error(f"❌ {result['status']}")
    
    st.markdown("---")
    
    st.subheader("📥 Available Models")
    
    # Refresh and display models
    try:
        models = list_models_http(host, port, None)
        st.session_state.ollama_models = models
        
        if models:
            st.success(f"Found {len(models)} installed models:")
            for model in models:
                st.caption(f"✓ {model}")
        else:
            st.warning("No models installed. Use 'ollama pull <model>' to download.")
    except Exception as e:
        st.error(f"Cannot reach Ollama: {e}")
    
    st.markdown("---")
    
    st.subheader("🤖 Expert Agents")
    
    try:
        agents = load_agent_profiles()
        if agents:
            col1, col2 = st.columns(2)
            enabled = 0
            
            for idx, agent in enumerate(agents):
                col = col1 if idx % 2 == 0 else col2
                with col:
                    key = f"agent_enabled_{agent['name'].lower().replace(' ', '_')}"
                    is_enabled = st.checkbox(
                        agent['name'],
                        value=st.session_state.get(key, True),
                        key=key,
                        help=agent.get('role', '')[:100]
                    )
                    if is_enabled:
                        enabled += 1
            
            st.caption(f"{enabled}/{len(agents)} experts enabled")
        else:
            st.info("No agent profiles configured")
    except Exception as e:
        st.warning(f"Could not load agents: {e}")


def render_data_sources_config():
    """Render data sources configuration panel."""
    st.header("📡 Data Sources Configuration")
    
    cfg = st.session_state.config
    
    # RSS Feeds
    st.subheader("📰 RSS Feed Sources")
    
    feeds_cfg = cfg.get("feeds", {}).get("rss", {})
    rss_enabled = st.checkbox(
        "Enable RSS Feeds",
        value=feeds_cfg.get("enabled", True)
    )
    cfg["feeds"]["rss"]["enabled"] = rss_enabled
    
    if rss_enabled:
        sources = feeds_cfg.get("sources", [])
        
        st.caption(f"Configured {len(sources)} RSS feeds")
        
        for idx, source in enumerate(sources):
            with st.expander(f"📌 {source['name']}", expanded=False):
                cols = st.columns([2, 1])
                with cols[0]:
                    source['url'] = st.text_input(
                        f"URL #{idx}",
                        value=source['url'],
                        key=f"rss_url_{idx}",
                        label_visibility="collapsed"
                    )
                with cols[1]:
                    source['active'] = st.checkbox(
                        "Active",
                        value=source.get('active', True),
                        key=f"rss_active_{idx}",
                        label_visibility="collapsed"
                    )
    
    st.markdown("---")
    
    # Trending Feeds
    st.subheader("🔥 Trending Feeds")
    
    trending_cfg = cfg.get("feeds", {}).get("trending", {})
    trending_enabled = st.checkbox(
        "Enable Trending Feeds",
        value=trending_cfg.get("enabled", True)
    )
    cfg["feeds"]["trending"]["enabled"] = trending_enabled
    
    if trending_enabled:
        col1, col2 = st.columns(2)
        
        with col1:
            google_trends = st.checkbox(
                "Google Trends",
                value=trending_cfg.get("google_trends_enabled", False),
                help="Requires pytrends library"
            )
            cfg["feeds"]["trending"]["google_trends_enabled"] = google_trends
        
        with col2:
            exploding = st.checkbox(
                "Exploding Topics",
                value=trending_cfg.get("exploding_topics_enabled", False),
                help="May be unreliable due to scraping"
            )
            cfg["feeds"]["trending"]["exploding_topics_enabled"] = exploding
        
        max_items = st.slider(
            "Max items per feed",
            min_value=5,
            max_value=100,
            value=trending_cfg.get("max_items_per_feed", 50)
        )
        cfg["feeds"]["trending"]["max_items_per_feed"] = max_items
    
    st.markdown("---")
    
    # Ingest controls
    st.subheader("⚡ Ingest Controls")
    
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("🔄 Fetch All Feeds Now", use_container_width=True):
            with st.spinner("Fetching feeds..."):
                try:
                    from forecasting.ingest import fetch_multiple_feeds, default_public_feeds
                    from forecasting.storage import insert_articles
                    
                    urls = default_public_feeds()
                    items = fetch_multiple_feeds(urls)
                    inserted = insert_articles(items)
                    
                    st.success(f"✅ Fetched and inserted {inserted} articles")
                except Exception as e:
                    st.error(f"❌ Ingest failed: {e}")
    
    with col2:
        if st.button("🧹 Optimize Database", use_container_width=True):
            with st.spinner("Optimizing..."):
                try:
                    conn = sqlite3.connect("data/live.db")
                    conn.execute("VACUUM")
                    conn.execute("ANALYZE")
                    conn.close()
                    st.success("✅ Database optimized")
                except Exception as e:
                    st.error(f"❌ Optimization failed: {e}")


def render_local_threats_config():
    """Render local threats configuration panel."""
    st.header("🚨 Local Threats Configuration")
    
    cfg = st.session_state.config
    threats_cfg = cfg.get("local_threats", {})
    
    # Enable/disable
    enabled = st.checkbox(
        "Enable Local Threat Monitoring",
        value=threats_cfg.get("enabled", True)
    )
    cfg["local_threats"]["enabled"] = enabled
    
    if not enabled:
        st.info("Local threat monitoring is disabled")
        return
    
    st.markdown("---")
    
    # Severity filter
    min_severity = st.slider(
        "Minimum Severity Level",
        min_value=1,
        max_value=5,
        value=threats_cfg.get("min_severity", 3),
        help="1=Routine, 5=Critical"
    )
    cfg["local_threats"]["min_severity"] = min_severity
    
    # Scrape interval
    interval = st.slider(
        "Scrape Interval (seconds)",
        min_value=60,
        max_value=3600,
        value=threats_cfg.get("scrape_interval_seconds", 600),
        step=60
    )
    cfg["local_threats"]["scrape_interval_seconds"] = interval
    
    st.markdown("---")
    
    # Jurisdiction info
    st.subheader("📍 Available Jurisdictions")
    
    try:
        jurisdictions = get_jurisdictions()
        zips = get_available_zip_codes()
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.metric("Jurisdictions", len(jurisdictions))
        
        with col2:
            st.metric("ZIP Codes", len(zips))
        
        if jurisdictions:
            st.subheader("Configured Jurisdictions")
            for j in jurisdictions:
                st.caption(f"✓ {j}")
    except Exception as e:
        st.warning(f"Could not load jurisdictions: {e}")


def render_advanced_config():
    """Render advanced configuration panel."""
    st.header("⚡ Advanced Configuration")
    
    cfg = st.session_state.config
    advanced = cfg.get("advanced", {})
    
    col1, col2 = st.columns(2)
    
    with col1:
        cache_ttl = st.number_input(
            "Cache TTL (seconds)",
            min_value=60,
            max_value=3600,
            value=advanced.get("cache_ttl_seconds", 900)
        )
        cfg["advanced"]["cache_ttl_seconds"] = cache_ttl
    
    with col2:
        max_retries = st.number_input(
            "Max Retries",
            min_value=1,
            max_value=10,
            value=advanced.get("max_retries", 3)
        )
        cfg["advanced"]["max_retries"] = max_retries
    
    st.markdown("---")
    
    # Database
    st.subheader("🗄️ Database Management")
    
    try:
        conn = sqlite3.connect("data/live.db")
        cursor = conn.cursor()
        
        # Get stats
        cursor.execute("SELECT COUNT(*) FROM articles")
        article_count = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(DISTINCT source_url) FROM articles")
        source_count = cursor.fetchone()[0]
        
        conn.close()
        
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Articles", f"{article_count:,}")
        with col2:
            st.metric("Sources", f"{source_count:,}")
        with col3:
            db_size = Path("data/live.db").stat().st_size / 1024 / 1024
            st.metric("Size", f"{db_size:.1f} MB")
    except Exception as e:
        st.warning(f"Could not get DB stats: {e}")
    
    st.markdown("---")
    
    # Logging
    st.subheader("📝 Logging")
    
    log_level = st.selectbox(
        "Log Level",
        ["DEBUG", "INFO", "WARNING", "ERROR"],
        index=["DEBUG", "INFO", "WARNING", "ERROR"].index(advanced.get("log_level", "INFO"))
    )
    cfg["advanced"]["log_level"] = log_level
    
    if st.button("📄 View Recent Logs"):
        try:
            with open("logs/app.log", "r") as f:
                lines = f.readlines()[-50:]  # Last 50 lines
                st.text("".join(lines))
        except Exception as e:
            st.error(f"Could not read logs: {e}")


# ============================================================================
# MAIN ANALYSIS TABS
# ============================================================================

def render_dashboard_tab():
    """Render dashboard tab."""
    st.header("📊 Data Ingestion Dashboard")
    
    col1, col2, col3 = st.columns(3)
    
    try:
        conn = sqlite3.connect("data/live.db")
        cursor = conn.cursor()
        
        cursor.execute("SELECT COUNT(*) FROM articles")
        article_count = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(DISTINCT source_url) FROM articles")
        source_count = cursor.fetchone()[0]
        
        cursor.execute("SELECT MAX(published) FROM articles")
        latest = cursor.fetchone()[0]
        
        conn.close()
        
        with col1:
            st.metric("📚 Total Articles", article_count)
        with col2:
            st.metric("🌐 Sources", source_count)
        with col3:
            st.metric("🕐 Latest", latest[:10] if latest else "—")
        
        st.markdown("---")
        
        # Top domains
        st.subheader("Top News Domains")
        
        try:
            conn = sqlite3.connect("data/live.db")
            df = pd.read_sql_query(
                "SELECT source_url, COUNT(*) as count FROM articles GROUP BY source_url ORDER BY count DESC LIMIT 10",
                conn
            )
            conn.close()
            
            if not df.empty:
                import tldextract
                
                df['domain'] = df['source_url'].apply(
                    lambda x: tldextract.extract(x).registered_domain or x
                )
                
                col1, col2 = st.columns([3, 2])
                
                with col1:
                    st.bar_chart(df.set_index('domain')['count'])
                
                with col2:
                    st.dataframe(df[['domain', 'count']].head(10), use_container_width=True, hide_index=True)
        except Exception as e:
            st.warning(f"Could not display top domains: {e}")
    
    except Exception as e:
        st.error(f"Could not load dashboard: {e}")


def render_prediction_tab():
    """Render prediction analysis tab."""
    st.header("🔮 Multi-Agent Prediction Lab")
    
    st.markdown("""
    Ask the AI experts to analyze recent events and predict outcomes.
    The system retrieves relevant articles and synthesizes expert opinions.
    """)
    
    # Rate limiting
    time_since_last = time.time() - st.session_state.last_analysis_time
    min_interval = 5
    can_analyze = time_since_last >= min_interval
    
    if not can_analyze:
        remaining = int(min_interval - time_since_last)
        st.info(f"⏱️ Please wait {remaining}s before starting another analysis")
    
    # Get available agents
    try:
        agent_profiles = load_agent_profiles()
        if not agent_profiles:
            st.warning("No agent profiles configured")
            return
    except Exception as e:
        st.error(f"Failed to load agents: {e}")
        return
    
    # Form
    with st.form("prediction_form"):
        question = st.text_area(
            "Your Question",
            value="How likely is a major disruption to global semiconductor supply within 3 months?",
            height=80
        )
        
        col1, col2 = st.columns(2)
        with col1:
            days = st.slider("Analyze last X days", min_value=1, max_value=90, value=14)
        with col2:
            topk = st.slider("Articles to read", min_value=3, max_value=20, value=5)
        
        submitted = st.form_submit_button("🚀 Run Analysis", type="primary", disabled=not can_analyze)
    
    if submitted and can_analyze:
        if not question or not question.strip():
            st.error("Please enter a question")
        else:
            st.session_state.last_analysis_time = time.time()
            
            with st.spinner("Running multi-agent analysis... (2-3 minutes)"):
                try:
                    result = run_conversation(
                        question=question.strip(),
                        db_path="data/live.db",
                        topk=topk,
                        days=days,
                        enabled_agents=[a['name'] for a in agent_profiles],
                    )
                    
                    st.session_state.scenario_result = result
                    st.success("✅ Analysis Complete!")
                    st.balloons()
                
                except Exception as e:
                    st.error(f"Analysis failed: {e}")
    
    # Display results
    result = st.session_state.scenario_result
    if result:
        st.markdown("---")
        st.subheader("📊 Results")
        
        summary = result.get("summary", {})
        prob = summary.get("probability")
        conf = summary.get("confidence")
        
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Probability", f"{prob:.0%}" if prob else "—")
        with col2:
            st.metric("Confidence", f"{conf:.0%}" if conf else "—")
        with col3:
            agents_list = result.get("agents", [])
            st.metric("Experts", len(agents_list))
        with col4:
            st.metric("Sources", len(result.get("context_items", [])))
        
        st.markdown("---")
        
        verdict = summary.get("verdict", "Pending")
        if prob and prob > 0.7:
            st.error(f"🚨 HIGH LIKELIHOOD: {verdict}")
        elif prob and prob > 0.4:
            st.warning(f"⚠️ MODERATE: {verdict}")
        else:
            st.info(f"ℹ️ LOW LIKELIHOOD: {verdict}")


def render_local_threats_tab():
    """Render local threats monitoring tab."""
    st.header("🚨 Local Threat Monitoring")
    
    cfg = st.session_state.config
    if not cfg.get("local_threats", {}).get("enabled", False):
        st.info("Local threat monitoring is disabled in settings")
        return
    
    col1, col2 = st.columns(2)
    
    with col1:
        identifier_input = st.text_input(
            "Enter Location (ZIP code, area code, or district)",
            placeholder="e.g., 23112, 90210"
        )
    
    with col2:
        jurisdictions = get_jurisdictions()
        jurisdiction_select = st.selectbox(
            "Or select Jurisdiction",
            ["All"] + jurisdictions if jurisdictions else ["No jurisdictions configured"]
        )
    
    if st.button("🔍 Fetch Local Threats", use_container_width=True):
        with st.spinner("Scraping dispatch feeds..."):
            try:
                identifier_to_use = None
                
                if identifier_input:
                    identifier_to_use = identifier_input
                elif jurisdiction_select != "All":
                    # Find first identifier for selected jurisdiction
                    zips = get_available_zip_codes()
                    for z, j in zips.items():
                        if j == jurisdiction_select:
                            identifier_to_use = z
                            break
                
                if not identifier_to_use:
                    st.warning("Please enter an identifier or select a jurisdiction")
                    return
                
                min_severity = cfg.get("local_threats", {}).get("min_severity", 3)
                
                feed_items = fetch_local_threat_feeds_with_health_tracking(
                    zip_code=identifier_to_use,
                    lookback_hours=6,
                    min_severity=min_severity,
                    tracker_db_path="data/local_threats.db",
                    health_db_path="data/feed_health.db"
                )
                
                if feed_items:
                    st.success(f"✅ Found {len(feed_items)} active dispatch calls")
                    
                    # Metrics
                    severities = [item.get('severity', 0) for item in feed_items]
                    
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        st.metric("Total Calls", len(feed_items))
                    with col2:
                        st.metric("Avg Severity", f"{sum(severities) / len(severities):.1f}/5")
                    with col3:
                        st.metric("Critical Calls", sum(1 for s in severities if s >= 5))
                    
                    st.markdown("---")
                    
                    # Display by severity
                    for severity_level in [5, 4, 3]:
                        calls = [item for item in feed_items if item.get('severity') == severity_level]
                        if calls:
                            severity_names = {5: "🔴 Critical", 4: "🟠 High", 3: "🟡 Medium"}
                            st.subheader(severity_names.get(severity_level, f"Level {severity_level}"))
                            
                            for call in calls:
                                with st.container(border=True):
                                    st.write(f"**{call['title']}**")
                                    st.caption(f"📍 {call.get('jurisdiction', 'Unknown')}")
                                    st.caption(f"🕐 {call.get('published', 'N/A')}")
                else:
                    st.warning("⚠️ No dispatch calls found")
            
            except Exception as e:
                st.error(f"❌ Error: {e}")


# ============================================================================
# MAIN APPLICATION
# ============================================================================

def main():
    """Main application entry point."""
    
    # Render header
    render_header()
    
    st.markdown("---")
    
    # Sidebar navigation
    settings_tab = render_sidebar()
    
    # Main content tabs
    main_tab = st.selectbox(
        "Main",
        ["📊 Dashboard", "🔮 Predictions", "🚨 Local Threats"],
        key="main_tab"
    )
    
    # Route to appropriate tab
    if main_tab == "📊 Dashboard":
        render_dashboard_tab()
    elif main_tab == "🔮 Predictions":
        render_prediction_tab()
    elif main_tab == "🚨 Local Threats":
        render_local_threats_tab()
    
    # Settings tabs
    if settings_tab == "🎯 Quick Start":
        render_quick_start()
    elif settings_tab == "🤖 AI Models":
        render_ai_models_config()
    elif settings_tab == "📡 Data Sources":
        render_data_sources_config()
    elif settings_tab == "🚨 Local Threats":
        render_local_threats_config()
    elif settings_tab == "⚡ Advanced":
        render_advanced_config()


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        st.error(f"Application error: {e}")
        logger.exception("Unhandled exception")
