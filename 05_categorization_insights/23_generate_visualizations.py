import os
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns

BASE_DIR = r"E:\Downloads\01_Projects_and_Research\AI-driven closed-loop dyeing system for Bangladesh textiles"
IN_DIR = os.path.join(BASE_DIR, "2026-09-03_Categorization_Insights")
OUT_DIR = IN_DIR

# Set seaborn style for beautiful manuscript-ready charts
sns.set(style="whitegrid", context="talk")

# --- 1. Time Series Plot (2021-2026) ---
print("Generating Time Series Chart...")
ts_file = os.path.join(IN_DIR, "Time_Series_2021_2026.csv")
df_ts = pd.read_csv(ts_file)

# Convert Month to datetime
df_ts['Month'] = pd.to_datetime(df_ts['Month'], errors='coerce')
df_ts = df_ts.dropna(subset=['Month']).sort_values('Month')

plt.figure(figsize=(14, 7))
plt.plot(df_ts['Month'], df_ts['Unit_A_Count'], label='Unit_A (Cotton)', color='#1f77b4', linewidth=2.5)
plt.plot(df_ts['Month'], df_ts['Unit_D_Count'], label='Unit_D (Blends)', color='#ff7f0e', linewidth=2.5)
plt.plot(df_ts['Month'], df_ts['Unit_C_Count'], label='Unit_C (Polyester)', color='#2ca02c', linewidth=2.5)

plt.title('Monthly Batch Production Volume (2021-2026)', fontsize=18, fontweight='bold', pad=15)
plt.xlabel('Year', fontsize=14)
plt.ylabel('Number of Batches Processed', fontsize=14)
plt.legend(title='Dyeing Unit', fontsize=12, title_fontsize=13, loc='upper left')
plt.tight_layout()
ts_out = os.path.join(OUT_DIR, "Chart_TimeSeries_Production.png")
plt.savefig(ts_out, dpi=300)
plt.close()

# --- 2. Fabric Qty Time Series Plot ---
plt.figure(figsize=(14, 7))
plt.plot(df_ts['Month'], df_ts['Total_Fabric_Kg'] / 1000, label='Total Fabric (Tons)', color='#9467bd', linewidth=3)
plt.fill_between(df_ts['Month'], df_ts['Total_Fabric_Kg'] / 1000, color='#9467bd', alpha=0.2)

plt.title('Monthly Fabric Production (Metric Tons)', fontsize=18, fontweight='bold', pad=15)
plt.xlabel('Year', fontsize=14)
plt.ylabel('Fabric Processed (Tons)', fontsize=14)
plt.tight_layout()
kg_out = os.path.join(OUT_DIR, "Chart_TimeSeries_FabricKg.png")
plt.savefig(kg_out, dpi=300)
plt.close()

print("Charts successfully generated in:", OUT_DIR)


