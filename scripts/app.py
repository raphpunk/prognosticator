#!/usr/bin/env python3
"""Unified Event Forecasting Console - Dashboard + Admin UI in one app."""

import sqlite3
import json
import time
from pathlib import Path
from typing import Dict, Any, List, Optional
import sys
import re

try:
    import requests
except ImportError:  # pragma: no cover - optional dependency
    requests = None  # type: ignore[assignment]

import pandas as pd
import streamlit as st

# Ensure project src directory is importable when running via Streamlit/CLI
PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_PATH = PROJECT_ROOT / "src"
if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))

from forecasting.agents import run_conversation, load_agent_profiles, get_required_models
from forecasting.ollama_utils import list_models_http, pull_model_http, test_ollama_connection


def load_feeds_config(path: str = "feeds.json") -> Dict[str, Any]:
    """Load feeds.json configuration safely."""
    if not Path(path).exists():
        return {"feeds": []}
    try:
        with open(path, "r") as fh:
            return json.load(fh)
    except Exception:
        return {"feeds": []}


def save_feeds_config(cfg: Dict[str, Any], path: str = "feeds.json") -> None:
    """Save configuration to feeds.json."""
    with open(path, "w") as fh:
        json.dump(cfg, fh, indent=2)


def render_model_pull_ui(host: str, port: int, available_models: Optional[List[str]] = None) -> None:
    """Render model pulling interface with progress tracking."""
    st.markdown("### 📥 Model Manager")
    st.caption("Pull specialized models for expert analysis")
    
    # Get required models from agent profiles (no hardcoding!)
    required_models = get_required_models(config_path="feeds.json")
    
    # Get currently available models
    available = available_models if available_models is not None else list_models_http(host or "http://localhost", int(port) or 11434, None)
    available_names = [m.split(":")[0] for m in available]  # Extract base model name
    
    for model_name, description in required_models:
        model_base = model_name.split(":")[0]
        is_available = any(model_base in available_name for available_name in available_names)
        
        col1, col2 = st.columns([3, 1])
        
        with col1:
            if is_available:
                st.success(f"✅ {model_name}")
                st.caption(description)
            else:
                st.warning(f"⚠️ {model_name}")
                st.caption(description)
        
        with col2:
            if not is_available:
                if st.button(f"📥 Pull", key=f"pull_{model_name}", width='stretch'):
                    with st.spinner(f"Downloading {model_name}..."):
                        progress_bar = st.progress(0)
                        status_text = st.empty()
                        
                        def progress_callback(status_dict):
                            percent = status_dict.get("percent", 0) / 100.0
                            progress_bar.progress(min(percent, 0.99))  # Cap at 99% until complete
                            stage = status_dict.get("stage", "")
                            if stage:
                                status_text.caption(f"Stage: {stage} ({status_dict.get('percent', 0)}%)")
                        
                        success, message = pull_model_http(host or "http://localhost", int(port) or 11434, model_name, progress_callback=progress_callback)
                        progress_bar.progress(1.0)
                        
                        if success:
                            st.success(f"✅ {message}")
                            time.sleep(1)
                            st.rerun()
                        else:
                            st.error(f"❌ Failed: {message}")
            else:
                st.caption("Ready")


def _agent_state_key(name: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "_", name.lower()).strip("_") or "agent"
    return f"agent_enabled_{slug}"


def _normalize_host(host: str) -> str:
    value = (host or "").strip() or "http://localhost"
    if not value.startswith("http://") and not value.startswith("https://"):
        value = f"http://{value}"
    return value.rstrip("/")


def _is_model_available(model_name: str, available_models: List[str]) -> bool:
    if not model_name:
        return False
    base = model_name.split(":")[0]
    for candidate in available_models:
        if not candidate:
            continue
        if candidate == model_name:
            return True
        if candidate.split(":")[0] == base:
            return True
    return False


