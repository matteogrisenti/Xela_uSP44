import os
import sys
import time
import itertools
import argparse

import numpy as np
import pandas as pd
from tqdm import tqdm

import matplotlib
import matplotlib.cm as cm
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors
import matplotlib.animation as animation
matplotlib.use('TkAgg') 

current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
sys.path.append(parent_dir)
from utility.zeroing import calculate_tare_csv


# 1. Terminal Argument Configuration
parser = argparse.ArgumentParser(description="XELA CSV Offline Visualizer - UniTac Style")
parser.add_argument("filename", help="Name of the CSV file to load (e.g., test1.csv)")
parser.add_argument("--folder", default="csv_records/", help="Path to the folder containing the CSV")
parser.add_argument("--mode", choices=['normal', 'slow'], default='normal', help="Playback mode: 'normal' or 'slow'")
parser.add_argument("--max-z", type=float, default=0.02, help="Max Z force for color saturation (Dark Blue).")
parser.add_argument("--arrow-scale", type=float, default=1.0, help="Scale divisor for arrows. Lower = BIGGER arrows.")
parser.add_argument("--noise-filter", type=float, default=0.012, help="Deadzone for Force values (default: 0.012N)")
parser.add_argument("--raw-noise-filter", type=float, default=15.0, help="Deadzone for Raw positional movement (default: 15 ticks)")
parser.add_argument("--style", choices=['arrows', 'text'], default='arrows', help="Display style inside squares: 'arrows' or 'text'")
parser.add_argument("--save-mp4", type=str, default=None, help="Save the animation to this mp4 file (e.g., output.mp4).")
parser.add_argument("--export-fps", type=int, default=60, help="Fixed FPS for perfect video sync (default: 30. Use 60 for smoother UI).")
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

baseline = calculate_tare_csv(df, num_frames=100)
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
custom_colors = ["#00008B", "#ADD8E6", "#FFFFFF", "#FFD700", "#8B4513"]
# (DarkBlue, LightBlue, White, Gold, SaddleBrown)
cmap = mcolors.LinearSegmentedColormap.from_list("BlueWhiteBrown", custom_colors)
norm = mcolors.TwoSlopeNorm(vmin=-args.max_z, vcenter=0.0, vmax=args.max_z)

# Initialize Background Rectangles
rects = []
for i in range(16):
    rect = plt.Rectangle((grid_x[i]-0.5, grid_y[i]-0.5), 1, 1, facecolor='white', edgecolor='#333333', linewidth=2)
    ax.add_patch(rect)
    rects.append(rect)

    # --- Cell Number in Top-Left Corner ---
    circle_x = grid_x[i] - 0.35
    circle_y = grid_y[i] + 0.35

    circle = plt.Circle((circle_x, circle_y), radius=0.12, facecolor='white', edgecolor='black', linewidth=1, zorder=5)
    ax.add_patch(circle)

    ax.text(circle_x, circle_y, str(i + 1), 
            color='black', ha='center', va='center', 
            fontsize=8, fontweight='bold', zorder=6)

# Conditional Initialization based on selected Style
scat = None
Q = None
text_artists = []

if args.style == 'arrows':
    scat = ax.scatter(grid_x, grid_y, s=50, c='white', edgecolors='black', zorder=3)
    init_zeros = np.zeros(16)
    Q = ax.quiver(grid_x, grid_y, init_zeros, init_zeros, color='red', edgecolor='black', linewidth=1.0, 
                  angles='xy', scale_units='xy', scale=args.arrow_scale, 
                  width=0.015, headwidth=4, headlength=5, zorder=4, pivot='tail')
else:
    for i in range(16):
        t = ax.text(grid_x[i], grid_y[i], "", 
                    color='black', ha='center', va='center', 
                    fontsize=11, family='monospace', fontweight='bold', zorder=4)
        text_artists.append(t)

title_text = ax.set_title("", color='white', pad=20)

# 4. Animation Update Loop
def update_frame(tick):
    global playback_start_real_time
    
    if args.save_mp4:
        # LOGICA DI SYNC PER IL RENDER:
        # Calcoliamo il tempo esatto in cui dovrebbe trovarsi questo frame del video (es. frame 30 a 30fps = 1.0 secondi)
        target_time = tick / args.export_fps
        # Troviamo la riga del CSV più vicina a questo istante di tempo (ignorando il conteggio lineare delle righe)
        idx = df['relative_time'].searchsorted(target_time)
        frame_index = max(0, min(idx, len(df) - 1))
        
    elif args.mode == 'slow':
        frame_index = tick
        if frame_index >= len(df):
            if hasattr(ani, 'event_source') and ani.event_source:
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
    mode_str = "RENDER" if args.save_mp4 else args.mode.upper()
    title_text.set_text(f"CSV Playback [{mode_str}] - Row: {frame_index} | Elapsed: {row['relative_time']:.3f} s")
    
    X_offsets, Y_offsets = [], []
    U_arrows, V_arrows = [], []
    
    for i in range(1, 17):
        # -- Forces (Heatmap Z & Force values) --
        delta_force_x = get_force(row, i, 'X') - get_force(baseline, i, 'X')
        delta_force_y = get_force(row, i, 'Y') - get_force(baseline, i, 'Y')
        delta_force_z = get_force(row, i, 'Z') - get_force(baseline, i, 'Z')
        
        if abs(delta_force_x) < args.noise_filter: delta_force_x = 0.0
        if abs(delta_force_y) < args.noise_filter: delta_force_y = 0.0
        if abs(delta_force_z) < args.noise_filter: delta_force_z = 0.0
        
        if abs(delta_force_z) < args.noise_filter: 
            delta_force_z = 0.0
        color = cmap(norm(delta_force_z))

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
            text_artists[i-1].set_color('black')

    if args.style == 'arrows':
        coords = np.column_stack((X_offsets, Y_offsets))
        scat.set_offsets(coords)
        Q.set_offsets(coords)
        Q.set_UVC(np.array(U_arrows), np.array(V_arrows))

# 5. Execute
if args.save_mp4:
    total_duration_seconds = df['relative_time'].iloc[-1]
    
    # Calcola il numero di frame totali per il video in base alla durata esatta e l'FPS richiesto
    total_video_frames = int(total_duration_seconds * args.export_fps)
    
    print(f"\n--- RENDER INFO ---")
    print(f"Experiment Duration: {total_duration_seconds:.2f} seconds")
    print(f"Target Video FPS: {args.export_fps}")
    print(f"Total CSV Data Rows: {len(df)}")
    print(f"Total Video Frames to Render: {total_video_frames}\n")
    
    ani = animation.FuncAnimation(fig, update_frame, frames=total_video_frames, repeat=False)
    
    with tqdm(total=total_video_frames, desc="Rendering Video", unit="frames", dynamic_ncols=True) as pbar:
        def update_progress(current_frame, total_frames):
            pbar.update(1)
            
        ani.save(args.save_mp4, writer='ffmpeg', fps=args.export_fps, progress_callback=update_progress)
        
    print("\nRender complete!")
else:
    if args.mode == 'slow':
        ani = animation.FuncAnimation(fig, update_frame, frames=len(df), interval=50, repeat=False)
    else:
        ani = animation.FuncAnimation(fig, update_frame, frames=itertools.count(), interval=30, repeat=False, cache_frame_data=False)
    plt.show()