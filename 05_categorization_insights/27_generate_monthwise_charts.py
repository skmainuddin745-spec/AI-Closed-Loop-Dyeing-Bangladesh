import os
import csv
import json
from collections import defaultdict

BASE_DIR = r"E:\Downloads\01_Projects_and_Research\AI-driven closed-loop dyeing system for Bangladesh textiles"
IN_DIR = os.path.join(BASE_DIR, "2026-09-03_Categorization_Insights")
CSV_FILE = os.path.join(IN_DIR, "Monthwise_InDepth_Permutations_2021_2026.csv")
HTML_FILE = os.path.join(IN_DIR, "Monthwise_Permutation_Insights_Chart.html")

# Read data
data = defaultdict(lambda: defaultdict(int)) # data[month][permutation] = volume
perm_totals = defaultdict(int)
all_months = set()

with open(CSV_FILE, 'r', encoding='utf-8') as f:
    reader = csv.DictReader(f)
    for row in reader:
        m = row["Month"]
        perm = "{} | {} | {} | {}".format(row["Dye_Class"], row["Fabric_Category"], row["GSM_Category"], row["Shade_Category"])
        vol = int(row["Total_Batches"])
        
        data[m][perm] += vol
        perm_totals[perm] += vol
        all_months.add(m)

months = sorted(list(all_months))

# Get top 7 permutations by total volume to plot
top_perms = [k for k, v in sorted(perm_totals.items(), key=lambda x: x[1], reverse=True)[:7]]

datasets = []
colors = ['#e74c3c', '#3498db', '#f1c40f', '#2ecc71', '#9b59b6', '#34495e', '#e67e22']

for i, perm in enumerate(top_perms):
    ds_data = [data[m].get(perm, 0) for m in months]
    datasets.append({
        "label": perm,
        "data": ds_data,
        "borderColor": colors[i],
        "backgroundColor": colors[i] + "22", # Add transparency
        "borderWidth": 2,
        "tension": 0.3,
        "fill": True
    })

html_content = """<!DOCTYPE html>
<html>
<head>
    <title>Monthwise Permutation Insights (2021-2026)</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <style>
        body {{ font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background-color: #f8f9fa; padding: 20px; }}
        .chart-container {{ width: 95%; margin: 20px auto; background: white; padding: 20px; border-radius: 10px; box-shadow: 0 4px 6px rgba(0,0,0,0.1); }}
        h1 {{ text-align: center; color: #2c3e50; }}
        .insight-box {{ background: #e8f4f8; border-left: 4px solid #3498db; padding: 15px; margin: 20px auto; border-radius: 4px; font-size: 15px; color: #2c3e50; width: 95%; box-sizing: border-box; }}
    </style>
</head>
<body>
    <h1>Rigorous Analysis: Top 7 Dyeing Permutations Over Time (2021-2026)</h1>
    
    <div class="insight-box">
        <strong>In-Depth Insight:</strong> This chart tracks the factory's exact operational shifts over the last 5 years. By cross-tabulating <strong>Dye Chemistry × Fabric × GSM × Shade</strong>, we can see exactly which combinations drive seasonal demand. 
        Notice how <em>Reactive | Single Jersey | Medium | Dark</em> (Red Line) consistently dominates the baseline, but look for seasonal spikes in other categories (like Fleece/Heavy in winter months) to understand exactly how the factory's chemical load fluctuates chronologically.
    </div>

    <div class="chart-container">
        <canvas id="permChart" height="120"></canvas>
    </div>

    <script>
        const ctx = document.getElementById('permChart').getContext('2d');
        new Chart(ctx, {{
            type: 'line',
            data: {{
                labels: {months},
                datasets: {datasets}
            }},
            options: {{
                responsive: true,
                plugins: {{ 
                    title: {{ display: true, text: 'Monthly Volume of Top 7 Permutations', font: {{size: 18}} }},
                    legend: {{ position: 'bottom', labels: {{ padding: 20, font: {{size: 12}} }} }}
                }},
                scales: {{ 
                    x: {{ title: {{ display: true, text: 'Timeline (2021-2026)' }} }},
                    y: {{ stacked: false, beginAtZero: true, title: {{ display: true, text: 'Number of Batches Processed' }} }} 
                }}
            }}
        }});
    </script>
</body>
</html>
""".format(
    months=json.dumps(months),
    datasets=json.dumps(datasets)
)

out_file = os.path.join(IN_DIR, "Monthwise_Permutation_Insights_Chart.html")
with open(out_file, 'w', encoding='utf-8') as f:
    f.write(html_content)

print("Monthwise Permutation chart generated at:", out_file)
