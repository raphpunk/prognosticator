"""Agent orchestration utilities for multi-model conversations via Ollama."""
from __future__ import annotations

import json
import os
import shutil
import sqlite3
import subprocess
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import linear_kernel

from forecasting.agent_cache import (
    init_agent_cache_db,
    get_cached_response,
    cache_response,
    record_debate_position,
    hash_question
)
from forecasting.config import get_config, get_logger, get_domain_expertise
from forecasting.prediction_report import PredictionReportGenerator
from forecasting.domain_consensus import DomainClassifier
from forecasting.performance_tracker import PerformanceTracker
from forecasting.reputation import ReputationTracker
from forecasting.ollama_resilience import with_circuit_breaker, with_retry_and_timeout

def _load_json(path: str) -> Dict:
    if not os.path.exists(path):
        return {}
    try:
        with open(path, "r") as fh:
            return json.load(fh)
    except Exception:
        return {}


def load_ollama_config(config_path: str = "feeds.json") -> Dict:
    data = _load_json(config_path)
    return data.get("ollama", {})


def load_agent_profiles(config_path: str = "feeds.json") -> List[Dict]:
    data = _load_json(config_path)
    
    # New format: models array with system prompts and weights
    ollama_cfg = data.get("ollama", {})
    models_list = ollama_cfg.get("models", [])
    
    if models_list and len(models_list) > 1:
        # Convert models with system prompts to agent profiles
        agents = []
        for model_cfg in models_list:
            agents.append({
                "name": model_cfg.get("name", "Model Agent"),
                "role": model_cfg.get("system_prompt", "You are a helpful assistant."),
                "model": model_cfg.get("model", "llama2"),
                "weight": model_cfg.get("weight", 1.0),
            })
        return agents
    
    # Built-in forecasting expert corps with lightweight models
    # Specialized domain experts for event prediction and analysis
    return [
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
            "model": "deepseek-r1:1.3b",
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
            "model": "tinytimemixer",
            "weight": 1.0,
        },
        {
            "name": "🎖️ Military Strategy Expert",
            "role": "You are a military strategist and conflict analyst. Assess military capabilities, force posture, and strategic intentions. Focus on: weapons systems, doctrine, force deployment, naval/air operations, and escalation dynamics. Provide tactical and strategic insights.",
            "model": "qwen2.5:0.5b",
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
            "model": "qwen2.5:0.5b",
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
            "model": "qwen2.5:0.5b",
            "weight": 1.0,
        },
        {
            "name": "🚨 Local Threat Analyst",
            "role": "You are a local law enforcement and emergency response analyst. Monitor police dispatch feeds, emergency calls, and incident patterns in Virginia jurisdictions (Richmond, Chesterfield, Henrico, Colonial Heights). Focus on: incident severity escalation, coordinated criminal activity, threat pattern spread across jurisdictions, officer safety indicators, and civil emergency signals. Cross-reference local threats with geopolitical and societal indicators to detect early warning signs of broader instability (protests → riots, isolated incidents → coordinated attacks). Weight local signals 3x for location-specific predictions.",
            "model": "gemma:2b",
            "weight": 3.0,
        },
    ]


def load_articles(db_path: str = "data/live.db", limit: int = 500, days: Optional[int] = 7) -> List[Dict]:
    if not os.path.exists(db_path):
        return []
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    query = "SELECT id, title, text, source_url, published FROM articles"
    params: List = []
    if days is not None:
        cutoff = (datetime.utcnow() - timedelta(days=days)).isoformat()
        query += " WHERE published >= ?"
        params.append(cutoff)
    query += " ORDER BY published DESC LIMIT ?"
    params.append(limit)
    cur.execute(query, params)
    rows = cur.fetchall()
    conn.close()
    articles = []
    for r in rows:
        aid, title, text, source_url, published = r
        full_text = "\n".join([t for t in [title or "", text or ""] if t])
        articles.append(
            {
                "id": aid,
                "title": title,
                "text": full_text,
                "source_url": source_url,
                "published": published,
            }
        )
    return articles


