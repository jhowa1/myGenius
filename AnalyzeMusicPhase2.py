import pickle
import numpy as np
import pandas as pd
from collections import Counter
from pathlib import Path
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler
from sklearn.decomposition import PCA

# --- CONFIGURATION ---
FEATURES_DATA = 'acoustic_features.pkl'
METADATA_DATA = 'itunes_metadata_map.pkl'
OUTPUT_DATA = 'clustered_library.pkl'

NUM_CLUSTERS = 20  
YEAR_WEIGHT = 10  

def get_era_genre_name(cluster_tracks):
    genres = [g for g in cluster_tracks['genre'] if g != 'Unknown']
    top_genre = Counter(genres).most_common(1)[0][0] if genres else "Eclectic"
    years = [y for y in cluster_tracks['year'] if y > 0] 
    
    if not years:
        return f"{top_genre} (Unknown Era)"
        
    min_year = min(years)
    max_year = max(years)
    
    if min_year == max_year:
        return f"{min_year} {top_genre}"
    elif (min_year // 10) == (max_year // 10):
        decade = str((min_year // 10) * 10)[-2:] + "s" 
        return f"'{decade} {top_genre}"
    else:
        return f"{top_genre} ({min_year}-{max_year})"

def get_vibe_name(cluster_tracks, cluster_id, pca_features, kmeans_model, original_df):
    centroid = kmeans_model.cluster_centers_[cluster_id]
    cluster_indices = cluster_tracks.index
    cluster_points = pca_features[cluster_indices]
    
    distances = np.linalg.norm(cluster_points - centroid, axis=1)
    anchor_idx = cluster_indices[np.argmin(distances)]
    anchor_artist = original_df.loc[anchor_idx, 'artist']
    
    genres = [g for g in cluster_tracks['genre'] if g != 'Unknown']
    top_genre = Counter(genres).most_common(1)[0][0] if genres else "Eclectic"

    vibe_dict = {
        'Rock': ['Driving', 'Heavy', 'Classic', 'High-Gain'],
        'Alternative': ['Gritty', 'Angsty', 'Fuzz', 'Alt'],
        'Jazz': ['Midnight', 'Smooth', 'Blue', 'Late Night'],
        'Metal': ['Crushing', 'Heavy', 'Shred', 'Dark'],
        'Pop': ['Upbeat', 'Neon', 'Vibrant', 'Groove'],
        'Acoustic': ['Coffeehouse', 'Mellow', 'Warm', 'Unplugged'],
        'Electronic': ['Synth', 'Pulse', 'Trance', 'Cyber'],
        'Blues': ['Muddy', 'Soulful', 'Slide', 'Grit']
    }

    vibe_words = vibe_dict.get(top_genre, ['Sonic', 'Resonant', 'Deep'])
    vibe = vibe_words[cluster_id % len(vibe_words)]

    years = [y for y in cluster_tracks['year'] if y > 0] 
    era = f"'{str(min(years))[-2:]}s" if years else "Timeless"

    templates = [
        f"{vibe} {top_genre} (The {anchor_artist} Core)",
        f"The {anchor_artist} Anchor ({vibe} {era})",
        f"{era} {vibe} {top_genre} (feat. {anchor_artist})",
        f"{vibe} Frequency: {anchor_artist} & more"
    ]
    
    return templates[cluster_id % len(templates)]

def run_hybrid_clustering():
    print("--- Phase 2: The Hybrid Synergist Engine ---")
    
    try:
        with open(FEATURES_DATA, 'rb') as f:
            audio_data = pickle.load(f)
        df_audio = pd.DataFrame(audio_data)
        df_meta = pd.read_pickle(METADATA_DATA)
    except FileNotFoundError as e:
        print(f"CRITICAL ERROR: Missing Brain File. {e}")
        return

    print("Synapsing Audio Physics with iTunes Metadata...")
    df_audio['merge_key'] = df_audio['path'].apply(lambda x: str(Path(x).resolve()).lower())
    df_meta['merge_key'] = df_meta['path'].apply(lambda x: str(Path(x).resolve()).lower())
    
    df = pd.merge(df_audio, df_meta, on='merge_key', how='inner', suffixes=('', '_drop'))
    df = df[[c for c in df.columns if not c.endswith('_drop')]] 
    df.drop(columns=['merge_key'], inplace=True)
    
    print(f"Successfully locked {len(df)} tracks for hybrid analysis.")

    base_features = np.array(df['features'].tolist())
    scaled_audio = StandardScaler().fit_transform(base_features)
    
    year_array = np.array(df['year']).reshape(-1, 1)
    scaled_year = StandardScaler().fit_transform(year_array) * YEAR_WEIGHT
    
    hybrid_matrix = np.hstack((scaled_audio, scaled_year))
    pca_features = PCA(n_components=10).fit_transform(hybrid_matrix)

    print(f"Crunching dimensions into {NUM_CLUSTERS} Acoustic/Era Neighborhoods...")
    kmeans = KMeans(n_clusters=NUM_CLUSTERS, random_state=42, n_init=20)
    df['cluster'] = kmeans.fit_predict(pca_features)

    print("Generating soulful playlist names via Centroid Anchors...")
    cluster_names = {}
    
    for i in range(NUM_CLUSTERS):
        cluster_tracks = df[df['cluster'] == i]
        base_name = get_vibe_name(cluster_tracks, i, pca_features, kmeans, df)
        
        if base_name in cluster_names.values():
            base_name = f"{base_name} Vol. II"
            
        cluster_names[i] = base_name

    df['cluster_name'] = df['cluster'].map(cluster_names)

    df.to_pickle(OUTPUT_DATA)
    print(f"\nSUCCESS: Mapped library saved to {OUTPUT_DATA}")

if __name__ == "__main__":
    run_hybrid_clustering()