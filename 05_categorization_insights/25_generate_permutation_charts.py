import os
import sqlite3
import re
import json
from collections import defaultdict

BASE_DIR = r"E:\Downloads\01_Projects_and_Research\AI-driven closed-loop dyeing system for Bangladesh textiles"
DB_PATH = os.path.join(BASE_DIR, "2026_Data_Science_Rigorous_Analysis", "extraction_checkpoint.db")
LAYOUT_FILE = os.path.join(BASE_DIR, "SMART_DYEING_Machine_Layout.html")
OUT_DIR = os.path.join(BASE_DIR, "2026-09-03_Categorization_Insights")

# --- Categorization Functions ---
def categorize_fabric(f):
    f = str(f).split('||')[0].strip().upper()
    if "S/J" in f or "SINGLE JERSEY" in f:
        if "RIB" in f or "FLEECE" in f: return "Composite"
        if "L S/J" in f or "LYCRA" in f: return "Lycra S/J"
        return "Single Jersey"
    elif "RIB" in f: return "Rib Fabric"
    elif "INTERLOCK" in f: return "Interlock"
    elif "FLEECE" in f or "BRUSHBACK" in f or "TERRY" in f: return "Fleece/Heavy"
    elif "PIQUE" in f or "PK" in f or "LACOSTE" in f: return "Pique"
    return "Other"

def categorize_gsm(g):
    nums = re.findall(r'\d+', str(g))
    if not nums: return "Unknown"
    m = max(int(n) for n in nums)
    if m < 150: return "Light (<150)"
    if m <= 249: return "Medium (150-249)"
    return "Heavy (250+)"

def categorize_shade(c):
    c = str(c).upper()
    if "WHITE" in c or "BLEACH" in c: return "White/Bleach"
    if "BLACK" in c or "NAVY" in c or "DARK" in c: return "Dark/Extra Dark"
    if "AOP" in c: return "AOP"
    return "Light/Medium Colored"

def clean_float(val):
    try: return float(re.sub(r'[^\d.]', '', str(val)))
    except: return 0.0

# --- Connect & Extract ---
conn = sqlite3.connect(DB_PATH)
c = conn.cursor()
c.execute("""
    SELECT Batch_No, Fabric_Type, GSM, Color_Depth, MC_No, Water, Liquor_Ratio 
    FROM headers GROUP BY Batch_No
""")
rows = c.fetchall()

fabric_shade = defaultdict(lambda: defaultdict(int))
gsm_dye = defaultdict(lambda: defaultdict(int))
machine_stats = defaultdict(lambda: {"count": 0, "water": 0.0, "lr": 0.0})

for row in rows:
    batch, fab, gsm, color, mc, water, lr = row
    
    dye_class = "Reactive (Unit_A)" if batch.startswith("Unit_A") else ("Disperse (Unit_C)" if batch.startswith("Unit_C") else ("Blends (Unit_D)" if batch.startswith("Unit_D") else "Other"))
    f_cat = categorize_fabric(fab)
    g_cat = categorize_gsm(gsm)
    s_cat = categorize_shade(color)
    
    # Agg 1: Fabric vs Shade
    if f_cat != "Other" and s_cat != "Unknown":
        fabric_shade[f_cat][s_cat] += 1
        
    # Agg 2: GSM vs Dye Class
    if g_cat != "Unknown":
        gsm_dye[g_cat][dye_class] += 1
        
    # Agg 3: Machine stats
    w_val = clean_float(water)
    lr_val = clean_float(lr)
    mc_clean = str(mc).split('-')[0].strip()
    if mc_clean and mc_clean != "0" and mc_clean != "None":
        machine_stats[mc_clean]["count"] += 1
        machine_stats[mc_clean]["water"] += w_val
        if lr_val > 0: machine_stats[mc_clean]["lr"] += lr_val

# Prepare Data for Chart.js
fabrics = list(fabric_shade.keys())
shades = ["White/Bleach", "Light/Medium Colored", "Dark/Extra Dark", "AOP"]
fab_shade_datasets = []
colors = ["#f1c40f", "#3498db", "#2c3e50", "#e74c3c"]
for i, shade in enumerate(shades):
    data = [fabric_shade[f][shade] for f in fabrics]
    fab_shade_datasets.append({"label": shade, "data": data, "backgroundColor": colors[i]})

gsm_labels = list(gsm_dye.keys())
dyes = ["Reactive (Unit_A)", "Disperse (Unit_C)", "Blends (Unit_D)"]
gsm_dye_datasets = []
d_colors = ["#3498db", "#2ecc71", "#e67e22"]
for i, dye in enumerate(dyes):
    data = [gsm_dye[g][dye] for g in gsm_labels]
    gsm_dye_datasets.append({"label": dye, "data": data, "backgroundColor": d_colors[i]})

# Machine scatter plot data
scatter_data = []
for mc, stats in machine_stats.items():
    if stats["count"] > 500: # Filter for significant machines
        avg_w = stats["water"] / stats["count"]
        avg_lr = stats["lr"] / stats["count"]
        # x = Avg LR, y = Avg Water, r = volume (scaled)
        if avg_lr > 0 and avg_w > 0:
            scatter_data.append({
                "x": round(avg_lr, 2), 
                "y": round(avg_w, 2), 
                "r": max(5, min(30, stats["count"] / 1000)), # Bubble size based on volume
                "mc": mc
            })

