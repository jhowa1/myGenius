import pickle
import numpy as np
import pandas as pd
import music_tag
from collections import Counter
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler
from sklearn.decomposition import PCA

# --- CONFIGURATION ---
INPUT_DATA = 'acoustic_features.pkl'
TEST_CLUSTERS = 10 

def extract_metadata(df):
    print("--- Extracting & Diagnosing Tags ---")
    genres, years = [], []
    for path in df['path']:
        try:
            f = music_tag.load_file(path)
            # Safely extract genre
            g = str(f['genre'].value).strip() if f['genre'].value else 'Unknown'
            # Safely extract year (grab the first 4 digits in case it's formatted like "1995-04-12")
            y_raw = str(f['year'].value).strip() if f['year'].value else '2000'
            y = int(y_raw[:4]) if y_raw[:4].isdigit() else 2000
            
            genres.append(g)
            years.append(y)
        except:
            genres.append('Unknown')
            years.append(2000)
            
    df['genre'] = genres
    df['year'] = years
    
    # DIAGNOSTIC REPORT
    print("\n[Tag Diagnostic Report]")
    top_years = Counter(years).most_common(5)
    print(f"Most common years found: {top_years}")
    top_genres = Counter(genres).most_common(5)
    print(f"Most common genres found: {top_genres}")
    
    return df

def run_ab_test():
    with open(INPUT_DATA, 'rb') as f:
        data = pickle.load(f)
    df = pd.DataFrame(data)
    df = extract_metadata(df)
    
    base_features = np.array(df['features'].tolist())
    scaled_base = StandardScaler().fit_transform(base_features)

    print("\n==================================================")
    print(" MODEL A: The Purist (Strict Decade Boundaries)")
    print("==================================================")
    # Find whatever the most common decade is to guarantee a result
    most_common_year = df['year'].mode()[0]
    decade_start = (most_common_year // 10) * 10
    
    df_decade = df[(df['year'] >= decade_start) & (df['year'] < decade_start + 10)].copy()
    print(f"Targeting the {decade_start}s (Found {len(df_decade)} tracks)")
    
    if len(df_decade) > 10:
        features_decade = np.array(df_decade['features'].tolist())
        scaled_dec = StandardScaler().fit_transform(features_decade)
        pca_dec = PCA(n_components=10).fit_transform(scaled_dec)
        
        kmeans_A = KMeans(n_clusters=max(2, int(len(df_decade)/50)), random_state=42, n_init=10)
        df_decade['cluster'] = kmeans_A.fit_predict(pca_dec)
        
        print(f"\n[Sample: {decade_start}s Mix]")
        sample_A = df_decade[df_decade['cluster'] == 0].head(7)
        for _, row in sample_A.iterrows():
            name = row['path'].split('\\')[-1]
            print(f" - {name} ({row['year']} | {row['genre']})")
    else:
        print("Still not enough tracks with clean year tags to run Model A.")

    print("\n==================================================")
    print(" MODEL B: The Synergist (Weighted Matrix Crossover)")
    print("==================================================")
    year_array = np.array(df['year']).reshape(-1, 1)
    scaled_years = StandardScaler().fit_transform(year_array)
    weighted_years = scaled_years * 1.5 
    
    hybrid_matrix = np.hstack((scaled_base, weighted_years))
    pca_hybrid = PCA(n_components=10).fit_transform(hybrid_matrix)
    
    kmeans_B = KMeans(n_clusters=TEST_CLUSTERS, random_state=42, n_init=10)
    df['cluster_B'] = kmeans_B.fit_predict(pca_hybrid)
    
    print("\n[Sample: Audio-Dominant Hybrid Mix]")
    sample_B = df[df['cluster_B'] == 0].head(10)
    for _, row in sample_B.iterrows():
        name = row['path'].split('\\')[-1]
        print(f" - {name} ({row['year']} | {row['genre']})")

if __name__ == "__main__":
    import warnings
    warnings.filterwarnings("ignore")
    run_ab_test()