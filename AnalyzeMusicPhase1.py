import os
import librosa
import numpy as np
import pickle
from tqdm import tqdm
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

# --- CONFIGURATION ---
LIBRARY_PATH = Path(r'C:\Users\jwhow\Music\iTunes\iTunes Media\Music')
FFMPEG_BIN_PATH = r'C:\ffmpeg\bin' 
OUTPUT_DATA = 'acoustic_features.pkl'
THREADS = 20 

os.environ["PATH"] += os.pathsep + FFMPEG_BIN_PATH

def analyze_track(file_path):
    """
    Extracts MFCC, Spectral Contrast, Chroma CENS, and Zero Crossing Rate.
    """
    try:
        y, sr = librosa.load(str(file_path), sr=22050)
        
        if len(y) < 100:
            return None

        mfcc = np.mean(librosa.feature.mfcc(y=y, sr=sr, n_mfcc=20).T, axis=0)
        contrast = np.mean(librosa.feature.spectral_contrast(y=y, sr=sr).T, axis=0)
        chroma = np.mean(librosa.feature.chroma_cens(y=y, sr=sr).T, axis=0)
        zcr = np.mean(librosa.feature.zero_crossing_rate(y).T, axis=0)

        return {
            "path": str(file_path),
            "features": np.hstack([mfcc, contrast, chroma, zcr])
        }
    except Exception as e:
        print(f"\nError processing {file_path.name}: {e}")
        return None

def run_extraction():
    print("--- Phase 1: Acoustic Feature Extraction (Delta Mode) ---")
    
    existing_data = []
    existing_paths = set()
    
    # Load existing acoustic_features.pkl to prevent redundant processing
    if Path(OUTPUT_DATA).exists():
        try:
            with open(OUTPUT_DATA, 'rb') as f:
                existing_data = pickle.load(f)
            existing_paths = {item["path"] for item in existing_data}
            print(f"Loaded {len(existing_paths)} existing tracks from cache.")
        except Exception as e:
            print(f"Failed to load cache: {e}. Starting fresh.")
            existing_data = []
            existing_paths = set()
    else:
        print("No cache found. Full library scan initiated.")

    print("--- Scanning Library ---")
    extensions = ['*.mp3', '*.m4a', '*.wav', '*.flac']
    all_files = []
    for ext in extensions:
        all_files.extend(list(LIBRARY_PATH.rglob(ext)))
    
    if not all_files:
        print("No files found. Check your LIBRARY_PATH.")
        return

    # Isolate delta (new files only)
    files_to_process = [f for f in all_files if str(f) not in existing_paths]
    
    print(f"Found {len(all_files)} total tracks. {len(files_to_process)} require analysis.")

    if not files_to_process:
        print("All tracks are up to date. Exiting.")
        return

    print(f"Initializing i9 Analysis on {THREADS} threads...")

    new_results = []
    with ProcessPoolExecutor(max_workers=THREADS) as executor:
        for res in tqdm(executor.map(analyze_track, files_to_process), total=len(files_to_process)):
            if res is not None:
                new_results.append(res)
    
    if new_results:
        final_data = existing_data + new_results
        with open(OUTPUT_DATA, 'wb') as f:
            pickle.dump(final_data, f)
        print(f"\nSUCCESS: Appended {len(new_results)} new tracks. Total library size: {len(final_data)}.")
    else:
        print("\nFAILURE/NO-OP: No new tracks were successfully analyzed.")

if __name__ == "__main__":
    import multiprocessing
    multiprocessing.freeze_support()
    run_extraction()