def render_expert_roster_integrated(host: str, port: int, available_models: List[str]) -> None:
    """Integrated expert roster with model availability, auto-download, and customization."""
    # Expanded expert library with diverse specializations
    expert_library = [
        {
            "name": "📊 Macro Risk Forecaster",
            "role": "You are a macroeconomic risk analyst specializing in geopolitical forecasting. Analyze large-scale economic, political, and systemic risks. Focus on: GDP trends, market volatility, monetary policy, trade dynamics, and black swan events. Provide probabilistic assessments of macro shocks.",
            "model": "gemma:2b",
            "weight": 1.2,
        },
        {
            "name": "🚚 Demand & Logistics Forecaster",
            "role": "You are a supply chain and demand forecasting specialist. Predict disruptions to global logistics, manufacturing demand, and resource flows. Focus on: container shipping indices, semiconductor shortages, port congestion, freight rates, and just-in-time vulnerabilities. Quantify supply chain shocks.",
            "model": "qwen2.5:0.5b-instruct",
            "weight": 1.1,
        },
        {
            "name": "💹 Financial Market Forecaster",
            "role": "You are a quantitative financial analyst forecasting market movements from geopolitical events. Predict correlations between events and asset prices. Focus on: equity volatility, FX movements, commodity prices, credit spreads, and tail risk. Provide technical and fundamental analysis.",
            "model": "gemma:2b",
            "weight": 1.2,
        },
        {
            "name": "⚡ Energy & Resource Forecaster",
            "role": "You are an energy and commodities expert. Forecast impact of geopolitical events on oil, natural gas, minerals, and renewables. Focus on: OPEC dynamics, renewable adoption, critical minerals, energy transitions, and resource scarcity. Provide supply-demand outlook.",
            "model": "gemma:2b",
            "weight": 1.1,
        },
        {
            "name": "📈 Time-Series Specialist",
            "role": "You are a time-series forecasting expert using advanced statistical methods. Detect patterns, trends, and anomalies in temporal data. Focus on: autocorrelation patterns, seasonality, structural breaks, and prediction intervals. Use statistical rigor.",
            "model": "qwen2.5:0.5b-instruct",
            "weight": 1.0,
        },
        {
            "name": "🎖️ Military Strategy Expert",
            "role": "You are a military strategist and conflict analyst. Assess military capabilities, force posture, and strategic intentions. Focus on: weapons systems, doctrine, force deployment, naval/air operations, and escalation dynamics. Provide tactical and strategic insights.",
            "model": "qwen2.5:0.5b-instruct",
            "weight": 1.2,
        },
        {
            "name": "📚 Historical Trends Expert",
            "role": "You are a historian and trends analyst specializing in geopolitical patterns. Contextualize current events within historical precedent and long-term cycles. Focus on: great power competition, empire dynamics, technology disruption, and civilizational trends. Draw historical parallels.",
            "model": "gemma:2b",
            "weight": 1.0,
        },
        {
            "name": "🔐 Technology & Cyber Expert",
            "role": "You are a technology and cybersecurity strategist. Forecast disruptions from AI, semiconductors, cyberattacks, and digital infrastructure. Focus on: chip supply chains, AI adoption, zero-day exploits, infrastructure vulnerabilities, and technological dominance. Assess digital warfare risks.",
            "model": "mistral:7b",
            "weight": 1.1,
        },
        {
            "name": "🌍 Climate & Environmental Expert",
            "role": "You are a climate scientist and environmental economist. Forecast climate impacts on geopolitics and vice versa. Focus on: weather patterns, resource scarcity, climate migration, agricultural disruption, and climate treaties. Provide environmental risk assessment.",
            "model": "gemma:2b",
            "weight": 1.0,
        },
        {
            "name": "👥 Societal Dynamics Expert",
            "role": "You are a sociologist and civil dynamics analyst. Forecast social movements, protests, and regime stability. Focus on: inequality trends, youth unemployment, demographic pressure, ethnic tensions, and social fragmentation. Assess civil unrest probability.",
            "model": "qwen2.5:0.5b-instruct",
            "weight": 1.0,
        },
        {
            "name": "🏛️ Policy & Governance Analyst",
            "role": "You are a public policy and governance expert. Analyze regulatory changes, government decision-making, and institutional stability. Focus on: policy cascades, regulatory arbitrage, institutional legitimacy, bureaucratic capacity, and governance resilience.",
            "model": "llama2:latest",
            "weight": 1.0,
        },
        {
            "name": "📡 Intelligence & OSINT Specialist",
            "role": "You are an open-source intelligence analyst. Synthesize public data, satellite imagery analysis, and signal detection. Focus on: information operations, disinformation campaigns, covert activities, and intelligence indicators.",
            "model": "phi3:mini",
            "weight": 1.1,
        },
        {
            "name": "🏭 Industrial & Manufacturing Analyst",
            "role": "You are an industrial production and manufacturing systems expert. Track capacity utilization, bottlenecks, and production trends. Focus on: factory output, industrial orders, equipment spending, and manufacturing PMIs.",
            "model": "gemma:2b",
            "weight": 1.0,
        },
        {
            "name": "🧬 Health & Biosecurity Expert",
            "role": "You are a public health and biosecurity specialist. Forecast pandemic risk, healthcare system stress, and biotech developments. Focus on: disease surveillance, vaccine distribution, hospital capacity, and biological threats.",
            "model": "llama2:latest",
            "weight": 1.0,
        },
        {
            "name": "🌐 Network & Infrastructure Analyst",
            "role": "You are a critical infrastructure and network resilience expert. Analyze telecommunications, power grids, and digital backbone vulnerabilities. Focus on: grid stability, network outages, infrastructure attacks, and system dependencies.",
            "model": "qwen2.5:0.5b-instruct",
            "weight": 1.0,
        },
        {
            "name": "🎲 Chaos Agent",
            "role": "You are a contrarian chaos agent. Challenge consensus, explore unlikely scenarios, and identify overlooked risks. Focus on: tail events, paradigm shifts, cognitive biases in forecasts, and scenarios dismissed by conventional wisdom. Deliberately argue against the mainstream view.",
            "model": "llama2:latest",
            "weight": 0.8,
        },
    ]
    
    st.caption(f"Enable experts, customize their prompts, and download required models")
    
    # Group by model to show download status
    model_groups = {}
    for expert in expert_library:
        model = expert["model"]
        if model not in model_groups:
            model_groups[model] = []
        model_groups[model].append(expert)
    
    for model_name, experts in model_groups.items():
        is_available = _is_model_available(model_name, available_models)
        
        # Model header with status
        col_header, col_action = st.columns([3, 1])
        with col_header:
            if is_available:
                st.success(f"✅ {model_name}", icon="✅")
            else:
                st.warning(f"⚠️ {model_name} (Not Installed)")
        
        with col_action:
            if not is_available:
                if st.button("📥 Pull", key=f"pull_model_{model_name}", help=f"Download {model_name}", width='stretch'):
                    with st.spinner(f"Downloading {model_name}..."):
                        progress_bar = st.progress(0)
                        status_text = st.empty()
                        
                        def progress_callback(status_dict):
                            percent = status_dict.get("percent", 0) / 100.0
                            progress_bar.progress(min(percent, 0.99))
                            stage = status_dict.get("stage", "")
                            if stage:
                                status_text.caption(f"{stage} ({status_dict.get('percent', 0)}%)")
                        
                        success, message = pull_model_http(host, port, model_name, progress_callback=progress_callback)
                        progress_bar.progress(1.0)
                        
                        if success:
                            st.success(message)
                            st.session_state["ollama_models"] = list_models_http(host, port, None)
                            time.sleep(1)
                            st.rerun()
                        else:
                            st.error(message)
        
        # Expert cards for this model
        for expert in experts:
            key = _agent_state_key(expert["name"])
            
            with st.expander(f"{expert['name']}", expanded=False):
                col_enable, col_weight = st.columns([3, 1])
                
                with col_enable:
                    enabled = st.checkbox(
                        "Enable this expert",
                        value=st.session_state.get(key, True),
                        key=key,
                        disabled=not is_available,
                        help="Must download model first" if not is_available else None
                    )
                
                with col_weight:
                    weight_key = f"{key}_weight"
                    weight = st.number_input(
                        "Weight",
                        min_value=0.1,
                        max_value=2.0,
                        value=st.session_state.get(weight_key, expert.get("weight", 1.0)),
                        step=0.1,
                        key=weight_key,
                        help="Higher weight = more influence in consensus"
                    )
                
                # System prompt editor
                prompt_key = f"{key}_prompt"
                default_prompt = st.session_state.get(prompt_key, expert["role"])
                
                custom_prompt = st.text_area(
                    "System Prompt",
                    value=default_prompt,
                    height=120,
                    key=prompt_key,
                    help="Customize this expert's behavior and focus areas"
                )
                
                col_reset, col_status = st.columns([1, 2])
                with col_reset:
                    if st.button("↺ Reset", key=f"{key}_reset", help="Reset to default prompt"):
                        st.session_state[prompt_key] = expert["role"]
                        st.rerun()
                
                with col_status:
                    if custom_prompt != expert["role"]:
                        st.caption("⚙️ Custom prompt active")
                    else:
                        st.caption("📋 Using default prompt")
        
        st.markdown("---")
    
    # Summary
    enabled_count = sum(
        1 for expert in expert_library 
        if st.session_state.get(_agent_state_key(expert["name"]), True) 
        and _is_model_available(expert["model"], available_models)
    )
    total_available = sum(
        1 for expert in expert_library 
        if _is_model_available(expert["model"], available_models)
    )
    st.info(f"**{enabled_count}/{total_available} experts enabled** ({len(expert_library)} total in library)")


def render_expert_roster_sidebar(host: str, port: int, available_models: List[str]) -> None:
    """Sidebar panel for enabling/disabling forecasting experts."""
    agent_profiles = load_agent_profiles()
    if not agent_profiles:
        st.info("No expert profiles configured.")
        return

    with st.sidebar.expander("👥 Expert Roster", expanded=False):
        st.caption("Toggle which specialists participate in analyses.")
        cols = st.columns(2)

        for idx, agent in enumerate(agent_profiles):
            key = _agent_state_key(agent["name"])
            checkbox_col = cols[idx % len(cols)]
            status_col = cols[(idx + 1) % len(cols)] if len(cols) > 1 else st.container()

            with checkbox_col:
                default_value = st.session_state.get(key, True)
                st.checkbox(
                    label=f"{agent['name']}",
                    value=default_value,
                    help=agent.get("role", ""),
                    key=key,
                )

            model_name = agent.get("model", "")
            slug = _agent_state_key(agent["name"]) + "_model"
            is_available = _is_model_available(model_name, available_models)
            with status_col:
                if is_available:
                    st.success(f"✅ {model_name}", icon="✅")
                else:
                    st.warning(f"⚠️ {model_name}")
                    if st.button("📥 Pull", key=f"pull_{slug}", help="Download model to Ollama", width='stretch'):
                        with st.spinner(f"Pulling {model_name}..."):
                            success, message = pull_model_http(host, port, model_name)
                        if success:
                            st.success(message)
                            st.session_state["ollama_models"] = list_models_http(host, port, None)
                            st.rerun()
                        else:
                            st.error(message)

        enabled_count = sum(
            1 for agent in agent_profiles if st.session_state.get(_agent_state_key(agent["name"]), True)
        )
        st.caption(f"{enabled_count}/{len(agent_profiles)} experts enabled.")


def get_db_stats(db_path: str = "data/live.db") -> Dict[str, int]:
    """Safely fetch database statistics with path validation."""
    db_path_obj = Path(db_path).resolve()
    if not db_path_obj.exists():
        return {}
    
    try:
        conn = sqlite3.connect(str(db_path_obj))
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM articles")
        article_count = cur.fetchone()[0]
        cur.execute("SELECT COUNT(*) FROM ingest_log")
        log_count = cur.fetchone()[0]
        cur.execute("SELECT COUNT(*) FROM feed_state")
        feed_count = cur.fetchone()[0]
        cur.execute("SELECT COUNT(DISTINCT source_url) FROM articles")
        unique_sources = cur.fetchone()[0]
        conn.close()
        return {"articles": article_count, "logs": log_count, "feeds": feed_count, "sources": unique_sources}
    except Exception:
        return {}


