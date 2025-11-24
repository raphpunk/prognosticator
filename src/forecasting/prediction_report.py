"""Comprehensive prediction report generation and analysis."""
import json
import hashlib
from datetime import datetime
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
from pathlib import Path


@dataclass
class AgentResponse:
    """Detailed agent response data."""
    agent_name: str
    response_text: str
    confidence: float
    base_weight: float
    relevance_boost: float
    performance_boost: float
    adjusted_weight: float
    execution_time_ms: int
    model_used: str
    prompt_tokens: Optional[int] = None
    completion_tokens: Optional[int] = None
    
    def to_dict(self) -> Dict:
        return asdict(self)


@dataclass
class DomainAnalysis:
    """Domain classification analysis."""
    primary_domain: str
    primary_confidence: float
    secondary_domains: List[Dict[str, float]]
    classification_reasoning: str
    domain_keywords_found: List[str]
    
    def to_dict(self) -> Dict:
        return asdict(self)


@dataclass
class ConsensusAnalysis:
    """Consensus calculation analysis."""
    consensus_strength: float
    total_weight: float
    top_weighted_agents: List[str]
    agreement_level: str  # unanimous, strong, moderate, weak, divergent
    outlier_agents: List[str]
    confidence_distribution: Dict[str, int]  # high, medium, low counts
    
    def to_dict(self) -> Dict:
        return asdict(self)


@dataclass
class PredictionMetadata:
    """Metadata about prediction execution."""
    prediction_id: str
    question: str
    question_hash: str
    timestamp: str
    total_execution_time_ms: int
    num_agents_called: int
    num_agents_succeeded: int
    num_agents_failed: int
    cache_hits: int
    circuit_breaker_trips: int
    
    def to_dict(self) -> Dict:
        return asdict(self)


@dataclass
class PredictionReport:
    """Complete prediction analysis report."""
    metadata: PredictionMetadata
    domain_analysis: DomainAnalysis
    agent_responses: List[AgentResponse]
    consensus_analysis: ConsensusAnalysis
    summary: str
    key_insights: List[str]
    uncertainty_factors: List[str]
    data_quality_score: float  # 0-1 based on agent agreement, confidence, etc.
    
    def to_dict(self) -> Dict:
        return {
            "metadata": self.metadata.to_dict(),
            "domain_analysis": self.domain_analysis.to_dict(),
            "agent_responses": [r.to_dict() for r in self.agent_responses],
            "consensus_analysis": self.consensus_analysis.to_dict(),
            "summary": self.summary,
            "key_insights": self.key_insights,
            "uncertainty_factors": self.uncertainty_factors,
            "data_quality_score": self.data_quality_score
        }
    
    def to_json(self) -> str:
        """Serialize report to JSON."""
        return json.dumps(self.to_dict(), indent=2, default=str)
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'PredictionReport':
        """Deserialize report from dict."""
        return cls(
            metadata=PredictionMetadata(**data["metadata"]),
            domain_analysis=DomainAnalysis(**data["domain_analysis"]),
            agent_responses=[AgentResponse(**r) for r in data["agent_responses"]],
            consensus_analysis=ConsensusAnalysis(**data["consensus_analysis"]),
            summary=data["summary"],
            key_insights=data["key_insights"],
            uncertainty_factors=data["uncertainty_factors"],
            data_quality_score=data["data_quality_score"]
        )


