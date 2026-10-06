---
title: AI Closed-Loop Dyeing  -  Home (Map of Content)
project: AI-Driven Closed-Loop Reactive Dyeing Control
programme: an applied industrial applied research programme
partner: Partner Industrial Facility
updated: 2026-06-23
tags: [ai-dyeing, MOC, home]
---

# 🧵 AI Closed-Loop Dyeing  -  Vault Home

> [!abstract] What this vault is
> The working knowledge base for the **AI-Driven Closed-Loop Process Control System for Knit Fabric Dyeing**. Start here. Every deliverable is linked below, grouped by theme, with a status tag so you always know what is **verified**, what is **projected** (not yet computed), and what is **pending**.

> [!tip] Status legend
> ✅ **verified**  -  traced to executed output / metered data ·  🟡 **projected**  -  intended, not yet computed ·  🔍 **draft / interim** ·  ♻️ **superseded** (use the newer note)

---

## 🚦 Project status at a glance

> [!success] Verified (safe to cite)
> - Energy baseline from **real metered production facility data**: 1.849 kWh/kg, 9.64 kg steam/kg (single-boiler), 77% thermal  -  [AI_DYEING_Energy_Baseline_Analysis_production facility](AI_DYEING_Energy_Baseline_Analysis_production facility.md)
> - ML pipeline executes clean (10/10 cells): KS R²=0.9833, AUC=0.9133, ΔE R²=0.8655  -  [AI_DYEING_ML_Pipeline_QA_Verification_Report](AI_DYEING_ML_Pipeline_QA_Verification_Report.md)
> - Module 1 CatBoost spectral→Lab R²=0.9972  -  [AI_DYEING_M1_M2_Compliance_VERIFIED](AI_DYEING_M1_M2_Compliance_VERIFIED.md)

> [!warning] Projected  -  do NOT present as achieved yet
> - The "Phase 5b scientific validation" stats (DeLong, Brier, ECE, bootstrap CI, Youden θ) are **not computed**  -  see [AI_DYEING_TodayFiles_Accuracy_Audit](AI_DYEING_TodayFiles_Accuracy_Audit.md)
> - The "74.7% beats Jasper" benchmark is **withdrawn / invalid**  -  see [AI_DYEING_Canonical_Figures_and_Corrections](AI_DYEING_Canonical_Figures_and_Corrections.md)

> [!danger] Pending (needs a real action)
> - One networked pipeline run to convert projected → verified
> - Per-machine, per-batch **sub-metering** (the data gap)  -  [AI_DYEING_Energy_Baseline_Analysis_production facility §9](AI_DYEING_Energy_Baseline_Analysis_production facility.md)
> - Confirm Sclavos controller interface  -  [AI_DYEING_PLC_Sclavos_Interface](AI_DYEING_PLC_Sclavos_Interface.md)

---

## 📁 Deliverables Index

### Phase 1  -  Baseline & Validation

| Document | Status | Description |
|---|---|---|
| [AI_DYEING_Technical_Summary.md](AI_DYEING_Technical_Summary.md) | ✅ Verified | Site baseline analysis and key metrics |
| [AI_DYEING_Inception_Report.md](AI_DYEING_Inception_Report.md) | 🔍 Draft | Project inception and design rationale |
| [PLC_AI_ClosedLoop_Review_FINAL.md](PLC_AI_ClosedLoop_Review_FINAL.md) | ✅ Verified | 95K-word closed-loop control technical review |

### Phase 2  -  ML Pipeline

| Document | Status | Description |
|---|---|---|
| ML Pipeline QA Verification | ✅ Verified | 10/10 cells clean, KS R²=0.9833 |
| CatBoost spectral→Lab mapping | ✅ Verified | R²=0.9972 on synthetic data |
| Phase 5b statistical validation | 🟡 Projected | DeLong, Brier, ECE  -  not yet computed |

### Phase 3  -  Deployment

| Action | Status | Description |
|---|---|---|
| Shadow-mode AI (read-only) | 🟡 Projected | Unit A pilot  -  4 weeks shadow mode |
| A/B prospective trial | 🟡 Projected | Requires Phase 2 completion |
| Closed-loop write-back | 🟡 Projected | Requires vendor interface confirmation |

---

## 📚 References & Documentation

- [AI_DYEING_Technical_Summary.md](AI_DYEING_Technical_Summary.md)  -  Site baseline analysis and key metrics
- [PLC_AI_ClosedLoop_Review_FINAL.md](PLC_AI_ClosedLoop_Review_FINAL.md)  -  95K-word closed-loop control technical review
- [AI_DYEING_Inception_Report.md](AI_DYEING_Inception_Report.md)  -  Project inception and design rationale
- [Deep_Analysis_Findings.md](Deep_Analysis_Findings.md)  -  Data integrity verification findings
