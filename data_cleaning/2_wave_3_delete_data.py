import pandas as pd
import numpy as np
from math import radians, cos, sin, asin, sqrt
import os

DISTANCE_THRESHOLD_METERS = 100
TIME_GAP_THRESHOLD_MINUTES = 5 



def haversine_distance(lat1, lon1, lat2, lon2):
    """
    Calculate the great circle distance between two points 
    on the earth (specified in decimal degrees).
    Returns distance in meters.
    """
    # Convert decimal degrees to radians 
    lon1, lat1, lon2, lat2 = map(radians, [lon1, lat1, lon2, lat2])
    
    # Haversine formula 
    dlon = lon2 - lon1 
    dlat = lat2 - lat1 
    a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
    c = 2 * asin(sqrt(a)) 
    r = 6371000  # Radius of earth in meters
    return c * r

def time_string_to_minutes(time_str):
    """
    Convert time string (HH:MM:SS or HH:MM:SS.ffffff) to minutes.
    Returns float value in minutes.
    """
    if pd.isna(time_str) or time_str is None:
        return 0
    
    time_str = str(time_str).strip()
    try:
        # Parse HH:MM:SS or HH:MM:SS.ffffff format
        parts = time_str.split(':')
        if len(parts) == 3:
            hours = int(parts[0])
            minutes = int(parts[1])
            seconds = float(parts[2])
            total_minutes = hours * 60 + minutes + seconds / 60
            return total_minutes
    except:
        pass
    return 0

def mark_deleted_trips(df):
    """
    Mark trips for deletion if:
    - Distance between start and end points <= DISTANCE_THRESHOLD_METERS AND time_duration <= TIME_GAP_THRESHOLD_MINUTES
    - mode_of_travel is None/NaN/empty
    - purpose_of_travel is None/NaN/empty
    
    Adds a new column 'deleted' with values:
    - 1: marked for deletion
    - 0: keep
    """
    df_copy = df.copy()
    
    # Initialize deleted column
    df_copy['deleted'] = 0
    
    deleted_by_distance_time = 0
    deleted_by_empty_mode = 0
    deleted_by_empty_purpose = 0
    
    for i in range(len(df_copy)):
        row = df_copy.iloc[i]
        should_delete = False
        
        # Check for empty mode_of_travel (None, NaN, empty string, 'empty')
        if 'mode_of_travel' in row:
            mode_value = row['mode_of_travel']
            if mode_value is None or pd.isna(mode_value) or str(mode_value).strip() == '' or str(mode_value).strip().lower() == 'empty':
                should_delete = True
                deleted_by_empty_mode += 1
        
        # Check for empty purpose_of_travel (None, NaN, empty string, 'empty')
        if 'purpose_of_travel' in row:
            purpose_value = row['purpose_of_travel']
            if purpose_value is None or pd.isna(purpose_value) or str(purpose_value).strip() == '' or str(purpose_value).strip().lower() == 'empty':
                should_delete = True
                deleted_by_empty_purpose += 1
        
        # Check distance and time conditions
        try:
            # Get coordinates
            start_lat = float(row['start_latitude'])
            start_lon = float(row['start_longitude'])
            end_lat = float(row['end_latitude'])
            end_lon = float(row['end_longitude'])
            
            # Calculate distance between start and end
            distance = haversine_distance(start_lat, start_lon, end_lat, end_lon)
            
            # Get time duration in minutes
            if 'time_duration' in row:
                duration_minutes = time_string_to_minutes(row['time_duration'])
            else:
                duration_minutes = 0
            
            # Check if both conditions are met
            if distance <= DISTANCE_THRESHOLD_METERS and duration_minutes <= TIME_GAP_THRESHOLD_MINUTES:
                should_delete = True
                deleted_by_distance_time += 1
                
        except Exception as e:
            # If there's any error (missing values, invalid data), skip distance/time check
            pass
        
        # Mark for deletion if any condition is met
        if should_delete:
            df_copy.loc[i, 'deleted'] = 1
    
    print(f"\nDeletion breakdown:")
    print(f"  By distance & time: {deleted_by_distance_time}")
    print(f"  By empty mode: {deleted_by_empty_mode}")
    print(f"  By empty purpose: {deleted_by_empty_purpose}")
    print(f"  Note: A trip may be counted in multiple categories")
    
    return df_copy

def main():
    # File paths
    input_file = 'wave3_output/app_data_wave3_20251202_merged.xlsx'
    output_file = 'wave3_output/app_data_wave3_20251202_merged_deleted_without_empty_purpose.xlsx'
    
    # Create output directory if it doesn't exist
    os.makedirs(os.path.dirname(output_file), exist_ok=True)
    
    # Read the Excel file
    print(f"Reading file: {input_file}")
    df = pd.read_excel(input_file)
    
    print(f"Total rows: {len(df)}")
    print(f"Columns: {list(df.columns)}")
    
    # Mark trips for deletion
    print("\nMarking trips for deletion...")
    df_marked = mark_deleted_trips(df)
    
    deleted_count = df_marked['deleted'].sum()
    print(f"Found {deleted_count} trips marked for deletion")
    print(f"Criteria: distance <= {DISTANCE_THRESHOLD_METERS}m AND time_duration <= {TIME_GAP_THRESHOLD_MINUTES} minutes")
    
    # Save to Excel first (to get the data written)
    print(f"\nSaving to: {output_file}")
    df_marked.to_excel(output_file, index=False, engine='openpyxl')
    
    print(f"\nDone! Output file: {output_file}")
    print(f"Total rows: {len(df_marked)}")
    print(f"Rows marked for deletion: {deleted_count}")
    print(f"Rows to keep: {len(df_marked) - deleted_count}")

if __name__ == "__main__":
    main()