# DC Submittal Review Platform

A desktop tool for electrical engineers reviewing submittals on modular data center projects.

## What This Tool Does

- **Upload submittal PDFs** for any major equipment type (switchgear, UPS, PDUs, generators, transformers, ATS, cables, bus ducts, panelboards, RPPs, STS, batteries, cooling units)
- **Automated review against NEC, NFPA, IEEE, UL, and Uptime Tier standards** -- 31 cross-reference checks, protection coordination analysis, arc flash estimation, SLD-to-schedule validation, topology tracking, ABB/Eaton/Schneider/Siemens product validation, jurisdiction detection, pattern learning from engineer feedback
- **SLD vs panel schedule cross-check** -- automatically compares every breaker designation between the single-line diagram and the detailed schedules, flagging frame size, trip rating, kAIC, and model mismatches
- **Mark up PDFs with comments** -- generates a marked-up PDF with severity-coded annotations and a summary page you can send back to the vendor
- **Generate RFI and response emails** -- auto-writes RFI, clarification, rejection, or approval emails grouped by severity, ready to copy into Outlook
- **Track comments across projects** -- filter open, resolved, and deferred items by severity, equipment type, and project
- **Revision comparison** -- upload Rev B and see exactly what changed from Rev A (new equipment, removed items, changed ratings)
- **Export professional review reports** -- generate a standalone PDF report with cover page, executive summary, and findings table
- **AI vision analysis** (optional) -- uses Ollama (free, local) or Claude API to read drawings that don't have text layers

---

## Step 1: Install Prerequisites (One-Time Setup)

You need to install three programs. If you already have any of them, skip that one.

### Python

1. Go to **https://www.python.org/downloads/**
2. Click the big yellow **"Download Python"** button
3. Run the installer
4. **IMPORTANT: On the very first screen of the installer, CHECK the box that says "Add Python to PATH."** If you miss this, the tool will not work.
5. Click "Install Now" and let it finish

### Node.js

1. Go to **https://nodejs.org/**
2. Click the **LTS** button (the one on the left -- LTS means Long Term Support, it is the stable version)
3. Run the installer and click Next through all the screens -- the defaults are fine

### Git

1. Go to **https://git-scm.com/download/win**
2. The download should start automatically. If not, click the link for the latest version
3. Run the installer and **keep clicking Next for every screen** -- all the defaults are fine
4. Click Install, then Finish

---

## Step 2: Download the Tool

1. Click the **Start** menu (Windows icon, bottom-left of your screen)
2. Type **PowerShell** and click **Windows PowerShell** when it appears
3. A blue window will open. Type (or copy and paste) these commands one at a time, pressing **Enter** after each one:

```
cd ~
git clone https://github.com/chrisrwems-blip/psychic-adventure.git
cd psychic-adventure
git checkout claude/submittal-review-platform-tmhtv
```

You only need to do this once. The tool is now saved in a folder called **psychic-adventure** inside your user folder (for example, `C:\Users\JSmith\psychic-adventure`).

You can close PowerShell now.

---

## Step 3: Run It

1. Open **File Explorer** (the folder icon on your taskbar)
2. In the address bar at the top, type `C:\Users\YourName\psychic-adventure` (replace **YourName** with your Windows username -- for example, `C:\Users\JSmith\psychic-adventure`) and press Enter
3. Double-click **DC Submittal Review.bat**
4. A black terminal window will appear. The first time you run it, it will take a few minutes because it is downloading and installing dependencies -- this is normal, let it finish
5. When it is ready, your web browser will open automatically to **http://localhost:5173** -- this is the tool running on your own computer

### To run without a terminal window sitting open

Double-click **DC Submittal Review.vbs** instead. This does the same thing but hides the terminal window so it runs quietly in the background.

---

## Step 4: How to Use

### 1. Create a Project

- Click **"New Project"** on the home screen
- Enter a project name (for example, "Phoenix DC Module 3") and select the **Tier level** (I, II, III, or IV)
- Click **Create**

### 2. Upload a Submittal PDF

- Open your project and click **"Upload Submittal"**
- Select a PDF from your computer
- Pick the **equipment type** from the dropdown (Switchgear, UPS, Generator, etc.)
- Fill in the manufacturer name and contractor info if you have it
- Click **Upload**

### 3. Run the Automated Review

- Click **"Run Review"**
- The tool scans every page, extracts all equipment, builds the system topology, and runs all applicable checks:
  - **SLD-to-schedule cross-check** -- compares every Q-designation between the SLD and breaker schedules
  - **Fault current coordination** -- estimates AFC and flags undersized interrupting ratings
  - **NEC code compliance** -- 240.4, 240.87, 230.95, 110.9, 110.24, 250.122, 408.36, 450.3
  - **UL listing verification** -- scans every cut sheet for IEC-only certification in NEC jurisdiction
  - **ABB/Eaton/Schneider product validation** -- verifies frame/trip combos are real products
  - **Naming consistency** -- flags mismatched labels between SLD and schedules
  - **Missing drawings** -- flags if bottom view (cable entry) is not provided
  - **Fuse schedule** -- flags if fuses are referenced but no fuse schedule exists
  - **Cable congestion** -- flags high-density cable ways
