"""
Article Pre-filtering System

Uses gemma3:1b to intelligently filter articles for relevance before passing
them to specialized agents. This reduces computational load and improves
response quality by ensuring agents only see truly relevant content.
"""

import logging
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass
import re

logger = logging.getLogger(__name__)


@dataclass
class FilteredArticle:
    """Article with relevance scoring"""
    article_id: str
    title: str
    text: str
    relevance_score: float  # 0.0 to 1.0
    relevance_reasoning: str
    keywords_matched: List[str]
    source_url: str = ""
    published: str = ""


class ArticlePreFilter:
    """Pre-filters articles using gemma3:1b for relevance assessment"""
    
    def __init__(self, ollama_url: str = "http://192.168.1.140:11434", 
                 filter_model: str = "gemma2:2b"):
        self.ollama_url = ollama_url
        self.filter_model = filter_model
        self.min_relevance_threshold = 0.3  # Default threshold
    
    def filter_articles_for_question(self, 
                                    question: str,
                                    articles: List[Dict],
                                    min_relevance: float = 0.3,
                                    max_articles: int = 20) -> List[FilteredArticle]:
        """
        Filter articles for relevance to a specific question using gemma3:1b
        
        Args:
            question: The forecasting question
            articles: List of article dicts with 'id', 'title', 'text' keys
            min_relevance: Minimum relevance score (0.0-1.0) to include
            max_articles: Maximum number of articles to return
            
        Returns:
            List of FilteredArticle objects sorted by relevance (highest first)
        """
        from src.forecasting.ollama_simple import call_ollama_simple
        
        filtered = []
        
        logger.info(f"Pre-filtering {len(articles)} articles with {self.filter_model}")
        
        for article in articles:
            try:
                # Build relevance assessment prompt
                prompt = self._build_relevance_prompt(question, article)
                
                # Call gemma2:2b for relevance assessment
                host = self.ollama_url.replace("http://", "").split(":")[0]
                response = call_ollama_simple(
                    model=self.filter_model,
                    prompt=prompt,
                    host=host,
                    port=11434,
                    timeout=30
                )
                
                # Parse relevance score and reasoning
                score, reasoning, keywords = self._parse_relevance_response(response)
                
                if score >= min_relevance:
                    filtered.append(FilteredArticle(
                        article_id=article.get('id', ''),
                        title=article.get('title', ''),
                        text=article.get('text', ''),
                        relevance_score=score,
                        relevance_reasoning=reasoning,
                        keywords_matched=keywords,
                        source_url=article.get('source_url', ''),
                        published=article.get('published', '')
                    ))
                    
            except Exception as e:
                logger.warning(f"Failed to filter article {article.get('id', 'unknown')}: {e}")
                # Include article with low score if filtering fails
                filtered.append(FilteredArticle(
                    article_id=article.get('id', ''),
                    title=article.get('title', ''),
                    text=article.get('text', ''),
                    relevance_score=0.5,  # Default medium relevance
                    relevance_reasoning="Filtering failed, included by default",
                    keywords_matched=[],
                    source_url=article.get('source_url', ''),
                    published=article.get('published', '')
                ))
        
        # Sort by relevance score (highest first)
        filtered.sort(key=lambda x: x.relevance_score, reverse=True)
        
        # Limit to max_articles
        filtered = filtered[:max_articles]
        
        logger.info(f"Filtered to {len(filtered)} relevant articles (min_relevance={min_relevance})")
        
        return filtered
    
    def _build_relevance_prompt(self, question: str, article: Dict) -> str:
        """Build prompt for relevance assessment"""
        
        # Extract key entities from question
        title = article.get('title', '')
        text_snippet = article.get('text', '')[:500]  # First 500 chars
        
        prompt = f"""Assess the relevance of this article to the forecasting question.

QUESTION: {question}

ARTICLE TITLE: {title}

ARTICLE EXCERPT: {text_snippet}

Provide your assessment in this exact format:
RELEVANCE_SCORE: X.XX (0.0 = not relevant, 1.0 = highly relevant)
KEYWORDS: keyword1, keyword2, keyword3 (key terms that match the question)
REASONING: Brief explanation of relevance

Be strict - only score highly (>0.7) if the article directly addresses the question's topic."""
        
        return prompt
    
    def _parse_relevance_response(self, response: str) -> Tuple[float, str, List[str]]:
        """Parse relevance score, reasoning, and keywords from model response"""
        
        score = 0.5  # Default medium relevance
        reasoning = "Unable to parse response"
        keywords = []
        
        try:
            # Extract relevance score
            score_match = re.search(r'RELEVANCE_SCORE:\s*([0-9.]+)', response, re.IGNORECASE)
            if score_match:
                score = float(score_match.group(1))
                score = max(0.0, min(1.0, score))  # Clamp to [0, 1]
            
            # Extract keywords
            keywords_match = re.search(r'KEYWORDS:\s*([^\n]+)', response, re.IGNORECASE)
            if keywords_match:
                keywords_str = keywords_match.group(1).strip()
                keywords = [k.strip() for k in keywords_str.split(',') if k.strip()]
            
            # Extract reasoning
            reasoning_match = re.search(r'REASONING:\s*([^\n]+(?:\n(?!RELEVANCE_SCORE|KEYWORDS)[^\n]+)*)', 
                                       response, re.IGNORECASE)
            if reasoning_match:
                reasoning = reasoning_match.group(1).strip()
        
        except Exception as e:
            logger.warning(f"Failed to parse relevance response: {e}")
        
        return score, reasoning, keywords
    
    def filter_articles_by_agent_domain(self,
                                       articles: List[Dict],
                                       agent_domain: str,
                                       min_relevance: float = 0.4) -> List[FilteredArticle]:
        """
        Filter articles relevant to a specific agent's domain of expertise
        
        Args:
            articles: List of article dicts
            agent_domain: Domain like 'military', 'financial', 'technology', etc.
            min_relevance: Minimum relevance threshold
            
        Returns:
            Filtered articles relevant to the domain
        """
        from src.forecasting.ollama_simple import call_ollama_simple
        
        domain_keywords = {
            'military': ['military', 'defense', 'army', 'navy', 'air force', 'weapons', 'conflict', 'war', 'deployment'],
            'financial': ['bank', 'finance', 'market', 'stock', 'economy', 'credit', 'debt', 'interest rate'],
            'technology': ['tech', 'cyber', 'software', 'hardware', 'semiconductor', 'AI', 'computer', 'network'],
            'energy': ['oil', 'gas', 'energy', 'power', 'electricity', 'renewable', 'coal', 'nuclear'],
            'health': ['health', 'medical', 'disease', 'pandemic', 'vaccine', 'hospital', 'patient'],
            'local': ['Richmond', 'Virginia', 'Chesterfield', 'local', 'county', 'municipality'],
        }
        
        filtered = []
        
        for article in articles:
            try:
                # Quick keyword check first (fast filter)
                text_lower = (article.get('title', '') + ' ' + article.get('text', '')).lower()
                keywords = domain_keywords.get(agent_domain, [])
                keyword_matches = [kw for kw in keywords if kw.lower() in text_lower]
                
                # If no keyword matches, skip expensive LLM call
                if not keyword_matches:
                    continue
                
                # Use gemma3:1b for detailed relevance scoring
                prompt = f"""Does this article contain information relevant to {agent_domain} domain analysis?

TITLE: {article.get('title', '')}
TEXT: {article.get('text', '')[:600]}

Respond with:
RELEVANCE: X.XX (0.0-1.0)
REASON: Brief explanation"""
                
                host = self.ollama_url.replace("http://", "").split(":")[0]
                response = call_ollama_simple(
                    model=self.filter_model,
                    prompt=prompt,
                    host=host,
                    port=11434,
                    timeout=30
                )
                
                score_match = re.search(r'RELEVANCE:\s*([0-9.]+)', response, re.IGNORECASE)
                reason_match = re.search(r'REASON:\s*([^\n]+)', response, re.IGNORECASE)
                
                score = float(score_match.group(1)) if score_match else 0.5
                reason = reason_match.group(1).strip() if reason_match else "Domain match"
                
                if score >= min_relevance:
                    filtered.append(FilteredArticle(
                        article_id=article.get('id', ''),
                        title=article.get('title', ''),
                        text=article.get('text', ''),
                        relevance_score=score,
                        relevance_reasoning=reason,
                        keywords_matched=keyword_matches,
                        source_url=article.get('source_url', ''),
                        published=article.get('published', '')
                    ))
            
            except Exception as e:
                logger.warning(f"Domain filtering failed for article: {e}")
        
        filtered.sort(key=lambda x: x.relevance_score, reverse=True)
        
        logger.info(f"Domain filter ({agent_domain}): {len(articles)} -> {len(filtered)} articles")
        
        return filtered


