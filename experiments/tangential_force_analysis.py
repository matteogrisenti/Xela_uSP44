import pandas as pd
import matplotlib
matplotlib.use('TkAgg') # Ensures the window opens cleanly on Ubuntu Wayland
import matplotlib.pyplot as plt
import sys
import argparse
import os

# 1. Terminal Argument Configuration
parser = argparse.ArgumentParser(description="XELA Tangential Force (X/Y-Axis) Analyzer")
parser.add_argument("filename", help="Name of the CSV file containing the touch recording")
parser.add_argument("--folder", default="csv_records/", help="Path to the folder containing the CSV")
parser.add_argument("--axis", choices=['X', 'x', 'Y', 'y'], default='X', help="Choose which tangential axis to analyze: X (Left/Right) or Y (Forward/Backward)")
# ----------------------
args = parser.parse_args()

target_axis = args.axis.upper()
csv_path = os.path.join(args.folder, args.filename)

print(f"Loading Tangential Force ({target_axis}-Axis) data from: {csv_path}")

try:
    df = pd.read_csv(csv_path)
except FileNotFoundError:
    print(f"Error: Could not find {csv_path}.")
    sys.exit()

df.columns = df.columns.str.strip()

# Time synchronization
time_cols = [col for col in df.columns if 'time' in col.lower()]
time_col_name = time_cols[0] if time_cols else df.columns[0]
df['relative_time'] = df[time_col_name] - df.iloc[0][time_col_name]

# Baseline zeroing (Average of the first 20 frames to eliminate idle offset)
num_baseline_frames = min(20, len(df))
baseline = df.iloc[0:num_baseline_frames].mean(numeric_only=True)

def get_tangential_data(row, idx, axis):
    """Fetches X or Y axis data, prioritizing calibrated Force if available."""
    force_col = f"Force {idx}{axis}"
    if force_col in row:
        return row[force_col], "Force (N)"
    raw_col = f"{idx}{axis}"
    if raw_col in row:
        return row[raw_col], "Raw Ticks"
    return 0.0, "Unknown"

# Extract data for all 16 cells
time_data = df['relative_time']
tangential_data_all = {}
y_label = "Force (N)"

for i in range(1, 17):
    # Get raw data column and baseline for the selected axis
    val_t, unit = get_tangential_data(df, i, target_axis)
    base_t, _ = get_tangential_data(baseline, i, target_axis)
    
    y_label = unit
    
    # Calculate zeroed tangential force
    tangential_data_all[i] = val_t - base_t

# ==========================================
# VISUALIZATION 1: 16 Individual Subplots
# ==========================================
fig1, axes = plt.subplots(4, 4, figsize=(14, 10), sharex=True, sharey=True)
fig1.canvas.manager.set_window_title(f'Tangential Force ({target_axis}) - 16 Channel Grid')
fig1.suptitle(f'Tangential Force ({target_axis}-Axis) per Taxel', fontsize=16, fontweight='bold')

colors = plt.cm.tab20.colors 

for i in range(1, 17):
    row = (i - 1) // 4
    col = (i - 1) % 4
    ax = axes[row, col]
    
    ax.plot(time_data, tangential_data_all[i], color=colors[(i-1)%20], linewidth=1.5)
    ax.set_title(f'Taxel {i}', fontsize=10)
    ax.grid(True, linestyle='--', alpha=0.6)
    
    # Add a zero line for reference
    ax.axhline(0, color='black', linewidth=0.8, linestyle='--')

# Set common labels
for ax in axes.flat:
    ax.set(xlabel='Time (s)', ylabel=y_label)
for ax in axes.flat:
    ax.label_outer()

fig1.tight_layout()
fig1.subplots_adjust(top=0.92)

# ==========================================
# VISUALIZATION 2: Overlaid Global Plot
# ==========================================
fig2, ax_main = plt.subplots(figsize=(12, 6))
fig2.canvas.manager.set_window_title(f'Tangential Force ({target_axis}) - Overlaid Channels')

for i in range(1, 17):
    ax_main.plot(time_data, tangential_data_all[i], label=f'Taxel {i}', color=colors[(i-1)%20], linewidth=1.5, alpha=0.8)

ax_main.axhline(0, color='black', linewidth=1.5, linestyle='--')
ax_main.set_title(f'Global Tangential Force ({target_axis}-Axis) (All Channels Overlaid)', fontsize=14, fontweight='bold')
ax_main.set_xlabel('Time (s)', fontsize=12)
ax_main.set_ylabel(y_label, fontsize=12)
ax_main.grid(True, linestyle='--', alpha=0.6)

# Put legend outside the plot
ax_main.legend(loc='center left', bbox_to_anchor=(1, 0.5), fontsize=9)
fig2.tight_layout()

# Show both windows simultaneously
plt.show()