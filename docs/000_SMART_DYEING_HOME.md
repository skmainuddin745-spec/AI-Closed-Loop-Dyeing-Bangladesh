---
title: SMART DYEING — Home (Map of Content)
project: AI-Driven Closed-Loop Reactive Dyeing Control
programme: Industrial Research Consortium/Research Programme Round 1 · Project EOI
partner: South East Textiles (Pvt.) Ltd.
updated: 2026-06-23
tags: [smart-dyeing, MOC, home]
---

# 🧵 SMART DYEING — Vault Home

> [!abstract] What this vault is
> The working knowledge base for the **AI-Driven Closed-Loop Process Control System for Knit Fabric Dyeing**. Start here. Every deliverable is linked below, grouped by theme, with a status tag so you always know what is **verified**, what is **projected** (not yet computed), and what is **pending**.

> [!tip] Status legend
> ✅ **verified** — traced to executed output / metered data ·  🟡 **projected** — intended, not yet computed ·  🔍 **draft / interim** ·  ♻️ **superseded** (use the newer note)

---

## 🚦 Project status at a glance

> [!success] Verified (safe to cite)
> - Energy baseline from **real metered SETL data**: 1.849 kWh/kg, 9.64 kg steam/kg (single-boiler), 77% thermal — [SMART_DYEING_Energy_Baseline_Analysis_SETL](SMART_DYEING_Energy_Baseline_Analysis_SETL.md)
> - ML pipeline executes clean (10/10 cells): KS R²=0.9833, AUC=0.9133, ΔE R²=0.8655 — [SMART_DYEING_ML_Pipeline_QA_Verification_Report](SMART_DYEING_ML_Pipeline_QA_Verification_Report.md)
> - Module 1 CatBoost spectral→Lab R²=0.9972 — [SMART_DYEING_M1_M2_Compliance_VERIFIED](SMART_DYEING_M1_M2_Compliance_VERIFIED.md)

> [!warning] Projected — do NOT present as achieved yet
> - The "Phase 5b scientific validation" stats (DeLong, Brier, ECE, bootstrap CI, Youden θ) are **not computed** — see [SMART_DYEING_TodayFiles_Accuracy_Audit](SMART_DYEING_TodayFiles_Accuracy_Audit.md)
> - The "74.7% beats Jasper" benchmark is **withdrawn / invalid** — see [SMART_DYEING_Canonical_Figures_and_Corrections](SMART_DYEING_Canonical_Figures_and_Corrections.md)

> [!danger] Pending (needs a real action)
> - One networked pipeline run to convert projected → verified
> - Per-machine, per-batch **sub-metering** (the data gap) — [SMART_DYEING_Energy_Baseline_Analysis_SETL §9](SMART_DYEING_Energy_Baseline_Analysis_SETL.md)
> - Confirm Sclavos controller interface — [SMART_DYEING_PLC_Sclavos_Interface](SMART_DYEING_PLC_Sclavos_Interface.md)

---

## 📁 Deliverables Index

### Phase 1 — Baseline & Validation

| Document | Status | Description |
|---|---|---|
| [SMART_DYEING_Technical_Summary.md](SMART_DYEING_Technical_Summary.md) | ✅ Verified | Site baseline analysis and key metrics |
| [SMART_DYEING_Inception_Report.md](SMART_DYEING_Inception_Report.md) | 🔍 Draft | Project inception and design rationale |
| [PLC_AI_ClosedLoop_Review_FINAL.md](PLC_AI_ClosedLoop_Review_FINAL.md) | ✅ Verified | 95K-word closed-loop control technical review |

### Phase 2 — ML Pipeline

| Document | Status | Description |
|---|---|---|
| ML Pipeline QA Verification | ✅ Verified | 10/10 cells clean, KS R²=0.9833 |
| CatBoost spectral→Lab mapping | ✅ Verified | R²=0.9972 on synthetic data |
| Phase 5b statistical validation | 🟡 Projected | DeLong, Brier, ECE — not yet computed |

### Phase 3 — Deployment

| Action | Status | Description |
|---|---|---|
| Shadow-mode AI (read-only) | 🟡 Projected | Unit A pilot — 4 weeks shadow mode |
| A/B prospective trial | 🟡 Projected | Requires Phase 2 completion |
| Closed-loop write-back | 🟡 Projected | Requires vendor interface confirmation |

---

## 📚 References & Documentation

- [SMART_DYEING_Technical_Summary.md](SMART_DYEING_Technical_Summary.md) — Site baseline analysis and key metrics
- [PLC_AI_ClosedLoop_Review_FINAL.md](PLC_AI_ClosedLoop_Review_FINAL.md) — 95K-word closed-loop control technical review
- [SMART_DYEING_Inception_Report.md](SMART_DYEING_Inception_Report.md) — Project inception and design rationale
- [Deep_Analysis_Findings.md](Deep_Analysis_Findings.md) — Data integrity verification findings
