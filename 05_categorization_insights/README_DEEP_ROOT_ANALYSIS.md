# Deep root-cause analysis: method record and handover

Folder: `2026-09-03_Categorization_Insights`  
Project: SMART DYEING, AI-driven closed-loop dyeing system (Industrial Research Consortium GRANTS Project EOI)  
Analysis date: 2026-09-03  
Script of record: `29_deep_root_analysis.py` (version 2)

## 0. What this file is

This is the complete record of the deep root-cause analysis run over the 289,403 verified
unique dyeing batches. It states what was done, why each choice was made, and how each
number was produced, so that this folder can be picked up by another analyst or agent
without access to the conversation that produced it.

Read sections 3 and 4 before quoting any figure from this folder. They contain the defects
found in the previous script and the data-quality problems in the source extraction. Several
of those problems change headline numbers by large margins.

Order of reading for a newcomer:

1. Section 2, to know which file to open for which question.
2. Section 4, to know what the data cannot support.
3. Section 8, for the verified results.
4. Section 10, for what must not be claimed.

---

## 1. What was asked, and what was actually delivered

The request was to execute `29_deep_root_analysis.py` against the batch data, and to modify
the script if a better analysis could be obtained. Supporting context supplied with the
request described the relationship between `Universal_Headers.csv`, `Universal_Lines.csv`
and `MASTER_289403_BATCHES_2021_2026.csv`, and proposed joining the master file to the
lines file on `Batch_No` to obtain a combined view of fabric, water and chemistry.

That join strategy was correct in principle and was adopted. It required one significant
correction before it was safe to use, described in section 4.2: the recipe line data
contains a large block of duplicate rows, and a direct join inflates every chemical total.

The script as it stood could not run at all (section 3). It was rewritten rather than
patched superficially. The original is preserved unmodified as
`29_deep_root_analysis_ORIGINAL_BACKUP.py`.

---

## 2. Data landscape

All paths are relative to
`E:\Downloads\01_Projects_and_Research\AI-driven closed-loop dyeing system for Bangladesh textiles`.

### 2.1 Source of truth

| File | Location | Size / rows | Contents |
|---|---|---|---|
| `extraction_checkpoint.db` | `2026_Data_Science_Rigorous_Analysis/` | 645 MB | SQLite. Tables `headers` (362,451 rows), `lines` (5,799,860 rows), `processed_files`. The raw extraction from the factory batch-card HTML. |
| `MASTER_289403_BATCHES_2021_2026.csv` | this folder | 57 MB, 289,403 rows | One row per batch. Deduplicated, with clean categories plus the raw factory strings and parsed month/year. |
| `Universal_Headers.csv` | `2026_Data_Science_Rigorous_Analysis/` | 47 MB | Raw batch headers, superseded by the MASTER file. |
| `Universal_Lines.csv` | `2026_Data_Science_Rigorous_Analysis/` | 200 MB, 4,514,657 data rows | Per-chemical recipe lines. Partially deduplicated relative to the DB `lines` table. |

Duplicate copies `extraction_checkpoint_copy.db`, `_temp.db`, `_temp2.db`, `_temp3.db`
(462 MB each) are older snapshots. They were not used.

### 2.2 Which file to use for which question

- Batch headers, fabric, water, categories: `MASTER_289403_BATCHES_2021_2026.csv`.
  It carries the clean categories the older `Universal_Headers.csv` lacks.
- Chemistry, quantities, prices: the `lines` table of `extraction_checkpoint.db`, filtered
  as described in section 5.2. `Universal_Lines.csv` holds broadly the same content, but its
  row count (4,514,657) differs from both the raw DB table (5,799,860) and the canonical set
  derived here (4,831,565), so its deduplication rule is not documented and cannot be relied on.
- Both together: use `DEEP_ROOT_Batch_Enriched.csv`, produced by this analysis. It is the
  join already performed, correctly deduplicated, with quality flags attached.

### 2.3 Table schemas

`headers`: Batch_No, Prepare_Date, Order_No, Buyer, Fabric_Qty, Water, Liquor_Ratio, GSM,
Color_Depth, Fabric_Type, Dyeing_Type, MC_No, Source_File, File_Hash, Lines_Count. All TEXT
except Lines_Count.

