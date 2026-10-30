import pandas as pd
import numpy as np
from sklearn.preprocessing import StandardScaler
from sklearn.decomposition import PCA
from pathlib import Path

def find_acoustic_orphans(threshold_percentile=95):
    print("--- Hunting for Acoustic Outliers ---")
    df = pd.read_pickle('clustered_library.pkl')
    
    # We need the original features to calculate distance
    features = np.array(df['features'].tolist())
    scaler = StandardScaler()
    scaled_features = scaler.fit_transform(features)
    
    # Redo the PCA as we did in Phase 2
    pca = PCA(n_components=10)
    reduced_features = pca.fit_transform(scaled_features)
    
    # We need to find the center (centroid) of each cluster
    orphans = []
    for cluster_id in range(df['cluster'].max() + 1):
        cluster_data = reduced_features[df['cluster'] == cluster_id]
        centroid = np.mean(cluster_data, axis=0)
        
        # Calculate distance of each song in the cluster to its centroid
        distances = np.linalg.norm(cluster_data - centroid, axis=1)
        
        # Identify the indices of the tracks in this cluster
        cluster_indices = df[df['cluster'] == cluster_id].index
        
        for i, dist in enumerate(distances):
            df.at[cluster_indices[i], 'distance_from_center'] = dist

    # Define "Orphans" as the top 5% most distant tracks in the entire library
    threshold = np.percentile(df['distance_from_center'], threshold_percentile)
    orphan_df = df[df['distance_from_center'] >= threshold]

    print(f"\nFound {len(orphan_df)} 'Acoustic Orphans' that don't fit well anywhere:")
    for _, row in orphan_df.head(20).iterrows():
        print(f" - {Path(row['path']).name} (Distance: {row['distance_from_center']:.2f})")
    
    return orphan_df

if __name__ == "__main__":
    find_acoustic_orphans()