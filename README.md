# Pharmacy Intelligence — GitHub Ready

Created by Automation Supervisor Ali Alsada.

## Upload
Upload the contents of this folder to the root of the GitHub repository and enable GitHub Pages from the main branch/root.

## Current password
`Pharmacy@2026`

The password is checked by SHA-256 in the browser. GitHub Pages is a static public host, so this is an access gate, **not server-side security**. For sensitive operational data use private hosting or an authentication layer such as Cloudflare Access / an authenticated app.

## Update model
- Dispensing: monthly
- STAT: monthly
- Hold: monthly
- Wasfaty: daily
- Inventory snapshot: daily

### File naming for automatic detection
Save/download new attachments into `incoming/` with one of these prefixes:
- `dispensing_qch_YYYY-MM.xlsx`
- `dispensing_pmfh_YYYY-MM.xlsx`
- `stat_qch_YYYY-MM.xlsx`
- `stat_pmfh_YYYY-MM.xlsx`
- `hold_YYYY-MM.xlsx`
- `wasfaty_YYYY-MM-DD.xlsx`

Run `python scripts/update_dashboard.py`. It refreshes `data/platform-data.json` and `data/platform-data.js`; the page design does not need to change.

## Gmail automation
The included GitHub Action can fetch `.xlsx` attachments daily if these repository secrets are configured: `GMAIL_CLIENT_ID`, `GMAIL_CLIENT_SECRET`, `GMAIL_REFRESH_TOKEN`. Optional repository variable: `GMAIL_QUERY`. If secrets are absent, the workflow simply processes files already placed in `incoming/`.

## Inventory Intelligence integration
The updater supports a daily inventory export. Set repository variable `INVENTORY_EXPORT_URL` to a CSV endpoint containing:
`nupco_code,medication_name,lc_qty,mosool_qty,updated_at`

Map Wasfaty medication names to NUPCO codes in `data/medication-map.csv`:
`wasfaty_medication,nupco_code`

Once matched, the Wasfaty page automatically shows:
- **Despite Availability** — Wasfaty items whose LC or Mosool quantity was > 0 in the current inventory snapshot.
- **Due to Unavailability** — matched Wasfaty items with zero LC + Mosool.
- Inventory matched / unmatched counts.

For historical “available at the exact prescription time”, archive one inventory snapshot per day instead of replacing `inventory-latest.csv`; the updater can then be extended to join by prescription date.

## KPI behavior
KPI trend charts always show the full Aug 2025 → current series. Selecting a month changes the KPI cards and tables, while the full trend remains visible for context.
