# Decision log · 决策记录

Newest first. One line per decision: what was decided, why, and what it changes.
最新的在最上面。每条写：决定了什么、为什么、影响什么。

| Date | Decision / 决定 | Why / 原因 | Impact / 影响 |
| --- | --- | --- | --- |
| 2026-10-21 | Use existing tools wherever they cover a layer; build only L2 eligibility rules, L4 scoring and the experience / STAR bank | Market scan found ready tools for scraping (Apify), company checks (Companies House MCP), CV matching (Teal / Jobscan), mock interviews (Yoodli) and tracking (Airtable) | Build issues 12 → 5; #2, #5, #8, #9, #13 merged into #20, #6, #10, #3 |
| 2026-10-21 | Rank by "paying to hire for UK roles now"; award lists only add points, never filter | Being on the register or on an award list doesn't mean a company is hiring | Priority score, #21 |
| 2026-10-21 | Don't rely on tools the scan couldn't verify; give third-party tools company names only | Unverified sources and extension permissions are a data and privacy risk | #20 |
| 2026-10-20 | Run the search as a 3-month project with gates G0–G4 | Need a clear finish line and weekly checkpoints | [ROADMAP.md](../ROADMAP.md), milestones, issues #1–#18 |
| 2026-10-20 | Target data analyst (SOC 3544) roles first, decide at G3 (2026-12-11) | 3544 is sponsorable only if the CoS is assigned before 2026-12-31 | 3544 applications front-loaded in Oct–Nov |
| 2026-10-20 | Keep personal data in a private tracker; public repo holds code and anonymous stats | Repo and site are public | Issue #2 |
| 2026-10-20 | Build role-level data next (job radar + eligibility check) | Company-level "hiring" doesn't say whether a role fits the visa rules | Issues #5–#7 |
| 2026-10-19 | Label Claude web-search results separately from Google AI and hand-checked ones | Keep the source of every link visible | Page labels |
| 2026-10-16 | Look up companies with Google AI Mode in the desktop browser, starting with Manchester IT | Google results judged more accurate than Claude's own guesses | `scripts/google_queue.py`, scheduled lookups |
| 2026-10-16 | Publish the public site on GitHub Pages | claude.ai isn't reachable from mainland China | `docs/` |
| 2026-10-15 | Use the official GOV.UK register as the single source, refreshed every weekday | Authoritative and updated daily | `scripts/update_register.py`, GitHub Actions |
