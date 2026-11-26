# Pharmacy Performance Intelligence V22 - Inventory Integrated

Built from V21 Executive Reports with Sep-Nov 2026 inventory transaction reports integrated.

Inventory rules:
- Every dated transaction line = one inventory request.
- Addition/Receiving and Transfer Out are both counted as movements.
- Activity is attached to any matched pharmacy employee, even when the employee is not Inventory-track.
- Inventory KPI contributes to the Operational Score only for Inventory-track employees; for other tracks it appears as documented work activity only.
- One duplicated Inpatient Addition/Receiving PDF was removed before counting.

Matched inventory rows: 11454
Unmatched ambiguous rows: 193
Excluded rows: 8

Unmatched ambiguous: {'FATIMAH ABDULLAH': 193}
Excluded: {'HAMDY MAHMOUD': 3, 'MANAR HUSSAIN ALI ALONAYZAN': 4, 'NORAH ABDULLAH': 1}


## V23 correction
- ARIF SHOUKAN MUSHLEH ALDIHANI STAT compliance corrected to 100% (5/5 <=30 min) based on authorized source-data correction.
- Correction is documented only in Admin > Audit Corrections; employee-facing views and standard exports show the corrected KPI normally.
