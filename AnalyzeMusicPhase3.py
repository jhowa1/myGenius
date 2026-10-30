import win32com.client
import pandas as pd
import numpy as np
import datetime
from pathlib import Path
from sklearn.preprocessing import StandardScaler
from sklearn.decomposition import PCA

# ==========================================
# --- THE MASTER CONTROL PANEL ---
# ==========================================

DRY_RUN = False               
EXPORT_MANIFEST = True       

# --- STANDARD ACOUSTIC CLUSTER RULES ---
MIN_SONGS = 8                
MAX_SONGS = 125              # Increased to 125 
MAX_ARTIST_APPEARANCES = 4   # Bumped to 4. (125 tracks / 2 artist max = 63 unique artists needed, which is too restrictive)

# --- DECADE OVERRIDE RULES ---
ENABLE_DECADE_MIXES = True   
TARGET_DECADES = [1970, 1980, 1990, 2000]
DECADE_ARTIST_LIMIT = 8    

# --- THE CURATOR BIAS ---
MAX_SKIP_TOLERANCE = 3       
PLAY_COUNT_BONUS = 0.05      

# --- SEMANTIC BLOCKLIST ---
INFIDELITY_BLOCKLIST = [
    "Lips of an Angel",             # Hinder
    "Lyin', Sneakin' and Cheatin'", # Michael Burks
    "Hey Joe",                      # Popa Chubby / Hendrix / Scott Finch
    "Me and Mrs. Jones"             # Example placeholder
]
# ==========================================

def clean_old_playlists(itunes):
    print("--- Running Self-Cleaning Protocol ---")
    sources = itunes.Sources
    library_source = sources.Item(1)
    playlists = library_source.Playlists
    
    deleted_count = 0
    for i in range(playlists.Count, 0, -1):
        playlist = playlists.Item(i)
        if "Mix" in playlist.Name or playlist.Name == "Odd ball songs":
            try:
                playlist.Delete()
                deleted_count += 1
            except:
                pass
    print(f"Purged {deleted_count} stale AI playlists.\n")

