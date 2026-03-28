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
        - If strong keywords are found → PASS (data is present in submittal)
        - If nothing found → FAIL for critical/major, NEEDS REVIEW for minor/info
        """
        keywords = self._extract_check_keywords(item)
        relevant = [kw for kw in keywords if len(kw) > 2]

        if not relevant:
            # No meaningful keywords to check — mark as needs review
            return self._needs_review(item, f"Manual verification required: {item.check}")

        matched_count = sum(1 for kw in relevant if kw in text)
        match_ratio = matched_count / len(relevant) if relevant else 0

        if match_ratio >= 0.5:
            # Strong match — data appears to be present
            return self._pass(item, f"Data found in submittal. Verified present: {item.check}")
        elif match_ratio > 0:
            # Partial match — something relevant is there but not complete
            return self._needs_review(item, f"Partial data found. Verify completeness: {item.check}")
        else:
            # Nothing found
            return self._fail(item, f"Not found in submittal. Must verify: {item.check}")

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
