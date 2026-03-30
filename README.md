# ArcLight

**Data center electrical submittal review tool by POSITRON.**

Upload submittal PDFs, get automated NEC/IEEE compliance checks, generate marked-up PDFs and review reports, track comments and RFIs, send emails — all running locally on your machine.

---

## Install

1. Download **[install.bat](https://raw.githubusercontent.com/chrisrwems-blip/psychic-adventure/main/install.bat)** (right-click → Save Link As)
2. Double-click **install.bat**
3. It handles everything — Python, Node.js, Git, downloading ArcLight, building the .exe, and creating a desktop shortcut
4. When it finishes, double-click the **ArcLight** shortcut on your Desktop

That's it. The installer only needs to run once. After that, just use the desktop shortcut.

### Updating

Run **install.bat** again. It detects ArcLight is already installed, pulls the latest version, and rebuilds the .exe.

---

## What ArcLight Does

**Review** — Upload electrical submittal PDFs. ArcLight auto-detects all equipment, runs 500+ NEC/IEEE compliance checks, cross-references sizing and coordination, and generates individual reports with page numbers and code citations. Upload multiple PDFs for batch review.

**Markup** — Annotates PDFs with color-coded comments. Approval stamps. Revision comparison (Rev A vs Rev B). Spec validation against Division 26.

**Track** — Comment tracker with resolve/reject/reply workflow. RFI tracker. Submittal register. Dashboard with drill-down navigation.

**Email** — Auto-generates RFIs, clarifications, rejections, and approvals. Sends directly via SMTP (Gmail, Outlook, Yahoo, etc.).

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

## Documentation

- **[User Guide](docs/GUIDE.md)** — step-by-step guide for every feature
- **[API Reference](docs/API.md)** — all 55 API endpoints

---

## Troubleshooting

**Installer fails to download Python/Node/Git**
Your network may block downloads. Install them manually: [Python](https://www.python.org/downloads/), [Node.js](https://nodejs.org/), [Git](https://git-scm.com/download/win). Then run install.bat again.

**"Port already in use" error**
ArcLight is already running. Open Task Manager (Ctrl+Shift+Esc), find "python" in the list, End Task, then try again.

**Review takes a long time on large submittals**
First review extracts text from every page — 1-2 minutes for 400+ page submittals is normal.

---

## Optional: Ollama Vision AI

For analyzing scanned drawings with local AI:

1. Install Ollama from https://ollama.com
2. Run: `ollama pull llava`
3. ArcLight detects it automatically
