# DC Submittal Review Platform — Ambitious Roadmap

## Current State
- 11,600+ lines of code
- 21 cross-reference checks with NEC references
- SLD-to-schedule cross-check
- System topology tracking
- ABB/Eaton/Schneider product validation
- Jurisdiction detection (NEC vs IEC)
- 69% coverage of real engineer review comments (up from 0%)
- PDF markup, email generation, comment tracking

---

## Phase 1: Get to 90%+ Accuracy (Immediate)

### 1.1 Vision AI integration for drawing analysis
- [ ] Auto-detect pages with drawings (no text layer) and queue for vision
- [ ] SLD visual analysis: read every breaker, transformer, cable from the drawing image
- [ ] Cut sheet UL verification: visually confirm UL mark presence
- [ ] Clearance verification: read dimensions from GA drawings vs NEC 110.26
- [ ] Cable routing analysis: identify cable trays, conduits, penetrations
- [ ] Support Ollama (free local) and Claude API (paid, more accurate)

### 1.2 Protection coordination analysis
- [ ] Parse time-current curves from PDF pages (image analysis)
- [ ] Verify selective coordination: upstream curve must be to the right of downstream
- [ ] Check ZSI wiring between Ekip trip units (ABB-specific)
- [ ] Validate that instantaneous settings don't cause nuisance tripping
- [ ] Verify ground fault coordination (main GFP vs feeder GFP)

### 1.3 Full SLD topology from drawing vision
- [ ] Build complete equipment tree from visual SLD reading (not text extraction)
- [ ] Cross-validate text extraction against vision extraction — flag discrepancies
- [ ] Trace every circuit path: utility → ATS → switchgear → transformer → panelboard → load
- [ ] Verify single point of failure for Tier III/IV

### 1.4 Constructability intelligence
- [ ] Read physical dimensions from GA drawings (vision AI)
- [ ] Verify NEC 110.26 clearances from layout drawings automatically
- [ ] Check cable way dimensions vs cable count
- [ ] Verify shipping split locations won't create field problems
- [ ] Flag where cable routing conflicts with structural/mechanical

---

## Phase 2: Multi-Document Intelligence

### 2.1 Spec document integration
- [ ] Upload Division 26 specification alongside submittal
- [ ] Parse spec requirements: "Switchgear shall be ABB Emax 2 or approved equal"
- [ ] Auto-validate: does submittal match spec? Flag deviations
- [ ] Track spec section cross-references (e.g., "per Section 26 24 16.2.A.3")
- [ ] Flag "or equal" substitutions for engineer review

### 2.2 Multi-submittal project coordination
- [ ] Link related submittals: switchgear + UPS + generator + ATS + transformer + cable
- [ ] Cross-reference between submittals: generator kW matches ATS rating matches switchgear incomer
- [ ] Track what's been submitted vs what's still outstanding per spec section
- [ ] Submittal register with status tracking (not submitted / under review / approved / rejected)

### 2.3 Revision management
- [ ] Track all revisions per submittal (Rev A, B, C...)
- [ ] Diff view showing exactly what changed between revisions
- [ ] Flag when a revision introduces new issues (regression detection)
- [ ] Revision history timeline
- [ ] Auto-generate cover letter listing changes from previous revision

### 2.4 Drawing set integration
- [ ] Upload full electrical drawing set (E-sheets)
- [ ] Cross-reference submittal equipment against drawing equipment schedules
- [ ] Verify panel schedules match between drawings and submittals
- [ ] Check that every piece of equipment on the drawings has a corresponding submittal

---

## Phase 3: Intelligence & Learning

### 3.1 Pattern learning from engineer feedback
- [ ] Track which findings the engineer agrees with vs dismisses
- [ ] Learn to suppress finding types that are consistently dismissed
- [ ] Prioritize finding types that consistently lead to RFIs
- [ ] Vendor-specific patterns: "ABB submittals from this panel builder always have X issue"

### 3.2 Industry knowledge base
- [ ] NEC code commentary and explanations for each check
- [ ] Common interpretations and AHJ-specific requirements
- [ ] Equipment substitution database: "if spec says X, acceptable equals are Y, Z"
- [ ] Known issues database: "ABB E6.2H with firmware < 3.0 has ZSI compatibility issue"

### 3.3 Automatic fault current study
- [ ] Input utility fault current data and transformer impedance
- [ ] Calculate fault current at every point in the system
- [ ] Auto-generate fault current label values per NEC 110.24
- [ ] Verify every device interrupting rating against calculated AFC
- [ ] Output: fault current one-line diagram overlay

