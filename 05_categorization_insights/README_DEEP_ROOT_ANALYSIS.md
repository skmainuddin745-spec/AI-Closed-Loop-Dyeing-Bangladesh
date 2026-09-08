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
The template contained literal CSS and JavaScript braces, for example
`:root{--bg:#0f172a;...}`. Python's format parser reads that as a replacement field named
`--bg` and raises `KeyError: '--bg'`. Verified directly:

```
>>> ':root{--bg:#0f172a;--card:#1e293b}'.format(total=1)
KeyError: '--bg'
```

The script therefore always terminated at the final step, after doing all its work.

**3.2 Fatal: chart data was defined after it was used.**
The `new Chart(...)` constructors appeared in a `<script>` block placed before the block
defining `YOYL`, `YOYV`, `YRL` and the rest. Every chart would have thrown
`ReferenceError` even if 3.1 had been fixed.

**3.3 An entire report section was structurally empty.**
The "Top 15 Most Active Machines" table read `MC_No` from `headers`. That column is empty in
all 362,451 rows. The section could only ever render blank. See section 4.1.

**3.4 Arbitrary row selection per batch.**
Headers were read as `SELECT ... FROM headers GROUP BY Batch_No`. SQLite returns an
arbitrary row from each group. With 362,451 header rows covering 289,403 batches, roughly
73,000 rows were duplicates, and which one represented each batch was undefined and could
change between runs.

**3.5 Liquor ratio parsing could corrupt values.**
`clean_float()` was `float(re.sub(r'[^\d.]','',str(v)))`, which strips the colon. A ratio
written `1:8` becomes `18.0`. The stored values happen to be plain decimals, so no damage
occurred in practice, but the function was unsafe for the field it was applied to.

**3.6 Mean of ratios instead of a mass-weighted figure.**
Water intensity was computed as the mean of per-batch litres-per-kilogram. That weights a
5 kg sample batch the same as a 1,145 kg production batch, and does not reconcile to a
factory water bill. See section 5.4.

**3.7 A duplicated header row inside the table body.**
`wi_table_html` was built with its own header row, then inserted as the table body while a
separate header was also emitted, so the header would have appeared twice.

**3.8 Chemistry was absent entirely.**
Version 1 read only the monthly permutation CSV and the header table. Chemical names,
quantities and costs, which is where roughly half the analytical value of this dataset sits,
were not touched.

---

## 4. Data-quality findings

These are properties of the source extraction, not of the analysis. Each one was verified
directly against the database.

### 4.1 Machine number is empty in 100% of rows

```sql
SELECT MC_No, COUNT(*) FROM headers GROUP BY MC_No;
-- ('', 362451)
```

Consequence: no machine-level utilisation, capacity-fit, per-machine efficiency or
machine-as-a-feature analysis is possible from this extraction. Recovering it requires
returning to the source HTML files. Any pipeline referencing `MC_No` will silently produce
a constant column.

### 4.2 The recipe line table contains 968,295 duplicate rows

52,228 batches were extracted from more than one HTML source file, for example both
`BATCH_337761.html` and `C-337761.html`. Their recipe lines appear once per source file.
Verified: the duplicate groups number 1,020,094 at the (Batch_No, Item_Name, Req_Qty_kg,
Amount_Tk) level.

A direct join of `MASTER` to `lines` on `Batch_No` therefore overstates every chemical mass
and every cost by roughly 17 percent. The handling is described in section 5.2.

For 18,338 of those batches the two source files disagree on how many lines were extracted,
so the choice of which extraction to keep is not arbitrary and had to be made explicitly.

### 4.3 25,072 batches have no recorded water, and they are almost all Unit C

A block of batches carries the liquor ratio `1.00` with water recorded as exactly the fabric
weight. That is the placeholder ratio written through into the water field, not a metered
volume. No exhaust jet dyeing process runs at 1 litre per kilogram; the physical floor is
around 1:3 even on ultra-low-liquor machines.

Distribution across units, from the enriched export:

| Unit | Batches | Usable | Placeholder water | Share of unit |
|---|---|---|---|---|
| Unit A | 177,204 | 176,030 | 0 | 0.0% |
| Unit D | 77,612 | 76,397 | 0 | 0.0% |
| Unit C | 34,587 | 8,708 | 25,463 | 73.6% |

By year: 2022 3,379, 2023 7,645, 2024 5,728, 2025 7,684, 2026 1,027.

