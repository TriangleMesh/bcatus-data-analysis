"""
Test different merge and delete parameters to see their impact on trip per person per day
"""

import pandas as pd
import numpy as np
import json
import os
from datetime import datetime, timedelta
from math import radians, cos, sin, asin, sqrt

# ============================================================================
# CONFIGURATION: Define parameter combinations to test
# ============================================================================

# List of parameter combinations to test
PARAMETER_SETS = [
    # === Time < 20 minutes (Very Conservative) ===
    {
        'name': 'Very Strict: 400m/10min merge, 100m/5min delete',
        'distance_threshold': 400,
        'time_gap_threshold': 10,
        'delete_distance': 100,
        'delete_time': 5,
    },
    {
        'name': 'Strict: 500m/12min merge, 110m/6min delete',
        'distance_threshold': 500,
        'time_gap_threshold': 12,
        'delete_distance': 110,
        'delete_time': 6,
    },
    {
        'name': 'Strict: 550m/15min merge, 120m/6min delete',
        'distance_threshold': 550,
        'time_gap_threshold': 15,
        'delete_distance': 120,
        'delete_time': 6,
    },
    {
        'name': 'Strict: 600m/15min merge, 125m/7min delete',
        'distance_threshold': 600,
        'time_gap_threshold': 15,
        'delete_distance': 125,
        'delete_time': 7,
    },
    {
        'name': 'Strict: 650m/18min merge, 130m/7min delete',
        'distance_threshold': 650,
        'time_gap_threshold': 18,
        'delete_distance': 130,
        'delete_time': 7,
    },
    {
        'name': 'Strict: 700m/18min merge, 140m/7min delete',
        'distance_threshold': 700,
        'time_gap_threshold': 18,
        'delete_distance': 140,
        'delete_time': 7,
    },
    
    # === Reference: More conservative time thresholds ===
    {
        'name': 'Very Conservative: 600m/30min merge, 130m/7min delete',
        'distance_threshold': 600,
        'time_gap_threshold': 30,
        'delete_distance': 130,
        'delete_time': 7,
    },
    {
        'name': 'Conservative: 700m/35min merge, 150m/8min delete',
        'distance_threshold': 700,
        'time_gap_threshold': 35,
        'delete_distance': 150,
        'delete_time': 8,
    },
    {
        'name': 'Moderate: 750m/37min merge, 145m/8min delete',
        'distance_threshold': 750,
        'time_gap_threshold': 37,
        'delete_distance': 145,
        'delete_time': 8,
    },
    {
        'name': 'Current: 800m/40min merge, 100m/5min delete',
        'distance_threshold': 800,
        'time_gap_threshold': 40,
        'delete_distance': 100,
        'delete_time': 5,
    },
]

INPUT_FILE = 'raw/app_data_20250210_all_with_routes.xlsx'

# ============================================================================
# UTILITY FUNCTIONS (from merge and delete scripts)
# ============================================================================

def haversine_distance(lat1, lon1, lat2, lon2):
    """Calculate the great circle distance between two points in meters."""
    lon1, lat1, lon2, lat2 = map(radians, [lon1, lat1, lon2, lat2])
    dlon = lon2 - lon1
    dlat = lat2 - lat1
    a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
    c = 2 * asin(sqrt(a))
    r = 6371000  # Radius of earth in meters
    return c * r

def time_string_to_seconds(time_str):
    """Convert time string (HH:MM:SS or HH:MM:SS.ffffff) to seconds."""
    if pd.isna(time_str) or time_str is None:
        return 0
    
    time_str = str(time_str).strip()
    try:
        parts = time_str.split(':')
        if len(parts) == 3:
            hours = int(parts[0])
            minutes = int(parts[1])
            seconds = float(parts[2])
            total_seconds = hours * 3600 + minutes * 60 + seconds
            return total_seconds
    except:
        pass
    return 0

def seconds_to_time_string(seconds):
    """Convert seconds (float) back to HH:MM:SS format."""
    if seconds == 0:
        return "0:00:00"
    
    total_seconds = int(seconds)
    microseconds = int((seconds - total_seconds) * 1000000)
    
    hours = total_seconds // 3600
    minutes = (total_seconds % 3600) // 60
    secs = total_seconds % 60
    
    if microseconds > 0:
        return f"{hours}:{minutes:02d}:{secs:02d}.{microseconds:06d}"
    else:
        return f"{hours}:{minutes:02d}:{secs:02d}"

