from flask import Flask, render_template, jsonify, request
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from functools import lru_cache
import os

app = Flask(__name__)

# Data file paths


# Wave 1
# DATA_FILE = 'wave1/Wave 1.xlsx'
DATA_FILE = 'wave1/Wave 1_region.xlsx'

# Wave 2
DATA_FILE = 'output/app_data_20250210_all_deleted_with_filled_purpose_with_adjusted_mode_region.xlsx'
# DATA_FILE = 'raw/app_data_20250210_all_with_routes.xlsx'

# Wave 3
# DATA_FILE = 'wave3_raw/app_data_wave3_20251202.xlsx'
# DATA_FILE = 'wave3_output/app_data_wave3_20251202_merged_deleted_region.xlsx'
TEMP_PROCESSED_FILE = 'output/temp_processed.xlsx'

# Configuration: Set to True if using raw data without merge_candidate and deleted columns
USE_RAW_DATA = False
SHOW_HIDDEN_TRIPS = False

# Cache for processed data
_data_cache = None
_cache_timestamp = None

def clean_text(text):
    """Remove zero-width characters and extra whitespace"""
    if pd.isna(text):
        return text
    # Remove zero-width characters (U+200B, U+200C, U+200D, U+FEFF)
    text = str(text).replace('\u200b', '').replace('\u200c', '').replace('\u200d', '').replace('\ufeff', '')
    # Strip and normalize whitespace
    return text.strip()

def load_and_process_data():
    """Load and process data with caching"""
    global _data_cache, _cache_timestamp
    
    # Check if file has been modified
    file_mtime = os.path.getmtime(DATA_FILE)
    
    # Return cached data if available and file hasn't changed
    if _data_cache is not None and _cache_timestamp == file_mtime:
        return _data_cache
    
    print(f"Loading data from {DATA_FILE}...")
    df = pd.read_excel(DATA_FILE)
    
    # Filter data based on configuration
    if USE_RAW_DATA:
        # Use all data without filtering
        filtered_df = df.copy()
    else:
        # Filter data: keep merge_candidate 0 or 2, and deleted = 0
        filtered_df = df[(df['merge_candidate'].isin([0, 2])) & (df['deleted'] == 0)].copy()
    
    # Clean text columns to remove zero-width characters
    filtered_df['mode_of_travel'] = filtered_df['mode_of_travel'].apply(clean_text)
    filtered_df['purpose_of_travel'] = filtered_df['purpose_of_travel'].apply(clean_text)
    
    # Filter hidden trips based on configuration
    if not SHOW_HIDDEN_TRIPS:
        # Filter out trips where both purpose and mode are None/empty
        def is_empty_value(series):
            return (series.isna() | 
                    (series.astype(str).str.strip() == '') | 
                    (series.astype(str).str.strip().str.lower() == 'empty'))
        
        # Keep trips that have either purpose OR mode (or both)
        original_count = len(filtered_df)
        purpose_empty = is_empty_value(filtered_df['purpose_of_travel'])
        mode_empty = is_empty_value(filtered_df['mode_of_travel'])
        
        # Filter out rows where BOTH purpose AND mode are empty
        filtered_df = filtered_df[~(purpose_empty & mode_empty)].copy()
        hidden_count = original_count - len(filtered_df)
        print(f"Hidden trips filter: removed {hidden_count} trips with both empty purpose and mode")
    
    # Parse time columns with format='mixed' to avoid warnings
    filtered_df['start_time_parsed'] = pd.to_datetime(filtered_df['start_time'], format='mixed', errors='coerce')
    filtered_df['end_time_parsed'] = pd.to_datetime(filtered_df['end_time'], format='mixed', errors='coerce')
    
    # Extract hour from start time
    filtered_df['start_hour'] = filtered_df['start_time_parsed'].dt.hour
    
    # Classify weekday vs weekend
    weekend_days = ['Saturday', 'Sunday']
    filtered_df['day_type'] = filtered_df['start_weekday'].apply(
        lambda x: 'Weekend' if x in weekend_days else 'Weekday'
    )
    
    # Filter out 'Other' region data if region_area column exists
    if 'region_area' in filtered_df.columns:
        filtered_df = filtered_df[filtered_df['region_area'] != 'Other'].copy()
        print(f"Filtered out 'Other' region. Remaining records: {len(filtered_df)}")
    
    # Cache the processed data
    _data_cache = (df, filtered_df)
    _cache_timestamp = file_mtime
    print(f"Data loaded and cached. Total records: {len(df)}, Filtered: {len(filtered_df)}")
    
    return df, filtered_df



@app.route('/')
def index():
    """Main page"""
    return render_template('index.html')

