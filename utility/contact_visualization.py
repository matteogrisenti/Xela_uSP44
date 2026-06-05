import pandas as pd
import os
import sys

def load_contact_windows(folder_path, filename="contacts_windows.csv"):
    """
    Carica il file CSV contenente i lassi di tempo dei contatti.
    """
    csv_path = os.path.join(folder_path, filename)
    if not os.path.exists(csv_path):
        print(f"Warning: Contact windows file not found at {csv_path}. Skipping visualization.")
        return None
    
    try:
        df = pd.read_csv(csv_path)
        # Rimuove spazi bianchi nei nomi delle colonne
        df.columns = df.columns.str.strip()
        return df
    except Exception as e:
        print(f"Error loading contact windows: {e}")
        return None

def add_contact_overlays(ax, df_contacts, ymin_text=None):
    """
    Disegna le bande verdi verticali sullo sfondo dell'asse (ax) fornito
    e aggiunge l'ID del contatto in alto a sinistra di ogni colonna.
    """
    if df_contacts is None or df_contacts.empty:
        return

    # Determina la coordinata Y per il testo (in alto nell'asse)
    # Usiamo le coordinate dei dati se disponibili, altrimenti ci affidiamo alle coordinate trasformate
    ylim = ax.get_ylim()
    # Posiziona il testo al 92% dell'altezza massima visibile nel grafico
    y_pos = ylim[1] - (ylim[1] - ylim[0]) * 0.08

    for _, row in df_contacts.iterrows():
        c_id = int(row['Contact ID'])
        start = float(row['Start Time'])
        end = float(row['End Time'])
        
        # Disegna la banda verde sullo sfondo (zorder=0 la mette dietro i dati del segnale)
        ax.axvspan(start, end, color='#d4edda', alpha=0.5, zorder=0, label='_nolegend_')
        
        # Aggiunge il numero del contatto in alto a sinistra della colonna verde
        # Un piccolo offset (start + 0.1) evita che il testo sia attaccato al bordo della linea
        ax.text(start + 0.1, y_pos, f"C{c_id}", 
                color='#155724', 
                fontsize=10, 
                fontweight='bold',
                verticalalignment='top',
                zorder=5)