def load_stats(db_path: str = "data/live.db") -> pd.DataFrame:
    """Safely load articles with path validation."""
    db_path_obj = Path(db_path).resolve()
    if not db_path_obj.exists():
        return pd.DataFrame()
    try:
        conn = sqlite3.connect(str(db_path_obj))
        df_articles = pd.read_sql_query("SELECT published, source_url, content_hash FROM articles", conn)
        conn.close()
        # Convert published to datetime to avoid type comparison errors
        if not df_articles.empty and 'published' in df_articles.columns:
            df_articles['published'] = pd.to_datetime(df_articles['published'], utc=True, errors='coerce')
        return df_articles
    except Exception:
        return pd.DataFrame()


def render_ai_settings(cfg: Dict[str, Any]) -> None:
    """Render AI model settings sidebar panel (HTTP-only mode)."""
    with st.sidebar.expander("🤖 AI Model Settings", expanded=True):
        ollama_cfg = cfg.get("ollama", {}) if isinstance(cfg, dict) else {}
        
        # HTTP-only mode (remote Ollama server)
        host_input = st.text_input("Ollama Host", value=ollama_cfg.get("host", "http://localhost"), label_visibility="collapsed")
        port_input = st.number_input("Port", value=int(ollama_cfg.get("port", 11434)), min_value=1, max_value=65535, label_visibility="collapsed")

        host_value = (host_input or "http://localhost").strip() or "http://localhost"
        effective_host = _normalize_host(host_value)
        effective_port = int(port_input or 11434)

        st.caption("Connects to remote Ollama server via HTTP.")

        if "ollama_models" not in st.session_state:
            st.session_state["ollama_models"] = []

        endpoint = (effective_host, effective_port)
        if st.session_state.get("_ollama_endpoint") != endpoint:
            st.session_state["_ollama_endpoint"] = endpoint
            try:
                st.session_state["ollama_models"] = list_models_http(effective_host, effective_port, None)
            except Exception:
                st.session_state["ollama_models"] = []

        # Test connection button
        st.markdown("---")
        if st.button("🧪 Test Connection", width='stretch'):
            with st.spinner("Testing connection..."):
                result = test_ollama_connection(effective_host, effective_port, None)
                if result["success"]:
                    st.success(f"✅ {result['status']}")
                    st.info(result["details"])
                    if result["models"]:
                        st.write("**Available models:**")
                        for model in result["models"]:
                            st.caption(f"  • {model}")
                else:
                    st.error(f"❌ {result['status']}")
                    st.error(result["details"])
                    if result.get("diagnostic_tips"):
                        st.markdown("---")
                        for tip in result["diagnostic_tips"]:
                            st.caption(tip)

        st.markdown("---")

        # Refresh models
        def refresh_models():
            """Refresh available models."""
            models = list_models_http(effective_host, effective_port, None)
            st.session_state["ollama_models"] = models

        if st.button("🔄 Refresh Models", width='stretch'):
            refresh_models()
            st.rerun()

        # Save connection settings
        if st.button("💾 Save Connection", width='stretch'):
            cfg["ollama"] = cfg.get("ollama", {})
            cfg["ollama"]["host"] = host_input
            cfg["ollama"]["port"] = int(port_input)
            cfg["ollama"]["mode"] = "http"
            save_feeds_config(cfg)
            st.success("✅ Connection settings saved!")

        available_models = st.session_state.get("ollama_models", [])

        # Model pulling UI with Expert Roster integrated
        st.markdown("---")
        with st.expander("📥 Model Manager & Expert Roster", expanded=False):
            st.markdown("### 🤖 Base Models")
            render_model_pull_ui(effective_host, effective_port, available_models)
            
            st.markdown("---")
            st.markdown("### 👥 Expert Agents")
            render_expert_roster_integrated(effective_host, effective_port, available_models)


def render_dashboard_tab(db_path: str) -> None:
    """Render Dashboard tab: Ingest overview."""
    st.header("📰 Data Ingestion")
    
    if st.button("🔄 Refresh Data"):
        df_articles = load_stats(db_path)
        
        # Responsive metrics: 3 cols on desktop, 1-2 on mobile
        cols = st.columns(3)
        with cols[0]:
            st.metric("📚 Total", len(df_articles))
        with cols[1]:
            st.metric("🌐 Sources", df_articles["source_url"].nunique())
        with cols[2]:
            if not df_articles.empty and "published" in df_articles.columns:
                latest = pd.to_datetime(df_articles["published"], errors='coerce').max()
                st.metric("🕐 Latest", latest.strftime("%m-%d %H:%M") if pd.notnull(latest) else "N/A")
            else:
                st.metric("🕐 Latest", "—")

        import tldextract

        def get_reg_domain(url: str) -> str:
            try:
                ext = tldextract.extract(url or "")
                reg = ext.registered_domain
                return reg or (ext.domain + ("." + ext.suffix if ext.suffix else ""))
            except Exception:
                return url

        df_articles["reg_domain"] = df_articles["source_url"].fillna("").apply(get_reg_domain)
        top_domains = df_articles["reg_domain"].value_counts().head(10)

        st.markdown("### Top Domains")
        
        # Responsive layout: 2-col on desktop, 1-col on mobile
        try:
            # Try 2-column layout (desktop)
            left, right = st.columns([3, 2])
            with left:
                st.bar_chart(top_domains)
            with right:
                total = len(df_articles)
                tbl = top_domains.rename_axis("domain").reset_index(name="count")
                if total > 0:
                    tbl["pct"] = (tbl["count"] / total * 100).round(1).astype(str) + "%"
                st.table(tbl)
        except Exception:
            # Fallback to single column (mobile)
            st.bar_chart(top_domains)
            total = len(df_articles)
            tbl = top_domains.rename_axis("domain").reset_index(name="count")
            if total > 0:
                tbl["pct"] = (tbl["count"] / total * 100).round(1).astype(str) + "%"
            st.table(tbl)

        with st.expander("📄 Recent Articles"):
            if not df_articles.empty:
                df_show = df_articles.sort_values(by="published", ascending=False).head(200)[["published", "reg_domain", "source_url"]]
                st.dataframe(df_show, width='stretch', height=400)
    else:
        st.info("Click 'Refresh Data' to load statistics.")


