import matplotlib
matplotlib.use('Agg') # Fondamentale per salvare video senza aprire finestre
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation
from matplotlib import animation
import argparse
import os
import numpy as np
import sys
from tqdm import tqdm

# Aggiunge la root directory del progetto (Xela_uSP44) al path di Python
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
sys.path.append(parent_dir)

# Importa le funzioni dal tuo modulo utility 
from experiments.normal_force_analysis import load_and_process_data, create_grid_plot, create_global_plot

# ==========================================
# Configurazione
# ==========================================
parser = argparse.ArgumentParser(description="Modular Video Generator")
parser.add_argument("filename", help="Nome file CSV")
parser.add_argument("--folder", default="csv_records/")
parser.add_argument("--output", default="animation.mp4")
parser.add_argument("--fps", type=int, default=30)
parser.add_argument("--plot_type", choices=['global', 'grid'], default='global', help="Quale grafico usare come base")
parser.add_argument("--xmin", type=float, default=0.000)
parser.add_argument("--xmax", type=float, default=None)
parser.add_argument("--ymin", type=float, default=-0.02)
parser.add_argument("--ymax", type=float, default=0.05)
args = parser.parse_args()

# 1. Caricamento Dati tramite la tua utility
csv_path = os.path.join(args.folder, args.filename)
print(f"Loading data from: {csv_path}")
time_data, z_data_all, y_label = load_and_process_data(csv_path)

# 2. Generazione del Grafico Base scelto
xmin_val = args.xmin
xmax_val = args.xmax if args.xmax is not None else time_data[-1]

print(f"Generating base plot: {args.plot_type.upper()}...")
if args.plot_type == 'global':
    fig, axes = create_global_plot(time_data, z_data_all, y_label, xmin_val, xmax_val, args.ymin, args.ymax)
    axes_list = [axes] # Trasforma l'asse singolo in lista per uniformità
else:
    fig, axes = create_grid_plot(time_data, z_data_all, y_label, xmin_val, xmax_val, args.ymin, args.ymax)
    axes_list = axes.flat # Flatten della matrice 4x4 in una lista 1D

# 3. Preparazione Animazione (Aggiunta barre rosse a tutti i subplot)
time_bars = []
for ax in axes_list:
    bar = ax.axvline(x=xmin_val, color='red', linewidth=2, linestyle='-')
    time_bars.append(bar)

duration = xmax_val - xmin_val
total_frames = int(duration * args.fps)
print(f"Rendering Video: {duration:.2f}s at {args.fps} FPS ({total_frames} frames)...")


def update(frame):
    current_time = xmin_val + (frame / args.fps)
    # Aggiorna la posizione di tutte le barre rosse in tutti i subplot
    for bar in time_bars:
        bar.set_xdata([current_time, current_time])
    return time_bars

# 4. Esportazione
ani = FuncAnimation(fig, update, frames=total_frames, blit=True)

# Crea la barra di caricamento
pbar = tqdm(total=total_frames, desc="Rendering Video", unit="frame")

# Funzione che Matplotlib chiamerà ad ogni frame calcolato
def progress_callback(current_frame, total_frames):
    pbar.update(1)

# Salva il video passando il callback
if 'ffmpeg' in animation.writers.list():
    ani.save(args.output, fps=args.fps, writer='ffmpeg', extra_args=['-vcodec', 'libx264'], progress_callback=progress_callback)
else:
    ani.save(args.output, fps=args.fps, progress_callback=progress_callback)

pbar.close() # Chiudi la barra quando ha finito
print(f"Done! Video saved to {args.output}")
plt.close(fig)