This is the single most consequential finding in the dataset for project scoping. Water is
largely not captured on the batch card for the polyester and disperse unit. No water
baseline, no saving verification and no water-side model can be built for Unit C from this
extraction. Either the field is populated at source, or Unit C is scoped out of the
water-reduction claim and retained for chemical and energy work only.

Effect on the headline KPI: leaving these batches in yields a plant water intensity of
6.27 L/kg. Removing them yields 6.75 L/kg. The lower figure is an artefact of averaging a
phantom 1 L/kg against a real operating range near 6 to 7 L/kg.

### 4.4 Liquor ratio distribution

```
7.00  178,871      6.00   83,990      6.50  30,649
1.00   25,632      5.00   17,650      7.50  15,832
8.00    3,750     10.00    1,006     12.00     436     8.50   244
```

The 25,632 records at 1.00 are the placeholders of section 4.3. A further 220 fall outside
the plausible window 1:1.5 to 1:20.

### 4.5 Recorded water disagrees with ratio times weight on 27,650 batches

Where a liquor ratio is valid, water should equal ratio multiplied by fabric weight. On
27,650 usable batches the two differ by more than 15 percent. Those batches are retained
(the recorded water is used) but the count is reported, because it bounds how far the ratio
field can be trusted as an independent input.

### 4.6 Chemical cost per kilogram steps at year boundaries

Monthly chemical cost per kilogram, derived from the enriched export:

```
2025-10  72.50   2025-11  62.93   2025-12  67.56
2026-01 119.25   2026-02 128.42   2026-03 131.58   2026-04 115.85
```

A near doubling between December and January, holding at the new level, is not how physical
dosing behaves. The same pattern appears at the 2023 boundary (46.87 to 70.84 Tk/kg, plus
51 percent). This is characteristic of a price-list revaluation in the source system, and
may also carry currency effects.

Consequence: chemical mass per kilogram is the safe efficiency measure across these
boundaries. Cost per kilogram must be verified against procurement records before it is
presented as a real change in consumption or as evidence of saving. The report detects this
automatically and prints a warning naming the affected years.

### 4.7 Stray year labels

The master file contains 4 batches dated 2017, 1 dated 2018 and 172 dated 2019, against
tens of thousands per year from 2020 onward. These are date-parse strays. Left in a trend
line, a single 2018 batch reads as a year at 10.00 L/kg and looks like a real efficiency
excursion. They are shown in the yearly table for completeness and excluded from every
trend, chart and growth calculation.

### 4.8 Coverage window

2020 is complete (all twelve months present, 25,141 batches), so the 2021 year-on-year
figure is a valid comparison. 2026 runs January to August and is marked partial. The
analysis window is 2020-01 to 2026-08, wider than the "2021_2026" in the master file name.

---

## 5. Method, and why each choice was made

### 5.1 Header source: the MASTER csv, not the database

The deduplicated master file is used as the header source rather than
`SELECT ... GROUP BY Batch_No` over `headers`. Reason: the group-by returns an undefined row
per batch out of 362,451 rows (defect 3.4), whereas the master file is already one row per
batch and carries the clean categories. The database is still opened, but only for the audit
counts and the recipe lines.

### 5.2 Canonical source-file selection

Rule: for each batch, keep the lines from exactly one source file, chosen as the file
contributing the most lines; ties break alphabetically on the file name.

Why the fullest extraction: for 18,338 batches the two source files disagree on line count,
which means one extraction is incomplete. Taking the larger recovers the fuller recipe.

Why not a naive `SELECT DISTINCT Batch_No, Item_Name, Req_Qty_kg, Amount_Tk`: a real recipe
can legitimately dose the same chemical twice with an identical quantity and price, for
example the same auxiliary in two rinse stages. Distinct-collapsing would silently delete
those genuine second doses. Selecting a whole source file preserves the recipe exactly as
that extraction recorded it.

Why alphabetical tie-breaking: it makes the choice reproducible across runs, which a
`GROUP BY` does not guarantee.

Result: 5,799,860 raw lines reduce to 4,831,565 canonical lines, removing 968,295 duplicates.
Verified independently with a window-function query (section 9).

### 5.3 Physical plausibility screening

Records outside these windows are excluded from KPI arithmetic and counted in the integrity
panel of the report. Nothing is dropped silently.

