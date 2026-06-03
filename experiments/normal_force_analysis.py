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




def load_and_process_data(csv_path):
    """Carica il CSV e restituisce i dati processati e pronti per il plot."""
    try:
        df = pd.read_csv(csv_path)
    except FileNotFoundError:
        print(f"Error: Could not find {csv_path}.")
        sys.exit()

    df.columns = df.columns.str.strip()

    time_cols = [col for col in df.columns if 'time' in col.lower()]
    time_col_name = time_cols[0] if time_cols else df.columns[0]
    df['relative_time'] = df[time_col_name] - df.iloc[0][time_col_name]

    baseline = calculate_tare_csv(df, num_frames=100)

    def get_z_data(row, idx):
        force_col = f"Force {idx}Z"
        if force_col in row: return row[force_col], "Force (N)"
        raw_col = f"{idx}Z"
        if raw_col in row: return row[raw_col], "Raw Ticks"
        return 0.0, "Unknown"

    time_data = df['relative_time'].values
    z_data_all = {}
    y_label = "Force (N)"

    for i in range(1, 17):
        val_z, unit = get_z_data(df, i)
        base_z, _ = get_z_data(baseline, i)
        y_label = unit
        z_data_all[i] = (val_z - base_z).values

    return time_data, z_data_all, y_label




def create_grid_plot(time_data, z_data_all, y_label, xmin=None, xmax=None, ymin=None, ymax=None, selected_taxel=None):
    """Genera e restituisce la Figura e gli Assi per la griglia 4x4 (o cella singola)."""
    # Se è selezionato un taxel specifico, riduciamo la griglia a 1x1 invece di 4x4
    if selected_taxel is not None:
        fig, ax = plt.subplots(figsize=(10, 6))
        axes = np.array([[ax]]) # incapsulato per compatibilità di interfaccia
        colors = plt.cm.tab20.colors 
        
        ax.plot(time_data, z_data_all[selected_taxel], color=colors[(selected_taxel-1)%20], linewidth=1.5)
        ax.set_title(f'Taxel {selected_taxel} (Individual Analysis)', fontsize=16)
        ax.grid(True, linestyle='--', alpha=0.6)
        ax.axhline(0, color='black', linewidth=0.8, linestyle='--')
        ax.set(xlabel='Time (s)', ylabel=y_label)
        
        if xmin is not None or xmax is not None: ax.set_xlim(left=xmin, right=xmax)
        if ymin is not None or ymax is not None: ax.set_ylim(bottom=ymin, top=ymax)
        
        fig.tight_layout()
        return fig, axes

    # Comportamento standard a 16 canali se selected_taxel è None
    fig, axes = plt.subplots(4, 4, figsize=(14, 10), sharex=True, sharey=True)
    colors = plt.cm.tab20.colors 

    for i in range(1, 17):
        row = (i - 1) // 4
        col = (i - 1) % 4
        ax = axes[row, col]
        ax.plot(time_data, z_data_all[i], color=colors[(i-1)%20], linewidth=1.5)
        ax.set_title(f'Taxel {i}', fontsize=16)
        ax.grid(True, linestyle='--', alpha=0.6)
        ax.axhline(0, color='black', linewidth=0.8, linestyle='--')

    for ax in axes.flat:
        ax.set(xlabel='Time (s)', ylabel=y_label)
        if xmin is not None or xmax is not None: ax.set_xlim(left=xmin, right=xmax)
        if ymin is not None or ymax is not None: ax.set_ylim(bottom=ymin, top=ymax)
        ax.label_outer()

    fig.tight_layout()
    fig.subplots_adjust(top=0.92)
    return fig, axes




