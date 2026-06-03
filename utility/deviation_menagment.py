import numpy as np
from scipy import signal

def remove_drift_polynomial(time_data, z_data, deg=2):
    """
    Rimuove la deriva fittando un polinomio di grado 'deg' (es. 2 o 3 per derive curve).
    """
    # Creiamo un array di indici temporali per il fit numerico
    x = np.arange(len(z_data))
    
    # Fit del polinomio sui dati affetti da drift
    p = np.polyfit(x, z_data, deg=deg)
    
    # Calcolo della curva di trend stimata
    drift = np.polyval(p, x)
    
    # Sottrazione del trend dal segnale originale
    corrected_data = z_data - drift
    return corrected_data

def remove_drift_highpass(time_data, z_data, cutoff_hz=0.01, fs=133.0):
    """
    Rimuove la deriva usando un filtro Butterworth passa-alto CAUSALE.
    Simula esattamente il comportamento del filtro applicato in tempo reale (real-time).
    """
    # Configurazione del filtro (ordine 2)
    nyquist = 0.5 * fs
    normal_cutoff = cutoff_hz / nyquist
    b, a = signal.butter(2, normal_cutoff, btype='high', analog=False)
    
    # Inizializziamo lo stato del filtro a zero (come all'accensione del sensore)
    zi = signal.lfilter_zi(b, a) * 0.0
    
    # lfilter applica il filtro in modo causale (solo in avanti) sfruttando lo stato zi
    corrected_data, _ = signal.lfilter(b, a, z_data, zi=zi)
    
    return corrected_data

def apply_deviation_management(time_data, z_data_all, method='poly', **kwargs):
    """
    Funzione wrapper per applicare la correzione a tutti i taxel in modo modulare.
    Metodi supportati: 'poly', 'highpass'
    """
    corrected_z_data = {}
    
    for taxel_id, data in z_data_all.items():
        if method == 'poly':
            deg = kwargs.get('deg', 2)
            corrected_z_data[taxel_id] = remove_drift_polynomial(time_data, data, deg=deg)
        elif method == 'highpass':
            cutoff = kwargs.get('cutoff_hz', 0.01)
            fs = kwargs.get('fs', 133.0) # Assumi 133Hz di default se non specificato
            corrected_z_data[taxel_id] = remove_drift_highpass(time_data, data, cutoff_hz=cutoff, fs=fs)
        else:
            # Se il metodo non è riconosciuto, restituisce i dati non modificati
            corrected_z_data[taxel_id] = data
            
    return corrected_z_data