| Screen | Window | Excluded | Reason |
|---|---|---|---|
| Fabric load | 5 to 5,000 kg | 2,791 | Outside the range of an exhaust jet machine. |
| Water intensity | 2 to 60 L/kg | 404 | Below roughly 1:3 is physically unreachable; above 60 indicates a unit or decimal error. |
| Placeholder water | ratio under 1.5 and water within 2% of fabric weight | 25,072 | Section 4.3. Not a measurement. |
| Liquor ratio | 1:1.5 to 1:20 | 220 | Outside the operating range of the equipment. |
| Chemical dose | up to 3,000 g/kg | 167 | Above three kilograms of chemical per kilogram of fabric is an extraction error. Chemistry is zeroed for these batches only; their water figures are retained. |
| Zero or blank fabric quantity | | 1 | Cannot compute any intensity. |

Net: 261,135 of 289,403 batches (90.2%) are usable for KPI arithmetic. Every batch remains
present in the enriched export with a `QC_Usable` flag, so nothing is lost to a downstream user.

### 5.4 Statistical choices

**Mass-weighted intensity as the primary KPI.** Total water divided by total fabric, not the
mean of per-batch ratios. Reason: the mean of ratios weights a 5 kg sample the same as a
1,145 kg production batch, and does not reconcile to a factory water bill. The weighted
figure does, which is what a grant auditor will check against utility records.

**Percentiles reported alongside.** Median, P25, P75 and P90 are reported for every cut.
Reason: the spread is the actionable quantity. A wide P25-to-P90 gap on one fabric and shade
combination means the same product is being run at very different water levels, which is
exactly the variance a closed-loop controller removes. P90 is also the better early indicator
of a control system working, because control compresses the tail before it moves the mean.
Percentiles are linear-interpolated on the sorted values.

**Year-on-year growth between consecutive complete years only.** A year counts as complete
when all twelve months carry batches and the year holds at least 1,000 batches. This
prevents a partial or stray year producing a fictional growth rate.

**Partial-month exclusion from rankings.** The first and last months of coverage are excluded
from the peak, trough and water-efficiency month rankings, so the ranking is not an artefact
of where the extraction window happens to start and stop.

**Run-rate projection labelled as a projection.** The 2026 full-year figure is computed from
the observed monthly rate and stated in the report as an estimate, not a measurement.

### 5.5 Chemical classification

495 distinct product names are classified by rule into eight classes, evaluated in this
order: Salt (electrolyte), Alkali, Bleach/redox, Dyestuff, Acid, Enzyme, Softener/finish,
Auxiliary. Ordering matters: peroxide is tested before dye brands so that a bleach product
carrying a colour word is not misfiled.

Dyestuff detection uses brand tokens (BEZAKTIV, REMAZOL, NOVACRON, RIFAZOL, AVITERA,
DRIMAREN, TAICRON, NEOCRON, TERASIL, DIANIX, LEVAFIX, CIBACRON and others) with a secondary
colour-word rule (BLACK, NAVY, TURQ, CARMINE, RUBINE, SCARLET, MAGENTA, CRIMSON, VIOLET,
CORAL).

This is a heuristic and it is stated as one. `DEEP_ROOT_Chemical_Master.csv` prints the class
next to every product with its mass and cost, so every assignment can be audited. The
Auxiliary bucket (219 products, 10.2% of mass, 24.2% of spend) is the one most worth
spot-checking, since it is the residual category.

Classification is memoised: 495 distinct names against 4.8 million lines, so the rules run
495 times rather than millions of times.

### 5.6 Savings methodology

For every fabric by shade by GSM peer group holding at least 200 usable batches, the group's
own 25th-percentile water intensity is taken as the benchmark. Each batch above it
contributes `(intensity - P25) x fabric_kg` litres of addressable excess.

Why the plant's own P25 rather than a literature or vendor figure: it is an operating point
the plant already reaches on a quarter of its own batches of that exact fabric, shade and
weight. It cannot be dismissed as a theoretical target, which is what a grant reviewer will
test first. 49 peer groups qualify. The minimum P25 across them is 5.7 L/kg, so no benchmark
sits at an implausible floor.

Why a minimum group size of 200: below that the P25 is unstable and a handful of unusual
batches can set the benchmark.

What the number is and is not: it is a ceiling on control-side saving before any equipment
change, not a forecast. Part of the P25-to-P90 spread comes from real differences the four
categories do not capture, including specific shade, buyer fastness requirement, and the
machine actually used. Machine identity is entirely absent (section 4.1) and is a plausible
driver of some of the residual variance. The report states this explicitly next to the number.

### 5.7 Automatic cost-step detection

