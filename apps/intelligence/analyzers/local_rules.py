import re
from typing import Optional, Dict, Any, Tuple
from .base import BaseCivicAnalyzer, CivicAnalysisResult
from apps.master_data.models import CivicLocation, Department, CivicCategory

class LocalCivicAnalyzer(BaseCivicAnalyzer):
    """
    Deterministic multilingual civic intelligence analyzer.
    Engineered for Gujarati, Hindi, English, and Gujlish civic text in Rajkot.
    Extracts sentiment, department, urgency with evidence, and verified landmarks.
    """
    version_identifier = "pulse-local-heuristic-v1.0"

    def __init__(self):
        # Cache ward and area gazetteer in memory for high-speed regex matching
        self._load_gazetteer()

    def _load_gazetteer(self):
        self.ward_keywords = []
        try:
            for loc in CivicLocation.objects.all():
                landmarks = [l.strip().lower() for l in loc.known_landmarks.split(",") if len(l.strip()) > 3]
                self.ward_keywords.append({
                    "ward_number": loc.ward_number,
                    "zone": loc.zone,
                    "ward_name": loc.ward_name,
                    "landmarks": landmarks,
                })
        except Exception:
            # Fallback for bootstrap before db migrations
            self.ward_keywords = [
                {"ward_number": 7, "zone": "CENTRAL", "ward_name": "Ward 7 - Amin Marg / Race Course", "landmarks": ["race course", "amin marg", "prem mandir", "kotecha chowk", "yagnik road"]},
                {"ward_number": 2, "zone": "CENTRAL", "ward_name": "Ward 2 - Railnagar", "landmarks": ["railnagar", "popatpara", "bajrangwadi"]},
                {"ward_number": 4, "zone": "EAST", "ward_name": "Ward 4 - Bhagvati Para", "landmarks": ["bhagvati para", "bedi para", "morbi road"]},
                {"ward_number": 9, "zone": "WEST", "ward_name": "Ward 9 - Nana Mava", "landmarks": ["nana mava", "raiya road", "speedwell"]},
                {"ward_number": 10, "zone": "WEST", "ward_name": "Ward 10 - 150ft Ring Road", "landmarks": ["150 feet ring road", "mavdi", "umiya chowk"]},
                {"ward_number": 11, "zone": "WEST", "ward_name": "Ward 11 - Kalawad Road", "landmarks": ["kalawad road", "pushkar dham"]},
            ]

    def detect_language(self, text: str) -> str:
        """Detects whether text is in Gujarati script, Devanagari Hindi, Latin English, Hinglish, or Gujlish."""
        gu_script = len(re.findall(r'[\u0A80-\u0AFF]', text))
        hi_script = len(re.findall(r'[\u0900-\u097F]', text))
        latin_count = len(re.findall(r'[a-zA-Z]', text))

        if gu_script > 3 and latin_count > 3:
            return "mixed"
        if gu_script > 3:
            return "gu"
        if hi_script > 3:
            return "hi"

        # Check for Romanized / Transliterated civic text (Gujlish / Hinglish)
        lower = text.lower()
        hinglish_markers = ["raha hai", "pad rahe", "paani", "peene", "bimaar", "bacche", "bahut", "kijiye", "ganda", "badbudaar", "hoga", "karo"]
        gujlish_markers = ["che", "nathi", "aave che", "bharaay", "moklo", "khada", "vadhigayo", "karyo", "thase", "trass"]

        hi_score = sum(1 for m in hinglish_markers if m in lower)
        gu_score = sum(1 for m in gujlish_markers if m in lower)

        if hi_score >= 2:
            return "hi"
        if gu_score >= 2:
            return "gu"
        if hi_score >= 1 or gu_score >= 1:
            return "mixed"

        if latin_count > 0:
            return "en"
        return "und"

    def extract_location(self, text: str) -> Tuple[Optional[str], Optional[int]]:
        """Matches landmarks in text against Rajkot gazetteer in both Gujarati script and English."""
        lower_text = text.lower()
        
        # 1. Check explicit ward numbers (e.g. 'ward 7', 'ward no 2', 'વોર્ડ ૭', 'વોર્ડ 4')
        ward_match = re.search(r'(?:ward|ward\s*no\.?|વોર્ડ)\s*[:#-]?\s*(\d{1,2})', lower_text)
        if ward_match:
            try:
                w_num = int(ward_match.group(1))
                if 1 <= w_num <= 18:
                    return f"Ward {w_num}", w_num
            except ValueError:
                pass

        # 2. Native Gujarati script landmark gazetteer
        gujarati_landmarks = [
            (2, ["રેલનગર", "પોપટપરા", "બજરંગવાડી"]),
            (7, ["કાલાવડ રોડ", "પ્રેમ મંદિર", "રેસકોર્સ", "અમીન માર્ગ", "કોટેચા ચોક", "યાજ્ઞિક રોડ"]),
            (4, ["ભગવતી પરા", "બેડી પરા", "મોરબી રોડ"]),
            (5, ["પેડક રોડ", "ગ્રીનલેન્ડ", "સંત કબીર રોડ", "ત્રિકોણ બાગ"]),
            (9, ["નાના મવા", "રૈયા રોડ", "સ્પીડવેલ"]),
            (10, ["૧૫૦ ફીટ રીંગ રોડ", "માવડી", "ઉમિયા ચોક"]),
            (11, ["પુષ્કર ધામ", "હરિદર્શન"]),
            (1, ["ગાંધીગ્રામ", "માધાપર"]),
            (8, ["યુનિવર્સિટી રોડ", "ઇન્દિરા સર્કલ", "સાધુ વાસવાણી"]),
            (13, ["ટાગોર રોડ", "ગોંડલ રોડ", "ભક્તિનગર"]),
            (15, ["ચુનારાવાડ", "ભાવનગર રોડ"]),
            (16, ["આજી ડેમ", "માર્કેટિંગ યાર્ડ"]),
            (17, ["કોઠારીયા", "આટિકા"]),
        ]
        for w_num, g_list in gujarati_landmarks:
            for g_item in g_list:
                if g_item in text:
                    return g_item, w_num

        # 3. Match English / Latin gazetteer landmarks
        for item in self.ward_keywords:
            for landmark in item["landmarks"]:
                if landmark in lower_text:
                    return landmark.title(), item["ward_number"]

        return None, None

    def analyze(self, raw_text: str, metadata: Optional[Dict[str, Any]] = None) -> CivicAnalysisResult:
        text = raw_text.strip()
        lower_text = text.lower()
        lang = self.detect_language(text)

        # 1. Department & Category Heuristics
        dept_code = "solid-waste-management"
        cat_code = "miscellaneous"
        theme = "General Civic Inquiry"
        confidence = 0.75

        # DRAINAGE
        if any(w in lower_text for w in ["ગટર", "મેનહોલ", "ચોકઅપ", "ઉભરાય", "sewage", "gutter", "drainage", "overflow", "blackwater", "choke"]):
            dept_code = "drainage-chockup-overflow"
            cat_code = "main-line-overflowing"
            theme = "Manhole & Sewer Overflow"
            confidence = 0.92

        # ROSHNI / STREETLIGHTS
        elif any(w in lower_text for w in ["લાઈટ", "અંધારું", "થાંભલો", "streetlight", "light", "dark", "pole", "led", "bulb"]):
            dept_code = "roshni-branch"
            cat_code = "led-tl-not-functioning"
            theme = "Streetlight Failure"
            confidence = 0.94

        # WATER WORKS
        elif any(w in lower_text for w in ["પાણી", "પીવાનું પાણી", "ગંદુ પાણી", "લીકેજ", "પ્રેશર", "water", "drinking water", "pipeline leak", "low force", "polluted water", "paani", "peene", "pani"]):
            dept_code = "water-works-outdoor"
            if "ગંદુ" in lower_text or "polluted" in lower_text or "contamination" in lower_text or "badbudaar" in lower_text:
                cat_code = "polluted-water"
                theme = "Drinking Water Contamination"
            else:
                cat_code = "pipeline-leakage"
                theme = "Water Supply & Pipeline Leak"
            confidence = 0.91

        # ROADS & CIVIL / BANDHKAM
        elif any(w in lower_text for w in ["ખાડા", "ખાડો", "રસ્તો", "તૂટેલો", "ડામર", "પેવર બ્લોક", "pothole", "broken road", "asphalt", "bitumen", "footpath", "cave-in"]):
            dept_code = "bandhkam-civil-roads"
            cat_code = "pothole-bitumen-damage"
            theme = "Potholes & Road Damage"
            confidence = 0.93

        # SOLID WASTE
        elif any(w in lower_text for w in ["કચરો", "કચરાપેટી", "ગંદકી", "ડમ્પિંગ", "ટીપર", "garbage", "trash", "dustbin", "waste", "sweeping", "swachhata"]):
            dept_code = "solid-waste-management"
            cat_code = "sweeping-not-done"
            theme = "Garbage Collection & Sweeping"
            confidence = 0.90

        # ANIMALS / CATTLE / DOGS
        elif any(w in lower_text for w in ["ઢોર", "ગાય", "આખલો", "કૂતરા", "cattle", "cow", "bull", "dog", "dhor", "stray"]):
            dept_code = "ancd-animal-control"
            cat_code = "catch-the-animal-dhor-pakadva"
            theme = "Stray Animals & Cattle Control"
            confidence = 0.88

        # CONSERVANCY / DEAD ANIMAL
        elif any(w in lower_text for w in ["મરેલું", "મરેલો", "dead animal", "carcass", "dead"]):
            dept_code = "conservancy-dead-animal"
            cat_code = "dead-animal-removal"
            theme = "Dead Animal Carcass Removal"
            confidence = 0.95

        # HEALTH / MOSQUITO
        elif any(w in lower_text for w in ["મચ્છર", "મેલેરિયા", "ડેન્ગ્યુ", "દવા છંટકાવ", "mosquito", "fogging", "malaria", "dengue"]):
            dept_code = "health-urban-maleriya"
            cat_code = "mosquito-fogging"
            theme = "Mosquito Fogging & Vector Control"
            confidence = 0.89

        # CITY BUS
        elif any(w in lower_text for w in ["સિટી બસ", "બીઆરટીએસ", "city bus", "brts", "bus stop"]):
            dept_code = "city-bus-rajpath"
            cat_code = "bus-service"
            theme = "City Bus Service"
            confidence = 0.87

        # 2. Urgency Classification with Evidence-Backed Reasoning
        urgency = "MEDIUM"
        urgency_reason = "Standard civic grievance logged for routine municipal response."

        # EMERGENCY CHECKS
        if any(w in lower_text for w in ["અકસ્માત", "accident", "સ્લીપ", "slip", "હોસ્પિટલ", "hospital", "ઝાડા", "ઉલટી", "illness", "bimaar", "બિમાર", "વાયર", "કરંટ", "shock", "live wire", "open manhole", "ખુલ્લી ગટર"]):
            urgency = "EMERGENCY"
            urgency_reason = "High hazard safety risk detected: Potential casualty, open electrical hazard, or waterborne illness reported."
            confidence = max(confidence, 0.92)
        elif any(w in lower_text for w in ["દિવસથી", "days", "ગંભીર", "urgent", "emergency", "તાત્કાલિક", "dangerous", "overnight", "flooding", "blackwater"]):
            urgency = "HIGH"
            urgency_reason = "Active escalation factor: Prolonged disruption (>48h) or hazardous sanitation spill."
        elif any(w in lower_text for w in ["આભાર", "thanks", "thank you", "good work", "repaired", "prompt", "સારું કામ"]):
            urgency = "LOW"
            urgency_reason = "Appreciative civic feedback or resolved issue notification."

        # 3. Sentiment Polarity
        pos_words = ["આભાર", "thanks", "thank you", "good", "great", "prompt", "સારું", "સુંદર", "repaired", "solved", "best"]
        neg_words = ["ખાડો", "ગટર", "ગંદકી", "દુર્ગંધ", "બિમાર", "ત્રાસ", "મુશ્કેલ", "ખરાબ", "pothole", "leakage", "dirty", "worst", "smell", "terrible", "accident", "nuisance"]
        
        pos_hits = sum(1 for w in pos_words if w in lower_text)
        neg_hits = sum(1 for w in neg_words if w in lower_text)

        if pos_hits > 0 and neg_hits == 0:
            sentiment = "POSITIVE"
            sentiment_score = 0.85
        elif neg_hits > 0 and pos_hits == 0:
            sentiment = "NEGATIVE"
            sentiment_score = -0.85
        elif pos_hits > 0 and neg_hits > 0:
            sentiment = "MIXED"
            sentiment_score = -0.20
        else:
            sentiment = "NEUTRAL"
            sentiment_score = 0.0

        # 4. Location Extraction
        extracted_loc, suggested_ward = self.extract_location(text)

        # 5. Human Review Flag
        requires_review = (confidence < 0.70) or (urgency == "EMERGENCY") or (sentiment == "MIXED")

        return CivicAnalysisResult(
            is_civic_related=True,
            sentiment=sentiment,
            sentiment_score=sentiment_score,
            detected_language=lang,
            category_code=cat_code,
            department_code=dept_code,
            urgency=urgency,
            urgency_reasoning=urgency_reason,
            extracted_location_name=extracted_loc,
            suggested_ward_number=suggested_ward,
            recurring_theme=theme,
            short_summary=text[:120],
            confidence_score=confidence,
            requires_human_review=requires_review,
            model_version=self.version_identifier,
            raw_response={"engine": "LocalCivicAnalyzer", "matched_theme": theme}
        )
