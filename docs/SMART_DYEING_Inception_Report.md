---
project: SMART DYEING
status: draft
type: technical
milestone: M1-M2
tags: [smart-dyeing, technical, draft]
home: "[000_SMART_DYEING_HOME](../docs/000_SMART_DYEING_HOME.md)"
---

# SMART DYEING: Inception Report

**Project Title:** An AI-Driven Closed-Loop Process Control System for Optimizing Resource Consumption in Knit Fabric Dyeing  
**Project Lead:** Research Supervisor (Department of Textile Engineering)  
**Research Assistant:** SK Mainuddin  
**Grant Program:** Bangladesh Industry Research Development and Innovation (Industrial Research Consortium) / Research Programme

## 1. Executive Summary

This inception report outlines the foundation for the SMART DYEING project. Moving from traditional, heuristic-based batch dyeing to a sophisticated, closed-loop AI-driven system, the project addresses critical resource inefficiencies in Bangladesh's textile wet processing sector. It aligns strictly with international standards, having validated its theoretical basis through a PRISMA 2020 systematic review.

## 2. Problem Statement (ECR 2023 Alignment)

The global textile industry, specifically knit fabric dyeing in Bangladesh, faces existential sustainability challenges:

- **Water Intensity:** Conventional dyeing consumes ~80–150 litres of water per kg of fabric.
- **Open-Loop Failures:** Manual monitoring relies on subjective human judgment, leading to inconsistent shade matching, under-dyeing, and over-dosing.
- **Environmental Impact:** High residual dye and chemical waste severely load Effluent Treatment Plants (ETPs), degrading local water systems.
- **Regulatory Compliance:** Current heuristic practices struggle to meet the strict wastewater and environmental mandates established under the **Bangladesh ECR 2023 Regulatory Framework**.

## 3. Aims and Objectives

The core objective is to achieve a "Lights-Out", autonomous dyeing framework. Specifically:

1. **IoT Integration:** Develop a real-time sensor-integrated data acquisition layer (pH, conductivity, temperature, spectrophotometry) linked to production PLCs via OPC UA / Modbus RTU.
2. **AI Prediction Models:** Build and validate ML models (XGBoost, LightGBM, CatBoost) capable of predicting final colour error (ΔE₂₀₀₀), K/S strength, and right-first-time (RFT) probability from inline sensor streams.
3. **Closed-Loop Control:** Design a phased validation staircase — shadow mode → prospective A/B trial → constrained closed-loop write-back — to safely transition from advisory to autonomous control.
4. **Verified Baseline:** Establish a rigorous, independently audited production baseline (water, steam, electrical energy, colour error) from real metered data at the partner facility (South East Textiles Pvt. Ltd., Tangail, Bangladesh).

## 4. Background & Literature (PRISMA 2020 Review)

The project's theoretical basis was validated through a PRISMA 2020 systematic review of 60+ peer-reviewed sources (2012–2025). Key findings:

- Dyebath pH accounts for approximately **45% of total fixation variance** (Zhang et al., 2022, Taguchi L27) — yet is systematically absent from standard PLC telemetry in developing-country dyehouses.
- OPC UA (IEC 62541) enables full read/write AI integration on SETEX E390/C390 and Sedo Treepoint Sedomat platforms. Sclavos AquaChron requires vendor gateway — a critical, under-reported gap.
- Published ML models achieve ΔE prediction with R² up to 0.88 (Hossain et al., 2016) and LSSVR+Taguchi reaches Pearson R ≈ 0.98 on E/F/T/K-S (Pervez et al., 2023).
- Inline spectrophotometry reduced dyeing time by 20.1% and wash time by 16.6% in a documented factory trial (Terkesli et al., 2019).

## 5. Partner Facility — Verified Baseline

Production partner: **South East Textiles (Pvt.) Ltd., Tangail, Bangladesh**  
Data window: January–April 2026 (single-boiler baseline period)

| Metric | Verified Value | Source |
|--------|---------------|--------|
| Water intensity | 67.1 L/kg (SD 26.4 L/kg) | 2,332 clean batches, Jun 2026 |
| Steam intensity | 9.64 kg steam/kg fabric | Metered, Jan–Apr 2026 |
| Electrical intensity | 1.849 kWh/kg | Metered, Jan–Apr 2026 |
| Colour error (ΔE₂₀₀₀) | 13.05 ± 2.50 | Pre-intervention baseline |
| RFT rate | Not yet measured | Pending inline sensor installation |

> **Note:** The site already performs better than the Bangladesh national average (164 L/kg). The project's objective is systematic optimisation from this credible baseline — targeting ≤ 50 L/kg water and ≥ 85% RFT.

## 6. Methodology — Four Phases

| Phase | Period | Activities |
|-------|--------|-----------|
| **Phase 1 — Baseline & Data Pipeline** | M1–M3 | Metered baseline, data validation, ML training on historical data |
| **Phase 2 — Shadow Mode (Read-Only)** | M3–M6 | AI runs alongside operators, no control action, A/B comparison data collected |
| **Phase 3 — Prospective A/B Trial** | M6–M12 | Randomised allocation of batches to AI-recommended vs standard recipe |
| **Phase 4 — Constrained Closed-Loop** | M12–M18 | AI writes setpoint adjustments within SPC-monitored safety bounds |

## 7. Ethical & Safety Framework

- All AI write-back actions are bounded by hard safety limits in the machine PLC (IEC 61511 / IEC 62061 compliant). The AI system never touches Layer 1 (hardwired safety interlocks).
- Human override is always available; the AI operates in "advisory then constrained-write" mode, not autonomous control.
- Industrial data is used under formal research collaboration agreement. Proprietary batch data is not published.

## 8. Expected Outcomes

| KPI | Baseline | Target | Projected Improvement |
|-----|----------|--------|----------------------|
| Water per kg | 67.1 L/kg | ≤ 50 L/kg | 25–30% reduction |
| RFT rate | ~40–65% (open-loop estimate) | ≥ 85% | 20–45 pp improvement |
| ΔE₂₀₀₀ | 13.05 | ≤ 1.0 | Order-of-magnitude improvement |
| Chemical cost | Baseline TBD | −10–15% | Via recipe optimisation |

---

## 📚 References & Documentation

- [000_SMART_DYEING_HOME.md](../docs/000_SMART_DYEING_HOME.md) — Project knowledge base home
- [SMART_DYEING_Technical_Summary.md](../docs/SMART_DYEING_Technical_Summary.md) — Site baseline analysis and key metrics
- [PLC_AI_ClosedLoop_Review_FINAL.md](../docs/PLC_AI_ClosedLoop_Review_FINAL.md) — 95K-word closed-loop control technical review
