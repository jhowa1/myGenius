# Local Genius Pipeline - README.md

**Local Genius** is a high-performance, strictly local machine-learning pipeline designed to replace Apple's discontinued iTunes Genius feature. Built for massive local libraries (2TB+) and high-end hardware (i9, 64GB RAM), it analyzes the raw acoustic physics of audio files to generate hyper-accurate, context-aware playlists via the iTunes COM interface.

No cloud. No subscriptions. 100% local processing.

## 🚀 Core Features

* **Hardcore Acoustic Analysis:** Uses `librosa` to extract deep acoustic features from the *full duration* of tracks, not just snippets.
  * *MFCCs:* Timbre and vocal texture.
  * *Spectral Contrast:* Grit, distortion, and gain (crucial for differentiating guitar tones).
  * *Chroma CENS:* Harmonic modes and melodic structure.
  * *Zero Crossing Rate:* Percussive attack and rhythm.
* **Hardware Optimized:** Specifically engineered to hammer high-end CPUs with 20+ threads for massive parallel feature extraction and memory-efficient chunking.
* **Delta Processing Cache:** Intelligently caches previously analyzed tracks (`acoustic_features.pkl`) to only analyze newly acquired music, saving massive amounts of compute time.
* **Advanced Curation Logic:** 
  * Mutual exclusivity: A track can only appear in *one* generated playlist.
  * Extended lengths: Playlists can contain up to 125 tracks.
  * Semantic Bouncer: Hardcoded blocklist to automatically drop tracks based on lyrical themes (e.g., infidelity/cheating).
* **Direct iTunes Integration:** Uses `pywin32` (win32com) to seamlessly map clusters back into Windows iTunes as native playlists.

## 🛠️ Tech Stack

* **Language:** Python 3.x
* **Audio Processing:** `librosa`, `ffmpeg`
* **Machine Learning:** `scikit-learn` (PCA, K-Means, StandardScaler), `pandas`, `numpy`
* **Automation:** `pywin32` (Windows COM Interface)

## 📂 Architecture & Workflow

The pipeline runs in a sequential order to extract metadata, analyze acoustics, map the multidimensional space, and finally inject the clusters.

### 0. Metadata Extraction (`get_artist_metadata.py`)
Connects to iTunes via COM to pull the latest library metadata, including play counts and skip counts. Outputs `itunes_metadata_map.pkl`.

### 1. Phase 1: Feature Extraction (`AnalyzeMusicPhase1.py`)
Scans the local music repository and extracts raw acoustic features using `librosa`. Utilizes Python's `multiprocessing` (20 threads) to process only *new* tracks not found in the cache. Outputs the updated raw mathematical matrix.

### 2. Phase 2: Dimensionality & Clustering (`AnalyzeMusicPhase2.py`)
Merges the acoustic data with iTunes metadata. Normalizes and performs dimensionality reduction (PCA down to 10 components). Applies K-Means clustering (set to 20 clusters) to group mathematically similar tracks. Outputs `clustered_library.pkl`.

### 3. Phase 3: Playlist Injection (`AnalyzeMusicPhase3.py`)
Connects to iTunes via the Windows COM interface. Enforces the curator rules (125 max songs, zero duplication across playlists, skip tolerances, and semantic blocklists). Automatically builds, names, and populates the playlists directly into your iTunes library. 

## ⚙️ Usage

Ensure iTunes is running in the background before executing Phase 0 and Phase 3.

```bash
# 0. Update play/skip counts and metadata from iTunes
python get_artist_metadata.py

# 1. Hammer the CPU and extract acoustic matrices for new tracks
python AnalyzeMusicPhase1.py

# 2. Map the acoustic space and cluster into 20 neighborhoods
python AnalyzeMusicPhase2.py

# 3. Sync directly to iTunes (enforcing bouncer rules and exclusivity)
python AnalyzeMusicPhase3.py
```

## 🔒 Operational Directives

* **Strictly Local:** Do not integrate any external APIs (e.g., Spotify, Last.fm, Apple Music) for collaborative filtering.
* **Full-Song Default:** Always analyze the entire track length.
* **Hardware Unlocked:** Maintain aggressive multi-threading configurations.