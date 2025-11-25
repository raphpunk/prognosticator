"""Agent response caching and debate transcript storage using SQLite."""
import sqlite3
import json
from datetime import datetime
from typing import Dict, List, Optional
import hashlib


def init_agent_cache_db(db_path: str = "data/agent_cache.db") -> None:
    """Initialize agent response cache database."""
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    
    # Store agent analyses
    cur.execute("""
        CREATE TABLE IF NOT EXISTS agent_responses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            question_hash TEXT NOT NULL,
            agent_name TEXT NOT NULL,
            analysis TEXT,
            probability REAL,
            confidence REAL,
            recommendation TEXT,
            raw_response TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(question_hash, agent_name)
        )
    """)
    
    # Store debate transcripts (confirmations/denials by subsequent agents)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS debate_transcript (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            question_hash TEXT NOT NULL,
            round_number INTEGER,
            agent_name TEXT NOT NULL,
            statement_id INTEGER,
            position TEXT,  -- 'confirm', 'deny', 'neutral'
            evidence_sources TEXT,  -- JSON array of source URLs
            rationale TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (statement_id) REFERENCES agent_responses(id)
        )
    """)
    
    # Store synthesis history
    cur.execute("""
        CREATE TABLE IF NOT EXISTS synthesis_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            question_hash TEXT NOT NULL,
            question TEXT NOT NULL,
            verdict TEXT,
            probability REAL,
            confidence REAL,
            final_rationale TEXT,
            agents_used TEXT,  -- JSON array of agent names
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    conn.commit()
    conn.close()


def hash_question(question: str) -> str:
    """Create deterministic hash of question for caching."""
    return hashlib.md5(question.lower().strip().encode()).hexdigest()


def get_cached_response(question: str, agent_name: str, db_path: str = "data/agent_cache.db") -> Optional[Dict]:
    """Retrieve cached agent response if available."""
    q_hash = hash_question(question)
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    
    cur.execute("""
        SELECT analysis, probability, confidence, recommendation, raw_response 
        FROM agent_responses 
        WHERE question_hash = ? AND agent_name = ?
        LIMIT 1
    """, (q_hash, agent_name))
    
    row = cur.fetchone()
    conn.close()
    
    if row:
        return {
            "analysis": row[0],
            "probability": row[1],
            "confidence": row[2],
            "recommendation": row[3],
            "raw_response": row[4]
        }
    return None


def cache_response(
    question: str, 
    agent_name: str, 
    analysis: str,
    probability: Optional[float],
    confidence: Optional[float],
    recommendation: str,
    raw_response: str,
    db_path: str = "data/agent_cache.db"
) -> int:
    """Store agent response in cache. Returns response ID."""
    q_hash = hash_question(question)
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    
    try:
        cur.execute("""
            INSERT INTO agent_responses 
            (question_hash, agent_name, analysis, probability, confidence, recommendation, raw_response)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (q_hash, agent_name, analysis, probability, confidence, recommendation, raw_response))
        conn.commit()
        response_id = cur.lastrowid
        conn.close()
        return response_id if response_id is not None else 0
    except sqlite3.IntegrityError:
        # Already cached
        cur.execute(
            "SELECT id FROM agent_responses WHERE question_hash = ? AND agent_name = ?",
            (q_hash, agent_name)
        )
        result = cur.fetchone()
        response_id = result[0] if result else 0
        conn.close()
        return response_id


def record_debate_position(
    question: str,
    agent_name: str,
    position: str,  # 'confirm', 'deny', 'neutral'
    evidence_sources: List[str],
    rationale: str,
    previous_statement_id: int,
    round_number: int = 2,
    db_path: str = "data/agent_cache.db"
) -> None:
    """Record subsequent agent's confirmation/denial of previous agent's statement."""
    q_hash = hash_question(question)
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    
    cur.execute("""
        INSERT INTO debate_transcript 
        (question_hash, round_number, agent_name, statement_id, position, evidence_sources, rationale)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (
        q_hash,
        round_number,
        agent_name,
        previous_statement_id,
        position,
        json.dumps(evidence_sources),
        rationale
    ))
    
    conn.commit()
    conn.close()


def get_debate_transcript(question: str, db_path: str = "data/agent_cache.db") -> List[Dict]:
    """Retrieve full debate transcript for a question."""
    q_hash = hash_question(question)
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    
    cur.execute("""
        SELECT agent_name, position, evidence_sources, rationale, round_number
        FROM debate_transcript
        WHERE question_hash = ?
        ORDER BY round_number, id
    """, (q_hash,))
    
    rows = cur.fetchall()
    conn.close()
    
    transcript = []
    for row in rows:
        transcript.append({
            "agent": row[0],
            "position": row[1],
            "sources": json.loads(row[2]) if row[2] else [],
            "rationale": row[3],
            "round": row[4]
        })
    
    return transcript


def get_agent_history(agent_name: str, limit: int = 10, db_path: str = "data/agent_cache.db") -> List[Dict]:
    """Get cached responses for an agent across multiple questions."""
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    
    cur.execute("""
        SELECT analysis, probability, confidence, created_at
        FROM agent_responses
        WHERE agent_name = ?
        ORDER BY created_at DESC
        LIMIT ?
    """, (agent_name, limit))
    
    rows = cur.fetchall()
    conn.close()
    
    return [{
        "analysis": row[0],
        "probability": row[1],
        "confidence": row[2],
        "timestamp": row[3]
    } for row in rows]


def clear_cache(db_path: str = "data/agent_cache.db") -> None:
    """Clear all cached responses (useful for testing)."""
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    
    cur.execute("DELETE FROM debate_transcript")
    cur.execute("DELETE FROM agent_responses")
    cur.execute("DELETE FROM synthesis_history")
    
    conn.commit()
    conn.close()


__all__ = [
    "init_agent_cache_db",
    "hash_question",
    "get_cached_response",
    "cache_response",
    "record_debate_position",
    "get_debate_transcript",
    "get_agent_history",
    "clear_cache"
]
