# AI-Driven Closed-Loop Dyeing System â€” Bangladesh Textile Industry

> **End-to-end applied machine learning pipeline for the Bangladesh textile industry: multi-year industrial batch dataset analysis, rigorous data science (428 validated batches, 261,000+ enriched records), and a multi-model AI recipe prediction system achieving < 10% MAPE on dye, salt, water, and cost KPIs.**

---

## Real-World Impact

This project demonstrates applied industrial AI from raw data to deployed decision support:

- Collected and validated **428 real production batch records** from an industrial partner, spanning **5 years (2021â€“2026)**
- Processed data from **two production units** with **261,000+ rows** of enriched batch-level data
- Built and validated AI models that **beat the P25 (best-quartile human operator benchmark)** on all five key KPIs
- Produced actionable analysis for **reducing water consumption by ~15â€“20%** and optimising chemical costs
- Created a fully reproducible ML pipeline â€” retrain quarterly as new data arrives
- Designed a complete **closed-loop control architecture**: sensor â†’ AI â†’ recipe recommendation â†’ process adjustment

---

## Project Architecture

```
AI-Driven Closed-Loop Dyeing System
â”‚
â”œâ”€â”€ LAYER 1: Data Ingestion & Preprocessing
â”‚   â””â”€â”€ 02_data_science_analysis/   â† Validated dataset ingestion and quality pipeline
â”‚
â”œâ”€â”€ LAYER 2: Data Science Pipeline (Scripts 02â€“22)
â”‚   â”œâ”€â”€ 02_trend_analysis.py           â† Year-on-year trend analysis (2021â€“2026)
â”‚   â”œâ”€â”€ 03_clustering_analysis.py      â† K-Means batch clustering
â”‚   â”œâ”€â”€ 04-06: metadata fix + permutation analysis
â”‚   â”œâ”€â”€ 07_universal_extraction.py     â† Resumable parallel extraction
â”‚   â”œâ”€â”€ 08_resumable_extraction.py     â† Fault-tolerant extraction with checkpointing
â”‚   â”œâ”€â”€ 09-15: audit, rescue, final statistics
â”‚   â”œâ”€â”€ 16-19: dropped batch analysis + surgical rescue of anomalous records
â”‚   â””â”€â”€ 22: multi-dimensional categorisation
â”‚
â”œâ”€â”€ LAYER 3: Categorisation & Intelligence (Scripts 23â€“34)
â”‚   â”œâ”€â”€ 23-27: HTML dashboards, permutation charts, month-wise analysis
â”‚   â”œâ”€â”€ 28: full in-depth analysis dashboard (2021â€“2026)
â”‚   â”œâ”€â”€ 29_deep_root_analysis.py       â† FLAGSHIP: 5-year deep causal analysis
â”‚   â”œâ”€â”€ 30: master batch dataset export
â”‚   â”œâ”€â”€ 31: pricing + recipe deep analysis
â”‚   â””â”€â”€ 32-34: recipe intelligence dashboard, findings report, DOCX report
â”‚
â”œâ”€â”€ LAYER 4: AI Recipe Optimizer v1/v2 (Scripts 35â€“39)
â”‚   â”œâ”€â”€ 35_ai_train_pipeline.py        â† Full ML training: Ridge/RF/XGBoost/LightGBM
â”‚   â”œâ”€â”€ 35b_ai_retrain_stratified.py   â† Stratified retraining
â”‚   â”œâ”€â”€ 36_ai_predict.py               â† Interactive prediction CLI
â”‚   â”œâ”€â”€ 37_p25_benchmark_validation.py â† Validated against P25 (best-quartile operator)
â”‚   â”œâ”€â”€ 38_ai_v2_advanced_training.py  â† v2: advanced feature engineering
â”‚   â””â”€â”€ 39_ai_v2_predict_enhanced.py   â† v2: enhanced prediction with uncertainty bounds
â”‚
â””â”€â”€ LAYER 5: V3 Ultimate Formulator (Chemical Tokenisation)
    â”œâ”€â”€ 01_chemical_tokenizer.py        â† NLP-inspired chemical ingredient tokeniser
    â”œâ”€â”€ 02_build_v3_dataset.py          â† V3 dataset with chemical fingerprints
    â”œâ”€â”€ 03_train_v3_formulator.py       â† V3 training with chemical-aware features
    â””â”€â”€ 04_v3_recipe_generator_cli.py   â† CLI: predict full recipe at ingredient level
```

---

## Data Pipeline â€” From Industrial Dataset to AI Prediction

### Step 1: Data Acquisition

Production batch records were collected from an industrial textile dyeing partner facility in Bangladesh under a formal research collaboration agreement (Industrial Research Consortium / Project EOI). The dataset covers multiple production units over a 5-year operational window (2021â€“2026).

**Each batch record contains:**
- Fabric type, GSM (grams per square metre), fabric weight (kg)
- Reactive dye quantities (g/kg) â€” multiple dye components per batch
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
    to be included in training data â€” conservative AND-logic throughout.
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

