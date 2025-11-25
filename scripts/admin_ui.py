#!/usr/bin/env python3
"""Admin UI for managing feeds, cooldowns, and monitoring ingestion status.

Run with:
  streamlit run scripts/admin_ui.py
"""
import streamlit as st
import json
from pathlib import Path
import sqlite3
from forecasting.ollama_utils import list_models_http, pull_model_http


def load_feeds_config() -> dict:
    """Load feeds config, ensuring it's always a dict."""
    if Path("feeds.json").exists():
        with open("feeds.json", "r") as fh:
            data = json.load(fh)
            # Ensure we always return a dict, even if file contains a list
            if isinstance(data, list):
                return {"feeds": data}
            return data if isinstance(data, dict) else {"feeds": []}
    return {"feeds": []}


def save_feeds_config(cfg):
    with open("feeds.json", "w") as fh:
        json.dump(cfg, fh, indent=2)


def get_db_stats(db_path="data/live.db"):
    try:
        conn = sqlite3.connect(db_path)
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


def main():
    st.set_page_config(page_title="Event AI Admin", layout="wide", page_icon="🔮")
    
    # Hide Streamlit main menu, header and footer
    hide_streamlit_style = """
        <style>
        #MainMenu {visibility: hidden;}
        footer {visibility: hidden;}
        header {visibility: hidden;}
        .block-container {padding-top: 1rem;}
        </style>
    """
    st.markdown(hide_streamlit_style, unsafe_allow_html=True)
    
    st.title("🔮 Event Forecasting Admin")
    st.markdown("Configure your data sources and AI models.")
    
    cfg: dict = load_feeds_config()  # Type annotation to help type checker
    feeds = cfg.get("feeds", [])

    # --- Stats Section ---
    with st.expander("📊 System Status & Database Stats", expanded=True):
        stats = get_db_stats()
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("📚 Articles", stats.get("articles", 0))
        c2.metric("📥 Ingest Logs", stats.get("logs", 0))
        c3.metric("📡 Active Feeds", stats.get("feeds", 0))
        c4.metric("🌐 Unique Sources", stats.get("sources", 0))

    st.markdown("---")
    
    # --- Feeds Section ---
    st.header("📡 Data Feeds")
    st.caption("Manage where the system gets its information. Supports RSS, JSON APIs, and Web Scraping.")
    
    tab_config, tab_add = st.tabs(["📝 Configure Existing Feeds", "➕ Add New Feed"])

    with tab_config:
        if not feeds:
            st.info("No feeds configured yet. Switch to the 'Add New Feed' tab to get started.")
        
        for i, feed in enumerate(feeds):
            feed_label = feed.get('url', 'Untitled')
            if len(feed_label) > 60:
                feed_label = feed_label[:60] + "..."
            
            # Use expander to keep UI clean
            with st.expander(f"Feed {i+1}: {feed_label}", expanded=False):
                col1, col2 = st.columns([3, 1])
                with col1:
                    feed["url"] = st.text_input(f"URL", feed.get("url", ""), key=f"url_{i}", help="The source URL for the feed or API.")
                with col2:
                    feed["active"] = st.checkbox(f"Enabled", feed.get("active", True), key=f"act_{i}")

                c_type, c_cool = st.columns([1, 1])
                with c_type:
                    current_fetch = feed.get("fetch", "rss")
                    fetch_options = ["rss", "api", "scrape"]
                    try:
                        idx = fetch_options.index(current_fetch)
                    except ValueError:
                        idx = 0
                    feed["fetch"] = st.selectbox(
                        f"Fetch Method", fetch_options, index=idx, key=f"fetch_{i}",
                        help="RSS: Standard feeds. API: JSON endpoints. Scrape: HTML parsing."
                    )
                with c_cool:
                    feed["cooldown"] = st.number_input(
                        f"Refresh Interval (seconds)", value=int(feed.get("cooldown", 300)), key=f"cool_{i}", min_value=60,
                        help="How often to check this feed for new content."
                    )

                # Advanced settings based on type
                if feed["fetch"] == "api":
                    st.markdown("#### ⚙️ API Configuration")
                    feed["api_endpoint"] = st.text_input("API Endpoint (if different from URL)", feed.get("api_endpoint", ""), key=f"api_ep_{i}")
                    
                    ac1, ac2 = st.columns(2)
                    with ac1:
                        feed["api_headers"] = st.text_area("API Headers (JSON)", value=json.dumps(feed.get("api_headers", {})), key=f"api_headers_{i}", height=100)
                    
                        if st.button(f"🧪 Test API Connection", key=f"test_api_{i}"):
                            try:
                                import requests

                                # validate JSON inputs
                                try:
                                    headers = json.loads(feed.get("api_headers", "{}")) if isinstance(feed.get("api_headers", "{}"), str) else feed.get("api_headers", {})
                                except Exception as e:
                                    st.error(f"Invalid API headers JSON: {e}")
                                    headers = {}
                                try:
                                    params = json.loads(feed.get("api_params", "{}")) if isinstance(feed.get("api_params", "{}"), str) else feed.get("api_params", {})
                                except Exception as e:
                                    st.error(f"Invalid API params JSON: {e}")
                                    params = {}

                                target_url = feed.get("api_endpoint") or feed.get("url")
                                if not target_url:
                                    st.error("No URL configured for this feed.")
                                else:
                                    resp = requests.get(target_url, params=params, headers=headers, timeout=10)
                                    if resp.status_code == 200:
                                        st.success(f"Success (200 OK). Received {len(resp.text)} bytes.")
                                        with st.expander("View Response Snippet"):
                                            st.code(resp.text[:500])
                                    else:
                                        st.error(f"Failed: HTTP {resp.status_code} - {resp.text[:500]}")
                            except Exception as e:
                                st.error(f"Connection failed: {repr(e)}")

                elif feed["fetch"] == "scrape":
                    st.markdown("#### 🕸️ Scraper Configuration")
                    feed["scrape_selector"] = st.text_input("CSS Selector", feed.get("scrape_selector", ""), key=f"scrape_sel_{i}", help="e.g. 'div.article-content' or 'main p'")
                    
                    if st.button(f"🧪 Test Scraper", key=f"test_scrape_{i}"):
                        try:
                            import requests
                            from bs4 import BeautifulSoup
                            r = requests.get(feed.get("url"), timeout=10)
                            soup = BeautifulSoup(r.text, "html.parser")
                            sel = feed.get("scrape_selector", "")
                            found = soup.select(sel) if sel else []
                            if found:
                                st.success(f"Found {len(found)} matching elements.")
                                with st.expander("View First Match"):
                                    st.text(found[0].get_text()[:500])
                            else:
                                st.warning("No elements found matching that selector.")
                        except Exception as e:
                            st.error(f"Scraping failed: {e}")
                
                # Remove button inside the expander for context
                if st.button("🗑️ Remove This Feed", key=f"rem_{i}"):
                    feeds.pop(i)
                    cfg["feeds"] = feeds
                    save_feeds_config(cfg)
                    st.success("Feed removed!")
                    st.rerun()

    with tab_add:
        st.subheader("Add New Source")
        with st.form("add_feed_form"):
            new_url = st.text_input("Feed URL", placeholder="https://example.com/rss")
            new_cooldown = st.number_input("Refresh Interval (seconds)", value=300, min_value=60)
            submitted = st.form_submit_button("Add Feed")
            if submitted and new_url:
                feeds.append({"url": new_url, "cooldown": new_cooldown, "active": True, "fetch": "rss"})
                cfg["feeds"] = feeds
                save_feeds_config(cfg)
                st.success("Feed added successfully!")
                st.rerun()

    if st.button("💾 Save All Changes", type="primary"):
        cfg["feeds"] = feeds
        save_feeds_config(cfg)
        st.success("Configuration saved successfully!")

    st.markdown("---")
    st.header("🤖 AI Model Settings (Ollama)")
    st.caption("Configure the local or remote AI model provider.")

    ollama_cfg = cfg.get("ollama", {})
    if not isinstance(ollama_cfg, dict):
        ollama_cfg = {}

    with st.expander("⚙️ Connection Settings", expanded=True):
        c_mode, c_host, c_port = st.columns([1, 2, 1])
        with c_mode:
            mode_idx = 0 if ollama_cfg.get("mode", "cli") == "cli" else 1
            mode = st.selectbox("Connection Mode", ["cli", "http"], index=mode_idx, 
                                help="CLI: Runs 'ollama run' locally. HTTP: Connects to an Ollama server.")
        with c_host:
            host = st.text_input("Host URL", value=ollama_cfg.get("host", "http://localhost"), disabled=(mode=="cli"))
        with c_port:
            port = st.number_input("Port", value=int(ollama_cfg.get("port", 11434)), min_value=1, max_value=65535, disabled=(mode=="cli"))
        
        if mode == "http":
            api_key = st.text_input("API Key (Optional)", value=ollama_cfg.get("api_key", ""), type="password")
        else:
            api_key = ollama_cfg.get("api_key", "")

    # Model discovery area
    st.subheader("🧠 Model Selection")
    if "ollama_models" not in st.session_state:
        st.session_state["ollama_models"] = []

    def refresh_models():
        """Refresh available models from Ollama (HTTP only)."""
        if mode == "http":
            models = list_models_http(host or "http://localhost", int(port) or 11434, api_key)
        else:
            # For CLI mode, cannot list models programmatically
            models = []
        st.session_state["ollama_models"] = models

    col_refresh, col_sel = st.columns([1, 3])
    with col_refresh:
        st.write("") # spacer
        st.write("") # spacer
        if st.button("🔄 Refresh Models"):
            refresh_models()

    models = st.session_state.get("ollama_models", [])
    with col_sel:
        if models:
            current_model = ollama_cfg.get("model", "")
            try:
                idx = models.index(current_model)
            except ValueError:
                idx = 0
            model = st.selectbox("Select Model", models, index=idx)
        else:
            model = st.text_input("Model Name (e.g. llama2)", value=ollama_cfg.get("model", ""))
            if not models:
                st.caption("No models found. Click Refresh or enter name manually.")

    if st.button("💾 Save AI Settings"):
        # Ensure cfg is dict before setting keys
        if not isinstance(cfg, dict):
            cfg = {"feeds": feeds if isinstance(feeds, list) else []}
        cfg["ollama"] = {"mode": mode, "model": model, "host": host, "port": int(port), "api_key": api_key}
        save_feeds_config(cfg)
        st.success("AI settings saved!")

    if st.button("Test Ollama"):
        # Build a tiny test prompt
        test_prompt = "Tell me in one sentence what the test prompt is checking." 
        st.info("Running test against configured Ollama...")
        try:
            import subprocess, shutil, requests
            ocfg = cfg.get("ollama", {}) if isinstance(cfg, dict) else {}
            if ocfg.get("mode", "cli") == "cli":
                if not shutil.which("ollama"):
                    st.error("`ollama` CLI not found in PATH")
                else:
                    proc = subprocess.run(["ollama", "run", ocfg.get("model", "")], input=test_prompt, text=True, capture_output=True, timeout=30)
                    if proc.returncode != 0:
                        st.error(f"Ollama CLI error: {proc.stderr}")
                    else:
                        st.success("Ollama CLI response:")
                        st.code(proc.stdout)
            else:
                # HTTP mode: POST to configured host:port/ (user must configure endpoint semantics)
                host_val = ocfg.get('host', 'http://localhost')
                port_val = ocfg.get('port', 11434)
                url = f"{host_val.rstrip('/')}:{port_val}/api/predict"
                headers = {"Content-Type": "application/json"}
                if ocfg.get("api_key"):
                    headers["Authorization"] = f"Bearer {ocfg.get('api_key')}"
                payload = {"model": ocfg.get("model", ""), "prompt": test_prompt}
                resp = requests.post(url, json=payload, headers=headers, timeout=20)
                if resp.status_code != 200:
                    st.error(f"HTTP call failed: {resp.status_code} {resp.text}")
                else:
                    st.success("Ollama HTTP response:")
                    st.json(resp.json())
        except Exception as e:
            st.error(f"Test failed: {e}")

    st.markdown("---")
    st.subheader("Install / Pull Model")
    new_model = st.text_input("Model to install (e.g. llava/llama2)")
    if st.button("Pull model (HTTP)"):
        if not host:
            st.error("Host is required")
        else:
            success, msg = pull_model_http(host, int(port) or 11434, new_model, api_key)
            if success:
                st.success(msg)
                refresh_models()
            else:
                st.error(msg)


if __name__ == "__main__":
    main()
