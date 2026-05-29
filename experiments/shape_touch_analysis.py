import pandas as pd
import numpy as np
import matplotlib
matplotlib.use('TkAgg') # Fondamentale per Ubuntu Wayland
import matplotlib.pyplot as plt
import matplotlib.animation as animation
from scipy.interpolate import RectBivariateSpline
import sys
import argparse
import os
import time
import itertools

# 1. Configurazione Parametri
parser = argparse.ArgumentParser(description="XELA 3D Touch Shape Analyzer")
parser.add_argument("filename", help="Nome del file CSV da analizzare")
parser.add_argument("--folder", default="csv_records/", help="Cartella contenente il CSV")
parser.add_argument("--noise-filter", type=float, default=0.005, help="Deadzone per azzerare il rumore (default: 0.005N)")
parser.add_argument("--z-max", type=float, default=0.5, help="Forza Massima in Newton per fissare l'altezza del grafico (es. 1.0, 2.5)")
args = parser.parse_args()

csv_path = os.path.join(args.folder, args.filename)
print(f"Caricamento dati di Forma 3D da: {csv_path}")

try:
    df = pd.read_csv(csv_path)
except FileNotFoundError:
    print(f"Errore: Impossibile trovare {csv_path}.")
    sys.exit()

df.columns = df.columns.str.strip()

time_cols = [col for col in df.columns if 'time' in col.lower()]
time_col_name = time_cols[0] if time_cols else df.columns[0]
start_time = df.iloc[0][time_col_name]
df['relative_time'] = df[time_col_name] - start_time

# Baseline per la "Tara" (Media dei primi 20 frame)
num_baseline_frames = min(20, len(df))
baseline = df.iloc[0:num_baseline_frames].mean(numeric_only=True)

def get_force_z(row, idx):
    """Estrae la Forza Z calibrata. Se manca, usa i tick grezzi."""
    force_col = f"Force {idx}Z"
    if force_col in row:
        return row[force_col]
    raw_col = f"{idx}Z"
    if raw_col in row:
        return row[raw_col]
    return 0.0

# 2. Setup Griglia e Grafico 3D
fig = plt.figure(figsize=(10, 8))
ax = fig.add_subplot(111, projection='3d')
fig.canvas.manager.set_window_title('XELA 3D Touch Shape')

# Mappatura della griglia fisica XELA (4x4)
# Y va da 0 a 3, X va da 0 a 3
grid_x_map = [0, 1, 2, 3, 0, 1, 2, 3, 0, 1, 2, 3, 0, 1, 2, 3]
grid_y_map = [3, 3, 3, 3, 2, 2, 2, 2, 1, 1, 1, 1, 0, 0, 0, 0]

# Griglia grezza per l'interpolazione
x_raw = np.arange(4)
y_raw = np.arange(4)

# Griglia ad alta risoluzione (50x50 punti) per rendere la superficie "morbida"
x_fine = np.linspace(0, 3, 50)
y_fine = np.linspace(0, 3, 50)
X_fine, Y_fine = np.meshgrid(x_fine, y_fine)

playback_start_real_time = None

# 3. Funzione di Animazione
def update_frame(tick):
    global playback_start_real_time
    
    # Sincronizzazione in Tempo Reale
    if playback_start_real_time is None:
        playback_start_real_time = time.time()
    
    elapsed_real_time = time.time() - playback_start_real_time
    idx = df['relative_time'].searchsorted(elapsed_real_time) - 1
    frame_index = max(0, min(idx, len(df) - 1))
    
    if frame_index >= len(df) - 1:
        ani.event_source.stop()

    row = df.iloc[frame_index]
    relative_time = row['relative_time']
    
    # Popoliamo la matrice 4x4 dei sensori
    Z_matrix = np.zeros((4, 4))
    
    for i in range(1, 17):
        val_z = get_force_z(row, i)
        base_z = get_force_z(baseline, i)
        delta_z = val_z - base_z
        
        # Applica il filtro rumore (deadzone)
        if abs(delta_z) < args.noise_filter: 
            delta_z = 0.0
            
        # Assegna il valore alla matrice (Y, X)
        x_idx = grid_x_map[i-1]
        y_idx = grid_y_map[i-1]
        Z_matrix[y_idx, x_idx] = delta_z

    # --- MAGIA DELL'INTERPOLAZIONE ---
    # Creiamo una funzione spline basata sui 16 punti reali
    interp_spline = RectBivariateSpline(y_raw, x_raw, Z_matrix)
    # Generiamo i 2500 punti per la griglia HD
    Z_fine = interp_spline(y_fine, x_fine)
    
    # Pulisci e ridisegna il grafico 3D
    ax.clear()
    
    # Manteniamo la scala statica così l'animazione non "salta"
    ax.set_xlim(0, 3)
    ax.set_ylim(0, 3)
    ax.set_zlim(0, args.z_max)
    
    ax.set_xlabel('Sensor X', fontweight='bold')
    ax.set_ylabel('Sensor Y', fontweight='bold')
    ax.set_zlabel('Normal Force (N)', fontweight='bold')
    ax.set_title(f"3D Shape Interpolation | Elapsed: {relative_time:.3f} s", color='white', pad=20)
    
    # Disegniamo la superficie! (Uso 'plasma' o 'viridis' per far sembrare il calore)
    surf = ax.plot_surface(X_fine, Y_fine, Z_fine, cmap='plasma', edgecolor='none', alpha=0.9)
    
    # Sfondo scuro per contrasto
    ax.set_facecolor('black')
    fig.patch.set_facecolor('black')
    ax.xaxis.pane.fill = False
    ax.yaxis.pane.fill = False
    ax.zaxis.pane.fill = False
    ax.xaxis.pane.set_edgecolor('gray')
    ax.yaxis.pane.set_edgecolor('gray')
    ax.zaxis.pane.set_edgecolor('gray')
    ax.tick_params(colors='white')
    ax.xaxis.label.set_color('white')
    ax.yaxis.label.set_color('white')
    ax.zaxis.label.set_color('white')

# 4. Eseguiamo
ani = animation.FuncAnimation(fig, update_frame, frames=itertools.count(), interval=30, repeat=False, cache_frame_data=False)

plt.show()