@app.route('/api/trips-per-person')
def get_trips_per_person():
    """Indicator 1: Trips per person per day (should be around 4)
    
    Calculation formulas:
    - overall_avg: Total trips / total days across all users
    - weekday_avg (Mon-Fri): Total weekday trips / total weekday days
    - saturday_avg / sunday_avg: Total weekend trips / total weekend days  
    """
    _, filtered_df = load_and_process_data()
    
    # Calculate trips per person per day
    trips_per_person_per_day = filtered_df.groupby(['accessCode', 'start_date']).size().reset_index(name='trip_count')
    
    # Add weekday info
    weekday_info = filtered_df[['start_date', 'start_weekday']].drop_duplicates()
    trips_per_person_per_day = trips_per_person_per_day.merge(weekday_info, on='start_date', how='left')
    
    overall_avg = round(trips_per_person_per_day['trip_count'].mean(), 2)
    weekday_avg = round(trips_per_person_per_day[~trips_per_person_per_day['start_weekday'].isin(['Saturday', 'Sunday'])]['trip_count'].mean(), 2)
    monday_avg = round(trips_per_person_per_day[trips_per_person_per_day['start_weekday'] == 'Monday']['trip_count'].mean(), 2)
    tuesday_avg = round(trips_per_person_per_day[trips_per_person_per_day['start_weekday'] == 'Tuesday']['trip_count'].mean(), 2)
    wednesday_avg = round(trips_per_person_per_day[trips_per_person_per_day['start_weekday'] == 'Wednesday']['trip_count'].mean(), 2)
    thursday_avg = round(trips_per_person_per_day[trips_per_person_per_day['start_weekday'] == 'Thursday']['trip_count'].mean(), 2)
    friday_avg = round(trips_per_person_per_day[trips_per_person_per_day['start_weekday'] == 'Friday']['trip_count'].mean(), 2)
    saturday_avg = round(trips_per_person_per_day[trips_per_person_per_day['start_weekday'] == 'Saturday']['trip_count'].mean(), 2)
    sunday_avg = round(trips_per_person_per_day[trips_per_person_per_day['start_weekday'] == 'Sunday']['trip_count'].mean(), 2)
    
    # Calculate by region - assign each user to their primary region
    by_region = {}
    if 'region_area' in filtered_df.columns:
        # Determine primary region for each user (region with most trips)
        user_region_counts = filtered_df.groupby(['accessCode', 'region_area']).size().reset_index(name='trip_count')
        primary_regions = user_region_counts.loc[user_region_counts.groupby('accessCode')['trip_count'].idxmax()]
        user_primary_region = dict(zip(primary_regions['accessCode'], primary_regions['region_area']))
        
        for region in ['Vancouver', 'Okanagan']:
            # Get users whose primary region is this region
            region_users = [user for user, primary_region in user_primary_region.items() if primary_region == region]
            region_df = filtered_df[filtered_df['accessCode'].isin(region_users)]
            
            if len(region_df) > 0:
                region_trips_per_person = region_df.groupby(['accessCode', 'start_date']).size().reset_index(name='trip_count')
                region_weekday_info = region_df[['start_date', 'start_weekday']].drop_duplicates()
                region_trips_per_person = region_trips_per_person.merge(region_weekday_info, on='start_date', how='left')
                
                region_monday_avg = round(region_trips_per_person[region_trips_per_person['start_weekday'] == 'Monday']['trip_count'].mean(), 2)
                region_tuesday_avg = round(region_trips_per_person[region_trips_per_person['start_weekday'] == 'Tuesday']['trip_count'].mean(), 2)
                region_wednesday_avg = round(region_trips_per_person[region_trips_per_person['start_weekday'] == 'Wednesday']['trip_count'].mean(), 2)
                region_thursday_avg = round(region_trips_per_person[region_trips_per_person['start_weekday'] == 'Thursday']['trip_count'].mean(), 2)
                region_friday_avg = round(region_trips_per_person[region_trips_per_person['start_weekday'] == 'Friday']['trip_count'].mean(), 2)
                region_saturday_avg = round(region_trips_per_person[region_trips_per_person['start_weekday'] == 'Saturday']['trip_count'].mean(), 2)
                region_sunday_avg = round(region_trips_per_person[region_trips_per_person['start_weekday'] == 'Sunday']['trip_count'].mean(), 2)
                
                by_region[region] = {
                    'overall_avg': round(region_trips_per_person['trip_count'].mean(), 2),
                    'weekday_avg': round(region_trips_per_person[~region_trips_per_person['start_weekday'].isin(['Saturday', 'Sunday'])]['trip_count'].mean(), 2),
                    'monday_avg': region_monday_avg,
                    'tuesday_avg': region_tuesday_avg,
                    'wednesday_avg': region_wednesday_avg,
                    'thursday_avg': region_thursday_avg,
                    'friday_avg': region_friday_avg,
                    'saturday_avg': region_saturday_avg,
                    'sunday_avg': region_sunday_avg,
                    'total_people': len(region_users),
                    'total_trips': len(region_df)
                }
    
    return jsonify({
        'overall_avg': overall_avg,
        'weekday_avg': weekday_avg,
        'monday_avg': monday_avg,
        'tuesday_avg': tuesday_avg,
        'wednesday_avg': wednesday_avg,
        'thursday_avg': thursday_avg,
        'friday_avg': friday_avg,
        'saturday_avg': saturday_avg,
        'sunday_avg': sunday_avg,
        'total_people': filtered_df['accessCode'].nunique(),
        'total_trips': len(filtered_df),
        'by_region': by_region
    })

@app.route('/api/mode-share')
def get_mode_share():
    """Indicator 2: Mode share (Auto-driver should have highest share)
    
    Calculation formulas:
    - count: Number of trips for each mode
    - percentage: count for this mode / total trips * 100
    """
    _, filtered_df = load_and_process_data()
    
    # Count trips by mode
    mode_counts = filtered_df['mode_of_travel'].value_counts()
    total = len(filtered_df)
    
    mode_share = []
    for mode, count in mode_counts.items():
        if pd.notna(mode):
            mode_share.append({
                'mode': str(mode),
                'count': int(count),
                'percentage': round(count / total * 100, 2)
            })
    
    # Sort by count descending
    mode_share.sort(key=lambda x: x['count'], reverse=True)
    
    # Calculate by region
    by_region = {}
    if 'region_area' in filtered_df.columns:
        for region in ['Vancouver', 'Okanagan']:
            region_df = filtered_df[filtered_df['region_area'] == region]
            if len(region_df) > 0:
                region_mode_counts = region_df['mode_of_travel'].value_counts()
                region_total = len(region_df)
                region_mode_share = []
                for mode, count in region_mode_counts.items():
                    if pd.notna(mode):
                        region_mode_share.append({
                            'mode': str(mode),
                            'count': int(count),
                            'percentage': round(count / region_total * 100, 2)
                        })
                region_mode_share.sort(key=lambda x: x['count'], reverse=True)
                by_region[region] = region_mode_share
    
    return jsonify({
        'overall': mode_share,
        'by_region': by_region
    })

