from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Optional, Dict, Any

@dataclass
class CivicAnalysisResult:
    """
    Standardized, validated output contract for any civic AI analyzer.
    Preserves confidence scores, evidence-backed urgency reasoning, and location grounding.
    """
    is_civic_related: bool
    sentiment: str                 # POSITIVE, NEGATIVE, NEUTRAL, MIXED, UNCERTAIN
    sentiment_score: float         # -1.0 to 1.0
    detected_language: str         # gu, hi, en, mixed, und
    category_code: Optional[str]   # e.g. 'main-line-overflowing', 'potholes'
    department_code: Optional[str] # e.g. 'drainage-chockup-overflow', 'bandhkam-civil-roads'
    urgency: str                   # EMERGENCY, HIGH, MEDIUM, LOW
    urgency_reasoning: str
    extracted_location_name: Optional[str] = None
    suggested_ward_number: Optional[int] = None
    recurring_theme: str = ""
    short_summary: str = ""
    confidence_score: float = 0.0  # 0.0 to 1.0
    requires_human_review: bool = False
    model_version: str = "base-v1"
    raw_response: Dict[str, Any] = field(default_factory=dict)


class BaseCivicAnalyzer(ABC):
    """
    Abstract interface for PULSE civic sentiment & issue analyzers.
    Enables plug-and-play swapping between offline rule-based engines and cloud LLM providers.
    """
    version_identifier: str = "base-analyzer"

    @abstractmethod
    def analyze(self, raw_text: str, metadata: Optional[Dict[str, Any]] = None) -> CivicAnalysisResult:
        """
        Analyzes raw citizen feedback across Gujarati, Hindi, English, and Gujlish.
        Returns a validated CivicAnalysisResult.
        """
        pass
