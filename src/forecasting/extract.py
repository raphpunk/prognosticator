"""Event extraction utilities.

Provides a lightweight extractor using spaCy if available, otherwise falls back to simple heuristics.
Functions are written to avoid importing heavy libs at module import time.
"""
from typing import Dict, List


def extract_entities_spacy(text: str) -> List[Dict]:
    try:
        import spacy
    except Exception as e:
        raise RuntimeError("spaCy is required for advanced extraction. Install it or use demo mode.") from e

    nlp = spacy.load("en_core_web_sm")
    doc = nlp(text)
    out = []
    for ent in doc.ents:
        out.append({"text": ent.text, "label": ent.label_})
    return out


def simple_extractor(text: str) -> List[Dict]:
    # primitive extraction: look for capitalized words groups as named entities
    tokens = text.split()
    entities = []
    cur = []
    for t in tokens:
        if t.istitle() and len(t) > 1:
            cur.append(t.strip(".,"))
        else:
            if cur:
                entities.append(" ".join(cur))
                cur = []
    if cur:
        entities.append(" ".join(cur))
    return [{"text": e, "label": "PROPER"} for e in entities]


def extract_from_article(article: Dict, use_spacy: bool = False, classify_content: bool = True) -> Dict:
    text = article.get("text") or article.get("summary") or article.get("title", "")
    if use_spacy:
        ents = extract_entities_spacy(text)
    else:
        ents = simple_extractor(text)

    content_type = None
    if classify_content:
        try:
            from forecasting.classify import SimpleContentClassifier

            clf = SimpleContentClassifier()
            content_type = clf.predict([text])[0]
        except Exception:
            content_type = "other"

    return {
        "id": article.get("id"),
        "title": article.get("title"),
        "published": article.get("published"),
        "source_url": article.get("source_url"),
        "entities": ents,
        "content_type": content_type,
    }


if __name__ == "__main__":
    print(simple_extractor("President Alice met with the Ministry of Energy in Paris."))
