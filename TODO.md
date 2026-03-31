# ArcLight — Current TODO

## Ready
- [x] Electron desktop app — working in dev mode
- [x] Ollama LLaVA — installed, works as fallback
- [x] Gemini Vision — free tier, no cost
- [ ] Electron production build — `npm run build` to create installer
- [ ] First GitHub Release — triggers auto-update for future versions

## Next Up
- [ ] Ball-in-court tracking — assigned-to dropdown on submittals (Engineer / Contractor / Owner) with dashboard indicator
- [ ] Due date tracking — overdue highlighting on submittals past SLA
- [ ] Export closeout report — project-level PDF summarizing all submittals and dispositions
- [ ] Primary equipment filtering — suppress checklist findings for equipment types that are merely referenced, not the subject of the review

## Backlog
- [ ] Saved filter views — name and save custom filter combos in comment tracker
- [ ] Side-by-side revision viewer — show Rev A and Rev B PDFs next to each other
- [ ] Version history / audit trail — who approved what, when, with rollback
- [ ] @Mentions + notifications — tag people in comments, trigger alerts
- [ ] Approval roadmap — visual chain showing submittal progress through review stages
- [ ] Field photo linking — attach site photos to submittals
- [ ] Mobile-responsive layout — for tablet use on site
- [ ] Code signing certificate — eliminates Windows SmartScreen warning on .exe ($200/yr)

## Done This Session
- [x] Dark mode toggle with localStorage persistence
- [x] Electron scaffolding + electron-updater for auto-updates
- [x] GitHub Actions CI/CD for automated releases on tag push
- [x] ArcLight branding + icon throughout app
- [x] Batch review — multi-file upload with parallel processing
- [x] Comment tracker — green checkmark / red X / threaded replies / quick templates
- [x] Clickable dashboard tiles
- [x] SMTP email sending with auto-detected provider settings
- [x] Settings page — email, reviewer profile, company info, review preferences, vision backend selector
- [x] Profile settings wired into emails, reports, and approval stamps
- [x] "Reviewed by" terminology (replaced "Engineer of Record")
- [x] User guide (docs/GUIDE.md) and API reference (docs/API.md)
- [x] One-click installer (install.bat)
- [x] File cleanup — removed junk, unified branding
- [x] Client PDFs scrubbed from git history
- [x] Code review cleanup — security fixes, memory leaks, DRY improvements
- [x] build_exe.py fixed — missing hidden imports for register, rfis, feedback
- [x] Auto-fill submittal title from filename
- [x] Update checker — blue banner when new version available
- [x] Vision AI — Claude, Gemini, and Ollama backends with selector
- [x] Vision page analysis — SLD review, UL listing verification, clearance checks, nameplate reading
- [x] Smart verification — AI-powered false positive detection on FAIL/NEEDS REVIEW findings
- [x] Vision AI indicator badge on Run Review button
- [x] Vision pages triggered list in review summary
- [x] Comment export endpoint for sharing findings
- [x] False positive fixes — ABB model parsing, pole count, UL text fragments, voltage anomaly, vision page filtering
- [x] Rate limiting + credit exhaustion detection for API calls
- [x] Verification skips non-technical pages and weak keyword matches
- [x] Poppler integration for PDF-to-image conversion on Windows