def render_prediction_tab(db_path: str) -> None:
    """Render Prediction Lab tab."""
    st.header("🔮 Prediction Lab")
    st.markdown("Ask the AI to analyze recent events and predict outcomes.")
    
    # Rate limiting check
    if "last_analysis_time" not in st.session_state:
        st.session_state["last_analysis_time"] = 0
    
    time_since_last = time.time() - st.session_state["last_analysis_time"]
    min_interval = 5  # seconds between analyses
    
    can_analyze = time_since_last >= min_interval
    if not can_analyze:
        remaining = int(min_interval - time_since_last)
        st.info(f"⏱️ Please wait {remaining}s before starting another analysis (rate limiting)")

    agent_profiles = load_agent_profiles()
    enabled_agents = [
        agent
        for agent in agent_profiles
        if st.session_state.get(_agent_state_key(agent["name"]), True)
    ]

    st.caption(
        f"Currently enabled experts: {len(enabled_agents)}/{len(agent_profiles)}"
        if agent_profiles
        else "No experts configured"
    )
    
    with st.expander("ℹ️ How it works", expanded=False):
        st.markdown("""
        1. Ask a question about a future event or trend.
        2. System retrieves relevant articles from database.
        3. Multiple AI agents debate the topic.
        4. Final probability and verdict are synthesized.
        """)

    with st.form("prediction_form"):
        question = st.text_area(
            "What do you want to know?",
            value=st.session_state.get("scenario_question", "How likely is a major disruption to global semiconductor supply within 3 months?"),
            help="Be specific about the event and timeframe.",
            height=80
        )
        
        # Responsive: 2 cols on desktop, 1 on mobile (sliders stack naturally)
        try:
            c1, c2 = st.columns(2)
            with c1:
                days = st.slider("Analyze last X days", min_value=1, max_value=90, value=14)
            with c2:
                topk = st.slider("Articles to read", min_value=3, max_value=20, value=5)
        except Exception:
            # Fallback to single column
            days = st.slider("Analyze last X days", min_value=1, max_value=90, value=14)
            topk = st.slider("Articles to read", min_value=3, max_value=20, value=5)
            
        submitted = st.form_submit_button("🚀 Run Analysis", type="primary", disabled=not can_analyze)

    if st.button("Clear Results"):
        st.session_state.pop("scenario_result", None)
        st.rerun()

    if submitted and can_analyze:
        selected_agent_names = [
            agent["name"]
            for agent in agent_profiles
            if st.session_state.get(_agent_state_key(agent["name"]), True)
        ]

        if not question or not question.strip():
            st.error("Please enter a question.")
        elif len(selected_agent_names) < 2:
            st.error("Enable at least two experts before running the analysis.")
        else:
            st.session_state["scenario_question"] = question
            
            # Create a container for progress visualization
            progress_container = st.container()
            
            with progress_container:
                st.markdown("### 🤖 Multi-Agent Analysis in Progress")
                
                # Phase indicators with columns
                phase_cols = st.columns(4)
                
                with phase_cols[0]:
                    st.markdown("#### 📋 Phase 1")
                    st.markdown("**Plan**")
                    phase1_placeholder = st.empty()
                    phase1_placeholder.info("⏳ Building...")
                
                with phase_cols[1]:
                    st.markdown("#### 🔍 Phase 2")
                    st.markdown("**Context**")
                    phase2_placeholder = st.empty()
                    phase2_placeholder.info("⏳ Searching...")
                
                with phase_cols[2]:
                    st.markdown("#### 👥 Phase 3")
                    st.markdown("**Experts**")
                    phase3_placeholder = st.empty()
                    phase3_placeholder.info("⏳ Analyzing...")
                
                with phase_cols[3]:
                    st.markdown("#### 🧠 Phase 4")
                    st.markdown("**Synthesis**")
                    phase4_placeholder = st.empty()
                    phase4_placeholder.info("⏳ Waiting...")
                
                # Agent status bars
                st.markdown("---")
                st.markdown("### 👥 Expert Status")
                agents_container = st.container()
                
                # Run analysis with visual progress
                phase1_placeholder.success("✅ Plan built")
                time.sleep(0.1)
                phase2_placeholder.success("✅ Context retrieved")
                
                with st.spinner("🤖 Running parallel expert analysis... This may take 2-3 minutes depending on Ollama load."):
                    # Record analysis start time for rate limiting
                    st.session_state["last_analysis_time"] = time.time()
                    
                    result = run_conversation(
                        question=question.strip(),
                        db_path=db_path,
                        topk=topk,
                        days=days,
                        enabled_agents=selected_agent_names,
                    )
                
                # Update agent statuses - participating agents
                participating_agents = result.get("agents", [])
                declined_agents = result.get("declined_agents", [])
                total_experts = len(participating_agents) + len(declined_agents)
                
                if participating_agents:
                    st.markdown("#### ✅ Participating Experts")
                    agent_cols = st.columns(min(3, len(participating_agents)))
                    for idx, agent_entry in enumerate(participating_agents):
                        with agent_cols[idx % len(agent_cols)] if len(participating_agents) > 0 else st.container():
                            if agent_entry.get("parsed"):
                                st.success(f"✅ {agent_entry['agent']}")
                            elif agent_entry.get("raw", "").startswith("ERROR"):
                                st.error(f"❌ {agent_entry['agent']}")
                            else:
                                st.warning(f"⚠️ {agent_entry['agent']}")
                
                # Show declined agents
                if declined_agents:
                    st.markdown("#### 🙅 Declined Experts")
                    decline_cols = st.columns(min(3, len(declined_agents)))
                    for idx, agent_entry in enumerate(declined_agents):
                        with decline_cols[idx % len(decline_cols)] if len(declined_agents) > 0 else st.container():
                            reason = agent_entry.get("parsed", {}).get("reason", "Not applicable to topic")
                            st.info(f"⊘ {agent_entry['agent']}\n*{reason}*")
                
                phase3_placeholder.success(f"✅ {len(participating_agents)}/{total_experts} experts analyzed")
                phase4_placeholder.success("✅ Results ready")
                
            st.markdown("---")
            st.session_state["scenario_result"] = result
            st.success("✅ Analysis Complete!")
            st.balloons()

    result = st.session_state.get("scenario_result")
    if not result:
        st.info("Enter a question and click Run Analysis.")
        return

    # Show Phase 1: Orchestrator Plan
    if result.get("orchestrator_plan"):
        st.markdown("## 📊 Analysis Results")
        st.markdown("---")
        
        with st.expander("### 📋 Phase 1: Orchestrator (Gathering Context)", expanded=True):
            plan = result["orchestrator_plan"]
            col_p1, col_p2 = st.columns([1, 1])
            
            with col_p1:
                st.markdown("**🎯 Priority Areas Identified:**")
                if plan.get("priority_areas") and isinstance(plan["priority_areas"], list):
                    for area in plan["priority_areas"]:
                        st.markdown(f"  • {area}")
                else:
                    st.caption("No specific priority areas identified")
            
            with col_p2:
                st.markdown("**🔍 Research Direction:**")
                if plan.get("research_focus"):
                    st.info(f"→ {plan['research_focus']}")
                else:
                    st.caption("General analysis")
            
            # Show articles gathered by orchestrator
            articles_count = plan.get("articles_gathered", 0)
            st.markdown(f"**📚 Articles Gathered for Experts:** {articles_count}")
            
            if plan.get("context_quality"):
                prog_val = float(plan["context_quality"]) if isinstance(plan["context_quality"], (int, float)) else 0.5
                st.progress(min(1.0, max(0, prog_val)), text=f"Context Quality Score: {prog_val:.0%}")

    # Show Phase 2: Context Articles (moved here for prominence)
    st.markdown("---")
    context_items = result.get("context_items", [])
    with st.expander(f"### 📚 Phase 2: Retrieved Context ({len(context_items)} Relevant Articles)", expanded=True):
        st.caption(f"Contextual articles from {len(set(item.get('source_url', '') for item in context_items))} sources - automatically selected based on relevance to your question")
        
        for idx, item in enumerate(context_items, 1):
            score = item.get("score", 0)
            
            # Visual relevance indicator
            if score > 0.7:
                relevance_icon = "🔴"  # Highly relevant
            elif score > 0.4:
                relevance_icon = "🟡"  # Moderately relevant
            else:
                relevance_icon = "🟢"  # Somewhat relevant
            
            with st.expander(f"{relevance_icon} [{idx}] {item['title'] or '[No Title]'} ({score:.1%})", expanded=idx <= 2):
                st.caption(f"📍 {item['source_url']}")
                st.write(item["snippet"])
                st.progress(score, text=f"Relevance Score: {score:.1%}")

    # Expert Analysis with visual status
    agents_list = result.get("agents", [])
    st.markdown("---")
    st.markdown("## 🤖 Phase 3 & 4: Expert Analysis & Synthesis")
    st.markdown("---")
    st.markdown("### 👥 Expert Consensus")
    
    # Count successful vs failed analyses
    successful_agents = sum(1 for a in agents_list if a.get("parsed") is not None)
    failed_agents = len(agents_list) - successful_agents
    
    agent_status_col = st.columns([1, 1, 1, 1])
    with agent_status_col[0]:
        st.metric("👥 Experts", len(agents_list))
    with agent_status_col[1]:
        st.metric("✅ Analyzed", successful_agents, delta=f"{failed_agents} issues" if failed_agents > 0 else "")
    
    summary = result.get("summary", {})
    prob = summary.get("probability")
    conf = summary.get("confidence")
    
    with agent_status_col[2]:
        if isinstance(prob, (int, float)):
            prob_pct = f"{prob:.0%}"
            st.metric("📊 Probability", prob_pct)
        else:
            st.metric("📊 Probability", "N/A")
    
    with agent_status_col[3]:
        if isinstance(conf, (int, float)):
            conf_pct = f"{conf:.0%}"
            st.metric("🎯 Confidence", conf_pct)
        else:
            st.metric("🎯 Confidence", "N/A")

    # Synthesized verdict
    st.markdown("### 🎙️ Final Verdict")
    verdict = summary.get("verdict", "Analysis pending")
    rationale = summary.get("rationale", "")
    
    # Color-code verdict based on probability
    if isinstance(prob, (int, float)):
        if prob > 0.7:
            st.error(f"🚨 HIGH LIKELIHOOD: {verdict}")
        elif prob > 0.4:
            st.warning(f"⚠️ MODERATE LIKELIHOOD: {verdict}")
        else:
            st.info(f"ℹ️ LOW LIKELIHOOD: {verdict}")
    else:
        st.info(verdict)
    
    if rationale:
        with st.expander("📝 Reasoning", expanded=True):
            st.write(rationale)

    # Expert Analyses - Enhanced visual cards
    st.markdown("---")
    st.markdown("### 🧑‍🔬 Expert Analyses (Detailed)")
    
    if not agents_list:
        st.warning("⚠️ No agent responses received. Check Ollama connection.")
    else:
        # Create responsive grid of agent cards
        agent_cols = st.columns(min(2, len(agents_list)))
        
        for idx, agent_entry in enumerate(agents_list):
            with agent_cols[idx % len(agent_cols)]:
                agent_name = agent_entry.get("agent", "Unknown Agent")
                parsed = agent_entry.get("parsed")
                
                # Visual status indicator
                if parsed and isinstance(parsed, dict):
                    indicator = "✅"
                    border_color = "green"
                    analysis = parsed.get("analysis", "No analysis provided")
                    agent_prob = parsed.get("probability")
                    agent_conf = parsed.get("confidence")
                    recommendation = parsed.get("recommendation", "")
                elif agent_entry.get("raw", "").startswith("ERROR"):
                    indicator = "❌"
                    border_color = "red"
                    analysis = agent_entry.get("raw", "")[:200]
                    agent_prob = None
                    agent_conf = None
                    recommendation = ""
                else:
                    indicator = "⚠️"
                    border_color = "orange"
                    analysis = agent_entry.get("raw", "")[:300]
                    agent_prob = None
                    agent_conf = None
                    recommendation = ""
                
                # Custom card-like display
                st.markdown(f"**{indicator} {agent_name}**")
                
                with st.container(border=True):
                    st.markdown(f"*{analysis}*" if len(analysis) < 200 else f"{analysis}...")
                    
                    # Show metrics if available
                    if isinstance(agent_prob, (int, float)) and isinstance(agent_conf, (int, float)):
                        m1, m2 = st.columns(2)
                        with m1:
                            st.caption(f"📊 Prob: {agent_prob:.0%}")
                        with m2:
                            st.caption(f"🎯 Conf: {agent_conf:.0%}")
                    
                    if recommendation:
                        st.caption(f"💡 {recommendation[:100]}")

    # Debate Transcript - Full round-robin conversation
    st.markdown("---")
    with st.expander("💬 Debate Transcript (Peek at Full Conversation)", expanded=False):
        st.markdown("**Round-Robin Expert Discussion:**")
        st.caption("Full unfiltered responses from each expert agent")
        
        for idx, agent_entry in enumerate(agents_list, 1):
            agent_name = agent_entry.get("agent", "Unknown Agent")
            raw_response = agent_entry.get("raw", "No response")
            parsed = agent_entry.get("parsed")
            
            # Determine icon based on success/failure
            if parsed and isinstance(parsed, dict):
                icon = "✅"
                status_color = "#90EE90"  # Light green
            elif raw_response.startswith("ERROR"):
                icon = "❌"
                status_color = "#FFB6C6"  # Light red
            else:
                icon = "⚠️"
                status_color = "#FFFFE0"  # Light yellow
            
            st.markdown(f"#### {icon} **Agent {idx}: {agent_name}**")
            
            # Show structured parsed data if available
            if parsed and isinstance(parsed, dict):
                with st.expander(f"Parsed Analysis", expanded=False):
                    st.json(parsed)
            
            # Show raw response with syntax highlighting
            with st.expander(f"Raw Response", expanded=False):
                st.code(raw_response, language="json" if raw_response.strip().startswith('{') else "text")
            
            st.divider()

