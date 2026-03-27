"""Generate RFI and clarification emails from review findings."""
from datetime import datetime, timezone, timedelta
from sqlalchemy.orm import Session

from app.models.database_models import Submittal, ReviewComment, GeneratedEmail, Project


def generate_email(
    db: Session,
    submittal_id: int,
    email_type: str = "clarification",
    recipients: str = "",
    additional_notes: str = "",
) -> GeneratedEmail:
    """Generate a professional email based on review comments."""
    submittal = db.query(Submittal).filter(Submittal.id == submittal_id).first()
    if not submittal:
        raise ValueError(f"Submittal {submittal_id} not found")

    project = db.query(Project).filter(Project.id == submittal.project_id).first()

    # Get open comments
    comments = (
        db.query(ReviewComment)
        .filter(ReviewComment.submittal_id == submittal_id, ReviewComment.status == "open")
        .all()
    )

    if email_type == "rfi":
        subject, body = _build_rfi_email(project, submittal, comments, additional_notes)
    elif email_type == "clarification":
        subject, body = _build_clarification_email(project, submittal, comments, additional_notes)
    elif email_type == "rejection":
        subject, body = _build_rejection_email(project, submittal, comments, additional_notes)
    elif email_type == "approval":
        subject, body = _build_approval_email(project, submittal, comments, additional_notes)
    else:
        subject, body = _build_clarification_email(project, submittal, comments, additional_notes)

    email = GeneratedEmail(
        submittal_id=submittal_id,
        email_type=email_type,
        subject=subject,
        body=body,
        recipients=recipients,
    )
    db.add(email)
    db.commit()
    db.refresh(email)
    return email


def _build_rfi_email(project, submittal, comments, notes):
    project_name = project.name if project else "Project"
    response_date = (datetime.now(timezone.utc) + timedelta(days=7)).strftime("%B %d, %Y")

    subject = f"RFI - {project_name} - {submittal.equipment_type.upper()} Submittal Review - {submittal.title}"

    critical = [c for c in comments if c.severity == "critical"]
    major = [c for c in comments if c.severity == "major"]
    minor = [c for c in comments if c.severity in ("minor", "info")]

    body = f"""Subject: {subject}

To: {submittal.contractor or '[Contractor Name]'}
From: [Engineer of Record]
Date: {datetime.now(timezone.utc).strftime("%B %d, %Y")}
Project: {project_name}
Re: {submittal.title}
Submittal No: {submittal.submittal_number or 'N/A'}
Equipment Type: {submittal.equipment_type.replace('_', ' ').title()}
Manufacturer: {submittal.manufacturer or 'N/A'}

Dear {submittal.contractor or '[Contractor]'},

We have completed our review of the above-referenced submittal. The following items require your response and/or clarification before we can proceed with approval.

Please respond to each item below by {response_date}.
"""

    item_num = 1

    if critical:
        body += "\n--- CRITICAL ITEMS (Must be resolved before approval) ---\n\n"
        for c in critical:
            ref = f" [{c.reference_code}]" if c.reference_code else ""
            body += f"{item_num}. {c.comment_text}{ref}\n"
            item_num += 1

    if major:
        body += "\n--- MAJOR ITEMS (Require clarification) ---\n\n"
        for c in major:
            ref = f" [{c.reference_code}]" if c.reference_code else ""
            body += f"{item_num}. {c.comment_text}{ref}\n"
            item_num += 1

    if minor:
        body += "\n--- MINOR ITEMS (For information/correction) ---\n\n"
        for c in minor:
            ref = f" [{c.reference_code}]" if c.reference_code else ""
            body += f"{item_num}. {c.comment_text}{ref}\n"
            item_num += 1

    if notes:
        body += f"\n--- ADDITIONAL NOTES ---\n\n{notes}\n"

    body += f"""
Please provide written responses to each item above. Revised submittals should clearly indicate all changes made in response to these comments.

If you have any questions regarding this review, please do not hesitate to contact us.

Regards,
[Engineer of Record]
[Company Name]
[Phone / Email]
"""
    return subject, body


def _build_clarification_email(project, submittal, comments, notes):
    project_name = project.name if project else "Project"
    subject = f"Clarification Request - {project_name} - {submittal.title}"

    body = f"""Subject: {subject}

To: {submittal.contractor or '[Contractor Name]'}
Date: {datetime.now(timezone.utc).strftime("%B %d, %Y")}
Project: {project_name}
Re: {submittal.title} (Submittal No: {submittal.submittal_number or 'N/A'})

Dear {submittal.contractor or '[Contractor]'},

During our review of the above submittal, we identified the following items that require clarification:

"""
    for i, c in enumerate(comments, 1):
        ref = f" (Ref: {c.reference_code})" if c.reference_code else ""
        body += f"{i}. {c.comment_text}{ref}\n"

    if notes:
        body += f"\nAdditional Notes: {notes}\n"

    body += """
Please provide your response at your earliest convenience so we may continue our review.

Regards,
[Engineer of Record]
"""
    return subject, body


def _build_rejection_email(project, submittal, comments, notes):
    project_name = project.name if project else "Project"
    subject = f"Submittal Rejected - Revise & Resubmit - {project_name} - {submittal.title}"

    body = f"""Subject: {subject}

To: {submittal.contractor or '[Contractor Name]'}
Date: {datetime.now(timezone.utc).strftime("%B %d, %Y")}
Project: {project_name}
Re: {submittal.title} (Submittal No: {submittal.submittal_number or 'N/A'})

Dear {submittal.contractor or '[Contractor]'},

The above-referenced submittal has been reviewed and is being returned with a status of REVISE AND RESUBMIT. The following critical issues must be addressed:

"""
    for i, c in enumerate(comments, 1):
        severity_tag = f"[{c.severity.upper()}] " if c.severity else ""
        ref = f" (Ref: {c.reference_code})" if c.reference_code else ""
        body += f"{i}. {severity_tag}{c.comment_text}{ref}\n"

    if notes:
        body += f"\nAdditional Notes: {notes}\n"

    body += """
Please address ALL items above and resubmit for review. Do not proceed with fabrication or procurement until an approved submittal is received.

Regards,
[Engineer of Record]
"""
    return subject, body


def _build_approval_email(project, submittal, comments, notes):
    project_name = project.name if project else "Project"
    has_comments = len(comments) > 0
    status = "APPROVED AS NOTED" if has_comments else "APPROVED"
    subject = f"Submittal {status} - {project_name} - {submittal.title}"

    body = f"""Subject: {subject}

To: {submittal.contractor or '[Contractor Name]'}
Date: {datetime.now(timezone.utc).strftime("%B %d, %Y")}
Project: {project_name}
Re: {submittal.title} (Submittal No: {submittal.submittal_number or 'N/A'})

Dear {submittal.contractor or '[Contractor]'},

The above-referenced submittal has been reviewed and is {status}.

"""
    if has_comments:
        body += "Please note the following comments:\n\n"
        for i, c in enumerate(comments, 1):
            ref = f" (Ref: {c.reference_code})" if c.reference_code else ""
            body += f"{i}. {c.comment_text}{ref}\n"

    if notes:
        body += f"\nAdditional Notes: {notes}\n"

    body += """
This approval does not relieve the contractor of responsibility to comply with the contract documents and applicable codes.

Regards,
[Engineer of Record]
"""
    return subject, body