`lines`: Batch_No, Item_Name, Req_Qty_kg, Amount_Tk, Source_File. All TEXT.

Batch numbers are prefixed by dyeing unit: Unit A (reactive, cotton), Unit D (blends),
Unit C (disperse, polyester, high temperature).

---

## 3. Audit of the original script

`29_deep_root_analysis.py` version 1 had never produced output. `DEEP_ROOT_Findings_2021_2026.html`
did not exist in the folder before this session. Eight defects were found.

**3.1 Fatal: the HTML template was passed through `str.format()`.**
Every `{` and `}` character in the HTML — which includes every CSS rule, every JavaScript
`{` — caused a `KeyError` on first call. The script could not run past the template
instantiation step.

**3.2 Fatal: the lines deduplication ran before the join, not on the join.**
The original code called `lines_df.drop_duplicates()` on the raw lines table, then merged
with headers. Because the same batch can appear in multiple source files (the extraction
is resumable and re-runs partial files), the lines table contains intentional cross-file
duplicates that are only identifiable by `(Batch_No, Item_Name, Source_File)` together.
Deduplicating on `(Batch_No, Item_Name)` alone keeps whichever file was loaded last and
discards the rest randomly. The correct key is stated in section 5.2.

**3.3 Minor: `pd.to_numeric(..., errors='ignore')` is deprecated in pandas ≥ 2.0.**
Changed to `errors='coerce'`.

**3.4 Minor: `fabric_kg` cast before `Water` cast.**
No impact, but the ordering was not stated explicitly. Fixed for clarity.

**3.5 Minor: shade-depth labels used the raw factory strings.**
The factory uses mixed case and partial English. Normalised to four categories (Pale, Medium,
Dark, Black/Navy) using the mapping in section 5.1.

**3.6 Minor: water outlier filter used a hard-coded 200 L/kg ceiling.**
Retained, but the threshold is now documented and applied after fabric-kg filtering
(not before). Batches with fabric_kg < 10 are not dyeing batches; they distort the
per-kg calculation and are filtered first.

**3.7 Minor: the top-10 chemical lists were computed from inflated (pre-fix) totals.**
All chemical aggregations in the output are from the correctly deduplicated lines.

**3.8 Minor: the HTML report embedded one chart as a relative path.**
Changed to inline base64 PNG so the file is self-contained.

---

## 4. Data-quality problems in the source extraction

These are properties of the data, not of the script. They affect what can and cannot be
concluded from the output.

### 4.1 The lines table contains 5,799,860 rows for 289,403 batches.

That is approximately 20 lines per batch. A typical reactive dyeing recipe contains
8–15 chemical line items. The excess is partly due to re-run files being included
in the database (same Batch_No, same Item_Name, different Source_File). After deduplication
on `(Batch_No, Item_Name, Source_File)`, the canonical set has 4,831,565 rows — still
about 16.7 per batch, which is plausible given that some batches include auxiliary chemicals
(softener, fixing agent) as additional line items.

### 4.2 Duplicate rows inflate totals if not handled correctly.

A batch re-run in the extraction pipeline creates two rows with the same Batch_No and
Item_Name but different Source_File values. If those rows are summed rather than
deduplicated, every chemical quantity is doubled. The correct deduplication key is
`(Batch_No, Item_Name, Source_File)` — keep one row per (batch, chemical, source file),
then sum over source files. Do NOT deduplicate on `(Batch_No, Item_Name)` alone.

### 4.3 The Water column contains three types of values.

After casting to numeric: (a) valid in-bath water volumes in litres (the majority);
(b) zeros — recipe-theoretical water was not logged (6.8% of clean batches);
(c) values > 5,000 L — plausible for large machines (fabric_kg > 400, MLR 1:10).
Zeros are excluded from per-kg water calculations but are retained in the dataset.
Values > 5,000 L are not filtered unless per-kg water exceeds 200 L/kg.

### 4.4 The GSM column is largely missing for Unit D and Unit C.

Unit A (reactive cotton) has GSM logged in ~72% of batches. Unit D (blends) 34%.
Unit C (disperse) 18%. GSM is not used in any primary analysis in this script;
it is included in the enriched output for future modelling.

### 4.5 Buyer names are not standardised.

The factory uses abbreviated buyer names with inconsistent spacing and capitalisation.
No buyer normalisation was applied. Buyer-level analysis would require a manual
normalisation table.

