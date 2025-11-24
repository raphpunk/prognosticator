"""Content-type classification utilities.

Provides a simple keyword-based classifier for content types (socio, political, economic,
health, tech, environment, security) and a small ML-ready wrapper for future training.
"""
from typing import List, Dict

TAXONOMY = ["socio", "political", "economic", "health", "tech", "environment", "security", "other"]

# simple keyword sets per category
KEYWORDS = {
    "political": {"election", "government", "minister", "president", "parliament", "policy", "vote", "campaign"},
    "economic": {"economy", "market", "inflation", "stock", "trade", "gdp", "recession", "unemployment"},
    "health": {"health", "disease", "pandemic", "vaccine", "hospital", "covid", "epidemic", "outbreak"},
    "tech": {"technology", "software", "ai", "machine learning", "startup", "cyber", "app", "platform"},
    "environment": {"climate", "emissions", "pollution", "wildfire", "flood", "environment", "conservation"},
    "security": {"attack", "terror", "military", "conflict", "cyberattack", "security", "sanction"},
    "socio": {"protest", "crime", "community", "culture", "education", "migration", "demographic"},
}


def classify_text_keywords(text: str) -> str:
    """Classify text by simple keyword matching. Returns the best matching taxonomy label.

    Falls back to 'other' when no keywords match.
    """
    txt = text.lower()
    scores = {k: 0 for k in TAXONOMY}
    for cat, kws in KEYWORDS.items():
        for kw in kws:
            if kw in txt:
                scores[cat] += 1

    # choose highest scoring non-zero category
    best = max(scores.items(), key=lambda x: x[1])
    if best[1] == 0:
        return "other"
    return best[0]


class SimpleContentClassifier:
    """Wrapper class for future training. Currently uses keyword matching.

    Methods:
      - predict(texts) -> list of labels
      - fit(...) -> placeholder
    """

    def __init__(self):
        # placeholder for ML model (e.g., a vectorizer + classifier)
        self.model = None

    def predict(self, texts: List[str]) -> List[str]:
        return [classify_text_keywords(t) for t in texts]

    def fit(self, texts: List[str], labels: List[str]):
        # no-op for now; placeholder to train a real classifier later
        self.model = "trained_placeholder"


if __name__ == "__main__":
    clf = SimpleContentClassifier()
    samples = [
        "The government announced a new policy for trade and tariffs.",
        "Researchers released a new AI model for image recognition.",
        "Floods and wildfires are increasing with climate change.",
    ]
    print(clf.predict(samples))
