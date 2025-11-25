"""Cascade modeling to analyze how events in one domain affect others.

This module tracks multi-domain event cascades like:
- Military action → Oil prices → Banking stress → Commercial real estate opportunities
- Natural disaster → Supply chain → Inflation → Monetary policy
- Cyber attack → Infrastructure → Economic disruption → Political instability
"""
from typing import Dict, List, Optional, Tuple, Set
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
import json


class CascadeStage(Enum):
    """Stages of a cascade event sequence."""
    TRIGGER = "trigger"  # Initial event
    PRIMARY = "primary"  # Direct first-order effects
    SECONDARY = "secondary"  # Second-order effects
    TERTIARY = "tertiary"  # Third-order effects
    TERMINAL = "terminal"  # Final outcome/stabilization


@dataclass
class CascadeNode:
    """Node in a cascade event graph."""
    domain: str
    event_type: str
    description: str
    probability: float
    confidence: float
    stage: CascadeStage
    timestamp: datetime
    indicators: List[str] = field(default_factory=list)
    

@dataclass
class CascadeEdge:
    """Edge connecting cascade nodes (cause -> effect relationship)."""
    source_domain: str
    target_domain: str
    mechanism: str  # How source affects target
    lag_time: timedelta  # Expected delay
    probability: float  # Probability of transmission
    confidence: float  # Confidence in the relationship


@dataclass
class CascadePathway:
    """Complete cascade pathway from trigger to terminal state."""
    pathway_id: str
    trigger_event: str
    nodes: List[CascadeNode]
    edges: List[CascadeEdge]
    overall_probability: float
    total_lag_time: timedelta
    detection_confidence: float
    

# Predefined cascade relationships
CASCADE_RELATIONSHIPS = {
    # Military action cascades
    ("military", "energy"): CascadeEdge(
        source_domain="military",
        target_domain="energy",
        mechanism="Carrier deployment/bomber forward basing → Oil supply uncertainty → Price spike",
        lag_time=timedelta(hours=6),
        probability=0.75,
        confidence=0.85
    ),
    ("military", "financial"): CascadeEdge(
        source_domain="military",
        target_domain="financial",
        mechanism="Military escalation → Flight to safety → Treasury yields down, gold up",
        lag_time=timedelta(hours=2),
        probability=0.80,
        confidence=0.90
    ),
    
    # Energy price cascades
    ("energy", "financial"): CascadeEdge(
        source_domain="energy",
        target_domain="financial",
        mechanism="Oil price spike → Inflation expectations → Fed policy tightening fears",
        lag_time=timedelta(days=2),
        probability=0.70,
        confidence=0.85
    ),
    ("energy", "banking"): CascadeEdge(
        source_domain="energy",
        target_domain="banking",
        mechanism="Energy price shock → Corporate loan stress → Bank credit quality deterioration",
        lag_time=timedelta(days=7),
        probability=0.60,
        confidence=0.75
    ),
    
    # Banking stress cascades
    ("banking", "real_estate"): CascadeEdge(
        source_domain="banking",
        target_domain="real_estate",
        mechanism="Bank liquidity crisis → Lending freeze → CRE distressed asset opportunities",
        lag_time=timedelta(days=14),
        probability=0.65,
        confidence=0.80
    ),
    ("banking", "credit_markets"): CascadeEdge(
        source_domain="banking",
        target_domain="credit_markets",
        mechanism="Regional bank failure → Credit spreads widen → Corporate debt refinancing crisis",
        lag_time=timedelta(days=3),
        probability=0.75,
        confidence=0.85
    ),
    
    # Real estate cascades
    ("real_estate", "local_economy"): CascadeEdge(
        source_domain="real_estate",
        target_domain="local_economy",
        mechanism="CRE vacancy surge → Local tax revenue decline → Municipal service cuts",
        lag_time=timedelta(days=90),
        probability=0.55,
        confidence=0.70
    ),
    
    # Cyber attack cascades
    ("cyber", "infrastructure"): CascadeEdge(
        source_domain="cyber",
        target_domain="infrastructure",
        mechanism="Cyber attack → Power/water/transport disruption → Economic activity halt",
        lag_time=timedelta(hours=12),
        probability=0.70,
        confidence=0.80
    ),
    ("infrastructure", "local_security"): CascadeEdge(
        source_domain="infrastructure",
        target_domain="local_security",
        mechanism="Infrastructure failure → Civil order breakdown → Emergency services overwhelmed",
        lag_time=timedelta(days=2),
        probability=0.60,
        confidence=0.75
    ),
    
    # Supply chain cascades
    ("supply_chain", "inflation"): CascadeEdge(
        source_domain="supply_chain",
        target_domain="inflation",
        mechanism="Logistics disruption → Goods scarcity → Price pressures",
        lag_time=timedelta(days=14),
        probability=0.70,
        confidence=0.85
    ),
    ("inflation", "monetary_policy"): CascadeEdge(
        source_domain="inflation",
        target_domain="monetary_policy",
        mechanism="Persistent inflation → Fed rate hikes → Economic slowdown",
        lag_time=timedelta(days=45),
        probability=0.75,
        confidence=0.90
    ),
}