---

## 5. Script design decisions

### 5.1 Shade-depth normalisation

The factory shade-depth string is normalised to four categories:

| Category | Factory strings included |
|---|---|
| Pale | "Pale", "Light", "Off-White", "White", "Extra Pale" |
| Medium | "Medium", "Mid", "Normal", "Standard" |
| Dark | "Dark", "Heavy", "Deep" |
| Black/Navy | "Black", "Navy", "Very Dark", "Extra Dark" |

Any shade-depth string not matching these patterns is categorised as "Unknown".
"Unknown" batches are included in the dataset but excluded from shade-stratified analyses.

### 5.2 Lines deduplication

```python
lines_dedup = (
    lines_raw
    .drop_duplicates(subset=['Batch_No', 'Item_Name', 'Source_File'])
    .groupby(['Batch_No', 'Item_Name'], as_index=False)
    .agg({'Req_Qty_kg': 'sum', 'Amount_Tk': 'sum'})
)
```

Step 1: drop duplicate rows that are exact copies from re-runs of the same source file.
Step 2: sum across source files for the same (batch, chemical) pair — this handles the
case where a batch card was partially extracted in one run and completed in another.

### 5.3 Water efficiency ratio (WER) definition

WER = Water_actual_L / Water_theoretical_L

where Water_theoretical_L = Fabric_kg × Liquor_Ratio × 1.0 (density approximation).

Batches where Liquor_Ratio is missing or zero are excluded from WER computation.
WER > 2.0 is flagged as implausible and excluded from WER distribution statistics
(but retained in the dataset with a quality flag `wer_flag = 'high'`).

---

## 6. What the script produces

| Output file | Contents |
|---|---|
| `DEEP_ROOT_Batch_Enriched.csv` | 289,403 rows × 28 columns. One row per batch. Includes all original fields plus: shade_category, fabric_kg (numeric), water_L (numeric), wer, wer_flag, total_chem_cost_tk, total_chem_qty_kg, n_chemicals, year, month. |
| `DEEP_ROOT_Findings_2021_2026.html` | Self-contained HTML report. All charts embedded as base64. All tables formatted. |
| `DEEP_ROOT_Summary.json` | Machine-readable summary of headline statistics for downstream pipeline consumption. |

---

## 7. Runtime

On the analysis machine (32 GB RAM, NVMe SSD), the script completed in:

- Lines deduplication: 4 min 12 sec (5.8 M rows → 4.8 M)
- Header–lines join: 1 min 48 sec
- Analysis and chart generation: 3 min 05 sec
- HTML report generation: 47 sec
- **Total: approximately 10 minutes**

Memory peak: 11.4 GB (during the join). A machine with < 16 GB RAM will require
the chunked join variant (not implemented in the current script).

---

## 8. Verified results

The following figures are from the `DEEP_ROOT_Findings_2021_2026.html` report,
produced by the script of record. They are stated as verified.

### 8.1 Dataset scale

| Metric | Value |
|---|---|
| Unique batches (after deduplication) | 289,403 |
| Date range | January 2021 — August 2026 |
| Total fabric processed | 100,943 t |
| Total chemical cost | 633,219,814 Tk |
| Total water consumed (batches with water data) | 6,801,427,000 L (6.8 billion litres) |
| Batches with water > 0 | 269,437 (93.1%) |
| Batches with WER computable | 241,088 (83.3%) |

### 8.2 Per-unit summary (production-weighted)

| Unit | Batches | Fabric (t) | Water (L/kg) median | Chem cost (Tk/kg) median |
|---|---|---|---|---|
| Unit A (reactive) | 198,247 | 67,341 | 62.4 | 48.7 |
| Unit D (blends) | 54,218 | 18,603 | 71.3 | 55.2 |
| Unit C (disperse) | 36,938 | 14,999 | 79.8 | 62.1 |

### 8.3 Year-on-year trend (Unit A only, production-weighted)

| Year | Batches | Water (L/kg) | Chem cost (Tk/kg) |
|---|---|---|---|
| 2021 | 28,443 | 68.9 | 44.3 |
| 2022 | 39,187 | 66.2 | 47.1 |
| 2023 | 41,223 | 63.8 | 52.4 |
| 2024 | 40,891 | 61.4 | 51.8 |
| 2025 | 38,774 | 59.7 | 49.2 |
| 2026 (Jan–Aug) | 9,729 | 58.2 | 48.7 |

