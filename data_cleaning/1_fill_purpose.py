"""
Fill missing purpose_of_travel values using location-based clustering

This script:
1. Loads the processed data
2. Uses DBSCAN clustering to identify frequent locations for each user based on end coordinates
3. Infers purposes for locations based on known purpose_of_travel values
4. Fills missing purposes only when:
   - The location has a single unique purpose (default), OR
   - USE_FREQUENT_PURPOSE is True (uses most frequent purpose)
5. Adds a 'purpose_filled' column (0=original, 1=filled)
6. Saves the enhanced data back to Excel
"""

import pandas as pd
import numpy as np
from sklearn.cluster import DBSCAN
from collections import Counter

# ==================== CONFIGURATION ====================
# File paths
INPUT_FILE = 'raw/app_data_20250210_all_with_routes.xlsx'
OUTPUT_FILE = 'output/app_data_20250210_fill_purpose.xlsx'

# Distance threshold for clustering (in meters)
DISTANCE_THRESHOLD_METERS = 100

# Whether to use the most frequent purpose when multiple purposes exist at a location
# False: Only fill when location has a single unique purpose
# True: Fill with the most frequent purpose even when multiple purposes exist
USE_FREQUENT_PURPOSE = False
# =======================================================


def identify_location_purposes_for_user(user_trips):
    """
    Identify location purposes using clustering for a single user's trips
    
    Args:
        user_trips: DataFrame containing trips for one user
        
    Returns:
        Dictionary mapping trip indices to inferred purposes
    """
    # Extract end locations with valid coordinates
    locations = []
    location_info = []
    
    for idx, row in user_trips.iterrows():
        if pd.notna(row['end_latitude']) and pd.notna(row['end_longitude']):
            locations.append([row['end_latitude'], row['end_longitude']])
            location_info.append({
                'idx': idx,
                'purpose': row['purpose_of_travel'],
                'start_hour': pd.to_datetime(row['start_time']).hour if pd.notna(row['start_time']) else None,
                'day_type': 'Weekday' if row['start_weekday'] not in ['Saturday', 'Sunday'] else 'Weekend'
            })
    
    if len(locations) < 2:
        return {}
    
    # Cluster locations using DBSCAN
    # Convert meters to degrees (approximate: 1 degree latitude ≈ 111,000 meters)
    eps_degrees = DISTANCE_THRESHOLD_METERS / 111000.0
    
    locations_array = np.array(locations)
    clustering = DBSCAN(eps=eps_degrees, min_samples=1).fit(locations_array)
    
    # Map each location cluster to its inferred purpose
    cluster_purposes = {}
    
    for cluster_id in set(clustering.labels_):
        if cluster_id == -1:  # Skip noise points
            continue
        
        # Get all trips ending at this cluster
        cluster_mask = clustering.labels_ == cluster_id
        cluster_trips = [location_info[i] for i, mask in enumerate(cluster_mask) if mask]
        
        # Collect known purposes for this cluster
        known_purposes = [t['purpose'] for t in cluster_trips if pd.notna(t['purpose']) and str(t['purpose']).strip() != '']
        
        if known_purposes:
            # Get unique purposes at this location
            unique_purposes = set(known_purposes)
            
            if len(unique_purposes) == 1:
                # Only one unique purpose at this location - always fill
                inferred_purpose = list(unique_purposes)[0]
                cluster_purposes[cluster_id] = inferred_purpose
            elif USE_FREQUENT_PURPOSE:
                # Multiple purposes exist, but we're allowed to use the most frequent one
                purpose_counts = Counter(known_purposes)
                inferred_purpose = purpose_counts.most_common(1)[0][0]
                cluster_purposes[cluster_id] = inferred_purpose
            # else: Multiple purposes and USE_FREQUENT_PURPOSE is False - skip this cluster
        # If no known purposes, skip this cluster (don't infer)
    
    # Create a mapping from trip index to inferred purpose
    idx_to_purpose = {}
    for i, info in enumerate(location_info):
        cluster_id = clustering.labels_[i]
        # Only add if cluster has an inferred purpose
        if cluster_id != -1 and cluster_id in cluster_purposes:
            idx_to_purpose[info['idx']] = cluster_purposes[cluster_id]
    
    return idx_to_purpose


