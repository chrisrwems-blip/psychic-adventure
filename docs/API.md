# ArcLight API Reference

Base URL: `http://localhost:8000/api`

All endpoints return JSON unless noted otherwise. File uploads use `multipart/form-data`. PDF downloads return `application/pdf`.

---

## System

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/health` | Health check — returns `{"status": "healthy", "service": "ArcLight"}` |
| GET | `/dashboard` | Dashboard stats — projects, submittals, comments, RFIs, register counts, breakdowns by status/severity |

---

## Projects

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/projects/` | List all projects |
| POST | `/projects/` | Create project — body: `{name, description?, client?, location?, tier_level?}` |
| GET | `/projects/{id}` | Get project details |
| DELETE | `/projects/{id}` | Delete project |

---

## Submittals

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/submittals/` | List submittals — query: `project_id` (optional) |
| POST | `/submittals/upload` | Upload PDF — form: `file`, `project_id`, `title`, `equipment_type?`, `submittal_number?`, `manufacturer?`, `model_number?`, `spec_section?`, `submitted_by?`, `contractor?` |
| GET | `/submittals/{id}` | Get submittal details |
| GET | `/submittals/{id}/pdf` | Download original PDF |
| POST | `/submittals/{id}/annotate` | Generate marked-up PDF with review comments |
| GET | `/submittals/{id}/annotated-pdf` | Download annotated PDF — query: `download=true` for attachment header |
| POST | `/submittals/{id}/stamp` | Apply approval stamp — form: `disposition`, `reviewer_name` |
| DELETE | `/submittals/{id}` | Delete submittal |

---

## Reviews

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/reviews/{id}/run` | Run review — query: `full=true` (default) for full package review |
| POST | `/reviews/batch` | Batch review — body: `{submittal_ids: [1, 2, 3]}` — runs in parallel, returns immediately |
| GET | `/reviews/{id}/results` | Get review results (list of findings) |
| GET | `/reviews/{id}/report` | Download PDF review report |
| GET | `/reviews/{id}/diagnose` | Diagnostic — shows extracted text, metadata, equipment, page types |
| POST | `/reviews/{id}/compare-revision` | Compare revision — form: `file` (revised PDF) |
| POST | `/reviews/{id}/validate-spec` | Validate against spec — form: `file` (spec PDF) |
| GET | `/reviews/equipment-types` | List supported equipment types |
| POST | `/reviews/{id}/vision-analyze` | Start AI vision analysis (requires Ollama or Claude API) |
| GET | `/reviews/{id}/vision-status` | Check vision analysis progress |
| GET | `/reviews/vision-available` | Check if vision backend is available |
| GET | `/reviews/nec-commentary/{code_ref}` | Get NEC code commentary for a reference (e.g., `NEC 240.87`) |
| POST | `/reviews/project/{project_id}/cross-reference` | Cross-reference all submittals in a project |

---

## Comments

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/comments/submittal/{id}` | List comments for a submittal — query: `status?`, `severity?` |
| GET | `/comments/all` | List all comments — query: `status?`, `severity?`, `project_id?` |
| POST | `/comments/submittal/{id}` | Add comment — body: `{comment_text, severity?, page_number?, reference_code?}` |
| PATCH | `/comments/{id}` | Update comment — body: `{status?, resolution_notes?, severity?}` |
| DELETE | `/comments/{id}` | Delete comment |

---

## Emails

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/emails/{submittal_id}/generate` | Generate email — body: `{email_type, recipients?, additional_notes?}` — types: `rfi`, `clarification`, `rejection`, `approval` |
| GET | `/emails/submittal/{id}` | List emails for a submittal |
| GET | `/emails/{id}` | Get email details |
| PATCH | `/emails/{id}/mark-sent` | Mark email as sent |
| POST | `/emails/{id}/send` | Send via SMTP — body: `{to, cc?}` — requires email configured in Settings |

---

## RFIs

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/rfis/all` | List all RFIs — query: `status?`, `severity?`, `project_id?` |
| POST | `/rfis/{submittal_id}/create` | Create RFI — body: `{subject?, severity?, recipients?, due_date?, related_comment_ids?}` |
| GET | `/rfis/{submittal_id}` | List RFIs for a submittal |
| PATCH | `/rfis/{id}/status` | Update RFI status — body: `{status}` — values: `draft`, `sent`, `responded`, `closed` |
| PATCH | `/rfis/{id}/response` | Log vendor response — body: `{response_text}` |

---

## Submittal Register

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/register/{project_id}` | List register items for project |
| POST | `/register/{project_id}` | Add register item — body: `{spec_section, description, priority?}` |
| PATCH | `/register/{id}` | Update register item — body: `{status?, notes?, due_date?}` |
| DELETE | `/register/{id}` | Delete register item |
| GET | `/register/{project_id}/summary` | Get register summary (counts by status) |

---

## Feedback (Learning System)

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/feedback/{submittal_id}` | Record feedback on a finding — body: `{finding_type, action, notes?}` — actions: `agreed`, `dismissed`, `modified` |
| GET | `/feedback/stats` | Get suppression and priority lists from historical feedback |
| GET | `/feedback/history` | List feedback — query: `submittal_id?`, `finding_type?`, `action?`, `limit?` |
| POST | `/feedback/apply-learning` | Apply learning to findings list — body: `{findings: [...]}` |

---

## Settings

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/settings/email/detect` | Auto-detect SMTP from email — body: `{email}` |
| POST | `/settings/email/save` | Save SMTP settings — body: `{email, password, host, port, display_name?}` |
| GET | `/settings/email` | Get email settings (password not returned) |
| DELETE | `/settings/email` | Remove email settings |
| POST | `/settings/email/test` | Test SMTP connection — body: `{email, password, host, port}` |
| GET | `/settings/profile` | Get profile and preferences |
| POST | `/settings/profile` | Save profile — body: `{reviewer_name?, reviewer_title?, company_name?, company_address?, company_phone?, default_jurisdiction?, review_sla_days?, report_min_severity?}` |

---

## Status Values

### Submittal Status
`uploaded` → `reviewing` → `reviewed` → `approved` / `rejected` / `revise_resubmit`

### Comment Status
`open` → `resolved` / `deferred`

### RFI Status
`draft` → `sent` → `responded` → `closed`

### Comment Severity
`critical` | `major` | `minor` | `info`

### Equipment Types
`switchgear` | `transformer` | `panelboard` | `ats` | `ups` | `generator` | `busway` | `cable` | `cooling` | `fire_protection` | `monitoring` | `pdu` | `rpp` | `sts` | `battery`

### Jurisdictions
`NEC` | `IEC` | `AS/NZS` | `auto`

---

## Interactive API Docs

When ArcLight is running, visit `http://localhost:8000/docs` for the auto-generated Swagger UI where you can try any endpoint interactively.