def build_context(question: str, articles: List[Dict], topk: int = 5) -> Tuple[str, List[Dict]]:
    """Build context from articles using TF-IDF vectorization with optimizations."""
    if not articles:
        return "No articles available.", []
    
    texts = [a["text"] for a in articles]
    
    # Optimize TF-IDF: limit to most recent articles to speed up vectorization
    if len(texts) > 200:
        texts = texts[:200]
        articles = articles[:200]
    
    try:
        # Use faster TF-IDF parameters with optimizations
        vec = TfidfVectorizer(
            max_features=5000,
            stop_words="english",
            min_df=1,
            max_df=0.95,
            ngram_range=(1, 2),
            dtype='float32',
            lowercase=True,
            strip_accents='ascii'
        )
        X = vec.fit_transform(texts)
        qv = vec.transform([question])
        sims = linear_kernel(qv, X).flatten()
    except Exception as e:
        # Fallback: simple keyword matching if TF-IDF fails
        logger = get_logger()
        logger.warning(f"TF-IDF failed: {e}, using keyword fallback")
        sims = []
        q_words = set(question.lower().split())
        for text in texts:
            t_words = set(text.lower().split())
            overlap = len(q_words & t_words)
            sims.append(float(overlap) / max(len(q_words), len(t_words), 1))
        sims = __import__('numpy').array(sims)
    
    idxs = sims.argsort()[::-1][:topk]
    top = []
    for idx in idxs:
        art = articles[idx]
        snippet = art["text"].replace("\n", " ")[:600]
        top.append({"title": art["title"], "snippet": snippet, "source_url": art["source_url"], "score": float(sims[idx])})
    context = "\n---\n".join(
        [
            f"[{i+1}] {item['title'] or '[no title]'} (score={item['score']:.3f})\n{item['snippet']}\nSource: {item['source_url']}"
            for i, item in enumerate(top)
        ]
    )
    return context, top


def _call_ollama_cli(model: str, prompt: str) -> str:
    if not shutil.which("ollama"):
        raise RuntimeError("`ollama` CLI not found in PATH")
    proc = subprocess.run(["ollama", "run", model], input=prompt, text=True, capture_output=True, check=False)
    if proc.returncode != 0:
        raise RuntimeError(proc.stderr.strip() or "ollama CLI failed")
    return proc.stdout


@with_circuit_breaker
@with_retry_and_timeout(timeout=30, max_attempts=3)
def _call_ollama_http(model: str, prompt: str, host: str, port: int, api_key: Optional[str], timeout: Optional[int] = None) -> str:
    """Call Ollama HTTP API with security and error handling."""
    import requests
    
    # Use config timeout if not provided (decorators will override with their timeout)
    if timeout is None:
        timeout = 30  # Default to 30 seconds

    url = f"{host.rstrip('/')}:{port}/api/generate"
    headers = {"Content-Type": "application/json"}
    
    # Add API key if configured
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"
    
    # Validate model name to prevent injection
    if not model or not model.strip():
        raise RuntimeError("Model name cannot be empty")
    
    payload = {
        "model": model.strip(),
        "prompt": prompt,
        "stream": False
    }
    
    try:
        resp = requests.post(url, json=payload, headers=headers, timeout=timeout)
        
        # Validate response status
        if resp.status_code != 200:
            raise RuntimeError(f"HTTP {resp.status_code}: {resp.text[:200]}")
        
        # Parse and validate response
        try:
            data = resp.json()
            if isinstance(data, dict) and "response" in data:
                return data["response"]
            return json.dumps(data)
        except json.JSONDecodeError:
            return resp.text
            
    except requests.exceptions.Timeout:
        raise RuntimeError(f"Model timeout after {timeout}s. Ollama may be overloaded or model not loaded.")
    except requests.exceptions.ConnectionError:
        raise RuntimeError(f"Cannot reach Ollama at {host}:{port}")
    except requests.exceptions.RequestException as e:
        raise RuntimeError(f"Request failed: {str(e)[:100]}")
    except Exception as e:
        raise RuntimeError(f"Model error: {str(e)[:100]}")


def call_model(prompt: str, model: str, cfg: Dict) -> str:
    mode = cfg.get("mode", "http")
    host = cfg.get("host", "http://localhost")
    port = int(cfg.get("port", 11434))
    result = _call_ollama_http(model or cfg.get("model", model), prompt, host, port, cfg.get("api_key"))
    
    # Handle circuit breaker response
    if isinstance(result, dict):
        if result.get("status") == "degraded":
            raise RuntimeError(f"Service degraded: {result.get('error')}")
        return result.get("response", "")
    
    return result


