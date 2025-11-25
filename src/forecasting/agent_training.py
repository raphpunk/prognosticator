"""
Agent Training and Testing System

Provides tools to:
1. Test agent performance on historical events with known outcomes
2. Train agents by fine-tuning prompts based on performance
3. Track accuracy metrics over time
4. Generate training reports
"""

import json
import sqlite3
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, asdict
import logging

logger = logging.getLogger(__name__)


@dataclass
class TrainingCase:
    """A training/test case with known outcome"""
    id: str
    question: str
    context_articles: List[str]  # Article IDs or text snippets
    actual_outcome: bool  # True if event occurred, False if not
    outcome_date: datetime
    domain: str  # military, financial, technology, etc.
    difficulty: str  # easy, medium, hard
    notes: str = ""


@dataclass
class AgentTestResult:
    """Result of testing an agent on a training case"""
    agent_name: str
    case_id: str
    predicted_probability: float
    predicted_confidence: float
    actual_outcome: bool
    brier_score: float  # (predicted_prob - actual_outcome)^2
    log_score: float  # -log(predicted_prob) if outcome=True, else -log(1-predicted_prob)
    calibration_error: float
    test_date: datetime
    model_used: str
    response_text: str


@dataclass
class AgentPerformanceMetrics:
    """Aggregated performance metrics for an agent"""
    agent_name: str
    total_tests: int
    avg_brier_score: float
    avg_log_score: float
    avg_calibration_error: float
    accuracy_rate: float  # % of correct predictions (prob >0.5 matches outcome)
    domain_performance: Dict[str, float]  # Brier score by domain
    model_used: str