Consecutive trend years are compared on chemical cost per kilogram. A rise above 40 percent
is flagged automatically in the report with the years and magnitudes named. This is a guard
so that the price revaluation of section 4.6 cannot be quoted as an efficiency result by a
later reader who has not seen this file.

---

## 6. Engineering constraints and how they were handled

The analysis runs on the desktop Linux workspace, which has 895 MB of RAM, 2 cores, and a
shell call ceiling of about 180 seconds per invocation. Background processes do not survive
between calls. Three changes were required to make a 5.8 million row job fit.

**6.1 Columnar storage instead of a dict per batch.** A Python dict of about 20 keys costs
roughly 1.2 kB, which is 350 MB across 289,403 batches, before any accumulator. Replaced with
packed `array` columns (doubles for quantities, small integers for interned category codes),
costing about 25 MB. Group accumulators also hold raw doubles in `array('d')` rather than
lists of boxed floats. The category interning helpers are `code()` and `label()`.

**6.2 Aggregation pushed into SQL.** Streaming 4.8 million rows through a Python loop did not
finish in the available time. The join and the sums now run inside SQLite against two
temporary tables: `canon` (batch to canonical source file) and `icls` (product name to class
code). Python receives roughly one million pre-aggregated batch-by-class rows instead of 4.8
million raw ones.

`CAST(Req_Qty_kg AS REAL)` is used inside SQL rather than the Python numeric parser. This was
verified safe first: the table contains no blanks, no thousands separators, and no value that
casts to zero from a non-empty string, so the cast is exactly equivalent to the Python parser
used elsewhere.

**6.3 Local database staging and a resumable cache.** SQLite full scans against the mounted
volume run about an order of magnitude slower than against local disk (a group-by that takes
23 seconds locally was not completing in minutes over the mount). The 645 MB database is
copied once to `~/.deep_root_cache/work.db` and reused. The result of the chemistry join is
cached to `~/.deep_root_cache/chem.bin` and `chem_meta.json`, keyed on the size and
modification time of both the database and the master csv, so it invalidates automatically if
either changes. A first run builds the cache, subsequent runs restore it in about a second.

Neither the cache nor the local copy is written into the project folder.

---

## 7. Outputs

All four files are regenerated from scratch on every run.

### 7.1 `DEEP_ROOT_Findings_2021_2026.html`

Self-contained report, 8 sections, 8 charts (Chart.js 4.4.0 loaded from CDN, so charts need
an internet connection; all tables render offline). Sections: data integrity, production by
year, water and chemistry by unit and shade, fabric by shade intensity matrix, chemistry by
class and product, addressable saving, seasonality and process mix, implications for modelling.

Chart data is embedded as JSON in a `<script type="application/json">` block and parsed at
load, which is what removes the ordering defect 3.2. The template uses token replacement
rather than `str.format()`, which is what removes defect 3.1.

### 7.2 `DEEP_ROOT_Batch_Enriched.csv`

289,403 rows, one per batch. This is the merged modelling table: the header categories joined
to correctly deduplicated per-batch chemistry. Use this rather than performing the join again.

| Column | Meaning |
|---|---|
| `Batch_No` | Join key, unit prefix Unit A / Unit D / Unit C |
| `Year`, `Month` | Parsed from the batch date |
| `Dye_Unit` | Unit A reactive, Unit D blends, Unit C disperse |
| `Fabric_Category`, `GSM_Category`, `Shade_Category` | Clean categories from the master file |
| `Dyeing_Type` | Process route code |
| `Fabric_Kg`, `Water_L`, `Liquor_Ratio_1_to_X` | As recorded |
| `Water_Intensity_L_per_kg` | Water divided by fabric |
| `Recipe_Lines` | Canonical line count for the batch |
| `Chem_Total_Kg`, `Chem_Cost_Tk` | Totals over canonical lines |
| `Chem_g_per_kg`, `Cost_Tk_per_kg` | Normalised by fabric weight |
| `Salt_Kg`, `Salt_g_per_kg` | Electrolyte, the effluent conductivity driver |
| `Dye_Kg`, `Dye_g_per_kg` | Dyestuff only |
| `Alkali_Kg` | Soda ash and caustic |
| `QC_Usable` | 1 if the batch passed all screens in 5.3. **Filter on this.** |
| `QC_Chem_Excluded` | 1 if chemistry was zeroed as implausible while water was kept |

### 7.3 `DEEP_ROOT_Chemical_Master.csv`

495 rows, one per product: class, line count, batches used in, batch penetration percent,
total kilograms, total cost, implied unit price, share of total mass. Use it to audit the
classification of section 5.5.