class CascadeAnalyzer:
    """Analyze event cascades across multiple domains."""
    
    def __init__(self):
        self.relationships = CASCADE_RELATIONSHIPS.copy()
        self.active_cascades: List[CascadePathway] = []
    
    def add_custom_relationship(self, edge: CascadeEdge) -> None:
        """Add a custom cascade relationship.
        
        Args:
            edge: Custom cascade edge definition
        """
        key = (edge.source_domain, edge.target_domain)
        self.relationships[key] = edge
    
    def analyze_cascades(
        self,
        trigger_domain: str,
        trigger_event: str,
        max_depth: int = 4,
        min_probability: float = 0.3
    ) -> List[CascadePathway]:
        """Analyze potential cascades from a trigger event.
        
        Args:
            trigger_domain: Domain of the triggering event
            trigger_event: Description of the triggering event
            max_depth: Maximum cascade depth to explore
            min_probability: Minimum pathway probability threshold
            
        Returns:
            List of identified cascade pathways
        """
        pathways = []
        
        # Start with trigger node
        trigger_node = CascadeNode(
            domain=trigger_domain,
            event_type="trigger",
            description=trigger_event,
            probability=1.0,
            confidence=0.90,
            stage=CascadeStage.TRIGGER,
            timestamp=datetime.utcnow()
        )
        
        # Explore cascades via BFS
        self._explore_cascade_paths(
            current_node=trigger_node,
            pathway_nodes=[trigger_node],
            pathway_edges=[],
            depth=0,
            max_depth=max_depth,
            min_probability=min_probability,
            pathways=pathways,
            visited=set()
        )
        
        # Sort by probability
        pathways.sort(key=lambda p: p.overall_probability, reverse=True)
        
        return pathways
    
    def _explore_cascade_paths(
        self,
        current_node: CascadeNode,
        pathway_nodes: List[CascadeNode],
        pathway_edges: List[CascadeEdge],
        depth: int,
        max_depth: int,
        min_probability: float,
        pathways: List[CascadePathway],
        visited: Set[str]
    ) -> None:
        """Recursively explore cascade pathways.
        
        Args:
            current_node: Current node in the cascade
            pathway_nodes: Nodes accumulated so far
            pathway_edges: Edges accumulated so far
            depth: Current depth
            max_depth: Maximum depth to explore
            min_probability: Minimum probability threshold
            pathways: List to accumulate complete pathways
            visited: Set of visited domains to avoid cycles
        """
        if depth >= max_depth:
            return
        
        # Mark current domain as visited
        visited.add(current_node.domain)
        
        # Find outgoing edges from current domain
        outgoing_edges = [
            (target_domain, edge)
            for (source, target_domain), edge in self.relationships.items()
            if source == current_node.domain and target_domain not in visited
        ]
        
        if not outgoing_edges:
            # Terminal node reached - save pathway if probability acceptable
            overall_prob = self._calculate_pathway_probability(pathway_edges)
            if overall_prob >= min_probability:
                total_lag = sum((e.lag_time for e in pathway_edges), timedelta())
                avg_confidence = sum(n.confidence for n in pathway_nodes) / len(pathway_nodes)
                
                pathway = CascadePathway(
                    pathway_id=f"cascade_{datetime.utcnow().timestamp()}",
                    trigger_event=pathway_nodes[0].description,
                    nodes=pathway_nodes.copy(),
                    edges=pathway_edges.copy(),
                    overall_probability=overall_prob,
                    total_lag_time=total_lag,
                    detection_confidence=avg_confidence
                )
                pathways.append(pathway)
            return
        
        # Explore each outgoing edge
        for target_domain, edge in outgoing_edges:
            # Create next node
            stage_map = {
                0: CascadeStage.PRIMARY,
                1: CascadeStage.SECONDARY,
                2: CascadeStage.TERTIARY,
            }
            next_stage = stage_map.get(depth, CascadeStage.TERMINAL)
            
            next_node = CascadeNode(
                domain=target_domain,
                event_type=f"{edge.mechanism.split('→')[1].strip()}",
                description=edge.mechanism,
                probability=edge.probability,
                confidence=edge.confidence,
                stage=next_stage,
                timestamp=datetime.utcnow() + edge.lag_time
            )
            
            # Recurse
            self._explore_cascade_paths(
                current_node=next_node,
                pathway_nodes=pathway_nodes + [next_node],
                pathway_edges=pathway_edges + [edge],
                depth=depth + 1,
                max_depth=max_depth,
                min_probability=min_probability,
                pathways=pathways,
                visited=visited.copy()
            )
    
    def _calculate_pathway_probability(self, edges: List[CascadeEdge]) -> float:
        """Calculate overall probability of a cascade pathway.
        
        Args:
            edges: List of edges in the pathway
            
        Returns:
            Overall probability (product of edge probabilities)
        """
        if not edges:
            return 1.0
        
        prob = 1.0
        for edge in edges:
            prob *= edge.probability
        
        return prob
    
    def get_critical_cascades(
        self,
        pathways: List[CascadePathway],
        min_probability: float = 0.4,
        max_lag_days: int = 30
    ) -> List[CascadePathway]:
        """Filter for critical high-probability, near-term cascades.
        
        Args:
            pathways: List of cascade pathways
            min_probability: Minimum probability threshold
            max_lag_days: Maximum lag time in days
            
        Returns:
            Filtered list of critical cascades
        """
        critical = []
        for pathway in pathways:
            if (pathway.overall_probability >= min_probability and
                pathway.total_lag_time <= timedelta(days=max_lag_days)):
                critical.append(pathway)
        
        return critical
    
    def format_cascade_report(self, pathway: CascadePathway) -> str:
        """Format a cascade pathway as a readable report.
        
        Args:
            pathway: Cascade pathway to format
            
        Returns:
            Formatted report string
        """
        report = []
        report.append(f"=== CASCADE ANALYSIS ===")
        report.append(f"Trigger: {pathway.trigger_event}")
        report.append(f"Overall Probability: {pathway.overall_probability:.1%}")
        report.append(f"Total Lag Time: {pathway.total_lag_time.days} days")
        report.append(f"Detection Confidence: {pathway.detection_confidence:.1%}")
        report.append("")
        report.append("Cascade Sequence:")
        
        for i, (node, edge) in enumerate(zip(pathway.nodes[:-1], pathway.edges), 1):
            report.append(f"\n{i}. {node.domain.upper()} [{node.stage.value}]")
            report.append(f"   Event: {node.description}")
            report.append(f"   Probability: {node.probability:.1%}")
            report.append(f"   ↓")
            report.append(f"   {edge.mechanism}")
            report.append(f"   Lag: {edge.lag_time.days}d {edge.lag_time.seconds//3600}h")
        
        # Terminal node
        terminal = pathway.nodes[-1]
        report.append(f"\n{len(pathway.nodes)}. {terminal.domain.upper()} [{terminal.stage.value}]")
        report.append(f"   Outcome: {terminal.description}")
        report.append(f"   Probability: {terminal.probability:.1%}")
        
        return "\n".join(report)


def analyze_event_cascade(
    trigger_domain: str,
    trigger_event: str,
    max_depth: int = 3,
    min_probability: float = 0.3
) -> Dict[str, any]:
    """Convenience function to analyze cascades from an event.
    
    Args:
        trigger_domain: Domain of triggering event
        trigger_event: Description of trigger
        max_depth: Maximum cascade depth
        min_probability: Minimum probability threshold
        
    Returns:
        Dictionary with cascade analysis results
    """
    analyzer = CascadeAnalyzer()
    pathways = analyzer.analyze_cascades(
        trigger_domain=trigger_domain,
        trigger_event=trigger_event,
        max_depth=max_depth,
        min_probability=min_probability
    )
    
    critical = analyzer.get_critical_cascades(pathways)
    
    return {
        "trigger": trigger_event,
        "total_pathways": len(pathways),
        "critical_pathways": len(critical),
        "pathways": pathways,
        "critical": critical,
        "reports": [analyzer.format_cascade_report(p) for p in critical]
    }


__all__ = [
    'CascadeStage',
    'CascadeNode',
    'CascadeEdge',
    'CascadePathway',
    'CascadeAnalyzer',
    'CASCADE_RELATIONSHIPS',
    'analyze_event_cascade'
]