class PredictionReportGenerator:
    """Generate comprehensive prediction reports."""
    
    def __init__(self, reports_dir: str = "data/prediction_reports"):
        self.reports_dir = Path(reports_dir)
        self.reports_dir.mkdir(parents=True, exist_ok=True)
    
    def generate_report(
        self,
        question: str,
        domain_classification: Dict,
        agent_responses: List[Dict],
        consensus_result: Dict,
        execution_metrics: Dict
    ) -> PredictionReport:
        """Generate comprehensive prediction report."""
        
        # Generate prediction ID
        question_hash = hashlib.sha256(question.encode()).hexdigest()[:16]
        timestamp = datetime.utcnow().isoformat()
        prediction_id = f"{question_hash}_{timestamp.replace(':', '-').replace('.', '-')}"
        
        # Build metadata
        metadata = PredictionMetadata(
            prediction_id=prediction_id,
            question=question,
            question_hash=question_hash,
            timestamp=timestamp,
            total_execution_time_ms=execution_metrics.get("total_time_ms", 0),
            num_agents_called=len(agent_responses),
            num_agents_succeeded=execution_metrics.get("succeeded", len(agent_responses)),
            num_agents_failed=execution_metrics.get("failed", 0),
            cache_hits=execution_metrics.get("cache_hits", 0),
            circuit_breaker_trips=execution_metrics.get("circuit_breaker_trips", 0)
        )
        
        # Build domain analysis
        domain_analysis = self._analyze_domain_classification(
            question,
            domain_classification
        )
        
        # Build agent response objects
        agent_response_objects = []
        for resp in agent_responses:
            agent_response_objects.append(AgentResponse(
                agent_name=resp.get("agent_name", "Unknown"),
                response_text=resp.get("response", ""),
                confidence=resp.get("confidence", 0.5),
                base_weight=resp.get("base_weight", 1.0),
                relevance_boost=resp.get("relevance_boost", 1.0),
                performance_boost=resp.get("performance_boost", 1.0),
                adjusted_weight=resp.get("adjusted_weight", 1.0),
                execution_time_ms=resp.get("execution_time_ms", 0),
                model_used=resp.get("model", "unknown"),
                prompt_tokens=resp.get("prompt_tokens"),
                completion_tokens=resp.get("completion_tokens")
            ))
        
        # Build consensus analysis
        consensus_analysis = self._analyze_consensus(
            agent_response_objects,
            consensus_result
        )
        
        # Generate summary and insights
        summary = self._generate_summary(
            question,
            domain_analysis,
            consensus_analysis,
            agent_response_objects
        )
        
        key_insights = self._extract_key_insights(
            agent_response_objects,
            consensus_analysis
        )
        
        uncertainty_factors = self._identify_uncertainty_factors(
            agent_response_objects,
            consensus_analysis,
            execution_metrics
        )
        
        # Calculate data quality score
        data_quality_score = self._calculate_data_quality_score(
            agent_response_objects,
            consensus_analysis,
            execution_metrics
        )
        
        report = PredictionReport(
            metadata=metadata,
            domain_analysis=domain_analysis,
            agent_responses=agent_response_objects,
            consensus_analysis=consensus_analysis,
            summary=summary,
            key_insights=key_insights,
            uncertainty_factors=uncertainty_factors,
            data_quality_score=data_quality_score
        )
        
        # Save report
        self._save_report(report)
        
        return report
    
    def _analyze_domain_classification(
        self,
        question: str,
        classification: Dict
    ) -> DomainAnalysis:
        """Analyze domain classification results."""
        primary = classification.get("primary_domain", "general")
        confidence = classification.get("confidence", 0.0)
        secondary = classification.get("secondary_domains", [])
        
        # Extract keywords that triggered classification
        keywords_found = self._extract_domain_keywords(question, primary)
        
        reasoning = f"Classified as {primary} based on "
        if len(keywords_found) > 0:
            reasoning += f"{len(keywords_found)} domain-specific keywords"
        else:
            reasoning += "general geopolitical context"
        
        return DomainAnalysis(
            primary_domain=primary,
            primary_confidence=confidence,
            secondary_domains=[
                {"domain": d[0], "confidence": d[1]} 
                for d in secondary
            ] if isinstance(secondary, list) else [],
            classification_reasoning=reasoning,
            domain_keywords_found=keywords_found
        )
    
    def _extract_domain_keywords(self, question: str, domain: str) -> List[str]:
        """Extract domain-specific keywords found in question."""
        # Simplified - in production, use domain patterns from DomainClassifier
        domain_keywords = {
            "military": ["military", "troop", "weapon", "defense", "combat"],
            "financial": ["market", "stock", "currency", "inflation", "gdp"],
            "energy": ["oil", "gas", "energy", "petroleum", "renewable"],
            "technology": ["cyber", "hack", "ai", "chip", "tech"],
            "climate": ["climate", "weather", "carbon", "emissions"],
        }
        
        keywords = domain_keywords.get(domain, [])
        found = [kw for kw in keywords if kw in question.lower()]
        return found[:5]  # Top 5
    
    def _analyze_consensus(
        self,
        agent_responses: List[AgentResponse],
        consensus_result: Dict
    ) -> ConsensusAnalysis:
        """Analyze consensus strength and agreement."""
        total_weight = sum(r.adjusted_weight for r in agent_responses)
        top_3 = sorted(agent_responses, key=lambda x: x.adjusted_weight, reverse=True)[:3]
        top_3_weight = sum(r.adjusted_weight for r in top_3)
        
        consensus_strength = top_3_weight / total_weight if total_weight > 0 else 0.0
        
        # Determine agreement level
        if consensus_strength >= 0.8:
            agreement_level = "unanimous"
        elif consensus_strength >= 0.65:
            agreement_level = "strong"
        elif consensus_strength >= 0.5:
            agreement_level = "moderate"
        elif consensus_strength >= 0.35:
            agreement_level = "weak"
        else:
            agreement_level = "divergent"
        
        # Find outliers (agents with very different views)
        avg_weight = total_weight / len(agent_responses) if agent_responses else 0
        outliers = [
            r.agent_name for r in agent_responses
            if r.adjusted_weight < avg_weight * 0.3
        ]
        
        # Confidence distribution
        confidence_dist = {"high": 0, "medium": 0, "low": 0}
        for r in agent_responses:
            if r.confidence >= 0.7:
                confidence_dist["high"] += 1
            elif r.confidence >= 0.4:
                confidence_dist["medium"] += 1
            else:
                confidence_dist["low"] += 1
        
        return ConsensusAnalysis(
            consensus_strength=consensus_strength,
            total_weight=total_weight,
            top_weighted_agents=[r.agent_name for r in top_3],
            agreement_level=agreement_level,
            outlier_agents=outliers,
            confidence_distribution=confidence_dist
        )
    
    def _generate_summary(
        self,
        question: str,
        domain_analysis: DomainAnalysis,
        consensus_analysis: ConsensusAnalysis,
        agent_responses: List[AgentResponse]
    ) -> str:
        """Generate executive summary of prediction."""
        summary_parts = []
        
        # Domain context
        summary_parts.append(
            f"Analysis of {domain_analysis.primary_domain} question "
            f"with {domain_analysis.primary_confidence:.0%} classification confidence."
        )
        
        # Consensus strength
        summary_parts.append(
            f"Consensus shows {consensus_analysis.agreement_level} agreement "
            f"(strength: {consensus_analysis.consensus_strength:.0%}) "
            f"across {len(agent_responses)} expert agents."
        )
        
        # Top agents
        if consensus_analysis.top_weighted_agents:
            top_agent = consensus_analysis.top_weighted_agents[0]
            summary_parts.append(
                f"Analysis led by {top_agent} with highest domain relevance."
            )
        
        # Confidence
        high_conf = consensus_analysis.confidence_distribution.get("high", 0)
        total_agents = len(agent_responses)
        if high_conf >= total_agents * 0.6:
            summary_parts.append("High confidence across majority of agents.")
        elif high_conf < total_agents * 0.3:
            summary_parts.append("Low confidence indicates high uncertainty.")
        
        return " ".join(summary_parts)
    
    def _extract_key_insights(
        self,
        agent_responses: List[AgentResponse],
        consensus_analysis: ConsensusAnalysis
    ) -> List[str]:
        """Extract key insights from agent responses."""
        insights = []
        
        # Top weighted agent perspectives
        top_agents = consensus_analysis.top_weighted_agents[:3]
        for agent_name in top_agents:
            agent = next((r for r in agent_responses if r.agent_name == agent_name), None)
            if agent:
                # Extract first sentence as insight
                first_sentence = agent.response_text.split('.')[0].strip()
                if len(first_sentence) > 20:  # Meaningful sentence
                    insights.append(f"{agent_name}: {first_sentence}")
        
        # Performance-based insights
        high_performers = [r for r in agent_responses if r.performance_boost > 1.2]
        if high_performers:
            insights.append(
                f"High-accuracy agents ({', '.join([r.agent_name for r in high_performers[:2]])}) "
                f"contribute weighted analysis"
            )
        
        return insights[:5]  # Top 5 insights
    
    def _identify_uncertainty_factors(
        self,
        agent_responses: List[AgentResponse],
        consensus_analysis: ConsensusAnalysis,
        execution_metrics: Dict
    ) -> List[str]:
        """Identify factors contributing to prediction uncertainty."""
        factors = []
        
        # Low consensus
        if consensus_analysis.consensus_strength < 0.5:
            factors.append(
                f"Low consensus ({consensus_analysis.consensus_strength:.0%}) "
                f"indicates divergent expert opinions"
            )
        
        # Outliers
        if len(consensus_analysis.outlier_agents) > 2:
            factors.append(
                f"{len(consensus_analysis.outlier_agents)} agents provided "
                f"significantly divergent analysis"
            )
        
        # Low confidence
        low_conf_count = consensus_analysis.confidence_distribution.get("low", 0)
        if low_conf_count > len(agent_responses) * 0.4:
            factors.append(
                f"{low_conf_count}/{len(agent_responses)} agents expressed low confidence"
            )
        
        # Execution issues
        if execution_metrics.get("failed", 0) > 0:
            factors.append(
                f"{execution_metrics['failed']} agent(s) failed to respond - "
                f"reduced analysis coverage"
            )
        
        if execution_metrics.get("circuit_breaker_trips", 0) > 0:
            factors.append(
                "Service instability detected - some analysis may be incomplete"
            )
        
        return factors
    
    def _calculate_data_quality_score(
        self,
        agent_responses: List[AgentResponse],
        consensus_analysis: ConsensusAnalysis,
        execution_metrics: Dict
    ) -> float:
        """Calculate overall data quality score (0-1)."""
        scores = []
        
        # Consensus strength (weight: 0.3)
        scores.append(consensus_analysis.consensus_strength * 0.3)
        
        # Confidence distribution (weight: 0.25)
        high_conf = consensus_analysis.confidence_distribution.get("high", 0)
        conf_score = high_conf / len(agent_responses) if agent_responses else 0
        scores.append(conf_score * 0.25)
        
        # Agent success rate (weight: 0.25)
        total_called = execution_metrics.get("succeeded", 0) + execution_metrics.get("failed", 0)
        success_rate = execution_metrics.get("succeeded", 0) / total_called if total_called > 0 else 1.0
        scores.append(success_rate * 0.25)
        
        # Performance-weighted agents (weight: 0.2)
        high_performers = [r for r in agent_responses if r.performance_boost > 1.0]
        perf_score = len(high_performers) / len(agent_responses) if agent_responses else 0
        scores.append(perf_score * 0.2)
        
        return sum(scores)
    
    def _save_report(self, report: PredictionReport) -> None:
        """Save report to disk."""
        report_file = self.reports_dir / f"{report.metadata.prediction_id}.json"
        with open(report_file, 'w') as f:
            f.write(report.to_json())
    
    def load_report(self, prediction_id: str) -> Optional[PredictionReport]:
        """Load report from disk."""
        report_file = self.reports_dir / f"{prediction_id}.json"
        if not report_file.exists():
            return None
        
        with open(report_file, 'r') as f:
            data = json.load(f)
            return PredictionReport.from_dict(data)
    
    def list_reports(self, limit: int = 100) -> List[Dict[str, Any]]:
        """List all prediction reports (metadata only)."""
        reports = []
        
        for report_file in sorted(self.reports_dir.glob("*.json"), reverse=True)[:limit]:
            try:
                with open(report_file, 'r') as f:
                    data = json.load(f)
                    reports.append({
                        "prediction_id": data["metadata"]["prediction_id"],
                        "question": data["metadata"]["question"],
                        "timestamp": data["metadata"]["timestamp"],
                        "domain": data["domain_analysis"]["primary_domain"],
                        "consensus_strength": data["consensus_analysis"]["consensus_strength"],
                        "data_quality_score": data["data_quality_score"],
                        "num_agents": data["metadata"]["num_agents_called"]
                    })
            except Exception:
                continue
        
        return reports
