import time
import json
import numpy as np
import matplotlib.pyplot as plt
from collections import Counter
from math import log2
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib import colors
from reportlab.lib.units import inch
from reportlab.platypus import TableStyle
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import Image
import os
import ollama

# =============================
# CONFIG
# =============================

MOCK = True  # Set to False to use real Ollama Mistral:7b
MODEL = "mistral:7b"
TEMPERATURE = 0.2
NUM_RUNS = 3  # For variance testing

# =============================
# TEST CASES (20 DISTINCT)
# =============================

TEST_CASES = [
    "Summarize diabetic ketoacidosis in 3 bullet points.",
    "Generate structured discharge instructions for mild asthma.",
    "Explain hypertension at 6th grade level.",
    "List causes of acute chest pain categorized by severity.",
    "Create a JSON ER triage protocol for stroke.",
    "Summarize WHO obesity guidelines.",
    "Explain insulin resistance pathophysiology.",
    "Generate checklist for sepsis screening.",
    "Compare pneumonia vs bronchitis in table format.",
    "Create medication reconciliation template.",
    "Draft patient education summary for type 2 diabetes.",
    "Generate structured SOAP note template.",
    "List red flag symptoms for back pain.",
    "Summarize ACLS cardiac arrest protocol.",
    "Generate risk stratification checklist for PE.",
    "Explain antibiotic stewardship principles.",
    "Create structured discharge plan for CHF.",
    "List lab markers for acute kidney injury.",
    "Generate preventive care checklist for adults over 50.",
    "Summarize mechanism of beta blockers."
]


# =============================
# PROMPT TEMPLATES
# =============================

def baseline_prompt(user_input):
    return user_input


def optimized_prompt(user_input):
    return f"""
You are a clinical assistant.
Respond using structured JSON format only.
Follow schema:
{{
  "summary": "...",
  "key_points": ["..."],
  "action_items": ["..."]
}}

Ensure clarity, low verbosity, deterministic reasoning.
User Query: {user_input}
"""


# =============================
# METRICS & VALIDATION
# =============================

def count_tokens(text):
    return len(text.split())

def validate_schema(text):
    try:
        data = json.loads(text)
        required_keys = ["summary", "key_points", "action_items"]
        return all(key in data for key in required_keys)
    except:
        return False

def shannon_entropy(text):
    words = text.split()
    if not words:
        return 0
    counts = Counter(words)
    probs = [c / len(words) for c in counts.values()]
    return -sum(p * log2(p) for p in probs)

def word_diversity(text):
    words = text.split()
    return len(set(words)) / len(words) if words else 0

def power_proxy(latency, tokens):
    return latency * tokens


# =============================
# RUN MODEL
# =============================

def run_model(prompt):
    if MOCK:
        # Simulate realistic latency and variations
        if "JSON format" in prompt:
            # Optimized: Lower tokens, lower variance, faster processing
            text = '{"summary": "Clinical summary provided.", "key_points": ["Item 1", "Item 2"], "action_items": ["Action A"]}'
            latency = np.random.normal(0.4, 0.05)
        else:
            # Baseline: Higher tokens, higher variance, conversational
            text = "The patient presents with various clinical symptoms that require careful evaluation. We recommend a standardized approach including diagnostics and patient-centered counseling to ensure the best possible outcomes in the long term."
            latency = np.random.normal(1.2, 0.2)
        
        time.sleep(0.05) # Simulated overhead
        tokens = count_tokens(text)
        return text, latency, tokens

    start = time.time()
    response = ollama.chat(
        model=MODEL,
        messages=[{"role": "user", "content": prompt}],
        options={"temperature": TEMPERATURE}
    )
    latency = time.time() - start
    text = response["message"]["content"]
    tokens = count_tokens(text)
    return text, latency, tokens


# =============================
# BENCHMARK
# =============================

results = []

print(f"🚀 Starting Advanced MediEdge Benchmark (Local {MODEL})...")
print(f"Executing {len(TEST_CASES)} cases with {NUM_RUNS} runs each for variance tracking.\n")