@app.route('/api/trip-start-time')
def get_trip_start_time():
    """Indicator 3: Trip start time by hour (should show morning and afternoon peaks on weekdays)
    
    Calculation formulas:
    - count: Number of trips starting at each hour
    - percentage: count at this hour / total trips for this day type * 100
      (Weekday: % of all weekday trips; Saturday/Sunday: % of those respective day trips)
    """
    _, filtered_df = load_and_process_data()
    
    # Filter out rows with invalid start_hour
    valid_df = filtered_df[filtered_df['start_hour'].notna()].copy()
    
    # Weekday distribution
    weekday_df = valid_df[~valid_df['start_weekday'].isin(['Saturday', 'Sunday'])]
    weekday_hourly = weekday_df.groupby('start_hour').size().reindex(range(24), fill_value=0).to_dict()
    weekday_total = sum(weekday_hourly.values())
    weekday_hourly_pct = {str(int(k)): round(v / weekday_total * 100, 2) if weekday_total > 0 else 0 for k, v in weekday_hourly.items()}
    
    # Saturday distribution
    saturday_df = valid_df[valid_df['start_weekday'] == 'Saturday']
    saturday_hourly = saturday_df.groupby('start_hour').size().reindex(range(24), fill_value=0).to_dict()
    saturday_total = sum(saturday_hourly.values())
    saturday_hourly_pct = {str(int(k)): round(v / saturday_total * 100, 2) if saturday_total > 0 else 0 for k, v in saturday_hourly.items()}
    
    # Sunday distribution
    sunday_df = valid_df[valid_df['start_weekday'] == 'Sunday']
    sunday_hourly = sunday_df.groupby('start_hour').size().reindex(range(24), fill_value=0).to_dict()
    sunday_total = sum(sunday_hourly.values())
    sunday_hourly_pct = {str(int(k)): round(v / sunday_total * 100, 2) if sunday_total > 0 else 0 for k, v in sunday_hourly.items()}
    
    # Calculate by region
    by_region = {}
    if 'region_area' in valid_df.columns:
        for region in ['Vancouver', 'Okanagan']:
            region_df = valid_df[valid_df['region_area'] == region]
            if len(region_df) > 0:
                region_weekday_df = region_df[~region_df['start_weekday'].isin(['Saturday', 'Sunday'])]
                region_saturday_df = region_df[region_df['start_weekday'] == 'Saturday']
                region_sunday_df = region_df[region_df['start_weekday'] == 'Sunday']
                
                # Calculate counts and percentages for weekday
                region_weekday_hourly = region_weekday_df.groupby('start_hour').size().reindex(range(24), fill_value=0).to_dict()
                region_weekday_total = sum(region_weekday_hourly.values())
                region_weekday_hourly_pct = {str(int(k)): round(v / region_weekday_total * 100, 2) if region_weekday_total > 0 else 0 for k, v in region_weekday_hourly.items()}
                
                # Calculate counts and percentages for Saturday
                region_saturday_hourly = region_saturday_df.groupby('start_hour').size().reindex(range(24), fill_value=0).to_dict()
                region_saturday_total = sum(region_saturday_hourly.values())
                region_saturday_hourly_pct = {str(int(k)): round(v / region_saturday_total * 100, 2) if region_saturday_total > 0 else 0 for k, v in region_saturday_hourly.items()}
                
                # Calculate counts and percentages for Sunday
                region_sunday_hourly = region_sunday_df.groupby('start_hour').size().reindex(range(24), fill_value=0).to_dict()
                region_sunday_total = sum(region_sunday_hourly.values())
                region_sunday_hourly_pct = {str(int(k)): round(v / region_sunday_total * 100, 2) if region_sunday_total > 0 else 0 for k, v in region_sunday_hourly.items()}
                
                by_region[region] = {
                    'weekday': {str(int(k)): int(v) for k, v in region_weekday_hourly.items()},
                    'weekday_percentage': region_weekday_hourly_pct,
                    'saturday': {str(int(k)): int(v) for k, v in region_saturday_hourly.items()},
                    'saturday_percentage': region_saturday_hourly_pct,
                    'sunday': {str(int(k)): int(v) for k, v in region_sunday_hourly.items()},
                    'sunday_percentage': region_sunday_hourly_pct
                }
    
    return jsonify({
        'weekday': {str(int(k)): int(v) for k, v in weekday_hourly.items()},
        'weekday_percentage': weekday_hourly_pct,
        'saturday': {str(int(k)): int(v) for k, v in saturday_hourly.items()},
        'saturday_percentage': saturday_hourly_pct,
        'sunday': {str(int(k)): int(v) for k, v in sunday_hourly.items()},
        'sunday_percentage': sunday_hourly_pct,
        'by_region': by_region
    })

@app.route('/api/trip-purpose-mode-coverage')
def get_trip_purpose_mode_coverage():
    """Indicator 4: All trips should have trip purposes and modes"""
    _, filtered_df = load_and_process_data()
    
    total_trips = len(filtered_df)
    trips_with_mode = filtered_df['mode_of_travel'].notna().sum()
    trips_with_purpose = filtered_df['purpose_of_travel'].notna().sum()
    trips_with_both = filtered_df[filtered_df['mode_of_travel'].notna() & filtered_df['purpose_of_travel'].notna()].shape[0]
    
    # Calculate by region
    by_region = {}
    if 'region_area' in filtered_df.columns:
        for region in ['Vancouver', 'Okanagan']:
            region_df = filtered_df[filtered_df['region_area'] == region]
            if len(region_df) > 0:
                region_total = len(region_df)
                region_with_mode = region_df['mode_of_travel'].notna().sum()
                region_with_purpose = region_df['purpose_of_travel'].notna().sum()
                region_with_both = region_df[region_df['mode_of_travel'].notna() & region_df['purpose_of_travel'].notna()].shape[0]
                
                by_region[region] = {
                    'total_trips': int(region_total),
                    'trips_with_mode': int(region_with_mode),
                    'trips_with_purpose': int(region_with_purpose),
                    'trips_with_both': int(region_with_both),
                    'mode_coverage_pct': round(region_with_mode / region_total * 100, 2),
                    'purpose_coverage_pct': round(region_with_purpose / region_total * 100, 2)
                }
    
    return jsonify({
        'total_trips': int(total_trips),
        'trips_with_mode': int(trips_with_mode),
        'trips_with_purpose': int(trips_with_purpose),
        'trips_with_both': int(trips_with_both),
        'mode_coverage_pct': round(trips_with_mode / total_trips * 100, 2),
        'purpose_coverage_pct': round(trips_with_purpose / total_trips * 100, 2),
        'by_region': by_region
    })

