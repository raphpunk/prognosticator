#!/usr/bin/env python3
"""Streamlit dashboard for ingestion stats and scenario lab."""

import sqlite3
import json
import shutil
from pathlib import Path

import pandas as pd
import streamlit as st

from forecasting.agents import run_conversation
from forecasting.ollama_utils import list_models_cli, list_models_http


def load_stats(db_path: str = "data/live.db") -> pd.DataFrame:
    """Safely load articles with path validation."""
    db_path = Path(db_path).resolve()
    if not db_path.exists():
        return pd.DataFrame()
    try:
        conn = sqlite3.connect(str(db_path))
        df_articles = pd.read_sql_query("SELECT published, source_url, content_hash FROM articles", conn)
        conn.close()
        return df_articles
    except Exception:
        return pd.DataFrame()


def render_ingest_tab(db_path: str):
    st.header("📰 Data Ingestion")
    
    if st.button("🔄 Refresh Data"):
        df_articles = load_stats(db_path)
        
        # Top metrics
        m1, m2, m3 = st.columns(3)
        m1.metric("Total Articles", len(df_articles))
        m2.metric("Sources", df_articles["source_url"].nunique())
        if not df_articles.empty and "published" in df_articles.columns:
            latest = pd.to_datetime(df_articles["published"], errors='coerce').max()
            m3.metric("Latest Article", latest.strftime("%Y-%m-%d %H:%M") if pd.notnull(latest) else "N/A")

        # Aggregate by registered domain using tldextract for accuracy
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
        left, right = st.columns([3, 2])
        with left:
            st.bar_chart(top_domains)
        with right:
            # show counts and percentages
            total = len(df_articles)
            tbl = top_domains.rename_axis("domain").reset_index(name="count")
            if total > 0:
                tbl["pct"] = (tbl["count"] / total * 100).round(1).astype(str) + "%"
            st.table(tbl)

        with st.expander("📄 Recent Articles (Grouped by Domain)"):
            if not df_articles.empty:
                df_show = df_articles.sort_values(by="published", ascending=False).head(200)[["published", "reg_domain", "source_url"]]
                st.dataframe(df_show, width=0, height=400)
            else:
                st.info("No articles found.")
    else:
        st.info("Click 'Refresh Data' to load the latest statistics.")


def render_scenario_tab(db_path: str):
    st.header("🔮 Prediction Lab")
    st.markdown("Ask the AI to analyze recent events and predict outcomes.")
    
    with st.expander("ℹ️ How it works", expanded=False):
        st.markdown("""
        1. **Ask a question** about a future event or trend.
        2. The system retrieves relevant articles from the database.
        3. Multiple AI agents debate the topic.
        4. A final probability and verdict is synthesized.
        """)

    with st.form("prediction_form"):
        question = st.text_area(
            "What do you want to know?",
            value=st.session_state.get("scenario_question", "How likely is a major disruption to global semiconductor supply within 3 months?"),
            help="Be specific about the event and timeframe."
        )
        
        c1, c2 = st.columns(2)
        with c1:
            days = st.slider("Analyze last X days", min_value=1, max_value=90, value=14, help="How far back to look for news.")
        with c2:
            topk = st.slider("Articles to read", min_value=3, max_value=20, value=5, help="More articles = more context but slower.")
            
        submitted = st.form_submit_button("🚀 Run Analysis", type="primary")

    if st.button("Clear Results"):
        st.session_state.pop("scenario_result", None)
        st.rerun()

    if submitted:
        st.session_state["scenario_question"] = question
        with st.status("🤖 AI Agents are working...", expanded=True) as status:
            st.write("🔍 Searching database for relevant news...")
            result = run_conversation(question=question, db_path=db_path, topk=topk, days=days)
            st.write("✅ Analysis complete.")
            status.update(label="Analysis Complete!", state="complete", expanded=False)
        st.session_state["scenario_result"] = result

    result = st.session_state.get("scenario_result")
    if not result:
        st.info("Enter a question above and click Run Analysis to start.")
        return

    summary = result.get("summary", {})
    st.markdown("### Outcome Synthesis")
    col_s1, col_s2, col_s3 = st.columns(3)
    with col_s1:
        st.metric("Verdict", summary.get("verdict", "Pending"))
    with col_s2:
        st.metric("Probability", summary.get("probability"))
    with col_s3:
        st.metric("Confidence", summary.get("confidence"))
    st.write(summary.get("rationale", summary))

    st.markdown("### Agent Briefings")
    for agent_entry in result.get("agents", []):
        with st.expander(agent_entry["agent"]):
            parsed = agent_entry.get("parsed")
            if parsed:
                st.json(parsed)
            st.markdown("**Raw Output**")
            st.code(agent_entry.get("raw", ""))

    st.markdown("### Evidence Snippets")
    for item in result.get("context_items", []):
        st.write(f"**{item['title'] or '[no title]'}** (score={item['score']:.2f})")
        st.caption(item["source_url"])
        st.write(item["snippet"])


