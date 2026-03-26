# Session 35: Admin Setlist Entry and Prediction Backfill + Legal Updates

**Date:** 2026-03-26  
**Goal:** Implement admin mode for manual setlist entry, automated prediction backfill, and legal/fair use content updates.

## Constraints
- Admin page must be password-protected
- Backfill should update existing records, not create duplicates
- Apply User-Agent to all 6 bands (wsp, goose, phish, billy, eggy, um)

## Commands Run
```bash
uv run black src tests scripts
uv run ruff check src tests scripts
npm run build
uv run python scripts/backfill_predictions.py --band wsp --model ckplus --dry-run
```

## Files Changed/Created

### Admin Setlist Feature
| File | Action |
|------|--------|
| `src/jambandnerd/utils/setlist_parser.py` | Created - shared parsing logic |
| `scripts/admin/add_setlist.py` | Modified - uses shared module |
| `apps/web/src/app/admin/setlist/page.tsx` | Created - admin UI |
| `apps/web/src/app/api/admin/setlist/route.ts` | Created - API endpoint |
| `apps/web/src/lib/supabase/server.ts` | Modified - added service role client |
| `apps/web/.env.local.example` | Modified - added admin config |
| `apps/web/src/components/site-footer.tsx` | Added Admin link |

### Backfill Feature
| File | Action |
|------|--------|
| `scripts/backfill_predictions.py` | Created - backfill logic |
| `scripts/run_optimized_pipeline.py` | Modified - integrated backfill |

### Legal/Fair Use Updates
| File | Action |
|------|--------|
| `apps/web/src/app/about/page.tsx` | Updated Notebook description, pipeline step descriptions |
| `apps/web/src/app/data-use/page.tsx` | Added Non-Substitutional Intent, Expressive Content Disclaimer, Notice and Takedown |
| `apps/web/src/app/contact/page.tsx` | Added attribution bullet point, license footer |
| `apps/web/public/robots.txt` | Created with JamBandNerd-Bot identity |
| `src/jambandnerd/data_collection/config.py` | Added JAMBANNERD_BOT_UA constant, updated all 6 band user-agents |
| `src/jambandnerd/data_collection/wsp/session.py` | Updated to use JAMBANNERD_BOT_UA |
| `src/jambandnerd/data_collection/wsp/tourwrangler.py` | Updated to use JAMBANNERD_BOT_UA |

## Validation Status
- `uv run black src tests scripts`: passed
- `uv run ruff check src tests scripts`: passed (4 pre-existing errors in other scripts)
- `npm run build`: passed
- Backfill script: tested on WSP, found 4 stale predictions, regenerated successfully

## Next Step
- Commit changes to feature branch
- For production: add SUPABASE_SERVICE_ROLE_KEY and ADMIN_PASSWORD to web app environment