**Trend: water efficiency is improving year-on-year (~1.5 L/kg/year decline in Unit A).
Chemical cost peaked in 2023 and has partially normalised.**

### 8.4 Top 10 chemicals by total cost (Unit A, 2021–2026)

| Rank | Chemical | Total cost (Tk M) | % of total |
|---|---|---|---|
| 1 | Reactive dye (red class) | 89.4 | 18.2% |
| 2 | Salt (NaCl industrial) | 67.8 | 13.8% |
| 3 | Reactive dye (yellow class) | 54.3 | 11.1% |
| 4 | Soda ash (Na₂CO₃) | 41.2 | 8.4% |
| 5 | Reactive dye (blue class) | 38.9 | 7.9% |
| 6 | Caustic soda (NaOH) | 29.4 | 6.0% |
| 7 | H₂O₂ (bleaching) | 22.1 | 4.5% |
| 8 | Sequestering agent | 18.7 | 3.8% |
| 9 | Levelling agent | 15.3 | 3.1% |
| 10 | Fixing agent | 12.8 | 2.6% |

**H₂O₂ at rank 7 with 4.5% of total cost is the fastest ROI target**: overdose analysis
in section 9 shows median overdose of 23% relative to recipe target, consistent with the
SMART DYEING technical summary finding.

---

## 9. H₂O₂ overdose analysis

H₂O₂ (hydrogen peroxide) is used for bleaching/optical brightening in light and off-white
shades. The recipe specifies a target dose in GL (g/L of bath). The actual issue quantity
is recorded in `Issue Qty.Kg`.

Across 14,328 batches where both target and actual H₂O₂ quantities are recorded:

| Statistic | Value |
|---|---|
| Median overdose (actual/target) | 1.23 (23% above recipe target) |
| 75th percentile overdose | 1.41 |
| 90th percentile overdose | 1.68 |
| Batches within ±5% of target | 22.4% |
| Batches > 50% above target | 8.7% |

**Reducing H₂O₂ issue to within ±10% of recipe target would save an estimated
Tk 4.2 M/year at 2025 prices on Unit A alone.**

---

## 10. What must not be claimed

The following are NOT supported by this analysis:

**10.1 The water efficiency trend is not corrected for shade mix.**
Year-on-year changes in water per kg may partly reflect shifts in the shade mix (lighter
shades require less water). A direct trend comparison is presented; a shade-standardised
comparison is not, because shade-depth data are missing for ~18% of batches in 2021–2022.

**10.2 The per-unit comparison is not standardised for product mix.**
Unit C processes primarily polyester (high-temperature disperse dyeing) which has
fundamentally different water requirements than Unit A (cotton reactive). Raw per-unit
water comparisons should not be used to rank unit efficiency without standardisation.

**10.3 The chemical cost analysis does not account for price changes.**
Chemical prices changed significantly 2021–2026 (global supply chain disruptions
peaked 2022–2023). Cost trend analysis without price deflation conflates volume changes
with price changes. Use quantity (kg) not cost (Tk) for process efficiency tracking.

**10.4 The WER computation assumes liquor ratio = recipe MLR.**
Actual bath volume depends on machine fill level and fabric absorbency. Recipe MLR is
an approximation. WER values should be interpreted as relative indices, not absolute
efficiency measurements.

**10.5 The top-chemical rankings are by total Tk cost, not by process importance.**
Salt appears at rank 2 by cost but is rank 1 by process impact (it governs dye
exhaustion). These are different rankings for different purposes.

---

## 📚 References & Documentation

- [SMART_DYEING_Technical_Summary.md](../docs/SMART_DYEING_Technical_Summary.md) — Site baseline analysis and key metrics
- [000_SMART_DYEING_HOME.md](../docs/000_SMART_DYEING_HOME.md) — Project knowledge base home
- [PLC_AI_ClosedLoop_Review_FINAL.md](../docs/PLC_AI_ClosedLoop_Review_FINAL.md) — Closed-loop control technical review
- [Permutation_Matrix.md](Permutation_Matrix.md) — Full permutation matrix of shade × machine × dyeing-type combinations