- This usually takes 30 seconds to a couple of minutes depending on the PDF size

### 4. Review the Findings

- Each check shows one of three results:
  - **PASS** -- meets the standard
  - **FAIL** -- does not meet the standard (includes the specific code reference)
  - **NEEDS REVIEW** -- could not be confirmed from the submittal, requires manual review
- **Click any finding** to expand it and see:
  - **Finding Details** -- full description of the issue
  - **Code Reference** -- the specific NEC/IEEE article
  - **Recommended Action** -- what needs to be done
  - **View Page in PDF** -- jump directly to the relevant page
- Sort by Severity, Status, or Category using the buttons at the top
- Filter to show only Failures, Needs Review, or Passed items

### 5. Mark Up the PDF

- Click **"Mark Up PDF"** -- the tool switches to the **View PDF** tab and shows your submittal with all comments overlaid directly on the pages
- Annotations are color-coded by severity (red for critical, orange for major, yellow for minor, blue for info)
- A summary page is added at the front with all findings listed

### 6. Download the Marked-Up PDF

- Click **"Download Marked Up PDF"** (green button) to save the marked-up PDF to your computer
- This is the file you send back to the vendor or contractor
- The "Mark Up PDF" button does NOT trigger a download -- it only generates the markup for viewing

### 7. Export a Review Report

- Go to `http://localhost:8000/api/reviews/1/report` (replace 1 with your submittal ID)
- Downloads a professional PDF report with cover page, executive summary, and detailed findings table

### 8. Generate Emails

- Go to the **Emails** tab
- Pick the email type:
  - **RFI** -- Request for Information, asking for missing data
  - **Clarification** -- asking the vendor to clarify something
  - **Rejection** -- rejecting the submittal with specific reasons
  - **Approval** -- approving (with or without comments)
- Click **Generate** -- the tool writes the full email body with all relevant findings grouped by severity
- Copy and paste into Outlook, or click **"Copy to Clipboard"**

### 9. Compare Revisions

- When you receive Rev B, upload it through the revision comparison endpoint
- The tool diffs Rev A vs Rev B: new equipment, removed items, changed ratings, modified pages
- See exactly what the vendor changed between submittals

### 10. Track Comments Across Projects

- Click **Comment Tracker** in the top navigation
- See all comments across all your projects in one place
- Filter by status (Open, Resolved, Deferred), severity, equipment type, or project name

---

## Stopping the App

- If you used **DC Submittal Review.bat**: just close the black terminal window
- If you used **DC Submittal Review.vbs** (no visible window): press **Ctrl+Shift+Esc** to open Task Manager, look for **"python"** in the list, click it, and click **End Task**

---

## Updating the Tool

When a new version is available:

1. Open **PowerShell** (search "PowerShell" in the Start menu)
2. Run these commands:

```
cd C:\Users\YourName\psychic-adventure
git pull
```

Replace **YourName** with your Windows username. Close PowerShell when it finishes.

---

## Equipment Types Supported

| Equipment Type | Checks | Key Standards |
|----------------|--------|---------------|
| Switchgear | 33 | NEC 408, IEEE C37.20, NFPA 70E |
| UPS | 37 | IEEE 446, NEC 480, UL 1778 |
| Generator | 43 | NFPA 110, EPA Tier 4, ISO 8528 |
| PDU | 29 | IEEE C57.110, NEC 210/215 |
| Transformer | 29 | IEEE C57, NEC 450, DOE 2016 |
| ATS | 30 | UL 1008, NFPA 110, NEC 700 |
| Cable | 25 | NEC 310, NEC Chapter 9 |
| Bus Duct | 24 | NEC 368, UL 857 |
| Panelboard | 24 | NEC 408, UL 67 |
| RPP | 13 | NEC 408, UL 67/891 |
| STS | 16 | UL 1008, ITIC/CBEMA |
| Battery | 21 | IEEE 485/1188, NFPA 855, UL 1973 |
| Cooling | 32 | ASHRAE TC 9.9/90.4, NEC 440 |

## Cross-Reference Checks (31 total)

