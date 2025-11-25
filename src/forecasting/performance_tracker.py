"""Agent performance tracking and historical accuracy scoring."""
import sqlite3
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum


class PredictionOutcome(Enum):
    """Outcome classification for predictions."""
    PENDING = "pending"
    CORRECT = "correct"
    INCORRECT = "incorrect"
    PARTIALLY_CORRECT = "partially_correct"
    UNVERIFIABLE = "unverifiable"


@dataclass
class AgentPrediction:
    """Individual agent prediction record."""
    agent_name: str
    question: str
    response: str
    confidence: float
    timestamp: datetime
    domain: str
    prediction_id: str


@dataclass
class AgentMetrics:
    """Performance metrics for an agent."""
    agent_name: str
    total_predictions: int
    correct: int
    incorrect: int
    partially_correct: int
    accuracy: float
    domain_accuracy: Dict[str, float]
    confidence_calibration: float
    recent_performance: float  # Last 30 days


class PerformanceTracker:
    """Track and score agent prediction accuracy over time."""
    
    def __init__(self, db_path: str = "data/agent_performance.db"):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_database()
    
    def _init_database(self) -> None:
        """Initialize performance tracking tables."""
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()
        
        # Predictions table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS predictions (
                prediction_id TEXT PRIMARY KEY,
                question TEXT NOT NULL,
                question_hash TEXT NOT NULL,
                domain TEXT,
                timestamp TEXT NOT NULL,
                consensus_result TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Agent responses table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS agent_responses (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                prediction_id TEXT NOT NULL,
                agent_name TEXT NOT NULL,
                response TEXT NOT NULL,
                confidence REAL DEFAULT 0.5,
                weight_used REAL DEFAULT 1.0,
                execution_time_ms INTEGER,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (prediction_id) REFERENCES predictions(prediction_id)
            )
        """)
        
        # Prediction outcomes table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS prediction_outcomes (
                prediction_id TEXT PRIMARY KEY,
                outcome TEXT NOT NULL,
                actual_result TEXT,
                verification_date TEXT NOT NULL,
                verification_source TEXT,
                notes TEXT,
                FOREIGN KEY (prediction_id) REFERENCES predictions(prediction_id)
            )
        """)
        
        # Agent performance cache
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS agent_metrics_cache (
                agent_name TEXT PRIMARY KEY,
                total_predictions INTEGER DEFAULT 0,
                correct INTEGER DEFAULT 0,
                incorrect INTEGER DEFAULT 0,
                partially_correct INTEGER DEFAULT 0,
                accuracy REAL DEFAULT 0.0,
                domain_accuracy TEXT,
                last_updated TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Create indexes
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_agent_responses_agent ON agent_responses(agent_name)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_agent_responses_prediction ON agent_responses(prediction_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_predictions_domain ON predictions(domain)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_predictions_timestamp ON predictions(timestamp)")
        
        conn.commit()
        conn.close()
    
    def record_prediction(
        self,
        prediction_id: str,
        question: str,
        question_hash: str,
        domain: Optional[str] = None,
        agent_responses: Optional[List[Dict]] = None
    ) -> None:
        """Record a new prediction and agent responses."""
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()
        
        # Insert prediction
        cursor.execute("""
            INSERT OR REPLACE INTO predictions 
            (prediction_id, question, question_hash, domain, timestamp)
            VALUES (?, ?, ?, ?, ?)
        """, (prediction_id, question, question_hash, domain or "general", datetime.utcnow().isoformat()))
        
        # Insert agent responses
        if agent_responses:
            for resp in agent_responses:
                cursor.execute("""
                    INSERT INTO agent_responses 
                    (prediction_id, agent_name, response, confidence, weight_used, execution_time_ms)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (
                    prediction_id,
                    resp.get("agent_name"),
                    resp.get("response", ""),
                    resp.get("confidence", 0.5),
                    resp.get("weight", 1.0),
                    resp.get("execution_time_ms", 0)
                ))
        
        conn.commit()
        conn.close()
    
    def record_outcome(
        self,
        prediction_id: str,
        outcome: PredictionOutcome,
        actual_result: Optional[str] = None,
        verification_source: Optional[str] = None,
        notes: Optional[str] = None
    ) -> None:
        """Record the actual outcome of a prediction."""
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT OR REPLACE INTO prediction_outcomes
            (prediction_id, outcome, actual_result, verification_date, verification_source, notes)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            prediction_id,
            outcome.value,
            actual_result,
            datetime.utcnow().isoformat(),
            verification_source,
            notes
        ))
        
        conn.commit()
        conn.close()
        
        # Update agent metrics cache
        self._update_agent_metrics(prediction_id, outcome)
    
    def _update_agent_metrics(self, prediction_id: str, outcome: PredictionOutcome) -> None:
        """Update cached metrics for agents involved in a prediction."""
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()
        
        # Get agents involved
        cursor.execute("""
            SELECT DISTINCT agent_name FROM agent_responses
            WHERE prediction_id = ?
        """, (prediction_id,))
        
        agents = [row[0] for row in cursor.fetchall()]
        
        for agent_name in agents:
            # Recalculate metrics for this agent
            metrics = self._calculate_agent_metrics(agent_name, cursor)
            
            # Update cache
            cursor.execute("""
                INSERT OR REPLACE INTO agent_metrics_cache
                (agent_name, total_predictions, correct, incorrect, partially_correct, accuracy, domain_accuracy, last_updated)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                agent_name,
                metrics.total_predictions,
                metrics.correct,
                metrics.incorrect,
                metrics.partially_correct,
                metrics.accuracy,
                json.dumps(metrics.domain_accuracy),
                datetime.utcnow().isoformat()
            ))
        
        conn.commit()
        conn.close()
    
    def _calculate_agent_metrics(self, agent_name: str, cursor: sqlite3.Cursor) -> AgentMetrics:
        """Calculate comprehensive metrics for an agent."""
        # Get all predictions with outcomes
        cursor.execute("""
            SELECT 
                p.domain,
                po.outcome,
                ar.confidence
            FROM agent_responses ar
            JOIN predictions p ON ar.prediction_id = p.prediction_id
            LEFT JOIN prediction_outcomes po ON ar.prediction_id = po.prediction_id
            WHERE ar.agent_name = ? AND po.outcome IS NOT NULL
        """, (agent_name,))
        
        rows = cursor.fetchall()
        
        if not rows:
            return AgentMetrics(
                agent_name=agent_name,
                total_predictions=0,
                correct=0,
                incorrect=0,
                partially_correct=0,
                accuracy=0.0,
                domain_accuracy={},
                confidence_calibration=0.0,
                recent_performance=0.0
            )
        
        total = len(rows)
        correct = sum(1 for r in rows if r[1] == PredictionOutcome.CORRECT.value)
        incorrect = sum(1 for r in rows if r[1] == PredictionOutcome.INCORRECT.value)
        partial = sum(1 for r in rows if r[1] == PredictionOutcome.PARTIALLY_CORRECT.value)
        
        # Calculate domain-specific accuracy
        domain_stats = {}
        for row in rows:
            domain = row[0] or "general"
            outcome = row[1]
            
            if domain not in domain_stats:
                domain_stats[domain] = {"total": 0, "correct": 0}
            
            domain_stats[domain]["total"] += 1
            if outcome == PredictionOutcome.CORRECT.value:
                domain_stats[domain]["correct"] += 1
        
        domain_accuracy = {
            domain: stats["correct"] / stats["total"]
            for domain, stats in domain_stats.items()
        }
        
        accuracy = correct / total if total > 0 else 0.0
        
        # Calculate recent performance (last 30 days)
        cursor.execute("""
            SELECT COUNT(*) as total, 
                   SUM(CASE WHEN po.outcome = 'correct' THEN 1 ELSE 0 END) as correct
            FROM agent_responses ar
            JOIN predictions p ON ar.prediction_id = p.prediction_id
            LEFT JOIN prediction_outcomes po ON ar.prediction_id = po.prediction_id
            WHERE ar.agent_name = ? 
              AND po.outcome IS NOT NULL
              AND p.timestamp >= datetime('now', '-30 days')
        """, (agent_name,))
        
        recent = cursor.fetchone()
        recent_performance = recent[1] / recent[0] if recent and recent[0] > 0 else accuracy
        
        return AgentMetrics(
            agent_name=agent_name,
            total_predictions=total,
            correct=correct,
            incorrect=incorrect,
            partially_correct=partial,
            accuracy=accuracy,
            domain_accuracy=domain_accuracy,
            confidence_calibration=0.0,  # TODO: Implement Brier score
            recent_performance=recent_performance
        )
    
    def get_agent_metrics(self, agent_name: str) -> AgentMetrics:
        """Get current metrics for an agent."""
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()
        
        # Try cache first
        cursor.execute("""
            SELECT total_predictions, correct, incorrect, partially_correct, accuracy, domain_accuracy
            FROM agent_metrics_cache
            WHERE agent_name = ?
        """, (agent_name,))
        
        row = cursor.fetchone()
        
        if row:
            metrics = AgentMetrics(
                agent_name=agent_name,
                total_predictions=row[0],
                correct=row[1],
                incorrect=row[2],
                partially_correct=row[3],
                accuracy=row[4],
                domain_accuracy=json.loads(row[5]) if row[5] else {},
                confidence_calibration=0.0,
                recent_performance=row[4]  # Use overall accuracy as fallback
            )
        else:
            # Calculate fresh
            metrics = self._calculate_agent_metrics(agent_name, cursor)
        
        conn.close()
        return metrics
    
    def get_all_agent_rankings(self) -> List[Tuple[str, float, int]]:
        """Get ranked list of agents by accuracy."""
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT agent_name, accuracy, total_predictions
            FROM agent_metrics_cache
            ORDER BY accuracy DESC, total_predictions DESC
        """)
        
        rankings = cursor.fetchall()
        conn.close()
        
        return rankings
    
    def get_domain_specialists(self, domain: str, top_n: int = 5) -> List[Tuple[str, float]]:
        """Get top N agents for a specific domain."""
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT ar.agent_name, 
                   COUNT(*) as total,
                   SUM(CASE WHEN po.outcome = 'correct' THEN 1 ELSE 0 END) as correct
            FROM agent_responses ar
            JOIN predictions p ON ar.prediction_id = p.prediction_id
            LEFT JOIN prediction_outcomes po ON ar.prediction_id = po.prediction_id
            WHERE p.domain = ? AND po.outcome IS NOT NULL
            GROUP BY ar.agent_name
            HAVING total >= 3
            ORDER BY (correct * 1.0 / total) DESC
            LIMIT ?
        """, (domain, top_n))
        
        specialists = [(row[0], row[2] / row[1]) for row in cursor.fetchall()]
        conn.close()
        
        return specialists
    
    def get_prediction_history(self, limit: int = 100) -> List[Dict]:
        """Get recent prediction history with outcomes."""
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT 
                p.prediction_id,
                p.question,
                p.domain,
                p.timestamp,
                po.outcome,
                po.actual_result,
                COUNT(ar.id) as num_agents
            FROM predictions p
            LEFT JOIN prediction_outcomes po ON p.prediction_id = po.prediction_id
            LEFT JOIN agent_responses ar ON p.prediction_id = ar.prediction_id
            GROUP BY p.prediction_id
            ORDER BY p.timestamp DESC
            LIMIT ?
        """, (limit,))
        
        history = []
        for row in cursor.fetchall():
            history.append({
                "prediction_id": row[0],
                "question": row[1],
                "domain": row[2],
                "timestamp": row[3],
                "outcome": row[4],
                "actual_result": row[5],
                "num_agents": row[6]
            })
        
        conn.close()
        return history