def render_prediction_review_tab() -> None:
    """Render Prediction Review tab for analyzing historical predictions."""
    st.header("📋 Prediction Review")
    st.markdown("Review past predictions, analyze agent performance, and mark outcomes.")
    
    # Import dependencies
    import glob
    import json
    from pathlib import Path
    
    # Get all prediction reports
    reports_dir = Path("data/prediction_reports")
    if not reports_dir.exists():
        st.info("No prediction reports found. Make predictions in the Prediction tab first.")
        return
    
    report_files = sorted(glob.glob(str(reports_dir / "*.json")), reverse=True)
    
    if not report_files:
        st.info("No prediction reports found. Make predictions in the Prediction tab first.")
        return
    
    st.caption(f"Found {len(report_files)} prediction reports")
    
    # Filters
    col1, col2, col3 = st.columns(3)
    with col1:
        filter_domain = st.selectbox(
            "Filter by Domain",
            ["All"] + ["military", "financial", "energy", "technology", "climate", "geopolitical", 
                       "health", "infrastructure", "societal", "policy"]
        )
    with col2:
        sort_by = st.selectbox(
            "Sort by",
            ["Recent First", "Oldest First", "Highest Quality", "Lowest Quality"]
        )
    with col3:
        show_limit = st.number_input("Show reports", min_value=5, max_value=100, value=20, step=5)
    
    # Load and filter reports
    reports = []
    for report_file in report_files[:show_limit]:
        try:
            with open(report_file, 'r') as f:
                report = json.load(f)
                
                # Apply domain filter
                if filter_domain != "All":
                    if report.get("domain_analysis", {}).get("primary_domain") != filter_domain:
                        continue
                
                reports.append({
                    "file": report_file,
                    "data": report
                })
        except Exception as e:
            st.warning(f"Could not load {Path(report_file).name}: {e}")
    
    # Apply sorting
    if sort_by == "Oldest First":
        reports = list(reversed(reports))
    elif sort_by == "Highest Quality":
        reports = sorted(reports, key=lambda r: r["data"].get("data_quality_score", 0), reverse=True)
    elif sort_by == "Lowest Quality":
        reports = sorted(reports, key=lambda r: r["data"].get("data_quality_score", 0))
    
    if not reports:
        st.info(f"No reports match the filter: {filter_domain}")
        return
    
    # Report selector
    report_options = []
    for i, r in enumerate(reports):
        metadata = r["data"].get("metadata", {})
        question = r["data"].get("question", "Unknown")[:60]
        timestamp = metadata.get("timestamp", "Unknown")
        quality = r["data"].get("data_quality_score", 0)
        report_options.append(f"{i+1}. [{quality:.2f}] {timestamp} - {question}...")
    
    selected_idx = st.selectbox("Select Prediction Report", range(len(reports)), 
                                format_func=lambda i: report_options[i])
    
    if selected_idx is not None:
        selected_report = reports[selected_idx]["data"]
        st.divider()
        
        # Report overview
        st.subheader("📊 Prediction Overview")
        
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Data Quality", f"{selected_report.get('data_quality_score', 0):.2%}")
        with col2:
            consensus = selected_report.get("consensus_analysis", {})
            st.metric("Consensus", consensus.get("agreement_level", "Unknown"))
        with col3:
            st.metric("Consensus Strength", f"{consensus.get('consensus_strength', 0):.2%}")
        with col4:
            metadata = selected_report.get("metadata", {})
            st.metric("Agents", f"{metadata.get('successful_agents', 0)}/{metadata.get('total_agents', 0)}")
        
        # Question and domain
        st.markdown(f"**Question:** {selected_report.get('question', 'Unknown')}")
        
        domain_analysis = selected_report.get("domain_analysis", {})
        st.markdown(f"**Primary Domain:** {domain_analysis.get('primary_domain', 'Unknown')} "
                   f"(Confidence: {domain_analysis.get('confidence', 0):.2%})")
        
        if domain_analysis.get("secondary_domains"):
            st.markdown(f"**Secondary Domains:** {', '.join(domain_analysis.get('secondary_domains', []))}")
        
        if domain_analysis.get("keywords_found"):
            with st.expander("🔍 Domain Keywords Found"):
                st.write(", ".join(domain_analysis.get("keywords_found", [])))
        
        # Outcome tracking
        st.divider()
        st.subheader("✅ Mark Outcome")
        
        from forecasting.performance_tracker import PerformanceTracker
        
        tracker = PerformanceTracker()
        prediction_id = metadata.get("prediction_id")
        
        # Check if outcome already recorded
        existing_outcome = None
        if prediction_id:
            try:
                conn = sqlite3.connect(str(tracker.db_path))
                cursor = conn.execute(
                    "SELECT outcome, notes FROM prediction_outcomes WHERE prediction_id = ?",
                    (prediction_id,)
                )
                row = cursor.fetchone()
                if row:
                    existing_outcome = {"outcome": row[0], "notes": row[1]}
                conn.close()
            except Exception as e:
                st.warning(f"Could not check existing outcome: {e}")
        
        if existing_outcome:
            st.success(f"✅ Outcome already recorded: **{existing_outcome['outcome']}**")
            if existing_outcome['notes']:
                st.info(f"Notes: {existing_outcome['notes']}")
        else:
            col1, col2, col3 = st.columns(3)
            
            with col1:
                if st.button("✅ Mark Correct", type="primary"):
                    if prediction_id:
                        from forecasting.performance_tracker import PredictionOutcome
                        tracker.record_outcome(prediction_id, PredictionOutcome.CORRECT, "")
                        st.success("Marked as correct!")
                        st.rerun()
            
            with col2:
                if st.button("❌ Mark Incorrect", type="secondary"):
                    if prediction_id:
                        from forecasting.performance_tracker import PredictionOutcome
                        tracker.record_outcome(prediction_id, PredictionOutcome.INCORRECT, "")
                        st.warning("Marked as incorrect")
                        st.rerun()
            
            with col3:
                if st.button("⚠️ Mark Partial", type="secondary"):
                    if prediction_id:
                        from forecasting.performance_tracker import PredictionOutcome
                        tracker.record_outcome(prediction_id, PredictionOutcome.PARTIALLY_CORRECT, "")
                        st.info("Marked as partial")
                        st.rerun()
            
            notes = st.text_area("Outcome Notes (optional)", 
                               help="Add context about why the prediction was right/wrong")
            
            if notes and prediction_id:
                # Would need to update the last recorded outcome with notes
                pass
        
        # Agent responses detail
        st.divider()
        st.subheader("👥 Agent Responses")
        
        agent_responses = selected_report.get("agent_responses", [])
        if agent_responses:
            # Create dataframe for agent summary
            import pandas as pd
            
            agent_summary = []
            for resp in agent_responses:
                agent_summary.append({
                    "Agent": resp.get("agent_name", "Unknown"),
                    "Confidence": f"{resp.get('confidence', 0):.2%}",
                    "Base Weight": f"{resp.get('base_weight', 1.0):.2f}",
                    "Relevance Boost": f"{resp.get('relevance_boost', 1.0):.2f}x",
                    "Performance Boost": f"{resp.get('performance_boost', 1.0):.2f}x",
                    "Final Weight": f"{resp.get('adjusted_weight', 1.0):.2f}",
                    "Cached": "✓" if resp.get("cached", False) else "✗",
                    "Model": resp.get("model", "unknown")
                })
            
            df = pd.DataFrame(agent_summary)
            st.dataframe(df, width='stretch', hide_index=True)
            
            # Detailed responses
            with st.expander("📄 View Full Agent Responses"):
                for resp in agent_responses:
                    st.markdown(f"**{resp.get('agent_name', 'Unknown')}**")
                    st.markdown(resp.get("response", "No response"))
                    st.divider()
        
        # Consensus analysis
        st.divider()
        st.subheader("🤝 Consensus Analysis")
        
        consensus = selected_report.get("consensus_analysis", {})
        
        col1, col2 = st.columns(2)
        with col1:
            st.markdown(f"**Agreement Level:** {consensus.get('agreement_level', 'Unknown')}")
            st.markdown(f"**Consensus Strength:** {consensus.get('consensus_strength', 0):.2%}")
        
        with col2:
            if consensus.get("outlier_agents"):
                st.markdown("**Outlier Agents:**")
                for outlier in consensus.get("outlier_agents", []):
                    st.markdown(f"- {outlier}")
            else:
                st.markdown("**No outlier agents detected**")
        
        if consensus.get("confidence_distribution"):
            with st.expander("📊 Confidence Distribution"):
                st.json(consensus.get("confidence_distribution", {}))
        
        # Key insights
        if selected_report.get("key_insights"):
            st.divider()
            st.subheader("💡 Key Insights")
            for insight in selected_report.get("key_insights", []):
                st.markdown(f"- {insight}")
        
        # Uncertainty factors
        if selected_report.get("uncertainty_factors"):
            st.divider()
            st.subheader("⚠️ Uncertainty Factors")
            for factor in selected_report.get("uncertainty_factors", []):
                st.markdown(f"- {factor}")
        
        # Execution metadata
        with st.expander("⚙️ Execution Metadata"):
            st.json(metadata)
        
        # Raw report data
        with st.expander("📋 Raw Report Data"):
            st.json(selected_report)

