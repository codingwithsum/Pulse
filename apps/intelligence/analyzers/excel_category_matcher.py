import re
from typing import Optional, Tuple, Dict, Any, List
from difflib import SequenceMatcher
from apps.master_data.models import Department, CivicCategory

# Multilingual civic synonym dictionaries for Gujarati, Hindi, English
SYNONYMS = {
    # Water Works
    "water": ["પાણી", "પીવાનું પાણી", "ગંદુ પાણી", "લીકેજ", "પ્રેશર", "water", "pipeline", "leak", "tap", "pressure", "paani", "peene", "pani", "dhar"],
    "contamination": ["ગંદુ", "વાસ", "દુર્ગંધ", "contaminated", "dirty", "turbid", "smell", "badbudaar", "pradushit"],
    "no_water": ["પાણી નથી", "પાણી આવતું નથી", "no water", "shortage", "nahi aa raha", "pani bandh"],

    # Drainage
    "drainage": ["ગટર", "મેનહોલ", "ચોકઅપ", "ઉભરાય", "sewer", "drainage", "manhole", "overflow", "blackwater", "choke", "gutter", "dhalak"],
    "manhole_cover": ["મેનહોલ કવર", "ઢાંકણું", "લેવલિંગ", "manhole cover", "chamber cover", "damaged cover", "broken slab"],

    # Roshni / Streetlights
    "streetlight": ["લાઈટ", "અંધારું", "થાંભલો", "streetlight", "light", "dark", "pole", "led", "bulb", "tube light", "batti", "andharu"],
    
    # Bandhkam / Roads
    "road": ["ખાડા", "ખાડો", "રસ્તો", "તૂટેલો", "ડામર", "પેવર બ્લોક", "pothole", "broken road", "asphalt", "bitumen", "footpath", "cave-in", "sadak", "gaddhe"],
    
    # Solid Waste
    "garbage": ["કચરો", "કચરાપેટી", "ગંદકી", "ડમ્પિંગ", "ટીપર", "garbage", "trash", "dustbin", "waste", "sweeping", "swachhata", "kachra", "safai"],
    
    # Animal Control
    "animal": ["ઢોર", "ગાય", "આખલો", "કૂતરા", "cattle", "cow", "bull", "dog", "dhor", "stray", "bhatakta", "pakadva"],
    
    # Dead Animal
    "dead_animal": ["મરેલું", "મરેલો", "dead animal", "carcass", "dead dog", "dead cow"],
    
    # Health / Mosquito
    "mosquito": ["મચ્છર", "મેલેરિયા", "ડેન્ગ્યુ", "દવા છંટકાવ", "mosquito", "fogging", "malaria", "dengue", "machhar"],
    
    # City Bus
    "bus": ["સિટી બસ", "બીઆરટીએસ", "city bus", "brts", "bus stop", "rajpath", "conductor"],
}


def semantic_similarity(text_a: str, text_b: str) -> float:
    """Calculates word and character sequence similarity."""
    a_words = set(re.findall(r'\w+', text_a.lower()))
    b_words = set(re.findall(r'\w+', text_b.lower()))

    if not a_words or not b_words:
        return 0.0

    # Jaccard word overlap
    overlap = len(a_words & b_words) / float(len(a_words | b_words))
    # String sequence matcher
    seq = SequenceMatcher(None, text_a.lower(), text_b.lower()).ratio()

    return (overlap * 0.6) + (seq * 0.4)


def match_complaint_to_excel_category(
    complaint_text: str
) -> Tuple[Optional[CivicCategory], Optional[Department], float, str]:
    """
    Compares complaint meaning with official Complaint Types and Departments
    extracted from the Excel reference dataset.

    Returns:
        (matched_category, matched_department, confidence_score, reasoning)
    """
    lower = complaint_text.lower()
    categories = list(CivicCategory.objects.filter(is_active=True).select_related('department'))

    if not categories:
        return None, None, 0.0, "No official categories loaded from Excel reference dataset."

    best_cat = None
    best_score = 0.0

    # 1. Check against multilingual synonyms and keywords
    concept_scores = {}
    for concept, keywords in SYNONYMS.items():
        hits = sum(1 for kw in keywords if kw in lower)
        if hits > 0:
            concept_scores[concept] = hits

    # 2. Evaluate against every official category
    for cat in categories:
        cat_name = cat.name.lower()
        dept_name = cat.department.name.lower()

        score = semantic_similarity(lower, cat_name)

        # Boost score if keywords or synonyms align with category name or department
        for concept, hits in concept_scores.items():
            concept_keywords = SYNONYMS[concept]
            if any(k in cat_name or k in dept_name for k in concept_keywords[:4]):
                score += (0.18 * min(hits, 3))

        # Direct containment boost
        if cat_name in lower or any(word in cat_name for word in lower.split() if len(word) > 4):
            score += 0.25

        if score > best_score:
            best_score = score
            best_cat = cat

    # Normalize score between 0.0 and 1.0
    confidence = min(round(best_score, 2), 0.98)

    # Threshold checks per Rule 4
    if confidence >= 0.55 and best_cat:
        dept = best_cat.department
        reason = f"Semantically matched to official Complaint Type '{best_cat.name}' under department '{dept.name}'."
        return best_cat, dept, confidence, reason

    # Low confidence fallback
    misc_cat = CivicCategory.objects.filter(name__icontains="MISCELLANEOUS").first()
    if misc_cat:
        return misc_cat, misc_cat.department, 0.45, "Low confidence match; mapped to official Miscellaneous for Admin Review."

    return None, None, 0.0, "Uncategorised (complaint text could not be reliably classified)."