def create_global_plot(time_data, z_data_all, y_label, xmin=None, xmax=None, ymin=None, ymax=None, selected_taxel=None):
    """Genera e restituisce la Figura e l'Asse per il grafico globale sovrapposto."""
    fig, ax = plt.subplots(figsize=(12, 6))
    colors = plt.cm.tab20.colors 

    # Se viene richiesto un taxel specifico nel plot globale, plottiamo solo quello
    taxels_to_plot = [selected_taxel] if selected_taxel is not None else range(1, 17)

    for i in taxels_to_plot:
        ax.plot(time_data, z_data_all[i], label=f'Taxel {i}', color=colors[(i-1)%20], linewidth=1.5, alpha=0.8)

    ax.axhline(0, color='black', linewidth=1.5, linestyle='--')
    title_suffix = f' (Taxel {selected_taxel} Only)' if selected_taxel is not None else ' (All Channels Overlaid)'
    ax.set_title('Global Normal Force' + title_suffix, fontsize=14, fontweight='bold')
    ax.set_xlabel('Time (s)', fontsize=12)
    ax.set_ylabel(y_label, fontsize=12)
    ax.grid(True, linestyle='--', alpha=0.6)

    if xmin is not None or xmax is not None: ax.set_xlim(left=xmin, right=xmax)
    if ymin is not None or ymax is not None: ax.set_ylim(bottom=ymin, top=ymax)

    ax.legend(loc='center left', bbox_to_anchor=(1, 0.5), fontsize=9)
    fig.tight_layout()
    return fig, ax




# Se eseguito direttamente dal terminale
if __name__ == "__main__":
    import argparse
    matplotlib.use('TkAgg')
    
    parser = argparse.ArgumentParser()
    parser.add_argument("filename")
    parser.add_argument("--folder", default="csv_records/")
    parser.add_argument("--xmin", type=float, default=0.000)
    parser.add_argument("--xmax", type=float, default=None)
    parser.add_argument("--ymin", type=float, default=-0.050)
    parser.add_argument("--ymax", type=float, default=0.050)
    
    # NUOVO: Selezione del singolo Taxel da studiare
    parser.add_argument("--taxel", type=int, default=None, choices=range(1, 17),
                        help="ID della cella (1-16) da analizzare singolarmente. Di default le mostra tutte.")
    
    # NUOVO: Parametri per la gestione delle deviazioni
    parser.add_argument("--correct-drift", action="store_true", 
                        help="Attiva la correzione e rimozione della deriva del segnale.")
    parser.add_argument("--drift-method", type=str, default="poly", choices=["poly", "highpass"],
                        help="Metodo di correzione: 'poly' (polinomiale) o 'highpass' (filtro passa-alto).")
    parser.add_argument("--poly-deg", type=int, default=2, 
                        help="Grado del polinomio per il metodo 'poly' (default: 2).")
    
    args = parser.parse_args()

    csv_path = os.path.join(args.folder, args.filename)
    time_data, z_data_all, y_label = load_and_process_data(csv_path)

    # APPLICAZIONE MODULARE DEL DETRENDING
    if args.correct_drift and apply_deviation_management is not None:
        print(f"Applying drift correction using method: {args.drift_method}...")
        z_data_all = apply_deviation_management(
            time_data, 
            z_data_all, 
            method=args.drift_method, 
            deg=args.poly_deg,
            cutoff_hz=0.01, # Eventualmente parametrizzabile da CLI
            fs=133.0        # Assumi frequenza sensore
        )

    # Generazione dei plot (passando l'eventuale taxel singolo selezionato)
    if not args.taxel:
        fig1, axes1 = create_grid_plot(time_data, z_data_all, y_label, args.xmin, args.xmax, args.ymin, args.ymax, selected_taxel=args.taxel)
        win_title_grid = f'Taxel {args.taxel} Analysis' if args.taxel else '16 Channel Grid'
        fig1.canvas.manager.set_window_title(win_title_grid)

    fig2, ax_main = create_global_plot(time_data, z_data_all, y_label, args.xmin, args.xmax, args.ymin, args.ymax, selected_taxel=args.taxel)
    win_title_global = f'Taxel {args.taxel} Overlaid' if args.taxel else 'Overlaid Channels'
    fig2.canvas.manager.set_window_title(win_title_global)

    plt.show()