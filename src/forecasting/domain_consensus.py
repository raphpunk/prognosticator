"""Domain-aware consensus algorithm with dynamic weight adjustment."""
import re
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass
from collections import defaultdict


@dataclass
class DomainClassification:
    """Question domain classification result."""
    primary_domain: str
    confidence: float
    secondary_domains: List[Tuple[str, float]]


class DomainClassifier:
    """Classify questions into domains for expert routing."""
    
    # Domain keywords and patterns
    DOMAIN_PATTERNS = {
        "military": [
            r"\b(military|troop|deployment|weapon|missile|naval|airforce|army|defense|combat|war|conflict|strategic|tactical)\b",
            r"\b(nato|pentagon|defense minister|battalion|carrier group|aircraft|fighter jet)\b"
        ],
        "financial": [
            r"\b(market|stock|bond|currency|forex|gdp|inflation|interest rate|fed|central bank|dollar|euro)\b",
            r"\b(s&p|dow|nasdaq|wall street|investor|trading|volatility|recession|bull market|bear market)\b"
        ],
        "energy": [
            r"\b(oil|gas|petroleum|opec|energy|barrel|crude|natural gas|renewable|solar|wind|nuclear)\b",
            r"\b(pipeline|refinery|lng|power grid|electricity|coal|uranium|carbon)\b"
        ],
        "technology": [
            r"\b(cyber|hack|malware|ransomware|ai|artificial intelligence|semiconductor|chip|tech|software)\b",
            r"\b(data breach|vulnerability|zero-day|encryption|quantum|5g|cloud|infrastructure)\b"
        ],
        "climate": [
            r"\b(climate|weather|hurricane|flood|drought|temperature|carbon|emissions|renewable)\b",
            r"\b(ipcc|paris agreement|cop\d+|green|sustainability|environmental)\b"
        ],
        "geopolitical": [
            r"\b(diplomatic|treaty|alliance|sanction|embargo|un|security council|ambassador)\b",
            r"\b(sovereignty|territorial|border|refugee|migration|humanitarian)\b"
        ],
        "logistics": [
            r"\b(supply chain|shipping|container|port|freight|cargo|transportation|bottleneck)\b",
            r"\b(semiconductor shortage|just-in-time|inventory|logistics|distribution)\b"
        ],
        "societal": [
            r"\b(protest|riot|civil unrest|demonstration|strike|inequality|poverty|unemployment)\b",
            r"\b(social movement|populism|polarization|demographic|migration)\b"
        ],
        "health": [
            r"\b(pandemic|virus|vaccine|outbreak|epidemic|who|health|hospital|disease|covid)\b",
            r"\b(biosecurity|bioweapon|quarantine|mortality|infection rate)\b"
        ],
        "intelligence": [
            r"\b(intelligence|spy|espionage|osint|surveillance|reconnaissance|classified)\b",
            r"\b(cia|fbi|nsa|mi6|mossad|signal intelligence|humint)\b"
        ]
    }
    
    # Expert-to-domain mapping
    EXPERT_DOMAINS = {
        "📊 Macro Risk Forecaster": ["geopolitical", "financial"],
        "🚚 Demand & Logistics Forecaster": ["logistics", "energy"],
        "💹 Financial Market Forecaster": ["financial"],
        "⚡ Energy & Resource Forecaster": ["energy"],
        "📈 Time-Series Specialist": ["financial", "logistics"],
        "🎖️ Military Strategy Expert": ["military"],
        "📚 Historical Trends Expert": ["geopolitical", "societal"],
        "🔐 Technology & Cyber Expert": ["technology"],
        "🌍 Climate & Environmental Expert": ["climate", "energy"],
        "👥 Societal Dynamics Expert": ["societal"],
        "🏛️ Policy & Governance Analyst": ["geopolitical"],
        "📡 Intelligence & OSINT Specialist": ["intelligence", "military"],
        "🏭 Industrial & Manufacturing Analyst": ["logistics"],
        "🧬 Health & Biosecurity Expert": ["health"],
        "🌐 Network & Infrastructure Analyst": ["technology"],
        "🎲 Chaos Agent": []  # No specific domain, contrarian to all
    }
    
    def classify(self, question: str) -> DomainClassification:
        """Classify question into primary and secondary domains."""
        question_lower = question.lower()
        
        # Count pattern matches per domain
        domain_scores = defaultdict(int)
        
        for domain, patterns in self.DOMAIN_PATTERNS.items():
            for pattern in patterns:
                matches = len(re.findall(pattern, question_lower))
                domain_scores[domain] += matches
        
        if not domain_scores:
            # Default to geopolitical for general questions
            return DomainClassification(
                primary_domain="geopolitical",
                confidence=0.3,
                secondary_domains=[]
            )
        
        # Sort domains by score
        sorted_domains = sorted(domain_scores.items(), key=lambda x: x[1], reverse=True)
        
        total_score = sum(domain_scores.values())
        primary_domain, primary_score = sorted_domains[0]
        primary_confidence = primary_score / total_score if total_score > 0 else 0.5
        
        # Secondary domains (score >= 20% of primary)
        secondary_threshold = primary_score * 0.2
        secondary_domains = [
            (domain, score / total_score)
            for domain, score in sorted_domains[1:]
            if score >= secondary_threshold
        ]
        
        return DomainClassification(
            primary_domain=primary_domain,
            confidence=primary_confidence,
            secondary_domains=secondary_domains[:2]  # Top 2 secondary
        )


