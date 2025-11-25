"""Specialized agent profiles for targeted analysis domains."""
from typing import Dict, List, Optional, Set
from dataclasses import dataclass
import re


@dataclass
class SpecializedAgent:
    """Specialized agent with domain expertise and keyword monitoring."""
    name: str
    role: str
    model: str
    weight: float
    keywords: List[str]
    domain: str
    priority_patterns: List[str]  # Regex patterns for high-priority detection
    
    def matches_content(self, text: str, threshold: int = 2) -> bool:
        """Check if content matches agent's domain expertise.
        
        Args:
            text: Text content to analyze
            threshold: Minimum keyword matches required
            
        Returns:
            True if content is relevant to this agent's domain
        """
        text_lower = text.lower()
        matches = sum(1 for keyword in self.keywords if keyword.lower() in text_lower)
        return matches >= threshold
    
    def detect_priority_signals(self, text: str) -> List[str]:
        """Detect high-priority patterns in content.
        
        Args:
            text: Text content to analyze
            
        Returns:
            List of matched priority patterns
        """
        matches = []
        for pattern in self.priority_patterns:
            if re.search(pattern, text, re.IGNORECASE):
                matches.append(pattern)
        return matches
    
    def calculate_relevance_score(self, text: str) -> float:
        """Calculate relevance score for content (0.0 - 1.0).
        
        Args:
            text: Text content to analyze
            
        Returns:
            Relevance score
        """
        text_lower = text.lower()
        
        # Base keyword matching (max 0.6)
        keyword_matches = sum(1 for kw in self.keywords if kw.lower() in text_lower)
        keyword_score = min(keyword_matches / len(self.keywords), 0.6)
        
        # Priority pattern matching (max 0.4)
        priority_matches = self.detect_priority_signals(text)
        priority_score = min(len(priority_matches) * 0.2, 0.4)
        
        return keyword_score + priority_score


# Specialized agent definitions
OSINT_FLIGHT_TRACKER = SpecializedAgent(
    name="🛩️ OSINT Flight Tracker",
    role=(
        "You are an OSINT analyst specializing in military flight pattern analysis. "
        "Monitor tanker deployments, carrier strike group movements, and strategic airlift operations. "
        "Detect anomalous military aviation activity that precedes major operations. "
        "Focus on: KC-135/KC-46 tanker deployments, P-8 Poseidon maritime patrol, "
        "E-3 AWACS orbits, strategic bomber movements (B-52/B-1/B-2), and carrier air wing repositioning. "
        "Correlate flight patterns with diplomatic events and threat escalation."
    ),
    model="gemma:2b",
    weight=1.3,
    keywords=[
        "tanker", "KC-135", "KC-46", "refueling", 
        "carrier strike group", "CSG", "carrier air wing",
        "P-8", "Poseidon", "maritime patrol", "anti-submarine",
        "AWACS", "E-3", "airborne early warning",
        "B-52", "B-1", "B-2", "strategic bomber",
        "C-17", "C-5", "strategic airlift", "heavy lift",
        "reconnaissance", "RC-135", "SIGINT",
        "exercise", "deployment", "sortie rate",
        "fighter escort", "F-35", "F-22", "F/A-18"
    ],
    domain="military/osint",
    priority_patterns=[
        r"carrier strike.*deployed",
        r"tanker.*unusual pattern",
        r"bomber.*forward deploy",
        r"AWACS.*sustained orbit",
        r"strategic airlift.*surge",
        r"(reconnaissance|SIGINT).*increase",
        r"exercise.*extended",
        r"sortie rate.*elevated"
    ]
)