def render_feeds_tab(cfg: Dict[str, Any]) -> None:
    """Render Feeds management tab."""
    st.header("📡 Data Feeds")
    st.caption("Manage data sources: RSS, APIs, Web Scraping.")
    
    feeds = cfg.get("feeds", [])
    
    tab_config, tab_add = st.tabs(["Configure", "Add New"])

    with tab_config:
        if not feeds:
            st.info("No feeds configured. Add one in the 'Add New' tab.")
        
        for i, feed in enumerate(feeds):
            feed_label = feed.get('url', 'Untitled')
            if len(feed_label) > 60:
                feed_label = feed_label[:60] + "..."
            
            with st.expander(f"Feed {i+1}: {feed_label}", expanded=False):
                # Responsive: 3-col on desktop, stack on mobile
                col1, col2, col3 = st.columns([2, 1, 1])
                with col1:
                    feed["url"] = st.text_input(f"URL", feed.get("url", ""), key=f"url_{i}", label_visibility="collapsed")
                with col2:
                    current_fetch = feed.get("fetch", "rss")
                    fetch_options = ["rss", "api", "scrape"]
                    try:
                        idx = fetch_options.index(current_fetch)
                    except ValueError:
                        idx = 0
                    feed["fetch"] = st.selectbox(f"Fetch", fetch_options, index=idx, key=f"fetch_{i}", label_visibility="collapsed")
                with col3:
                    feed["cooldown"] = st.number_input(f"Refresh", value=int(feed.get("cooldown", 300)), key=f"cool_{i}", min_value=60, label_visibility="collapsed")
                
                feed["active"] = st.checkbox(f"Enabled", feed.get("active", True), key=f"act_{i}")

                if feed["fetch"] == "api":
                    st.markdown("#### ⚙️ API Configuration")
                    feed["api_endpoint"] = st.text_input("Endpoint", feed.get("api_endpoint", ""), key=f"api_ep_{i}")
                    ac1, ac2 = st.columns(2)
                    with ac1:
                        feed["api_params"] = st.text_area("Params (JSON)", value=json.dumps(feed.get("api_params", {})), key=f"api_params_{i}", height=100)
                    with ac2:
                        feed["api_headers"] = st.text_area("Headers (JSON)", value=json.dumps(feed.get("api_headers", {})), key=f"api_headers_{i}", height=100)
                    
                    if st.button(f"Test API", key=f"test_api_{i}"):
                        try:
                            import requests
                            headers = json.loads(feed.get("api_headers", "{}")) if isinstance(feed.get("api_headers", "{}"), str) else feed.get("api_headers", {})
                            params = json.loads(feed.get("api_params", "{}")) if isinstance(feed.get("api_params", "{}"), str) else feed.get("api_params", {})
                            target_url = feed.get("api_endpoint") or feed.get("url")
                            if not target_url:
                                st.error("No URL configured.")
                            else:
                                resp = requests.get(target_url, params=params, headers=headers, timeout=10)
                                if resp.status_code == 200:
                                    st.success(f"Success (200 OK). {len(resp.text)} bytes.")
                                else:
                                    st.error(f"Failed: HTTP {resp.status_code}")
                        except Exception as e:
                            st.error(f"Error: {repr(e)[:200]}")

                elif feed["fetch"] == "scrape":
                    st.markdown("#### 🕸️ Scraper Configuration")
                    feed["scrape_selector"] = st.text_input("CSS Selector", feed.get("scrape_selector", ""), key=f"scrape_sel_{i}")
                    
                    if st.button(f"Test Scraper", key=f"test_scrape_{i}"):
                        try:
                            import requests
                            from bs4 import BeautifulSoup
                            r = requests.get(feed.get("url"), timeout=10)
                            soup = BeautifulSoup(r.text, "html.parser")
                            sel = feed.get("scrape_selector", "")
                            found = soup.select(sel) if sel else []
                            if found:
                                st.success(f"Found {len(found)} elements.")
                                with st.expander("First Match"):
                                    st.text(found[0].get_text()[:500])
                            else:
                                st.warning("No elements found.")
                        except Exception as e:
                            st.error(f"Error: {repr(e)[:200]}")
                
                if st.button("🗑️ Remove", key=f"rem_{i}"):
                    feeds.pop(i)
                    cfg["feeds"] = feeds
                    save_feeds_config(cfg)
                    st.success("Removed!")
                    st.rerun()

    with tab_add:
        st.subheader("Add New Feed")
        with st.form("add_feed_form"):
            new_url = st.text_input("URL", placeholder="https://example.com/rss")
            new_cooldown = st.number_input("Refresh (sec)", value=300, min_value=60)
            submitted = st.form_submit_button("Add Feed")
            if submitted and new_url:
                feeds.append({"url": new_url, "cooldown": new_cooldown, "active": True, "fetch": "rss"})
                cfg["feeds"] = feeds
                save_feeds_config(cfg)
                st.success("Added!")
                st.rerun()

    if st.button("💾 Save All Changes", type="primary"):
        cfg["feeds"] = feeds
        save_feeds_config(cfg)
        st.success("Config saved!")


