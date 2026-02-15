import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
import os

# Read the CSV file
df = pd.read_csv('/results/evaluation_metrics.csv')

# Calculate average metrics for each method
methods = ['BM25', 'Fuzzy', 'Semantic', 'Hybrid']
p10 = []
r50 = []
ndcg = []
mrr = []

for method in methods:
    method_data = df[df['method'] == method]
    p10.append(method_data['precision@10'].mean())
    r50.append(method_data['recall@50'].mean())
    ndcg.append(method_data['ndcg@10'].mean())
    mrr.append(method_data['mrr'].mean())

# Print the actual values for reference
print("Actual Metric Values:")
print(f"{'Method':<10} {'P@10':<10} {'R@50':<10} {'nDCG@10':<10} {'MRR':<10}")
print("-" * 50)
for i, method in enumerate(methods):
    print(f"{method:<10} {p10[i]:<10.4f} {r50[i]:<10.4f} {ndcg[i]:<10.4f} {mrr[i]:<10.4f}")

# Create the plot
x = np.arange(len(methods))
width = 0.2

fig, ax = plt.subplots(figsize=(10, 6))
ax.bar(x - 1.5*width, p10, width, label='P@10', color='#2196F3')
ax.bar(x - 0.5*width, r50, width, label='R@50', color='#4CAF50')
ax.bar(x + 0.5*width, ndcg, width, label='nDCG@10', color='#FF9800')
ax.bar(x + 1.5*width, mrr, width, label='MRR', color='#9C27B0')

ax.set_ylabel('Score')
ax.set_title('IR Metrics Comparison Across Retrieval Methods')
ax.set_xticks(x)
ax.set_xticklabels(methods)
ax.legend()
ax.set_ylim(0, 1.0)
ax.axhline(y=0.5, color='red', linestyle='--', alpha=0.5, label='Target baseline')
plt.tight_layout()

# Create report/figures directory if it doesn't exist
os.makedirs('/report/figures', exist_ok=True)

# Save the figure
plt.savefig('/report/figures/metrics_comparison.png', dpi=150)
print("\nPlot saved to: /report/figures/metrics_comparison.png")
plt.show()