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

# Importa entrambi i moduli di analisi come alias per mantenere il codice pulito
import experiments.normal_force_analysis as nfa
import experiments.tangential_force_analysis as tfa

# ==========================================
# Configurazione CLI
# ==========================================
parser = argparse.ArgumentParser(description="Modular Video Generator (Normal & Tangential)")
parser.add_argument("filename", help="Nome file CSV")
parser.add_argument("--folder", default="csv_records/")
parser.add_argument("--output", default="animation.mp4")
parser.add_argument("--fps", type=int, default=30)
parser.add_argument("--plot_type", choices=['global', 'grid'], default='global', help="Quale grafico usare come base")

# NUOVI PARAMETRI DI SELEZIONE FORZA/ASSE
parser.add_argument("--force", choices=['normal', 'tangential'], default='normal', 
                    help="Scegli il tipo di forza da plottare: 'normal' (Asse Z) o 'tangential' (Assi X/Y).")
parser.add_argument("--axis", choices=['X', 'x', 'Y', 'y'], default='X', 
                    help="Se si sceglie la forza tangenziale, specifica l'asse: X (Left/Right) o Y (Forward/Backward).")

# Parametri di visualizzazione ed elaborazione (ereditati)
parser.add_argument("--xmin", type=float, default=0.000)
parser.add_argument("--xmax", type=float, default=None)
parser.add_argument("--ymin", type=float, default=-0.02)
parser.add_argument("--ymax", type=float, default=0.05)
parser.add_argument("--taxel", type=int, default=None, choices=range(1, 17))
parser.add_argument("--show-contacts", action="store_true")
parser.add_argument("-t", "--threshold", type=float, default=None)
parser.add_argument("--correct-drift", action="store_true")
parser.add_argument("--drift-method", type=str, default="highpass", choices=["poly", "highpass"])
parser.add_argument("--poly-deg", type=int, default=2)
args = parser.parse_args()

csv_path = os.path.join(args.folder, args.filename)

# ==========================================
# 1. Caricamento e Processamento Dati Dinamico
# ==========================================
if args.force == 'normal':
    print(f"Loading Normal Force (Z-Axis) data from: {csv_path}")
    time_data, data_all, y_label, df_contacts = nfa.load_and_process_data(
        csv_path=csv_path,
        folder=args.folder,
        show_contacts=args.show_contacts,
        correct_drift=args.correct_drift,
        drift_method=args.drift_method,
        poly_deg=args.poly_deg
    )
else:
    target_axis = args.axis.upper()
    print(f"Loading Tangential Force ({target_axis}-Axis) data from: {csv_path}")
    time_data, data_all, y_label, df_contacts = tfa.load_and_process_data(
        csv_path=csv_path,
        target_axis=target_axis,
        folder=args.folder,
        show_contacts=args.show_contacts,
        correct_drift=args.correct_drift,
        drift_method=args.drift_method,
        poly_deg=args.poly_deg
    )

# Limiti temporali
xmin_val = args.xmin
xmax_val = args.xmax if args.xmax is not None else time_data[-1]

# ==========================================
# 2. Generazione del Grafico Base Scelto
# ==========================================
print(f"Generating base plot: {args.plot_type.upper()} ({args.force.upper()})...")

if args.plot_type == 'global':
    if args.force == 'normal':
        fig, axes = nfa.create_global_plot(
            time_data, data_all, y_label, 
            xmin=xmin_val, xmax=xmax_val, ymin=args.ymin, ymax=args.ymax,
            threshold=args.threshold, df_contacts=df_contacts, selected_taxel=args.taxel
        )
    else:
        fig, axes = tfa.create_global_plot(
            time_data, data_all, y_label, target_axis=target_axis,
            xmin=xmin_val, xmax=xmax_val, ymin=args.ymin, ymax=args.ymax,
            threshold=args.threshold, df_contacts=df_contacts, selected_taxel=args.taxel
        )
    axes_list = [axes] # Lista di un solo asse per uniformità
else:
    if args.force == 'normal':
        fig, axes = nfa.create_grid_plot(
            time_data, data_all, y_label, 
            xmin=xmin_val, xmax=xmax_val, ymin=args.ymin, ymax=args.ymax,
            threshold=args.threshold, df_contacts=df_contacts, selected_taxel=args.taxel
        )
    else:
        fig, axes = tfa.create_grid_plot(
            time_data, data_all, y_label, target_axis=target_axis,
            xmin=xmin_val, xmax=xmax_val, ymin=args.ymin, ymax=args.ymax,
            threshold=args.threshold, df_contacts=df_contacts, selected_taxel=args.taxel
        )
    axes_list = axes.flat # Appiattisce la matrice di assi in una lista 1D

# ==========================================
# 3. Preparazione Animazione (Barre rosse temporali)
# ==========================================
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

# ==========================================
# 4. Esportazione Video
# ==========================================
ani = FuncAnimation(fig, update, frames=total_frames, blit=True)

# Crea la barra di caricamento CLI
pbar = tqdm(total=total_frames, desc="Rendering Video", unit="frame")

def progress_callback(current_frame, total_frames):
    pbar.update(1)

# Salva il file mp4
if 'ffmpeg' in animation.writers.list():
    ani.save(args.output, fps=args.fps, writer='ffmpeg', extra_args=['-vcodec', 'libx264'], progress_callback=progress_callback)
else:
    ani.save(args.output, fps=args.fps, progress_callback=progress_callback)

pbar.close()
print(f"Done! Video saved to {args.output}")
plt.close(fig)