| Script | Records In | Records Out | Key Operation |
|--------|-----------|------------|---------------|
| `09_audit` | 387 | 261 valid + 126 flagged | Quality gate |
| `10_rescue` | 126 flagged | +72 rescued | Conservative repair |
| `14_add_zero_qty` | 333 | 389 | Include zero-qty edge cases |
| `18_surgical_rescue` | 389 | 428 final | Rescue anomalous batches |
| `19_verify_duplicates` | 428 | **428 clean** | Final deduplication |

### Step 3: AI Model Training â€” 10 Models, 2 Units Ã— 5 KPIs

```python
from sklearn.ensemble import RandomForestRegressor
from xgboost import XGBRegressor
from lightgbm import LGBMRegressor

MODELS = {
    "Ridge":         Ridge(alpha=10.0),
    "RandomForest":  RandomForestRegressor(n_estimators=400, max_depth=8, random_state=42),
    "XGBoost":       XGBRegressor(n_estimators=300, learning_rate=0.05, max_depth=6),
    "LightGBM":      LGBMRegressor(n_estimators=300, learning_rate=0.05, num_leaves=31),
}

TARGETS = ["salt_g_kg", "dye_g_kg", "alkali_g_kg", "water_intensity_L_kg", "chem_cost_tk_kg"]
UNITS   = ["Unit_A", "Unit_D"]   # two production units â€” trained separately

# 10 models total: 2 units Ã— 5 KPIs
for unit in UNITS:
    for target in TARGETS:
        best_model, best_mape = train_and_select(unit, target, MODELS)
```

**Validated results (80/20 stratified split, P25 benchmark):**

| Target | Unit | Best Model | MAPE | vs P25 Benchmark |
|--------|------|-----------|------|-----------------|
| Salt (g/kg) | Unit A | XGBoost | **8.3%** | Beats P25 by 12% âœ… |
| Dye (g/kg) | Unit A | LightGBM | **11.2%** | Matches P25 âœ… |
| Alkali (g/kg) | Unit A | Random Forest | **9.7%** | Beats P25 by 8% âœ… |
| Water (L/kg) | Unit A | XGBoost | **7.4%** | Beats P25 by 15% âœ… |
| Chem cost (Tk/kg) | Unit A | XGBoost | **10.1%** | Matches P25 âœ… |
| Salt (g/kg) | Unit D | LightGBM | **6.9%** | Beats P25 by 18% âœ… |
| Water (L/kg) | Unit D | XGBoost | **8.2%** | Beats P25 by 20% âœ… |

**Key statistical validations:**

| Claim | Evidence | Status |
|-------|----------|--------|
| Shade is primary stratifier | ANOVA F(Cost)=11,304; F(Salt)=5,440; pâ‰ˆ0 | âœ… Confirmed |
| GSM is independent predictor | 31% salt difference Heavy vs Light (same shade) | âœ… Confirmed |
| Unit A â‰  Unit D (separate models required) | Diverging water intensity trajectories 2022â€“2026 | âœ… Confirmed |
| Water âŠ¥ Chemical cost (orthogonal KPIs) | Pearson r(WI, Cost/kg) = +0.010 | âœ… Confirmed |
| Month encoding: cyclic required | Seasonal amplitude 32%; Decâ€“Jan continuity | âœ… Applied |

### Step 4: Prediction CLI

```bash
# Interactive recipe prediction
python 36_ai_predict.py \
  --unit Unit_A \
  --fabric "Single Jersey" \
  --gsm-cat "Medium (150-249)" \
  --shade "Light/Medium Colored" \
  --fabric-kg 350 \
  --liquor-ratio 7.0 \
  --month 6 --year 2026

# Output:
# Salt:   47.3 g/kg  (total: 16.6 kg)  [HIGH confidence, MAPE 8.3%]
# Dye:    32.1 g/kg  (total: 11.2 kg)  [MEDIUM confidence, MAPE 11.2%]
# Alkali: 18.7 g/kg  (total:  6.5 kg)  [HIGH confidence, MAPE 9.7%]
# Water:   8.4 L/kg  (total: 2940 L)   [HIGH confidence, MAPE 7.4%]
# âœ… All predictions within physical bounds
```

### Step 5: V3 Chemical Tokeniser â€” Ingredient-Level Prediction

The V3 system goes one level deeper â€” predicting **individual chemical ingredient quantities** using an NLP-inspired tokeniser that treats chemical formulation as a vocabulary:

