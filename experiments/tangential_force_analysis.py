import pandas as pd
import numpy as np
import matplotlib
import matplotlib.pyplot as plt
import sys
import os

# Aggiunge la root directory del progetto (Xela_uSP44) al path di Python
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
sys.path.append(parent_dir)

from utility.zeroing import calculate_tare_csv
from utility.deviation_menagment import apply_deviation_management
from utility.contact_visualization import load_contact_windows, add_contact_overlays


def load_and_process_data(csv_path, target_axis='X', folder=None, show_contacts=False, correct_drift=False, drift_method="highpass", poly_deg=2):
    """Carica il CSV e restituisce i dati tangenziali processati e pronti per il plot."""
    try:
        df = pd.read_csv(csv_path)
    except FileNotFoundError:
        print(f"Error: Could not find {csv_path}.")
        sys.exit()

    df.columns = df.columns.str.strip()

    time_cols = [col for col in df.columns if 'time' in col.lower()]
    time_col_name = time_cols[0] if time_cols else df.columns[0]
    df['relative_time'] = df[time_col_name] - df.iloc[0][time_col_name]

    # Utilizziamo num_frames=20 come nel tuo script originale per l'asse tangenziale
    baseline = calculate_tare_csv(df, num_frames=20)

    def get_tangential_data(row, idx, axis):
        force_col = f"Force {idx}{axis}"
        if force_col in row: return row[force_col], "Force (N)"
        raw_col = f"{idx}{axis}"
        if raw_col in row: return row[raw_col], "Raw Ticks"
        return 0.0, "Unknown"

    time_data = df['relative_time'].values
    tangential_data_all = {}
    y_label = "Force (N)"

    for i in range(1, 17):
        val_t, unit = get_tangential_data(df, i, target_axis)
        base_t, _ = get_tangential_data(baseline, i, target_axis)
        y_label = unit
        tangential_data_all[i] = (val_t - base_t).values

    # CARICAMENTO DEI CONTATTI
    df_contacts = None
    if show_contacts and folder is not None and load_contact_windows is not None:
        df_contacts = load_contact_windows(folder, "contacts_windows.csv")

    # APPLICAZIONE MODULARE DEL DETRENDING
    if correct_drift and apply_deviation_management is not None:
        print(f"Applying drift correction using method: {drift_method}...")
        tangential_data_all = apply_deviation_management(
            time_data, 
            tangential_data_all, 
            method=drift_method, 
            deg=poly_deg,
            cutoff_hz=0.005, # Eventualmente parametrizzabile
            fs=133.0         # Assumi frequenza sensore
        )

    return time_data, tangential_data_all, y_label, df_contacts


def create_grid_plot(time_data, tangential_data_all, y_label, target_axis, xmin=None, xmax=None, ymin=None, ymax=None, threshold=None, df_contacts=None, selected_taxel=None):
    """Genera e restituisce la Figura e gli Assi per la griglia 4x4 (o cella singola)."""
    if selected_taxel is not None:
        fig, ax = plt.subplots(figsize=(10, 6))
        axes = np.array([[ax]]) 
        colors = plt.cm.tab20.colors 
        
        ax.plot(time_data, tangential_data_all[selected_taxel], color=colors[(selected_taxel-1)%20], linewidth=1.5)
        ax.set_title(f'Taxel {selected_taxel} ({target_axis}-Axis Individual Analysis)', fontsize=16)
        ax.grid(True, linestyle='--', alpha=0.6)
        ax.axhline(0, color='black', linewidth=0.8, linestyle='--')

        if threshold is not None:
            ax.axhline(threshold, color='black', linewidth=2.0, linestyle='--', zorder=4, label=f'Threshold ({threshold})')
            ax.axhline(-threshold, color='black', linewidth=2.0, linestyle='--', zorder=4)
            ax.legend(loc='upper right')

        ax.set(xlabel='Time (s)', ylabel=y_label)
        
        if xmin is not None or xmax is not None: ax.set_xlim(left=xmin, right=xmax)
        if ymin is not None or ymax is not None: ax.set_ylim(bottom=ymin, top=ymax)

        if add_contact_overlays and df_contacts is not None:
            add_contact_overlays(ax, df_contacts)
        
        fig.tight_layout()
        return fig, axes

    fig, axes = plt.subplots(4, 4, figsize=(14, 10), sharex=True, sharey=True)
    colors = plt.cm.tab20.colors 

    for i in range(1, 17):
        row = (i - 1) // 4
        col = (i - 1) % 4
        ax = axes[row, col]
        ax.plot(time_data, tangential_data_all[i], color=colors[(i-1)%20], linewidth=1.5)
        ax.set_title(f'Taxel {i}', fontsize=16)
        ax.grid(True, linestyle='--', alpha=0.6)
        ax.axhline(0, color='black', linewidth=0.8, linestyle='--')

        if threshold is not None:
            ax.axhline(threshold, color='black', linewidth=2.0, linestyle='--', zorder=4, label=f'Threshold +/-({threshold})')
            ax.axhline(-threshold, color='black', linewidth=2.0, linestyle='--', zorder=4)
            ax.legend(loc='upper right')

        if add_contact_overlays and df_contacts is not None:
            add_contact_overlays(ax, df_contacts)

    for ax in axes.flat:
        ax.set(xlabel='Time (s)', ylabel=y_label)
        if xmin is not None or xmax is not None: ax.set_xlim(left=xmin, right=xmax)
        if ymin is not None or ymax is not None: ax.set_ylim(bottom=ymin, top=ymax)
        ax.label_outer()

    fig.tight_layout()
    fig.subplots_adjust(top=0.92)
    return fig, axes