class AgentTrainingSystem:
    """System for testing and training forecasting agents"""
    
    def __init__(self, db_path: str = "data/training.db"):
        self.db_path = db_path
        self._init_database()
    
    def _init_database(self):
        """Initialize training database schema"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Training cases table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS training_cases (
                id TEXT PRIMARY KEY,
                question TEXT NOT NULL,
                context_articles TEXT NOT NULL,
                actual_outcome INTEGER NOT NULL,
                outcome_date TEXT NOT NULL,
                domain TEXT NOT NULL,
                difficulty TEXT NOT NULL,
                notes TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Test results table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS test_results (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                agent_name TEXT NOT NULL,
                case_id TEXT NOT NULL,
                predicted_probability REAL NOT NULL,
                predicted_confidence REAL NOT NULL,
                actual_outcome INTEGER NOT NULL,
                brier_score REAL NOT NULL,
                log_score REAL NOT NULL,
                calibration_error REAL NOT NULL,
                test_date TEXT NOT NULL,
                model_used TEXT NOT NULL,
                response_text TEXT,
                FOREIGN KEY (case_id) REFERENCES training_cases(id)
            )
        """)
        
        # Create indexes
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_test_agent ON test_results(agent_name)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_test_case ON test_results(case_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_test_date ON test_results(test_date)")
        
        conn.commit()
        conn.close()
    
    def add_training_case(self, case: TrainingCase) -> bool:
        """Add a new training case to the database"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("""
                INSERT INTO training_cases 
                (id, question, context_articles, actual_outcome, outcome_date, domain, difficulty, notes)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                case.id,
                case.question,
                json.dumps(case.context_articles),
                1 if case.actual_outcome else 0,
                case.outcome_date.isoformat(),
                case.domain,
                case.difficulty,
                case.notes
            ))
            
            conn.commit()
            conn.close()
            logger.info(f"Added training case: {case.id}")
            return True
        except Exception as e:
            logger.error(f"Failed to add training case: {e}")
            return False
    
    def get_training_cases(self, domain: Optional[str] = None, 
                          difficulty: Optional[str] = None) -> List[TrainingCase]:
        """Retrieve training cases, optionally filtered"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        query = "SELECT * FROM training_cases WHERE 1=1"
        params = []
        
        if domain:
            query += " AND domain = ?"
            params.append(domain)
        if difficulty:
            query += " AND difficulty = ?"
            params.append(difficulty)
        
        cursor.execute(query, params)
        rows = cursor.fetchall()
        conn.close()
        
        cases = []
        for row in rows:
            cases.append(TrainingCase(
                id=row[0],
                question=row[1],
                context_articles=json.loads(row[2]),
                actual_outcome=bool(row[3]),
                outcome_date=datetime.fromisoformat(row[4]),
                domain=row[5],
                difficulty=row[6],
                notes=row[7] or ""
            ))
        
        return cases
    
    def record_test_result(self, result: AgentTestResult) -> bool:
        """Record an agent test result"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("""
                INSERT INTO test_results 
                (agent_name, case_id, predicted_probability, predicted_confidence, 
                 actual_outcome, brier_score, log_score, calibration_error, 
                 test_date, model_used, response_text)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                result.agent_name,
                result.case_id,
                result.predicted_probability,
                result.predicted_confidence,
                1 if result.actual_outcome else 0,
                result.brier_score,
                result.log_score,
                result.calibration_error,
                result.test_date.isoformat(),
                result.model_used,
                result.response_text
            ))
            
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            logger.error(f"Failed to record test result: {e}")
            return False
    
    def calculate_agent_performance(self, agent_name: str, 
                                   days_lookback: int = 30) -> Optional[AgentPerformanceMetrics]:
        """Calculate performance metrics for an agent"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cutoff_date = (datetime.utcnow() - timedelta(days=days_lookback)).isoformat()
        
        cursor.execute("""
            SELECT 
                agent_name,
                COUNT(*) as total_tests,
                AVG(brier_score) as avg_brier,
                AVG(log_score) as avg_log,
                AVG(calibration_error) as avg_calibration,
                model_used
            FROM test_results
            WHERE agent_name = ? AND test_date >= ?
            GROUP BY agent_name, model_used
        """, (agent_name, cutoff_date))
        
        row = cursor.fetchone()
        if not row:
            conn.close()
            return None
        
        # Calculate accuracy rate
        cursor.execute("""
            SELECT 
                COUNT(*) as correct
            FROM test_results
            WHERE agent_name = ? 
            AND test_date >= ?
            AND ((predicted_probability >= 0.5 AND actual_outcome = 1) OR 
                 (predicted_probability < 0.5 AND actual_outcome = 0))
        """, (agent_name, cutoff_date))
        
        correct_count = cursor.fetchone()[0]
        accuracy_rate = correct_count / row[1] if row[1] > 0 else 0.0
        
        # Calculate domain-specific performance
        cursor.execute("""
            SELECT tc.domain, AVG(tr.brier_score) as avg_brier
            FROM test_results tr
            JOIN training_cases tc ON tr.case_id = tc.id
            WHERE tr.agent_name = ? AND tr.test_date >= ?
            GROUP BY tc.domain
        """, (agent_name, cutoff_date))
        
        domain_perf = {domain: brier for domain, brier in cursor.fetchall()}
        
        conn.close()
        
        return AgentPerformanceMetrics(
            agent_name=row[0],
            total_tests=row[1],
            avg_brier_score=row[2],
            avg_log_score=row[3],
            avg_calibration_error=row[4],
            accuracy_rate=accuracy_rate,
            domain_performance=domain_perf,
            model_used=row[5]
        )
    
    def get_all_agent_performance(self, days_lookback: int = 30) -> List[AgentPerformanceMetrics]:
        """Get performance metrics for all tested agents"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cutoff_date = (datetime.utcnow() - timedelta(days=days_lookback)).isoformat()
        
        cursor.execute("""
            SELECT DISTINCT agent_name
            FROM test_results
            WHERE test_date >= ?
        """, (cutoff_date,))
        
        agent_names = [row[0] for row in cursor.fetchall()]
        conn.close()
        
        metrics = []
        for agent_name in agent_names:
            perf = self.calculate_agent_performance(agent_name, days_lookback)
            if perf:
                metrics.append(perf)
        
        return sorted(metrics, key=lambda x: x.avg_brier_score)
    
    def generate_training_report(self, days_lookback: int = 30) -> str:
        """Generate a comprehensive training report"""
        metrics = self.get_all_agent_performance(days_lookback)
        
        if not metrics:
            return "No training data available."
        
        report = []
        report.append("=" * 80)
        report.append(f"AGENT TRAINING REPORT (Last {days_lookback} Days)")
        report.append("=" * 80)
        report.append("")
        report.append(f"Total Agents Tested: {len(metrics)}")
        report.append("")
        
        for i, perf in enumerate(metrics, 1):
            report.append(f"{i}. {perf.agent_name}")
            report.append(f"   Model: {perf.model_used}")
            report.append(f"   Tests: {perf.total_tests}")
            report.append(f"   Brier Score: {perf.avg_brier_score:.4f} (lower is better)")
            report.append(f"   Log Score: {perf.avg_log_score:.4f} (lower is better)")
            report.append(f"   Accuracy: {perf.accuracy_rate:.1%}")
            report.append(f"   Calibration Error: {perf.avg_calibration_error:.4f}")
            
            if perf.domain_performance:
                report.append(f"   Domain Performance:")
                for domain, brier in sorted(perf.domain_performance.items(), key=lambda x: x[1]):
                    report.append(f"     - {domain}: {brier:.4f}")
            report.append("")
        
        # Best performers by metric
        report.append("Best Performers:")
        report.append(f"  Most Accurate: {metrics[0].agent_name} ({metrics[0].accuracy_rate:.1%})")
        best_brier = min(metrics, key=lambda x: x.avg_brier_score)
        report.append(f"  Best Brier Score: {best_brier.agent_name} ({best_brier.avg_brier_score:.4f})")
        best_calibrated = min(metrics, key=lambda x: x.avg_calibration_error)
        report.append(f"  Best Calibrated: {best_calibrated.agent_name} ({best_calibrated.avg_calibration_error:.4f})")
        
        return "\n".join(report)


