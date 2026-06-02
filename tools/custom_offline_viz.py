import pandas as pd
import numpy as np
import matplotlib
matplotlib.use('TkAgg') # Ensures the window opens cleanly on Ubuntu Wayland
import matplotlib.pyplot as plt
import matplotlib.animation as animation
import matplotlib.cm as cm
import matplotlib.colors as mcolors
import sys
import argparse
import time
import itertools

# 1. Terminal Argument Configuration
parser = argparse.ArgumentParser(description="XELA CSV Offline Visualizer - UniTac Style")
parser.add_argument("filename", help="Name of the CSV file to load (e.g., test1.csv)")
parser.add_argument("--folder", default="csv_records/", help="Path to the folder containing the CSV")
parser.add_argument("--mode", choices=['normal', 'slow'], default='normal', help="Playback mode: 'normal' or 'slow'")
parser.add_argument("--max-z", type=float, default=1.0, help="Max Z force for color saturation (Dark Blue).")
parser.add_argument("--arrow-scale", type=float, default=1.0, help="Scale divisor for arrows. Lower = BIGGER arrows.")
parser.add_argument("--noise-filter", type=float, default=0.012, help="Deadzone for Force values (default: 0.012N)")
parser.add_argument("--raw-noise-filter", type=float, default=15.0, help="Deadzone for Raw positional movement (default: 15 ticks)")
parser.add_argument("--style", choices=['arrows', 'text'], default='arrows', help="Display style inside squares: 'arrows' or 'text'")
args = parser.parse_args()

csv_path = f"{args.folder}{args.filename}"
print(f"Loading data from: {csv_path}")
print(f"Playback Mode: {args.mode.upper()} | Style: UNITAC-NV ({args.style.upper()})")

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

num_baseline_frames = min(20, len(df))
baseline = df.iloc[0:num_baseline_frames].mean(numeric_only=True)
playback_start_real_time = None

# Data Fetchers
def get_raw(row, idx, axis):
    col = f"{idx}{axis.upper()}"
    return row[col] if col in row else 0.0

def get_force(row, idx, axis):
    col = f"Force {idx}{axis.upper()}"
    return row[col] if col in row else 0.0

# 3. Setup the Figure and Static Elements
fig, ax = plt.subplots(figsize=(8, 8))
fig.canvas.manager.set_window_title('XELA - UniTac Style Visualizer')
ax.set_xlim(-0.5, 3.5)
ax.set_ylim(-0.5, 3.5)
ax.set_xticks([]) 
ax.set_yticks([])
ax.set_aspect('equal') 
ax.set_facecolor('black')
fig.patch.set_facecolor('black')

# Create the colormap for Normal Force (Z-axis)
cmap = cm.Blues
norm = mcolors.Normalize(vmin=0, vmax=args.max_z)

# Initialize Background Rectangles
rects = []
for i in range(16):
    rect = plt.Rectangle((grid_x[i]-0.5, grid_y[i]-0.5), 1, 1, facecolor='white', edgecolor='#333333', linewidth=2)
    ax.add_patch(rect)
    rects.append(rect)

# Conditional Initialization based on selected Style
scat = None
Q = None
text_artists = []

if args.style == 'arrows':
    # Initialize Tracking Dots
    scat = ax.scatter(grid_x, grid_y, s=50, c='white', edgecolors='black', zorder=3)
    # Initialize Shear Force Arrows
    init_zeros = np.zeros(16)
    Q = ax.quiver(grid_x, grid_y, init_zeros, init_zeros, color='red', edgecolor='black', linewidth=1.0, 
                  angles='xy', scale_units='xy', scale=args.arrow_scale, 
                  width=0.015, headwidth=4, headlength=5, zorder=4, pivot='tail')
else:
    # Initialize text blocks centered in each square
    for i in range(16):
        t = ax.text(grid_x[i], grid_y[i], "", 
                    color='black', ha='center', va='center', 
                    fontsize=11, family='monospace', fontweight='bold', zorder=4)
        text_artists.append(t)

title_text = ax.set_title("", color='white', pad=20)

# 4. Animation Update Loop
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
            return

    row = df.iloc[frame_index]
    title_text.set_text(f"CSV Playback [{args.mode.upper()}] - Frame: {frame_index} | Elapsed: {row['relative_time']:.3f} s")
    
    X_offsets, Y_offsets = [], []
    U_arrows, V_arrows = [], []
    
    for i in range(1, 17):
        # -- Forces (Heatmap Z & Force values) --
        delta_force_x = get_force(row, i, 'X') - get_force(baseline, i, 'X')
        delta_force_y = get_force(row, i, 'Y') - get_force(baseline, i, 'Y')
        delta_force_z = get_force(row, i, 'Z') - get_force(baseline, i, 'Z')
        
        if delta_force_x < args.noise_filter: delta_force_x = 0.0
        if delta_force_y < args.noise_filter: delta_force_y = 0.0
        if delta_force_z < args.noise_filter: delta_force_z = 0.0
        
        # Custom Non-linear color mapping for an instant threshold jump
        z_abs = abs(delta_force_z)
        if z_abs == 0.0:
            color = cmap(0.0) # Pure baseline white when below threshold
        else:
            # 0.25 is the starting jump. It maps from 0.25 (clear light blue) to 1.0 (deep blue)
            color_intensity = 0.25 + (z_abs / args.max_z) * 0.75
            color = cmap(min(1.0, color_intensity))

        rects[i-1].set_facecolor(color)
        
        # -- Style Option 1: Arrows & Dots --
        if args.style == 'arrows':
            delta_raw_x = get_raw(row, i, 'X') - get_raw(baseline, i, 'X')
            delta_raw_y = get_raw(row, i, 'Y') - get_raw(baseline, i, 'Y')
            
            if abs(delta_raw_x) < args.raw_noise_filter: delta_raw_x = 0.0
            if abs(delta_raw_y) < args.raw_noise_filter: delta_raw_y = 0.0
            
            dot_x = grid_x[i-1] + (delta_raw_x / 500.0)
            dot_y = grid_y[i-1] - (delta_raw_y / 500.0)
            X_offsets.append(dot_x)
            Y_offsets.append(dot_y)
            
            U_arrows.append(delta_force_x)
            V_arrows.append(-delta_force_y) 
            
        # -- Style Option 2: Live Text Values --
        else:
            fmt = "{:.2f}"
            text_str = f"X: {fmt.format(delta_force_x)}\nY: {fmt.format(delta_force_y)}\nZ: {fmt.format(delta_force_z)}"
            text_artists[i-1].set_text(text_str)
            
            # Dynamic Contrast: Flip text color to white if background gets too dark
            if z_abs > (args.max_z * 0.45):
                text_artists[i-1].set_color('white')
            else:
                text_artists[i-1].set_color('black')

    # Push changes to graphics hardware if running arrow mode
    if args.style == 'arrows':
        coords = np.column_stack((X_offsets, Y_offsets))
        scat.set_offsets(coords)
        Q.set_offsets(coords)
        Q.set_UVC(np.array(U_arrows), np.array(V_arrows))

# 5. Execute
if args.mode == 'slow':
    ani = animation.FuncAnimation(fig, update_frame, frames=len(df), interval=50, repeat=False)
else:
    ani = animation.FuncAnimation(fig, update_frame, frames=itertools.count(), interval=30, repeat=False, cache_frame_data=False)

plt.show()