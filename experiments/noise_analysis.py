import pandas as pd
import numpy as np
import argparse
import sys
import os
from scipy.signal import butter, filtfilt

# Funzione per il filtro passa-alto
def apply_highpass_filter(data, cutoff, fs, order=2):
    nyq = 0.5 * fs
    normal_cutoff = cutoff / nyq
    b, a = butter(order, normal_cutoff, btype='high', analog=False)
    return filtfilt(b, a, data)

# 1. Argument Configuration
parser = argparse.ArgumentParser(description="XELA Sensor Noise Analyzer with Drift Correction")
parser.add_argument("filename", help="Name of the CSV file (recorded WITHOUT touching the sensor)")
parser.add_argument("--folder", default="csv_records/", help="Path to the folder containing the CSV")
parser.add_argument("--folder_output", default="results/noise_study_results/", help="Path to the folder to store the results")

# Nuovi parametri per il detrending
parser.add_argument("--correct-drift", action="store_true", help="Apply high-pass filter to remove signal drift before computing noise.")
parser.add_argument("--cutoff-hz", type=float, default=0.01, help="Cutoff frequency for the high-pass filter (default: 0.01 Hz).")
args = parser.parse_args()

csv_path = os.path.join(args.folder, args.filename)
print(f"Analyzing noise from file: {csv_path}\n")

try:
    df = pd.read_csv(csv_path)
except FileNotFoundError:
    print(f"Error: Could not find {csv_path}.")
    sys.exit()

df.columns = df.columns.str.strip()

# Estrazione tempo e calcolo frequenza di campionamento (Fs)
time_cols = [col for col in df.columns if 'time' in col.lower()]
time_col_name = time_cols[0] if time_cols else df.columns[0]
df['relative_time'] = df[time_col_name] - df.iloc[0][time_col_name]

dt = df['relative_time'].diff().mean()
fs = 1.0 / dt if dt > 0 else 133.0 # Frequenza calcolata o default

# Preparazione DataFrame per il calcolo del rumore (filtrato o meno)
df_noise = df.copy()
axes = ['X', 'Y', 'Z']
data_types = [('Raw', ''), ('Force', 'Force ')] # (Label, CSV Prefix)

if args.correct_drift:
    print(f"Applying High-Pass Filter (Cutoff: {args.cutoff_hz} Hz, Fs: {fs:.1f} Hz) to isolate pure noise...")
    for typ_label, prefix in data_types:
        for axis in axes:
            for i in range(1, 17):
                col_name = f"{prefix}{i}{axis}"
                if col_name in df_noise.columns:
                    # Rimuove eventuali NaN prima di filtrare
                    clean_data = np.nan_to_num(df_noise[col_name].values, nan=df_noise[col_name].mean())
                    df_noise[col_name] = apply_highpass_filter(clean_data, args.cutoff_hz, fs)
else:
    print("Drift correction is OFF. Noise will include natural sensor drift.")

# Data structures for the results
results = []

# 2. Cell-by-Cell Analysis (1-16)
for i in range(1, 17):
    for typ_label, prefix in data_types:
        for axis in axes:
            col_name = f"{prefix}{i}{axis}"
            
            if col_name in df.columns:
                # Mantiene la media originale per capire l'offset statico
                mean_val = df[col_name].mean()
                
                # Calcola la Deviazione Standard sui dati (eventualmente filtrati)
                std_val = df_noise[col_name].std()
                threshold = 3 * std_val
                
                results.append({
                    'Cell': f"{i:02d}",
                    'Type': typ_label,
                    'Axis': axis,
                    'Mean (Offset)': mean_val,
                    'Std (Noise)': std_val,
                    'Threshold (3xStd)': threshold
                })

# 3. Global Analysis (All cells combined)
for typ_label, prefix in data_types:
    for axis in axes:
        # Find all columns related to this axis and type
        cols = [f"{prefix}{i}{axis}" for i in range(1, 17) if f"{prefix}{i}{axis}" in df.columns]
        
        if cols:
            subset_orig = df[cols]
            subset_noise = df_noise[cols]
            
            # Media globale assoluta calcolata sui dati ORIGINALI
            global_mean = subset_orig.values.flatten().mean()
            
            # CRITICAL: Sottraiamo la media individuale ANCHE dai dati filtrati 
            # per non confondere le discrepanze tra le celle con il rumore temporale.
            zero_mean_data = subset_noise - subset_noise.mean()
            global_noise_std = zero_mean_data.values.flatten().std()
            global_threshold = 3 * global_noise_std
            
            results.append({
                'Cell': 'GLOBAL',
                'Type': typ_label,
                'Axis': axis,
                'Mean (Offset)': global_mean,
                'Std (Noise)': global_noise_std,
                'Threshold (3xStd)': global_threshold
            })

# 4. Create DataFrame and Format Output
res_df = pd.DataFrame(results)

# Separate Global and Individual stats for printing
global_df = res_df[res_df['Cell'] == 'GLOBAL'].copy()
cells_df = res_df[res_df['Cell'] != 'GLOBAL'].copy()

print("\n" + "="*70)
print(" 🌍 GLOBAL NOISE SUMMARY (All 16 cells combined)")
print("="*70)
pd.options.display.float_format = '{:.5f}'.format
print(global_df.to_string(index=False))
print("\n")

print("="*70)
print(" 🔬 WORST FLUCTUATIONS DETAIL (Max 3xStd per Axis)")
print("="*70)
for typ_label in ['Raw', 'Force']:
    for axis in axes:
        mask = (cells_df['Type'] == typ_label) & (cells_df['Axis'] == axis)
        if mask.any():
            worst_cell = cells_df[mask].loc[cells_df[mask]['Threshold (3xStd)'].idxmax()]
            print(f"Worst {typ_label} {axis} -> Cell {worst_cell['Cell']} | 3xStd: {worst_cell['Threshold (3xStd)']:.5f}")

print("\n")

# 5. Export Full Report
# Crea la directory di output se non esiste
os.makedirs(args.folder_output, exist_ok=True)

output_filename = f"noise_report_{os.path.splitext(args.filename)[0]}.csv"
output_path = os.path.join(args.folder_output, output_filename)
res_df.to_csv(output_path, index=False)

print(f"✅ Full report for all individual cells saved to: {output_path}")