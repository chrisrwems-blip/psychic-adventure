# CLAUDE.md — Armada Systems Inc

## Company & Project Context

**Armada Systems Inc** (Armada.ai) designs and manufactures modular, prefabricated data centers. The flagship product is the **Leviathan** — a factory-built, transportable data center unit.

The primary consulting engagement is with **J. Dunton Associates Ltd (JDA)**, a UK-based firm, on the **Leviathan project**.

The user is **Chris**, an engineer at Armada involved in electrical design, submittal reviews, site assessments, and client-facing technical documentation.

---

## Leviathan Reference Specifications

Use these as the baseline for any Leviathan-related work. Do not use generic data center assumptions.

### System Envelope
- **IT Load**: 1.77 MW per Leviathan
- **Total Cooling Capacity**: 2.2 MW per Leviathan
- **Footprint**: 36,300 mm × 13,600 mm (~119 ft × 45 ft) per unit
- **Zones**: IT zone, electrical plant zone, mechanical plant zone
- **Chiller Placement**: Adjacent to mechanical plant zone; requires airflow clearance on all sides

### Power Architecture
- **Utility Interface**: 480V / 60Hz
- **Distribution**: Modular UPS-backed power distribution
- **Compute Racks**: 8× racks at 200 kW each
- **Network Racks**: 4× racks at 42.5 kW each

### Cooling Architecture
- **Topology**: Redundant N+1 chiller-driven, closed-loop (no onsite water supply needed)
- **Cooling Ratio**: 80% liquid / 20% air
- **Method**: Direct-to-chip liquid cooling for compute; air cooling for ambient
- **Heat Rejection**: Air-cooled condensers (no cooling towers)

### IT Architecture
- **Rack Standard**: OCP ORv3-based racks with blind-mate busbar and manifold connections
- **GPU Support**: NVIDIA GB300 (576 GPUs/unit), NVL72 / HGX B300 / HGX B200 (512 GPUs/unit), AMD Instinct
- **Networking**: 800 Gb/s InfiniBand (NDR) and Spectrum-X capable
- **Clustering**: NVIDIA Reference Architecture compliant; pod = 4× Leviathans

---

## Electrical Engineering Domain

### Primary Code References
- **NEC (NFPA 70)**: Articles 220, 230, 240, 250, 310, 408, 450, 480, 645, 700, 701, 702, 706, Chapter 9 Tables
- **UL 2755**: Modular Data Centers standard — applies to factory-built, transportable units
- **NFPA 72**: Fire alarm; **NFPA 101**: Life safety; **IFC**: International Fire Code
- **ASHRAE**: Climate zone references for cooling design
- **IBC/ASCE 7**: Seismic and wind loading

### Power Distribution Chain
Utility/Generator → Main Switchgear → ATS → UPS → PDU → RPP/Panel → Rack PDU → IT Load

### Key Design Considerations
- Redundancy topologies: N, N+1, 2N, 2(N+1)
- K-factor transformers for harmonic-rich IT loads (K-13 or K-20)
- Voltage drop targets: <2% branch, <3% feeder, <5% total
- Always cite specific NEC articles when making code-driven decisions
- Space constraints are critical — everything fits in a prefab enclosure
- UL 2755 compliance implications for every electrical decision

### Common Calculations
- Load calculations (NEC Art. 220 demand factors, 20-30% spare capacity)
- Conductor sizing (NEC Table 310.16, temperature/bundling derating)
- Voltage drop: V_drop = (2 × L × I × R) / 1000 (single-phase); √3 factor for three-phase
- Short-circuit: MVA method or point-to-point; AIC ratings must meet available fault current
- Conduit fill: NEC Ch. 9 Table 1 (40% for 3+ conductors)
- Battery/UPS runtime: Account for end-of-life capacity (80% nameplate) and temperature derating

---

## Document & Workflow Standards

### RFIs
- Numbering format: `ARM-RFI-XXXX` (auto-incrementing per project)
- Fields: project, date, from/to, discipline, priority, response-required-by date
- Disciplines: Electrical, Mechanical, Structural, Civil, Fire, Controls
- Status tracking: Open → Closed → Superseded

### Transmittals
- Numbering format: `ARM-TX-XXXX`
- Document status options: For Review, For Approval, For Construction, As-Built, For Information
- Include document table with number, title, revision, status

### Submittal Reviews
- Process client comment registers (Excel/CSV/PDF)
- Response categories: Acknowledged, Noted, Clarification Required, Design Change, Rejected
- Group by discipline, prioritize Critical/High first
- Flag items needing engineering review vs. straightforward responses
- Status codes: Open, Responded, Closed, Deferred
- Multi-round tracking (1st round, 2nd round)
- Never modify original client comment text
- Flag confidential/IP-sensitive responses for Chris's review before sending

### Meeting Minutes
- Sections: Attendees, Agenda Items, Key Decisions, Action Items, Open Questions, Next Steps
- Action items need: Owner, Task, Due Date, Priority, Status
- Flag incomplete items (missing owner or deadline)
- Tone: Professional but not stuffy — easy to read and actionable

### Site Assessments
- 9 assessment categories: Site Access, Footprint/Ground Works, Electrical Infrastructure, Cooling/Mechanical, Networking, Environmental, Regulatory, Security, Operational Readiness
- Always identify critical-path blockers (utility power is typically #1, 6-18 months lead)
- Every checklist item should define what "done" looks like
- Output as .docx (print-ready) and/or .xlsx (tracking spreadsheet)

---

## One-Line Diagram Conventions

- A-feed: Blue (#0066CC), B-feed: Red (#CC0000), Common: Green (#009900)
- Layout: Top-to-bottom hierarchy (Utility → Switchgear → Transformers → UPS → Busway → PDU → Racks)
- Symbols: IEC 60617 standard (UL/ANSI available on request)
- Always include voltage labels at each transformation stage
- Title block: Project, Revision, Date, Designer initials
- Canvas: 1400×900px SVG for typical 2N topology

---

## Client Context

- **JDA (J. Dunton Associates Ltd)**: UK-based consulting firm, primary engagement partner on Leviathan
- **WinDC / MCS**: Data center operator clients with standardized comment review processes
- Submittal review SLA: 5-7 business days for 1st round; expedited for Critical items
- Tone with clients: Professional, technical, solution-focused; acknowledge all comments; clear rationale for any rejections
- AS/NZS standards referenced where relevant (some projects have Australian scope)

---

## Coding Conventions

- When building tools for Armada workflows, keep the domain language consistent with the specs above
- Prefer TypeScript for web tooling; Python for data processing and engineering calculations
- Structure repos with clear separation: `/src`, `/docs`, `/templates`, `/tests`
- Keep generated documents (.docx, .xlsx) in `/output` or `/generated` — don't commit them to main
- Use meaningful commit messages referencing the Armada workflow (e.g., "feat: add NEC 310.16 lookup to conductor sizing module")

---

## Things to Flag for Chris

- Any design change that affects capacity, layout, or modular assembly sequence
- Code or standard interpretation questions
- Vendor constraints or long-lead equipment impacts
- Cost or schedule implications
- Conflicts between disciplines
- Confidential or IP-sensitive content before client distribution
