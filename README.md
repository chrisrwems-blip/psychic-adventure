# ArcLight

**Data center electrical submittal review tool by POSITRON.**

Upload submittal PDFs, get automated NEC/IEEE compliance checks, generate marked-up PDFs and review reports, track comments and RFIs, send emails — all running locally on your machine.

---

## Quick Start

### 1. Install Prerequisites (One-Time)

**Python** — https://www.python.org/downloads/
- Click the big yellow "Download Python" button
- Run the installer
- **CHECK the box that says "Add Python to PATH"** on the first screen
- Click "Install Now"

**Node.js** — https://nodejs.org/
- Click the LTS button (left side)
- Run the installer, click Next through everything

**Git** — https://git-scm.com/download/win
- Download starts automatically
- Run the installer, click Next through everything

### 2. Download ArcLight

Open PowerShell (search "PowerShell" in Start menu) and paste:

```
cd ~
git clone https://github.com/chrisrwems-blip/psychic-adventure.git
cd psychic-adventure
git checkout claude/document-submittal-flow-aYWlX
```

### 3. Build the .exe

In the same PowerShell window, paste:

```
cd C:\Users\YourName\psychic-adventure
pip install pyinstaller
python build_exe.py
```

Replace **YourName** with your Windows username. This takes a few minutes the first time.

When it finishes, you'll find **ArcLight.exe** in the `dist` folder.

### 4. Run It

Double-click **ArcLight.exe**. A terminal window opens and your browser loads the app automatically. That's it — no Python or Node.js needed to run the .exe.

---

## What ArcLight Does

**Review** — Upload electrical submittal PDFs. ArcLight auto-detects all equipment, runs 500+ NEC/IEEE compliance checks, cross-references sizing and coordination, and generates individual reports with page numbers and code citations. Upload multiple PDFs for batch review.

**Markup** — Annotates PDFs with color-coded comments (red/orange/yellow/blue by severity). Approval stamps. Revision comparison (Rev A vs Rev B). Spec validation against Division 26.

**Track** — Comment tracker with resolve/reject/reply workflow and quick-insert templates. RFI tracker. Submittal register. Dashboard with clickable drill-down tiles.

**Email** — Auto-generates RFIs, clarifications, rejections, and approvals grouped by severity with NEC citations. Sends directly via SMTP (Gmail, Outlook, Yahoo, etc.).

**Settings** — Reviewer profile, company info, review SLA defaults, jurisdiction preferences. Optional Ollama vision AI for scanned drawings.

**Runs locally** — no cloud, no subscriptions, no data leaving your machine.

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

---

## How to Use

1. **Create a Project** — name, client, tier level
2. **Upload submittal PDFs** — drag-drop one or many, equipment type auto-detected
3. **Run Review** — scans every page, extracts equipment, runs all applicable checks
4. **Review findings** — PASS / FAIL / NEEDS REVIEW with NEC code references and recommendations
5. **Mark Up PDF** — color-coded annotations overlaid on the submittal, summary page at front
6. **Download** — marked-up PDF to send back to the vendor, or standalone review report
7. **Generate Email** — pick RFI/clarification/rejection/approval, send directly from the app
8. **Track** — all comments, RFIs, and submittals across projects in one place

---

## Troubleshooting

**Python errors about packages not found**
- Make sure you checked "Add Python to PATH" when you installed Python. If unsure, uninstall and reinstall, watching for the checkbox on the first screen.

**"Port already in use" error**
- The app is already running. Open Task Manager (Ctrl+Shift+Esc), find "python" in the list, End Task, then try again.

**Review takes a long time on large submittals (400+ pages)**
- First review extracts text from every page, which can take 1-2 minutes for very large files. Normal.

**"Tesseract not found" warning**
- Optional. Install from https://github.com/UB-Mannheim/tesseract/wiki for OCR on scanned pages. The tool works fine without it for PDFs with embedded text.

---

## Optional: Ollama Vision AI

For analyzing scanned drawings and nameplates with local AI:

1. Install Ollama from https://ollama.com
2. Run: `ollama pull llava`
3. ArcLight detects it automatically

No API keys or cloud services needed. This is optional — ArcLight works fully without it.

---

## Optional: Electron Desktop App

For a native desktop window instead of browser:

```
cd C:\Users\YourName\psychic-adventure\electron
npm install
npm run dev
```

Requires Node.js and a decent internet connection for the initial Electron download (~150MB).

---

## Updating

Open PowerShell and paste:

```
cd C:\Users\YourName\psychic-adventure
git pull
python build_exe.py
```

Replace **YourName** with your Windows username.
