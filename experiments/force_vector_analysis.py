import pandas as pd
import numpy as np
import matplotlib
matplotlib.use('TkAgg') # Ensures the window opens cleanly on Ubuntu Wayland
import matplotlib.pyplot as plt
import matplotlib.animation as animation
import sys
import argparse
import os
import time
import itertools

# 1. Terminal Argument Configuration
parser = argparse.ArgumentParser(description="XELA 3D Force Vector (Quiver) Analyzer")
parser.add_argument("filename", help="Name of the CSV file containing the recording")
parser.add_argument("--folder", default="csv_records/", help="Path to the folder containing the CSV")
parser.add_argument("--noise-z", type=float, default=0.005, help="Deadzone for Normal Force Z (default: 0.005N)")
parser.add_argument("--noise-xy", type=float, default=0.005, help="Deadzone for Shear Forces X/Y (default: 0.005N)")
parser.add_argument("--scale", type=float, default=2.0, help="Visual multiplier to make the arrows longer or shorter")
args = parser.parse_args()

csv_path = os.path.join(args.folder, args.filename)
print(f"Loading 3D Vector data from: {csv_path}")

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

# Baseline zeroing (Average of the first 20 frames)
num_baseline_frames = min(20, len(df))
baseline = df.iloc[0:num_baseline_frames].mean(numeric_only=True)

def get_force(row, idx, axis):
    """Fetches calibrated Force. If missing, falls back to raw ticks."""
    force_col = f"Force {idx}{axis.upper()}"
    if force_col in row:
        return row[force_col]
    raw_col = f"{idx}{axis.upper()}"
    if raw_col in row:
        return row[raw_col]
    return 0.0

# 2. Setup 3D Plot
fig = plt.figure(figsize=(10, 8))
ax = fig.add_subplot(111, projection='3d')
fig.canvas.manager.set_window_title('XELA 3D Force Vectors')

# Physical Sensor Grid Origins (X, Y, Z=0)
grid_x = [0, 1, 2, 3, 0, 1, 2, 3, 0, 1, 2, 3, 0, 1, 2, 3]
grid_y = [3, 3, 3, 3, 2, 2, 2, 2, 1, 1, 1, 1, 0, 0, 0, 0]
grid_z = [0] * 16

playback_start_real_time = None

# 3. Animation Function
def update_frame(tick):
    global playback_start_real_time
    
    # Real-Time Sync
    if playback_start_real_time is None:
        playback_start_real_time = time.time()
    
    elapsed_real_time = time.time() - playback_start_real_time
    idx = df['relative_time'].searchsorted(elapsed_real_time) - 1
    frame_index = max(0, min(idx, len(df) - 1))
    
    if frame_index >= len(df) - 1:
        ani.event_source.stop()

    row = df.iloc[frame_index]
    relative_time = row['relative_time']
    
    # Arrays to hold the direction/magnitude of the 16 arrows (Vectors U, V, W)
    U, V, W = [], [], []
    colors = []
    
    for i in range(1, 17):
        # Extract forces
        f_x = get_force(row, i, 'X')
        f_y = get_force(row, i, 'Y')
        f_z = get_force(row, i, 'Z')
        
        base_x = get_force(baseline, i, 'X')
        base_y = get_force(baseline, i, 'Y')
        base_z = get_force(baseline, i, 'Z')
        
        delta_x = f_x - base_x
        delta_y = f_y - base_y
        delta_z = f_z - base_z
        
        # Apply separated noise filters (Shear and Normal forces can have different noise profiles)
        if abs(delta_x) < args.noise_xy: delta_x = 0.0
        if abs(delta_y) < args.noise_xy: delta_y = 0.0
        if abs(delta_z) < args.noise_z: delta_z = 0.0
        
        U.append(delta_x)
        V.append(delta_y)
        W.append(delta_z)
        
        # Color mapping based on Z-force intensity (Green = Low force, Red = High force)
        intensity = min(1.0, abs(delta_z) * 2.0) # Simple scaling for color
        colors.append((intensity, 1.0 - intensity, 0.2, 1.0)) # RGB Alpha

    # Clear and redraw the 3D space
    ax.clear()
    
    # Keep the grid static and squared
    ax.set_xlim(-1, 4)
    ax.set_ylim(-1, 4)
    ax.set_zlim(0, 1.5) # Z-axis height (can be adjusted)
    
    ax.set_xlabel('Sensor X', fontweight='bold')
    ax.set_ylabel('Sensor Y', fontweight='bold')
    ax.set_zlabel('Force Magnitude', fontweight='bold')
    ax.set_title(f"3D Vector Force (Quiver) | Elapsed: {relative_time:.3f} s", color='white', pad=20)
    
    # Draw the sensor surface plane for visual reference
    X, Y = np.meshgrid(np.arange(-1, 5), np.arange(-1, 5))
    Z = np.zeros_like(X)
    ax.plot_surface(X, Y, Z, color='gray', alpha=0.1, edgecolor='none')
    
    # Draw the 16 Arrows (Quiver)
    ax.quiver(grid_x, grid_y, grid_z, U, V, W, 
              length=args.scale, normalize=False, 
              colors=colors, arrow_length_ratio=0.3, linewidth=2)
    
    # Styling
    ax.set_facecolor('black')
    fig.patch.set_facecolor('black')
    ax.xaxis.pane.fill = False
    ax.yaxis.pane.fill = False
    ax.zaxis.pane.fill = False
    ax.xaxis.pane.set_edgecolor('#444444')
    ax.yaxis.pane.set_edgecolor('#444444')
    ax.zaxis.pane.set_edgecolor('#444444')
    ax.tick_params(colors='white')
    ax.xaxis.label.set_color('white')
    ax.yaxis.label.set_color('white')
    ax.zaxis.label.set_color('white')

# 4. Run Animation
ani = animation.FuncAnimation(fig, update_frame, frames=itertools.count(), interval=30, repeat=False, cache_frame_data=False)

plt.show()