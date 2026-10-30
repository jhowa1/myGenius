import win32com.client
import pandas as pd

def extract_itunes_database_with_stats():
    print("--- Interrogating iTunes Database (Metadata + Deep Stats) ---")
    try:
        itunes = win32com.client.Dispatch("iTunes.Application")
        tracks = itunes.LibraryPlaylist.Tracks
    except Exception as e:
        print(f"Could not connect to iTunes: {e}")
        return

    track_count = tracks.Count
    print(f"Connected. Scanning {track_count} tracks for historical data...")

    metadata_list = []
    
    # COM interfaces use 1-based indexing
    for i in range(1, track_count + 1):
        track = tracks.Item(i)
        
        # We only want local files (Kind == 1 means ITTrackKindFile)
        if track.Kind == 1:
            try:
                # Cast to File track to access the hard drive path
                file_track = win32com.client.CastTo(track, 'IITFileOrCDTrack')
                file_path = file_track.Location
                
                if file_path:  # If the file actually exists on the drive
                    # Safely extract stats. If iTunes hasn't recorded a stat, default to 0.
                    try: plays = track.PlayedCount 
                    except: plays = 0
                    
                    try: skips = track.SkippedCount 
                    except: skips = 0
                    
                    # Note: iTunes ratings are out of 100 (e.g., 5 stars = 100, 4 stars = 80)
                    try: rating = track.Rating 
                    except: rating = 0

                    metadata_list.append({
                        'path': str(file_path),
                        'artist': track.Artist if track.Artist else "Unknown",
                        'genre': track.Genre if track.Genre else "Unknown",
                        'year': track.Year if track.Year else 2000,
                        'play_count': plays,
                        'skip_count': skips,
                        'rating': rating
                    })
            except Exception:
                continue

    # Convert to DataFrame
    df = pd.DataFrame(metadata_list)
    print("\n--- iTunes Deep Extraction Complete ---")
    print(f"Successfully mapped {len(df)} local tracks with play statistics.")
    
    # Overwrite the old map with this new, stat-rich version
    df.to_pickle('itunes_metadata_map.pkl')
    
    print("\n[Diagnostic Sample: Your Heavy Rotation]")
    # Sort by play count to prove we grabbed the right data
    top_played = df.sort_values(by='play_count', ascending=False).head(5)
    print(top_played[['artist', 'play_count', 'skip_count', 'rating']])

if __name__ == "__main__":
    extract_itunes_database_with_stats()