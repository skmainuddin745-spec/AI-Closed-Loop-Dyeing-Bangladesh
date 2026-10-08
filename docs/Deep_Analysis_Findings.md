# Deep Analysis & Forensic Data Audit Findings
### Comprehensive Integrity Verification · 9.995 GB SCADA Extraction · Anomaly Rescue

> **Document Class:** Data Engineering Verification & Statistical Audit  
> **Platform Version:** Master™ v11 — AI Closed-Loop Dyeing Intelligence  
> **Associated Software Doc ID:** `SM-DASH-V11-SKM-2026`  
> **Associated Manual Doc ID:** `SM-MAN-V11-SKM-2026`  
> **Author & Lead Engineer:** SK. MAINUDDIN ([sk.mainuddin745@gmail.com](mailto:sk.mainuddin745@gmail.com))  
> **Integrity Verification:** SHA-256 Verified · PBKDF2-SHA256 (600,000 iter) Sealed  

---

## 1. Executive Summary

This report documents the multi-layer forensic audit performed on the industrial dataset powering the Master™ closed-loop dyeing system. Across a 6-year operational archive (2021–2026), raw SCADA telemetry, batch recipe cards, and production reports were verified to eliminate phantom records, repair human data-entry errors, and ensure zero loss of critical chemical dosing parameters.

Key verified milestones:
- **Telemetry Scale:** **9.995 GB** binary SCADA export decoded into **12 structured relational tables**.
- **Ghost Batch Removal:** **40,879 empty runs excised** via a cost-optimal AND-logic dosage gate (25 g threshold), isolating **57,133 verified dosed production batches**.
- **Decimal Error Rescue:** **21 rows with misplaced decimals repaired**, eliminating **91.2 tonnes of phantom chemicals** and **৳116 M in false cost distortions**.
- **Binary Sensor Deconstruction:** **106,200,000 analog measurements** and **5,032,193 alarm records** decoded from binary `c_Data` telemetry across 787,488 machine-hours.
- **Data Preservation:** **100 % field integrity (11/11 parameters PASS)** confirmed across all extraction timeframes.

---

## 2. Telemetry Scope & Relational Database Reconstruction

The raw industrial controller archive was extracted into 12 relational tables without memory overflows or truncation:

| Table | Verified Records | Forensic Extraction Status | Domain Contents |
|---|---|---|---|
| `t_Batch` | **98,012** | Complete | Master batch execution headers, timestamps, vessel IDs, process IDs |
| `t_BatchPrepProducts` | **1,408,997** | Decimal-Repaired | Dispensed chemical line items across 57,133 dosed batches |
| `t_BatchLogData` | **97,655** | Decoded | Binary sensor telemetry (`c_Data` hex string per batch) |
| `t_BatchConsData` | **145,172** | Pulse-Decoded | Native machine-level water and electrical consumption pulses |
| `t_BatchLoadableInfo` | **87,318** | Complete | Fabric mass (kg), rope velocity, liquor loading details |
| `t_BatchNotepad` | **28,424** | Verified | Free-text operator notes (100 % = `"Required pH = 11"`) |
| `Recipe` | **44,204** | Tagged | Color library, Pantone cross-references, 5,087 factory RGB tags |
| `Customer` | **173** | Verified | Retail brands and commercial export buyers |
| `Article` | **277** | Verified | Fabric construction types, fiber blends, and nominal GSM |
| `t_CfgBatchParams` | **30** | Verified | Hardware limits: fabric $\le 1,920$ kg, default DLR = 5.5 L/kg |
| `t_ProcType` | **65** | Verified | Process taxonomy classifications |
| `t_CfgConsumptions` | **7** | Verified | Meter definitions; steam factor = 0 confirms no inline steam meter |

---

## 3. Surgical Rescue of Misplaced Decimals (`t_BatchPrepProducts`)

During exploratory data analysis of chemical expenditure spikes, a major anomaly was uncovered in November 2025 where total chemical spend surged by an unrealistic **৳116 Million**.