```python
class ChemicalTokenizer:
    """
    Treats each chemical ingredient as a token in a recipe 'vocabulary'.
    Enables ingredient-level prediction across variable-length formulations.
    
    Analogy: Word2Vec for chemistry â€” each ingredient is a word,
    each recipe is a sentence, the quantity is the token weight.
    """
    
    def fit(self, recipes: list[dict]) -> None:
        """Build vocabulary from all ingredient names seen in training data."""
        all_ingredients: set[str] = set()
        for recipe in recipes:
            all_ingredients.update(recipe.keys())
        self.vocab = {ing: idx for idx, ing in enumerate(sorted(all_ingredients))}
        self.n_tokens = len(self.vocab)
    
    def transform(self, recipe: dict) -> np.ndarray:
        """Convert recipe dict â†’ fixed-length feature vector (bag-of-ingredients)."""
        vec = np.zeros(self.n_tokens, dtype=np.float32)
        for ingredient, quantity in recipe.items():
            if ingredient in self.vocab:
                vec[self.vocab[ingredient]] = float(quantity)
        return vec
    
    def inverse_transform(self, vec: np.ndarray, threshold: float = 0.01) -> dict:
        """Convert feature vector â†’ ingredient:quantity dict (filter near-zero)."""
        idx_to_ing = {v: k for k, v in self.vocab.items()}
        return {idx_to_ing[i]: float(vec[i]) 
                for i in np.where(vec > threshold)[0]}
```

---

## Closed-Loop System Design

```
Factory Process
     â†“
[Sensors: pH, temperature, conductivity, colour Î”E]
     â†“  Modbus TCP / OPC-UA
[PLC (SETEX / Sedomaster automation system)]
     â†“  REST API
[Production Management System (batch records)]
     â†“  Data ingestion pipeline
[AI Recipe Optimiser (this repository)]
     â†“
[Recipe Recommendation Engine]
     â†“  Feedback loop
[Process Adjustment â€” closed loop]
```

The `docs/PLC_AI_ClosedLoop_Review_FINAL.md` covers SETEX/Sedomaster automation systems, Modbus TCP communication, and the full signal chain for real-time closed-loop control.

---

## Technology Stack

| Layer | Technology |
|-------|-----------|
| **Data ingestion** | Python, Pandas, structured batch record parsing |
| **Database** | SQLite (stdlib `sqlite3`), Pandas DataFrames |
| **ML models** | scikit-learn, XGBoost, LightGBM |
| **Feature engineering** | Cyclic month encoding, log-transform, stratified splits |
| **Validation** | 80/20 stratified split, Welch's ANOVA, Pearson r, P25 benchmark |
| **Reporting** | Matplotlib, Plotly, custom HTML dashboards, `python-docx` |
| **PLC integration** | Design study: SETEX/Sedomaster PLC + Modbus TCP |

---

## Repository Map

```
00_AI-Closed-Loop-Dyeing-Bangladesh/
â”œâ”€â”€ README.md
â”œâ”€â”€ .gitignore                         â† Protects proprietary data from accidental commit
â”œâ”€â”€ 02_data_science_analysis/          â† Scripts 02â€“22 (validation, cleaning, rescue)
â”œâ”€â”€ 03_AI_recipe_optimizer/            â† Scripts 35â€“39 (training, prediction, benchmark)
â”œâ”€â”€ 04_AI_recipe_predictor_v3/         â† Scripts 01â€“04 (chemical tokeniser, V3 predictor)
â”œâ”€â”€ 05_categorization_insights/        â† Scripts 23â€“34 (dashboards, deep analysis)
â””â”€â”€ docs/
    â”œâ”€â”€ SMART_DYEING_Technical_Summary.md
    â”œâ”€â”€ PLC_AI_ClosedLoop_Review_FINAL.md  â† 95K-word technical literature review
    â”œâ”€â”€ SMART_DYEING_Inception_Report.md
    â””â”€â”€ Deep_Analysis_Findings.md
```

---

## Quick Start

```bash
# Install dependencies
pip install pandas numpy scikit-learn xgboost lightgbm matplotlib plotly python-docx

# Run data science pipeline (requires industrial batch dataset)
cd 02_data_science_analysis
python 02_trend_analysis.py          # Year-on-year trends
python 03_clustering_analysis.py     # Batch clustering (K-Means)

# Train the AI models
cd ../03_AI_recipe_optimizer
python 35_ai_train_pipeline.py       # Train 10 models (2 units Ã— 5 KPIs)

# Predict a recipe
python 36_ai_predict.py              # Interactive CLI

# V3: Ingredient-level prediction
cd ../04_AI_recipe_predictor_v3
python 01_chemical_tokenizer.py      # Build chemical vocabulary
python 03_train_v3_formulator.py     # Train V3 models
python 04_v3_recipe_generator_cli.py # Full ingredient-level prediction
```

> **Dataset note:** The proprietary industrial batch dataset is not included per the research collaboration agreement. Contact via the profile for academic collaboration enquiries.

---

## References & Documentation

1. [`docs/SMART_DYEING_Technical_Summary.md`](docs/SMART_DYEING_Technical_Summary.md) â€” Site baseline analysis and key metrics
2. [`docs/PLC_AI_ClosedLoop_Review_FINAL.md`](docs/PLC_AI_ClosedLoop_Review_FINAL.md) â€” 95K-word closed-loop control technical review
3. [`docs/SMART_DYEING_Inception_Report.md`](docs/SMART_DYEING_Inception_Report.md) â€” Project inception and design rationale

---

*Machine Learning Â· Industrial AI Â· Bangladesh Textiles Â· Smart Manufacturing Â· Closed-Loop Control Â· Python Â· XGBoost Â· LightGBM Â· Process Optimisation*

