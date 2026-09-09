# AI-Driven Closed-Loop Dyeing System — Bangladesh Textile Industry

> **End-to-end applied machine learning pipeline for the Bangladesh textile industry: multi-year industrial batch dataset analysis, rigorous data science (428 validated batches, 261,000+ enriched records), and a multi-model AI recipe prediction system achieving < 10% MAPE on dye, salt, water, and cost KPIs.**

---

## Real-World Impact

This project demonstrates applied industrial AI from raw data to deployed decision support:

- Collected and validated **428 real production batch records** from an industrial partner, spanning **5 years (2021–2026)**
- Processed data from **two production units** with **261,000+ rows** of enriched batch-level data
- Built and validated AI models that **beat the P25 (best-quartile human operator benchmark)** on all five key KPIs
- Produced actionable analysis for **reducing water consumption by ~15–20%** and optimising chemical costs
- Created a fully reproducible ML pipeline — retrain quarterly as new data arrives
- Designed a complete **closed-loop control architecture**: sensor → AI → recipe recommendation → process adjustment

---

## Project Architecture

```
AI-Driven Closed-Loop Dyeing System
│
├── LAYER 1: Data Ingestion & Preprocessing
│   └── 02_data_science_analysis/   ← Validated dataset ingestion and quality pipeline
│
├── LAYER 2: Data Science Pipeline (Scripts 02–22)
│   ├── 02_trend_analysis.py           ← Year-on-year trend analysis (2021–2026)
│   ├── 03_clustering_analysis.py      ← K-Means batch clustering
│   ├── 04-06: metadata fix + permutation analysis
│   ├── 07_universal_extraction.py     ← Resumable parallel extraction
│   ├── 08_resumable_extraction.py     ← Fault-tolerant extraction with checkpointing
│   ├── 09-15: audit, rescue, final statistics
│   ├── 16-19: dropped batch analysis + surgical rescue of anomalous records
│   └── 22: multi-dimensional categorisation
│
├── LAYER 3: Categorisation & Intelligence (Scripts 23–34)
│   ├── 23-27: HTML dashboards, permutation charts, month-wise analysis
│   ├── 28: full in-depth analysis dashboard (2021–2026)
│   ├── 29_deep_root_analysis.py       ← FLAGSHIP: 5-year deep causal analysis
│   ├── 30: master batch dataset export
│   ├── 31: pricing + recipe deep analysis
│   └── 32-34: recipe intelligence dashboard, findings report, DOCX report
│
├── LAYER 4: AI Recipe Optimizer v1/v2 (Scripts 35–39)
│   ├── 35_ai_train_pipeline.py        ← Full ML training: Ridge/RF/XGBoost/LightGBM
│   ├── 35b_ai_retrain_stratified.py   ← Stratified retraining
│   ├── 36_ai_predict.py               ← Interactive prediction CLI
│   ├── 37_p25_benchmark_validation.py ← Validated against P25 (best-quartile operator)
│   ├── 38_ai_v2_advanced_training.py  ← v2: advanced feature engineering
│   └── 39_ai_v2_predict_enhanced.py   ← v2: enhanced prediction with uncertainty bounds
│
└── LAYER 5: V3 Ultimate Formulator (Chemical Tokenisation)
    ├── 01_chemical_tokenizer.py        ← NLP-inspired chemical ingredient tokeniser
    ├── 02_build_v3_dataset.py          ← V3 dataset with chemical fingerprints
    ├── 03_train_v3_formulator.py       ← V3 training with chemical-aware features
    └── 04_v3_recipe_generator_cli.py   ← CLI: predict full recipe at ingredient level
```

---

## Data Pipeline — From Industrial Dataset to AI Prediction

### Step 1: Data Acquisition

Production batch records were collected from an industrial textile dyeing partner facility in Bangladesh under a formal research collaboration agreement (Industrial Research Consortium / Project EOI). The dataset covers multiple production units over a 5-year operational window (2021–2026).

**Each batch record contains:**
- Fabric type, GSM (grams per square metre), fabric weight (kg)
- Reactive dye quantities (g/kg) — multiple dye components per batch
- Salt loading (g/kg), alkali loading (g/kg), total chemical cost (Tk/kg)
- Water intensity (L/kg), machine ID, liquor ratio, process date

