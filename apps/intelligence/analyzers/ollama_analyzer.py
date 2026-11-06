"""
OllamaCivicAnalyzer
===================
Civic complaint analyzer powered by a local Ollama model (default: llama3.2).

Why llama3.2?
-------------
- Best-in-class multilingual support for Gujarati, Hindi, English, and Gujlish
- Runs fully offline — no API key or internet required
- Accurate JSON-structured output for civic NLP tasks
- Fast enough for batch processing on commodity hardware

Setup (one-time):
-----------------
1. Install Ollama from https://ollama.com
2. Pull the model:
       ollama pull llama3.2
3. Make sure Ollama is running:
       ollama serve
4. In Django settings (settings.py or .env), set:
       OLLAMA_MODEL = "llama3.2"           # or llama3.2:1b for lower RAM
       OLLAMA_BASE_URL = "http://localhost:11434"

The analyzer is automatically activated when OLLAMA_MODEL is set in Django settings
and Ollama is reachable. It falls back to LocalCivicAnalyzer if Ollama is unavailable.
"""

import json
import logging
import re
from typing import Optional, Dict, Any

from .base import BaseCivicAnalyzer, CivicAnalysisResult

logger = logging.getLogger(__name__)

# RMC Rajkot master data — keeps the prompt grounded to real dept/category codes
RMC_DEPARTMENTS = """
Available Departments (use EXACT code from this list only):
- drainage-sewerage         : Drainage / Sewer / Manhole overflow / gutter
- drainage-chockup-overflow : Drainage chockup / overflow emergency
- drainage-maintenance      : Drainage maintenance / pipe repair
- roshni-branch             : Streetlights / LED lights / Poles
- solid-waste               : Garbage collection / Dustbin / Tipper / door-to-door van
- solid-waste-management    : Sweeping / waste management
- water-works               : Water supply / Pipeline leakage / Contamination
- water-works-outdoor       : Outdoor water works / water connection
- engineering-roads         : Potholes / Road damage / Footpath / Civil works
- bandhkam-civil-roads      : Road construction / civil works
- city-bus-rajpath          : BRTS / City bus / Bus stop
- ancd-animal-control       : Stray cattle / Dogs / Animal nuisance
- conservancy-dead-animal   : Dead animal carcass removal
- garden-sports             : Park / Garden / Playground
- daban-hatav-branch        : Encroachment / Illegal construction
- health-sanitation         : Mosquito fogging / Malaria / Dengue / Sanitation
- health-urban-maleriya     : Urban health / vector control
- food-sanitation           : Food safety / Contaminated food
- town-planning-estate      : Building permit / Town planning
- traffic-streetlighting    : Traffic signals / Streetlighting / Road signs / Stray cattle on road
- traffic-transport-cell    : Traffic / Parking / Transport
"""

RMC_CATEGORIES = """
Available Category Codes (use EXACT code from this list only):
- manhole-overflow          (drainage-sewerage)      : Manhole / gutter overflow
- pipeline-leak             (water-works)            : Water pipeline leakage
- water-contamination       (water-works)            : Polluted / contaminated water
- potholes                  (engineering-roads)      : Potholes / broken road / bitumen
- footpath                  (engineering-roads)      : Footpath damage
- mosquito-fogging          (health-sanitation)      : Mosquito / fogging / malaria / dengue
- garbage-overflow          (solid-waste)            : Garbage not collected / overflow
- door-to-door-van          (solid-waste)            : Door-to-door garbage van not coming
- streetlight-off           (traffic-streetlighting) : Streetlight not working / LED off
- stray-cattle              (traffic-streetlighting) : Stray cattle / animals on road
"""

SYSTEM_PROMPT = """You are a municipal civic complaint classifier for Rajkot Municipal Corporation (RMC), Gujarat, India.

Your job is to analyze citizen complaint text — which may be in Gujarati, Hindi, English, or mixed (Gujlish/Hinglish) — and extract structured information.

ALWAYS respond with a single valid JSON object. No extra text before or after. No markdown.

JSON schema (all fields required):
{
  "is_civic_related": true/false,
  "sentiment": "POSITIVE" | "NEGATIVE" | "NEUTRAL" | "MIXED" | "UNCERTAIN",
  "sentiment_score": float between -1.0 (very negative) and 1.0 (very positive),
  "detected_language": "gu" | "hi" | "en" | "mixed" | "und",
  "department_code": "<exact code from list below or null>",
  "category_code": "<exact code from list below or null>",
  "urgency": "EMERGENCY" | "HIGH" | "MEDIUM" | "LOW",
  "urgency_reasoning": "<one sentence evidence-backed reasoning>",
  "extracted_location_name": "<area, landmark, or street name if mentioned, else null>",
  "suggested_ward_number": <integer 1-18 if identifiable, else null>,
  "recurring_theme": "<short normalized issue label in English>",
  "short_summary": "<1-sentence English summary of the complaint>",
  "confidence_score": float between 0.0 and 1.0,
  "requires_human_review": true/false
}

Urgency rules:
- EMERGENCY: live electrical hazard, open manhole, accident, waterborne illness, flooding inside homes
- HIGH: issue persisting > 48 hours, major road blocked, sewage spill on road
- MEDIUM: standard civic complaint needing timely action
- LOW: feedback, appreciation, already resolved

Rajkot Wards and Gujlish Rules:
- Rajkot has Wards 1 to 18. If the text mentions any ward (e.g. "ward 13", "ward 10", "વોર્ડ ૭"), extract that number into "suggested_ward_number" as an integer (1 to 18).
- "gay" or "dhor" in Gujarati/Gujlish means cow/cattle (Animal Control: ancd-animal-control, category: stray-cattle). "gay road par bese che" means stray cattle sitting on road causing traffic.
- Never extract "Ma Gay Road" or similar words as location names.

""" + RMC_DEPARTMENTS + "\n" + RMC_CATEGORIES


