"""
Article Tagging System

Automatically tags articles with relevant agent profiles based on content analysis.
Uses keyword matching and domain classification to determine which agents would
find each article interesting.
"""

import re
import json
from typing import List, Dict, Set
import logging

logger = logging.getLogger(__name__)


# Agent domain keywords mapping
AGENT_DOMAIN_KEYWORDS = {
    "military": {
        "keywords": [
            "military", "defense", "army", "navy", "air force", "marines", "pentagon",
            "carrier", "deployment", "forces", "troops", "combat", "strike group",
            "weapons", "missile", "aircraft", "submarine", "destroyer", "bomber",
            "nato", "command", "operation", "strategic", "tactical", "warship"
        ],
        "agents": ["Military Strategy Expert", "OSINT Flight Tracker"]
    },
    "financial": {
        "keywords": [
            "bank", "banking", "financial", "market", "stock", "economy", "economic",
            "fed", "federal reserve", "interest rate", "inflation", "credit", "debt",
            "treasury", "bond", "equity", "trading", "liquidity", "fdic", "crisis",
            "deposit", "loan", "mortgage", "commercial real estate", "recession"
        ],
        "agents": ["Macro Risk Forecaster", "Financial Market Forecaster", "Banking Crisis Analyst"]
    },
    "technology": {
        "keywords": [
            "technology", "tech", "cyber", "software", "hardware", "semiconductor",
            "chip", "ai", "artificial intelligence", "computer", "network", "data",
            "cloud", "server", "hack", "breach", "vulnerability", "ransomware",
            "tsmc", "intel", "nvidia", "apple", "google", "microsoft", "meta"
        ],
        "agents": ["Technology & Cyber Expert", "Network & Infrastructure Analyst"]
    },
    "energy": {
        "keywords": [
            "oil", "gas", "energy", "petroleum", "opec", "crude", "refinery",
            "pipeline", "power", "electricity", "renewable", "solar", "wind",
            "coal", "nuclear", "lng", "natural gas", "fuel", "utility"
        ],
        "agents": ["Energy & Resource Forecaster"]
    },
    "supply_chain": {
        "keywords": [
            "supply chain", "logistics", "shipping", "freight", "cargo", "port",
            "warehouse", "inventory", "shortage", "disruption", "container",
            "transport", "distribution", "procurement", "vendor", "supplier"
        ],
        "agents": ["Demand & Logistics Forecaster", "Industrial & Manufacturing Analyst"]
    },
    "geopolitical": {
        "keywords": [
            "china", "russia", "iran", "north korea", "venezuela", "taiwan",
            "ukraine", "middle east", "sanctions", "diplomat", "treaty",
            "alliance", "conflict", "tension", "summit", "negotiation", "g7", "g20"
        ],
        "agents": ["Intelligence & OSINT Specialist", "Policy & Governance Analyst"]
    },
    "health": {
        "keywords": [
            "health", "medical", "disease", "pandemic", "epidemic", "virus",
            "vaccine", "hospital", "cdc", "who", "outbreak", "infection",
            "patient", "healthcare", "pharmaceutical", "drug", "treatment"
        ],
        "agents": ["Health & Biosecurity Expert"]
    },
    "local_virginia": {
        "keywords": [
            "richmond", "virginia", "va", "chesterfield", "henrico", "petersburg",
            "midlothian", "mechanicsville", "glen allen", "short pump",
            "emergency", "police", "fire", "dispatch", "evacuation", "threat"
        ],
        "agents": ["Local Threat Monitor", "Local Threat Analyst"]
    },
    "environment": {
        "keywords": [
            "climate", "weather", "hurricane", "flood", "drought", "wildfire",
            "environment", "pollution", "emission", "carbon", "greenhouse",
            "temperature", "storm", "disaster", "rainfall", "sea level"
        ],
        "agents": ["Climate & Environmental Expert"]
    },
    "social": {
        "keywords": [
            "protest", "demonstration", "riot", "unrest", "movement", "strike",
            "labor", "unemployment", "population", "migration", "refugee",
            "demographic", "census", "inequality", "poverty", "election", "vote"
        ],
        "agents": ["Societal Dynamics Expert"]
    }
}