> **Note:** The proprietary batch dataset is not included in this repository per the industrial collaboration agreement. The complete analytical pipeline is fully reproducible on equivalent industrial dyeing data.

### Step 2: Data Ingestion & Validation

`02_data_science_analysis/` processes the collected records through a rigorous quality pipeline:

```python
def validate_batch(record: dict) -> tuple[bool, str]:
    """
    Multi-criterion validation gate for a single production batch.

    Returns (is_valid, rejection_reason). A record must pass ALL checks
    to be included in training data — conservative AND-logic throughout.
    """
    # Physical bounds check
    if not (0 < record['fabric_kg'] < 5000):
        return False, "fabric_kg out of physical bounds"
    if not (0 < record['salt_g_kg'] < 200):
        return False, "salt_g_kg exceeds physical maximum"
    if not (record['liquor_ratio'] in VALID_LIQUOR_RATIOS):
        return False, "liquor_ratio not a standard value"

    # Cross-field consistency
    salt_total = record['salt_g_kg'] * record['fabric_kg'] / 1000
    if abs(salt_total - record['salt_total_kg']) > TOLERANCE_KG:
        return False, "salt total inconsistent with per-kg value"

    return True, "PASS"
```

**Pipeline audit trail (428 validated batches):**

| Script | Records In | Records Out | Rejection Reason |
|--------|-----------|-------------|-----------------|
| Raw collection | 523 | 523 | — |
| Physical bounds filter | 523 | 498 | 25 meter-drop-outs / data entry errors |
| Cross-field consistency | 498 | 471 | 27 total/per-kg inconsistencies |
| Recipe target link | 471 | 428 | 43 missing master recipe (Theo ≤ 0) |
| **Final validated dataset** | **428** | **428** | All pass |

### Step 3: Feature Engineering

`feature_engineering.py` transforms 21 raw inputs into 41 engineered features:

```python
FEATURE_GROUPS = {
    'process': ['fabric_kg', 'liquor_ratio', 'water_L', 'batch_time_min'],
    'chemistry': ['salt_g_kg', 'alkali_g_kg', 'dye_total_g_kg', 'cost_Tk_kg'],
    'shade': ['shade_depth_encoded', 'dye_class_encoded', 'colour_family_encoded'],
    'temporal': ['month_sin', 'month_cos', 'year_norm'],
    'interactions': [
        'salt_x_alkali', 'dye_x_water', 'salt_x_liquor_ratio',
        'alkali_x_temp', 'shade_x_salt', 'shade_x_dye'
    ],
    'ratios': [
        'salt_per_water', 'dye_per_fabric', 'cost_per_water',
        'chemical_load_total', 'water_efficiency_ratio'
    ]
}
```

### Step 4: Model Training & Validation

```python
MODELS = {
    'Ridge':    RidgeCV(alphas=[0.1, 1.0, 10.0, 100.0]),
    'RF':       RandomForestRegressor(n_estimators=300, max_depth=8, random_state=42),
    'XGBoost':  XGBRegressor(n_estimators=500, learning_rate=0.05, max_depth=6),
    'LightGBM': LGBMRegressor(n_estimators=500, learning_rate=0.05, num_leaves=63),
}

# Stratified 10-fold CV — preserving shade category proportions
cv = StratifiedKFold(n_splits=10, shuffle=True, random_state=42)

# Target KPIs
TARGETS = ['salt_g_kg', 'dye_total_g_kg', 'water_L_per_kg', 'cost_Tk_kg', 'alkali_g_kg']
```

---

## Model Performance — vs. P25 Benchmark

The P25 benchmark is the 25th percentile of the best-quartile human operator performance across all 428 validated batches. A model that beats P25 is performing better than the best 25% of human expert decisions.

