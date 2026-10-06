import os
import csv
import json

BASE_DIR = r"E:\Downloads\01_Projects_and_Research\AI-driven closed-loop dyeing system for Bangladesh textiles"
IN_DIR = os.path.join(BASE_DIR, "2026-09-03_Categorization_Insights")
CSV_FILE = os.path.join(IN_DIR, "Time_Series_2021_2026.csv")
HTML_FILE = os.path.join(IN_DIR, "2021_2026_Production_Dashboard.html")

months = []
Unit_A = []
Unit_D = []
Unit_C = []
kg = []

with open(CSV_FILE, 'r', encoding='utf-8') as f:
    reader = csv.DictReader(f)
    for row in reader:
        if row["Month"] != "Unknown":
            months.append(row["Month"])
            Unit_A.append(int(row["Unit_A_Count"]))
            Unit_D.append(int(row["Unit_D_Count"]))
            Unit_C.append(int(row["Unit_C_Count"]))
            kg.append(float(row["Total_Fabric_Kg"]) / 1000) # Convert to Tons

html_content = """<!DOCTYPE html>
<html>
<head>
    <title>2021-2026 Production Time Series</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <style>
        body {{ font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background-color: #f8f9fa; padding: 20px; }}
        .chart-container {{ width: 80%; margin: 20px auto; background: white; padding: 20px; border-radius: 10px; box-shadow: 0 4px 6px rgba(0,0,0,0.1); }}
        h1 {{ text-align: center; color: #2c3e50; }}
    </style>
</head>
<body>
    <h1>Historical Production Volumes (2021-2026)</h1>
    
    <div class="chart-container">
        <canvas id="batchChart"></canvas>
    </div>
    
    <div class="chart-container">
        <canvas id="fabricChart"></canvas>
    </div>

    <script>
        const ctxBatch = document.getElementById('batchChart').getContext('2d');
        const batchChart = new Chart(ctxBatch, {{
            type: 'line',
            data: {{
                labels: {months},
                datasets: [
                    {{
                        label: 'Unit_A (Cotton)',
                        data: {Unit_A},
                        borderColor: '#3498db',
                        backgroundColor: 'rgba(52, 152, 219, 0.1)',
                        borderWidth: 2,
                        tension: 0.3,
                        fill: true
                    }},
                    {{
                        label: 'Unit_D (Blends)',
                        data: {Unit_D},
                        borderColor: '#e67e22',
                        backgroundColor: 'rgba(230, 126, 34, 0.1)',
                        borderWidth: 2,
                        tension: 0.3,
                        fill: true
                    }},
                    {{
                        label: 'Unit_C (Polyester)',
                        data: {Unit_C},
                        borderColor: '#2ecc71',
                        backgroundColor: 'rgba(46, 204, 113, 0.1)',
                        borderWidth: 2,
                        tension: 0.3,
                        fill: true
                    }}
                ]
            }},
            options: {{
                responsive: true,
                plugins: {{ title: {{ display: true, text: 'Monthly Batch Production (Count)', font: {{size: 18}} }} }},
                scales: {{ y: {{ beginAtZero: true, title: {{ display: true, text: 'Number of Batches' }} }} }}
            }}
        }});

        const ctxFabric = document.getElementById('fabricChart').getContext('2d');
        const fabricChart = new Chart(ctxFabric, {{
            type: 'line',
            data: {{
                labels: {months},
                datasets: [
                    {{
                        label: 'Total Fabric (Metric Tons)',
                        data: {kg},
                        borderColor: '#9b59b6',
                        backgroundColor: 'rgba(155, 89, 182, 0.3)',
                        borderWidth: 3,
                        tension: 0.3,
                        fill: true
                    }}
                ]
            }},
            options: {{
                responsive: true,
                plugins: {{ title: {{ display: true, text: 'Monthly Fabric Production (Tons)', font: {{size: 18}} }} }},
                scales: {{ y: {{ beginAtZero: true, title: {{ display: true, text: 'Tons' }} }} }}
            }}
        }});
    </script>
</body>
</html>
""".format(
    months=json.dumps(months),
    Unit_A=json.dumps(Unit_A),
    Unit_D=json.dumps(Unit_D),
    Unit_C=json.dumps(Unit_C),
    kg=json.dumps(kg)
)

with open(HTML_FILE, 'w', encoding='utf-8') as f:
    f.write(html_content)

print("Interactive HTML dashboard successfully generated at:", HTML_FILE)


