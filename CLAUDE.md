# CLAUDE.md — Project Context

## User Profile
- Electrical engineer, NOT a software engineer
- Designs modular data centers
- Does not know terminal/git — always provide exact copy-paste commands
- Always give the full path starting from `C:\Users\chris\psychic-adventure`
- Uses Windows + PowerShell (not CMD)
- Currently testing with a 480-page ABB submittal for Armada Leviathan MDC

## Project: DC Submittal Review Platform
One-stop shop for EEs reviewing submittals for modular data centers.
Upload PDFs → automated review → mark up PDF → generate RFI emails → track comments.

## Key Technical Decisions

### Electrical Engineering
- **AFC estimation**: Utility = 42kA (infinite bus, typical 2000kVA MV xfmr, 5.75%Z). Generator = 20kA (~12% Xd"). With interlocked breakers (NOT paralleled), AFC = max(utility, generator), NOT the sum. Only true paralleling switchgear adds contributions.
- **Metric cables**: This is a European/ABB submittal using mm² notation (300mm², 150mm²). Must convert to AWG equivalent for NEC ampacity checks.
- **ABB equipment format**: E6.2H 4000 (Emax 2 ACB), XT7H 1000 (Tmax XT MCCB), Sn=27.78[kVA] (apparent power notation). Not all Sn= values are transformers — chillers, pumps, power shelves, racks use Sn= for their load draw.
- **AFCI/GFCI**: Valid check, but check ONCE for the document — not every breaker. IT spaces are exempt. Only relevant for dwelling units, bathrooms, kitchens if they exist in the facility.
- **Spec-dependent checks**: Skip unless a spec document is uploaded. The tool should be spec-agnostic by default.
- **SLD topology**: Interlocked breakers between Source A (utility) and Source B (generator) — only one source at a time, never paralleled in normal operation.

### Review Philosophy
- The goal is 99% of the review done by the tool. Engineer just sanity-checks.
- Focus on: NEC code compliance, life safety, constructability, actual mistakes
- Comments must be SPECIFIC: "Page 16: Breaker Q2 E2.2H 1600A — NEC 240.87 requires arc energy reduction for 1200A+. Confirm ZSI provided."
- NOT vague: "Related content found, verify..." is useless
- One finding per issue per document. NOT one per page.
- Comments only for critical/major issues. Minor/info = results only, no comment clutter.
- The 480-page submittal should produce 20-50 actionable comments, not 1832.

### Frontend/UX
- "Mark Up PDF" button should NOT trigger download — it generates markup and switches to View PDF tab
- Only the "Download Marked Up PDF" button triggers download
- Review summary dashboard should persist across page refreshes
- Sort by severity is important — critical first

### Running the App
- Double-click "DC Submittal Review.bat" (shows terminal) or "DC Submittal Review.vbs" (hidden)
- Backend: Python FastAPI on port 8000
- Frontend: Vite React on port 5173
- Python 3.14 on user's machine — need unpinned deps (>=) not pinned (==) to avoid Rust compilation issues

## Branch
All work on: `claude/submittal-review-platform-tmhtv`