### 3.4 Arc flash analysis integration
- [ ] Calculate incident energy at each point using IEEE 1584-2018
- [ ] Generate arc flash labels
- [ ] Verify that submitted equipment supports the required PPE category
- [ ] Check for arc energy reduction features (NEC 240.87)
- [ ] Output: arc flash hazard report

---

## Phase 4: Collaboration & Workflow

### 4.1 RFI workflow management
- [ ] Track RFIs from creation through vendor response to resolution
- [ ] Auto-generate RFI log
- [ ] Link RFI items back to specific findings
- [ ] Track response due dates and send reminders
- [ ] Import vendor responses and auto-close resolved items

### 4.2 Approval workflow
- [ ] Formal approval workflow: review → mark up → RFI → response → final review → stamp
- [ ] Digital submittal stamp (Approved / Approved as Noted / Revise & Resubmit / Rejected)
- [ ] Auto-generate transmittal letter
- [ ] Track approval chain and timestamps

### 4.3 Real-time collaboration (future)
- [ ] Multiple engineers reviewing the same submittal simultaneously
- [ ] Comment threading and @mentions
- [ ] Conflict resolution when two engineers mark the same item differently
- [ ] Activity feed: "Chris added 3 comments to the MDB submittal"

### 4.4 Integration with other tools
- [ ] Outlook integration: send RFI emails directly, track responses
- [ ] Bluebeam integration: import/export markups in Bluebeam format
- [ ] Procore integration: sync submittal status with project management
- [ ] SharePoint/OneDrive: auto-save submittals and reports to project folder

---

## Phase 5: Productization

### 5.1 Desktop application
- [ ] Single .exe installer (PyInstaller + Inno Setup)
- [ ] Desktop shortcut, Start Menu entry
- [ ] Auto-update mechanism
- [ ] Offline operation (no internet required for core features)
- [ ] System tray icon with status indicator

### 5.2 Cloud deployment option
- [ ] Docker container for self-hosted deployment
- [ ] AWS/Azure one-click deployment
- [ ] Multi-tenant with project isolation
- [ ] S3/Blob storage for PDFs
- [ ] PostgreSQL for production database

### 5.3 Mobile companion (future)
- [ ] View review results on phone/tablet
- [ ] Approve/reject findings on the go
- [ ] Push notifications for new RFI responses
- [ ] Photo capture: snap a nameplate in the field, verify against submittal

### 5.4 Analytics & reporting
- [ ] Dashboard: submittals by status, findings by severity, turnaround time
- [ ] Vendor scorecard: which vendors have the most issues, fastest response
- [ ] Project health metrics: how many submittals still outstanding
- [ ] Engineer workload tracking
- [ ] Export analytics to PDF/Excel

### 5.5 Template library
- [ ] Pre-built review checklists for common data center equipment types
- [ ] Custom checklist builder for project-specific requirements
- [ ] Share checklists between projects
- [ ] Industry-standard checklist packages (Uptime Tier III, Tier IV)

---

## Phase 6: Advanced AI Features

### 6.1 Natural language review
- [ ] "Check if the UPS has bypass provisions" → auto-searches submittal and answers
- [ ] "What's the fault current at panel LP-1?" → calculates from topology
- [ ] "Compare this submittal against the one from last project" → cross-project analysis
- [ ] Chat interface for asking questions about the submittal

### 6.2 Automatic spec writing
- [ ] Generate Division 26 spec sections from project requirements
- [ ] "I need a spec for a 2N data center at 480V with 2MW IT load" → generates spec
- [ ] Keep specs up to date with latest NEC edition

### 6.3 Predictive issue detection
- [ ] "Based on similar projects, this design will likely have X issue"
- [ ] Suggest design improvements proactively
- [ ] Flag when a vendor's submittal quality is declining over time

---

## Moonshot: Full Automated Design Review

### 7.1 Complete NEC compliance scan
- [ ] Every article in NEC Chapter 1-8 that applies to data center electrical
- [ ] Automated compliance report with pass/fail for every applicable section
- [ ] AHJ-specific amendments and interpretations
- [ ] Annual re-check when NEC edition changes

### 7.2 Digital twin integration
- [ ] Import BIM model, cross-reference against submittals
- [ ] 3D visualization of equipment layout with clearance checking
- [ ] Cable routing optimization
- [ ] Thermal analysis: does the cooling design match the electrical load?

### 7.3 Construction support
- [ ] Generate installation checklists from approved submittals
- [ ] QC inspection checklists tied to specific equipment
- [ ] Commissioning test procedures from manufacturer data
- [ ] Punch list management integrated with submittal findings