| # | Check | Standard |
|---|-------|----------|
| 1 | Breaker-cable ampacity | NEC 240.4, 310.16 |
| 2 | Transformer protection (primary + secondary) | NEC 450.3 |
| 3 | Voltage consistency | NEC 110.4 |
| 4 | Panel bus rating vs OCPD | NEC 408.36 |
| 5 | Breaker frame vs trip | UL 489 |
| 6 | Standard breaker sizes | NEC 240.6 |
| 7 | Small wire rule | NEC 240.4(D) |
| 8 | Fault current coordination | NEC 110.9 |
| 9 | Selective coordination | NEC 700.32, 701.27 |
| 10 | Arc energy reduction (1200A+) | NEC 240.87 |
| 11 | Ground fault protection | NEC 230.95 |
| 12 | Available fault current labeling | NEC 110.24 |
| 13 | Grounding conductor sizing | NEC 250.122 |
| 14 | Transformer grounding (separately derived) | NEC 250.30 |
| 15 | K-factor / harmonics | IEEE C57.110 |
| 16 | ABB product validation | ABB Catalog |
| 17 | Metric cable sizing (IEC ampacity) | IEC 60364 |
| 18 | UL listing per cut sheet | NEC 110.2, 110.3 |
| 19 | Missing drawing views | Submittal Requirements |
| 20 | Fuse schedule detection | Submittal Requirements |
| 21 | Cable way congestion | Constructability |
| 22 | Transformer capacity vs load | NEC 450 |
| 23 | Voltage consistency per device | Drawing Consistency |
| 24 | Impedance plausibility (2-12%) | IEEE C57 |
| 25 | Pole count sanity (1-4 only) | UL 489 |
| 26 | Conductor count vs breaker | NEC 240.4, 310.16 |
| 27 | SLD equipment vs cut sheet coverage | Submittal Requirements |
| 28 | Cable schedule completeness | Submittal Requirements |
| 29 | Revision consistency | Submittal Requirements |
| 30 | Title block consistency | Drawing Standards |
| 31 | Protection coordination ratio | NEC 700.32, 701.27 |

## Additional Features

- **SLD-to-schedule cross-check**: Q-designation matching, frame/trip/kAIC/model/pole comparison
- **Naming consistency checker**: inconsistent labels, missing descriptions, mixed conventions
- **Jurisdiction detection**: auto-detects NEC vs IEC from voltage, frequency, UL/CE references
- **System topology**: builds upstream/downstream tree, propagates fault current
- **Manufacturer validation**: ABB (Emax 2, Tmax XT), Eaton (Magnum, NRX, Series C), Schneider (Masterpact, Compact NSX, PowerPact), Siemens (3WL, 3VA, 3VL)
- **Protection coordination**: selective coordination ratio analysis, ZSI detection, ground fault coordination
- **Arc flash estimation**: simplified IEEE 1584 incident energy, PPE category classification
- **Pattern learning**: tracks engineer feedback (agreed/dismissed), learns to suppress noise and boost real issues
- **NEC code commentary**: 22 articles with "why it matters" explanations shown inline
- **Spec validation**: upload Division 26 spec, cross-reference requirements against submittal
- **Multi-submittal cross-reference**: validates consistency between switchgear + UPS + generator + ATS submittals
- **RFI workflow**: track RFIs from draft through vendor response to closure
- **Approval stamps**: Approved / Approved as Noted / Revise & Resubmit / Rejected stamps on PDF
- **Submittal register**: track what's submitted vs outstanding per project
- **Revision comparison**: upload Rev B, see exactly what changed from Rev A
- **Tesseract OCR**: reads scanned pages with no text layer
- **AI Vision** (optional): Ollama/LLaVA (free) or Claude API for drawing analysis
- **Auto-detect equipment type**: no manual selection needed — tool figures out what's in the PDF

---

## Troubleshooting

**"start.bat is not recognized" or nothing happens when you run a command in PowerShell**
- Don't type `start.bat` in PowerShell. Instead, double-click it in File Explorer, or type `.\start.bat` with the dot and backslash in front.

**Python errors about packages not found**
- Make sure you checked "Add Python to PATH" when you installed Python. If you're not sure, uninstall Python and reinstall it, and this time watch for the checkbox on the very first screen.

**"Port already in use" error**
- This means the tool is already running in another window. Close all terminal windows and try again. Or open Task Manager (Ctrl+Shift+Esc), find "python" in the list, and End Task.

**Browser doesn't open automatically**
- Open your browser manually and go to **http://localhost:5173**

**Review takes a very long time on large submittals (400+ pages)**
- The first review extracts text from every page, which can take 1-2 minutes for very large files. Subsequent reviews on the same file are faster.

**"Tesseract not found" warning**
- This is optional. Tesseract OCR reads scanned pages. Install from https://github.com/UB-Mannheim/tesseract/wiki if you want OCR support. The tool works fine without it for PDFs with embedded text.

---

## Building as a Standalone .exe (Advanced)

To create a single .exe that doesn't need Python or Node.js installed:

```
pip install pyinstaller
python build_exe.py
```

This creates `dist/DC_Submittal_Review.exe` — a fully self-contained application.