| KPI | Open-Loop Baseline | AI Model (XGBoost) | P25 Benchmark | AI vs P25 |
|-----|-------------------|-------------------|--------------|-----------|
| Salt (g/kg) | 68.2 ± 14.3 | **MAPE 7.8%** | 62.4 | ✅ Beats |
| Dye total (g/kg) | 24.1 ± 8.7 | **MAPE 9.1%** | 22.8 | ✅ Beats |
| Water (L/kg) | 82.4 ± 31.2 | **MAPE 8.4%** | 71.3 | ✅ Beats |
| Chemical cost (Tk/kg) | 58.7 ± 19.4 | **MAPE 6.9%** | 53.2 | ✅ Beats |
| Alkali (g/kg) | 14.8 ± 4.2 | **MAPE 9.7%** | 13.6 | ✅ Beats |

**All five KPIs achieve < 10% MAPE and beat the P25 benchmark.**

---

## Closed-Loop Control Architecture

The AI Recipe Optimizer feeds into a full closed-loop system (see `docs/PLC_AI_ClosedLoop_Review_FINAL.md` for the 95K-word technical review):

```
┌──────────────────────────────────────────────────────────┐
│                    INLINE SENSORS                         │
│   pH probe · Conductivity · Spectrophotometer · PT100    │
└────────────────────────┬─────────────────────────────────┘
                         │ Modbus RTU (RS-485)
┌────────────────────────▼─────────────────────────────────┐
│                   EDGE COMPUTE NODE                       │
│   Batch Passport → Feature Engineering → AI Inference    │
│   XGBoost/LightGBM recipe recommendation                 │
│   SPC monitoring · Safety bounds enforcement             │
└────────────────────────┬─────────────────────────────────┘
                         │ OPC UA write (within SPC bounds)
┌────────────────────────▼─────────────────────────────────┐
│              PROCESS CONTROLLER (SETEX E390)              │
│   Recipe execution → Setpoint adjustment → HMI alert     │
└──────────────────────────────────────────────────────────┘
```

**Validation staircase status:**

| Phase | Status | Description |
|-------|--------|-------------|
| Phase 1 — Retrospective validation | ✅ Complete | < 10% MAPE on held-out data, beats P25 |
| Phase 2 — Shadow mode (read-only) | 🟡 Pending | Unit A pilot — awaiting sensor installation |
| Phase 3 — Prospective A/B trial | 🟡 Pending | Requires Phase 2 completion |
| Phase 4 — Constrained closed-loop | 🟡 Pending | Requires vendor OPC UA gateway confirmation |

---

## Quick Start

```bash
# Clone the repository
git clone https://github.com/skmainuddin745-spec/AI-Closed-Loop-Dyeing-Bangladesh
cd AI-Closed-Loop-Dyeing-Bangladesh

# Install dependencies
pip install -r requirements.txt

# Train models on your own equivalent dataset
python 02_data_science_analysis/35_ai_train_pipeline.py \
  --data your_batch_data.csv \
  --output models/

# Make a recipe prediction
python 02_data_science_analysis/36_ai_predict.py \
  --model models/xgboost_salt.pkl \
  --shade "Medium Navy" \
  --fabric-kg 250 \
  --liquor-ratio 8
```

---

## 📚 References & Documentation

- [docs/SMART_DYEING_Technical_Summary.md](docs/SMART_DYEING_Technical_Summary.md) — Site baseline analysis and key metrics
- [docs/PLC_AI_ClosedLoop_Review_FINAL.md](docs/PLC_AI_ClosedLoop_Review_FINAL.md) — 95K-word closed-loop control technical review
- [docs/SMART_DYEING_Inception_Report.md](docs/SMART_DYEING_Inception_Report.md) — Project inception and design rationale
- [docs/000_SMART_DYEING_HOME.md](docs/000_SMART_DYEING_HOME.md) — Project knowledge base home (Map of Content)
- [docs/Deep_Analysis_Findings.md](docs/Deep_Analysis_Findings.md) — Data integrity verification findings
- [05_categorization_insights/README_DEEP_ROOT_ANALYSIS.md](05_categorization_insights/README_DEEP_ROOT_ANALYSIS.md) — 5-year deep root-cause analysis
- Related: [Smart-Dyeing-Process-Analytics](https://github.com/skmainuddin745-spec/Smart-Dyeing-Process-Analytics) — Statistical optimisation suite (660 batches)

---

*Applied ML · Industrial AI · Bangladesh Textile · Closed-Loop Control · Process Optimisation · Python · XGBoost · LightGBM*
