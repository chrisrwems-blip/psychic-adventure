"""
Pattern Learning Service

Tracks engineer feedback on findings to learn which finding types are
consistently actionable vs. noise. Over time, suppresses low-value findings
and boosts high-value ones.
"""

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.database_models import FindingFeedback


def record_feedback(
    db: Session,
    submittal_id: int,
    finding_type: str,
    check_name: str,
    action: str,
    notes: str | None = None,
) -> FindingFeedback:
    """Save engineer feedback on a specific finding."""
    feedback = FindingFeedback(
        submittal_id=submittal_id,
        finding_type=finding_type,
        check_name=check_name,
        action=action,
        engineer_notes=notes,
    )
    db.add(feedback)
    db.commit()
    db.refresh(feedback)
    return feedback


def _get_feedback_rates(db: Session) -> dict[str, dict]:
    """
    Calculate agree/dismiss/modify rates per finding_type.

    Returns dict keyed by finding_type with counts and percentages.
    """
    rows = (
        db.query(
            FindingFeedback.finding_type,
            FindingFeedback.action,
            func.count(FindingFeedback.id),
        )
        .group_by(FindingFeedback.finding_type, FindingFeedback.action)
        .all()
    )

    stats: dict[str, dict] = {}
    for finding_type, action, count in rows:
        if finding_type not in stats:
            stats[finding_type] = {"agreed": 0, "dismissed": 0, "modified": 0, "total": 0}
        if action in stats[finding_type]:
            stats[finding_type][action] = count
        stats[finding_type]["total"] += count

    # Calculate percentages
    for finding_type, data in stats.items():
        total = data["total"]
        if total > 0:
            data["agree_rate"] = round(data["agreed"] / total * 100, 1)
            data["dismiss_rate"] = round(data["dismissed"] / total * 100, 1)
            data["modify_rate"] = round(data["modified"] / total * 100, 1)
        else:
            data["agree_rate"] = 0.0
            data["dismiss_rate"] = 0.0
            data["modify_rate"] = 0.0

    return stats


def get_suppression_list(db: Session) -> list[dict]:
    """
    Returns finding_types that are dismissed >70% of the time.

    These are likely noise and should be suppressed or deprioritized.
    Requires at least 3 feedback records to avoid premature suppression.
    """
    stats = _get_feedback_rates(db)
    suppressed = []
    for finding_type, data in stats.items():
        if data["total"] >= 3 and data["dismiss_rate"] > 70:
            suppressed.append({
                "finding_type": finding_type,
                "dismiss_rate": data["dismiss_rate"],
                "total_feedback": data["total"],
            })
    return sorted(suppressed, key=lambda x: x["dismiss_rate"], reverse=True)


def get_priority_list(db: Session) -> list[dict]:
    """
    Returns finding_types that are agreed >80% of the time.

    These are consistently actionable and should be boosted to the top.
    Requires at least 3 feedback records to confirm the pattern.
    """
    stats = _get_feedback_rates(db)
    prioritized = []
    for finding_type, data in stats.items():
        if data["total"] >= 3 and data["agree_rate"] > 80:
            prioritized.append({
                "finding_type": finding_type,
                "agree_rate": data["agree_rate"],
                "total_feedback": data["total"],
            })
    return sorted(prioritized, key=lambda x: x["agree_rate"], reverse=True)


def apply_learning(findings: list[dict], db: Session) -> list[dict]:
    """
    Filter and reorder findings based on historical feedback patterns.

    Each finding dict is expected to have at least a 'finding_type' key.
    This function:
      - Suppresses finding_types with >70% dismiss rate (moved to bottom, marked "likely noise")
      - Boosts finding_types with >80% agree rate (moved to top)
      - Adds a confidence indicator showing historical actionability rate
    """
    stats = _get_feedback_rates(db)

    boosted = []
    normal = []
    suppressed = []

    for finding in findings:
        finding_type = finding.get("finding_type", "")
        data = stats.get(finding_type)

        if data and data["total"] >= 3:
            actionable_rate = round(
                (data["agreed"] + data["modified"]) / data["total"] * 100, 1
            )
            finding["confidence"] = (
                f"Based on past reviews, this type of finding is {actionable_rate}% actionable"
            )
            finding["actionable_rate"] = actionable_rate
            finding["feedback_count"] = data["total"]

            if data["dismiss_rate"] > 70:
                finding["suppressed"] = True
                finding["suppression_reason"] = (
                    f"Dismissed {data['dismiss_rate']}% of the time "
                    f"({data['total']} reviews) — likely noise"
                )
                suppressed.append(finding)
            elif data["agree_rate"] > 80:
                finding["boosted"] = True
                finding["boost_reason"] = (
                    f"Agreed {data['agree_rate']}% of the time "
                    f"({data['total']} reviews) — consistently actionable"
                )
                boosted.append(finding)
            else:
                normal.append(finding)
        else:
            # Not enough data yet — leave as-is
            if data:
                finding["confidence"] = (
                    f"Limited data ({data['total']} reviews) — needs more feedback"
                )
                finding["feedback_count"] = data["total"]
            else:
                finding["confidence"] = "No historical feedback yet"
                finding["feedback_count"] = 0
            normal.append(finding)

    # Return boosted first, then normal, then suppressed at the bottom
    return boosted + normal + suppressed
