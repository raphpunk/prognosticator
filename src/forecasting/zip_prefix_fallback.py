"""Heuristic ZIP prefix fallback mapping.

Provides a lightweight fallback when LLM-driven jurisdiction discovery
fails or is globally disabled. Maps US ZIP code prefixes (first 3 digits)
to a likely state abbreviation. This is intentionally minimal and can be
expanded incrementally.

Usage:
    from forecasting.zip_prefix_fallback import lookup_state_for_zip
    state = lookup_state_for_zip("10001")  # -> "NY"

If a state is identified, upstream logic may attempt a secondary
discovery step such as querying for the largest city dispatch page in
that state. The mapping prioritizes major population and dispatch data
availability.
"""

from typing import Optional

# Compressed representative mapping of ZIP 3-digit prefixes to states.
# Sources: USPS public ZIP allocation references (simplified).
# NOTE: This is not exhaustive; extend as needed.
ZIP_PREFIX_TO_STATE = {
    # Northeast
    "010": "MA", "011": "MA", "012": "MA", "013": "MA", "014": "MA", "015": "MA",
    "016": "MA", "017": "MA", "018": "MA", "019": "MA",
    "020": "MA", "021": "MA", "022": "MA", "023": "MA", "024": "MA", "025": "MA",
    "026": "MA", "027": "MA", "028": "RI", "029": "RI",
    "030": "NH", "031": "NH", "032": "NH", "033": "NH", "034": "NH", "035": "NH",
    "036": "NH", "037": "NH", "038": "NH",
    "039": "ME", "040": "ME", "041": "ME", "042": "ME", "043": "ME", "044": "ME",
    "045": "ME", "046": "ME", "047": "ME", "048": "ME", "049": "ME",
    "050": "VT", "051": "VT", "052": "VT", "053": "VT", "054": "VT", "055": "VT",
    "056": "VT", "057": "VT", "058": "VT", "059": "VT",
    "060": "CT", "061": "CT", "062": "CT", "063": "CT", "064": "CT", "065": "CT",
    "066": "CT", "067": "CT", "068": "CT", "069": "CT",
    "070": "NJ", "071": "NJ", "072": "NJ", "073": "NJ", "074": "NJ", "075": "NJ",
    "076": "NJ", "077": "NJ", "078": "NJ", "079": "NJ", "080": "NJ", "081": "NJ",
    "082": "NJ", "083": "NJ", "084": "NJ", "085": "NJ", "086": "NJ", "087": "NJ",
    "088": "NJ", "089": "NJ",
    "100": "NY", "101": "NY", "102": "NY", "103": "NY", "104": "NY", "105": "NY",
    "106": "NY", "107": "NY", "108": "NY", "109": "NY", "110": "NY", "111": "NY",
    "112": "NY", "113": "NY", "114": "NY", "115": "NY", "116": "NY", "117": "NY",
    "118": "NY", "119": "NY",
    # Mid-Atlantic (partial)
    "200": "DC", "201": "VA", "202": "DC", "203": "DC", "204": "DC", "205": "DC",
    "206": "MD", "207": "MD", "208": "MD", "209": "MD",
    "210": "MD", "211": "MD", "212": "MD", "217": "MD",
    "220": "VA", "221": "VA", "222": "VA", "223": "VA", "224": "VA", "225": "VA",
    "226": "VA", "227": "VA", "228": "VA", "229": "VA", "230": "VA", "231": "VA",
    "232": "VA", "233": "VA", "234": "VA", "235": "VA", "236": "VA", "237": "VA",
    "238": "VA", "239": "VA",
    "240": "VA", "241": "VA", "242": "VA", "243": "VA", "244": "VA", "245": "VA",
    # Selected large metros for fallback inference
    "606": "IL",  # Chicago
    "850": "AZ",  # Phoenix
    "900": "CA", "901": "CA", "902": "CA", "903": "CA", "904": "CA", "905": "CA",
    "906": "CA", "907": "CA", "908": "CA", "909": "CA",
    "940": "CA", "941": "CA",  # Bay Area
    "770": "TX",  # Houston
    "752": "TX",  # Dallas
    "331": "FL",  # Miami
    "606": "IL",  # Chicago
    "802": "CO",  # Denver
    "972": "OR",  # Portland
    "981": "WA",  # Seattle
}


def lookup_state_for_zip(zip_code: str) -> Optional[str]:
    """Return state abbreviation using first 3 digits of ZIP.

    Args:
        zip_code: 5-digit ZIP as string (or longer)

    Returns:
        Two-letter state code or None.
    """
    if not zip_code or len(zip_code) < 3 or not zip_code.isdigit():
        return None
    prefix = zip_code[:3]
    return ZIP_PREFIX_TO_STATE.get(prefix)


__all__ = ["lookup_state_for_zip", "ZIP_PREFIX_TO_STATE"]
