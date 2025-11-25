"""Meta-Analyst Quality Control System for Agent Responses.

Ensures agents provide deep, evidence-based analysis rather than surface-level responses.
Reviews all agent outputs, identifies weak analysis, and re-queries with follow-up questions.
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple
from datetime import datetime

from forecasting.config import get_logger

logger = get_logger()


@dataclass
class AnalysisQualityScore:
    """Quality assessment of an agent's analysis."""
    
    agent_name: str
    depth_score: float  # 0.0-1.0
    evidence_based: float  # 0.0-1.0 - Uses specific data, citations, numbers
    causal_reasoning: float  # 0.0-1.0 - Explains mechanisms and causation
    uncertainty_handling: float  # 0.0-1.0 - Acknowledges limitations and uncertainty
    counterarguments: float  # 0.0-1.0 - Considers alternative viewpoints
    specifics: float  # 0.0-1.0 - Provides specific details vs vague statements
    temporal_reasoning: float  # 0.0-1.0 - Considers timelines and sequences
    red_flags: List[str]  # Indicators of superficial analysis
    needs_requery: bool
    follow_up_questions: List[str]
    
    def __str__(self) -> str:
        """Human-readable quality report."""
        status = "🔴 NEEDS REQUERY" if self.needs_requery else "✅ ACCEPTABLE"
        lines = [
            f"Agent: {self.agent_name}",
            f"Status: {status}",
            f"Overall Depth Score: {self.depth_score:.2f}",
            "",
            "Quality Breakdown:",
            f"  Evidence-Based: {self.evidence_based:.2f}",
            f"  Causal Reasoning: {self.causal_reasoning:.2f}",
            f"  Uncertainty: {self.uncertainty_handling:.2f}",
            f"  Counterarguments: {self.counterarguments:.2f}",
            f"  Specificity: {self.specifics:.2f}",
            f"  Temporal Reasoning: {self.temporal_reasoning:.2f}",
        ]
        
        if self.red_flags:
            lines.append("")
            lines.append("⚠️ Red Flags:")
            for flag in self.red_flags:
                lines.append(f"  • {flag}")
        
        if self.follow_up_questions:
            lines.append("")
            lines.append("📋 Follow-up Questions:")
            for i, q in enumerate(self.follow_up_questions, 1):
                lines.append(f"  {i}. {q}")
        
        return "\n".join(lines)


