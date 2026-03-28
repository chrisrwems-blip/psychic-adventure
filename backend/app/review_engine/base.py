from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class CheckItem:
    id: str
    check: str
    category: str
    standard: str
    severity: str  # critical, major, minor, info


@dataclass
class ReviewFinding:
    check_id: str
    check_name: str
    category: str
    passed: int  # 1=pass, 0=fail, -1=needs_review
    details: str
    reference_standard: str
    severity: str
    page_hint: Optional[int] = None


class BaseEquipmentChecker(ABC):
    """Abstract base for all equipment-type review checkers."""

    @abstractmethod
    def equipment_type(self) -> str:
        ...

    @abstractmethod
    def get_checklist(self) -> list[CheckItem]:
        ...

    def run_checks(self, extracted_text: str, metadata: dict) -> list[ReviewFinding]:
        """Run all checklist items against extracted PDF data.

        For each check, tries to find relevant data in the text.
        If data is found, attempts to validate. If not found, marks as needs_review.
        """
        findings = []
        text_lower = extracted_text.lower()

        for item in self.get_checklist():
            finding = self._evaluate_check(item, text_lower, metadata)
            findings.append(finding)

        return findings

    def _evaluate_check(self, item: CheckItem, text: str, metadata: dict) -> ReviewFinding:
        """Default evaluation — subclasses override for smarter checks."""
        # Look for keywords related to this check
        keywords = self._extract_keywords(item.check)
        found_any = any(kw in text for kw in keywords if len(kw) > 2)

        if found_any:
            return ReviewFinding(
                check_id=item.id,
                check_name=item.check,
                category=item.category,
                passed=-1,  # needs human review but data appears present
                details=f"Related content found in submittal. Verify: {item.check}",
                reference_standard=item.standard,
                severity=item.severity,
            )
        else:
            return ReviewFinding(
                check_id=item.id,
                check_name=item.check,
                category=item.category,
                passed=0 if item.severity in ("critical", "major") else -1,
                details=f"Could not locate relevant data. Manually verify: {item.check}",
                reference_standard=item.standard,
                severity=item.severity,
            )

    def _extract_keywords(self, check_text: str) -> list[str]:
        """Pull meaningful keywords from check description for text matching."""
        stop_words = {
            "the", "and", "for", "are", "with", "has", "per", "meets",
            "match", "matches", "specified", "verify", "check", "ensure",
            "that", "from", "this", "been", "have", "not", "all", "any",
            "shall", "must", "should", "appropriate", "adequate", "properly",
            "clearly", "documented", "provided", "included", "present",
        }
        words = check_text.lower().replace("(", "").replace(")", "").replace(",", "").split()
        return [w for w in words if w not in stop_words and len(w) > 2]
