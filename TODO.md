# DC Submittal Review Platform — Roadmap

## Current State (as built)
- **16,300+ lines** of code across 81 source files
- **31 cross-reference checks** (all equipment-agnostic)
- **13 equipment type checkers** with 356 individual checks
- **SLD-to-schedule cross-check** (supports ABB, Eaton, Schneider, Siemens, generic US formats)
- **System topology tracking** with fault current propagation
- **ABB, Eaton, Schneider, Siemens** product catalogs
- **Jurisdiction detection** (NEC vs IEC from voltage/frequency/UL)
- **Protection coordination analysis** + arc flash estimation
- **Pattern learning** from engineer feedback
- **NEC code commentary** database (22 articles with "why it matters")
- **IEC 60364 ampacity tables** for metric cables
- **Professional frontend** with 6 pages
- **PDF markup, email generation, RFI tracking, approval stamps**
- **Revision comparison, spec validation, multi-submittal cross-reference**
- **Tesseract OCR** + Vision AI (Ollama/Claude) integration
- **47 unit tests** passing
- **Auto-detect equipment type** — no manual selection needed

---

## Phase 1: Get to 90%+ Accuracy

### 1.1 Vision AI integration ✅ BUILT
- [x] Auto-detect pages with drawings and queue for vision
- [x] SLD visual analysis prompts
- [x] Cut sheet UL verification prompts
- [x] Clearance verification prompts
- [x] Support Ollama (free local) and Claude API
- [ ] End-to-end testing with Ollama installed

### 1.2 Protection coordination analysis ✅ BUILT
- [x] Selective coordination ratio analysis (flag <2:1 ratios)
- [x] ZSI requirement detection
- [x] Arc flash incident energy estimation (simplified IEEE 1584)
- [x] Ground fault coordination check
- [ ] Parse actual time-current curve images (needs Vision AI)
- [ ] Validate instantaneous settings don't cause nuisance tripping

### 1.3 Full SLD topology from drawing vision
- [ ] Build equipment tree from visual SLD reading
- [ ] Cross-validate text extraction against vision
- [ ] Trace every circuit path visually
- [ ] Verify single point of failure for Tier III/IV

### 1.4 Constructability intelligence — Partial
- [x] Cable congestion check (cable way density)
- [x] Missing drawing views (bottom view for cable entry)
- [ ] Read dimensions from GA drawings (needs Vision AI)
- [ ] Verify NEC 110.26 clearances from layout drawings
- [ ] Shipping split analysis

---

## Phase 2: Multi-Document Intelligence

### 2.1 Spec document integration ✅ BUILT
- [x] Upload Division 26 spec alongside submittal
- [x] Parse spec requirements (manufacturers, standards, performance)
- [x] Auto-validate submittal against spec
- [x] Flag "or equal" substitutions
- [x] Frontend upload UI

### 2.2 Multi-submittal coordination ✅ BUILT
- [x] Cross-reference all submittals in a project
- [x] Voltage consistency across submittals
- [x] Equipment rating mismatches between submittals
- [x] Submittal register with status tracking
- [ ] Auto-detect what's still outstanding per spec section

### 2.3 Revision management ✅ BUILT
- [x] Diff view showing what changed between revisions
- [x] Frontend with color-coded changes (added/removed/modified)
- [ ] Flag when revision introduces new issues
- [ ] Auto-generate cover letter listing changes

### 2.4 Drawing set integration
- [ ] Upload full electrical drawing set
- [ ] Cross-reference against submittal equipment
- [ ] Verify panel schedules match between drawings and submittals

---

## Phase 3: Intelligence & Learning

### 3.1 Pattern learning ✅ BUILT
- [x] Track engineer feedback (agreed/dismissed/modified)
- [x] Learn suppression list (>70% dismiss rate)
- [x] Learn priority list (>80% agree rate)
- [x] Apply learning to filter/reorder findings
- [x] Feedback API endpoints

### 3.2 Industry knowledge base ✅ BUILT
- [x] NEC code commentary for 22 articles
- [x] "Why it matters" explanations in plain language
- [x] Inline commentary in expanded findings
- [ ] Common AHJ-specific interpretations
- [ ] Equipment substitution database

### 3.3 Automatic fault current study — Partial
- [x] Estimate AFC at service entrance (infinite bus + generator)
- [x] Propagate through transformers using impedance
- [x] Verify interrupting ratings against estimated AFC
- [ ] Input actual utility fault current data
- [ ] Auto-generate NEC 110.24 label values

### 3.4 Arc flash analysis ✅ BUILT
- [x] Simplified IEEE 1584 incident energy estimation
- [x] PPE category classification (Cat 0-4 + Dangerous)
- [x] Flag locations ≥ Cat 3
- [ ] Full IEEE 1584-2018 calculation with electrode configurations
- [ ] Generate arc flash labels

---

## Phase 4: Collaboration & Workflow

### 4.1 RFI workflow ✅ BUILT
- [x] Track RFIs from creation through response to closure
- [x] Auto-generate from review comments
- [x] Status flow: draft → sent → responded → closed
- [x] Frontend RFI Tracker page
- [ ] Due date reminders
- [ ] Import vendor responses

### 4.2 Approval workflow ✅ BUILT
- [x] Digital stamps (Approved / Approved as Noted / Revise & Resubmit / Rejected)
- [x] Stamp overlay on PDF with reviewer name and date
- [x] Frontend stamp UI with disposition selector
- [ ] Transmittal letter auto-generation
- [ ] Approval chain tracking

### 4.3 Tool integration — NOT BUILT
- [ ] Outlook integration
- [ ] Bluebeam markup import/export
- [ ] Procore integration
- [ ] SharePoint/OneDrive

---

## Phase 5: Productization

### 5.1 Desktop application — Partial
- [x] PyInstaller build script
- [x] Windows .bat/.vbs/.ps1 launchers
- [ ] Test .exe build end-to-end
- [ ] Inno Setup installer with desktop shortcut
- [ ] Auto-update mechanism

### 5.4 Analytics & reporting ✅ BUILT
- [x] Dashboard with stat cards and bar charts
- [x] Submittals by status chart
- [x] Comments by severity chart
- [x] Professional PDF review report export
- [ ] Vendor scorecard
- [ ] Export analytics to Excel

### 5.5 Template library — NOT BUILT
- [ ] Pre-built checklists for common equipment types
- [ ] Custom checklist builder
- [ ] Industry-standard packages (Uptime Tier III, IV)

---

## Phase 6: Advanced AI — NOT STARTED
- [ ] Natural language review ("check if UPS has bypass")
- [ ] Automatic spec writing
- [ ] Predictive issue detection

## Moonshot — NOT STARTED
- [ ] Complete NEC compliance scan
- [ ] Digital twin / BIM integration
- [ ] Construction support (installation checklists, commissioning)
