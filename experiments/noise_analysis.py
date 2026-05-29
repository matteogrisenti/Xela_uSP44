import pandas as pd
import numpy as np
import argparse
import sys
import os

# 1. Argument Configuration
parser = argparse.ArgumentParser(description="XELA Sensor Noise Analyzer")
parser.add_argument("filename", help="Name of the CSV file (recorded WITHOUT touching the sensor)")
parser.add_argument("--folder", default="csv_records/", help="Path to the folder containing the CSV")
args = parser.parse_args()

csv_path = os.path.join(args.folder, args.filename)
print(f"Analyzing noise from file: {csv_path}\n")

try:
    df = pd.read_csv(csv_path)
except FileNotFoundError:
    print(f"Error: Could not find {csv_path}.")
    sys.exit()

df.columns = df.columns.str.strip()

# Data structures for the results
results = []
axes = ['X', 'Y', 'Z']
data_types = [('Raw', ''), ('Force', 'Force ')] # (Label, CSV Prefix)

# 2. Cell-by-Cell Analysis (1-16)
for i in range(1, 17):
    for typ_label, prefix in data_types:
        for axis in axes:
            col_name = f"{prefix}{i}{axis}"
            
            if col_name in df.columns:
                data = df[col_name]
                
                mean_val = data.mean()
                std_val = data.std()
                threshold = 3 * std_val
                
                results.append({
                    'Cell': f"{i:02d}",
                    'Type': typ_label,
                    'Axis': axis,
                    'Mean': mean_val,
                    'Std (Noise)': std_val,
                    'Threshold (3xStd)': threshold
                })

# 3. Global Analysis (All cells combined)
for typ_label, prefix in data_types:
    for axis in axes:
        # Find all columns related to this axis and type (e.g., all 'Force *Z')
        cols = [f"{prefix}{i}{axis}" for i in range(1, 17) if f"{prefix}{i}{axis}" in df.columns]
        
        if cols:
            subset = df[cols]
            
            # Calculate the absolute global mean
            global_mean = subset.values.flatten().mean()
            
            # CRITICAL: To calculate the true global noise, we must subtract the individual 
            # mean of each cell first. Otherwise, the Std would measure the physical offset 
            # differences between the cells rather than the actual temporal fluctuation (noise).
            zero_mean_data = subset - subset.mean()
            global_noise_std = zero_mean_data.values.flatten().std()
            global_threshold = 3 * global_noise_std
            
            results.append({
                'Cell': 'GLOBAL',
                'Type': typ_label,
                'Axis': axis,
                'Mean': global_mean,
                'Std (Noise)': global_noise_std,
                'Threshold (3xStd)': global_threshold
            })

# 4. Create DataFrame and Format Output
res_df = pd.DataFrame(results)

# Separate Global and Individual stats for printing
global_df = res_df[res_df['Cell'] == 'GLOBAL'].copy()
cells_df = res_df[res_df['Cell'] != 'GLOBAL'].copy()

print("="*60)
print(" 🌍 GLOBAL NOISE SUMMARY (All 16 cells combined)")
print("="*60)
# Formatting for terminal output
pd.options.display.float_format = '{:.5f}'.format
print(global_df.to_string(index=False))
print("\n")

print("="*60)
print(" 🔬 WORST FLUCTUATIONS DETAIL (Max 3xStd per Axis)")
print("="*60)
for typ_label in ['Raw', 'Force']:
    for axis in axes:
        mask = (cells_df['Type'] == typ_label) & (cells_df['Axis'] == axis)
        if mask.any():
            worst_cell = cells_df[mask].loc[cells_df[mask]['Threshold (3xStd)'].idxmax()]
            print(f"Worst {typ_label} {axis} -> Cell {worst_cell['Cell']} | 3xStd: {worst_cell['Threshold (3xStd)']:.5f}")

print("\n")

# 5. Export Full Report
output_filename = f"noise_report_{os.path.splitext(args.filename)[0]}.csv"
output_path = os.path.join(args.folder, output_filename)
res_df.to_csv(output_path, index=False)

print(f"✅ Full report for all individual cells saved to: {output_path}")