class DomainAwareConsensus:
    """Weighted consensus with domain-specific expert boosting."""
    
    def __init__(self, classifier: Optional[DomainClassifier] = None):
        self.classifier = classifier or DomainClassifier()
    
    def calculate_weighted_consensus(
        self,
        question: str,
        agent_responses: List[Dict],
        performance_metrics: Optional[Dict[str, float]] = None
    ) -> Dict:
        """
        Calculate consensus with domain-aware weighting.
        
        Args:
            question: The forecasting question
            agent_responses: List of agent responses with weights
            performance_metrics: Optional historical accuracy per agent
        
        Returns:
            Dict with consensus analysis and adjusted weights
        """
        # Classify question domain
        classification = self.classifier.classify(question)
        
        # Calculate domain relevance for each agent
        agent_relevance = self._calculate_agent_relevance(
            classification,
            [r["agent_name"] for r in agent_responses]
        )
        
        # Adjust weights based on domain relevance and performance
        adjusted_responses = []
        for response in agent_responses:
            agent_name = response["agent_name"]
            base_weight = response.get("weight", 1.0)
            
            # Domain relevance multiplier
            relevance_boost = agent_relevance.get(agent_name, 0.5)
            
            # Performance multiplier (if available)
            performance_boost = 1.0
            if performance_metrics and agent_name in performance_metrics:
                # Use historical accuracy as multiplier (0.5 - 1.5 range)
                accuracy = performance_metrics[agent_name]
                performance_boost = 0.5 + (accuracy * 1.0)
            
            # Calculate final weight
            adjusted_weight = base_weight * relevance_boost * performance_boost
            
            adjusted_responses.append({
                **response,
                "base_weight": base_weight,
                "relevance_boost": relevance_boost,
                "performance_boost": performance_boost,
                "adjusted_weight": adjusted_weight
            })
        
        # Sort by adjusted weight
        adjusted_responses.sort(key=lambda x: x["adjusted_weight"], reverse=True)
        
        # Calculate consensus confidence
        total_weight = sum(r["adjusted_weight"] for r in adjusted_responses)
        top_3_weight = sum(r["adjusted_weight"] for r in adjusted_responses[:3])
        consensus_strength = top_3_weight / total_weight if total_weight > 0 else 0.0
        
        return {
            "classification": {
                "primary_domain": classification.primary_domain,
                "confidence": classification.confidence,
                "secondary_domains": classification.secondary_domains
            },
            "adjusted_responses": adjusted_responses,
            "consensus_strength": consensus_strength,
            "total_weight": total_weight,
            "explanation": self._generate_explanation(classification, adjusted_responses)
        }
    
    def _calculate_agent_relevance(
        self,
        classification: DomainClassification,
        agent_names: List[str]
    ) -> Dict[str, float]:
        """Calculate domain relevance score for each agent."""
        relevance_scores = {}
        
        for agent_name in agent_names:
            expert_domains = DomainClassifier.EXPERT_DOMAINS.get(agent_name, [])
            
            if not expert_domains:
                # Chaos Agent or unknown - neutral relevance
                relevance_scores[agent_name] = 0.8
                continue
            
            # Check primary domain match
            if classification.primary_domain in expert_domains:
                relevance_scores[agent_name] = 1.5  # Strong boost
            # Check secondary domain match
            elif any(domain in expert_domains for domain, _ in classification.secondary_domains):
                relevance_scores[agent_name] = 1.2  # Moderate boost
            else:
                # Not directly relevant, but still included
                relevance_scores[agent_name] = 0.6  # Reduced weight
        
        return relevance_scores
    
    def _generate_explanation(
        self,
        classification: DomainClassification,
        adjusted_responses: List[Dict]
    ) -> str:
        """Generate human-readable explanation of weighting logic."""
        primary = classification.primary_domain
        
        # Find top weighted agents
        top_3 = adjusted_responses[:3]
        top_agents = [r["agent_name"] for r in top_3]
        
        explanation = f"Question classified as **{primary}** domain (confidence: {classification.confidence:.1%}). "
        
        if classification.secondary_domains:
            secondary = ", ".join([d for d, _ in classification.secondary_domains])
            explanation += f"Secondary domains: {secondary}. "
        
        explanation += f"\n\nTop weighted experts:\n"
        for i, resp in enumerate(top_3, 1):
            explanation += (
                f"{i}. **{resp['agent_name']}** "
                f"(weight: {resp['adjusted_weight']:.2f}, "
                f"relevance: {resp['relevance_boost']:.2f}x)\n"
            )
        
        return explanation
    
    def get_domain_specialists(
        self,
        domain: str,
        top_n: int = 5
    ) -> List[str]:
        """Get top N specialist agents for a domain."""
        specialists = []
        
        for agent_name, domains in DomainClassifier.EXPERT_DOMAINS.items():
            if domain in domains:
                specialists.append(agent_name)
        
        return specialists[:top_n]
