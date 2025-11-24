"""Agent reputation and historical performance tracking system."""
import sqlite3
import json
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime, timedelta
from collections import defaultdict


@dataclass
class AgentReputation:
    """Reputation metrics for an agent."""
    agent_name: str
    overall_score: float  # 0-1
    domain_scores: Dict[str, float]  # domain -> score mapping
    total_predictions: int
    correct_predictions: int
    recent_accuracy: float  # Last 30 days
    confidence_calibration: float  # How well confidence matches outcomes


class ReputationTracker:
    """Track agent performance and calculate reputation scores."""
    
    def __init__(self, db_path: str = "data/agent_reputation.db"):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_database()
    
    def _init_database(self) -> None:
        """Initialize reputation tracking tables."""
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()
        
        # Predictions with outcomes
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS predictions (
                id TEXT PRIMARY KEY,
                timestamp TEXT NOT NULL,
                agent_name TEXT NOT NULL,
                domain TEXT NOT NULL,
                prediction_text TEXT NOT NULL,
                confidence REAL NOT NULL,
                outcome TEXT,
                accuracy_score REAL,
                verification_date TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Cached reputation scores
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS reputation_cache (
                agent_name TEXT NOT NULL,
                domain TEXT NOT NULL,
                reputation_score REAL NOT NULL,
                sample_size INTEGER NOT NULL,
                last_updated TEXT NOT NULL,
                PRIMARY KEY (agent_name, domain)
            )
        """)
        
        # Create indexes
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_predictions_agent ON predictions(agent_name)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_predictions_domain ON predictions(domain)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_predictions_timestamp ON predictions(timestamp)")
        
        conn.commit()
        conn.close()
    
    def record_prediction(
        self,
        prediction_id: str,
        agent_name: str,
        domain: str,
        prediction_text: str,
        confidence: float
    ) -> None:
        """Record a new prediction from an agent."""
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO predictions (id, timestamp, agent_name, domain, prediction_text, confidence)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            prediction_id,
            datetime.utcnow().isoformat(),
            agent_name,
            domain,
            prediction_text,
            confidence
        ))
        
        conn.commit()
        conn.close()
    
    def record_outcome(
        self,
        prediction_id: str,
        outcome: str,
        accuracy_score: float
    ) -> None:
        """Record the actual outcome and accuracy of a prediction.
        
        Args:
            prediction_id: Unique prediction identifier
            outcome: 'correct', 'incorrect', 'partial'
            accuracy_score: 0.0-1.0 score (1.0 = perfect, 0.0 = completely wrong)
        """
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()
        
        cursor.execute("""
            UPDATE predictions
            SET outcome = ?, accuracy_score = ?, verification_date = ?
            WHERE id = ?
        """, (outcome, accuracy_score, datetime.utcnow().isoformat(), prediction_id))
        
        # Invalidate cache for this agent/domain
        cursor.execute("""
            SELECT agent_name, domain FROM predictions WHERE id = ?
        """, (prediction_id,))
        
        row = cursor.fetchone()
        if row:
            agent_name, domain = row
            cursor.execute("""
                DELETE FROM reputation_cache
                WHERE agent_name = ? AND domain = ?
            """, (agent_name, domain))
        
        conn.commit()
        conn.close()
    
    def calculate_agent_reputation(
        self,
        agent_name: str,
        domain: Optional[str] = None,
        use_cache: bool = True
    ) -> float:
        """Calculate reputation score for an agent in a specific domain.
        
        Args:
            agent_name: Name of the agent
            domain: Specific domain (None for overall reputation)
            use_cache: Whether to use cached scores
        
        Returns:
            Reputation score between 0.0 and 1.0
        """
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()
        
        # Check cache first
        if use_cache and domain:
            cursor.execute("""
                SELECT reputation_score, last_updated FROM reputation_cache
                WHERE agent_name = ? AND domain = ?
            """, (agent_name, domain))
            
            row = cursor.fetchone()
            if row:
                score, last_updated = row
                # Cache valid for 24 hours
                updated = datetime.fromisoformat(last_updated)
                if datetime.utcnow() - updated < timedelta(hours=24):
                    conn.close()
                    return score
        
        # Calculate fresh score
        query = """
            SELECT accuracy_score, confidence, timestamp
            FROM predictions
            WHERE agent_name = ? AND outcome IS NOT NULL
        """
        params = [agent_name]
        
        if domain:
            query += " AND domain = ?"
            params.append(domain)
        
        cursor.execute(query, params)
        rows = cursor.fetchall()
        
        if not rows:
            conn.close()
            return 0.5  # Neutral score for new agents
        
        # Calculate reputation components
        total = len(rows)
        accuracy_scores = [row[0] for row in rows if row[0] is not None]
        
        if not accuracy_scores:
            conn.close()
            return 0.5
        
        # Base accuracy (weight: 50%)
        base_accuracy = sum(accuracy_scores) / len(accuracy_scores)
        
        # Recent performance (weight: 30%)
        recent_cutoff = (datetime.utcnow() - timedelta(days=30)).isoformat()
        recent_scores = [
            row[0] for row in rows
            if row[2] >= recent_cutoff and row[0] is not None
        ]
        recent_accuracy = sum(recent_scores) / len(recent_scores) if recent_scores else base_accuracy
        
        # Confidence calibration (weight: 20%)
        # Measures how well confidence predicts accuracy
        calibration_errors = []
        for accuracy, confidence, _ in rows:
            if accuracy is not None:
                calibration_errors.append(abs(accuracy - confidence))
        
        calibration_score = 1.0 - (sum(calibration_errors) / len(calibration_errors)) if calibration_errors else 0.5
        
        # Weighted combination
        reputation_score = (
            base_accuracy * 0.5 +
            recent_accuracy * 0.3 +
            calibration_score * 0.2
        )
        
        # Apply sample size penalty for low prediction counts
        if total < 10:
            sample_penalty = total / 10.0
            reputation_score = reputation_score * sample_penalty + 0.5 * (1 - sample_penalty)
        
        # Cache the result
        if domain:
            cursor.execute("""
                INSERT OR REPLACE INTO reputation_cache
                (agent_name, domain, reputation_score, sample_size, last_updated)
                VALUES (?, ?, ?, ?, ?)
            """, (agent_name, domain, reputation_score, total, datetime.utcnow().isoformat()))
            conn.commit()
        
        conn.close()
        return reputation_score
    
    def get_agent_reputation(self, agent_name: str) -> AgentReputation:
        """Get comprehensive reputation data for an agent."""
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()
        
        # Overall stats
        cursor.execute("""
            SELECT COUNT(*), SUM(CASE WHEN outcome = 'correct' THEN 1 ELSE 0 END)
            FROM predictions
            WHERE agent_name = ? AND outcome IS NOT NULL
        """, (agent_name,))
        
        row = cursor.fetchone()
        total = row[0] if row else 0
        correct = row[1] if row else 0
        
        # Domain-specific scores
        cursor.execute("""
            SELECT DISTINCT domain FROM predictions WHERE agent_name = ?
        """, (agent_name,))
        
        domains = [row[0] for row in cursor.fetchall()]
        domain_scores = {
            domain: self.calculate_agent_reputation(agent_name, domain, use_cache=True)
            for domain in domains
        }
        
        # Recent accuracy
        recent_cutoff = (datetime.utcnow() - timedelta(days=30)).isoformat()
        cursor.execute("""
            SELECT AVG(accuracy_score)
            FROM predictions
            WHERE agent_name = ? AND outcome IS NOT NULL AND timestamp >= ?
        """, (agent_name, recent_cutoff))
        
        recent_accuracy = cursor.fetchone()[0] or 0.5
        
        # Confidence calibration
        cursor.execute("""
            SELECT AVG(ABS(accuracy_score - confidence))
            FROM predictions
            WHERE agent_name = ? AND outcome IS NOT NULL
        """, (agent_name,))
        
        calibration_error = cursor.fetchone()[0] or 0.5
        confidence_calibration = 1.0 - calibration_error
        
        conn.close()
        
        overall_score = self.calculate_agent_reputation(agent_name, domain=None, use_cache=False)
        
        return AgentReputation(
            agent_name=agent_name,
            overall_score=overall_score,
            domain_scores=domain_scores,
            total_predictions=total,
            correct_predictions=correct,
            recent_accuracy=recent_accuracy,
            confidence_calibration=confidence_calibration
        )
    
    def get_weighted_consensus(
        self,
        agent_predictions: List[Dict],
        domain: str,
        use_reputation: bool = True
    ) -> Dict:
        """Calculate weighted consensus using reputation scores.
        
        Args:
            agent_predictions: List of dicts with 'agent_name', 'prediction', 'confidence', 'probability'
            domain: Domain of the question
            use_reputation: Whether to use reputation weighting
        
        Returns:
            Dict with consensus probability, confidence, and weighting details
        """
        if not agent_predictions:
            return {
                "consensus_probability": 0.5,
                "consensus_confidence": 0.0,
                "total_weight": 0.0,
                "agent_weights": []
            }
        
        weighted_predictions = []
        total_weight = 0.0
        
        for pred in agent_predictions:
            agent_name = pred.get("agent_name", "Unknown")
            confidence = pred.get("confidence", 0.5)
            probability = pred.get("probability", 0.5)
            base_weight = pred.get("weight", 1.0)
            
            # Calculate final weight
            if use_reputation:
                reputation_score = self.calculate_agent_reputation(agent_name, domain)
            else:
                reputation_score = 1.0
            
            final_weight = base_weight * reputation_score * confidence
            
            weighted_predictions.append({
                "agent_name": agent_name,
                "probability": probability,
                "confidence": confidence,
                "base_weight": base_weight,
                "reputation_score": reputation_score,
                "final_weight": final_weight
            })
            
            total_weight += final_weight
        
        # Calculate consensus
        if total_weight > 0:
            consensus_probability = sum(
                p["probability"] * p["final_weight"] for p in weighted_predictions
            ) / total_weight
            
            consensus_confidence = sum(
                p["confidence"] * p["final_weight"] for p in weighted_predictions
            ) / total_weight
        else:
            consensus_probability = 0.5
            consensus_confidence = 0.0
        
        # Calculate dissent level
        dissent_count = 0
        consensus_range = 0.2
        for pred in weighted_predictions:
            if abs(pred["probability"] - consensus_probability) > consensus_range:
                dissent_count += 1
        
        dissent_percentage = dissent_count / len(weighted_predictions) if weighted_predictions else 0.0
        
        return {
            "consensus_probability": consensus_probability,
            "consensus_confidence": consensus_confidence,
            "total_weight": total_weight,
            "agent_weights": sorted(weighted_predictions, key=lambda x: x["final_weight"], reverse=True),
            "dissent_percentage": dissent_percentage,
            "requires_review": dissent_percentage > 0.4
        }