### 7.4 `DEEP_ROOT_Savings_Opportunity.csv`

49 rows, one per qualifying peer group: batches, fabric, water, weighted and median and P25
and P75 and P90 intensity, addressable excess litres, excess as a percent of group water,
salt intensity, cost intensity. Sorted by addressable excess descending, so the top rows are
where to start.

---

## 8. Verified results

Population: 289,403 batches, of which 261,135 (90.2%) pass the screens. 4,831,565 canonical
recipe lines. Window 2020-01 to 2026-08.

### 8.1 Headline

| Measure | Value |
|---|---|
| Fabric dyed | 123,258 t |
| Process water | 832.46 ML |
| Water intensity, mass-weighted | 6.75 L/kg |
| Chemicals dosed | 62,257 t |
| Salt | 34,006 t |
| Dyestuff | 3,568 t |
| Chemical cost | 61.81 Tk/kg (see 4.6 before quoting) |
| Addressable water excess | 70.0 ML, 8.41% of recorded water |

### 8.2 By year

| Year | Batches | Fabric t | Water ML | L/kg wtd | Median | P90 | Tk/kg | YoY |
|---|---|---|---|---|---|---|---|---|
| 2020 | 24,652 | 9,960 | 63.40 | 6.36 | 6.50 | 12.63 | 36.60 | |
| 2021 | 45,472 | 20,609 | 132.16 | 6.41 | 6.50 | 10.71 | 36.46 | +84.5% |
| 2022 | 46,505 | 20,448 | 142.21 | 6.95 | 7.00 | 8.57 | 46.87 | +2.3% |
| 2023 | 38,669 | 17,944 | 124.68 | 6.95 | 7.00 | 8.00 | 70.84 | -16.9% |
| 2024 | 41,935 | 21,014 | 144.28 | 6.87 | 7.00 | 7.50 | 62.95 | +8.4% |
| 2025 | 40,841 | 21,317 | 144.91 | 6.80 | 7.00 | 7.50 | 65.91 | -2.6% |
| 2026 partial | 22,900 | 11,960 | 80.77 | 6.75 | 7.00 | 7.12 | 129.16 | |

The substantive trend is in P90, not the mean: 12.63 in 2020 falling to 7.12 in 2026. The
tail of wasteful batches has been compressed considerably while the median has stayed near
7.00. That is the shape of a process that has been standardised but not yet optimised, which
is the condition a closed-loop controller is designed to improve on.

### 8.3 By dyeing unit

| Unit | Batches usable | Fabric t | L/kg wtd | P25 | P90 | Dye g/kg | Salt g/kg | Tk/kg |
|---|---|---|---|---|---|---|---|---|
| Unit A reactive | 176,030 | 94,914 | 6.77 | 6.50 | 7.50 | 32.21 | 292.2 | 67.79 |
| Unit D blends | 76,397 | 26,670 | 6.74 | 6.50 | 12.50 | 19.12 | 234.8 | 43.81 |
| Unit C disperse | 8,708 | 1,675 | 6.05 | 6.00 | 6.00 | 0.32 | 8.3 | 9.08 |

The Unit C row rests on 8,708 of 34,587 batches because of section 4.3, and must not be read as
representative of that unit. Unit D has by far the widest tail (P90 of 12.50 against a P25 of
6.50), which makes it the highest-variance target in the plant.

### 8.4 By shade depth

| Shade | Batches | Fabric t | L/kg wtd | P25 | P90 | Dye g/kg | Salt g/kg | Tk/kg |
|---|---|---|---|---|---|---|---|---|
| Light/Medium Colored | 191,402 | 89,223 | 6.78 | 6.50 | 8.96 | 31.14 | 300.0 | 71.97 |
| White/Bleach | 40,225 | 18,653 | 6.64 | 6.00 | 7.50 | 0.04 | 3.8 | 15.15 |
| Dark/Extra Dark | 29,508 | 15,382 | 6.75 | 6.50 | 8.00 | 51.30 | 466.2 | 59.43 |

Dye and salt intensity rise together with shade depth, as reactive chemistry predicts: more
electrolyte is needed to drive more dye onto the fibre. Dark shades carry 466 g/kg of salt
against 300 for light and medium. Shade depth is known before a batch starts, which makes it
the natural first input to a recipe optimiser.

Water intensity, by contrast, barely moves with shade (6.64 to 6.78). This is worth noting:
it suggests machines are being filled to a standard ratio regardless of what the shade
actually requires, which is itself the opportunity.

