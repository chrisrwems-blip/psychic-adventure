# DataCenter Submittal Review Platform

One-stop shop for electrical engineers reviewing submittals for modular data center projects.

## What It Does

1. **Upload any submittal PDF** (switchgear, UPS, PDU, generators, transformers, ATS, cables, bus ducts, panelboards, RPP, STS, batteries, cooling)
2. **Automated review** against NEC, NFPA, IEEE, UL, Uptime Tier, and other standards — 308 checks across 13 equipment types
3. **Mark up the PDF** with comments — generates a marked-up PDF with severity-coded annotations and a summary page
4. **Generate emails** — auto-writes RFI, clarification, rejection, or approval emails grouped by severity
5. **Track comments** — filter by status (open/resolved/deferred), severity, and project

## Prerequisites

You need two things installed on your computer:

- **Python 3.10+** — [Download here](https://www.python.org/downloads/)
- **Node.js 18+** — [Download here](https://nodejs.org/)

To check if you have them, open a terminal and run:
```
python3 --version
node --version
```

## How to Run

### Option 1: One command (easiest)
```
./start.sh
```
Then open **http://localhost:5173** in your browser.

To stop it: press **Ctrl+C** or run `./stop.sh`

### Option 2: Manual (two terminal windows)

**Terminal 1 — Backend:**
```
cd backend
pip install -r requirements.txt
python3 -m uvicorn app.main:app --port 8000
```

**Terminal 2 — Frontend:**
```
cd frontend
npm install
npm run dev
```

Then open **http://localhost:5173**

## How to Use

1. **Create a project** (e.g., "Phoenix DC Module 3", Tier III)
2. **Upload a submittal PDF** — pick the equipment type, fill in manufacturer/contractor info
3. **Click "Run Review"** — the engine checks the PDF against all applicable standards
4. **Review findings** — see PASS/FAIL/NEEDS REVIEW for each check with code references
5. **Add manual comments** if needed
6. **Click "Mark Up PDF"** — generates a marked-up PDF with all comments overlaid
7. **Generate an email** — pick RFI, clarification, rejection, or approval and it writes the whole thing
8. **Track all comments** across projects in the Comment Tracker page

## Equipment Types Supported

| Type | Checks | Key Standards |
|------|--------|---------------|
| Switchgear | 35 | NEC 408, IEEE C37.20, NFPA 70E |
| UPS | 28 | IEEE 446, NEC 480, UL 1778 |
| Generator | 32 | NFPA 110, EPA Tier 4, ISO 8528 |
| PDU | 25 | IEEE C57.110, NEC 210/215 |
| Transformer | 22 | IEEE C57, NEC 450, DOE 2016 |
| ATS | 24 | UL 1008, NFPA 110, NEC 700 |
| Cable | 20 | NEC 310, NEC Chapter 9 |
| Bus Duct | 18 | NEC 368, UL 857 |
| Panelboard | 20 | NEC 408, UL 67 |
| RPP | 13 | NEC 408, UL 67/891 |
| STS | 16 | UL 1008, ITIC/CBEMA |
| Battery | 23 | IEEE 485/1188, NFPA 855, UL 1973 |
| Cooling | 32 | ASHRAE TC 9.9/90.4, NEC 440 |
