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
    requires_spec: bool = False  # True = only run if spec document is uploaded
    context: str = "all"  # "all", "data_center", "commercial", "industrial"
    check_scope: str = "document"  # "document" = check once for whole doc, "per_equipment" = per item found


@dataclass
class ReviewFinding:
    check_id: str
    check_name: str
    category: str
    passed: int  # 1=pass, 0=fail, -1=needs_review
    details: str
    reference_standard: str
    severity: str
    page_number: Optional[int] = None  # 1-indexed page where issue was found


class BaseEquipmentChecker(ABC):
    """Abstract base for all equipment-type review checkers."""

    @abstractmethod
    def equipment_type(self) -> str:
        ...

    @abstractmethod
    def get_checklist(self) -> list[CheckItem]:
        ...

    def run_checks(self, extracted_text: str, metadata: dict) -> list[ReviewFinding]:
        """Run all checklist items against full PDF text (legacy, no page info)."""
        findings = []
        text_lower = extracted_text.lower()

        for item in self.get_checklist():
            finding = self._evaluate_check(item, text_lower, metadata)
            findings.append(finding)

        return findings

    def run_checks_by_page(self, pages: list[dict], metadata: dict) -> list[ReviewFinding]:
        """Run all checklist items page-by-page to identify which page each issue is on.

        pages: list of {"page": int, "text": str, "text_lower": str, "metadata": dict}
        """
        findings = []
        # Build full text for checks that need global context
        full_text = "\n".join(p["text_lower"] for p in pages)

        for item in self.get_checklist():
            # Get the specific keywords this check cares about
            keywords = self._extract_check_keywords(item)
            relevant_keywords = [kw for kw in keywords if len(kw) > 2]

            # Find which pages have content related to this check
            pages_with_content = []
            for page_data in pages:
                page_text = page_data["text_lower"]
                matched = sum(1 for kw in relevant_keywords if kw in page_text)
                if matched > 0:
                    pages_with_content.append((page_data["page"], matched, page_text))

            if pages_with_content:
                # Use the page with the most keyword matches
                pages_with_content.sort(key=lambda x: x[1], reverse=True)
                best_page_num = pages_with_content[0][0]
                best_page_text = pages_with_content[0][2]

                # Run the specific check against the best matching page
                finding = self._evaluate_check(item, best_page_text, metadata)
                finding.page_number = best_page_num

                # Add page context to details
                if "(Page" not in finding.details:
                    finding.details = f"(Page {best_page_num}) {finding.details}"
            else:
                # Not found on any page — check against full text as fallback
                finding = self._evaluate_check(item, full_text, metadata)
                if finding.passed == 1 or finding.passed == -1:
                    # Found in full text but not isolated to a page
                    finding.details = f"(Found in document) {finding.details}"

            findings.append(finding)

        return findings

    def _evaluate_check(self, item: CheckItem, text: str, metadata: dict) -> ReviewFinding:
        """Default evaluation — subclasses override for smarter checks.

        Logic:
        - If strong keywords are found → PASS with what was found
        - If nothing found → FAIL for critical/major, NEEDS REVIEW for minor/info
        - All messages are SPECIFIC — no "Related content found, verify..." garbage
        """
        keywords = self._extract_check_keywords(item)
        relevant = [kw for kw in keywords if len(kw) > 2]

        if not relevant:
            return self._needs_review(item,
                f"Manual review required — {item.check}. "
                f"Reference: {item.standard}.")

        matched = [kw for kw in relevant if kw in text]
        match_ratio = len(matched) / len(relevant) if relevant else 0

        if match_ratio >= 0.5:
            # Found — report what keywords confirmed it
            return self._pass(item,
                f"Confirmed in submittal: {item.check}")
        elif match_ratio > 0:
            # Partial — report what's present and what's missing
            missing = [kw for kw in relevant if kw not in text]
            return self._needs_review(item,
                f"{item.check} — partially addressed. "
                f"Confirm: {', '.join(missing[:3])} per {item.standard}.")
        else:
            # Not found — specific about what's missing and why it matters
            if item.severity == "critical":
                return self._fail(item,
                    f"{item.check} — NOT FOUND in submittal. "
                    f"Required per {item.standard}. This is a critical item "
                    f"that must be addressed before approval.")
            elif item.severity == "major":
                return self._fail(item,
                    f"{item.check} — not documented in submittal. "
                    f"Required per {item.standard}.")
            else:
                return self._needs_review(item,
                    f"{item.check} — not found. Verify per {item.standard}.")

    def _extract_check_keywords(self, item: CheckItem) -> list[str]:
        """Pull meaningful keywords from a check item for text matching."""
        return self._extract_keywords(item.check)

    def _extract_keywords(self, check_text: str) -> list[str]:
        """Pull meaningful keywords from check description for text matching."""
        stop_words = {
            "the", "and", "for", "are", "with", "has", "per", "meets",
            "match", "matches", "specified", "verify", "check", "ensure",
            "that", "from", "this", "been", "have", "not", "all", "any",
            "shall", "must", "should", "appropriate", "adequate", "properly",
            "clearly", "documented", "provided", "included", "present",
            "required", "rated", "rating", "type", "class",
        }
        words = check_text.lower().replace("(", "").replace(")", "").replace(",", "").split()
        return [w for w in words if w not in stop_words and len(w) > 2]

    # --- Helper methods for subclasses ---
    def _pass(self, item: CheckItem, details: str) -> ReviewFinding:
        return ReviewFinding(item.id, item.check, item.category, 1, details, item.standard, item.severity)

    def _fail(self, item: CheckItem, details: str) -> ReviewFinding:
        return ReviewFinding(item.id, item.check, item.category, 0, details, item.standard, item.severity)

    def _needs_review(self, item: CheckItem, details: str) -> ReviewFinding:
        return ReviewFinding(item.id, item.check, item.category, -1, details, item.standard, item.severity)
