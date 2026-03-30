# ArcLight — Current TODO

## Ready When Internet Available
- [ ] Electron desktop app — `cd electron && npm install && npm run dev` (needs ~150MB download)
- [ ] Ollama LLaVA vision model — `ollama pull llava` (needs ~4GB download)

## Next Up
- [ ] Ball-in-court tracking — assigned-to dropdown on submittals (Engineer / Contractor / Owner) with dashboard indicator
- [ ] Due date tracking — overdue highlighting on submittals past SLA
- [ ] Export closeout report — project-level PDF summarizing all submittals and dispositions

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
- [x] Electron scaffolding (main.js, dev.js, build-backend.js, package.json)
- [x] ArcLight branding + icon throughout app
- [x] Batch review — multi-file upload with parallel processing
- [x] Comment tracker — green checkmark / red X / threaded replies / quick templates
- [x] Clickable dashboard tiles
- [x] SMTP email sending with auto-detected provider settings
- [x] Settings page — email, reviewer profile, company info, review preferences
- [x] Profile settings wired into emails, reports, and approval stamps
- [x] "Reviewed by" terminology (replaced "Engineer of Record")
- [x] User guide (docs/GUIDE.md) and API reference (docs/API.md)
- [x] One-click installer (install.bat)
- [x] File cleanup — removed junk, unified branding
- [x] Client PDFs scrubbed from git history
- [x] Code review cleanup — security fixes, memory leaks, DRY improvements
- [x] build_exe.py fixed — missing hidden imports for register, rfis, feedback