@app.route('/api/trip-duration')
def get_trip_duration():
    """Indicator 5: Trip duration distribution (10-30 mins should have highest share)
    
    Calculation formulas:
    - count: Number of trips in each duration range
    - avg_duration_minutes: Total duration minutes / count for each range
    """
    _, filtered_df = load_and_process_data()
    
    # Parse duration
    def parse_duration_minutes(duration_str):
        try:
            if pd.isna(duration_str):
                return None
            duration_str = str(duration_str)
            # Handle timedelta format
            if 'days' in duration_str:
                return None  # Skip multi-day trips
            parts = duration_str.split(':')
            if len(parts) >= 2:
                hours = int(parts[0])
                minutes = int(parts[1].split('.')[0])
                return hours * 60 + minutes
        except:
            return None
        return None
    
    filtered_df['duration_minutes'] = filtered_df['time_duration'].apply(parse_duration_minutes)
    
    # Categorize durations
    bins = [0, 10, 30, 60, 120, float('inf')]
    labels = ['0-10 min', '10-30 min', '30-60 min', '1-2 hrs', '>2 hrs']
    
    def process_duration_data(df):
        """Process duration data for a subset of trips"""
        valid_df = df[df['duration_minutes'].notna()].copy()
        if len(valid_df) == 0:
            return [], None
        
        duration_categories = pd.cut(valid_df['duration_minutes'], bins=bins, labels=labels, right=False)
        duration_dist = duration_categories.value_counts().sort_index()
        
        result = []
        max_count = 0
        max_category = None
        
        for category, count in duration_dist.items():
            result.append({
                'category': str(category),
                'count': int(count),
                'percentage': round(count / len(valid_df) * 100, 2)
            })
            if count > max_count:
                max_count = count
                max_category = str(category)
        
        return result, max_category
    
    # Overall data
    overall_data, overall_max = process_duration_data(filtered_df)
    
    # Calculate overall average trip duration
    valid_df_overall = filtered_df[filtered_df['duration_minutes'].notna()].copy()
    overall_avg_duration = round(valid_df_overall['duration_minutes'].mean(), 2) if len(valid_df_overall) > 0 else 0
    
    # Weekday data
    weekday_df = filtered_df[~filtered_df['start_weekday'].isin(['Saturday', 'Sunday'])]
    weekday_data, weekday_max = process_duration_data(weekday_df)
    
    # Saturday data
    saturday_df = filtered_df[filtered_df['start_weekday'] == 'Saturday']
    saturday_data, saturday_max = process_duration_data(saturday_df)
    
    # Sunday data
    sunday_df = filtered_df[filtered_df['start_weekday'] == 'Sunday']
    sunday_data, sunday_max = process_duration_data(sunday_df)
    
    # Requirement: 10-30 min should have highest share (check overall)
    meets_requirement = overall_max == '10-30 min'
    
    # Calculate by region
    by_region = {}
    if 'region_area' in filtered_df.columns:
        for region in ['Vancouver', 'Okanagan']:
            region_df = filtered_df[filtered_df['region_area'] == region]
            if len(region_df) > 0:
                region_overall_data, region_overall_max = process_duration_data(region_df)
                region_weekday_df = region_df[~region_df['start_weekday'].isin(['Saturday', 'Sunday'])]
                region_weekday_data, _ = process_duration_data(region_weekday_df)
                
                by_region[region] = {
                    'overall': region_overall_data,
                    'weekday': region_weekday_data,
                    'meets_requirement': region_overall_max == '10-30 min'
                }
    
    return jsonify({
        'overall': overall_data,
        'overall_avg_duration_minutes': overall_avg_duration,
        'weekday': weekday_data,
        'saturday': saturday_data,
        'sunday': sunday_data,
        'meets_requirement': meets_requirement,
        'by_region': by_region
    })