### 8.5 By fabric

| Fabric | Batches | Fabric t | L/kg wtd | P25 | P90 | Salt g/kg | Tk/kg |
|---|---|---|---|---|---|---|---|
| Composite | 75,647 | 43,280 | 6.79 | 6.50 | 7.50 | 313.7 | 73.90 |
| Rib Fabric | 55,958 | 25,511 | 6.74 | 6.00 | 9.09 | 269.7 | 59.93 |
| Single Jersey | 52,813 | 21,341 | 6.69 | 6.00 | 10.35 | 223.7 | 48.33 |
| Lycra S/J | 37,204 | 17,322 | 6.68 | 6.00 | 7.89 | 274.0 | 52.72 |
| Fleece/Heavy | 19,320 | 8,702 | 6.89 | 6.50 | 10.10 | 271.2 | 61.85 |
| Interlock | 8,837 | 4,090 | 6.75 | 6.00 | 8.00 | 243.3 | 61.35 |
| Pique | 2,419 | 876 | 6.91 | 6.50 | 9.00 | 249.9 | 49.17 |
| Other | 8,937 | 2,136 | 6.84 | 6.38 | 13.24 | 213.4 | 53.45 |

### 8.6 Chemistry by class

| Class | Products | Tonnes | % mass | M Tk | % spend |
|---|---|---|---|---|---|
| Salt (electrolyte) | 2 | 34,116 | 54.1% | 584 | 7.5% |
| Alkali | 3 | 11,963 | 19.0% | 598 | 7.7% |
| Auxiliary | 219 | 6,446 | 10.2% | 1,868 | 24.2% |
| Dyestuff | 192 | 3,581 | 5.7% | 3,343 | 43.2% |
| Bleach / redox | 4 | 3,420 | 5.4% | 445 | 5.8% |
| Acid | 11 | 2,112 | 3.3% | 255 | 3.3% |
| Softener / finish | 53 | 735 | 1.2% | 382 | 4.9% |
| Enzyme | 11 | 721 | 1.1% | 260 | 3.4% |

Mass and spend are inverted. Salt and alkali are 73 percent of the tonnage and 15 percent of
the money; dyestuff is 5.7 percent of the tonnage and 43 percent of the money. These are two
separate business cases from one dataset: a water and effluent recovery loop is justified on
salt load and discharge compliance, a dosing correction loop is justified on dyestuff cost.
Presenting them as one blended saving weakens both.

Single largest product by mass: sodium sulphate (Soudiam Sulphate, Viscose grade),
approximately 34,000 t, more than half of all chemical mass dosed in the plant.

### 8.7 Largest addressable water groups

| Fabric | Shade | GSM | Batches | L/kg now | P25 | P90 | Excess ML |
|---|---|---|---|---|---|---|---|
| Composite | Light/Medium | Heavy 250+ | 34,682 | 6.85 | 6.50 | 7.50 | 10.49 |
| Rib Fabric | Light/Medium | Heavy 250+ | 25,540 | 6.79 | 6.10 | 8.87 | 9.60 |
| Lycra S/J | Light/Medium | Medium 150-249 | 23,194 | 6.68 | 6.00 | 8.40 | 7.66 |
| Single Jersey | Light/Medium | Medium 150-249 | 23,694 | 6.70 | 6.00 | 11.72 | 6.01 |
| Rib Fabric | Light/Medium | Medium 150-249 | 17,154 | 6.73 | 6.00 | 9.76 | 5.48 |
| Composite | Light/Medium | Medium 150-249 | 20,861 | 6.76 | 6.50 | 7.27 | 4.27 |
| Single Jersey | Light/Medium | Light <150 | 9,831 | 6.67 | 6.00 | 10.20 | 2.92 |
| Composite | White/Bleach | Heavy 250+ | 6,629 | 6.66 | 6.00 | 7.00 | 2.45 |

The opportunity is concentrated in high-volume light and medium shades, not in the dark
shades that intuition suggests. Dark batches are already run tightly. The saving is in the
routine work.

---

## 9. Verification performed

Every headline number was re-derived through a code path independent of the one that
produced it.

**9.1 Canonical line count, independent SQL.** A window-function query written separately
from the analysis code:

