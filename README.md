Pharmacy Performance Intelligence V31 — Clean Role Engine

Key changes:
- Rebuilt scoring from V30 logic; no percentile ranking.
- All workload benchmarks use monthly-normalized rates.
- Benchmark = average of top 3 monthly rates in the correct peer group.
- UI filters never affect benchmarks.
- Staff roles have separate core models (Regular / Clinical / Inventory).
- Additional out-of-role work is capped at +5 points.
- Supervisors/Managers: personal dispensing is evidence only, not core MCC.
- Auto MCC requires at least 3 mapped scored staff; otherwise MCC is entered in Admin.
- Supervisor final = 50% MCC + 50% Administrative.
- Manager final = 60% MCC + 40% Administrative.
- Maryam Al Muzayen default MCC = 70% mapped Acute Care team + 30% personal Clinical core.
- Existing Arif STAT correction remains in source data/audit history from prior version.