@app.route('/api/activity-duration')
def get_activity_duration():
    """Indicator 6: Activity duration by purpose (time spent at destination)
    
    Calculation formulas:
    - avg_duration_hours: Sum of duration / count for each purpose
      (Sorted by this in chart - shows average time per activity)
    - total_duration_hours: Sum of all durations for each purpose
    - percentage_of_total in summary: Work/School total_hours / (Work + School) total_hours * 100
    
    Method for Work/School: use stay duration (next trip start - current trip end), summed per day per purpose
    Method for Other purposes: sum the reported time_duration directly
    
    Note: Use fill_purpose.py to pre-fill missing purposes before running this analysis
    """
    _, filtered_df = load_and_process_data()
    
    # Sort by person and time
    sorted_df = filtered_df.sort_values(['accessCode', 'start_time_parsed']).copy()
    
    # ---- Work / School: stay-duration method ----
    daily_purpose_durations = []
    
    for person in sorted_df['accessCode'].unique():
        person_trips = sorted_df[sorted_df['accessCode'] == person].copy()
        person_trips = person_trips.reset_index(drop=True)
        
        # Group by date to calculate daily totals
        for date in person_trips['start_date'].unique():
            daily_trips = person_trips[person_trips['start_date'] == date].copy()
            daily_trips = daily_trips.reset_index(drop=True)
            
            # Calculate stay durations for each trip in this day
            purpose_durations = {}  # purpose -> total duration for this day
            
            for i in range(len(daily_trips) - 1):
                current_trip = daily_trips.iloc[i]
                next_trip = daily_trips.iloc[i + 1]
                
                current_end = current_trip['end_time_parsed']
                next_start = next_trip['start_time_parsed']
                current_purpose_raw = current_trip['purpose_of_travel']
                
                # Normalize purpose: handle NaN, empty strings, whitespace, and "empty" literal
                if pd.isna(current_purpose_raw) or str(current_purpose_raw).strip() == '' or str(current_purpose_raw).strip().lower() == 'empty':
                    current_purpose = None  # Skip unknown purposes
                else:
                    current_purpose = str(current_purpose_raw).strip()
                
                # Only process if we have a valid purpose and it's Work/School
                if current_purpose in ['Work', 'School'] and pd.notna(current_end) and pd.notna(next_start):
                    # Calculate stay duration in hours
                    stay_duration_hours = (next_start - current_end).total_seconds() / 3600
                    
                    # Filter reasonable stay durations: between 0 and 24 hours
                    if 0 < stay_duration_hours < 24:
                        # Add to the total for this purpose on this day
                        if current_purpose not in purpose_durations:
                            purpose_durations[current_purpose] = 0
                        purpose_durations[current_purpose] += stay_duration_hours
            
            # Add daily totals to the overall list
            for purpose, total_duration in purpose_durations.items():
                daily_purpose_durations.append({
                    'duration_hours': total_duration,
                    'purpose': purpose,
                    'user': person,
                    'date': date
                })

    # Build stats for Work / School (stay-duration)
    work_school_result = []
    work_stats = pd.Series(dtype=float)
    school_stats = pd.Series(dtype=float)
    if daily_purpose_durations:
        df_stay = pd.DataFrame(daily_purpose_durations)
        stats_stay = df_stay.groupby('purpose')['duration_hours'].agg([
            ('avg_duration_hours', 'mean'),
            ('total_duration_hours', 'sum'),
            ('count', 'count')
        ]).reset_index()
        for _, row in stats_stay.iterrows():
            work_school_result.append({
                'purpose': row['purpose'],
                'avg_duration_hours': round(row['avg_duration_hours'], 2),
                'total_duration_hours': round(row['total_duration_hours'], 2),
                'count': int(row['count'])
            })
        work_stats = df_stay[df_stay['purpose'] == 'Work']['duration_hours']
        school_stats = df_stay[df_stay['purpose'] == 'School']['duration_hours']

    # ---- Other purposes: sum time_duration ----
    def parse_duration_hours(duration_str):
        try:
            if pd.isna(duration_str):
                return None
            duration_str = str(duration_str)
            if 'days' in duration_str:
                return None  # skip multi-day
            parts = duration_str.split(':')
            if len(parts) >= 2:
                hours = int(parts[0])
                minutes = int(parts[1].split('.')[0])
                return hours + minutes / 60.0
        except Exception:
            return None
        return None

    # Normalize purpose and filter non-work/school
    def normalize_purpose(p):
        if pd.isna(p) or str(p).strip() == '' or str(p).strip().lower() == 'empty':
            return None
        return str(p).strip()

    other_df = filtered_df.copy()
    other_df['purpose_normalized'] = other_df['purpose_of_travel'].apply(normalize_purpose)
    other_df['duration_hours'] = other_df['time_duration'].apply(parse_duration_hours)
    other_df = other_df[
        other_df['purpose_normalized'].notna() &
        other_df['duration_hours'].notna() &
        ~other_df['purpose_normalized'].isin(['Work', 'School'])
    ]

    other_result = []
    if len(other_df) > 0:
        stats_other = other_df.groupby('purpose_normalized')['duration_hours'].agg([
            ('avg_duration_hours', 'mean'),
            ('total_duration_hours', 'sum'),
            ('count', 'count')
        ]).reset_index()
        for _, row in stats_other.iterrows():
            other_result.append({
                'purpose': row['purpose_normalized'],
                'avg_duration_hours': round(row['avg_duration_hours'], 2),
                'total_duration_hours': round(row['total_duration_hours'], 2),
                'count': int(row['count'])
            })

    # Combine results
    combined_result = work_school_result + other_result
    combined_result.sort(key=lambda x: x['avg_duration_hours'], reverse=True)

    # Calculate total hours for summary (work/school percentages only)
    total_work_hours = round(work_stats.sum(), 2) if len(work_stats) > 0 else 0
    total_school_hours = round(school_stats.sum(), 2) if len(school_stats) > 0 else 0
    total_hours_work_school = total_work_hours + total_school_hours
    
    summary = {
        'work': {
            'avg_hours': round(work_stats.mean(), 2) if len(work_stats) > 0 else 0,
            # total_hours: sum of all daily Work duration (calculated from stay-duration method)
            'total_hours': total_work_hours,
            'count': int(len(work_stats)),
            # percentage_of_total: Work total_hours / (Work + School) total_hours * 100
            'percentage_of_total': round(total_work_hours / total_hours_work_school * 100, 2) if total_hours_work_school > 0 else 0
        },
        'school': {
            'avg_hours': round(school_stats.mean(), 2) if len(school_stats) > 0 else 0,
            # total_hours: sum of all daily School duration (calculated from stay-duration method)
            'total_hours': total_school_hours,
            'count': int(len(school_stats)),
            # percentage_of_total: School total_hours / (Work + School) total_hours * 100
            'percentage_of_total': round(total_school_hours / total_hours_work_school * 100, 2) if total_hours_work_school > 0 else 0
        }
    }

    # Calculate by region
    by_region = {}
    if 'region_area' in filtered_df.columns:
        for region in ['Vancouver', 'Okanagan']:
            region_df = filtered_df[filtered_df['region_area'] == region].copy()

            # Sort by person and time
            reg_sorted = region_df.sort_values(['accessCode', 'start_time_parsed']).copy()

            # Work/School stay-duration
            reg_daily = []
            for person in reg_sorted['accessCode'].unique():
                person_trips = reg_sorted[reg_sorted['accessCode'] == person].copy().reset_index(drop=True)
                for date in person_trips['start_date'].unique():
                    daily_trips = person_trips[person_trips['start_date'] == date].copy().reset_index(drop=True)
                    purpose_durations = {}
                    for i in range(len(daily_trips) - 1):
                        current_trip = daily_trips.iloc[i]
                        next_trip = daily_trips.iloc[i + 1]
                        current_end = current_trip['end_time_parsed']
                        next_start = next_trip['start_time_parsed']
                        raw_purpose = current_trip['purpose_of_travel']
                        if pd.isna(raw_purpose) or str(raw_purpose).strip() == '' or str(raw_purpose).strip().lower() == 'empty':
                            current_purpose = None
                        else:
                            current_purpose = str(raw_purpose).strip()
                        if current_purpose in ['Work', 'School'] and pd.notna(current_end) and pd.notna(next_start):
                            stay_h = (next_start - current_end).total_seconds() / 3600
                            if 0 < stay_h < 24:
                                purpose_durations[current_purpose] = purpose_durations.get(current_purpose, 0) + stay_h
                    for purpose, total_h in purpose_durations.items():
                        reg_daily.append({'duration_hours': total_h, 'purpose': purpose, 'user': person, 'date': date})

            reg_ws_result = []
            work_stats = pd.Series(dtype=float)
            school_stats = pd.Series(dtype=float)
            if reg_daily:
                df_stay = pd.DataFrame(reg_daily)
                stats_stay = df_stay.groupby('purpose')['duration_hours'].agg([
                    ('avg_duration_hours', 'mean'),
                    ('total_duration_hours', 'sum'),
                    ('count', 'count')
                ]).reset_index()
                for _, row in stats_stay.iterrows():
                    reg_ws_result.append({
                        'purpose': row['purpose'],
                        'avg_duration_hours': round(row['avg_duration_hours'], 2),
                        'total_duration_hours': round(row['total_duration_hours'], 2),
                        'count': int(row['count'])
                    })
                work_stats = df_stay[df_stay['purpose'] == 'Work']['duration_hours']
                school_stats = df_stay[df_stay['purpose'] == 'School']['duration_hours']

            # Other purposes
            def normalize_purpose(p):
                if pd.isna(p) or str(p).strip() == '' or str(p).strip().lower() == 'empty':
                    return None
                return str(p).strip()

            reg_other = region_df.copy()
            reg_other['purpose_normalized'] = reg_other['purpose_of_travel'].apply(normalize_purpose)
            reg_other['duration_hours'] = reg_other['time_duration'].apply(parse_duration_hours)
            reg_other = reg_other[
                reg_other['purpose_normalized'].notna() &
                reg_other['duration_hours'].notna() &
                ~reg_other['purpose_normalized'].isin(['Work', 'School'])
            ]

            reg_other_result = []
            if len(reg_other) > 0:
                stats_other = reg_other.groupby('purpose_normalized')['duration_hours'].agg([
                    ('avg_duration_hours', 'mean'),
                    ('total_duration_hours', 'sum'),
                    ('count', 'count')
                ]).reset_index()
                for _, row in stats_other.iterrows():
                    reg_other_result.append({
                        'purpose': row['purpose_normalized'],
                        'avg_duration_hours': round(row['avg_duration_hours'], 2),
                        'total_duration_hours': round(row['total_duration_hours'], 2),
                        'count': int(row['count'])
                    })

            reg_combined = reg_ws_result + reg_other_result
            reg_combined.sort(key=lambda x: x['avg_duration_hours'], reverse=True)

            # Calculate totals for work/school summary
            region_total_work_hours = round(work_stats.sum(), 2) if len(work_stats) > 0 else 0
            region_total_school_hours = round(school_stats.sum(), 2) if len(school_stats) > 0 else 0
            region_total_hours_work_school = region_total_work_hours + region_total_school_hours
            
            by_region[region] = {
                'by_purpose': reg_combined,
                'summary': {
                    'work': {
                        'avg_hours': round(work_stats.mean(), 2) if len(work_stats) > 0 else 0,
                        # total_hours: sum of all daily Work duration in this region
                        'total_hours': region_total_work_hours,
                        'count': int(len(work_stats)),
                        # percentage_of_total: Work total_hours / (Work + School) total_hours * 100 for this region
                        'percentage_of_total': round(region_total_work_hours / region_total_hours_work_school * 100, 2) if region_total_hours_work_school > 0 else 0
                    },
                    'school': {
                        'avg_hours': round(school_stats.mean(), 2) if len(school_stats) > 0 else 0,
                        # total_hours: sum of all daily School duration in this region
                        'total_hours': region_total_school_hours,
                        'count': int(len(school_stats)),
                        # percentage_of_total: School total_hours / (Work + School) total_hours * 100 for this region
                        'percentage_of_total': round(region_total_school_hours / region_total_hours_work_school * 100, 2) if region_total_hours_work_school > 0 else 0
                    }
                }
            }
    

    return jsonify({
        'by_purpose': combined_result,
        'summary': summary,
        'by_region': by_region
    })