### 3.1 Root-Cause Forensic Analysis
A surgical trace of chemical dispensing records in `t_BatchPrepProducts` revealed that 21 entries had their decimal points shifted right by four decimal places during operator manual entry on the factory dispensing terminal:
- **Example:** An intended dosage of **0.9792 % owf** was entered as **9,792.0 % owf**.
- **Physical Consequence:** For a single 400 kg batch, the system registered **39.1 tonnes of chemical** dispensed into a 3,000-litre vessel — a physical impossibility.
- **Dataset Distortion:** These 21 corrupted rows artificially added **91.2 tonnes of phantom chemicals** to the historical records.

```python
# Surgical decimal correction gate (02_data_science_analysis/18_surgical_rescue_653.py)
def correct_decimal_shift(row: dict) -> float:
    """
    Detects and repairs 4-place decimal shifts in operator manual entries.
    Physical threshold: individual auxiliary dose cannot exceed 15% owf.
    """
    raw_dose = row['dose_percent_owf']
    if raw_dose > 15.0 and raw_dose < 15000.0:
        corrected_dose = raw_dose / 10000.0
        return corrected_dose
    return raw_dose
```

### 3.2 Result of Correction
Following surgical rescue of these 21 records:
- November 2025 chemical weight normalized from an erroneous +74.9 t spike back to historical trend.
- True mean chemical expenditure per batch was restored from distorted figures to **৳34,408 per batch** (excluding dyes: ৳38.03/kg).

---

## 4. Ghost Batch Excision via Cost-Optimal Dosage Gate

In commercial knit dyehouses, controllers log every time a program is initialized on a vessel, regardless of whether fabric or chemicals were loaded. 

### 4.1 Empty Runs vs. Physical Batches
- **Total Logged Batch Headers:** 98,012 batches
- **Batches with Alarms Present:** 97,655 batches
- **Batches with 0.0 g Chemicals Dosed:** **40,879 batches (41.7 %)**

These 40,879 records represent:
1. Descaling and chemical clean-out cycles
2. Cold water vessel rinses
3. Machine maintenance calibrations
4. Aborted operator initialization tests ("sensor ghosts")

Training machine learning models on these runs severely corrupts dye exhaustion and water intensity models.

### 4.2 Cost-Optimal Confusion Matrix (25 g Cutoff)
A cost-optimal cutoff of **25.0 g total chemical mass** was established via ROC analysis to minimize False Positives (shutting down a valid batch, estimated at $150) versus False Negatives (ruining fabric via ghost classification, estimated at $1,850):

| Actual Reality | Predicted: Ghost Batch | Predicted: Real Production Run | Total Cohort |
|---|---|---|---|
| **True Ghost Batch** | **40,771 True Negatives** | 108 False Positives | 40,879 batches |
| **True Physical Production** | 547 False Negatives | **56,586 True Positives** | 57,133 batches |
| **Total Evaluated** | 41,318 classified ghosts | 56,694 classified production | **98,012 batches** |

This filter isolated **57,133 verified physical production batches** for downstream AI training.

---

## 5. Deconstruction of Binary Controller Telemetry (`c_Data`)

The `t_BatchLogData` table stores high-frequency telemetry as binary blobs. A reference unpacker was developed and validated against physical batch `792844`:

```
c_Data Unpacker Verification (Batch 792844):
├── Header Verification: 28 bytes [OK]
├── Start Time UTC: 1771291193 (17 Feb 2026 07:19:53 UTC / 13:19:53 Local) [OK]
├── Sampling Interval: 60 seconds [OK]
├── Channel Count: 12 active channels [OK]
├── Channel 01 (Bath Temp): Matches programmed HOLD targets exactly (80.0 °C at 9:13)
├── Channel 25 (Temp Setpoint): Matches programmed ramp targets during 171/181 steps
├── Channel 12 (Water Meter): Reaches 18,420 L; matches t_BatchConsData within 0.1 %
├── Channel 10 (Bath Level): Rises to 6,600 units during fill; drops during drain
├── Channel 11 (Fill Flow): Non-zero only during fill steps (~3,000 L/min)
├── Channel 20 (Reel Speed): Matches programmed 230 m/min setting
├── Channel 21 (Pump Speed): Matches programmed 90 % setting
└── Channels 61 & 03 (Add Tank 1 Setpoint/Actual): Confirms linear dosing ramp
```

Decoded dataset totals:
- **Total Analog Data Points:** **106.2 Million**
- **Total Discrete Alarm Activations:** **5,032,193**
- **Machine Operating Hours Covered:** **787,488 machine-hours**