```sql
WITH ranked AS (
  SELECT Batch_No b, Source_File sf, COUNT(*) n,
         ROW_NUMBER() OVER (PARTITION BY Batch_No ORDER BY COUNT(*) DESC, Source_File ASC) rn
  FROM lines GROUP BY 1,2)
SELECT COUNT(*), SUM(CAST(l.Req_Qty_kg AS REAL)), SUM(CAST(l.Amount_Tk AS REAL))
FROM lines l JOIN ranked r ON l.Batch_No=r.b AND l.Source_File=r.sf AND r.rn=1;
```

Returned 4,831,565 lines and 63,095 t. The analysis reports 4,831,565 lines. Exact match on
the line count. The mass differs by 838 t (1.3%), which is the chemistry zeroed on the 167
batches exceeding 3,000 g/kg plus batches failing other screens. The direction and magnitude
are as expected.

**9.2 Totals re-derived from the exported CSV.** Reading `DEEP_ROOT_Batch_Enriched.csv` with
a separate script and filtering on `QC_Usable` reproduced 123,258 t fabric, 832.46 ML water
and 6.754 L/kg, matching the report.

**9.3 Internal arithmetic consistency.** The per-year table sums to the headline: fabric
tonnage 123,259 and water 832.47 ML, giving 6.754 L/kg. Consistent to rounding.

**9.4 Batch conservation.** The enriched export contains exactly 289,403 data rows. No batch
is lost or duplicated anywhere in the pipeline. Header count 362,451, unique batches 289,403,
master rows 289,403, exported rows 289,403.

**9.5 Report structure.** Zero unreplaced template tokens remain in the HTML. 8 `<canvas>`
elements against 8 chart constructors. Every chart data series is non-empty. The JSON payload
parses.

**9.6 Benchmark sanity.** The minimum P25 across all 49 qualifying peer groups is 5.7 L/kg.
Before the placeholder screen of section 4.3 was added, one group had a P25 of 1.0 L/kg,
which is what exposed the problem. That check is the reason the finding was caught.

---

## 10. What must not be claimed from this data

1. **Nothing about machines.** `MC_No` is empty in every row. No utilisation, no capacity fit,
   no per-machine benchmarking, and it must not be used as a model feature.
2. **No water baseline for Unit C.** 73.6 percent of that unit has no recorded water. Do not
   present an Unit C water figure, and do not include Unit C in a water-saving commitment without
   first fixing the source field.
3. **No cost trend across 2023 or 2026.** See section 4.6. Use chemical mass per kilogram.
4. **The 8.41 percent is a ceiling, not a forecast.** It assumes every batch can reach the
   P25 of its peer group. Some of the residual spread is real process variation the four
   categories do not capture.
5. **Water per kilogram is close to arithmetic on many batches.** Where recorded water equals
   ratio times weight, predicting water from ratio and weight is not learning, it is
   restating the input. The genuine modelling target is the deviation from the peer-group
   benchmark, which is what the savings ledger exports.
6. **The chemical classification is a heuristic.** Audit it in the chemical master before
   relying on class-level conclusions, particularly the Auxiliary residual.
7. **Costs are batch-card amounts, not a market price series.** They inherit whatever pricing
   the source system held at the time.

### Implications for the modelling work

- Train per dyeing unit, or weight and validate per unit. Unit A, Unit D and Unit C are different
  chemistries in very different volumes, and a pooled model will fit Unit A and under-serve the
  others.
- Do not use `Liquor_Ratio_1_to_X` raw. On the placeholder block it will teach a model that
  a large group of batches ran at 1:1. Either filter on `QC_Usable` or add an explicit
  "ratio recorded" indicator.
- Filter on `QC_Usable = 1` for any water-related target.
- Unit D carries the widest spread (P90 12.50 against P25 6.50) and is the highest-value target
  for a first control intervention.

---

## 11. How to re-run

```
cd "E:\Downloads\01_Projects_and_Research\AI-driven closed-loop dyeing system for Bangladesh textiles\2026-09-03_Categorization_Insights"
python 29_deep_root_analysis.py
```

No third-party packages are required. Standard library only: `csv`, `sqlite3`, `re`, `json`,
`array`, `collections`, `shutil`, `tempfile`. No pandas, no numpy. The script targets a plain
interpreter and avoids f-strings for portability.

`BASE_DIR` is hard-coded at the top with a fallback that resolves relative to the script
location, so the folder can be moved without editing.

**Runtime.** First run roughly 4 to 5 minutes, dominated by copying the database to local
scratch and the SQL aggregation. Subsequent runs about 40 seconds, restoring the chemistry
join from cache. The console prints which path it took.