def parse_routes(routes_data):
    """Parse routes data - could be JSON string with single quotes."""
    if pd.isna(routes_data) or routes_data is None:
        return None
    
    if isinstance(routes_data, list):
        return routes_data
    
    if isinstance(routes_data, str):
        try:
            return json.loads(routes_data)
        except:
            try:
                routes_data_fixed = routes_data.replace("'", '"')
                return json.loads(routes_data_fixed)
            except:
                return None
    
    return None

def mark_merge_candidates(df, distance_threshold, time_gap_threshold):
    """Mark potential merge candidates."""
    df_copy = df.copy()
    
    df_copy['end_time_dt'] = pd.to_datetime(df_copy['end_time'], errors='coerce')
    df_copy['start_time_dt'] = pd.to_datetime(df_copy['start_time'], errors='coerce')
    
    df_copy['merge_candidate'] = 0
    
    i = 0
    while i < len(df_copy):
        merge_chain = [i]
        j = i
        
        while j < len(df_copy) - 1:
            current = df_copy.iloc[j]
            next_row = df_copy.iloc[j + 1]
            
            if (current['accessCode'] != next_row['accessCode'] or
                current['start_date'] != next_row['start_date'] or
                current['end_date'] != next_row['end_date']):
                break
            
            if pd.isna(current['end_time_dt']) or pd.isna(next_row['start_time_dt']):
                break
            
            time_diff = (next_row['start_time_dt'] - current['end_time_dt']).total_seconds() / 60
            if time_diff < 0 or time_diff > time_gap_threshold:
                break
            
            try:
                current_end_lat = float(current['end_latitude'])
                current_end_lon = float(current['end_longitude'])
                next_start_lat = float(next_row['start_latitude'])
                next_start_lon = float(next_row['start_longitude'])
                
                distance = haversine_distance(current_end_lat, current_end_lon,
                                             next_start_lat, next_start_lon)
                if distance > distance_threshold:
                    break
            except:
                break
            
            merge_chain.append(j + 1)
            j += 1
        
        if len(merge_chain) > 1:
            for idx in merge_chain:
                df_copy.loc[idx, 'merge_candidate'] = 1
        
        i = j + 1
    
    df_copy = df_copy.drop(['end_time_dt', 'start_time_dt'], axis=1)
    return df_copy

def merge_trips(df, distance_threshold, time_gap_threshold):
    """Merge consecutive trips."""
    df_copy = df.copy()
    df_copy['end_time'] = pd.to_datetime(df_copy['end_time'], errors='coerce')
    df_copy['start_time'] = pd.to_datetime(df_copy['start_time'], errors='coerce')
    
    result_rows = []
    processed = set()
    
    for i in range(len(df_copy)):
        if i in processed:
            continue
        
        current_row = df.iloc[i].copy()
        if 'is_merged' not in current_row:
            current_row['is_merged'] = False
        if 'merged_source_rows' not in current_row:
            current_row['merged_source_rows'] = ''
        result_rows.append((current_row, False, None))
        
        merged_indices = [i]
        last_idx = i
        
        for j in range(i + 1, len(df_copy)):
            if j in processed:
                break
            
            current = df_copy.iloc[i]
            next_row = df_copy.iloc[j]
            prev_row = df_copy.iloc[last_idx]
            
            if (current['accessCode'] != next_row['accessCode'] or
                current['start_date'] != next_row['start_date'] or
                current['end_date'] != next_row['end_date']):
                break
            
            if pd.isna(prev_row['end_time']) or pd.isna(next_row['start_time']):
                break
            
            time_diff = (next_row['start_time'] - prev_row['end_time']).total_seconds() / 60
            if time_diff < 0 or time_diff > time_gap_threshold:
                break
            
            try:
                prev_end_lat = float(prev_row['end_latitude'])
                prev_end_lon = float(prev_row['end_longitude'])
                next_start_lat = float(next_row['start_latitude'])
                next_start_lon = float(next_row['start_longitude'])
                
                distance = haversine_distance(prev_end_lat, prev_end_lon,
                                             next_start_lat, next_start_lon)
                if distance > distance_threshold:
                    break
            except:
                break
            
            merged_indices.append(j)
            last_idx = j
        
        if len(merged_indices) > 1:
            for idx in merged_indices[1:]:
                original_row = df.iloc[idx].copy()
                if 'is_merged' not in original_row:
                    original_row['is_merged'] = False
                if 'merged_source_rows' not in original_row:
                    original_row['merged_source_rows'] = ''
                result_rows.append((original_row, False, None))
                processed.add(idx)
            
            merged_row = df.iloc[merged_indices[0]].copy()
            merged_row['end_time'] = df.iloc[merged_indices[-1]]['end_time']
            merged_row['end_latitude'] = df.iloc[merged_indices[-1]]['end_latitude']
            merged_row['end_longitude'] = df.iloc[merged_indices[-1]]['end_longitude']
            
            total_seconds = 0
            for idx in merged_indices:
                row = df.iloc[idx]
                if 'time_duration' in row:
                    duration_str = row['time_duration']
                    total_seconds += time_string_to_seconds(duration_str)
            
            merged_row['time_duration'] = seconds_to_time_string(total_seconds)
            merged_row['is_merged'] = True
            source_rows_str = ', '.join([str(idx + 2) for idx in merged_indices])
            merged_row['merged_source_rows'] = f"Merged from rows: {source_rows_str}"
            merged_row['merge_candidate'] = 2
            
            result_rows.append((merged_row, True, None))
        
        processed.add(i)
    
    new_rows = [row_data for row_data, is_merged, info in result_rows]
    new_df = pd.DataFrame(new_rows)
    return new_df