def main():
    st.set_page_config(page_title="Event Forecasting Console", layout="wide")
    st.title("Event Forecasting Console")
    db_path = st.text_input("DB Path", "data/live.db")
    cfg = load_feeds_config()

    # Show AI settings directly on the main page for quick access
    render_ai_settings(cfg)
    # First-time setup checklist to guide entry-level users
    with st.expander("🚦 Quick Start Checklist", expanded=True):
        feeds_ok = bool(cfg.get("feeds"))
        ollama_ok = bool(cfg.get("ollama") and cfg.get("ollama", {}).get("model"))
        # Try to detect models (non-blocking)
        models_available = bool(st.session_state.get("ollama_models"))
        # Check if any articles exist
        try:
            df_tmp = load_stats(db_path)
            data_ok = len(df_tmp) > 0
        except Exception:
            data_ok = False

        st.markdown(f"- {'✅' if feeds_ok else '⬜'} Feeds configured")
        st.markdown(f"- {'✅' if ollama_ok else '⬜'} Ollama model selected")
        st.markdown(f"- {'✅' if models_available else '⬜'} Models available (refresh if empty)")
        st.markdown(f"- {'✅' if data_ok else '⬜'} Ingested data present")
        st.caption("Follow these steps before running the Prediction Lab. Click 'Refresh Models' in the sidebar if needed.")
    # Hide Streamlit main menu and footer (removes Deploy button)
    hide_streamlit_style = """
        <style>
        #MainMenu {visibility: hidden;}
        footer {visibility: hidden;}
        </style>
    """
    st.markdown(hide_streamlit_style, unsafe_allow_html=True)
    tabs = st.tabs(["Ingest", "Prediction Lab", "Settings"])
    with tabs[0]:
        render_ingest_tab(db_path)
    with tabs[1]:
        render_scenario_tab(db_path)
    with tabs[2]:
        render_settings_tab()


def load_feeds_config(path: str = "feeds.json"):
    import json, os

    if not os.path.exists(path):
        return {"feeds": []}
    try:
        with open(path, "r") as fh:
            return json.load(fh)
    except Exception:
        return {"feeds": []}


def save_feeds_config(cfg: dict, path: str = "feeds.json"):
    import json, os

    with open(path, "w") as fh:
        json.dump(cfg, fh, indent=2)


def render_settings_tab():
    st.subheader("System Settings")
    cfg = load_feeds_config()
    st.markdown("Edit `feeds.json` directly or use the Admin UI for feed-level changes.")
    raw = st.text_area("feeds.json", value=json.dumps(cfg, indent=2), height=400)
    col1, col2 = st.columns([1, 1])
    with col1:
        if st.button("Save feeds.json"):
            try:
                new = json.loads(raw)
                save_feeds_config(new)
                st.success("Saved feeds.json")
            except Exception as e:
                st.error(f"Invalid JSON: {e}")
    with col2:
        if st.button("Reload"):
            st.experimental_rerun()


def render_ai_settings(cfg: dict):
    """Compact AI settings panel surfaced on the main dashboard for easy access."""
    st.markdown("---")
    # Render settings in the sidebar for persistent access
    with st.sidebar.expander("🤖 AI Model Settings (Quick Access)", expanded=True):
        ollama_cfg = cfg.get("ollama", {}) if isinstance(cfg, dict) else {}
        c_mode, c_host, c_port = st.columns([1, 2, 1])
        with c_mode:
            mode_idx = 0 if ollama_cfg.get("mode", "cli") == "cli" else 1
            mode = st.selectbox("Mode", ["cli", "http"], index=mode_idx)
        with c_host:
            host = st.text_input("Host", value=ollama_cfg.get("host", "http://localhost"), disabled=(mode == "cli"))
        with c_port:
            port = st.number_input("Port", value=int(ollama_cfg.get("port", 11434)), min_value=1, max_value=65535, disabled=(mode == "cli"))

        st.caption("Choose connection mode. Use 'cli' if running Ollama locally.")

        # Model discovery and quick actions
        if "ollama_models" not in st.session_state:
            st.session_state["ollama_models"] = []

        col_r, col_s = st.columns([1, 3])
        with col_r:
            if st.button("🔄 Refresh Models"):
                if mode == "cli":
                    st.session_state["ollama_models"] = list_models_cli()
                else:
                    st.session_state["ollama_models"] = list_models_http(host, port)

        with col_s:
            models = st.session_state.get("ollama_models", [])
            if models:
                try:
                    idx = models.index(ollama_cfg.get("model", ""))
                except ValueError:
                    idx = 0
                selected = st.selectbox("Model", models, index=idx)
            else:
                selected = st.text_input("Model Name", value=ollama_cfg.get("model", ""))

        if st.button("💾 Save AI Settings (Quick)"):
            cfg["ollama"] = {"mode": mode, "model": selected, "host": host, "port": int(port)}
            save_feeds_config(cfg)
            # update session state to reflect new selection immediately
            st.session_state["ollama_models"] = st.session_state.get("ollama_models", [])
            st.success("AI settings saved to feeds.json")

        st.caption("Tip: Use the Admin UI for advanced feed configuration and bulk edits.")


if __name__ == "__main__":
    main()