AGENT_PROMPT = (
    "You are {name}, {role}. You are given curated context snippets and a mission question.\n"
    "Use ONLY the provided context. If you have meaningful insights, respond in JSON with keys: "
    "analysis (string), probability (0-1 float), confidence (0-1 float), recommendation (string).\n"
    "If the topic is outside your domain expertise or context provides insufficient relevant information for your specialty, "
    "you may DECLINE by responding with JSON: {{\"declined\": true, \"reason\": \"brief explanation\"}}.\n"
    "Context:\n{context}\n\nQuestion: {question}\n"
)

DEBATE_PROMPT = (
    "You are {name}, {role}. Review the following statement from another analyst:\n\n"
    "PREVIOUS STATEMENT:\n{previous_analysis}\n\n"
    "Does this statement hold up under scrutiny given the evidence provided? "
    "Use the context to CONFIRM (supported by sources), DENY (contradicted by sources), or remain NEUTRAL.\n"
    "Respond in JSON with keys: position ('confirm'|'deny'|'neutral'), evidence_sources (list of URLs supporting your position), rationale (string).\n"
    "Context:\n{context}\n\nQuestion: {question}\n"
)

SUMMARIZER_PROMPT = (
    "You are the lead forecaster. Review the question, the shared context, and each agent's JSON brief."
    "Combine them into a single JSON with keys: verdict (string), probability (0-1 float), confidence (0-1 float), rationale (string)"
    " and include `votes` as an array of {{agent, probability, confidence}} summarizing each brief."
    "\nContext:\n{context}\n\nAgent Briefs:\n{briefs}\n\nQuestion: {question}\n"
)


def _extract_json_block(text: str) -> Optional[Dict]:
    if not text:
        return None
    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end == -1 or end <= start:
        return None
    snippet = text[start : end + 1]
    try:
        return json.loads(snippet)
    except json.JSONDecodeError:
        return None