@app.route('/api/weekday-distribution')
def get_weekday_distribution():
    """Get distribution of users reporting data for each day of the week"""
    _, filtered_df = load_and_process_data()
    
    # Define all 7 days in order
    weekday_order = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
    total_users = filtered_df['accessCode'].nunique()
    
    # Count users for each weekday
    weekday_stats = []
    for day in weekday_order:
        users_with_day = filtered_df[filtered_df['start_weekday'] == day]['accessCode'].nunique()
        users_without_day = total_users - users_with_day
        
        weekday_stats.append({
            'day': day,
            'users_with_data': users_with_day,
            'users_without_data': users_without_day,
            'coverage_percentage': round(users_with_day / total_users * 100, 2) if total_users > 0 else 0
        })
    
    # Calculate by region
    by_region = {}
    if 'region_area' in filtered_df.columns:
        for region in ['Vancouver', 'Okanagan']:
            region_df = filtered_df[filtered_df['region_area'] == region]
            if len(region_df) > 0:
                region_total_users = region_df['accessCode'].nunique()
                region_weekday_stats = []
                
                for day in weekday_order:
                    region_users_with_day = region_df[region_df['start_weekday'] == day]['accessCode'].nunique()
                    region_users_without_day = region_total_users - region_users_with_day
                    
                    region_weekday_stats.append({
                        'day': day,
                        'users_with_data': region_users_with_day,
                        'users_without_data': region_users_without_day,
                        'coverage_percentage': round(region_users_with_day / region_total_users * 100, 2) if region_total_users > 0 else 0
                    })
                
                by_region[region] = {
                    'total_users': region_total_users,
                    'weekday_stats': region_weekday_stats
                }
    
    return jsonify({
        'total_users': total_users,
        'weekday_stats': weekday_stats,
        'by_region': by_region
    })

