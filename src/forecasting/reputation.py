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
    
    def validate_prediction(
        self,
        prediction_id: str,
        predicted_probability: float,
        predicted_confidence: float,
        actual_outcome: bool,
        outcome_context: Optional[str] = None
    ) -> Dict[str, float]:
        """Validate a prediction against actual outcome and update reputation.
        
        This method compares predicted probability to actual outcome, calculates
        accuracy metrics, and updates agent reputation accordingly.
        
        Args:
            prediction_id: Unique identifier for the prediction
            predicted_probability: Predicted probability (0.0-1.0)
            predicted_confidence: Agent's confidence in prediction (0.0-1.0)
            actual_outcome: Whether event occurred (True) or not (False)
            outcome_context: Optional context about the outcome
            
        Returns:
            Dictionary with validation metrics including accuracy_score,
            calibration_error, outcome_match, brier_score, and outcome_classification
        """
        # Calculate Brier score (lower is better, 0 = perfect)
        # Brier score = (predicted_prob - actual)^2
        actual_value = 1.0 if actual_outcome else 0.0
        brier_score = (predicted_probability - actual_value) ** 2
        
        # Convert Brier score to accuracy score (higher is better, 1 = perfect)
        # accuracy_score = 1 - brier_score
        accuracy_score = 1.0 - brier_score
        
        # Check if prediction direction was correct
        # If predicted >0.5 and event happened, or predicted <0.5 and didn't happen
        prediction_direction = predicted_probability > 0.5
        outcome_match = prediction_direction == actual_outcome
        
        # Calculate calibration error (how well confidence matched actual accuracy)
        calibration_error = abs(predicted_confidence - accuracy_score)
        
        # Determine outcome classification
        if outcome_match:
            if accuracy_score > 0.8:
                outcome = "correct"
            else:
                outcome = "partial"  # Right direction but poor calibration
        else:
            outcome = "incorrect"
        
        # Record the outcome
        self.record_outcome(
            prediction_id=prediction_id,
            outcome=outcome,
            accuracy_score=accuracy_score
        )
        
        return {
            "accuracy_score": accuracy_score,
            "brier_score": brier_score,
            "calibration_error": calibration_error,
            "outcome_match": outcome_match,
            "outcome_classification": outcome,
            "predicted_probability": predicted_probability,
            "predicted_confidence": predicted_confidence,
            "actual_outcome": actual_outcome
        }
    
    def batch_validate_predictions(
        self,
        validations: List[Dict]
    ) -> Dict:
        """Validate multiple predictions in batch.
        
        Args:
            validations: List of validation dicts with keys:
                - prediction_id
                - predicted_probability
                - predicted_confidence
                - actual_outcome
                - outcome_context (optional)
                
        Returns:
            Dictionary with batch validation summary
        """
        results = []
        total_accuracy = 0.0
        correct_count = 0
        
        for val in validations:
            result = self.validate_prediction(
                prediction_id=val["prediction_id"],
                predicted_probability=val["predicted_probability"],
                predicted_confidence=val["predicted_confidence"],
                actual_outcome=val["actual_outcome"],
                outcome_context=val.get("outcome_context")
            )
            results.append(result)
            total_accuracy += result["accuracy_score"]
            if result["outcome_match"]:
                correct_count += 1
        
        return {
            "total_predictions": len(validations),
            "correct_predictions": correct_count,
            "accuracy_rate": correct_count / len(validations) if validations else 0.0,
            "average_accuracy_score": total_accuracy / len(validations) if validations else 0.0,
            "results": results
        }