def create_global_plot(time_data, tangential_data_all, y_label, target_axis, xmin=None, xmax=None, ymin=None, ymax=None, threshold=None, df_contacts=None, selected_taxel=None):
    """Genera e restituisce la Figura e l'Asse per il grafico globale sovrapposto."""
    fig, ax = plt.subplots(figsize=(12, 6))
    colors = plt.cm.tab20.colors 

    taxels_to_plot = [selected_taxel] if selected_taxel is not None else range(1, 17)

    for i in taxels_to_plot:
        ax.plot(time_data, tangential_data_all[i], label=f'Taxel {i}', color=colors[(i-1)%20], linewidth=1.5, alpha=0.8)

    ax.axhline(0, color='black', linewidth=1.5, linestyle='--')

    if threshold is not None:
        ax.axhline(threshold, color='black', linewidth=2.0, linestyle='--', zorder=4, label=f'Threshold ({threshold})')
        ax.axhline(-threshold, color='black', linewidth=2.0, linestyle='--', zorder=4)
        ax.legend(loc='upper right')

    title_suffix = f' (Taxel {selected_taxel} Only)' if selected_taxel is not None else ' (All Channels Overlaid)'
    ax.set_title(f'Global Tangential Force ({target_axis}-Axis)' + title_suffix, fontsize=14, fontweight='bold')
    ax.set_xlabel('Time (s)', fontsize=12)
    ax.set_ylabel(y_label, fontsize=12)
    ax.grid(True, linestyle='--', alpha=0.6)

    if xmin is not None or xmax is not None: ax.set_xlim(left=xmin, right=xmax)
    if ymin is not None or ymax is not None: ax.set_ylim(bottom=ymin, top=ymax)

    if add_contact_overlays and df_contacts is not None:
        add_contact_overlays(ax, df_contacts)

    ax.legend(loc='center left', bbox_to_anchor=(1, 0.5), fontsize=9)
    fig.tight_layout()
    return fig, ax


# Se eseguito direttamente dal terminale
if __name__ == "__main__":
    import argparse
    matplotlib.use('TkAgg')
    
    parser = argparse.ArgumentParser(description="XELA Tangential Force (X/Y-Axis) Analyzer")
    parser.add_argument("filename")
    parser.add_argument("--folder", default="csv_records/")
    parser.add_argument("--axis", choices=['X', 'x', 'Y', 'y'], default='X', help="Asse tangenziale: X (Left/Right) o Y (Forward/Backward)")
    parser.add_argument("--xmin", type=float, default=0.000)
    parser.add_argument("--xmax", type=float, default=None)
    parser.add_argument("--ymin", type=float, default=-0.050)
    parser.add_argument("--ymax", type=float, default=0.050)

    parser.add_argument("--threshold", type=float, default=None,
                        help="Valore di soglia da disegnare come linea orizzontale tratteggiata.")

    parser.add_argument("--show-contacts", action="store_true", default=False,
                        help="Mostra le finestre temporali di contatto come bande verdi sullo sfondo.")
    
    parser.add_argument("--taxel", type=int, default=None, choices=range(1, 17),
                        help="ID della cella (1-16) da analizzare singolarmente.")
    
    parser.add_argument("--correct-drift", action="store_true", 
                        help="Attiva la correzione e rimozione della deriva del segnale.")
    parser.add_argument("--drift-method", type=str, default="highpass", choices=["poly", "highpass"],
                        help="Metodo di correzione: 'poly' o 'highpass'.")
    parser.add_argument("--poly-deg", type=int, default=2, 
                        help="Grado del polinomio (default: 2).")
    
    args = parser.parse_args()

    target_axis = args.axis.upper()
    csv_path = os.path.join(args.folder, args.filename)
    
    print(f"Loading Tangential Force ({target_axis}-Axis) data from: {csv_path}")

    # CHIAMATA ALLA FUNZIONE UNIFICATA
    time_data, tangential_data_all, y_label, df_contacts = load_and_process_data(
        csv_path=csv_path,
        target_axis=target_axis,
        folder=args.folder,
        show_contacts=args.show_contacts,
        correct_drift=args.correct_drift,
        drift_method=args.drift_method,
        poly_deg=args.poly_deg
    )

    # Generazione dei plot
    if not args.taxel:
        fig1, axes1 = create_grid_plot(
            time_data, tangential_data_all, y_label, target_axis, 
            args.xmin, args.xmax, args.ymin, args.ymax, 
            threshold=args.threshold, df_contacts=df_contacts, selected_taxel=args.taxel
        )
        win_title_grid = f'Taxel {args.taxel} Analysis' if args.taxel else f'Tangential ({target_axis}) - 16 Channel Grid'
        fig1.canvas.manager.set_window_title(win_title_grid)

    fig2, ax_main = create_global_plot(
        time_data, tangential_data_all, y_label, target_axis, 
        args.xmin, args.xmax, args.ymin, args.ymax, 
        threshold=args.threshold, df_contacts=df_contacts, selected_taxel=args.taxel
    )
    win_title_global = f'Taxel {args.taxel} Overlaid' if args.taxel else f'Tangential ({target_axis}) - Overlaid Channels'
    fig2.canvas.manager.set_window_title(win_title_global)

    plt.show()