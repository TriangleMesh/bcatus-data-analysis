# bcatus-data-analysis

**Backend (Python/Flask)**
- `app.py` - Main Flask application with all API routes
  - `/api/summary-stats` - Statistics dashboard
  - `/api/trips-per-person` - Trip count analysis
  - `/api/trip-purposes` - Purpose distribution
  - `/api/mode-distribution` - Transportation mode analysis
  - `/api/daily-patterns` - Time-based patterns
  - `/api/regions` - Regional analysis
  - Other visualization endpoints

**Data Processing Scripts**
- `1_fill_purpose.py` - Fill missing travel purposes using location clustering
- `1_wave_3_merge.py` - Wave 3 trip merging (Wave 3 specific)
- `2_mode_adjust.py` - Standardize transportation mode values
- `2_wave_3_delete_data.py` - Filter invalid trips for Wave 3
- `3_wave_2_merge.py` - Wave 2 trip merging (Wave 2 specific)
- `4_wave_2_delete_data.py` - Filter invalid trips for Wave 2
- `6_add_region_area.py` - Assign geographic regions using GeoJSON

**Frontend (HTML/CSS/JS)**
- `templates/index.html` - Main dashboard page
- `static/style.css` - Styling
- `static/script.js` - Dashboard interactivity (charts, filters, calculations)