**Cache.** `~/.deep_root_cache/` holds `work.db` (the local database copy),
`chem.bin` and `chem_meta.json`. It invalidates automatically when the database or the master
csv changes size or modification time. Delete the folder to force a full rebuild. Override the
location with the `DEEP_ROOT_CACHE` environment variable.

**Tuning.** The screening windows are constants at the top of the file under the "screening"
comment: `MIN_KG`, `MAX_KG`, `MIN_WI`, `MAX_WI`, `MIN_LR`, `MAX_LR`, `MAX_CHEM_GPKG`,
`MIN_YEAR_N`, and `MIN_CELL_N` for the savings peer-group minimum. Changing any of them
changes the integrity panel automatically, so the report always documents the thresholds
actually used.

---

## 12. Change log against version 1

| # | Change | Reason |
|---|---|---|
| 1 | Token replacement instead of `str.format()` for the HTML | Version 1 crashed on CSS braces (3.1) |
| 2 | Chart data embedded as JSON and parsed before the constructors | Version 1 referenced undefined variables (3.2) |
| 3 | Header source switched to the MASTER csv | Arbitrary row per batch from `GROUP BY` (3.4) |
| 4 | Machine table replaced with a nullity audit | The column is 100% empty (3.3, 4.1) |
| 5 | Explicit liquor ratio parser | The old cleaner turned `1:8` into 18.0 (3.5) |
| 6 | Mass-weighted intensity plus percentiles | Mean of ratios does not reconcile to a water bill (3.6) |
| 7 | Recipe lines joined with canonical source selection | 968,295 duplicate rows would inflate every total (4.2) |
| 8 | Physical plausibility screening with a published integrity panel | Nothing dropped silently (5.3) |
| 9 | Placeholder-water detection | 25,072 batches have no real water reading (4.3) |
| 10 | Sparse and partial year handling | 177 stray-dated batches distorted the trend (4.7) |
| 11 | Peer-group savings ledger | Quantifies the opportunity against the plant's own P25 (5.6) |
| 12 | Automatic cost-step warning | Guards against quoting a price revaluation as a saving (4.6) |
| 13 | Three CSV exports added | Makes the analysis reusable rather than a static page |
| 14 | Columnar storage, SQL aggregation, resumable cache | 895 MB RAM and a 180 second execution ceiling (section 6) |

---

## 13. Open questions and recommended next steps

1. **Recover `MC_No` from the source HTML.** It is the single largest missing feature. It
   plausibly explains part of the residual variance the savings estimate currently attributes
   to addressable waste, and without it no machine-scheduling work is possible.
2. **Fix or scope out Unit C water capture.** Decide this before the baseline is fixed, not
   after. As it stands the polyester unit cannot be included in a water-reduction claim.
3. **Reconcile the 2023 and 2026 cost steps** against procurement records, and if they are
   revaluations, hold a constant-price series for trend reporting.
4. **Audit the Auxiliary class** (219 products, 24.2% of spend). It is the residual bucket and
   the most likely place for a misclassified dyestuff or specialty product.
5. **Investigate the 27,650 ratio-versus-water mismatches.** If the ratio field is the more
   reliable of the two on those batches, the water figures for them need revisiting.
6. **Ask why water intensity barely varies with shade depth** (6.64 to 6.78 across
   White/Bleach to Dark). If machines are filled to a standard ratio regardless of process
   requirement, that is a direct and immediate control opportunity, and it is probably the
   most actionable single observation in this analysis.

---

## 14. File inventory produced by this analysis

| File | Purpose |
|---|---|
| `29_deep_root_analysis.py` | The analysis engine, version 2 |
| `29_deep_root_analysis_ORIGINAL_BACKUP.py` | Version 1, preserved unmodified for reference |
| `DEEP_ROOT_Findings_2021_2026.html` | The report |
| `DEEP_ROOT_Batch_Enriched.csv` | 289,403 batches, headers joined to chemistry, with QC flags |
| `DEEP_ROOT_Chemical_Master.csv` | 495 products with class, mass, cost, penetration |
| `DEEP_ROOT_Savings_Opportunity.csv` | 49 peer groups with benchmarks and addressable excess |
| `README_DEEP_ROOT_ANALYSIS.md` | This file |

Figures throughout derive from factory batch-card extractions and inherit any error present
at source. Where a number could not be verified from the data it is labelled as requiring
confirmation rather than stated as fact.

Note on distribution: Section 8 of the project Engagement Letter requires written sign-off
before project-specific content, partner names or internal figures are published externally.
This file and the report contain internal figures and were kept local for that reason.


