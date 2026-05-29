import pandas as pd
import matplotlib
matplotlib.use('TkAgg') # Ensures the window opens cleanly on Ubuntu Wayland
import matplotlib.pyplot as plt
import matplotlib.animation as animation
import sys
import argparse
import time
import itertools

# 1. Terminal Argument Configuration
parser = argparse.ArgumentParser(description="XELA CSV Offline Visualizer")
parser.add_argument("filename", help="Name of the CSV file to load (e.g., test1.csv)")
parser.add_argument("--folder", default="csv_records/", help="Path to the folder containing the CSV")
parser.add_argument("--mode", choices=['normal', 'slow'], default='normal', help="Playback mode: 'normal' or 'slow'")
parser.add_argument("--sensitivity", type=float, default=1.0, help="Multiplier for bubble growth.")
parser.add_argument("--max-size", type=float, default=3500.0, help="Maximum allowed dot size.")
parser.add_argument("--style", choices=['bubbles', 'text'], default='bubbles', help="Visual style: 'bubbles' or 'text'")
parser.add_argument("--noise-filter", type=float, default=0.05, help="Deadzone for Force values (default: 0.005N)")
parser.add_argument("--raw-noise-filter", type=float, default=15.0, help="Deadzone for Raw positional movement (default: 15 ticks)")
args = parser.parse_args()

csv_path = f"{args.folder}{args.filename}"
print(f"Loading data from: {csv_path}")
print(f"Playback Mode: {args.mode.upper()} | Style: {args.style.upper()}")

try:
    df = pd.read_csv(csv_path)
except FileNotFoundError:
    print(f"Error: Could not find {csv_path}.")
    sys.exit()

df.columns = df.columns.str.strip()

time_cols = [col for col in df.columns if 'time' in col.lower()]
time_col_name = time_cols[0] if time_cols else df.columns[0]

start_time = df.iloc[0][time_col_name]
df['relative_time'] = df[time_col_name] - start_time

# 2. Sensor Layout (uSPa44 4x4 Grid)
grid_x = [0, 1, 2, 3, 0, 1, 2, 3, 0, 1, 2, 3, 0, 1, 2, 3]
grid_y = [3, 3, 3, 3, 2, 2, 2, 2, 1, 1, 1, 1, 0, 0, 0, 0]

fig, ax = plt.subplots(figsize=(8, 8))
fig.canvas.manager.set_window_title('XELA CSV Offline Visualizer')

num_baseline_frames = min(20, len(df))
baseline = df.iloc[0:num_baseline_frames].mean(numeric_only=True)
playback_start_real_time = None

# --- NEW: Explicit Data Fetchers ---
def get_raw(row, idx, axis):
    """Fetches the raw positional data (e.g., '1X')"""
    col = f"{idx}{axis.upper()}"
    return row[col] if col in row else 0.0

def get_force(row, idx, axis):
    """Fetches the calibrated force data (e.g., 'Force 1X')"""
    col = f"Force {idx}{axis.upper()}"
    return row[col] if col in row else 0.0
# -----------------------------------

def update_frame(tick):
    global playback_start_real_time
    
    if args.mode == 'slow':
        frame_index = tick
        if frame_index >= len(df):
            ani.event_source.stop()
            return
    else:
        if playback_start_real_time is None:
            playback_start_real_time = time.time()
        
        elapsed_real_time = time.time() - playback_start_real_time
        idx = df['relative_time'].searchsorted(elapsed_real_time) - 1
        frame_index = max(0, min(idx, len(df) - 1))
        
        if frame_index >= len(df) - 1:
            ani.event_source.stop()

    ax.clear()
    ax.set_xlim(-0.5, 3.5)
    ax.set_ylim(-0.5, 3.5)
    ax.set_xticks(range(4))
    ax.set_yticks(range(4))
    ax.grid(True, linestyle='--', alpha=0.5, color='#444444')
    ax.set_facecolor('black') 
    
    row = df.iloc[frame_index]
    relative_time = row['relative_time']
    
    ax.set_title(f"CSV Playback [{args.mode.upper()}] - Frame: {frame_index} | Elapsed: {relative_time:.3f} s", color='white')
    
    sizes = []
    x_offsets = []
    y_offsets = []
    
    for i in range(1, 17):
        # 1. Calculate RAW positional movement (For bubble X/Y location)
        raw_x = get_raw(row, i, 'X')
        raw_y = get_raw(row, i, 'Y')
        base_raw_x = get_raw(baseline, i, 'X')
        base_raw_y = get_raw(baseline, i, 'Y')
        
        delta_raw_x = raw_x - base_raw_x
        delta_raw_y = raw_y - base_raw_y
        
        # Apply deadzone for raw position noise
        if abs(delta_raw_x) < args.raw_noise_filter: delta_raw_x = 0.0
        if abs(delta_raw_y) < args.raw_noise_filter: delta_raw_y = 0.0
        
        # 2. Calculate FORCE values (For bubble Size and Text Mode)
        force_x = get_force(row, i, 'X')
        force_y = get_force(row, i, 'Y')
        force_z = get_force(row, i, 'Z')
        base_force_x = get_force(baseline, i, 'X')
        base_force_y = get_force(baseline, i, 'Y')
        base_force_z = get_force(baseline, i, 'Z')
        
        delta_force_x = force_x - base_force_x
        delta_force_y = force_y - base_force_y
        delta_force_z = force_z - base_force_z
        
        # Apply deadzone for force noise (0.005N)
        if delta_force_x < args.noise_filter: delta_force_x = 0.0
        if delta_force_y < args.noise_filter: delta_force_y = 0.0
        if delta_force_z < args.noise_filter: delta_force_z = 0.0
        
        if args.style == 'bubbles':
            # Position logic (Uses RAW data)
            scale_pos = 500.0 
            x_offsets.append(grid_x[i-1] + (delta_raw_x / scale_pos))
            y_offsets.append(grid_y[i-1] - (delta_raw_y / scale_pos)) 
            
            # Size logic (Uses FORCE Z data)
            scale_size = 0.001 
            raw_calculated_size = abs(delta_force_z) / scale_size
            sensitive_size = raw_calculated_size * args.sensitivity
            final_size = min(max(10, sensitive_size), args.max_size)
            sizes.append(final_size)
            
        elif args.style == 'text':
            # Text logic (Uses FORCE X, Y, Z data exclusively)
            fmt = "{:.2f}"
            text_str = f"X: {fmt.format(delta_force_x)}\nY: {fmt.format(delta_force_y)}\nZ: {fmt.format(delta_force_z)}"
            
            ax.text(grid_x[i-1], grid_y[i-1], text_str, 
                    color='#00FF00', ha='center', va='center', 
                    fontsize=10, family='monospace', fontweight='bold')

    if args.style == 'bubbles':
        ax.scatter(x_offsets, y_offsets, s=sizes, c='#00FF00', alpha=0.8, edgecolors='white')

if args.mode == 'slow':
    ani = animation.FuncAnimation(fig, update_frame, frames=len(df), interval=50, repeat=False)
else:
    ani = animation.FuncAnimation(fig, update_frame, frames=itertools.count(), interval=30, repeat=False, cache_frame_data=False)

fig.patch.set_facecolor('black')
plt.show()