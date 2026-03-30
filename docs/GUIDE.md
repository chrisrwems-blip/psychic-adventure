# ArcLight User Guide

A complete guide to using ArcLight for electrical submittal reviews.

---

## Table of Contents

1. [Getting Started](#getting-started)
2. [Projects](#projects)
3. [Uploading Submittals](#uploading-submittals)
4. [Running a Review](#running-a-review)
5. [Understanding Review Results](#understanding-review-results)
6. [Marking Up PDFs](#marking-up-pdfs)
7. [Approval Stamps](#approval-stamps)
8. [Comments](#comments)
9. [Emails & RFIs](#emails--rfis)
10. [Revision Comparison](#revision-comparison)
11. [Spec Validation](#spec-validation)
12. [Batch Review](#batch-review)
13. [Settings](#settings)
14. [Dark Mode](#dark-mode)
15. [Keyboard Shortcuts](#keyboard-shortcuts)
16. [FAQ](#faq)

---

## Getting Started

After building the .exe (see README), double-click **DC_Submittal_Review.exe**. Your browser opens to the ArcLight dashboard.

The main navigation bar has five sections:
- **Dashboard** — overview of all projects and stats
- **Comment Tracker** — all review comments across projects
- **RFI Tracker** — all Requests for Information
- **Register** — submittal register per project
- **Settings** (gear icon) — email, profile, and preferences

---

## Projects

### Creating a Project

1. From the Dashboard, click **New Project**
2. Fill in:
   - **Project Name** (required) — e.g., "Phoenix DC Build Phase 2"
   - **Client** — e.g., "JDA" or "WinDC"
   - **Location** — e.g., "Dallas, TX"
   - **Redundancy Tier** — I through IV
3. Click **Create**

### Navigating to a Project

Click any project card on the Dashboard. This opens the project detail page showing all submittals for that project.

---

## Uploading Submittals

### Single File

1. Open a project and click **Upload Submittal**
2. Drag a PDF into the drop zone, or click to browse
3. Fill in metadata:
   - **Title** (required) — e.g., "Main Switchgear MSB-1"
   - **Equipment Type** — leave as "Auto-Detect" (recommended) or pick manually
   - **Submittal Number** — e.g., "E-001"
   - **Manufacturer** — e.g., "ABB"
   - **Model Number**, **Spec Section**, **Submitted By**, **Contractor** — optional
4. Click **Upload & Create**

### Multiple Files (Batch)

1. Drag multiple PDFs into the drop zone at once, or click browse and select multiple files
2. Each file appears in a list with a remove button
3. Shared metadata (equipment type, manufacturer, contractor) applies to all files
4. Titles auto-derive from filenames — no need to type each one
5. Click **Upload & Review (N files)**
6. All files upload, then batch review starts automatically
7. A progress panel shows per-file status as reviews complete

---

## Running a Review

1. Click into a submittal from the project page
2. Click **Run Review**

ArcLight scans every page and automatically:
- Extracts text (with OCR fallback for scanned pages)
- Classifies each page (SLD, panel schedule, cable schedule, cut sheet, etc.)
- Detects all equipment (breakers, transformers, panels, cables, UPS, generators, etc.)
- Determines jurisdiction (NEC vs IEC) from voltage/frequency/standards found
- Selects the right checkers based on what equipment is in the document
- Runs 500+ individual checks across 13 equipment types
- Cross-references sizing, protection, and coordination
- Builds a power topology (what feeds what)
- Compares SLD designations against panel schedules

This typically takes 30 seconds to 2 minutes depending on the PDF size.

### Review Summary

After the review completes, a summary card shows:
- **Total Checks** — how many individual checks were run
- **Passed / Failed / Needs Review** — counts for each
- **Critical / Major Issues** — counts requiring action
- **Equipment Found** — expandable list of every piece of equipment detected, with page numbers
- **Page Classification** — breakdown of page types found
- **Recommendation** — APPROVED, APPROVED AS NOTED, or REVISE AND RESUBMIT

---

## Understanding Review Results

Results are shown in the **Review Results** tab with three viewing options:

### Sorting
- **Severity** — groups by Critical, Major, Minor, Info
- **Status** — groups by FAIL, NEEDS REVIEW, PASS
- **Category** — groups by check category (Ratings, Protection, Grounding, etc.)

### Filtering
- **All** — show everything
- **Failures** — only failed checks
- **Needs Review** — items that couldn't be confirmed automatically
- **Passed** — only passing checks

### Expanding a Finding

Click any finding to expand it. You'll see:

1. **Finding Details** — full description of the issue with specific values found in the document (e.g., "Breaker Q2 E2.2H 1600A — NEC 240.87 requires arc energy reduction for 1200A+")
2. **Code Reference** — the specific NEC/IEEE article, with a plain-English explanation of why it matters
3. **Recommended Action** — what needs to be done to resolve the finding
4. **View Page in PDF** — links to jump directly to the relevant page in the PDF viewer

### What the Statuses Mean

| Status | Meaning |
|--------|---------|
| **PASS** | Meets the standard — no action needed |
| **FAIL** | Does not meet the standard — must be addressed |
| **NEEDS REVIEW** | Could not be confirmed from the submittal — requires manual verification by the engineer |

---

## Marking Up PDFs

1. Click **Mark Up PDF** (purple button)
2. ArcLight generates an annotated version of the submittal with:
   - A **summary page** added at the front listing all findings
   - **Color-coded annotations** on each page where issues were found:
     - Red = Critical
     - Orange = Major
     - Yellow = Minor
     - Blue = Info
3. The **View PDF** tab automatically switches to show the marked-up version
4. Toggle between **Original PDF** and **Marked Up PDF** using the buttons
5. Navigate pages with the arrow buttons or type a page number

### Downloading

- Click **Download Marked Up PDF** (green button) to save the annotated PDF
- This is the file you send back to the contractor or vendor
- The **Mark Up PDF** button does NOT trigger a download — it only generates the annotations

---

## Approval Stamps

1. Expand the **Apply Review Stamp** section on the submittal review page
2. Select a disposition:
   - **Approved**
   - **Approved as Noted**
   - **Revise & Resubmit**
   - **Rejected**
3. The **Reviewed by** field auto-fills from your profile (set in Settings)
4. Click **Apply Stamp & Download**
5. A stamped PDF downloads with:
   - A colored stamp box in the upper-right corner of the first page
   - Your name, the date, project name, and submittal title
   - A diagonal watermark across the page

---

## Comments

### In the Submittal Review Page

The **Comments** tab on each submittal shows:
- Auto-generated comments from the review (critical and major failures)
- Manually added comments
- Sort by severity, status, or date
- Add new comments with severity level and NEC reference code

### In the Comment Tracker (Global)

Access via the **Comment Tracker** link in the top navigation. This shows all comments across all projects.

**Actions on each comment:**
- **Green checkmark** — resolve the comment
- **Red X** — reject/defer the comment
- **Chat bubble** — add a note or reply

**Adding notes:**
1. Click the chat bubble icon on any comment
2. Type your note, or click a **quick template** to insert common responses:
   - "Verify NEC compliance — provide code reference"
   - "Provide voltage drop / sizing calculation"
   - "Clarify coordination with upstream OCPD"
   - "Resubmit with revised drawing"
   - "Confirm UL listing for US installation"
   - "Provide arc flash incident energy label"
3. Choose an action:
   - **Save Note** — adds the note without changing status
   - **Resolve with Note** — resolves and adds the note
   - **Reject with Note** — defers and adds the note

Notes are threaded — multiple notes on the same comment display as a conversation history.

**Filtering:**
- Status: Open, Resolved, Deferred
- Severity: Critical, Major, Minor, Info
- Project: filter to a specific project

---

## Emails & RFIs

### Generating an Email

1. Go to the **Emails** tab on a submittal review page
2. Select the email type:
   - **RFI** — formal Request for Information with response deadline
   - **Clarification** — asking for specific details
   - **Rejection** — REVISE AND RESUBMIT with critical issues listed
   - **Approval** — APPROVED or APPROVED AS NOTED
3. Enter recipient email address
4. Add any additional notes (optional)
5. Click **Generate Email**

The email auto-includes:
- All open comments grouped by severity (Critical, Major, Minor)
- NEC code references for each item
- Your name, title, and company from Settings
- Response deadline based on your configured SLA (default 5 days for RFIs)

### Sending an Email

If you've configured email in Settings:
1. Enter the recipient address in the **Send** field below the email preview
2. Click **Send** (green button)
3. A green checkmark confirms delivery

If email isn't configured, use **Copy** to copy the text and paste into Outlook.

### RFI Tracker

Access via the **RFI Tracker** link in the top navigation. Track RFIs through their lifecycle:
- **Draft** — generated but not sent
- **Sent** — sent to the contractor
- **Responded** — contractor has responded
- **Closed** — resolved and closed

---

## Revision Comparison

When a contractor resubmits after making changes:

1. Open the original submittal's review page
2. Expand **Compare with Revision (upload Rev B)**
3. Upload the revised PDF
4. ArcLight compares both and shows:
   - **Total Changes** — number of differences found
   - **Added** — new equipment in Rev B that wasn't in Rev A
   - **Removed** — equipment removed from Rev B
   - **Modified** — equipment with changed ratings (old value → new value highlighted)

---

## Spec Validation

Validate a submittal against a Division 26 specification:

1. Open a submittal's review page
2. Expand **Validate Against Spec (upload Division 26)**
3. Upload the spec PDF
4. ArcLight extracts spec requirements and cross-checks the submittal against them
5. Results show how many requirements were found and any deviations

---

## Batch Review

Upload and review multiple submittals simultaneously:

1. Open a project and click **Upload Submittal**
2. Drag multiple PDFs into the drop zone (or select multiple files)
3. Each file appears in a list — remove any you don't want
4. Shared metadata applies to all files; titles come from filenames
5. Click **Upload & Review (N files)**
6. A progress panel appears showing:
   - Per-file status (spinning = reviewing, checkmark = done)
   - Overall progress bar
   - "View Report" links as each review completes
7. Polling stops automatically when all reviews finish

Reviews run in parallel (up to 4 at once). If one fails, the others continue.

---

## Settings

Access Settings via the **gear icon** in the top-right of the navigation bar.

### Email Configuration

Connect your email to send RFIs and review emails directly from ArcLight.

1. Enter your **email address** — SMTP settings auto-detect for Gmail, Outlook, Yahoo, iCloud
2. Enter your **password** (or app password if you use two-factor authentication)
3. Set your **display name**
4. Click **Test Connection** to verify
5. Click **Save Settings**

**Two-factor authentication:** Gmail and Outlook require an "app-specific password" instead of your regular password. The settings page shows provider-specific instructions when detected.

**Advanced settings:** Click "Advanced Settings" to manually configure the SMTP host and port for custom email domains.

### Reviewer & Company

Pre-fills approval stamps, email signatures, and report cover pages.

- **Reviewer Name** — appears on stamps ("Reviewed by: ...") and email signatures
- **Title** — e.g., "Senior Electrical Engineer"
- **Company Name** — appears on report cover pages and email signatures
- **Company Address** and **Phone** — included in email signatures

### Review Preferences

- **Default Jurisdiction** — NEC (US), IEC (International), AS/NZS (Australia/NZ), or Auto-Detect
- **Review SLA** — default deadline for RFI responses (3, 5, 7, 10, or 14 days)
- **Report Min Severity** — minimum severity level included in generated reports (Critical only, Critical+Major, Critical+Major+Minor, or All)

### Vision AI (Ollama)

Optional local AI for analyzing scanned drawings and equipment nameplates. Requires:
1. Ollama installed (ollama.com)
2. LLaVA model pulled: `ollama pull llava`
3. ArcLight detects it automatically when Ollama is running

---

## Dark Mode

Click the **moon/sun icon** in the navigation bar to toggle dark mode. Your preference is saved and persists across sessions. If no preference is set, ArcLight follows your operating system's theme.

---

## Keyboard Shortcuts

| Shortcut | Action |
|----------|--------|
| **Esc** | Close any open modal |

---

## FAQ

**Q: How long does a review take?**
Typically 30 seconds to 2 minutes depending on the PDF size. Large submittals (400+ pages) may take longer on the first review due to text extraction.

**Q: Does ArcLight send data to the cloud?**
No. Everything runs locally on your machine. No data leaves your computer unless you explicitly send an email or use the Claude API for vision analysis (optional, not required).

**Q: What if the review says NEEDS REVIEW?**
This means ArcLight couldn't confirm or deny the check from the submittal content. It's not a failure — it just needs a human to verify. Common for items that require information not present in the PDF (e.g., field conditions, verbal agreements, specs not included).

**Q: Can I review non-electrical submittals?**
ArcLight is designed for electrical submittals (power distribution, cooling, fire protection). It won't produce useful results for mechanical, structural, or architectural submittals.

**Q: What PDF formats are supported?**
Any standard PDF. For scanned documents without embedded text, install Tesseract OCR for automatic text recognition. ArcLight works without it but may miss content on scanned pages.

**Q: Can multiple people use ArcLight on the same project?**
Currently ArcLight is a single-user desktop tool. Multiple engineers can each run their own instance with their own database. Shared project support would require a server deployment.

**Q: How do I reset the database and start fresh?**
Delete the `submittal_review.db` file in the application directory and restart. A new empty database will be created automatically.

**Q: What NEC edition does ArcLight use?**
NEC 2023 (NFPA 70). Code references in findings cite specific articles from the 2023 edition.

**Q: Can I add my own checks?**
The review engine is modular — each equipment type has its own checker file in `backend/app/review_engine/`. Adding a new check means adding an entry to the `get_checklist()` method in the relevant checker. See the developer documentation for details.