def run_conversation(
    question: str,
    db_path: str = "data/live.db",
    config_path: str = "feeds.json",
    topk: Optional[int] = None,
    days: int = 7,
    enabled_agents: Optional[List[str]] = None,
) -> Dict:
    """Run multi-agent orchestrated conversation with parallel expert execution.
    
    Args:
        question: The analysis question
        db_path: Path to articles database
        config_path: Path to feeds.json configuration
        topk: Number of top articles to retrieve (uses config.context_topk if None)
        days: Number of days of articles to consider
        
    Returns:
        Dictionary with orchestrator plan, agent analyses, and synthesis
    """
    cfg = get_config()
    logger = get_logger()
    
    # Input validation
    if not question or not question.strip():
        return {
            "question": "",
            "error": "Question cannot be empty",
            "summary": {"verdict": "Invalid input", "probability": None, "confidence": None}
        }
    
    # Sanitize question: limit length to prevent abuse
    question = question.strip()[:2000]
    
    # Use config defaults if not provided
    if topk is None:
        topk = cfg.context_topk
    
    max_articles = cfg.max_articles
    db_path = db_path or cfg.database.live_db
    
    logger.info(f"Running conversation for question: {question[:60]}...")
    
    # Phase 1: Orchestrator gathers ALL relevant articles
    articles = load_articles(db_path=db_path, limit=max_articles, days=days)
    logger.info(f"Loaded {len(articles)} articles from database")
    
    # Retrieve comprehensive context
    orchestrator_topk = max(topk * 3, 15)
    context, context_items = build_context(question, articles, topk=orchestrator_topk)
    logger.info(f"Built context with {len(context_items)} relevant articles")
    
    ollama_cfg = load_ollama_config(config_path)
    agents = load_agent_profiles(config_path)
    logger.info(f"Loaded {len(agents)} agent profiles")

    # Apply user-selected filters if provided
    if enabled_agents is not None:
        enabled_set = {name.strip() for name in enabled_agents if name}
        if enabled_set:
            original_count = len(agents)
            agents = [agent for agent in agents if agent.get("name") in enabled_set]
            logger.info(
                "Filtered agents based on user selection: %s -> %s",
                original_count,
                len(agents),
            )
    
    if not agents:
        logger.warning("No agents configured")
        return {
            "question": question,
            "context": context,
            "context_items": context_items,
            "agents": [],
            "summary": {"verdict": "No agents configured", "probability": None, "confidence": None},
        }

    # Prevent single-agent execution - need minimum 2 for orchestration
    if len(agents) < 2:
        logger.error(f"Insufficient agents: {len(agents)} < 2")
        return {
            "question": question,
            "context": context,
            "context_items": context_items,
            "agents": [],
            "summary": {
                "verdict": "⚠️ Orchestration Blocked",
                "probability": None,
                "confidence": None,
                "rationale": f"Multi-agent orchestration requires at least 2 agents. Currently configured: {len(agents)}. Add more model configurations to enable analysis.",
                "error": "Insufficient agents for meaningful multi-perspective analysis"
            },
        }

    # Build orchestrator plan from the comprehensive context gathered
    avg_relevance = sum(c.get('score', 0) for c in context_items) / max(len(context_items), 1)
    orchestrator_plan = {
        "priority_areas": list(set([item['title'][:50] for item in context_items[:5]])) if context_items else [],
        "research_focus": question,
        "context_quality": avg_relevance,
        "articles_gathered": len(context_items)  # Show how many articles orchestrator gathered
    }
    
    logger.info(f"Orchestrator gathered {len(context_items)} articles with quality {avg_relevance:.2f}")

    # Phase 3: Parallel expert analysis - run all agents concurrently with full context
    # Initialize agent cache
    init_agent_cache_db(cfg.database.cache_db)
    
    agent_outputs = []
    total_weight = 0
    weighted_probability = 0
    weighted_confidence = 0

    def call_agent(agent: Dict, use_cache: bool = True) -> Dict:
        """Call a single agent and return structured response with caching.
        
        Agents may decline if the topic is outside their expertise or context is insufficient.
        """
        agent_name = agent["name"]
        
        # Check cache first if enabled
        if use_cache and cfg.cache_responses:
            cached = get_cached_response(question, agent_name, cfg.database.cache_db)
            if cached:
                logger.debug(f"Cache hit for agent: {agent_name}")
                # Check if cached response was a decline
                if cached.get("analysis") == "DECLINED":
                    return {
                        "agent": agent_name,
                        "raw": cached["raw_response"],
                        "parsed": {"declined": True, "reason": cached.get("recommendation", "")},
                        "weight": agent.get("weight", 1.0),
                        "cached": True,
                        "declined": True
                    }
                return {
                    "agent": agent_name,
                    "raw": cached["raw_response"],
                    "parsed": {
                        "analysis": cached["analysis"],
                        "probability": cached["probability"],
                        "confidence": cached["confidence"],
                        "recommendation": cached["recommendation"]
                    },
                    "weight": agent.get("weight", 1.0),
                    "cached": True,
                    "declined": False
                }
        
        # Call model if not cached
        prompt = AGENT_PROMPT.format(
            name=agent_name,
            role=agent["role"],
            context=context,
            question=question
        )
        try:
            logger.debug(f"Calling agent: {agent_name}")
            raw = call_model(prompt, agent.get("model"), ollama_cfg)
            parsed = _extract_json_block(raw)
            
            # Check if agent declined
            declined = False
            if parsed and isinstance(parsed, dict) and parsed.get("declined"):
                declined = True
                logger.info(f"Agent {agent_name} declined: {parsed.get('reason', 'No reason provided')}")
                # Cache the decline
                if cfg.cache_responses:
                    cache_response(
                        question, agent_name,
                        "DECLINED",
                        None,
                        None,
                        parsed.get("reason", ""),
                        raw,
                        cfg.database.cache_db
                    )
                logger.debug(f"Cached decline for agent: {agent_name}")
            else:
                # Cache the regular response if enabled
                if parsed and isinstance(parsed, dict) and cfg.cache_responses:
                    cache_response(
                        question, agent_name,
                        parsed.get("analysis", ""),
                        parsed.get("probability"),
                        parsed.get("confidence"),
                        parsed.get("recommendation", ""),
                        raw,
                        cfg.database.cache_db
                    )
                    logger.debug(f"Cached response for agent: {agent_name}")
        except Exception as exc:
            logger.error(f"Agent {agent_name} failed: {exc}")
            raw = f"ERROR: {str(exc)[:200]}"
            parsed = None
            declined = False
        
        return {
            "agent": agent_name,
            "raw": raw,
            "parsed": parsed,
            "weight": agent.get("weight", 1.0),
            "cached": False,
            "declined": declined
        }

    # Round 1: All agents provide initial analyses (with caching)
    max_workers = min(len(agents), cfg.ollama.max_workers)
    logger.info(f"Starting parallel agent execution with {max_workers} workers")
    
    declined_agents = []
    participating_agents = []
    
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {executor.submit(call_agent, agent, use_cache=cfg.cache_responses): agent for agent in agents}
        for future in as_completed(futures):
            try:
                result = future.result(timeout=cfg.ollama.timeout + 10)
                agent_name = result.get('agent')
                
                # Track declines separately
                if result.get("declined"):
                    declined_agents.append(result)
                    logger.info(f"Agent {agent_name} declined participation")
                else:
                    agent_outputs.append(result)
                    participating_agents.append(agent_name)
                    logger.info(f"Agent {agent_name} completed (cached: {result.get('cached', False)})")
                    
                    # Aggregate weighted metrics only for participating agents
                    weight = result.get("weight", 1.0)
                    total_weight += weight
                    if result.get("parsed") and isinstance(result["parsed"], dict):
                        prob = result["parsed"].get("probability")
                        conf = result["parsed"].get("confidence")
                        if isinstance(prob, (int, float)):
                            weighted_probability += prob * weight
                        if isinstance(conf, (int, float)):
                            weighted_confidence += conf * weight
            except Exception as e:
                logger.error(f"Agent execution failed: {e}")
                agent_outputs.append({"agent": "Unknown", "raw": f"ERROR: {str(e)[:100]}", "parsed": None, "weight": 1.0, "declined": False})

    # Normalize weighted metrics
    if total_weight > 0:
        weighted_probability = weighted_probability / total_weight
        weighted_confidence = weighted_confidence / total_weight

    # Phase 4: Synthesize expert opinions
    briefs_text = json.dumps(
        {item["agent"]: item.get("parsed") or item.get("raw") for item in agent_outputs},
        indent=2
    )
    summary = None
    try:
        summary_prompt = SUMMARIZER_PROMPT.format(
            context=context,
            briefs=briefs_text,
            question=question
        )
        summarizer_model = agents[0].get("model") if agents else "llama2"
        raw_summary = call_model(summary_prompt, summarizer_model, ollama_cfg)
        summary = _extract_json_block(raw_summary)
        
        if summary is None:
            summary = {
                "verdict": raw_summary[:500],
                "probability": weighted_probability,
                "confidence": weighted_confidence,
                "rationale": "Model response processed (not JSON)"
            }
        else:
            if "probability" not in summary or summary.get("probability") is None:
                summary["probability"] = weighted_probability
            if "confidence" not in summary or summary.get("confidence") is None:
                summary["confidence"] = weighted_confidence
    except Exception as exc:
        logger.error(f"Synthesis failed: {exc}")
        summary = {
            "verdict": f"Synthesis complete with {len(agent_outputs)} expert inputs",
            "error": str(exc)[:100],
            "probability": weighted_probability,
            "confidence": weighted_confidence,
        }

    logger.info(f"Conversation complete. Participating agents: {len(agent_outputs)}, Declined: {len(declined_agents)}, Final probability: {weighted_probability:.2f}, Confidence: {weighted_confidence:.2f}")
    
    # Calculate reputation-weighted consensus
    reputation_tracker = ReputationTracker()
    reputation_consensus = None
    try:
        # Classify domain for reputation weighting
        classifier = DomainClassifier()
        domain_classification = classifier.classify(question)
        
        # Prepare agent predictions for reputation-weighted consensus
        agent_predictions = []
        for agent_output in agent_outputs:
            if not agent_output.get("declined"):
                parsed = agent_output.get("parsed", {})
                if isinstance(parsed, dict):
                    agent_name = agent_output.get("agent", "Unknown")
                    
                    # Get domain expertise multiplier
                    domain_expertise = get_domain_expertise(agent_name, domain_classification.primary_domain)
                    
                    agent_predictions.append({
                        "agent_name": agent_name,
                        "prediction": parsed.get("analysis", ""),
                        "probability": parsed.get("probability", 0.5),
                        "confidence": parsed.get("confidence", 0.5),
                        "weight": agent_output.get("weight", 1.0) * domain_expertise
                    })
        
        # Get reputation-weighted consensus
        reputation_consensus = reputation_tracker.get_weighted_consensus(
            agent_predictions,
            domain=domain_classification.primary_domain,
            use_reputation=True
        )
        
        # Update weighted values with reputation-based consensus
        if reputation_consensus:
            weighted_probability = reputation_consensus["consensus_probability"]
            weighted_confidence = reputation_consensus["consensus_confidence"]
            
            logger.info(f"Reputation-weighted consensus: probability={weighted_probability:.2f}, "
                       f"confidence={weighted_confidence:.2f}, "
                       f"dissent={reputation_consensus.get('dissent_percentage', 0):.1%}, "
                       f"requires_review={reputation_consensus.get('requires_review', False)}")
        
        # Record predictions for future reputation tracking
        import hashlib
        prediction_id = f"{hashlib.sha256(question.encode()).hexdigest()[:16]}_{datetime.utcnow().isoformat()}"
        for pred in agent_predictions:
            reputation_tracker.record_prediction(
                prediction_id=f"{prediction_id}_{pred['agent_name']}",
                agent_name=pred["agent_name"],
                domain=domain_classification.primary_domain,
                prediction_text=pred["prediction"],
                confidence=pred["confidence"]
            )
        
    except Exception as e:
        logger.error(f"Reputation-weighted consensus failed: {e}")
        # Continue with simple weighted average
    
    # Generate and save comprehensive prediction report
    report = None
    try:
        report_generator = PredictionReportGenerator()
        
        if 'domain_classification' not in locals():
            classifier = DomainClassifier()
            domain_classification = classifier.classify(question)
        
        domain_dict = {
            "primary_domain": domain_classification.primary_domain,
            "confidence": domain_classification.confidence,
            "secondary_domains": domain_classification.secondary_domains
        }
        
        # Prepare agent responses for report
        agent_responses_for_report = []
        for agent_output in agent_outputs:
            agent_responses_for_report.append({
                "agent_name": agent_output.get("agent", "Unknown"),
                "response": agent_output.get("raw", ""),
                "confidence": agent_output.get("parsed", {}).get("confidence", 0.5) if isinstance(agent_output.get("parsed"), dict) else 0.5,
                "base_weight": agent_output.get("weight", 1.0),
                "relevance_boost": 1.0,  # TODO: Calculate from domain analysis
                "performance_boost": 1.0,  # TODO: Get from PerformanceTracker
                "adjusted_weight": agent_output.get("weight", 1.0),
                "execution_time_ms": 0,  # TODO: Track execution time
                "model": agent_output.get("model", "unknown"),
                "cached": agent_output.get("cached", False)
            })
        
        # Consensus result
        consensus_result = {
            "strength": weighted_confidence,
            "total_weight": total_weight
        }
        
        # Execution metrics
        execution_metrics = {
            "total_time_ms": 0,  # TODO: Track total execution time
            "succeeded": len(agent_outputs),
            "failed": len(declined_agents),
            "cache_hits": sum(1 for a in agent_outputs if a.get("cached", False)),
            "circuit_breaker_trips": 0  # TODO: Track circuit breaker trips
        }
        
        report = report_generator.generate_report(
            question=question,
            domain_classification=domain_dict,
            agent_responses=agent_responses_for_report,
            consensus_result=consensus_result,
            execution_metrics=execution_metrics
        )
        
        logger.info(f"Generated prediction report: {report.metadata.prediction_id}")
        
        # Record prediction in performance tracker
        tracker = PerformanceTracker()
        tracker.record_prediction(
            prediction_id=report.metadata.prediction_id,
            question=question,
            question_hash=report.metadata.question_hash,
            domain=domain_classification.primary_domain,
            agent_responses=agent_responses_for_report
        )
        
    except Exception as e:
        logger.error(f"Failed to generate prediction report: {e}")
    
    return {
        "question": question,
        "context": context,
        "context_items": context_items,
        "agents": agent_outputs,
        "declined_agents": declined_agents,
        "summary": summary,
        "orchestrator_plan": orchestrator_plan,
        "report": report.to_dict() if report else None,
        "prediction_id": report.metadata.prediction_id if report else None,
        "reputation_consensus": reputation_consensus,
        "requires_review": reputation_consensus.get("requires_review", False) if reputation_consensus else False,
    }


__all__ = [
    "run_conversation",
    "load_agent_profiles",
    "load_ollama_config",
]
