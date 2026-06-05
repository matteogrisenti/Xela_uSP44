import pandas as pd
import numpy as np
import matplotlib
import sys
import os

# --- Gestione intelligente del Backend ---
if '--export' in sys.argv:
    matplotlib.use('Agg')
else:
    matplotlib.use('TkAgg')

import matplotlib.pyplot as plt
from matplotlib.widgets import Slider, Button
from matplotlib.animation import FuncAnimation, writers
from scipy.interpolate import griddata
import argparse
from tqdm import tqdm

# Aggiunge la root directory del progetto al path di Python
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
sys.path.append(parent_dir)

# ==========================================
# IMPORTA LA PIPELINE CONDIVISA DA NORMAL_FORCE
# ==========================================
from experiments.normal_force_analysis import load_and_process_data

class InteractiveShapeViewer:
    def __init__(self, time_data, Z_grids_all, threshold, mode, fps=30, export_mode=False):
        self.time_data = time_data
        self.Z_grids_all = Z_grids_all
        self.threshold = threshold
        self.mode = mode
        self.fps = fps
        self.export_mode = export_mode
        self.total_csv_frames = len(time_data)
        self.duration = time_data[-1]
        
        self.vmax = max(abs(Z_grids_all.min()), abs(Z_grids_all.max()))
        self.vmin = -self.vmax
        self.cmap = 'coolwarm'

        self.is_playing = False

        bottom_margin = 0.05 if export_mode else 0.25

        if mode == 'both':
            self.fig = plt.figure(figsize=(14, 10))
            self.axes_layout = [(2, 2, 1, 'discrete'), (2, 2, 2, 'continuous'), 
                                (2, 2, 3, 'discrete_3d'), (2, 2, 4, 'continuous_3d')]
        else:
            self.fig = plt.figure(figsize=(12, 6))
            self.axes_layout = [(1, 2, 1, mode), (1, 2, 2, f"{mode}_3d")]

        self.fig.subplots_adjust(bottom=bottom_margin)
        self.axes = {}

        for layout in self.axes_layout:
            rows, cols, pos, plot_type = layout
            is_3d = '3d' in plot_type
            ax = self.fig.add_subplot(rows, cols, pos, projection='3d' if is_3d else None)
            self.axes[plot_type] = ax

        if not self.export_mode:
            ax_slider = self.fig.add_axes([0.15, 0.1, 0.7, 0.03])
            self.slider = Slider(
                ax=ax_slider, label='Time (s)', 
                valmin=0.0, valmax=self.duration, 
                valinit=0.0
            )
            self.slider.on_changed(self.update_plot_from_time)

            ax_play = self.fig.add_axes([0.4, 0.03, 0.1, 0.04])
            self.btn_play = Button(ax_play, 'Play', hovercolor='0.975')
            self.btn_play.on_clicked(self.play)

            ax_pause = self.fig.add_axes([0.52, 0.03, 0.1, 0.04])
            self.btn_pause = Button(ax_pause, 'Pause', hovercolor='0.975')
            self.btn_pause.on_clicked(self.pause)

            self.anim = FuncAnimation(self.fig, self.anim_step, interval=1000/self.fps, cache_frame_data=False)
            self.anim.event_source.stop()

        self.update_plot_from_time(0.0)

    def process_grid(self, frame_idx):
        Z_grid = self.Z_grids_all[frame_idx]
        Z_thresh = np.copy(Z_grid)
        if self.threshold is not None:
            Z_thresh[np.abs(Z_thresh) < self.threshold] = 0
        return Z_grid, Z_thresh

    def update_plot_from_time(self, target_time):
        frame_idx = np.argmin(np.abs(self.time_data - target_time))
        
        Z_grid, Z_thresh = self.process_grid(frame_idx)
        current_time = self.time_data[frame_idx]
        
        self.fig.suptitle(f"Time: {current_time:.2f} s / {self.duration:.2f} s", fontsize=16, fontweight='bold')

        if self.mode in ['continuous', 'both']:
            x, y = np.meshgrid(np.arange(4), np.arange(4))
            xi, yi = np.linspace(0, 3, 40), np.linspace(0, 3, 40)
            xi, yi = np.meshgrid(xi, yi)
            zi = griddata((x.flatten(), y.flatten()), Z_thresh.flatten(), (xi, yi), method='cubic')

        for plot_type, ax in self.axes.items():
            ax.clear()
            if plot_type == 'discrete':
                ax.imshow(Z_thresh, cmap=self.cmap, vmin=self.vmin, vmax=self.vmax, origin='lower')
                ax.set_title('Discreto 2D')
            elif plot_type == 'continuous':
                ax.contourf(xi, yi, zi, levels=30, cmap=self.cmap, vmin=self.vmin, vmax=self.vmax)
                ax.set_title('Continuo 2D')
            elif plot_type == 'discrete_3d':
                xpos, ypos = np.meshgrid(np.arange(4) - 0.4, np.arange(4) - 0.4, indexing="ij")
                zpos = np.zeros_like(xpos.flatten())
                dx = dy = 0.8 * np.ones_like(zpos)
                dz = Z_thresh.flatten()
                colors = plt.cm.coolwarm(plt.Normalize(self.vmin, self.vmax)(dz))
                ax.bar3d(xpos.flatten(), ypos.flatten(), zpos, dx, dy, dz, color=colors)
                ax.set_title('Discreto 3D')
                ax.set_zlim(self.vmin, self.vmax)
            elif plot_type == 'continuous_3d':
                ax.plot_surface(xi, yi, zi, cmap=self.cmap, vmin=self.vmin, vmax=self.vmax, antialiased=False)
                ax.set_title('Continuo 3D')
                ax.set_zlim(self.vmin, self.vmax)

        self.fig.canvas.draw_idle()
        return []

    def anim_step(self, i):
        if self.is_playing and not self.export_mode:
            time_step = 1.0 / self.fps
            next_time = self.slider.val + time_step
            if next_time > self.duration:
                next_time = 0.0
            self.slider.set_val(next_time) 

    def play(self, event):
        self.is_playing = True
        self.anim.event_source.start()

    def pause(self, event):
        self.is_playing = False
        self.anim.event_source.stop()

    def export_video(self, filename):
        total_video_frames = int(self.duration * self.fps)
        print(f"\nRendering Video: {self.duration:.2f}s at {self.fps} FPS ({total_video_frames} frames)")
        
        pbar = tqdm(total=total_video_frames, desc="Processing", unit="frame")

        def video_update(frame_idx):
            target_time = frame_idx / self.fps
            self.update_plot_from_time(target_time)
            return []

        ani = FuncAnimation(self.fig, video_update, frames=total_video_frames, blit=False)

        def progress_callback(current_frame, total_frames):
            pbar.update(1)

        if 'ffmpeg' in writers.list():
            ani.save(filename, fps=self.fps, writer='ffmpeg', extra_args=['-vcodec', 'libx264'], progress_callback=progress_callback)
        else:
            ani.save(filename, fps=self.fps, progress_callback=progress_callback)

        pbar.close()
        print(f"✅ Video saved perfectly synced in real-time to: {filename}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="XELA Shape Viewer & Video Exporter")
    parser.add_argument("filename", help="Nome file CSV")
    parser.add_argument("--folder", default="csv_records/", help="Percorso della cartella")
    parser.add_argument("--threshold", type=float, default=0.015, help="Soglia di rumore")
    parser.add_argument("--mode", choices=['discrete', 'continuous', 'both'], default='both', help="Modalità di visualizzazione")
    
    # Comandi per il video
    parser.add_argument("--export", action="store_true", help="Non aprire l'interfaccia, esporta direttamente in mp4")
    parser.add_argument("--output", type=str, default="shape_video.mp4", help="Nome del file video in uscita")
    parser.add_argument("--fps", type=int, default=30, help="Framerate del video (e del player). Default: 30")

    args = parser.parse_args()

    csv_path = os.path.join(args.folder, args.filename)
    print(f"Loading data via central pipeline from: {csv_path}")

    # 1. Utilizza la funzione del modulo normal_force_analysis per caricare, fare zeroing e togliere il drift
    time_data, z_data_dict, y_label, df_contacts = load_and_process_data(
        csv_path=csv_path,
        folder=args.folder,
        show_contacts=False, # I contatti non ci servono nella griglia 3D
        correct_drift=True, # Attiva la correzione del drift
    )

    # 2. Converti il dizionario 1D dei taxel nella matrice 3D (Time x 4 x 4) richiesta per la forma
    num_frames = len(time_data)
    Z_grids_all = np.zeros((num_frames, 4, 4))
    
    for i in range(1, 17):
        row = (i - 1) // 4
        col = (i - 1) % 4
        Z_grids_all[:, row, col] = z_data_dict[i]

    # Avvia il visualizzatore
    viewer = InteractiveShapeViewer(
        time_data=time_data, 
        Z_grids_all=Z_grids_all, 
        threshold=args.threshold, 
        mode=args.mode,
        fps=args.fps,
        export_mode=args.export
    )

    if args.export:
        viewer.export_video(args.output)
    else:
        viewer.fig.canvas.manager.set_window_title(f"Shape Player - Mode: {args.mode.upper()}")
        plt.show()