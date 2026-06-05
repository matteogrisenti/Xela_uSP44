import pandas as pd
import numpy as np

# ===============================================
# 1. UTILITY FOR OFFLINE ANALYSIS (CSV)
# ======================================================
def calculate_tare_csv(df, num_frames=100):
    """
    Calculate the baseline (tare) value by averaging the first 'num_frames'.

    Args:
    df (pd.DataFrame): The raw data frame loaded from the CSV.
    num_frames (int): Number of frames (rows) to use for the calculation.

    Returns:
    pd.Series: A series containing the mean for each numeric column.
    """
    # Avoid errors if the CSV Has fewer rows than the frames required for tare.

    actual_frames = min(num_frames, len(df))

    # Calculate the average only on the numeric columns (ignore any anomalous strings/timestamps)
    baseline = df.iloc[0:actual_frames].mean(numeric_only=True)

    print(f"[Tare] Baseline calculated on {actual_frames} frames.")
    return baseline