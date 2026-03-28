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

        for item in self.get_checklist():
            # Search each page for content related to this check
            keywords = self._extract_keywords(item.check)
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

                # If the check found content, add page context to details
                if finding.passed != 0:
                    finding.details = f"(Page {best_page_num}) {finding.details}"
            else:
                # Not found on any page — run against empty to get a fail
                finding = self._evaluate_check(item, "", metadata)
                # No page_number since it wasn't found anywhere

            findings.append(finding)

        return findings

    def _evaluate_check(self, item: CheckItem, text: str, metadata: dict) -> ReviewFinding:
        """Default evaluation — subclasses override for smarter checks."""
        keywords = self._extract_keywords(item.check)
        found_any = any(kw in text for kw in keywords if len(kw) > 2)

        if found_any:
            return ReviewFinding(
                check_id=item.id,
                check_name=item.check,
                category=item.category,
                passed=-1,
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