def render_model_config_tab() -> None:
    """Render Model Configuration tab: manage Ollama connection, models, and expert agents."""
    st.header("🧠 Model Configuration")
    
    cfg = load_feeds_config()
    ollama_cfg = cfg.get("ollama", {})
    
    # Section 1: Ollama Connection Settings (Collapsible)
    with st.expander("🔌 Ollama Server Connection", expanded=False):
        col1, col2 = st.columns(2)
        with col1:
            host_input = st.text_input("Host", value=ollama_cfg.get("host", "http://localhost"), help="e.g., http://192.168.1.140")
        with col2:
            port_input = st.number_input("Port", value=int(ollama_cfg.get("port", 11434)), min_value=1, max_value=65535)
        
        host_value = (host_input or "http://localhost").strip() or "http://localhost"
        effective_host = _normalize_host(host_value)
        effective_port = int(port_input or 11434)
        
        # Initialize models cache
        if "ollama_models" not in st.session_state:
            st.session_state["ollama_models"] = []
        
        endpoint = (effective_host, effective_port)
        if st.session_state.get("_ollama_endpoint") != endpoint:
            st.session_state["_ollama_endpoint"] = endpoint
            try:
                st.session_state["ollama_models"] = list_models_http(effective_host, effective_port, None)
            except Exception:
                st.session_state["ollama_models"] = []
        
        # Connection status indicator
        available_models = st.session_state.get("ollama_models", [])
        if available_models:
            st.success(f"✅ Connected • {len(available_models)} models available")
        else:
            st.warning("⚠️ Not connected or no models found")
        
        col_test, col_save = st.columns(2)
        
        with col_test:
            if st.button("🧪 Test Connection", width='stretch'):
                with st.spinner("Testing..."):
                    result = test_ollama_connection(effective_host, effective_port, None)
                    if result["success"]:
                        st.success(f"✅ {result['details']}")
                    else:
                        st.error(f"❌ {result['status']}: {result['details']}")
        
        with col_save:
            if st.button("💾 Save & Refresh", width='stretch'):
                cfg["ollama"] = {"host": host_input, "port": int(port_input), "mode": "http"}
                save_feeds_config(cfg)
                st.session_state["ollama_models"] = list_models_http(effective_host, effective_port, None)
                st.success("✅ Saved!")
                st.rerun()
    
    # Get connection details for downstream use
    effective_host = _normalize_host(ollama_cfg.get("host", "http://localhost"))
    effective_port = int(ollama_cfg.get("port", 11434))
    available_models = st.session_state.get("ollama_models", [])
    
    # Section 2: Expert Agents (Primary focus)
    st.subheader("👥 Expert Agents")
    st.caption("Enable experts and download their required models automatically")
    render_expert_roster_integrated(effective_host, effective_port, available_models)


def render_model_install_tab() -> None:
    """Render Model Install tab: standalone model downloader."""
    st.header("📥 Install Model")
    
    col1, col2 = st.columns([0.7, 0.3])
    with col1:
        model_name = st.text_input(
            "Model Name",
            placeholder="e.g., llama2, mistral, gemma:2b, qwen2.5:0.5b-instruct",
            help="Enter the exact model name from Ollama library"
        )
    
    with col2:
        st.markdown("<br>", unsafe_allow_html=True)  # Vertical alignment
        if st.button("📥 Download Model", type="primary", width='stretch', disabled=not model_name):
            if not model_name:
                st.warning("⚠️ Please enter a model name")
            else:
                # Load Ollama connection config
                cfg = load_feeds_config()
                ollama_cfg = cfg.get("ollama", {})
                host = _normalize_host(str(ollama_cfg.get("host", "http://localhost")))
                port = int(ollama_cfg.get("port", 11434) or 11434)
                
                with st.spinner(f"Downloading {model_name}..."):
                    success, message = pull_model_http(host, port, model_name)
                    if success:
                        st.success(f"✅ {message}")
                        # Clear Ollama model cache after successful install
                        if "ollama_models" in st.session_state:
                            del st.session_state["ollama_models"]
                    else:
                        st.error(f"❌ {message}")
    
    st.markdown("---")
    st.info("💡 **Tip**: After installing, enable the model in the **Expert Roster** section above.")


