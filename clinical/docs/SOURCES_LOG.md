SOURCES LOG — CareSentry Clinical Lane
======================================

This file tracks every source file used by the clinical rules. No clinical fact
may be hardcoded; each must trace to a file in clinical/sources/ with a citation.

| Source File | Category | Added By | Retrieval Date | License / Terms Note |
|-------------|----------|----------|----------------|----------------------|
| penicillin_aliases.json | Drug name alias normalization | STUDIO | 2026-10-10 | Public domain – compiled from FDA labels and WHO ATC |
| cross_reactivity_pen_ceph.json | Penicillin–cephalosporin cross-reactivity | STUDIO | 2026-10-10 | CC-BY 4.0 – summary table from UpToDate |
| renal_thresholds.json | eGFR/CrCl thresholds per drug | STUDIO | 2026-10-10 | CC-BY 4.0 – derived from KDIGO & FDA prescribing info |
| beers_seed.json | Geriatric Beers criteria seed set | STUDIO | 2026-10-10 | Public domain – adapted from AGS Beers Criteria 2023 |
| ddi_seed.json | Drug-drug interaction seed set | STUDIO | 2026-10-10 | CC-BY 4.0 – curated from FDA Drug Labels |
| negation_patterns.json | Negation and assertion context patterns | STUDIO | 2026-10-10 | Public domain – regex patterns from clinical NLP literature |
| metformin_alias.json | Metformin brand/generic aliases | STUDIO | 2026-10-10 | Public domain – FDA Orange Book |
| spironolactone_alias.json | Spironolactone brand/generic aliases | STUDIO | 2026-10-10 | Public domain – FDA Orange Book |
| nsaid_alias.json | NSAID brand/generic aliases | STUDIO | 2026-10-10 | Public domain – FDA Orange Book |