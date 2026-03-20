"""
Adjust mode_of_travel values in the dataset

This script:
1. Loads the processed data
2. Converts 'Auto Passenger' to 'Auto Driver' in mode_of_travel column
3. Adds a 'mode_adjusted' column (0=original, 1=adjusted)
4. Saves the adjusted data back to Excel
"""

import pandas as pd

# ==================== CONFIGURATION ====================
# File paths
INPUT_FILE = 'output/app_data_20250210_fill_purpose.xlsx'
OUTPUT_FILE = 'output/app_data_20250210_fill_purpose_adjust_mode.xlsx'

# Mode conversion mapping
MODE_CONVERSIONS = {
    'Auto Passenger': 'Auto Driver'
}
# =======================================================


def clean_text(text):
    """Remove zero-width characters and extra whitespace"""
    if pd.isna(text):
        return text
    # Remove zero-width characters (U+200B, U+200C, U+200D, U+FEFF)
    text = str(text).replace('\u200b', '').replace('\u200c', '').replace('\u200d', '').replace('\ufeff', '')
    # Strip and normalize whitespace
    return text.strip()


def adjust_modes(df):
    """
    Adjust mode_of_travel values according to MODE_CONVERSIONS
    
    Args:
        df: DataFrame with trip data
        
    Returns:
        DataFrame with adjusted modes and mode_adjusted column
    """
    # Create a copy to avoid modifying original
    df_adjusted = df.copy()
    
    # First, clean all mode_of_travel values
    print("\nCleaning mode_of_travel values...")
    df_adjusted['mode_of_travel'] = df_adjusted['mode_of_travel'].apply(clean_text)
    
    # Add mode_adjusted column (0 = original, 1 = adjusted by code)
    df_adjusted['mode_adjusted'] = 0
    
    # Track statistics
    total_adjusted = 0
    adjustment_details = {}
    
    for old_mode, new_mode in MODE_CONVERSIONS.items():
        # Clean the old_mode for comparison
        old_mode_clean = clean_text(old_mode)
        
        # Find rows with the old mode (case-insensitive and whitespace-insensitive)
        mask = df_adjusted['mode_of_travel'].str.lower().str.strip() == old_mode_clean.lower().strip()
        count = mask.sum()
        
        if count > 0:
            # Convert to new mode
            df_adjusted.loc[mask, 'mode_of_travel'] = new_mode
            df_adjusted.loc[mask, 'mode_adjusted'] = 1
            
            total_adjusted += count
            adjustment_details[old_mode] = {'new_mode': new_mode, 'count': count}
            
            # Show some examples of what was matched
            matched_values = df_adjusted[mask]['mode_of_travel'].head(3).tolist()
            print(f"  Matched variations of '{old_mode}': {matched_values}")
    
    print(f"\nMode Adjustment Summary:")
    print(f"  Total adjusted: {total_adjusted}")
    
    if adjustment_details:
        print(f"\nAdjustment details:")
        for old_mode, details in adjustment_details.items():
            print(f"  '{old_mode}' → '{details['new_mode']}': {details['count']} records")
    else:
        print(f"  No records matched the conversion rules")
    
    return df_adjusted


def main():
    """Main function to process and adjust modes"""
    print("=" * 60)
    print("MODE ADJUSTMENT CONFIGURATION")
    print("=" * 60)
    print("Mode conversions:")
    for old_mode, new_mode in MODE_CONVERSIONS.items():
        print(f"  '{old_mode}' → '{new_mode}'")
    print("=" * 60)
    
    print(f"\nLoading data from {INPUT_FILE}...")
    df = pd.read_excel(INPUT_FILE)
    
    print(f"Total records: {len(df)}")
    print(f"Unique users: {df['accessCode'].nunique()}")
    
    # Check current mode distribution
    print(f"\nCurrent mode distribution (before cleaning):")
    mode_counts = df['mode_of_travel'].value_counts()
    for mode, count in mode_counts.head(10).items():
        if pd.notna(mode):
            # Show repr to reveal hidden characters
            print(f"  {repr(mode)}: {count} ({count / len(df) * 100:.1f}%)")
    
    # Check for modes that will be converted (with fuzzy matching)
    print(f"\nSearching for modes to be converted (case-insensitive):")
    for old_mode in MODE_CONVERSIONS.keys():
        # Exact match
        exact_count = (df['mode_of_travel'] == old_mode).sum()
        # Case-insensitive match
        fuzzy_mask = df['mode_of_travel'].astype(str).str.lower().str.strip() == old_mode.lower().strip()
        fuzzy_count = fuzzy_mask.sum()
        
        print(f"  '{old_mode}':")
        print(f"    Exact match: {exact_count} records")
        print(f"    Case-insensitive match: {fuzzy_count} records")
        
        # Show unique variations
        if fuzzy_count > 0:
            variations = df[fuzzy_mask]['mode_of_travel'].unique()
            print(f"    Variations found: {[repr(v) for v in variations[:5]]}")
    
    # Adjust modes
    print("\nAdjusting modes...")
    df_adjusted = adjust_modes(df)
    
    # Check new mode distribution
    print(f"\nNew mode distribution:")
    mode_counts_after = df_adjusted['mode_of_travel'].value_counts()
    for mode, count in mode_counts_after.items():
        if pd.notna(mode):
            print(f"  {mode}: {count} ({count / len(df_adjusted) * 100:.1f}%)")
    
    # Save to Excel
    print(f"\nSaving adjusted data to {OUTPUT_FILE}...")
    df_adjusted.to_excel(OUTPUT_FILE, index=False)
    print("Done!")


if __name__ == '__main__':
    main()