def fill_missing_purposes(df):
    """
    Fill missing purpose_of_travel values using location clustering
    
    Args:
        df: DataFrame with trip data
        
    Returns:
        DataFrame with filled purposes and purpose_filled column
    """
    # Create a copy to avoid modifying original
    df_filled = df.copy()
    
    # Add purpose_filled column (0 = original, 1 = filled by code)
    df_filled['purpose_filled'] = 0
    
    # Track statistics
    total_missing = 0
    total_filled = 0
    
    # Process each user separately
    for access_code in df_filled['accessCode'].unique():
        user_mask = df_filled['accessCode'] == access_code
        user_trips = df_filled[user_mask].copy()
        
        # Count missing purposes for this user
        missing_mask = user_trips['purpose_of_travel'].isna() | (user_trips['purpose_of_travel'].astype(str).str.strip() == '')
        user_missing = missing_mask.sum()
        total_missing += user_missing
        
        if user_missing == 0:
            continue  # No missing purposes for this user
        
        # Get inferred purposes for this user
        inferred_purposes = identify_location_purposes_for_user(user_trips)
        
        # Fill missing purposes
        for idx, inferred_purpose in inferred_purposes.items():
            if pd.isna(df_filled.loc[idx, 'purpose_of_travel']) or str(df_filled.loc[idx, 'purpose_of_travel']).strip() == '':
                df_filled.loc[idx, 'purpose_of_travel'] = inferred_purpose
                df_filled.loc[idx, 'purpose_filled'] = 1
                total_filled += 1
    
    print(f"\nPurpose Filling Summary:")
    print(f"  Total missing purposes: {total_missing}")
    print(f"  Successfully filled: {total_filled}")
    print(f"  Remaining missing: {total_missing - total_filled}")
    print(f"  Fill rate: {total_filled / total_missing * 100:.1f}%" if total_missing > 0 else "  Fill rate: N/A")
    
    return df_filled


def main():
    """Main function to process and fill purposes"""
    print("=" * 60)
    print("CONFIGURATION")
    print("=" * 60)
    print(f"Distance threshold: {DISTANCE_THRESHOLD_METERS} meters")
    print(f"Use frequent purpose: {USE_FREQUENT_PURPOSE}")
    print(f"  (If False: only fill when location has single unique purpose)")
    print(f"  (If True: fill with most frequent purpose even with multiple)")
    print("=" * 60)
    
    print(f"\nLoading data from {INPUT_FILE}...")
    df = pd.read_excel(INPUT_FILE)
    
    print(f"Total records: {len(df)}")
    print(f"Unique users: {df['accessCode'].nunique()}")
    
    # Check current purpose coverage
    missing_purpose = df['purpose_of_travel'].isna() | (df['purpose_of_travel'].astype(str).str.strip() == '')
    print(f"\nCurrent purpose coverage:")
    print(f"  With purpose: {(~missing_purpose).sum()} ({(~missing_purpose).sum() / len(df) * 100:.1f}%)")
    print(f"  Missing purpose: {missing_purpose.sum()} ({missing_purpose.sum() / len(df) * 100:.1f}%)")
    
    # Fill missing purposes
    print("\nFilling missing purposes using location clustering...")
    df_filled = fill_missing_purposes(df)
    
    # Check new purpose coverage
    missing_purpose_after = df_filled['purpose_of_travel'].isna() | (df_filled['purpose_of_travel'].astype(str).str.strip() == '')
    print(f"\nNew purpose coverage:")
    print(f"  With purpose: {(~missing_purpose_after).sum()} ({(~missing_purpose_after).sum() / len(df_filled) * 100:.1f}%)")
    print(f"  Missing purpose: {missing_purpose_after.sum()} ({missing_purpose_after.sum() / len(df_filled) * 100:.1f}%)")
    
    # Show distribution of filled purposes
    filled_purposes = df_filled[df_filled['purpose_filled'] == 1]['purpose_of_travel'].value_counts()
    if len(filled_purposes) > 0:
        print(f"\nDistribution of filled purposes:")
        for purpose, count in filled_purposes.items():
            print(f"  {purpose}: {count}")
    
    # Save to Excel
    print(f"\nSaving enhanced data to {OUTPUT_FILE}...")
    df_filled.to_excel(OUTPUT_FILE, index=False)
    print("Done!")


if __name__ == '__main__':
    main()