class MetaAnalystAgent:
    """Supervises agent responses to ensure analytical depth and quality."""
    
    # Quality assessment weights
    DEPTH_WEIGHTS = {
        "evidence_based": 0.25,
        "causal_reasoning": 0.20,
        "uncertainty_handling": 0.15,
        "counterarguments": 0.15,
        "specifics": 0.15,
        "temporal_reasoning": 0.10,
    }
    
    # Indicators of high-quality analysis
    DEPTH_INDICATORS = {
        "evidence_based": [
            r"\d+\.?\d*%",  # Percentages
            r"\$\d+",  # Dollar amounts
            r"\d{4}-\d{2}-\d{2}",  # Dates
            r"according to",
            r"data shows",
            r"reported",
            r"measured",
            r"observed",
            r"historically",
            r"statistics indicate",
        ],
        "causal_reasoning": [
            r"because",
            r"therefore",
            r"as a result",
            r"leads to",
            r"causes",
            r"due to",
            r"consequently",
            r"mechanism",
            r"pathway",
            r"triggers",
            r"drives",
        ],
        "uncertainty_handling": [
            r"uncertainty",
            r"unclear",
            r"unknown",
            r"may",
            r"might",
            r"could",
            r"possibly",
            r"potentially",
            r"difficult to predict",
            r"range of outcomes",
            r"depends on",
        ],
        "counterarguments": [
            r"however",
            r"although",
            r"alternatively",
            r"on the other hand",
            r"conversely",
            r"but",
            r"yet",
            r"despite",
            r"counterpoint",
            r"opposing view",
        ],
        "specifics": [
            r"\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)+\b",  # Proper nouns (names, places)
            r"\d+",  # Any numbers
            r"specifically",
            r"in particular",
            r"namely",
            r"for example",
            r"such as",
        ],
        "temporal_reasoning": [
            r"\d{4}",  # Years
            r"timeline",
            r"timeframe",
            r"within \d+",
            r"by \d{4}",
            r"after",
            r"before",
            r"during",
            r"sequence",
            r"progression",
            r"phases",
        ],
    }
    
    # Red flags for superficial analysis
    SUPERFICIAL_INDICATORS = [
        (r"^.{0,150}$", "Response too short (<150 chars)"),
        (r"^(yes|no|maybe|unclear|unknown)\.?$", "One-word answer"),
        (r"it depends", "Vague cop-out without specifics"),
        (r"(difficult|hard|impossible) to (say|predict|determine)", "Dismissive without analysis"),
        (r"(generally|usually|often|sometimes)", "Overgeneralization without evidence"),
        (r"need more (information|data|context)", "Deflection without using available context"),
    ]
    
    def __init__(self, requery_threshold: float = 0.6, max_follow_ups: int = 3):
        """Initialize meta-analyst.
        
        Args:
            requery_threshold: Minimum depth score to accept without requery (0.0-1.0)
            max_follow_ups: Maximum follow-up questions to generate per agent
        """
        self.requery_threshold = requery_threshold
        self.max_follow_ups = max_follow_ups
    
    def assess_analysis_quality(
        self,
        agent_name: str,
        raw_response: str,
        parsed_response: Optional[Dict],
        question: str,
        context: str,
    ) -> AnalysisQualityScore:
        """Assess the quality of an agent's analysis.
        
        Args:
            agent_name: Name of the agent
            raw_response: Raw text response from agent
            parsed_response: Parsed JSON response (if available)
            question: Original forecasting question
            context: Context provided to agent
        
        Returns:
            Quality assessment with depth score and recommendations
        """
        # Extract analysis text
        analysis_text = ""
        if parsed_response and isinstance(parsed_response, dict):
            analysis_text = parsed_response.get("analysis", "")
            if not analysis_text:
                analysis_text = parsed_response.get("recommendation", "")
        if not analysis_text:
            analysis_text = raw_response
        
        # Calculate quality scores for each dimension
        scores = {}
        for dimension, patterns in self.DEPTH_INDICATORS.items():
            count = 0
            for pattern in patterns:
                count += len(re.findall(pattern, analysis_text, re.IGNORECASE))
            
            # Normalize to 0.0-1.0 (diminishing returns after 5 indicators)
            scores[dimension] = min(1.0, count / 5.0)
        
        # Detect red flags
        red_flags = []
        for pattern, description in self.SUPERFICIAL_INDICATORS:
            if re.search(pattern, analysis_text.strip(), re.IGNORECASE):
                red_flags.append(description)
        
        # Calculate weighted depth score
        depth_score = sum(
            scores[dim] * weight for dim, weight in self.DEPTH_WEIGHTS.items()
        )
        
        # Apply penalty for red flags
        penalty = min(0.3, len(red_flags) * 0.1)
        depth_score = max(0.0, depth_score - penalty)
        
        # Determine if requery is needed
        needs_requery = depth_score < self.requery_threshold or len(red_flags) >= 2
        
        # Generate follow-up questions if needed
        follow_up_questions = []
        if needs_requery:
            follow_up_questions = self._generate_follow_ups(
                agent_name, analysis_text, scores, red_flags, question, context
            )
        
        return AnalysisQualityScore(
            agent_name=agent_name,
            depth_score=depth_score,
            evidence_based=scores["evidence_based"],
            causal_reasoning=scores["causal_reasoning"],
            uncertainty_handling=scores["uncertainty_handling"],
            counterarguments=scores["counterarguments"],
            specifics=scores["specifics"],
            temporal_reasoning=scores["temporal_reasoning"],
            red_flags=red_flags,
            needs_requery=needs_requery,
            follow_up_questions=follow_up_questions[:self.max_follow_ups],
        )
    
    def _generate_follow_ups(
        self,
        agent_name: str,
        analysis_text: str,
        scores: Dict[str, float],
        red_flags: List[str],
        question: str,
        context: str,
    ) -> List[str]:
        """Generate targeted follow-up questions based on quality gaps.
        
        Args:
            agent_name: Name of the agent
            analysis_text: Agent's analysis text
            scores: Quality scores for each dimension
            red_flags: Detected red flags
            question: Original question
            context: Available context
        
        Returns:
            List of follow-up questions targeting weak areas
        """
        follow_ups = []
        
        # Target weakest dimensions
        weak_dimensions = sorted(scores.items(), key=lambda x: x[1])[:3]
        
        for dimension, score in weak_dimensions:
            if score < 0.4:  # Significantly weak
                if dimension == "evidence_based":
                    follow_ups.append(
                        f"What specific data, numbers, or historical precedents support your analysis of {question[:60]}?"
                    )
                elif dimension == "causal_reasoning":
                    follow_ups.append(
                        f"Explain the causal mechanisms: HOW and WHY would this outcome occur? What are the intermediate steps?"
                    )
                elif dimension == "uncertainty_handling":
                    follow_ups.append(
                        f"What are the key uncertainties and unknown factors that could change your prediction?"
                    )
                elif dimension == "counterarguments":
                    follow_ups.append(
                        f"What evidence or arguments would CONTRADICT your assessment? Why might you be wrong?"
                    )
                elif dimension == "specifics":
                    follow_ups.append(
                        f"Provide specific names, places, dates, or quantitative details rather than general statements."
                    )
                elif dimension == "temporal_reasoning":
                    follow_ups.append(
                        f"What is the expected timeline? What would happen first, second, third? How long would each phase take?"
                    )
        
        # Address specific red flags
        if any("too short" in flag.lower() for flag in red_flags):
            follow_ups.append(
                f"Expand your analysis with more depth. Your response was too brief to properly assess {question[:60]}."
            )
        
        if any("vague" in flag.lower() or "general" in flag.lower() for flag in red_flags):
            follow_ups.append(
                "Avoid vague statements. Use the provided context to give concrete, specific analysis with evidence."
            )
        
        return follow_ups
    
    def requery_agent(
        self,
        agent: Dict,
        original_question: str,
        context: str,
        quality_score: AnalysisQualityScore,
        call_model_fn,
        ollama_cfg: Dict,
    ) -> Tuple[str, Optional[Dict]]:
        """Re-query an agent with follow-up questions for deeper analysis.
        
        Args:
            agent: Agent configuration dict
            original_question: Original forecasting question
            context: Context provided to agent
            quality_score: Quality assessment with follow-up questions
            call_model_fn: Function to call the model
            ollama_cfg: Ollama configuration
        
        Returns:
            Tuple of (raw_response, parsed_response) from requery
        """
        # Build enhanced prompt with quality feedback
        follow_ups_text = "\n".join(
            f"   {i}. {q}" for i, q in enumerate(quality_score.follow_up_questions, 1)
        )
        
        requery_prompt = f"""Your previous analysis lacked sufficient depth and detail. 

You MUST address these specific follow-up questions with concrete evidence and reasoning:

{follow_ups_text}

Original Question: {original_question}

Your Role: {agent['role']}

Available Context:
{context[:3000]}

Provide a COMPREHENSIVE, EVIDENCE-BASED response with:
- Specific data, numbers, dates, and citations
- Clear causal reasoning explaining HOW and WHY
- Acknowledgment of uncertainties and alternative viewpoints
- Concrete details and timelines

Respond with JSON:
{{
    "analysis": "Detailed analysis addressing all follow-up questions",
    "probability": 0.0-1.0,
    "confidence": 0.0-1.0,
    "recommendation": "Specific actionable insights"
}}"""
        
        try:
            logger.info(f"Re-querying {quality_score.agent_name} with {len(quality_score.follow_up_questions)} follow-ups")
            raw = call_model_fn(requery_prompt, agent.get("model"), ollama_cfg, timeout=60)
            
            # Try to extract JSON
            parsed = None
            try:
                # Look for JSON block in response
                json_match = re.search(r'\{.*\}', raw, re.DOTALL)
                if json_match:
                    parsed = json.loads(json_match.group())
            except json.JSONDecodeError:
                pass
            
            return raw, parsed
        
        except Exception as e:
            logger.error(f"Requery failed for {quality_score.agent_name}: {e}")
            return f"REQUERY_ERROR: {str(e)}", None
    
    def review_all_agents(
        self,
        agent_outputs: List[Dict],
        question: str,
        context: str,
    ) -> Dict[str, AnalysisQualityScore]:
        """Review quality of all agent responses.
        
        Args:
            agent_outputs: List of agent output dicts with 'agent', 'raw', 'parsed' keys
            question: Original forecasting question
            context: Context provided to agents
        
        Returns:
            Dict mapping agent name to quality score
        """
        quality_scores = {}
        
        for agent_output in agent_outputs:
            # Skip declined agents
            if agent_output.get("declined"):
                continue
            
            agent_name = agent_output.get("agent", "Unknown")
            raw_response = agent_output.get("raw", "")
            parsed_response = agent_output.get("parsed")
            
            score = self.assess_analysis_quality(
                agent_name=agent_name,
                raw_response=raw_response,
                parsed_response=parsed_response,
                question=question,
                context=context,
            )
            
            quality_scores[agent_name] = score
            
            if score.needs_requery:
                logger.warning(
                    f"Agent {agent_name} needs requery - Depth score: {score.depth_score:.2f}, "
                    f"Red flags: {len(score.red_flags)}"
                )
            else:
                logger.info(f"Agent {agent_name} passed quality check - Depth score: {score.depth_score:.2f}")
        
        return quality_scores
    
    def get_quality_summary(self, quality_scores: Dict[str, AnalysisQualityScore]) -> Dict:
        """Generate summary statistics for all agent quality scores.
        
        Args:
            quality_scores: Dict mapping agent name to quality score
        
        Returns:
            Summary statistics dict
        """
        if not quality_scores:
            return {
                "total_agents": 0,
                "agents_passed": 0,
                "agents_need_requery": 0,
                "avg_depth_score": 0.0,
                "min_depth_score": 0.0,
                "max_depth_score": 0.0,
            }
        
        scores = [qs.depth_score for qs in quality_scores.values()]
        needs_requery = [qs for qs in quality_scores.values() if qs.needs_requery]
        
        return {
            "total_agents": len(quality_scores),
            "agents_passed": len(quality_scores) - len(needs_requery),
            "agents_need_requery": len(needs_requery),
            "avg_depth_score": sum(scores) / len(scores),
            "min_depth_score": min(scores),
            "max_depth_score": max(scores),
            "requery_percentage": len(needs_requery) / len(quality_scores) if quality_scores else 0,
            "weakest_agents": [qs.agent_name for qs in sorted(quality_scores.values(), key=lambda x: x.depth_score)[:3]],
        }
