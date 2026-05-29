import pandas as pd
import matplotlib
matplotlib.use('TkAgg') # Ensures the window opens cleanly on Ubuntu Wayland
import matplotlib.pyplot as plt
import matplotlib.animation as animation
import sys
import argparse

# 1. Terminal Argument Configuration
parser = argparse.ArgumentParser(description="XELA CSV Offline Visualizer")
parser.add_argument("filename", help="Name of the CSV file to load (e.g., test1.csv)")
parser.add_argument("--folder", default="csv_records/", help="Path to the folder containing the CSV")
args = parser.parse_args()

csv_path = f"{args.folder}{args.filename}"
print(f"Loading data from: {csv_path}")

try:
    df = pd.read_csv(csv_path)
except FileNotFoundError:
    print(f"Error: Could not find {csv_path}.")
    sys.exit()

# Clean column names (strips any accidental spaces)
df.columns = df.columns.str.strip()

# Find the time column dynamically (Looks for 'time' or defaults to column 0)
time_cols = [col for col in df.columns if 'time' in col.lower()]
time_col_name = time_cols[0] if time_cols else df.columns[0]

# 2. Sensor Layout (uSPa44 4x4 Grid)
grid_x = [0, 1, 2, 3, 0, 1, 2, 3, 0, 1, 2, 3, 0, 1, 2, 3]
grid_y = [3, 3, 3, 3, 2, 2, 2, 2, 1, 1, 1, 1, 0, 0, 0, 0]

fig, ax = plt.subplots(figsize=(7, 7))
fig.canvas.manager.set_window_title('XELA CSV Offline Visualizer')

# We use the very first frame to center the idle state AND set the starting clock
baseline = df.iloc[0]
start_time = baseline[time_col_name]

# Helper function to find columns safely
def get_col(row, idx, axis):
    if f"{idx}{axis.upper()}" in row:
        return row[f"{idx}{axis.upper()}"]
    elif f"{idx}{axis.lower()}" in row:
        return row[f"{idx}{axis.lower()}"]
    return 0 

# 3. Animation Function
def update_frame(frame_index):
    ax.clear()
    
    # Keep the grid static and squared
    ax.set_xlim(-1, 4)
    ax.set_ylim(-1, 4)
    ax.set_xticks(range(4))
    ax.set_yticks(range(4))
    ax.grid(True, linestyle='--', alpha=0.5)
    ax.set_facecolor('black') 
    
    row = df.iloc[frame_index]
    
    # Calculate relative elapsed time
    current_time = row[time_col_name]
    relative_time = current_time - start_time
    
    ax.set_title(f"CSV Playback - Frame: {frame_index} | Elapsed: {relative_time:.3f} s", color='white')
    
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
        
        sizes.append(max(10, abs(delta_z) / scale_size))
        x_offsets.append(grid_x[i-1] + (delta_x / scale_pos))
        y_offsets.append(grid_y[i-1] - (delta_y / scale_pos)) 

    # Plot the bubbles 
    ax.scatter(x_offsets, y_offsets, s=sizes, c='#00FF00', alpha=0.8, edgecolors='white')

# 5. Run the Animation
ani = animation.FuncAnimation(fig, update_frame, frames=len(df), interval=50, repeat=False)

fig.patch.set_facecolor('black')
plt.show()