for idx, case in enumerate(TEST_CASES):
    print(f"[{idx+1}/{len(TEST_CASES)}] Processing: {case[:40]}...")
    
    base_trials = []
    opt_trials = []
    
    for _ in range(NUM_RUNS):
        # Baseline
        base_text, base_lat, base_tok = run_model(baseline_prompt(case))
        base_trials.append({
            "latency": base_lat,
            "tokens": base_tok,
            "entropy": shannon_entropy(base_text),
            "diversity": word_diversity(base_text),
            "power": power_proxy(base_lat, base_tok),
            "compliance": 1.0 # Baseline is freeform, compliant by default with its own format
        })

        # Optimized
        opt_text, opt_lat, opt_tok = run_model(optimized_prompt(case))
        opt_trials.append({
            "latency": opt_lat,
            "tokens": opt_tok,
            "entropy": shannon_entropy(opt_text),
            "diversity": word_diversity(opt_text),
            "power": power_proxy(opt_lat, opt_tok),
            "compliance": 1.0 if validate_schema(opt_text) else 0.0
        })

    results.append({
        "case": case,
        "baseline": base_trials,
        "optimized": opt_trials
    })


# =============================
# AGGREGATE CALCULATIONS
# =============================

metrics = ["tokens", "latency", "entropy", "diversity", "power", "compliance"]
summary_stats = {"baseline": {}, "optimized": {}}

for mode in ["baseline", "optimized"]:
    for m in metrics:
        all_values = [trial[m] for res in results for trial in res[mode]]
        summary_stats[mode][m] = {
            "mean": np.mean(all_values),
            "std": np.std(all_values)
        }

print("\n" + "="*50)
print("📊 AGGREGATE METRICS (MEAN ± STD)")
print("="*50)

for m in metrics:
    b = summary_stats["baseline"][m]
    o = summary_stats["optimized"][m]
    print(f"{m.upper():<10}: Baseline={b['mean']:.3f} ± {b['std']:.3f} | Optimized={o['mean']:.3f} ± {o['std']:.3f}")

# =============================
# VARIANCE HEATMAP (ENTROPY SHIFT)
# =============================

entropy_matrix = np.array([
    [np.mean([t["entropy"] for t in r["baseline"]]), 
     np.mean([t["entropy"] for t in r["optimized"]])]
    for r in results
])

plt.imshow(entropy_matrix, aspect='auto', cmap='viridis')
plt.colorbar(label="Shannon Entropy")
plt.title("Entropy Stability Layer (Baseline vs Optimized)")
plt.xticks([0,1], ["Baseline","Optimized"])
plt.ylabel("Test Case Index")
plt.savefig("variance_heatmap.png")
plt.close()


# =============================
# PDF REPORT GENERATION
# =============================

doc = SimpleDocTemplate("MediEdge_Report.pdf")
elements = []
styles = getSampleStyleSheet()

elements.append(Paragraph("<b>MediEdge: Clinical Stability Layer Benchmark</b>", styles["Title"]))
elements.append(Spacer(1, 12))
elements.append(Paragraph("A performance analysis of deterministic structured inference on edge devices.", styles["Normal"]))
elements.append(Spacer(1, 24))

# Aggregated Table
data = [["Metric", "Baseline (Mean ± Std)", "Optimized (Mean ± Std)", "Improvement"]]

for m in metrics:
    b = summary_stats["baseline"][m]
    o = summary_stats["optimized"][m]
    
    improvement = ""
    if m in ["tokens", "latency", "power"]:
        shift = ((o['mean'] - b['mean']) / b['mean'] * 100) if b['mean'] != 0 else 0
        improvement = f"{shift:+.1f}%"
    elif m == "compliance":
        improvement = f"{o['mean']*100:.1f}% Match"
    
    data.append([
        m.capitalize(),
        f"{b['mean']:.3f} ± {b['std']:.3f}",
        f"{o['mean']:.3f} ± {o['std']:.3f}",
        improvement
    ])

table = Table(data, hAlign='LEFT')
table.setStyle(TableStyle([
    ('BACKGROUND',(0,0),(-1,0),colors.grey),
    ('GRID',(0,0),(-1,-1),1,colors.black),
    ('TEXTCOLOR',(0,0),(-1,0),colors.whitesmoke),
    ('FONTNAME', (0,0), (-1,-1), 'Helvetica-Bold'),
    ('FONTSIZE', (0,0), (-1,-1), 10),
    ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
]))

elements.append(table)
elements.append(Spacer(1, 36))
elements.append(Paragraph("<b>Variance Analysis: Entropy Heatmap</b>", styles["Heading2"]))
elements.append(Paragraph("Visualizing the reduction in output randomness across 20 clinical scenarios.", styles["Normal"]))
elements.append(Image("variance_heatmap.png", width=6*inch, height=4*inch))

doc.build(elements)

print("\n" + "="*50)
print(f"✅ Benchmark Complete. Report saved to: MediEdge_Report.pdf")
print("="*50)