@app.route('/api/seven-day-coverage')
def get_seven_day_coverage():
    """Check how many users reported data for different numbers of weekdays (1-7 weekdays)"""
    _, filtered_df = load_and_process_data()
    
    # Define all 7 days of the week
    all_weekdays = {'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday'}
    
    # Analyze each user's weekday coverage
    total_users = filtered_df['accessCode'].nunique()
    user_coverage = []
    
    for user in filtered_df['accessCode'].unique():
        user_data = filtered_df[filtered_df['accessCode'] == user]
        # Filter out NaN values from start_weekday before creating set
        reported_days = set(user_data['start_weekday'].dropna().unique())
        
        has_full_week = all_weekdays.issubset(reported_days)
        missing_days = all_weekdays - reported_days
        weekdays_count = len(reported_days)  # Number of different weekdays reported
        
        user_coverage.append({
            'user': user,
            'reported_days': sorted(list(reported_days)),
            'missing_days': sorted(list(missing_days)),
            'has_full_week': has_full_week,
            'weekdays_count': weekdays_count
        })
    
    # Sort by weekdays_count descending
    user_coverage.sort(key=lambda x: x['weekdays_count'], reverse=True)
    
    # Calculate cumulative statistics (X weekdays or more)
    cumulative_stats = []
    for days in range(7, 0, -1):  # 7 down to 1
        users_with_x_or_more_days = sum(
            1 for coverage in user_coverage if coverage['weekdays_count'] >= days
        )
        percentage = round(users_with_x_or_more_days / total_users * 100, 2) if total_users > 0 else 0
        
        cumulative_stats.append({
            'days': days,
            'users_count': users_with_x_or_more_days,
            'percentage': percentage,
            'description': f"{days} weekdays or more"
        })
    
    # Calculate exact weekday statistics
    exact_stats = []
    for days in range(1, 8):  # 1 to 7
        users_count = sum(1 for coverage in user_coverage if coverage['weekdays_count'] == days)
        percentage = round(users_count / total_users * 100, 2) if total_users > 0 else 0
        
        exact_stats.append({
            'days': days,
            'users_count': users_count,
            'percentage': percentage,
            'description': f"exactly {days} weekday{'s' if days != 1 else ''}"
        })
    
    # Count users with full week (7 weekdays)
    users_with_full_week = sum(1 for coverage in user_coverage if coverage['weekdays_count'] == 7)
    
    # Calculate by region
    by_region = {}
    if 'region_area' in filtered_df.columns:
        for region in ['Vancouver', 'Okanagan']:
            region_df = filtered_df[filtered_df['region_area'] == region]
            if len(region_df) > 0:
                region_total_users = region_df['accessCode'].nunique()

                # Build coverage details per user
                region_user_coverage = []
                for user in region_df['accessCode'].unique():
                    user_data = region_df[region_df['accessCode'] == user]
                    reported_days = set(user_data['start_weekday'].dropna().unique())
                    weekdays_count = len(reported_days)
                    region_user_coverage.append({'user': user, 'weekdays_count': weekdays_count})

                # Region cumulative stats
                region_cumulative = []
                for days in range(7, 0, -1):
                    users_x_or_more = sum(1 for cov in region_user_coverage if cov['weekdays_count'] >= days)
                    pct = round(users_x_or_more / region_total_users * 100, 2) if region_total_users > 0 else 0
                    region_cumulative.append({
                        'days': days,
                        'users_count': users_x_or_more,
                        'percentage': pct,
                        'description': f"{days} weekdays or more"
                    })

                # Region exact stats
                region_exact = []
                for days in range(1, 8):
                    users_count = sum(1 for cov in region_user_coverage if cov['weekdays_count'] == days)
                    pct = round(users_count / region_total_users * 100, 2) if region_total_users > 0 else 0
                    region_exact.append({
                        'days': days,
                        'users_count': users_count,
                        'percentage': pct,
                        'description': f"exactly {days} weekday{'s' if days != 1 else ''}"
                    })

                region_full_week = sum(1 for cov in region_user_coverage if cov['weekdays_count'] == 7)

                by_region[region] = {
                    'total_users': region_total_users,
                    'users_with_full_week': region_full_week,
                    'coverage_percentage': round(region_full_week / region_total_users * 100, 2) if region_total_users > 0 else 0,
                    'cumulative_stats': region_cumulative,
                    'exact_stats': region_exact
                }
    
    return jsonify({
        'total_users': total_users,
        'users_with_full_week': users_with_full_week,
        'coverage_percentage': round(users_with_full_week / total_users * 100, 2) if total_users > 0 else 0,
        'cumulative_stats': cumulative_stats,  # X weekdays or more
        'exact_stats': exact_stats,  # Exactly X weekdays
        'user_details': user_coverage[:20],  # Return top 20 for display
        'by_region': by_region
    })