def render_local_threats_tab() -> None:
    """Render local threat monitoring interface with dynamic location lookup."""
    st.subheader("🚨 Local Threat Monitoring")
    st.markdown("Real-time police dispatch monitoring for configured jurisdictions")
    
    try:
        from forecasting.local_threats import get_available_zip_codes, get_jurisdictions, get_jurisdiction_for_zip
        from forecasting.local_threat_integration import fetch_local_threat_feeds_with_health_tracking
    except ImportError:
        st.error("❌ Local threat module not available. Ensure Playwright is installed: `pip install playwright`")
        return
    
    # Get available jurisdictions and identifiers
    available_identifiers = get_available_zip_codes()
    available_jurisdictions = get_jurisdictions()
    
    if not available_identifiers and not available_jurisdictions:
        st.warning("⚠️ No jurisdictions configured. See config/dispatch_jurisdictions.json")
        st.info("Add your jurisdictions to the configuration file to enable local threat monitoring.")
        return
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("#### Search by Identifier")
        identifier_input = st.text_input(
            "Enter Location Identifier",
            placeholder="e.g., zip code, area code, or district ID",
            key="local_threat_identifier"
        )
        
        discovered_jurisdiction = None
        if identifier_input:
            if identifier_input in available_identifiers:
                st.success(f"✓ Found (preconfigured): **{available_identifiers[identifier_input]}**")
                discovered_jurisdiction = available_identifiers[identifier_input]
            else:
                # Try LLM discovery
                with st.spinner("🔍 Searching for jurisdiction via LLM..."):
                    discovered_jurisdiction = get_jurisdiction_for_zip(identifier_input, use_llm=True)
                    if discovered_jurisdiction:
                        st.success(f"✓ Discovered: **{discovered_jurisdiction}**")
                    else:
                        st.warning(f"⚠️ Could not find jurisdiction for '{identifier_input}'")
                        st.caption(f"Preconfigured: {', '.join(list(available_identifiers.keys())[:5])}...")
    
    with col2:
        st.markdown("#### Search by Jurisdiction")
        jurisdiction_select = st.selectbox(
            "Select Jurisdiction",
            ["All Configured"] + available_jurisdictions,
            key="local_threat_jurisdiction"
        )
    
    if st.button("🔍 Fetch Local Threats", width='stretch'):
        with st.spinner("Scraping dispatch feeds..."):
            try:
                # Determine which identifier/jurisdiction to use
                identifier_to_use = None
                
                if identifier_input:
                    # Use discovered or preconfigured identifier
                    if identifier_input in available_identifiers or discovered_jurisdiction:
                        identifier_to_use = identifier_input
                elif jurisdiction_select != "All Configured":
                    # Find first identifier for selected jurisdiction
                    for z, j in available_identifiers.items():
                        if j == jurisdiction_select:
                            identifier_to_use = z
                            break
                
                feed_items = fetch_local_threat_feeds_with_health_tracking(
                    zip_code=identifier_to_use,
                    lookback_hours=6,
                    tracker_db_path="data/local_threats.db",
                    health_db_path="data/feed_health.db"
                )
                
                if feed_items:
                    st.success(f"✅ Found {len(feed_items)} active dispatch calls")
                    
                    # Display summary metrics
                    col1, col2, col3 = st.columns(3)
                    
                    severities = [item.get('severity', 0) for item in feed_items]
                    jurisdictions_found = set(item.get('jurisdiction', 'Unknown') for item in feed_items)
                    
                    with col1:
                        st.metric("Total Calls", len(feed_items))
                    with col2:
                        st.metric("Avg Severity", f"{sum(severities) / len(severities):.1f}/5")
                    with col3:
                        st.metric("Jurisdictions", len(jurisdictions_found))
                    
                    st.markdown("---")
                    st.markdown("#### Active Dispatch Calls")
                    
                    # Display calls grouped by severity
                    for severity_level in [5, 4, 3]:
                        calls_at_level = [item for item in feed_items if item.get('severity') == severity_level]
                        if calls_at_level:
                            severity_names = {5: "🔴 Critical", 4: "🟠 High", 3: "🟡 Medium"}
                            st.subheader(severity_names.get(severity_level, f"Level {severity_level}"))
                            
                            for call in calls_at_level:
                                with st.container(border=True):
                                    col1, col2 = st.columns([3, 1])
                                    with col1:
                                        st.write(f"**{call['title']}**")
                                        st.caption(f"📍 {call.get('jurisdiction', 'Unknown')}")
                                        st.caption(f"🕐 {call.get('published', 'N/A')}")
                                    with col2:
                                        st.metric("Severity", f"{call.get('severity', 0)}/5")
                    
                    # Raw data export option
                    st.markdown("---")
                    if st.button("📥 Export as JSON"):
                        st.json(feed_items)
                
                else:
                    st.warning("⚠️ No dispatch calls found for the selected jurisdiction")
                    st.caption("This may mean no active calls or dispatch site structure has changed")
            
            except Exception as e:
                st.error(f"❌ Error fetching local threats: {e}")
                st.caption("Check that Playwright is installed and dispatch sites are accessible")
    
    st.markdown("---")
    st.markdown("#### Configured Jurisdictions")
    
    if available_jurisdictions:
        cols = st.columns(min(len(available_jurisdictions), 4))
        for idx, jurisdiction in enumerate(available_jurisdictions):
            with cols[idx % len(cols)]:
                identifiers_for_jurisdiction = [z for z, j in available_identifiers.items() if j == jurisdiction]
                st.info(f"**{jurisdiction}**\nIDs: {', '.join(identifiers_for_jurisdiction[:2])}")
    else:
        st.info("No jurisdictions configured yet. Add them to config/dispatch_jurisdictions.json")


def main() -> None:
    """Main app entry point."""
    st.set_page_config(page_title="Event Forecasting Console", layout="wide", page_icon="🔮", initial_sidebar_state="expanded")
    
    # Hide Streamlit UI chrome and optimize for responsive scaling
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
        
        /* Responsive column padding */
        @media (max-width: 768px) {
            .stMetric {font-size: 0.8rem;}
            .stTabs [data-baseweb="tab"] {padding: 0.4rem 0.5rem; font-size: 0.75rem;}
            .stForm {padding: 0.5rem;}
        }
        
        @media (max-width: 480px) {
            .stMetric {font-size: 0.7rem;}
            .stTabs [data-baseweb="tab"] {padding: 0.3rem 0.4rem; font-size: 0.65rem;}
        }
        </style>
    """
    st.markdown(hide_streamlit_style, unsafe_allow_html=True)
    
    st.title("🔮 Event Forecasting Console")
    # Display active remote model status (GPT-5 global enablement)
    try:
        from forecasting.dispatch_discovery import load_model_config, is_model_globally_enabled
        cfg_model = load_model_config()
        model_name = cfg_model.get("model_name", "gpt-5")
        enabled = is_model_globally_enabled()
        endpoint = cfg_model.get("remote_llm_endpoint") or "(no endpoint configured)"
        status_str = f"🧠 Model: {model_name} • {'Enabled' if enabled else 'Disabled'}"
        st.caption(status_str)
        if enabled:
            st.caption(f"Remote LLM Endpoint: {endpoint}")
    except Exception:
        st.caption("🧠 Model: (config not loaded)")
    
    cfg = load_feeds_config()
    db_path = st.sidebar.text_input("DB Path", "data/live.db")
    
    # Quick start checklist in sidebar
    with st.sidebar.expander("🚦 Quick Start", expanded=True):
        feeds_ok = bool(cfg.get("feeds"))
        
        # Check if Ollama is configured and models are available
        models_ok = False
        try:
            from forecasting.ollama_utils import list_models_http
            ollama_cfg = cfg.get("ollama", {})
            host = ollama_cfg.get("host", "http://localhost")
            port = int(ollama_cfg.get("port", 11434))
            if not host.startswith("http"):
                host = f"http://{host}"
            models = list_models_http(host.rstrip("/"), port, None)
            models_ok = len(models) > 0
        except Exception:
            models_ok = False
        
        try:
            df_tmp = load_stats(db_path)
            data_ok = len(df_tmp) > 0
        except Exception:
            data_ok = False

        st.markdown(f"- {'✅' if feeds_ok else '⬜'} Feeds configured")
        st.markdown(f"- {'✅' if models_ok else '⬜'} Models available")
        st.markdown(f"- {'✅' if data_ok else '⬜'} Data present")

    # Navigation tabs
    tabs = st.tabs(["📊 Dashboard", "🔮 Prediction", "📋 Prediction Review", "📡 Feeds", "🚨 Local Threats", "🧠 Model Config", "📥 Install Model", "⚙️ Settings"])
    
    with tabs[0]:
        render_dashboard_tab(db_path)
    with tabs[1]:
        render_prediction_tab(db_path)
    with tabs[2]:
        render_prediction_review_tab()
    with tabs[3]:
        render_feeds_tab(cfg)
    with tabs[4]:
        render_local_threats_tab()
    with tabs[5]:
        render_model_config_tab()
    with tabs[6]:
        render_model_install_tab()
    with tabs[7]:
        st.subheader("System Settings")
        cfg_reload = load_feeds_config()
        raw = st.text_area("feeds.json", value=json.dumps(cfg_reload, indent=2), height=400)
        col1, col2 = st.columns([1, 1])
        with col1:
            if st.button("Save"):
                try:
                    new = json.loads(raw)
                    save_feeds_config(new)
                    st.success("Saved!")
                except Exception as e:
                    st.error(f"Invalid JSON: {e}")
        with col2:
            if st.button("Reload"):
                st.rerun()


if __name__ == "__main__":
    main()