def prefilter_articles_for_agents(question: str,
                                  articles: List[Dict],
                                  agent_profiles: List[Dict],
                                  ollama_url: str = "http://192.168.1.140:11434") -> Dict[str, List[FilteredArticle]]:
    """
    Pre-filter articles for each agent based on their domain expertise
    
    Args:
        question: The forecasting question
        articles: All available articles
        agent_profiles: List of agent profile dicts with 'name' and 'role' keys
        ollama_url: Ollama server URL
    
    Returns:
        Dict mapping agent_name -> list of relevant FilteredArticle objects
    """
    prefilter = ArticlePreFilter(ollama_url=ollama_url, filter_model="gemma2:2b")
    
    # First, filter all articles for general relevance to the question
    logger.info("Stage 1: Filtering articles for question relevance")
    question_relevant = prefilter.filter_articles_for_question(
        question=question,
        articles=articles,
        min_relevance=0.3,
        max_articles=30  # Keep top 30 for domain filtering
    )
    
    # Convert to dicts for domain filtering
    relevant_dicts = [
        {
            'id': a.article_id,
            'title': a.title,
            'text': a.text,
            'source_url': a.source_url,
            'published': a.published
        }
        for a in question_relevant
    ]
    
    # Then, filter by agent domain
    agent_articles = {}
    
    for agent in agent_profiles:
        agent_name = agent['name']
        
        # Extract domain from agent role/expertise
        role = agent.get('role', '').lower()
        domain = 'general'
        
        if 'military' in role or 'defense' in role:
            domain = 'military'
        elif 'financial' in role or 'economic' in role or 'market' in role:
            domain = 'financial'
        elif 'tech' in role or 'cyber' in role:
            domain = 'technology'
        elif 'energy' in role or 'resource' in role:
            domain = 'energy'
        elif 'health' in role or 'bio' in role:
            domain = 'health'
        elif 'local' in role or 'virginia' in role:
            domain = 'local'
        
        logger.info(f"Stage 2: Filtering for agent {agent_name} (domain: {domain})")
        
        if domain == 'general':
            # Give all question-relevant articles to general agents
            agent_articles[agent_name] = question_relevant
        else:
            # Domain-specific filtering
            domain_filtered = prefilter.filter_articles_by_agent_domain(
                articles=relevant_dicts,
                agent_domain=domain,
                min_relevance=0.4
            )
            agent_articles[agent_name] = domain_filtered if domain_filtered else question_relevant[:10]
    
    return agent_articles