def tag_article_for_agents(title: str, text: str, source_url: str = "") -> List[str]:
    """
    Tag an article with relevant agent names based on content analysis
    
    Args:
        title: Article title
        text: Article content
        source_url: Article source URL
        
    Returns:
        List of agent names that would find this article relevant
    """
    # Combine title and text for analysis (weight title higher)
    content = f"{title} {title} {text}".lower()
    
    # Track matched domains and agents
    matched_agents = set()
    domain_scores = {}
    
    # Check each domain's keywords
    for domain, config in AGENT_DOMAIN_KEYWORDS.items():
        keywords = config["keywords"]
        agents = config["agents"]
        
        # Count keyword matches
        match_count = 0
        for keyword in keywords:
            # Use word boundaries to avoid partial matches
            pattern = r'\b' + re.escape(keyword.lower()) + r'\b'
            matches = len(re.findall(pattern, content))
            match_count += matches
        
        # If we have matches, add the agents
        if match_count > 0:
            domain_scores[domain] = match_count
            for agent in agents:
                matched_agents.add(agent)
    
    # Always include general/versatile agents for any article
    general_agents = [
        "Historical Trends Expert",
        "Red Team Adversarial",
        "Time-Series Specialist"
    ]
    
    # Add general agents if we have at least one domain match
    if matched_agents:
        matched_agents.update(general_agents)
    
    # Convert to sorted list for consistency
    result = sorted(list(matched_agents))
    
    if result:
        logger.debug(f"Tagged article '{title[:50]}...' with {len(result)} agents")
        logger.debug(f"  Domains: {list(domain_scores.keys())}")
    
    return result


def tag_article_json(title: str, text: str, source_url: str = "") -> str:
    """
    Tag an article and return JSON string for database storage
    
    Args:
        title: Article title
        text: Article content
        source_url: Article source URL
        
    Returns:
        JSON string of agent names list
    """
    agents = tag_article_for_agents(title, text, source_url)
    return json.dumps(agents)


def get_agents_from_tags(agent_tags_json: str) -> List[str]:
    """
    Parse agent tags JSON from database
    
    Args:
        agent_tags_json: JSON string from database
        
    Returns:
        List of agent names
    """
    if not agent_tags_json:
        return []
    
    try:
        return json.loads(agent_tags_json)
    except json.JSONDecodeError:
        logger.warning(f"Failed to parse agent tags: {agent_tags_json}")
        return []


def filter_articles_by_agent(articles: List[Dict], agent_name: str) -> List[Dict]:
    """
    Filter articles to only those tagged for a specific agent
    
    Args:
        articles: List of article dicts with 'agent_tags' field
        agent_name: Name of the agent to filter for
        
    Returns:
        Filtered list of articles
    """
    filtered = []
    
    for article in articles:
        tags_json = article.get('agent_tags', '[]')
        agents = get_agents_from_tags(tags_json)
        
        if agent_name in agents:
            filtered.append(article)
    
    return filtered


def get_tag_statistics(articles: List[Dict]) -> Dict[str, int]:
    """
    Get statistics on agent tag distribution
    
    Args:
        articles: List of article dicts with 'agent_tags' field
        
    Returns:
        Dict mapping agent name to article count
    """
    stats = {}
    
    for article in articles:
        tags_json = article.get('agent_tags', '[]')
        agents = get_agents_from_tags(tags_json)
        
        for agent in agents:
            stats[agent] = stats.get(agent, 0) + 1
    
    return dict(sorted(stats.items(), key=lambda x: x[1], reverse=True))


# Example usage
if __name__ == "__main__":
    # Test tagging
    test_articles = [
        {
            "title": "U.S. Navy Deploys Carrier Strike Group to Caribbean",
            "text": "The Pentagon announced deployment of USS Abraham Lincoln carrier strike group with two destroyers to the Caribbean amid tensions with Venezuela...",
        },
        {
            "title": "Regional Banks Face Liquidity Crisis",
            "text": "FDIC officials monitor deposit outflows at regional banks as commercial real estate stress intensifies...",
        },
        {
            "title": "TSMC Reports Semiconductor Supply Chain Disruption",
            "text": "Taiwan Semiconductor Manufacturing Company warns of potential chip shortages due to equipment delivery delays...",
        }
    ]
    
    print("Article Tagging Test:\n")
    for article in test_articles:
        tags = tag_article_for_agents(article["title"], article["text"])
        print(f"Title: {article['title']}")
        print(f"Tagged agents ({len(tags)}): {', '.join(tags)}\n")