@app.route('/api/purpose-by-hour')
def get_purpose_by_hour():
    """Get trip purpose distribution by hour of day, separated by weekdays and weekends\n    
    Calculation formulas for Saturday/Sunday trips:
    - count: Number of trips for this purpose at this hour
    - percentage: count / total_trips_of_this_purpose_across_all_hours * 100
      (Each purpose's time distribution: what % of trips for this purpose occur at this hour)
    """
    _, filtered_df = load_and_process_data()
    
    # Filter out rows with invalid start_hour or purpose
    valid_df = filtered_df[
        filtered_df['start_hour'].notna() & 
        filtered_df['purpose_of_travel'].notna()
    ].copy()
    
    # Clean and normalize purpose values, filter out unknown purposes
    def normalize_purpose(purpose):
        if pd.isna(purpose) or str(purpose).strip() == '' or str(purpose).strip().lower() == 'empty':
            return None  # Return None for unknown purposes
        return str(purpose).strip()
    
    valid_df['purpose_normalized'] = valid_df['purpose_of_travel'].apply(normalize_purpose)
    
    # Filter out rows with unknown purposes
    valid_df = valid_df[valid_df['purpose_normalized'].notna()].copy()
    
    # Get top purposes (limit to top 6 for readability)
    top_purposes = valid_df['purpose_normalized'].value_counts().head(6).index.tolist()
    
    # Group others into 'Other' category
    valid_df['purpose_grouped'] = valid_df['purpose_normalized'].apply(
        lambda x: x if x in top_purposes else 'Other'
    )
    
    # Calculate hourly distribution for each purpose, separated by day type
    def calculate_hourly_data(df_subset, day_type_name):
        hourly_data = {}
        chart_data = {}
        
        # First, calculate total trips for each purpose in this subset
        purpose_totals = df_subset['purpose_grouped'].value_counts().to_dict()
        
        for hour in range(24):
            hour_data = df_subset[df_subset['start_hour'] == hour]
            total_trips_this_hour = len(hour_data)
            
            purpose_counts = hour_data['purpose_grouped'].value_counts()
            
            hourly_data[hour] = {
                'total_trips': total_trips_this_hour,
                'purposes': {}
            }
            
            # Calculate percentage for each purpose (count / purpose's total trips)
            for purpose in top_purposes + ['Other']:
                count = purpose_counts.get(purpose, 0)
                purpose_total = purpose_totals.get(purpose, 0)
                percentage = round(count / purpose_total * 100, 2) if purpose_total > 0 else 0
                
                hourly_data[hour]['purposes'][purpose] = {
                    'count': int(count),
                    'percentage': percentage
                }
        
        # Prepare data for chart (by purpose)
        for purpose in top_purposes + ['Other']:
            chart_data[purpose] = []
            for hour in range(24):
                chart_data[purpose].append(hourly_data[hour]['purposes'][purpose]['count'])
        
        return {
            'hourly_data': hourly_data,
            'chart_data': chart_data,
            'total_trips': len(df_subset)
        }
    
    # Calculate for weekdays, Saturday, and Sunday separately
    weekday_df = valid_df[~valid_df['start_weekday'].isin(['Saturday', 'Sunday'])]
    saturday_df = valid_df[valid_df['start_weekday'] == 'Saturday']
    sunday_df = valid_df[valid_df['start_weekday'] == 'Sunday']
    
    weekday_results = calculate_hourly_data(weekday_df, 'Weekday')
    saturday_results = calculate_hourly_data(saturday_df, 'Saturday')
    sunday_results = calculate_hourly_data(sunday_df, 'Sunday')
    
    # Calculate by region
    by_region = {}
    if 'region_area' in valid_df.columns:
        for region in ['Vancouver', 'Okanagan']:
            region_df = valid_df[valid_df['region_area'] == region]
            if len(region_df) > 0:
                reg_weekday = region_df[~region_df['start_weekday'].isin(['Saturday', 'Sunday'])]
                reg_saturday = region_df[region_df['start_weekday'] == 'Saturday']
                reg_sunday = region_df[region_df['start_weekday'] == 'Sunday']
                by_region[region] = {
                    'weekday': calculate_hourly_data(reg_weekday, 'Weekday'),
                    'saturday': calculate_hourly_data(reg_saturday, 'Saturday'),
                    'sunday': calculate_hourly_data(reg_sunday, 'Sunday')
                }

    return jsonify({
        'weekday': weekday_results,
        'saturday': saturday_results,
        'sunday': sunday_results,
        'top_purposes': top_purposes + ['Other'],
        'total_trips': len(valid_df),
        'by_region': by_region
    })

@app.route('/api/summary-stats')
def get_summary_stats():
    """Get summary statistics for dashboard"""
    df, filtered_df = load_and_process_data()
    
    trips_per_person_per_day = filtered_df.groupby(['accessCode', 'start_date']).size()
    
    # Determine which file is being used
    current_file = os.path.basename(DATA_FILE)
    is_temp = 'temp' in current_file.lower()
    
    # Calculate 7-day coverage
    all_weekdays = {'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday'}
    users_with_full_week = sum(
        1 for user in filtered_df['accessCode'].unique()
        if all_weekdays.issubset(set(filtered_df[filtered_df['accessCode'] == user]['start_weekday'].dropna().unique()))
    )
    
    # Get date range, handling potential NaN values
    start_dates = filtered_df['start_date'].dropna()
    if len(start_dates) > 0:
        date_range = {
            'start': str(start_dates.min()),
            'end': str(start_dates.max())
        }
    else:
        date_range = {
            'start': 'N/A',
            'end': 'N/A'
        }
    
    # Calculate by region - assign each user to their primary region
    by_region = {}
    if 'region_area' in filtered_df.columns:
        # Determine primary region for each user (region with most trips)
        user_region_counts = filtered_df.groupby(['accessCode', 'region_area']).size().reset_index(name='trip_count')
        primary_regions = user_region_counts.loc[user_region_counts.groupby('accessCode')['trip_count'].idxmax()]
        user_primary_region = dict(zip(primary_regions['accessCode'], primary_regions['region_area']))
        
        for region in ['Vancouver', 'Okanagan']:
            # Get users whose primary region is this region
            region_users = [user for user, primary_region in user_primary_region.items() if primary_region == region]
            region_df = filtered_df[filtered_df['accessCode'].isin(region_users)]
            
            if len(region_df) > 0:
                region_trips_per_person = region_df.groupby(['accessCode', 'start_date']).size()
                region_users_with_full_week = sum(
                    1 for user in region_users
                    if all_weekdays.issubset(set(region_df[region_df['accessCode'] == user]['start_weekday'].dropna().unique()))
                )
                
                by_region[region] = {
                    'total_valid_trips': len(region_df),
                    'unique_participants': len(region_users),
                    'users_with_full_week': region_users_with_full_week,
                    'full_week_percentage': round(region_users_with_full_week / len(region_users) * 100, 2) if len(region_users) > 0 else 0,
                    'avg_trips_per_person_per_day': round(region_trips_per_person.mean(), 2)
                }
    
    return jsonify({
        'total_raw_records': len(df),
        'total_valid_trips': len(filtered_df),
        'unique_participants': filtered_df['accessCode'].nunique(),
        'users_with_full_week': users_with_full_week,
        'full_week_percentage': round(users_with_full_week / filtered_df['accessCode'].nunique() * 100, 2) if filtered_df['accessCode'].nunique() > 0 else 0,
        'avg_trips_per_person_per_day': round(trips_per_person_per_day.mean(), 2),
        'date_range': date_range,
        'current_file': current_file,
        'is_temp_data': is_temp,
        'by_region': by_region
    })

if __name__ == '__main__':
    port = int(os.environ.get('PORT', '5050'))
    # Bind to localhost; change to '0.0.0.0' if you need external access
    app.run(debug=True, host='127.0.0.1', port=port)
