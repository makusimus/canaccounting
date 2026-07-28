# CanAccounting Changelog

## 2026-07-27 — v3 Migration

### What changed
- **Complete rewrite** from v2 → v3: SQLite-backed backend with batch processing pipeline
- **Database:** Added `canaccounting.db` — all transactions now stored in SQLite
- **Batch workflow:** Upload bank files → Categorize → Review → Process → Commit
- **Higher categories:** New `higher_category` column — "Running costs" vs "Periodic costs"
- **Duplicate detection:** Matches new uploads against committed transactions
- **Override system:** Pattern-based category overrides (preserved from v2, 48 patterns)
- **CSV Export:** Now includes "Higher category" column
- **UI:** Wider table, higher category badges, filter improvements
- **Binding:** Changed from `127.0.0.1` to `0.0.0.0` for SSH tunnel access

### Files replaced
- `server.py` — replaced v2 (354 lines) with v3 (883 lines)
- `index.html` — replaced with v3 version (higher category column)

### Migration notes
- PROD database was created fresh on first v3 startup
- Overrides from v2 were preserved at `overrides.json`
- No data loss — v2 didn't use a database