def generate_manifest(sync_plan):
    filename = "Sync_Manifest.txt"
    with open(filename, "w", encoding="utf-8") as f:
        f.write(f"=== LOCAL GENIUS SYNC MANIFEST ===\n")
        f.write(f"Generated: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"Total Playlists Proposed: {len(sync_plan)}\n")
        f.write("==================================\n\n")
        
        for playlist_name, tracks in sync_plan.items():
            f.write(f"[{playlist_name}] - {len(tracks)} Tracks\n")
            f.write("-" * 40 + "\n")
            for i, track in enumerate(tracks, 1):
                f.write(f"  {i:02d}. {track['title']} ({track['year']} | {track['artist']})\n")
            f.write("\n")
    print(f"\n[i] Pre-flight report saved to: {filename}")

def execute_master_sync(orphan_percentile=95):
    print("--- Phase 3: The Tunable Curator Engine ---")
    
    try:
        df = pd.read_pickle('clustered_library.pkl')
    except Exception as e:
        print(f"Initialization Error: {e}\nEnsure Phase 2 has completed successfully.")
        return

    df['title'] = df['path'].apply(lambda x: Path(x).stem)

    # 1. CALCULATE BASE ACOUSTIC FIT
    print("Calculating acoustic geometry...")
    features = np.array(df['features'].tolist())
    scaled = StandardScaler().fit_transform(features)
    pca_features = PCA(n_components=10).fit_transform(scaled)
    
    df['dist'] = 0.0
    for cid in df['cluster'].unique():
        indices = df[df['cluster'] == cid].index
        cluster_points = pca_features[df['cluster'] == cid]
        centroid = np.mean(cluster_points, axis=0)
        df.loc[indices, 'dist'] = np.linalg.norm(cluster_points - centroid, axis=1)

    # 2. APPLY THE BOUNCER & CURATOR
    original_count = len(df)
    
    # Filter out skips and infidelity tracks
    df = df[df['skip_count'] <= MAX_SKIP_TOLERANCE].copy()
    
    # Remove any track whose title contains a string from the blocklist
    escaped_blocklist = [str(item).lower() for item in INFIDELITY_BLOCKLIST]
    df = df[~df['title'].str.lower().apply(lambda x: any(blocked in x for blocked in escaped_blocklist))]
    
    print(f"Bouncer rejected {original_count - len(df)} tracks (skips + semantic blocklist).")

    df['curator_score'] = df['dist'] - (df['play_count'] * PLAY_COUNT_BONUS)
    df.loc[df['rating'] >= 80, 'curator_score'] -= 1.0 

    sync_plan = {} 
    used_tracks = set()  # Global tracker to ensure mutual exclusivity across all playlists
    
    print("Building Playlist Manifest in memory...")

    # 3. PLAN THE DECADE OVERRIDE MIXES
    if ENABLE_DECADE_MIXES:
        for decade_start in TARGET_DECADES:
            decade_end = decade_start + 9
            decade_df = df[(df['year'] >= decade_start) & (df['year'] <= decade_end)].sort_values('curator_score')
            
            final_tracks = []
            artist_counts = {}
            for _, row in decade_df.iterrows():
                if row['path'] in used_tracks:
                    continue  # Skip if already in another playlist
                    
                if artist_counts.get(row['artist'], 0) < DECADE_ARTIST_LIMIT:
                    final_tracks.append(row.to_dict())
                    used_tracks.add(row['path'])
                    artist_counts[row['artist']] = artist_counts.get(row['artist'], 0) + 1
            
            if len(final_tracks) >= MIN_SONGS:
                name = f"Ultimate '{str(decade_start)[-2:]}s Mix"
                sync_plan[name] = final_tracks

    # 4. PLAN THE ACOUSTIC CLUSTER MIXES
    threshold = np.percentile(df['dist'], orphan_percentile)
    main_library_df = df[df['dist'] < threshold]

    for cluster_name in main_library_df['cluster_name'].unique():
        cluster_tracks = main_library_df[main_library_df['cluster_name'] == cluster_name].sort_values('curator_score')
        
        final_tracks = []
        artist_counts = {}
        for _, row in cluster_tracks.iterrows():
            if row['path'] in used_tracks:
                continue  # Skip if grabbed by a decade mix or previous cluster
                
            if artist_counts.get(row['artist'], 0) < MAX_ARTIST_APPEARANCES:
                final_tracks.append(row.to_dict())
                used_tracks.add(row['path'])
                artist_counts[row['artist']] = artist_counts.get(row['artist'], 0) + 1
            
            if len(final_tracks) == MAX_SONGS:
                break 
                
        if len(final_tracks) >= MIN_SONGS:
            sync_plan[cluster_name] = final_tracks

    # 5. GENERATE THE REPORT
    if EXPORT_MANIFEST:
        generate_manifest(sync_plan)

    # 6. EXECUTE THE SYNC
    if DRY_RUN:
        print("\n[!] DRY RUN ACTIVE. iTunes has NOT been modified.")
        print("Review 'Sync_Manifest.txt' in your folder. When you are happy with the list, set DRY_RUN = False and run again.")
    else:
        print("\n--- INJECTING PLAYLISTS TO ITUNES ---")
        try:
            itunes = win32com.client.Dispatch("iTunes.Application")
            clean_old_playlists(itunes)
            
            for playlist_name, tracks in sync_plan.items():
                playlist = itunes.CreatePlaylist(playlist_name)
                playlist = win32com.client.CastTo(playlist, 'IITUserPlaylist')
                for track in tracks:
                    try:
                        playlist.AddFile(str(Path(track['path']).resolve()))
                    except:
                        pass
                print(f" [+] Pushed: {playlist_name} ({len(tracks)} tracks)")
                
            print("\n--- LIVE SYNC COMPLETE ---")
        except Exception as e:
            print(f"iTunes Push Error: {e}")

if __name__ == "__main__":
    execute_master_sync()