# Convenience functions

def add_default_training_cases(training_system: AgentTrainingSystem):
    """Add some default training cases for testing"""
    
    cases = [
        TrainingCase(
            id="case_001_venezuela_fto",
            question="What is the probability that the U.S. designates Venezuelan security forces as FTO within 30 days?",
            context_articles=[
                "State Department officials express concern over Venezuelan military",
                "Treasury sanctions Venezuelan intelligence officials",
                "Marco Rubio demands action on Venezuelan regime"
            ],
            actual_outcome=True,
            outcome_date=datetime(2025, 11, 20),
            domain="military",
            difficulty="medium",
            notes="Actually occurred on Nov 20, 2025"
        ),
        TrainingCase(
            id="case_002_bank_failure",
            question="What is the probability of a major U.S. regional bank failure within 60 days?",
            context_articles=[
                "Regional banks see deposit outflows amid rate uncertainty",
                "Commercial real estate stress at highest level since 2009",
                "FDIC prepares contingency plans for mid-tier institutions"
            ],
            actual_outcome=False,
            outcome_date=datetime(2025, 11, 15),
            domain="financial",
            difficulty="medium",
            notes="No major failures occurred"
        ),
        TrainingCase(
            id="case_003_semiconductor_disruption",
            question="What is the probability of major semiconductor supply chain disruption within 90 days?",
            context_articles=[
                "TSMC reports normal operations in Taiwan",
                "U.S. chipmakers diversifying production locations",
                "China announces new semiconductor export controls"
            ],
            actual_outcome=False,
            outcome_date=datetime(2025, 11, 1),
            domain="technology",
            difficulty="hard",
            notes="No major disruptions observed"
        ),
    ]
    
    for case in cases:
        training_system.add_training_case(case)
    
    logger.info(f"Added {len(cases)} default training cases")


def test_agent_on_case(agent_profile: Dict, case: TrainingCase, 
                       ollama_url: str, training_system: AgentTrainingSystem) -> AgentTestResult:
    """
    Test a single agent on a training case
    
    Note: This is a stub - actual implementation should call the agent
    with the case context and extract probability/confidence from response
    """
    import math
    from ..forecasting.ollama_resilience import call_ollama_http
    
    # Build context prompt
    context = "\n\n".join(case.context_articles)
    prompt = f"""Based on the following context, {case.question}

Context:
{context}

Provide your assessment as a probability (0.0 to 1.0) and confidence level (0.0 to 1.0).
Format your response as: PROBABILITY: X.XX | CONFIDENCE: X.XX"""
    
    try:
        response = call_ollama_http(
            url=ollama_url,
            model=agent_profile["model"],
            prompt=prompt,
            system=agent_profile.get("role", "You are a forecasting expert.")
        )
        
        # Parse response for probability and confidence
        prob = 0.5
        conf = 0.5
        
        # Simple regex extraction
        import re
        prob_match = re.search(r'PROBABILITY:\s*([0-9.]+)', response, re.IGNORECASE)
        conf_match = re.search(r'CONFIDENCE:\s*([0-9.]+)', response, re.IGNORECASE)
        
        if prob_match:
            prob = float(prob_match.group(1))
        if conf_match:
            conf = float(conf_match.group(1))
        
        # Calculate metrics
        actual_float = 1.0 if case.actual_outcome else 0.0
        brier = (prob - actual_float) ** 2
        
        # Log score (probabilistic scoring rule)
        if case.actual_outcome:
            log_score = -math.log(max(prob, 0.001))  # Avoid log(0)
        else:
            log_score = -math.log(max(1 - prob, 0.001))
        
        # Calibration error
        accuracy = 1.0 - brier
        calibration_error = abs(conf - accuracy)
        
        result = AgentTestResult(
            agent_name=agent_profile["name"],
            case_id=case.id,
            predicted_probability=prob,
            predicted_confidence=conf,
            actual_outcome=case.actual_outcome,
            brier_score=brier,
            log_score=log_score,
            calibration_error=calibration_error,
            test_date=datetime.utcnow(),
            model_used=agent_profile["model"],
            response_text=response
        )
        
        training_system.record_test_result(result)
        return result
        
    except Exception as e:
        logger.error(f"Test failed for {agent_profile['name']}: {e}")
        raise
