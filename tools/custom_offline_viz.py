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
parser.add_argument("--mode", choices=['normal', 'slow'], default='normal', help="Playback mode: 'normal' (real-time sync) or 'slow' (frame-by-frame)")
parser.add_argument("--sensitivity", type=float, default=20.0, help="Multiplier for how fast the dots grow. >1.0 for faster growth, <1.0 for slower.")
parser.add_argument("--max-size", type=float, default=3500.0, help="Maximum allowed dot size (area) to prevent them from breaking the grid layout.")
# ----------------------
args = parser.parse_args()

csv_path = f"{args.folder}{args.filename}"
print(f"Loading data from: {csv_path}")
print(f"Playback Mode: {args.mode.upper()}")
print(f"Sensitivity: {args.sensitivity}x | Max Size: {args.max_size}")

try:
    df = pd.read_csv(csv_path)
except FileNotFoundError:
    print(f"Error: Could not find {csv_path}.")
    sys.exit()

# Clean column names (strips any accidental spaces)
df.columns = df.columns.str.strip()

# Find the time column dynamically
time_cols = [col for col in df.columns if 'time' in col.lower()]
time_col_name = time_cols[0] if time_cols else df.columns[0]

# Pre-calculate relative times for the whole file to make real-time playback super fast
start_time = df.iloc[0][time_col_name]
df['relative_time'] = df[time_col_name] - start_time

# 2. Sensor Layout (uSPa44 4x4 Grid)
grid_x = [0, 1, 2, 3, 0, 1, 2, 3, 0, 1, 2, 3, 0, 1, 2, 3]
grid_y = [3, 3, 3, 3, 2, 2, 2, 2, 1, 1, 1, 1, 0, 0, 0, 0]

fig, ax = plt.subplots(figsize=(7, 7))
fig.canvas.manager.set_window_title('XELA CSV Offline Visualizer')

baseline = df.iloc[0]

# Real-time clock tracker
playback_start_real_time = None

def get_col(row, idx, axis):
    if f"{idx}{axis.upper()}" in row:
        return row[f"{idx}{axis.upper()}"]
    elif f"{idx}{axis.lower()}" in row:
        return row[f"{idx}{axis.lower()}"]
    return 0 

# 3. Animation Function
def update_frame(tick):
    global playback_start_real_time
    
    # --- TIME SYNC LOGIC ---
    if args.mode == 'slow':
        # Frame-by-frame mode (Ignores real-world time)
        frame_index = tick
        if frame_index >= len(df):
            ani.event_source.stop()
            return
    else:
        # Normal real-time mode
        if playback_start_real_time is None:
            playback_start_real_time = time.time()
        
        elapsed_real_time = time.time() - playback_start_real_time
        
        # Magically find the closest past frame that matches our real-world elapsed time
        idx = df['relative_time'].searchsorted(elapsed_real_time) - 1
        frame_index = max(0, min(idx, len(df) - 1))
        
        # Stop the animation if we reached the end of the recording
        if frame_index >= len(df) - 1:
            ani.event_source.stop()
    # -----------------------

    ax.clear()
    
    # Keep the grid static and squared
    ax.set_xlim(-1, 4)
    ax.set_ylim(-1, 4)
    ax.set_xticks(range(4))
    ax.set_yticks(range(4))
    ax.grid(True, linestyle='--', alpha=0.5)
    ax.set_facecolor('black') 
    
    row = df.iloc[frame_index]
    relative_time = row['relative_time']
    
    ax.set_title(f"CSV Playback [{args.mode.upper()}] - Frame: {frame_index} | Elapsed: {relative_time:.3f} s", color='white')
    
    sizes = []
    x_offsets = []
    y_offsets = []
    
    # 4. Extract data for all 16 taxels
    for i in range(1, 17):
        x_val = get_col(row, i, 'X')
        y_val = get_col(row, i, 'Y')
        z_val = get_col(row, i, 'Z')
        
        base_x = get_col(baseline, i, 'X')
        base_y = get_col(baseline, i, 'Y')
        base_z = get_col(baseline, i, 'Z')
        
        delta_x = x_val - base_x
        delta_y = y_val - base_y
        delta_z = z_val - base_z
        
        is_calibrated = isinstance(base_x, float) and abs(base_x) < 10
        scale_pos = 0.05 if is_calibrated else 500.0
        scale_size = 0.001 if is_calibrated else 10.0
        
        # --- SIZE LOGIC ---
        # 1. Calculate base size from Z-axis force
        raw_calculated_size = abs(delta_z) / scale_size
        
        # 2. Apply user's sensitivity multiplier
        sensitive_size = raw_calculated_size * args.sensitivity
        
        # 3. Clamp between min (10) and max (args.max_size)
        final_size = min(max(10, sensitive_size), args.max_size)
        # ----------------------
        
        sizes.append(final_size)
        x_offsets.append(grid_x[i-1] + (delta_x / scale_pos))
        y_offsets.append(grid_y[i-1] - (delta_y / scale_pos)) 

    # Plot the bubbles 
    ax.scatter(x_offsets, y_offsets, s=sizes, c='#00FF00', alpha=0.8, edgecolors='white')

# 5. Run the Animation
if args.mode == 'slow':
    ani = animation.FuncAnimation(fig, update_frame, frames=len(df), interval=50, repeat=False)
else:
    ani = animation.FuncAnimation(fig, update_frame, frames=itertools.count(), interval=30, repeat=False, cache_frame_data=False)
fig.patch.set_facecolor('black')
plt.show()