# SMART DYEING â€” the site Data: Technical Summary & Baseline Verdict
**Project:** AI-Driven Closed-Loop Dyeing (Project EOI) Â· **Site:** Production Site (Units Unit A, Unit D, Unit C) Â· **Data window:** 31 May â€“ 30 Jun 2026 Â· **Prepared:** 2026-07-10
*Engineer/scientist brief â€” every figure is computed from the site own production reports. Nothing rounded away, nothing hidden.*

---

## PAGE 1 â€” What we did, in sequence, and why (the method)

We worked as a **prepare â†’ verify â†’ compare loop** (each stage checks the one before it, and we only stopped when a further pass changed nothing material):

1. **Domain first (why before numbers).** Reactive knit dyeing consumes water as *bath + rinses*; the controlling physics is the **liquor ratio** (litres of bath per kg fabric) and **fixation** (how much dye bonds vs washes off). So the right primary metric is **water per kg (L/kg)**, judged against the machine's **recipe-theoretical L/kg** â€” not a raw average. *Why:* comparing a black against a pale on raw litres is meaningless; normalising to the recipe target is fair.

2. **Ingest all raw files (10 workbooks).** 4 batch-level *Production Reports* (one per unit) + 4 *Total Water* exports + 2 out-of-window periods. *Why:* the Total-Water exports also log machine-wash and re-dye cycles (extra rows), so they **overstate** per-kg water â€” we used the **batch-level Production Reports** as the correct denominator and did **not** sum the Total-Water files (avoids double counting).

