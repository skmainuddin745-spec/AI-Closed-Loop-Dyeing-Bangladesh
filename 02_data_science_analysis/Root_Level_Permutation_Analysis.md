# Root-Level Combinatorial Analysis
This report examines every unique permutation of **Fabric Type x Dyeing Process x Machine No x GSM** across the verified core dataset of 47403 unbiased batches.

## 1. Top 15 Most Efficient Operational Combinations
These specific combinations represent the absolute highest profitability and operational efficiency in the factory. They should be prioritized for max loading.
| Fabric Type | Dyeing Type | Machine No | GSM Class | Batches | Cost/kg (Tk) | Water/kg (L) | Chem/kg (kg) |
|---|---|---|---|---|---|---|---|
| Other | 2Part&nbsp; | Unknown | Heavy (>220) | 16 | **1.58** | 7.02 | 0.005 |
| Other | 2Part&nbsp; | Unknown | Medium (151-220) | 10 | **2.62** | 7.00 | 0.007 |
| Polyester/Blend | 2Part&nbsp; | Unknown | Heavy (>220) | 30 | **3.19** | 6.93 | 0.009 |
| Other | Normal&nbsp; | Unknown | Unknown | 234 | **4.13** | 10.06 | 0.027 |
| Other | Normal&nbsp; | Unknown | Light (<=150) | 2,499 | **4.14** | 7.05 | 0.016 |
| Polyester/Blend | Normal&nbsp; | Unknown | Unknown | 13 | **4.14** | 13.66 | 0.029 |
| Other | 2Part&nbsp; | Unknown | Light (<=150) | 8 | **4.19** | 7.51 | 0.015 |
| 100% Cotton | Normal&nbsp; | Unknown | Unknown | 607 | **4.86** | 12.75 | 0.030 |
| 100% Cotton | 2Part&nbsp; | Unknown | Heavy (>220) | 16 | **4.88** | 7.08 | 0.022 |
| 100% Cotton | Normal&nbsp; | Unknown | Heavy (>220) | 8,970 | **5.07** | 3.44 | 0.027 |
| Cotton-Elastane | Normal&nbsp; | Unknown | Medium (151-220) | 230 | **5.31** | 2.87 | 0.036 |
| Polyester/Blend | Normal&nbsp; | Unknown | Light (<=150) | 175 | **5.38** | 4.66 | 0.028 |
| Other | Normal&nbsp; | Unknown | Medium (151-220) | 1,610 | **5.41** | 3.97 | 0.034 |
| 100% Cotton | 2Part&nbsp; | Unknown | Light (<=150) | 5 | **5.81** | 6.17 | 0.025 |
| 100% Cotton | 2Part&nbsp; | Unknown | Medium (151-220) | 11 | **5.89** | 6.97 | 0.030 |

## 2. Top 15 Most Wasteful / Expensive Combinations
These combinations represent catastrophic profitability bleed. Reworks or specific machine-fabric mismatches heavily inflate chemical and water load.
| Fabric Type | Dyeing Type | Machine No | GSM Class | Batches | Cost/kg (Tk) | Water/kg (L) | Chem/kg (kg) |
|---|---|---|---|---|---|---|---|
| 100% Cotton | Normal&nbsp; | Unknown | Light (<=150) | 7,367 | **8.60** | 1.80 | 0.061 |
| 100% Cotton | Normal&nbsp; | Unknown | Medium (151-220) | 21,243 | **7.69** | 2.19 | 0.050 |
| Cotton-Elastane | Normal&nbsp; | Unknown | Heavy (>220) | 167 | **6.90** | 2.36 | 0.038 |
| Polyester/Blend | Normal&nbsp; | Unknown | Heavy (>220) | 1,651 | **6.69** | 2.35 | 0.048 |
| Other | Normal&nbsp; | Unknown | Heavy (>220) | 2,331 | **6.49** | 3.01 | 0.040 |
| Polyester/Blend | Normal&nbsp; | Unknown | Medium (151-220) | 202 | **6.34** | 1.79 | 0.043 |
| 100% Cotton | 2Part&nbsp; | Unknown | Medium (151-220) | 11 | **5.89** | 6.97 | 0.030 |
| 100% Cotton | 2Part&nbsp; | Unknown | Light (<=150) | 5 | **5.81** | 6.17 | 0.025 |
| Other | Normal&nbsp; | Unknown | Medium (151-220) | 1,610 | **5.41** | 3.97 | 0.034 |
| Polyester/Blend | Normal&nbsp; | Unknown | Light (<=150) | 175 | **5.38** | 4.66 | 0.028 |
| Cotton-Elastane | Normal&nbsp; | Unknown | Medium (151-220) | 230 | **5.31** | 2.87 | 0.036 |
| 100% Cotton | Normal&nbsp; | Unknown | Heavy (>220) | 8,970 | **5.07** | 3.44 | 0.027 |
| 100% Cotton | 2Part&nbsp; | Unknown | Heavy (>220) | 16 | **4.88** | 7.08 | 0.022 |
| 100% Cotton | Normal&nbsp; | Unknown | Unknown | 607 | **4.86** | 12.75 | 0.030 |
| Other | 2Part&nbsp; | Unknown | Light (<=150) | 8 | **4.19** | 7.51 | 0.015 |

## 3. The Rework Penalty Matrix
Aggregating strictly by Dyeing Type reveals the true financial penalty of non-'Normal' procedures.
| Dyeing Process | Total Batches | True Cost/kg (Tk) |
|---|---|---|
| 2Part&nbsp; | 96 | **3.29** |
| Normal&nbsp; | 47,299 | **7.36** |