def mark_deleted_trips(df, delete_distance, delete_time):
    """Mark trips for deletion."""
    df_copy = df.copy()
    df_copy['deleted'] = 0
    
    for i in range(len(df_copy)):
        row = df_copy.iloc[i]
        should_delete = False
        
        try:
            start_lat = float(row['start_latitude'])
            start_lon = float(row['start_longitude'])
            end_lat = float(row['end_latitude'])
            end_lon = float(row['end_longitude'])
            
            distance = haversine_distance(start_lat, start_lon, end_lat, end_lon)
            
            if 'time_duration' in row:
                time_str = str(row['time_duration']).strip()
                try:
                    parts = time_str.split(':')
                    if len(parts) == 3:
                        hours = int(parts[0])
                        minutes = int(parts[1])
                        seconds = float(parts[2])
                        duration_minutes = hours * 60 + minutes + seconds / 60
                    else:
                        duration_minutes = 0
                except:
                    duration_minutes = 0
            else:
                duration_minutes = 0
            
            if distance <= delete_distance and duration_minutes <= delete_time:
                should_delete = True
        except:
            pass
        
        if should_delete:
            df_copy.loc[i, 'deleted'] = 1
    
    return df_copy

def calculate_trips_per_person(df):
    """Calculate trips per person per day statistics (from app.py logic)."""
    # Filter data: keep merge_candidate 0 or 2, and deleted = 0
    if 'merge_candidate' in df.columns and 'deleted' in df.columns:
        filtered_df = df[(df['merge_candidate'].isin([0, 2])) & (df['deleted'] == 0)].copy()
    else:
        filtered_df = df.copy()
    
    # Filter out 'Other' region data (same as app.py)
    if 'region_area' in filtered_df.columns:
        filtered_df = filtered_df[filtered_df['region_area'] != 'Other'].copy()
    
    if len(filtered_df) == 0:
        return {
            'total_trips': 0,
            'unique_people': 0,
            'overall_avg': 0,
            'weekday_avg': 0,
        }
    
    # Calculate trips per person per day
    trips_per_person_per_day = filtered_df.groupby(['accessCode', 'start_date']).size().reset_index(name='trip_count')
    
    # Add weekday info
    weekday_info = filtered_df[['start_date', 'start_weekday']].drop_duplicates()
    trips_per_person_per_day = trips_per_person_per_day.merge(weekday_info, on='start_date', how='left')
    
    overall_avg = round(trips_per_person_per_day['trip_count'].mean(), 2)
    weekday_avg = round(trips_per_person_per_day[~trips_per_person_per_day['start_weekday'].isin(['Saturday', 'Sunday'])]['trip_count'].mean(), 2)
    
    return {
        'total_trips': len(filtered_df),
        'unique_people': filtered_df['accessCode'].nunique(),
        'overall_avg': overall_avg,
        'weekday_avg': weekday_avg,
    }

# ============================================================================
# MAIN TEST FUNCTION
# ============================================================================