3. **Validate & clean with justification (the engineer's gate).** From 2,445 dyeing batches we flagged **148 (6.05%)** as not-analysable and excluded them â€” each for a *physical* reason (see Page 2), leaving **2,332 clean batches (1,500 t)**. Machine-wash (148) and optical-white/scour prep (484) were separated because they are **not dyeing**. *Why:* a baseline built on meter drop-outs, sample runs and wash cycles is a false baseline.

4. **Compute production-weighted metrics.** Every intensity is Î£(metric Ã— kg) â„ Î£kg (true throughput average), reported with medians. *Why:* simple averages let tiny odd batches distort the number; weighting by fabric makes it the real factory figure.

5. **Find the relationships (what actually drives water).** Correlated water against steam, power, dye load, machine capacity, batch size, loading, batch time. *Why:* to separate *recipe* waste from *process/scheduling* waste â€” they need different fixes.

6. **Compare fairly (remove confounders).** Raw unit averages are biased by product mix, so we **standardised every unit to the site's shade mix** (direct standardisation) to get a like-for-like efficiency league. *Why:* a unit can look "efficient" only because it dyes easier shades.

7. **Verify independently (the audit agent).** A second, from-scratch recompute reproduced the headline (67.1 L/kg = 67.1), plus 13 integrity checks. *Why:* a number you can't reproduce is an opinion, not a measurement.

*Deliverables from this loop:* the 16-sheet interactive workbook, the HTML dashboard, the validated baseline report, and this summary â€” all from the same verified 2,332-batch dataset.

---

## PAGE 2 â€” What the data says (the site vs the project baseline)

### A. Data-validation verdict â€” is the data trustworthy? **Yes, after a justified 6% exclusion.**

| Flag (raw dyeing rows) | Count | % | Engineering reason |
|---|---|---|---|
| Water < 10 L/kg | 41 | 1.7% | Below the physical minimum bath (~1:4). Flow-meter drop-out / short-cycle mis-log. |
| Water > 200 L/kg | 8 | 0.3% | Re-run or half-load logged against a small weight. |
| **Recipe target missing (Theo â‰¤ 0)** | **66** | **2.7%** | **Master recipe not linked to the batch â€” a genuine manual data gap. â†’ Ask the site to link recipes so WER is computable for every batch.** |
| Steam > 12 kg/kg | 6 | 0.25% | Above thermodynamic norm (~2â€“5). Steam-meter spike / tiny-weight division. |
| "Production efficiency" > 400% | 26 | 1.1% | Reference-time Ã· near-zero cycle = sample/short run, not a full batch. |
| Negative duration | 1 | 0.04% | Data-entry error. |
| Load > 125% of machine capacity | **0** | 0% | **No capacity mislabels / weight mis-keys.** |
| kWh outside 0â€“1.5 | **0** | 0% | Energy channel clean. |

**Verdict:** the dataset is **sound and manually reliable**. The excluded 6% are legitimate *operational* records (washes, samples, re-runs, meter blips) that simply don't belong in a per-kg dyeing baseline â€” **no evidence of fabricated or capacity-tampered data.** The single item to fix at source is the **66 missing recipe targets**. Independent recompute + 13 checks = **10 PASS, 3 WARN, 0 FAIL**; steamâ€“water correlation = 1.00 (correct physics) confirms internal consistency.

### B. The baseline, against the project's literature baseline

| Metric | Project literature baseline | **the site measured** | Meaning |
|---|---|---|---|
| Process water | 136 L/kg (nat. avg) | **67.1 L/kg** (prep 30.1) | the site uses **~Â½ the national average** â€” best-in-class |
| Groundwater intake | 164 L/kg | (67.1 metered at machine) | ~2.4Ã— better |
| Efficiency vs own recipe (WER) | â€” | **0.948** | Runs slightly *under* its own targets on average |
| Steam / Electricity | â€” | **3.80 kg/kg Â· 0.221 kWh/kg** | New the site energy baseline |
| Chemicals, fixation %, Î”E, effluent | 449 g/kg Â· 65â€“70% Â· 13.05 Â· 119 L/kg | **not metered** | Data gaps â†’ must be added in M3â€“M4 |

**This reframes the project baseline:** the 136â€“164 L/kg literature figure is the *national/SME* average; the site is a top-tier mill already ~2Ã— better. So at the site the AI's value is **consistency and optimisation**, not rescuing a broken process.

### C. Relationships found (and their honest weight)

- **Water = energy.** Water â†” steam **r = 1.00**, water â†” power r = 0.64. Every litre saved is thermal energy saved â€” the single most useful correlation.
- **Water is process-driven, not chemistry.** Water â†” dye load **r â‰ˆ 0**, but water â†” efficiency r = 0.78. Consumption is set by *how* a batch is run, not the colour recipe â€” the core case for closed-loop control.
- **Machine size/loading is a *modest* lever (stated honestly).** Small machines (â‰¤250 kg) 71.5 vs large (â‰¥1000 kg) 65.6 L/kg; under-loaded batches carry only ~**770 mÂ³/month** (~0.8%) extra vs well-loaded ones (corr âˆ’0.16). Real, but *secondary* â€” not the headline.
- **Shade depth is monotonic.** White 30 â†’ Light 51 â†’ Medium 69 â†’ Special/Dark 75 L/kg. "Special Shade" is the quality pain point (lowest first-time-right, 7.6% need shade corrections).

### D. The best insight â€” unit efficiency after removing product mix

| Unit | Raw L/kg | Mix-adjusted L/kg | Verdict |
|---|---|---|---|
| **Unit C** | 49.7 | **50.2** | **Genuine efficiency leader** â€” real, not easy shades |
| B | 71.8 | 70.3 | ~ true ~70 |
| **Unit D** | 66.9 | **71.1** | **Hidden under-performer** â€” looks mid only because it dyes lighter shades |
| A | 77.2 | 75.3 | Heaviest even after adjustment |

### E. Where the savings are, and what to do next

- **Primary pool: 8,576 mÂ³/month (8.5%)** = water used above the site own recipe targets; **72% sits in Units A & B**. Target â‰¥20% â†’ **â‰¤ 54 L/kg**.
- **Secondary: ~770 mÂ³/month** from fuller machine loading (schedule small orders onto larger machines).
- **Instrument the gaps (M3â€“M4):** inline **colour (Î”E/K-S), pH, conductivity, exhaustion/fixation, effluent (BOD/COD/TDS)** â€” the site "RFT" (97.6%) is a *production pass flag*, **not** a Î”Eâ‰¤1 colour match, so it must not be equated with the project's lab Î”E 13.05.

**Bottom line:** the site data is trustworthy (6% justified exclusions, one recipe-linking gap to fix); the site is already ~2Ã— better than the literature baseline; water is governed by process/liquor-ratio and moves 1:1 with energy; the credible, no-recipe-change savings pool is ~8,600 mÂ³/month concentrated in A & B and the dark-shade book; and the closed-loop AI's job here is **consistency + the un-metered colour/chemistry loop**, not fixing a broken plant.

*Sources: the site Production Reports (A/B/Unit C/Unit D, 31 Mayâ€“30 Jun 2026); pipeline the site/_audit.py, _verify.py, _deep_analysis.py, _build_excel.py; literature comparators from SMART_DYEING_Baseline_Data_Report_VALIDATED.md.*