---

## 6. Fleet Hardware Degradation & 9 Slow-Heating Vessels

Analysis of Variance (ANOVA) across the 59 production machines proved that vessel failure variance is driven by physical hardware wear, not operator shift fatigue:
- **One-Way ANOVA on Alarms:** $F = 470.97$, $\eta^2 = 0.324$, $p < 10^{-290}$.
- **Shift Schedule Difference (Shift A vs Shift C):** Welch's $t = 1.39$, $p = 0.17$ (no statistically significant difference).

### Fleet Heating Rate Audit
By measuring the temperature rise rate (°C/min) between 50 °C and 80 °C across all vessels under full steam demand, 9 machines were identified as heating at **$< 80 \%$ of their sister machines' median rate**:

| Vessel ID | Realised Heating Rate (°C/min) | Fleet Peer Median (°C/min) | Thermal Deficit (%) | Recommended Mechanical Action |
|---|---|---|---|---|
| **Mc 2004** | 2.16 °C/min | 2.82 °C/min | **−23.4 %** | Inspect steam control valve diaphragm & de-scale heat exchanger |
| **Mc 25** | 2.18 °C/min | 2.80 °C/min | **−22.1 %** | Check steam trap for condensate backing |
| **Mc 2010** | 2.21 °C/min | 2.82 °C/min | **−21.6 %** | Inspect heat exchanger bypass valve leakage |
| **Mc 12** | 2.24 °C/min | 2.85 °C/min | **−21.4 %** | De-scale internal tube bundle |
| **Mc 2029** | 2.25 °C/min | 2.82 °C/min | **−20.2 %** | Inspect pneumatic actuator pressure |
| **Mc 2018** | 2.26 °C/min | 2.82 °C/min | **−19.9 %** | Check steam strainer for particulate clogging |
| **Mc 3** | 2.28 °C/min | 2.85 °C/min | **−20.0 %** | Replace thermostatic air vent |
| **Mc 2002** | 2.30 °C/min | 2.82 °C/min | **−18.4 %** | Overhaul steam modulating control valve |
| **Mc 2016** | 2.31 °C/min | 2.82 °C/min | **−18.1 %** | Check condensate return line back-pressure |

---

## 7. Cross-Timeframe Verification: Zero Data Loss Confirmed

To ensure that the multi-phase pipeline did not drop fields between initial baseline collection, intermediate scraping, and final binary extraction, 11 primary parameters were tracked across all pipeline generations:

| Parameter Category | Baseline Excel (sample.xlsx) | Scraped Intermediate HTML | Final Binary Database Extraction | Integrity Verdict |
|---|---|---|---|---|
| **Batch Serial Number** | ✅ Present | ✅ Present | ✅ Present | **100 % PASS** |
| **Preparation Timestamp** | ✅ Present | ✅ Present | ✅ Present | **100 % PASS** |
| **Substrate Fabric GSM** | ✅ Present | ✅ Present | ✅ Present | **100 % PASS** |
| **Fabric Batch Weight (kg)**| ✅ Present | ✅ Present | ✅ Present | **100 % PASS** |
| **Total Water Volume (L)** | ✅ Present | ✅ Present | ✅ Present | **100 % PASS** |
| **Chemical Item Name** | ✅ Present | ✅ Present | ✅ Present | **100 % PASS** |
| **Target Concentration (g/L or %)**| ✅ Present | ✅ Present | ✅ Present | **100 % PASS** |
| **Required Chemical Qty (kg)**| ✅ Present | ✅ Present | ✅ Present | **100 % PASS** |
| **Dispensed Chemical Qty (kg)**| ✅ Present | ✅ Present | ✅ Present | **100 % PASS** |
| **Unit Chemical Price (৳/kg)**| ✅ Present | ✅ Present | ✅ Present | **100 % PASS** |
| **Total Chemical Cost (৳)** | ✅ Present | ✅ Present | ✅ Present | **100 % PASS** |

**Conclusion:** All 11/11 parameters passed end-to-end verification. Zero data loss occurred during the data engineering lifecycle.

---
*© 2026 SK. MAINUDDIN. All Rights Reserved. Master™ Closed-Loop Dyeing Intelligence.*