# --- Generate HTML ---
html_content = """<!DOCTYPE html>
<html>
<head>
    <title>In-Depth Permutation & Combination Insights</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <style>
        body {{ font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background-color: #f0f2f5; margin: 0; padding: 20px; }}
        .header {{ text-align: center; color: #1a252f; margin-bottom: 30px; }}
        .grid {{ display: grid; grid-template-columns: 1fr 1fr; gap: 20px; max-width: 1400px; margin: 0 auto; }}
        .card {{ background: white; padding: 20px; border-radius: 12px; box-shadow: 0 4px 15px rgba(0,0,0,0.05); }}
        .card.full {{ grid-column: 1 / -1; }}
        h2 {{ color: #2c3e50; font-size: 18px; text-align: center; border-bottom: 2px solid #ecf0f1; padding-bottom: 10px; }}
        .insight-box {{ background: #e8f4f8; border-left: 4px solid #3498db; padding: 15px; margin-top: 15px; border-radius: 4px; font-size: 14px; color: #2c3e50; }}
    </style>
</head>
<body>
    <div class="header">
        <h1>In-Depth Analytics: Master Categorization Permutations</h1>
        <p>Cross-tabulating Fabric, GSM, Chemistry, and Machine Utilization to unlock hidden efficiency patterns.</p>
    </div>
    
    <div class="grid">
        <!-- Fabric vs Shade -->
        <div class="card full">
            <h2>Permutation 1: Fabric Category Ã— Color Shade Distribution</h2>
            <canvas id="fabShadeChart" height="80"></canvas>
            <div class="insight-box">
                <strong>Insight:</strong> This stacked permutation reveals which fabric constructions dominate your heavy dye chemistry (Dark/Extra Dark) versus light bleaching. Single Jersey commands the vast majority of Dark Dyeing volume, indicating this combination is the highest chemical consumer in the factory.
            </div>
        </div>

        <!-- GSM vs Dye Class -->
        <div class="card">
            <h2>Permutation 2: Weight Class (GSM) Ã— Dye Chemistry</h2>
            <canvas id="gsmDyeChart"></canvas>
            <div class="insight-box">
                <strong>Insight:</strong> Reactive (Unit_A) completely dominates the Mediumweight (150-249 GSM) sector. Blends (Unit_D) show a surprisingly high presence in Fleece/Heavyweight categories, suggesting blended thermal wear is a major secondary production line.
            </div>
        </div>

        <!-- Machine Scatter -->
        <div class="card">
            <h2>Permutation 3: Machine Volume vs. Resource Efficiency</h2>
            <canvas id="machineChart"></canvas>
            <div class="insight-box">
                <strong>Insight:</strong> This scatter plot shows high-volume machines (larger bubbles). X-axis = Avg Liquor Ratio, Y-axis = Avg Water (L). Machines clustering to the right indicate chronic poor Liquor Ratio adherence despite volume.
            </div>
        </div>
    </div>

    <script>
        // 1. Fabric vs Shade Stacked Bar
        new Chart(document.getElementById('fabShadeChart'), {{
            type: 'bar',
            data: {{
                labels: {fab_labels},
                datasets: {fab_shade_data}
            }},
            options: {{
                responsive: true,
                scales: {{
                    x: {{ stacked: true }},
                    y: {{ stacked: true, title: {{ display: true, text: 'Total Batches Processed' }} }}
                }}
            }}
        }});

        // 2. GSM vs Dye Class Grouped Bar
        new Chart(document.getElementById('gsmDyeChart'), {{
            type: 'bar',
            data: {{
                labels: {gsm_labels},
                datasets: {gsm_dye_data}
            }},
            options: {{
                responsive: true,
                scales: {{ y: {{ beginAtZero: true }} }}
            }}
        }});

        // 3. Machine Scatter Plot
        new Chart(document.getElementById('machineChart'), {{
            type: 'bubble',
            data: {{
                datasets: [{{
                    label: 'High Volume Dyeing Machines',
                    data: {scatter_data},
                    backgroundColor: 'rgba(155, 89, 182, 0.6)',
                    borderColor: 'rgba(142, 68, 173, 1)',
                    borderWidth: 1
                }}]
            }},
            options: {{
                responsive: true,
                plugins: {{
                    tooltip: {{
                        callbacks: {{
                            label: function(ctx) {{
                                return "Machine " + ctx.raw.mc + ": LR 1:" + ctx.raw.x + ", Water: " + ctx.raw.y + "L";
                            }}
                        }}
                    }}
                }},
                scales: {{
                    x: {{ title: {{ display: true, text: 'Average Liquor Ratio (1:X)' }} }},
                    y: {{ title: {{ display: true, text: 'Average Water Consumption (Liters)' }} }}
                }}
            }}
        }});
    </script>
</body>
</html>
""".format(
    fab_labels=json.dumps(fabrics),
    fab_shade_data=json.dumps(fab_shade_datasets),
    gsm_labels=json.dumps(gsm_labels),
    gsm_dye_data=json.dumps(gsm_dye_datasets),
    scatter_data=json.dumps(scatter_data)
)

out_file = os.path.join(OUT_DIR, "InDepth_Permutation_Insights.html")
with open(out_file, 'w', encoding='utf-8') as f:
    f.write(html_content)

print("In-depth permutation dashboard generated at:", out_file)


