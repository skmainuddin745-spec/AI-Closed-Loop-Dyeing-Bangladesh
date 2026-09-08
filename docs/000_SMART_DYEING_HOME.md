---
title: SMART DYEING â€” Home (Map of Content)
project: AI-Driven Closed-Loop Reactive Dyeing Control
programme: Industrial Research Consortium/Research Programme Round 1 Â· Project EOI
partner: South East Textiles (Pvt.) Ltd.
updated: 2026-06-23
tags: [smart-dyeing, MOC, home]
---

# ðŸ§µ SMART DYEING â€” Vault Home

> [!abstract] What this vault is
> The working knowledge base for the **AI-Driven Closed-Loop Process Control System for Knit Fabric Dyeing**. Start here. Every deliverable is linked below, grouped by theme, with a status tag so you always know what is **verified**, what is **projected** (not yet computed), and what is **pending**.

> [!tip] Status legend
> âœ… **verified** â€” traced to executed output / metered data Â·  ðŸŸ¡ **projected** â€” intended, not yet computed Â·  ðŸ“ **draft / interim** Â·  â™»ï¸ **superseded** (use the newer note)

---

## ðŸš¦ Project status at a glance

> [!success] Verified (safe to cite)
> - Energy baseline from **real metered SETL data**: 1.849 kWh/kg, 9.64 kg steam/kg (single-boiler), 77% thermal â€” [[SMART_DYEING_Energy_Baseline_Analysis_SETL]]
> - ML pipeline executes clean (10/10 cells): KS RÂ²=0.9833, AUC=0.9133, Î”E RÂ²=0.8655 â€” [[SMART_DYEING_ML_Pipeline_QA_Verification_Report]]
> - Module 1 CatBoost spectralâ†’Lab RÂ²=0.9972 â€” [[SMART_DYEING_M1_M2_Compliance_VERIFIED]]

> [!warning] Projected â€” do NOT present as achieved yet
> - The "Phase 5b scientific validation" stats (DeLong, Brier, ECE, bootstrap CI, Youden Î¸) are **not computed** â€” see [[SMART_DYEING_TodayFiles_Accuracy_Audit]]
> - The "74.7% beats Jasper" benchmark is **withdrawn / invalid** â€” see [[SMART_DYEING_Canonical_Figures_and_Corrections]]

> [!danger] Pending (needs a real action)
> - One networked pipeline run to convert projected â†’ verified
> - Per-machine, per-batch **sub-metering** (the data gap) â€” [[SMART_DYEING_Energy_Baseline_Analysis_SETL]] Â§9
> - Confirm Sclavos controller interface â€” [[SMART_DYEING_PLC_Sensor_Integration_0to1]] Phase 0

---

## ðŸ Milestone & compliance (M1â€“M2)

- âœ… [[SMART_DYEING_M1_M2_Compliance_VERIFIED]] â€” **use this one** Â· defensible, verified-only #verified
- â™»ï¸ [[M1_M2_Deliverable_Compliance_Report_Exhaustive]] â€” legacy; corrected in place #superseded
- ðŸ“ [[SMART_DYEING_M1_M2_Tickmark_Checklist]] â€” QA tickmark audit
- âœ… [[SMART_DYEING_Canonical_Figures_and_Corrections]] â€” single source of truth for figures #verified

## ðŸ¤– ML pipeline & QA

- âœ… [[SMART_DYEING_ML_Pipeline_QA_Verification_Report]] â€” end-to-end QA #verified
- âœ… [[SMART_DYEING_TodayFiles_Accuracy_Audit]] â€” projected-vs-measured audit #verified
- ðŸ“ [[SMART_DYEING_FIXES_APPLIED]] â€” bug-fix log
- ðŸ“ [[SMART_DYEING_PROJECT_COMPLETION_HANDOFF]] â€” handoff capstone
- ðŸ“ [[context]] â€” running context & next steps

## ðŸ“Š Baseline & energy (real data)

- âœ… [[SMART_DYEING_Energy_Baseline_Analysis_SETL]] â€” **real metered energy** + fixed/variable decomposition #verified
- âœ… [[SMART_DYEING_Baseline_Data_Report_VALIDATED]] â€” literature-validated baseline #verified
- â™»ï¸ [[SMART_DYEING_Baseline_Data_Report]] â€” earlier industry-level baseline #superseded

## ðŸ”Œ Technical & deployment

- âœ… [[SMART_DYEING_PLC_Sensor_Integration_0to1]] â€” SETEX/Sedo/Sclavos 0â†’1 runbook #verified
- ðŸ“ [[SMART_DYEING_Technical_Framework]] â€” architecture (corrected)
- ðŸ“ [[SMART_DYEING_Procurement_BoQ]] â€” sensor/hardware BoQ
- ðŸ“ [[SMART_DYEING_Inception_Report]] â€” inception

## ðŸ“š References & citations

- âœ… [[SMART_DYEING_Citation_Verification_Report]] â€” Jasper/Noh verification #verified
- âœ… [[SMART_DYEING_Reference_Acquisition_Register]] â€” DOIs, OA status, retrieval #verified

---

## ðŸ§­ Suggested reading order

1. This home note â†’ 2. [[SMART_DYEING_M1_M2_Compliance_VERIFIED]] â†’ 3. [[SMART_DYEING_Energy_Baseline_Analysis_SETL]] â†’ 4. [[SMART_DYEING_PLC_Sensor_Integration_0to1]] â†’ 5. [[SMART_DYEING_Canonical_Figures_and_Corrections]] (what to fix) â†’ 6. [[SMART_DYEING_PROJECT_COMPLETION_HANDOFF]] (what's left).

## ðŸ”– Tag index

`#verified` Â· `#projected` Â· `#superseded` Â· `#smart-dyeing`

> [!note] How to use in Obsidian
> Open **Graph view** to see how these notes connect, the **Backlinks** pane on any note to see what references it, and the **Tag pane** to filter by status. This note is the hub â€” every key deliverable links back here.