def test_parameters():
    """Test different parameter combinations."""
    
    print("\n" + "="*80)
    print("WAVE 2 PARAMETER TESTING")
    print("="*80)
    print(f"Input file: {INPUT_FILE}")
    print(f"Testing {len(PARAMETER_SETS)} parameter combinations\n")
    
    # Load original data
    print("Loading input data...")
    df_original = pd.read_excel(INPUT_FILE)
    print(f"Original data: {len(df_original)} rows\n")
    
    # Test each parameter set
    results = []
    
    for param_set in PARAMETER_SETS:
        print(f"\n{'─'*80}")
        print(f"Testing: {param_set['name']}")
        print(f"  Merge params: distance={param_set['distance_threshold']}m, time_gap={param_set['time_gap_threshold']}min")
        print(f"  Delete params: distance={param_set['delete_distance']}m, time={param_set['delete_time']}min")
        print(f"{'─'*80}")
        
        df = df_original.copy()
        
        # Step 1: Mark merge candidates
        print("  Step 1: Marking merge candidates...")
        df = mark_merge_candidates(df, param_set['distance_threshold'], param_set['time_gap_threshold'])
        merge_count = (df['merge_candidate'] == 1).sum()
        print(f"    Found {merge_count} small trips that could be merged")
        
        # Step 2: Perform merging
        print("  Step 2: Merging trips...")
        df = merge_trips(df, param_set['distance_threshold'], param_set['time_gap_threshold'])
        print(f"    After merge: {len(df)} rows")
        
        # Step 3: Mark deleted trips
        print("  Step 3: Marking trips for deletion...")
        df = mark_deleted_trips(df, param_set['delete_distance'], param_set['delete_time'])
        delete_count = (df['deleted'] == 1).sum()
        print(f"    Found {delete_count} trips marked for deletion")
        
        # Step 4: Calculate statistics
        print("  Step 4: Calculating statistics...")
        stats = calculate_trips_per_person(df)
        
        # Store results
        result = {
            'name': param_set['name'],
            'distance_threshold': param_set['distance_threshold'],
            'time_gap_threshold': param_set['time_gap_threshold'],
            'delete_distance': param_set['delete_distance'],
            'delete_time': param_set['delete_time'],
            'rows_after_merge': len(df),
            'total_trips': stats['total_trips'],
            'unique_people': stats['unique_people'],
            'overall_avg': stats['overall_avg'],
            'weekday_avg': stats['weekday_avg'],
        }
        
        results.append(result)
        
        print(f"  Results:")
        print(f"    Total valid trips: {stats['total_trips']}")
        print(f"    Unique participants: {stats['unique_people']}")
        print(f"    Trip per person per day (overall): {stats['overall_avg']}")
        print(f"    Trip per person per day (weekday): {stats['weekday_avg']}")
    
    # Print comparison table
    print("\n" + "="*80)
    print("SUMMARY: COMPARISON OF ALL PARAMETER SETS")
    print("="*80 + "\n")
    
    # Create comparison dataframe
    comparison_df = pd.DataFrame(results)
    
    # Display in a nice format
    pd.set_option('display.max_columns', None)
    pd.set_option('display.width', None)
    pd.set_option('display.max_colwidth', 30)
    
    print(comparison_df.to_string(index=False))
    
    # Show key insights
    print("\n" + "="*80)
    print("KEY INSIGHTS")
    print("="*80)
    
    min_trips_idx = comparison_df['overall_avg'].idxmin()
    max_trips_idx = comparison_df['overall_avg'].idxmax()
    
    print(f"\nLowest trip per person per day: {comparison_df.loc[min_trips_idx, 'name']}")
    print(f"  → {comparison_df.loc[min_trips_idx, 'overall_avg']} trips/person/day")
    print(f"  → {comparison_df.loc[min_trips_idx, 'total_trips']} total valid trips")
    
    print(f"\nHighest trip per person per day: {comparison_df.loc[max_trips_idx, 'name']}")
    print(f"  → {comparison_df.loc[max_trips_idx, 'overall_avg']} trips/person/day")
    print(f"  → {comparison_df.loc[max_trips_idx, 'total_trips']} total valid trips")
    
    reduction = comparison_df.loc[max_trips_idx, 'overall_avg'] - comparison_df.loc[min_trips_idx, 'overall_avg']
    print(f"\nMaximum reduction potential: {reduction} trips/person/day")
    print(f"  ({reduction / comparison_df.loc[max_trips_idx, 'overall_avg'] * 100:.1f}% reduction)")
    
    # Save results to CSV
    output_file = 'output/parameter_comparison_results.csv'
    os.makedirs(os.path.dirname(output_file), exist_ok=True)
    comparison_df.to_csv(output_file, index=False)
    print(f"\n✓ Results saved to: {output_file}")

if __name__ == '__main__':
    test_parameters()
