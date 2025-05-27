import matplotlib.pyplot as plt
import pandas as pd
from datetime import datetime, timedelta
from io import StringIO
import requests

# === Fetch 6 months of CDC variant data ===
file_url = "https://data.cdc.gov/resource/jr58-6ysp.csv"
six_months_ago = (datetime.now() - timedelta(weeks=26)).strftime('%Y-%m-%d')

params = {
    "$limit": 1000,
    "$where": f"week_ending >= '{six_months_ago}' AND usa_or_hhsregion = 'USA'"
}
resp = requests.get(file_url, params=params)
df = pd.read_csv(StringIO(resp.text))

# === Preprocess ===
df['week_ending'] = pd.to_datetime(df['week_ending'])
df['share'] = pd.to_numeric(df['share'], errors='coerce')
df = df[df['share'] >= 0.01]

# Pivot and normalize by row
pivot_df = df.pivot_table(index='week_ending', columns='variant', values='share', aggfunc='sum').fillna(0)
pivot_df = pivot_df.div(pivot_df.sum(axis=1), axis=0)

# Keep only variants that ever exceeded 1% overall
variant_totals = pivot_df.sum()
variants_to_keep = variant_totals[variant_totals >= 0.01].index.tolist()
pivot_df = pivot_df[variants_to_keep]

# Sort variants so most recent ones stack top-down (visually)
pivot_df = pivot_df[pivot_df.iloc[-1].sort_values(ascending=True).index]

# === Plot ===
fig, ax = plt.subplots(figsize=(28, 12))
bar_width = 0.8

# Prepare bar positions and reset index for numeric access
pivot_df = pivot_df.reset_index()
bar_positions = range(len(pivot_df))
bottom = pd.Series([0.0] * len(pivot_df))  # Properly aligned to row index

# Draw bars with spacing and inline variant labels
for variant in pivot_df.columns[1:]:  # Skip 'week_ending'
    values = pivot_df[variant]
    ax.bar(bar_positions,
           values,
           bottom=bottom,
           width=bar_width,
           label=variant,
           align='center')

    # Label only large visible segments
    for i, val in enumerate(values):
        if pd.notna(val) and val > 0.05:
            ax.text(bar_positions[i],
                    bottom.iloc[i] + val / 2,
                    variant,
                    ha='center',
                    va='center',
                    fontsize=7,
                    rotation=90)

    bottom += values

# === Axis setup ===
ax.set_title("SARS-CoV-2 Variant Proportions (Last 6 Months, ≥1% Share)", fontsize=16)
ax.set_xlabel("Week Ending", fontsize=12)
ax.set_ylabel("Proportion (%)", fontsize=12)
ax.set_xticks(list(bar_positions)[::2])
ax.set_xticklabels(
    [d.strftime('%b %d') for d in pivot_df['week_ending'].iloc[::2]],
    rotation=45,
    ha='right'
)

# === Legend with percentages from latest week ===
handles, labels = ax.get_legend_handles_labels()

# Get final week's values
latest_values = pivot_df.iloc[-1, 1:]  # skip 'week_ending'

# Build label → "Variant (12%)"
labels_with_pct = [
    f"{label} ({latest_values[label]*100:.1f}%)" if label in latest_values else label
    for label in labels
]

# Reverse for top-down stack match
ax.legend(handles[::-1], labels_with_pct[::-1],
          title='Variants',
          bbox_to_anchor=(1.02, 1),
          loc='upper left',
          fontsize=9)


plt.grid(True, axis='y', linestyle='--', alpha=0.5)
plt.tight_layout()
plt.show()