class OllamaCivicAnalyzer(BaseCivicAnalyzer):
    """
    Civic analyzer that calls a local Ollama model via its HTTP API.
    Default model: llama3.2 (best multilingual accuracy for Gujarati/Hindi/English civic text).
    """

    def __init__(self, model: str = "llama3.2", base_url: str = "http://localhost:11434", timeout: int = 60):
        self.model = model
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.version_identifier = f"ollama-{model}-v1"

    def _call_ollama(self, prompt: str) -> Optional[str]:
        """Calls Ollama /api/generate endpoint and returns raw text response."""
        import urllib.request
        import urllib.error

        payload = json.dumps({
            "model": self.model,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": 0.1,       # Low temp = deterministic, consistent output
                "top_p": 0.9,
                "num_predict": 512,
            }
        }).encode("utf-8")

        req = urllib.request.Request(
            f"{self.base_url}/api/generate",
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST"
        )

        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                return data.get("response", "").strip()
        except urllib.error.URLError as e:
            logger.warning(f"[OllamaCivicAnalyzer] Cannot reach Ollama at {self.base_url}: {e}")
            return None
        except Exception as e:
            logger.error(f"[OllamaCivicAnalyzer] Unexpected error: {e}")
            return None

    def _parse_response(self, raw: str) -> Optional[Dict[str, Any]]:
        """Extracts and validates the JSON object from the model response."""
        if not raw:
            return None

        # Try to extract JSON block if model wrapped it in markdown
        match = re.search(r'\{.*\}', raw, re.DOTALL)
        if match:
            raw = match.group(0)

        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            logger.warning(f"[OllamaCivicAnalyzer] Invalid JSON from model: {raw[:200]}")
            return None

        # Validate required fields
        required = ["is_civic_related", "sentiment", "sentiment_score", "detected_language",
                    "urgency", "urgency_reasoning", "confidence_score"]
        for field in required:
            if field not in data:
                logger.warning(f"[OllamaCivicAnalyzer] Missing field '{field}' in response")
                return None

        return data

    def _safe_str(self, val, choices, default) -> str:
        return val if val in choices else default

    def _safe_float(self, val, lo, hi, default) -> float:
        try:
            v = float(val)
            return max(lo, min(hi, v))
        except (TypeError, ValueError):
            return default

    def _safe_int(self, val, lo, hi) -> Optional[int]:
        try:
            v = int(val)
            return v if lo <= v <= hi else None
        except (TypeError, ValueError):
            return None

    def analyze(self, raw_text: str, metadata: Optional[Dict[str, Any]] = None) -> CivicAnalysisResult:
        text = raw_text.strip()

        prompt = f"{SYSTEM_PROMPT}\n\nCitizen complaint text:\n\"\"\"\n{text}\n\"\"\"\n\nJSON:"

        raw_response = self._call_ollama(prompt)
        parsed = self._parse_response(raw_response) if raw_response else None

        if parsed is None:
            # Fallback to local rules if Ollama fails
            logger.warning("[OllamaCivicAnalyzer] Falling back to LocalCivicAnalyzer.")
            from .local_rules import LocalCivicAnalyzer
            fallback = LocalCivicAnalyzer()
            result = fallback.analyze(text, metadata)
            result.model_version = f"{self.version_identifier}-fallback"
            return result

        # Validate and sanitize all fields
        sentiment_choices = ["POSITIVE", "NEGATIVE", "NEUTRAL", "MIXED", "UNCERTAIN"]
        urgency_choices   = ["EMERGENCY", "HIGH", "MEDIUM", "LOW"]
        lang_choices      = ["gu", "hi", "en", "mixed", "und"]

        sentiment    = self._safe_str(parsed.get("sentiment", "").upper(), sentiment_choices, "NEUTRAL")
        urgency      = self._safe_str(parsed.get("urgency", "").upper(), urgency_choices, "MEDIUM")
        language     = self._safe_str(parsed.get("detected_language", ""), lang_choices, "und")
        sent_score   = self._safe_float(parsed.get("sentiment_score"), -1.0, 1.0, 0.0)
        confidence   = self._safe_float(parsed.get("confidence_score"), 0.0, 1.0, 0.6)
        ward_number  = self._safe_int(parsed.get("suggested_ward_number"), 1, 18)

        requires_review = bool(parsed.get("requires_human_review", False)) or confidence < 0.65 or urgency == "EMERGENCY"

        return CivicAnalysisResult(
            is_civic_related=bool(parsed.get("is_civic_related", True)),
            sentiment=sentiment,
            sentiment_score=sent_score,
            detected_language=language,
            category_code=parsed.get("category_code") or "miscellaneous",
            department_code=parsed.get("department_code") or "solid-waste-management",
            urgency=urgency,
            urgency_reasoning=str(parsed.get("urgency_reasoning", ""))[:500],
            extracted_location_name=parsed.get("extracted_location_name"),
            suggested_ward_number=ward_number,
            recurring_theme=str(parsed.get("recurring_theme", ""))[:150],
            short_summary=str(parsed.get("short_summary", text[:120]))[:255],
            confidence_score=confidence,
            requires_human_review=requires_review,
            model_version=self.version_identifier,
            raw_response=parsed,
        )


def is_ollama_available(base_url: str = "http://localhost:11434") -> bool:
    """Quick non-blocking health-check — returns True only if Ollama server is immediately reachable."""
    import socket
    from urllib.parse import urlparse
    try:
        parsed = urlparse(base_url)
        host = parsed.hostname or "127.0.0.1"
        port = parsed.port or 11434
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(0.2)
            s.connect((host, port))
            return True
    except Exception:
        return False