BANKING_CRISIS_ANALYST = SpecializedAgent(
    name="🏦 Banking Crisis Analyst",
    role=(
        "You are a financial stability analyst specializing in regional banking stress and systemic risk. "
        "Monitor FDIC actions, deposit flight, liquidity crises, and contagion indicators. "
        "Focus on: regional bank mergers under duress, emergency Fed lending (discount window, BTFP), "
        "unrealized losses on held-to-maturity securities, commercial real estate exposure, "
        "deposit concentration risk, and interconnected counterparty exposures. "
        "Assess cascade risk from banking stress to credit markets and real economy."
    ),
    model="gemma:2b",
    weight=1.3,
    keywords=[
        "FDIC", "Federal Deposit Insurance", "bank failure",
        "liquidity crisis", "deposit flight", "bank run",
        "regional bank", "community bank", "state bank",
        "emergency lending", "discount window", "BTFP",
        "unrealized loss", "held-to-maturity", "HTM securities",
        "commercial real estate", "CRE", "office vacancy",
        "loan loss", "non-performing loan", "NPL",
        "capital adequacy", "Tier 1 capital", "stress test",
        "contagion", "systemic risk", "interconnected",
        "merger", "acquisition", "assisted transaction",
        "regulatory action", "consent order", "enforcement"
    ],
    domain="financial/banking",
    priority_patterns=[
        r"FDIC.*takeover",
        r"bank.*failure",
        r"emergency.*lending",
        r"deposit.*flight",
        r"liquidity.*crisis",
        r"regional bank.*merger",
        r"unrealized loss.*significant",
        r"CRE.*delinquency",
        r"stress test.*fail",
        r"systemic.*risk",
        r"contagion.*spread"
    ]
)

LOCAL_THREAT_MONITOR = SpecializedAgent(
    name="🚨 Local Threat Monitor (Virginia)",
    role=(
        "You are a local security analyst focused on Virginia threats and emergency response patterns. "
        "Monitor Midlothian, Richmond, Chesterfield, Henrico, and Colonial Heights for security incidents. "
        "Focus on: coordinated criminal activity, evacuation orders, hazmat incidents, "
        "active shooter situations, mass casualty events, civil disturbances, "
        "infrastructure failures (power, water, transportation), and suspicious activity patterns. "
        "Detect escalation indicators and cross-jurisdictional coordination that suggests major incidents."
    ),
    model="gemma:2b",
    weight=2.5,  # Higher weight for local relevance
    keywords=[
        "Richmond", "Midlothian", "Chesterfield", "Henrico", "Colonial Heights",
        "evacuation", "shelter in place", "lockdown",
        "active shooter", "shots fired", "armed suspect",
        "hazmat", "hazardous material", "chemical spill",
        "mass casualty", "multiple victims", "triage",
        "civil disturbance", "riot", "protest", "unrest",
        "infrastructure", "power outage", "water main",
        "suspicious package", "bomb threat", "explosive",
        "multi-alarm", "mutual aid", "all hands",
        "officer safety", "officer down", "backup requested",
        "tactical", "SWAT", "hostage", "barricade"
    ],
    domain="local/virginia",
    priority_patterns=[
        r"evacuation.*order",
        r"active shooter",
        r"mass casualty",
        r"hazmat.*emergency",
        r"multiple.*jurisdictions",
        r"all hands",
        r"officer down",
        r"SWAT.*deployed",
        r"shelter.*place",
        r"infrastructure.*failure",
        r"coordinated.*attack"
    ]
)


def get_specialized_agents() -> List[SpecializedAgent]:
    """Get all specialized agent profiles.
    
    Returns:
        List of specialized agents
    """
    return [
        OSINT_FLIGHT_TRACKER,
        BANKING_CRISIS_ANALYST,
        LOCAL_THREAT_MONITOR
    ]


def filter_agents_by_content(
    content: str,
    agents: Optional[List[SpecializedAgent]] = None,
    min_relevance: float = 0.3
) -> List[SpecializedAgent]:
    """Filter specialized agents based on content relevance.
    
    Args:
        content: Content to analyze
        agents: List of agents to filter (defaults to all specialized agents)
        min_relevance: Minimum relevance score threshold
        
    Returns:
        List of relevant agents sorted by relevance score
    """
    if agents is None:
        agents = get_specialized_agents()
    
    relevant = []
    for agent in agents:
        score = agent.calculate_relevance_score(content)
        if score >= min_relevance:
            relevant.append((agent, score))
    
    # Sort by relevance score descending
    relevant.sort(key=lambda x: x[1], reverse=True)
    return [agent for agent, _ in relevant]


def get_agent_by_domain(domain: str) -> Optional[SpecializedAgent]:
    """Get specialized agent for a specific domain.
    
    Args:
        domain: Domain identifier
        
    Returns:
        Specialized agent or None if not found
    """
    agents = get_specialized_agents()
    for agent in agents:
        if agent.domain == domain:
            return agent
    return None


__all__ = [
    'SpecializedAgent',
    'OSINT_FLIGHT_TRACKER',
    'BANKING_CRISIS_ANALYST',
    'LOCAL_THREAT_MONITOR',
    'get_specialized_agents',
    'filter_agents_by_content',
    'get_agent_by_domain'
]
