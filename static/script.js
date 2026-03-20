// Chart color schemes
const colors = {
    primary: 'rgba(102, 126, 234, 0.8)',
    secondary: 'rgba(118, 75, 162, 0.8)',
    success: 'rgba(72, 187, 120, 0.8)',
    warning: 'rgba(237, 137, 54, 0.8)',
    danger: 'rgba(245, 101, 101, 0.8)',
    info: 'rgba(66, 153, 225, 0.8)'
};

const colorPalette = [
    'rgba(102, 126, 234, 0.8)',
    'rgba(118, 75, 162, 0.8)',
    'rgba(72, 187, 120, 0.8)',
    'rgba(237, 137, 54, 0.8)',
    'rgba(245, 101, 101, 0.8)',
    'rgba(66, 153, 225, 0.8)',
    'rgba(159, 122, 234, 0.8)',
    'rgba(237, 100, 166, 0.8)'
];

// Load summary statistics
async function loadSummaryStats() {
    try {
        const response = await fetch('/api/summary-stats');
        const data = await response.json();

        document.getElementById('total-trips').textContent = data.total_valid_trips.toLocaleString();
        document.getElementById('unique-people').textContent = data.unique_participants;
        document.getElementById('full-week-users').textContent = data.users_with_full_week;
        document.getElementById('full-week-percentage').textContent = `${data.full_week_percentage}% with all 7 days`;
        document.getElementById('avg-trips').textContent = data.avg_trips_per_person_per_day;
        document.getElementById('date-range').textContent = `${data.date_range.start} to ${data.date_range.end}`;
        
        // Update data source info
        const fileElement = document.getElementById('current-file');
        if (fileElement) {
            fileElement.textContent = data.current_file;
            if (data.is_temp_data) {
                fileElement.classList.add('temp-data');
                fileElement.title = 'Using temporarily processed data with custom parameters';
            } else {
                fileElement.classList.remove('temp-data');
                fileElement.title = 'Using original processed data';
            }
        }

        // Display regional statistics
        if (data.by_region) {
            const regionalStatsDiv = document.getElementById('regional-stats');
            regionalStatsDiv.innerHTML = '';
            
            // Define the order of regions to display (removed 'Other')
            const regionOrder = ['Vancouver', 'Okanagan'];
            
            for (const region of regionOrder) {
                if (data.by_region[region]) {
                    const stats = data.by_region[region];
                    const statCard = document.createElement('div');
                    statCard.className = 'stat-card';
                    statCard.innerHTML = `
                        <h3>${region}</h3>
                        <p class="stat-value">${stats.total_valid_trips.toLocaleString()} trips</p>
                        <p class="stat-note">${stats.unique_participants} participants</p>
                        <p class="stat-note">${stats.avg_trips_per_person_per_day} trips/person/day</p>
                        <p class="stat-note">${stats.full_week_percentage}% full week</p>
                    `;
                    regionalStatsDiv.appendChild(statCard);
                }
            }
        }
    } catch (error) {
        console.error('Error loading summary stats:', error);
    }
}

// Indicator 1: Trips per Person per Day
async function loadTripsPerPerson() {
    try {
        const response = await fetch('/api/trips-per-person');
        const data = await response.json();

        // All values including new weekday data
        const allValues = [
            data.overall_avg, 
            data.weekday_avg, 
            data.monday_avg, 
            data.tuesday_avg, 
            data.wednesday_avg, 
            data.thursday_avg, 
            data.friday_avg, 
            data.saturday_avg, 
            data.sunday_avg
        ];
        const minValue = Math.min(...allValues);
        const maxValue = Math.max(...allValues);

        // Set Y-axis range to emphasize differences (add 50% padding)
        const range = maxValue - minValue;
        const yMin = Math.max(0, minValue - range * 0.5);
        const yMax = maxValue + range * 0.5;

        const ctx = document.getElementById('tripsPerPersonChart').getContext('2d');
        new Chart(ctx, {
            type: 'bar',
            data: {
                labels: ['Overall', 'Weekday Avg', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday'],
                datasets: [{
                    label: 'Trips per Person per Day',
                    data: [data.overall_avg, data.weekday_avg, data.monday_avg, data.tuesday_avg, data.wednesday_avg, data.thursday_avg, data.friday_avg, data.saturday_avg, data.sunday_avg],
                    backgroundColor: [
                        colors.primary, colors.secondary, 
                        colors.info, colors.info, colors.info, colors.info, colors.info, 
                        colors.success, colors.warning
                    ],
                    borderColor: [
                        colors.primary, colors.secondary, 
                        colors.info, colors.info, colors.info, colors.info, colors.info, 
                        colors.success, colors.warning
                    ],
                    borderWidth: 2
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: true,
                scales: {
                    y: {
                        beginAtZero: false,
                        min: yMin,
                        max: yMax,
                        title: {
                            display: true,
                            text: 'Average Trips per Day'
                        },
                        ticks: {
                            stepSize: 0.1
                        }
                    }
                },
                plugins: {
                    legend: {
                        display: false
                    },
                    tooltip: {
                        callbacks: {
                            label: function (context) {
                                return `${context.parsed.y.toFixed(2)} trips/day`;
                            }
                        }
                    }
                }
            }
        });

        // Region comparison chart
        if (data.by_region) {
            const ctxRegion = document.getElementById('tripsPerPersonRegionChart').getContext('2d');
            const regions = Object.keys(data.by_region).filter(r => ['Vancouver','Okanagan','Other'].includes(r));
            const regionColors = {
                'Vancouver': 'rgba(102, 126, 234, 0.8)',
                'Okanagan': 'rgba(237, 137, 54, 0.8)',
                'Other': 'rgba(72, 187, 120, 0.8)'
            };

            new Chart(ctxRegion, {
                type: 'bar',
                data: {
                    labels: regions,
                    datasets: [
                        {
                            label: 'Overall Average',
                            data: regions.map(r => data.by_region[r].overall_avg),
                            backgroundColor: regions.map(r => regionColors[r]),
                            borderColor: regions.map(r => regionColors[r]),
                            borderWidth: 2
                        },
                        {
                            label: 'Weekday Average',
                            data: regions.map(r => data.by_region[r].weekday_avg),
                            backgroundColor: regions.map(r => regionColors[r].replace('0.8', '0.6')),
                            borderColor: regions.map(r => regionColors[r]),
                            borderWidth: 2
                        },
                        {
                            label: 'Monday',
                            data: regions.map(r => data.by_region[r].monday_avg),
                            backgroundColor: regions.map(r => regionColors[r].replace('0.8', '0.5')),
                            borderColor: regions.map(r => regionColors[r]),
                            borderWidth: 1
                        },
                        {
                            label: 'Tuesday',
                            data: regions.map(r => data.by_region[r].tuesday_avg),
                            backgroundColor: regions.map(r => regionColors[r].replace('0.8', '0.45')),
                            borderColor: regions.map(r => regionColors[r]),
                            borderWidth: 1
                        },
                        {
                            label: 'Wednesday',
                            data: regions.map(r => data.by_region[r].wednesday_avg),
                            backgroundColor: regions.map(r => regionColors[r].replace('0.8', '0.4')),
                            borderColor: regions.map(r => regionColors[r]),
                            borderWidth: 1
                        },
                        {
                            label: 'Thursday',
                            data: regions.map(r => data.by_region[r].thursday_avg),
                            backgroundColor: regions.map(r => regionColors[r].replace('0.8', '0.35')),
                            borderColor: regions.map(r => regionColors[r]),
                            borderWidth: 1
                        },
                        {
                            label: 'Friday',
                            data: regions.map(r => data.by_region[r].friday_avg),
                            backgroundColor: regions.map(r => regionColors[r].replace('0.8', '0.3')),
                            borderColor: regions.map(r => regionColors[r]),
                            borderWidth: 1
                        },
                        {
                            label: 'Saturday',
                            data: regions.map(r => data.by_region[r].saturday_avg),
                            backgroundColor: regions.map(r => regionColors[r].replace('0.8', '0.25')),
                            borderColor: regions.map(r => regionColors[r]),
                            borderWidth: 1
                        },
                        {
                            label: 'Sunday',
                            data: regions.map(r => data.by_region[r].sunday_avg),
                            backgroundColor: regions.map(r => regionColors[r].replace('0.8', '0.15')),
                            borderColor: regions.map(r => regionColors[r]),
                            borderWidth: 1
                        }
                    ]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: true,
                    scales: {
                        y: {
                            beginAtZero: true,
                            title: {
                                display: true,
                                text: 'Average Trips per Day'
                            }
                        }
                    },
                    plugins: {
                        legend: {
                            display: true,
                            position: 'top'
                        },
                        tooltip: {
                            callbacks: {
                                label: function (context) {
                                    return `${context.dataset.label}: ${context.parsed.y.toFixed(2)} trips/day`;
                                }
                            }
                        }
                    }
                }
            });
        }
    } catch (error) {
        console.error('Error loading trips per person:', error);
    }
}

// Indicator 2: Mode Share
async function loadModeShare() {
    try {
        const response = await fetch('/api/mode-share');
        const data = await response.json();

        const ctx = document.getElementById('modeShareChart').getContext('2d');
        new Chart(ctx, {
            type: 'bar',
            data: {
                labels: data.overall.map(d => d.mode),
                datasets: [{
                    label: 'Number of Trips',
                    data: data.overall.map(d => d.count),
                    backgroundColor: colorPalette.slice(0, data.overall.length),
                    borderColor: colorPalette.slice(0, data.overall.length),
                    borderWidth: 2
                }]
            },
            options: {
                indexAxis: 'y',
                responsive: true,
                maintainAspectRatio: true,
                scales: {
                    x: {
                        beginAtZero: true,
                        title: {
                            display: true,
                            text: 'Number of Trips'
                        }
                    }
                },
                plugins: {
                    legend: {
                        display: false
                    },
                    tooltip: {
                        callbacks: {
                            label: function (context) {
                                const item = data.overall[context.dataIndex];
                                return `${item.count} trips (${item.percentage}%)`;
                            }
                        }
                    }
                }
            }
        });

        // Region comparison chart for top 5 modes
        if (data.by_region) {
            const top5Modes = data.overall.slice(0, 5).map(d => d.mode);
            const regions = Object.keys(data.by_region).filter(r => ['Vancouver','Okanagan','Other'].includes(r));
            const regionColors = {
                'Vancouver': 'rgba(102, 126, 234, 0.8)',
                'Okanagan': 'rgba(237, 137, 54, 0.8)',
                'Other': 'rgba(72, 187, 120, 0.8)'
            };

            const datasets = regions.map(region => {
                const regionData = data.by_region[region];
                const modeMap = {};
                regionData.forEach(item => {
                    modeMap[item.mode] = item.percentage;
                });
                
                return {
                    label: region,
                    data: top5Modes.map(mode => modeMap[mode] || 0),
                    backgroundColor: regionColors[region],
                    borderColor: regionColors[region],
                    borderWidth: 2
                };
            });

            const ctxRegion = document.getElementById('modeShareRegionChart').getContext('2d');
            new Chart(ctxRegion, {
                type: 'bar',
                data: {
                    labels: top5Modes,
                    datasets: datasets
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: true,
                    scales: {
                        y: {
                            beginAtZero: true,
                            title: {
                                display: true,
                                text: 'Percentage (%)'
                            }
                        }
                    },
                    plugins: {
                        legend: {
                            display: true,
                            position: 'top'
                        },
                        tooltip: {
                            callbacks: {
                                label: function (context) {
                                    return `${context.dataset.label}: ${context.parsed.y.toFixed(2)}%`;
                                }
                            }
                        }
                    }
                }
            });
        }
    } catch (error) {
        console.error('Error loading mode share:', error);
    }
}

// Indicator 3: Trip Start Time
async function loadTripStartTime() {
    try {
        const response = await fetch('/api/trip-start-time');
        const data = await response.json();

        const hours = Array.from({ length: 24 }, (_, i) => i);

        // Weekday chart - with count
        const ctxWeekday = document.getElementById('startTimeWeekdayChart').getContext('2d');
        new Chart(ctxWeekday, {
            type: 'line',
            data: {
                labels: hours.map(h => `${h}:00`),
                datasets: [{
                    label: 'Weekday Trip Starts (Count)',
                    data: hours.map(h => data.weekday[h] || 0),
                    backgroundColor: colors.primary,
                    borderColor: colors.primary,
                    borderWidth: 2,
                    fill: true,
                    tension: 0.4,
                    yAxisID: 'y'
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: true,
                scales: {
                    y: {
                        beginAtZero: true,
                        position: 'left',
                        title: {
                            display: true,
                            text: 'Number of Trips'
                        }
                    },
                    y1: {
                        type: 'linear',
                        position: 'right',
                        beginAtZero: true,
                        max: 100,
                        title: {
                            display: true,
                            text: 'Percentage (%)'
                        },
                        grid: { drawOnChartArea: false }
                    },
                    x: {
                        title: {
                            display: true,
                            text: 'Hour of Day'
                        }
                    }
                },
                plugins: {
                    title: {
                        display: true,
                        text: 'Weekday Trip Start Times'
                    },
                    legend: {
                        display: true
                    }
                }
            }
        });
        
        // Add percentage chart for weekday
        const ctxWeekdayPercentage = document.createElement('canvas');
        ctxWeekdayPercentage.id = 'startTimeWeekdayPercentageChart';
        ctxWeekdayPercentage.style.marginTop = '20px';
        document.getElementById('startTimeWeekdayChart').parentNode.appendChild(ctxWeekdayPercentage);
        
        // Calculate max percentage for dynamic scaling
        const weekdayPctValues = hours.map(h => data.weekday_percentage ? parseFloat(data.weekday_percentage[h]) || 0 : 0);
        const weekdayPctMax = Math.max(...weekdayPctValues) * 1.2; // Add 20% padding
        
        new Chart(ctxWeekdayPercentage.getContext('2d'), {
            type: 'line',
            data: {
                labels: hours.map(h => `${h}:00`),
                datasets: [{
                    label: 'Weekday Trip Starts (%)',
                    data: weekdayPctValues,
                    backgroundColor: 'rgba(102, 126, 234, 0.2)',
                    borderColor: colors.primary,
                    borderWidth: 2,
                    fill: true,
                    tension: 0.4
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: true,
                scales: {
                    y: {
                        beginAtZero: true,
                        max: weekdayPctMax,
                        title: {
                            display: true,
                            text: 'Percentage (%)'
                        }
                    },
                    x: {
                        title: {
                            display: true,
                            text: 'Hour of Day'
                        }
                    }
                },
                plugins: {
                    title: {
                        display: true,
                        text: 'Weekday Trip Start Times (%)'
                    },
                    legend: {
                        display: false
                    }
                }
            }
        });

        // Saturday chart with percentage
        const ctxSaturday = document.getElementById('startTimeSaturdayChart').getContext('2d');
        new Chart(ctxSaturday, {
            type: 'line',
            data: {
                labels: hours.map(h => `${h}:00`),
                datasets: [{
                    label: 'Saturday Trip Starts (Count)',
                    data: hours.map(h => data.saturday[h] || 0),
                    backgroundColor: colors.success,
                    borderColor: colors.success,
                    borderWidth: 2,
                    fill: true,
                    tension: 0.4
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: true,
                scales: {
                    y: {
                        beginAtZero: true,
                        title: {
                            display: true,
                            text: 'Number of Trips'
                        }
                    },
                    x: {
                        title: {
                            display: true,
                            text: 'Hour of Day'
                        }
                    }
                },
                plugins: {
                    legend: {
                        display: true
                    }
                }
            }
        });
        
        // Add percentage chart for Saturday
        const ctxSaturdayPercentage = document.createElement('canvas');
        ctxSaturdayPercentage.id = 'startTimeSaturdayPercentageChart';
        ctxSaturdayPercentage.style.marginTop = '20px';
        document.getElementById('startTimeSaturdayChart').parentNode.appendChild(ctxSaturdayPercentage);
        
        // Calculate max percentage for dynamic scaling
        const saturdayPctValues = hours.map(h => data.saturday_percentage ? parseFloat(data.saturday_percentage[h]) || 0 : 0);
        const saturdayPctMax = Math.max(...saturdayPctValues) * 1.2;
        
        new Chart(ctxSaturdayPercentage.getContext('2d'), {
            type: 'line',
            data: {
                labels: hours.map(h => `${h}:00`),
                datasets: [{
                    label: 'Saturday Trip Starts (%)',
                    data: saturdayPctValues,
                    backgroundColor: 'rgba(72, 187, 120, 0.2)',
                    borderColor: colors.success,
                    borderWidth: 2,
                    fill: true,
                    tension: 0.4
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: true,
                scales: {
                    y: {
                        beginAtZero: true,
                        max: saturdayPctMax,
                        title: {
                            display: true,
                            text: 'Percentage (%)'
                        }
                    },
                    x: {
                        title: {
                            display: true,
                            text: 'Hour of Day'
                        }
                    }
                },
                plugins: {
                    legend: {
                        display: false
                    }
                }
            }
        });

        // Sunday chart with percentage
        const ctxSunday = document.getElementById('startTimeSundayChart').getContext('2d');
        new Chart(ctxSunday, {
            type: 'line',
            data: {
                labels: hours.map(h => `${h}:00`),
                datasets: [{
                    label: 'Sunday Trip Starts (Count)',
                    data: hours.map(h => data.sunday[h] || 0),
                    backgroundColor: colors.warning,
                    borderColor: colors.warning,
                    borderWidth: 2,
                    fill: true,
                    tension: 0.4
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: true,
                scales: {
                    y: {
                        beginAtZero: true,
                        title: {
                            display: true,
                            text: 'Number of Trips'
                        }
                    },
                    x: {
                        title: {
                            display: true,
                            text: 'Hour of Day'
                        }
                    }
                },
                plugins: {
                    legend: {
                        display: true
                    }
                }
            }
        });
        
        // Add percentage chart for Sunday
        const ctxSundayPercentage = document.createElement('canvas');
        ctxSundayPercentage.id = 'startTimeSundayPercentageChart';
        ctxSundayPercentage.style.marginTop = '20px';
        document.getElementById('startTimeSundayChart').parentNode.appendChild(ctxSundayPercentage);
        
        // Calculate max percentage for dynamic scaling
        const sundayPctValues = hours.map(h => data.sunday_percentage ? parseFloat(data.sunday_percentage[h]) || 0 : 0);
        const sundayPctMax = Math.max(...sundayPctValues) * 1.2;
        
        new Chart(ctxSundayPercentage.getContext('2d'), {
            type: 'line',
            data: {
                labels: hours.map(h => `${h}:00`),
                datasets: [{
                    label: 'Sunday Trip Starts (%)',
                    data: sundayPctValues,
                    backgroundColor: 'rgba(237, 137, 54, 0.2)',
                    borderColor: colors.warning,
                    borderWidth: 2,
                    fill: true,
                    tension: 0.4
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: true,
                scales: {
                    y: {
                        beginAtZero: true,
                        max: sundayPctMax,
                        title: {
                            display: true,
                            text: 'Percentage (%)'
                        }
                    },
                    x: {
                        title: {
                            display: true,
                            text: 'Hour of Day'
                        }
                    }
                },
                plugins: {
                    legend: {
                        display: false
                    }
                }
            }
        });
        // Region comparison chart: Weekday only
        if (data.by_region) {
            const regions = Object.keys(data.by_region).filter(r => ['Vancouver','Okanagan','Other'].includes(r));
            const regionColors = {
                'Vancouver': 'rgba(102, 126, 234, 0.8)',
                'Okanagan': 'rgba(237, 137, 54, 0.8)',
                'Other': 'rgba(72, 187, 120, 0.8)'
            };
            const canvas = document.getElementById('startTimeWeekdayRegionChart');
            if (canvas) {
                const ctxRegion = canvas.getContext('2d');
                new Chart(ctxRegion, {
                    type: 'line',
                    data: {
                        labels: hours.map(h => `${h}:00`),
                        datasets: regions.map(region => ({
                            label: `${region} Weekday`,
                            data: hours.map(h => {
                                const dict = data.by_region[region].weekday || {};
                                const key = String(h);
                                return dict[key] || 0;
                            }),
                            backgroundColor: regionColors[region],
                            borderColor: regionColors[region],
                            borderWidth: 2,
                            fill: false,
                            tension: 0.4
                        }))
                    },
                    options: {
                        responsive: true,
                        maintainAspectRatio: true,
                        scales: {
                            y: { beginAtZero: true, title: { display: true, text: 'Number of Trips' } },
                            x: { title: { display: true, text: 'Hour of Day' } }
                        },
                        plugins: { legend: { display: true, position: 'top' } }
                    }
                });
            }
            
            // Weekday percentage region chart
            const canvasWeekdayPct = document.createElement('canvas');
            canvasWeekdayPct.id = 'startTimeWeekdayPercentageRegionChart';
            canvasWeekdayPct.style.marginTop = '20px';
            document.getElementById('startTimeWeekdayRegionChart')?.parentNode?.appendChild(canvasWeekdayPct);
            const ctxWeekdayPct = canvasWeekdayPct.getContext('2d');
            
            // Calculate max percentage for dynamic scaling (Weekday)
            const weekdayPctRegionValues = [];
            regions.forEach(region => {
                Object.keys(data.by_region[region].weekday_percentage || {}).forEach(hour => {
                    weekdayPctRegionValues.push(parseFloat(data.by_region[region].weekday_percentage[hour]) || 0);
                });
            });
            const weekdayRegionPctMax = Math.max(...weekdayPctRegionValues) * 1.2;
            
            new Chart(ctxWeekdayPct, {
                type: 'line',
                data: {
                    labels: hours.map(h => `${h}:00`),
                    datasets: regions.map(region => ({
                        label: `${region} Weekday %`,
                        data: hours.map(h => {
                            const dict = data.by_region[region].weekday_percentage || {};
                            const key = String(h);
                            return parseFloat(dict[key]) || 0;
                        }),
                        backgroundColor: regionColors[region].replace('0.8', '0.2'),
                        borderColor: regionColors[region],
                        borderWidth: 2,
                        fill: true,
                        tension: 0.4
                    }))
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: true,
                    scales: {
                        y: { beginAtZero: true, max: weekdayRegionPctMax, title: { display: true, text: 'Percentage (%)' } },
                        x: { title: { display: true, text: 'Hour of Day' } }
                    },
                    plugins: { legend: { display: true, position: 'top' } }
                }
            });
            
            // Saturday region chart
            const canvasSat = document.getElementById('startTimeSaturdayRegionChart');
            if (canvasSat) {
                const ctxSat = canvasSat.getContext('2d');
                new Chart(ctxSat, {
                    type: 'line',
                    data: {
                        labels: hours.map(h => `${h}:00`),
                        datasets: regions.map(region => ({
                            label: `${region} Saturday`,
                            data: hours.map(h => {
                                const dict = data.by_region[region].saturday || {};
                                const key = String(h);
                                return dict[key] || 0;
                            }),
                            backgroundColor: regionColors[region],
                            borderColor: regionColors[region],
                            borderWidth: 2,
                            fill: false,
                            tension: 0.4
                        }))
                    },
                    options: {
                        responsive: true,
                        maintainAspectRatio: true,
                        scales: {
                            y: { beginAtZero: true, title: { display: true, text: 'Number of Trips' } },
                            x: { title: { display: true, text: 'Hour of Day' } }
                        },
                        plugins: { legend: { display: true, position: 'top' } }
                    }
                });
            }
            
            // Saturday percentage region chart
            const canvasSatPct = document.createElement('canvas');
            canvasSatPct.id = 'startTimeSaturdayPercentageRegionChart';
            canvasSatPct.style.marginTop = '20px';
            document.getElementById('startTimeSaturdayRegionChart')?.parentNode?.appendChild(canvasSatPct);
            const ctxSatPct = canvasSatPct.getContext('2d');
            
            // Calculate max percentage for dynamic scaling (Saturday)
            const saturdayPctRegionValues = [];
            regions.forEach(region => {
                Object.keys(data.by_region[region].saturday_percentage || {}).forEach(hour => {
                    saturdayPctRegionValues.push(parseFloat(data.by_region[region].saturday_percentage[hour]) || 0);
                });
            });
            const saturdayRegionPctMax = Math.max(...saturdayPctRegionValues) * 1.2;
            
            new Chart(ctxSatPct, {
                type: 'line',
                data: {
                    labels: hours.map(h => `${h}:00`),
                    datasets: regions.map(region => ({
                        label: `${region} Saturday %`,
                        data: hours.map(h => {
                            const dict = data.by_region[region].saturday_percentage || {};
                            const key = String(h);
                            return parseFloat(dict[key]) || 0;
                        }),
                        backgroundColor: regionColors[region].replace('0.8', '0.2'),
                        borderColor: regionColors[region],
                        borderWidth: 2,
                        fill: true,
                        tension: 0.4
                    }))
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: true,
                    scales: {
                        y: { beginAtZero: true, max: saturdayRegionPctMax, title: { display: true, text: 'Percentage (%)' } },
                        x: { title: { display: true, text: 'Hour of Day' } }
                    },
                    plugins: { legend: { display: true, position: 'top' } }
                }
            });
            
            // Sunday region chart
            const canvasSun = document.getElementById('startTimeSundayRegionChart');
            if (canvasSun) {
                const ctxSun = canvasSun.getContext('2d');
                new Chart(ctxSun, {
                    type: 'line',
                    data: {
                        labels: hours.map(h => `${h}:00`),
                        datasets: regions.map(region => ({
                            label: `${region} Sunday`,
                            data: hours.map(h => {
                                const dict = data.by_region[region].sunday || {};
                                const key = String(h);
                                return dict[key] || 0;
                            }),
                            backgroundColor: regionColors[region],
                            borderColor: regionColors[region],
                            borderWidth: 2,
                            fill: false,
                            tension: 0.4
                        }))
                    },
                    options: {
                        responsive: true,
                        maintainAspectRatio: true,
                        scales: {
                            y: { beginAtZero: true, title: { display: true, text: 'Number of Trips' } },
                            x: { title: { display: true, text: 'Hour of Day' } }
                        },
                        plugins: { legend: { display: true, position: 'top' } }
                    }
                });
            }
            
            // Sunday percentage region chart
            const canvasSunPct = document.createElement('canvas');
            canvasSunPct.id = 'startTimeSundayPercentageRegionChart';
            canvasSunPct.style.marginTop = '20px';
            document.getElementById('startTimeSundayRegionChart')?.parentNode?.appendChild(canvasSunPct);
            const ctxSunPct = canvasSunPct.getContext('2d');
            
            // Calculate max percentage for dynamic scaling (Sunday)
            const sundayPctRegionValues = [];
            regions.forEach(region => {
                Object.keys(data.by_region[region].sunday_percentage || {}).forEach(hour => {
                    sundayPctRegionValues.push(parseFloat(data.by_region[region].sunday_percentage[hour]) || 0);
                });
            });
            const sundayRegionPctMax = Math.max(...sundayPctRegionValues) * 1.2;
            
            new Chart(ctxSunPct, {
                type: 'line',
                data: {
                    labels: hours.map(h => `${h}:00`),
                    datasets: regions.map(region => ({
                        label: `${region} Sunday %`,
                        data: hours.map(h => {
                            const dict = data.by_region[region].sunday_percentage || {};
                            const key = String(h);
                            return parseFloat(dict[key]) || 0;
                        }),
                        backgroundColor: regionColors[region].replace('0.8', '0.2'),
                        borderColor: regionColors[region],
                        borderWidth: 2,
                        fill: true,
                        tension: 0.4
                    }))
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: true,
                    scales: {
                        y: { beginAtZero: true, max: sundayRegionPctMax, title: { display: true, text: 'Percentage (%)' } },
                        x: { title: { display: true, text: 'Hour of Day' } }
                    },
                    plugins: { legend: { display: true, position: 'top' } }
                }
            });
        }
    } catch (error) {
        console.error('Error loading trip start time:', error);
    }
}

// Indicator 4: Trip Purpose and Mode Coverage
async function loadCoverage() {
    try {
        const response = await fetch('/api/trip-purpose-mode-coverage');
        const data = await response.json();

        document.getElementById('mode-coverage').textContent = `${data.mode_coverage_pct}%`;
        document.getElementById('purpose-coverage').textContent = `${data.purpose_coverage_pct}%`;
        // document.getElementById('both-coverage').textContent = `${data.both_coverage_pct}%`;

        // Region comparison chart
        if (data.by_region) {
            const regions = Object.keys(data.by_region);
            const regionColors = {
                'Vancouver': 'rgba(102, 126, 234, 0.8)',
                'Okanagan': 'rgba(237, 137, 54, 0.8)',
                'Other': 'rgba(159, 122, 234, 0.8)'
            };

            const ctxRegion = document.getElementById('coverageRegionChart').getContext('2d');
            new Chart(ctxRegion, {
                type: 'bar',
                data: {
                    labels: regions,
                    datasets: [{
                        label: 'Mode Coverage',
                        data: regions.map(r => data.by_region[r].mode_coverage_pct),
                        backgroundColor: regions.map(r => regionColors[r]),
                        borderColor: regions.map(r => regionColors[r]),
                        borderWidth: 2
                    }, {
                        label: 'Purpose Coverage',
                        data: regions.map(r => data.by_region[r].purpose_coverage_pct),
                        backgroundColor: regions.map(r => regionColors[r].replace('0.8', '0.5')),
                        borderColor: regions.map(r => regionColors[r]),
                        borderWidth: 2
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: true,
                    scales: {
                        y: {
                            beginAtZero: true,
                            max: 100,
                            title: {
                                display: true,
                                text: 'Coverage (%)'
                            }
                        }
                    },
                    plugins: {
                        legend: {
                            display: true,
                            position: 'top'
                        },
                        tooltip: {
                            callbacks: {
                                label: function (context) {
                                    return `${context.dataset.label}: ${context.parsed.y.toFixed(2)}%`;
                                }
                            }
                        }
                    }
                }
            });
        }
    } catch (error) {
        console.error('Error loading coverage:', error);
    }
}

// Indicator 5: Trip Duration
async function loadTripDuration() {
    try {
        const response = await fetch('/api/trip-duration');
        const result = await response.json();

        // Display overall average duration
        const avgDurationDiv = document.createElement('div');
        avgDurationDiv.className = 'duration-summary';
        avgDurationDiv.style.cssText = 'background-color: #f0f4ff; padding: 15px; border-radius: 8px; margin-bottom: 20px; text-align: center;';
        avgDurationDiv.innerHTML = `<h4 style="margin: 0 0 10px 0;">Overall Average Trip Duration</h4><p style="margin: 0; font-size: 24px; color: #667eea; font-weight: bold;">${result.overall_avg_duration_minutes} minutes</p>`;
        document.getElementById('tripDurationWeekdayChart').parentNode.insertBefore(avgDurationDiv, document.getElementById('tripDurationWeekdayChart'));

        // Create weekday chart
        const ctxWeekday = document.getElementById('tripDurationWeekdayChart').getContext('2d');
        new Chart(ctxWeekday, {
            type: 'pie',
            data: {
                labels: result.weekday.map(d => d.category),
                datasets: [{
                    label: 'Trip Duration',
                    data: result.weekday.map(d => d.count),
                    backgroundColor: colorPalette.slice(0, result.weekday.length),
                    borderColor: '#ffffff',
                    borderWidth: 2
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: true,
                plugins: {
                    legend: {
                        display: true,
                        position: 'bottom'
                    },
                    tooltip: {
                        callbacks: {
                            label: function (context) {
                                const item = result.weekday[context.dataIndex];
                                return `${item.category}: ${item.count} trips (${item.percentage}%)`;
                            }
                        }
                    }
                }
            }
        });

        // Create Saturday chart
        const ctxSaturday = document.getElementById('tripDurationSaturdayChart').getContext('2d');
        new Chart(ctxSaturday, {
            type: 'pie',
            data: {
                labels: result.saturday.map(d => d.category),
                datasets: [{
                    label: 'Trip Duration',
                    data: result.saturday.map(d => d.count),
                    backgroundColor: colorPalette.slice(0, result.saturday.length),
                    borderColor: '#ffffff',
                    borderWidth: 2
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: true,
                plugins: {
                    legend: {
                        display: true,
                        position: 'bottom'
                    },
                    tooltip: {
                        callbacks: {
                            label: function (context) {
                                const item = result.saturday[context.dataIndex];
                                return `${item.category}: ${item.count} trips (${item.percentage}%)`;
                            }
                        }
                    }
                }
            }
        });

        // Create Sunday chart
        const ctxSunday = document.getElementById('tripDurationSundayChart').getContext('2d');
        new Chart(ctxSunday, {
            type: 'pie',
            data: {
                labels: result.sunday.map(d => d.category),
                datasets: [{
                    label: 'Trip Duration',
                    data: result.sunday.map(d => d.count),
                    backgroundColor: colorPalette.slice(0, result.sunday.length),
                    borderColor: '#ffffff',
                    borderWidth: 2
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: true,
                plugins: {
                    legend: {
                        display: true,
                        position: 'bottom'
                    },
                    tooltip: {
                        callbacks: {
                            label: function (context) {
                                const item = result.sunday[context.dataIndex];
                                return `${item.category}: ${item.count} trips (${item.percentage}%)`;
                            }
                        }
                    }
                }
            }
        });

        // Region comparison (Weekday): stacked bar
        if (result.by_region) {
            const regions = Object.keys(result.by_region).filter(r => ['Vancouver','Okanagan','Other'].includes(r));
            const regionColors = {
                'Vancouver': 'rgba(102, 126, 234, 0.8)',
                'Okanagan': 'rgba(237, 137, 54, 0.8)',
                'Other': 'rgba(72, 187, 120, 0.8)'
            };
            const labels = result.weekday.map(d => d.category);
            const ctxRegion = document.getElementById('tripDurationWeekdayRegionChart')?.getContext('2d');
            if (ctxRegion) {
                new Chart(ctxRegion, {
                    type: 'bar',
                    data: {
                        labels,
                        datasets: regions.map(region => ({
                            label: region,
                            data: result.by_region[region].weekday.map(d => d.count),
                            backgroundColor: regionColors[region],
                            borderColor: regionColors[region],
                            borderWidth: 2
                        }))
                    },
                    options: {
                        responsive: true,
                        maintainAspectRatio: true,
                        scales: {
                            x: { stacked: true },
                            y: { stacked: true, beginAtZero: true, title: { display: true, text: 'Number of Trips' } }
                        },
                        plugins: { legend: { display: true, position: 'top' } }
                    }
                });
            }

            // Region pies: overall distribution for Vancouver and Okanagan
            const regionPieConfigs = [
                { region: 'Vancouver', canvasId: 'tripDurationRegionVancouverChart' },
                { region: 'Okanagan', canvasId: 'tripDurationRegionOkanaganChart' }
            ];
            regionPieConfigs.forEach(cfg => {
                const canvas = document.getElementById(cfg.canvasId);
                if (canvas && result.by_region[cfg.region] && result.by_region[cfg.region].overall) {
                    const dataArr = result.by_region[cfg.region].overall;
                    const ctxPie = canvas.getContext('2d');
                    new Chart(ctxPie, {
                        type: 'pie',
                        data: {
                            labels: dataArr.map(d => d.category),
                            datasets: [{
                                label: `${cfg.region} Trip Duration`,
                                data: dataArr.map(d => d.count),
                                backgroundColor: colorPalette.slice(0, dataArr.length),
                                borderColor: '#ffffff',
                                borderWidth: 2
                            }]
                        },
                        options: {
                            responsive: true,
                            maintainAspectRatio: true,
                            plugins: {
                                legend: { display: true, position: 'bottom' },
                                tooltip: {
                                    callbacks: {
                                        label: function (context) {
                                            const item = dataArr[context.dataIndex];
                                            return `${item.category}: ${item.count} trips (${item.percentage}%)`;
                                        }
                                    }
                                }
                            }
                        }
                    });
                }
            });
        }
    } catch (error) {
        console.error('Error loading trip duration:', error);
    }
}

// Indicator 6: Activity Duration
async function loadActivityDuration() {
    try {
        const response = await fetch('/api/activity-duration');
        const result = await response.json();

        // Extract the by_purpose array from the response
        const data = result.by_purpose || result;

        // Take top 10 purposes by count
        const topData = data.slice(0, 10);

        const ctx = document.getElementById('activityDurationChart').getContext('2d');
        new Chart(ctx, {
            type: 'bar',
            data: {
                labels: topData.map(d => d.purpose),
                datasets: [{
                    label: 'Average Duration (hours)',
                    data: topData.map(d => d.avg_duration_hours),
                    backgroundColor: colorPalette.slice(0, topData.length),
                    borderColor: colorPalette.slice(0, topData.length),
                    borderWidth: 2
                }]
            },
            options: {
                indexAxis: 'y',
                responsive: true,
                maintainAspectRatio: true,
                scales: {
                    x: {
                        beginAtZero: true,
                        title: {
                            display: true,
                            text: 'Average Duration (hours)'
                        }
                    }
                },
                plugins: {
                    legend: {
                        display: false
                    },
                    tooltip: {
                        callbacks: {
                            label: function (context) {
                                const item = topData[context.dataIndex];
                                return [
                                    `Avg: ${item.avg_duration_hours} hrs`,
                                    `Total: ${item.total_duration_hours} hrs`,
                                    `Count: ${item.count} activities`
                                ];
                            }
                        }
                    }
                }
            }
        });
        


        // Region comparison chart for activity duration (avg hours by top purposes)
        // Formula: avg_hours for each region/purpose combination
        if (result.by_region) {
            const ctxRegion = document.getElementById('activityDurationRegionChart')?.getContext('2d');
            if (ctxRegion) {
                const regions = Object.keys(result.by_region).filter(r => ['Vancouver','Okanagan','Other'].includes(r));
                const regionColors = {
                    'Vancouver': 'rgba(102, 126, 234, 0.8)',
                    'Okanagan': 'rgba(237, 137, 54, 0.8)',
                    'Other': 'rgba(72, 187, 120, 0.8)'
                };
                const purposes = topData.map(d => d.purpose);
                
                new Chart(ctxRegion, {
                    type: 'bar',
                    data: {
                        labels: purposes,
                        datasets: regions.map(region => ({
                            label: region,
                            data: purposes.map(p => {
                                const items = result.by_region[region].by_purpose;
                                const found = items.find(i => i.purpose === p);
                                return found ? found.avg_duration_hours : 0;
                            }),
                            backgroundColor: regionColors[region],
                            borderColor: regionColors[region],
                            borderWidth: 2
                        }))
                    },
                    options: {
                        responsive: true,
                        maintainAspectRatio: true,
                        scales: { y: { beginAtZero: true, title: { display: true, text: 'Avg Hours' } } },
                        plugins: { legend: { display: true, position: 'top' } }
                    }
                });
            }
        }
    } catch (error) {
        console.error('Error loading activity duration:', error);
    }
}

// Indicator 7: Weekday Coverage Distribution
async function loadWeekdayCoverage() {
    try {
        const response = await fetch('/api/weekday-distribution');
        const data = await response.json();

        const ctx = document.getElementById('weekdayCoverageChart').getContext('2d');
        new Chart(ctx, {
            type: 'bar',
            data: {
                labels: data.weekday_stats.map(d => d.day),
                datasets: [
                    {
                        label: 'Users with Data',
                        data: data.weekday_stats.map(d => d.users_with_data),
                        backgroundColor: colors.success,
                        borderColor: colors.success,
                        borderWidth: 2
                    },
                    {
                        label: 'Users without Data',
                        data: data.weekday_stats.map(d => d.users_without_data),
                        backgroundColor: colors.danger,
                        borderColor: colors.danger,
                        borderWidth: 2
                    }
                ]
            },
            options: {
                responsive: true,
                maintainAspectRatio: true,
                scales: {
                    x: {
                        stacked: true,
                        title: {
                            display: true,
                            text: 'Day of Week'
                        }
                    },
                    y: {
                        stacked: true,
                        beginAtZero: true,
                        title: {
                            display: true,
                            text: 'Number of Users'
                        }
                    }
                },
                plugins: {
                    legend: {
                        display: true,
                        position: 'top'
                    },
                    tooltip: {
                        callbacks: {
                            label: function (context) {
                                const item = data.weekday_stats[context.dataIndex];
                                if (context.datasetIndex === 0) {
                                    return `With data: ${item.users_with_data} (${item.coverage_percentage}%)`;
                                } else {
                                    return `Without data: ${item.users_without_data}`;
                                }
                            }
                        }
                    }
                }
            }
        });
    } catch (error) {
        console.error('Error loading weekday coverage:', error);
    }
}

// Indicator 8: User Completion Rate by Days
async function loadCompletionRates() {
    try {
        const response = await fetch('/api/seven-day-coverage');
        const data = await response.json();

        // Cumulative completion chart (X days or more)
        const ctxCumulative = document.getElementById('cumulativeCompletionChart').getContext('2d');
        new Chart(ctxCumulative, {
            type: 'bar',
            data: {
                labels: data.cumulative_stats.map(d => `${d.days}+ days`),
                datasets: [{
                    label: 'Percentage of Users',
                    data: data.cumulative_stats.map(d => d.percentage),
                    backgroundColor: colors.primary,
                    borderColor: colors.primary,
                    borderWidth: 2
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: true,
                scales: {
                    y: {
                        beginAtZero: true,
                        max: 100,
                        title: {
                            display: true,
                            text: 'Percentage (%)'
                        }
                    },
                    x: {
                        title: {
                            display: true,
                            text: 'Days Completed'
                        }
                    }
                },
                plugins: {
                    legend: {
                        display: false
                    },
                    tooltip: {
                        callbacks: {
                            label: function (context) {
                                const item = data.cumulative_stats[context.dataIndex];
                                return `${item.percentage}% (${item.users_count} users)`;
                            }
                        }
                    }
                }
            }
        });

        // Exact completion chart
        const ctxExact = document.getElementById('exactCompletionChart').getContext('2d');

        // Region comparison charts for Indicator 8
        if (data.by_region) {
            const regions = Object.keys(data.by_region).filter(r => ['Vancouver','Okanagan','Other'].includes(r));
            const regionColors = {
                'Vancouver': 'rgba(102, 126, 234, 0.8)',
                'Okanagan': 'rgba(237, 137, 54, 0.8)',
                'Other': 'rgba(72, 187, 120, 0.8)'
            };
            const ctxCumRegion = document.getElementById('cumulativeCompletionRegionChart')?.getContext('2d');
            const ctxExactRegion = document.getElementById('exactCompletionRegionChart')?.getContext('2d');
            if (ctxCumRegion) {
                new Chart(ctxCumRegion, {
                    type: 'bar',
                    data: {
                        labels: data.cumulative_stats.map(d => `${d.days}+ days`),
                        datasets: regions.map(region => ({
                            label: region,
                            data: data.by_region[region].cumulative_stats.map(d => d.percentage),
                            backgroundColor: regionColors[region],
                            borderColor: regionColors[region],
                            borderWidth: 2
                        }))
                    },
                    options: { responsive: true, maintainAspectRatio: true, scales: { y: { beginAtZero: true, max: 100 } }, plugins: { legend: { display: true, position: 'top' } } }
                });
            }
            if (ctxExactRegion) {
                new Chart(ctxExactRegion, {
                    type: 'bar',
                    data: {
                        labels: data.exact_stats.map(d => `${d.days} day${d.days !== 1 ? 's' : ''}`),
                        datasets: regions.map(region => ({
                            label: region,
                            data: data.by_region[region].exact_stats.map(d => d.percentage),
                            backgroundColor: regionColors[region],
                            borderColor: regionColors[region],
                            borderWidth: 2
                        }))
                    },
                    options: { responsive: true, maintainAspectRatio: true, scales: { y: { beginAtZero: true } }, plugins: { legend: { display: true, position: 'top' } } }
                });
            }
        }
        new Chart(ctxExact, {
            type: 'bar',
            data: {
                labels: data.exact_stats.map(d => `${d.days} day${d.days !== 1 ? 's' : ''}`),
                datasets: [{
                    label: 'Percentage of Users',
                    data: data.exact_stats.map(d => d.percentage),
                    backgroundColor: colors.secondary,
                    borderColor: colors.secondary,
                    borderWidth: 2
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: true,
                scales: {
                    y: {
                        beginAtZero: true,
                        title: {
                            display: true,
                            text: 'Percentage (%)'
                        }
                    },
                    x: {
                        title: {
                            display: true,
                            text: 'Exact Days Completed'
                        }
                    }
                },
                plugins: {
                    legend: {
                        display: false
                    },
                    tooltip: {
                        callbacks: {
                            label: function (context) {
                                const item = data.exact_stats[context.dataIndex];
                                return `${item.percentage}% (${item.users_count} users)`;
                            }
                        }
                    }
                }
            }
        });
    } catch (error) {
        console.error('Error loading completion rates:', error);
    }
}

// Indicator 9: Trip Purpose Distribution by Hour
async function loadPurposeByHour() {
    try {
        const response = await fetch('/api/purpose-by-hour');
        const data = await response.json();

        // Create chart function
        // Formula for count: Number of trips for each purpose at each hour
        function createPurposeChart(canvasId, chartData, dayType) {
            const ctx = document.getElementById(canvasId).getContext('2d');
            
            // Create datasets for each purpose
            const datasets = [];
            const purposes = data.top_purposes;
            
            purposes.forEach((purpose, index) => {
                datasets.push({
                    label: purpose,
                    data: chartData.chart_data[purpose],
                    backgroundColor: colorPalette[index % colorPalette.length],
                    borderColor: colorPalette[index % colorPalette.length],
                    borderWidth: 2,
                    fill: false,
                    tension: 0.4
                });
            });

            new Chart(ctx, {
                type: 'line',
                data: {
                    labels: Array.from({ length: 24 }, (_, i) => `${i}:00`),
                    datasets: datasets
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: true,
                    interaction: {
                        mode: 'index',
                        intersect: false,
                    },
                    scales: {
                        x: {
                            title: {
                                display: true,
                                text: 'Hour of Day'
                            }
                        },
                        y: {
                            beginAtZero: true,
                            title: {
                                display: true,
                                text: 'Number of Trips'
                            }
                        }
                    },
                    plugins: {
                        legend: {
                            display: true,
                            position: 'top'
                        },
                        tooltip: {
                            callbacks: {
                                label: function (context) {
                                    const hour = context.dataIndex;
                                    const purpose = context.dataset.label;
                                    const hourData = chartData.hourly_data[hour];
                                    const purposeData = hourData.purposes[purpose];
                                    
                                    return `${purpose}: ${purposeData.count} trips (${purposeData.percentage}%)`;
                                },
                                footer: function (tooltipItems) {
                                    if (tooltipItems.length > 0) {
                                        const hour = tooltipItems[0].dataIndex;
                                        const totalTrips = chartData.hourly_data[hour].total_trips;
                                        return `Total ${dayType.toLowerCase()} trips at ${hour}:00: ${totalTrips}`;
                                    }
                                    return '';
                                }
                            }
                        }
                    }
                }
            });
        }
        
        // Create percentage chart function
        // Formula for Saturday/Sunday: percentage = trips of this purpose in this hour / total trips of this purpose across all hours * 100
        function createPurposePercentageChart(canvasId, chartData, dayType) {
            const purposes = data.top_purposes;
            const canvasElement = document.createElement('canvas');
            canvasElement.id = canvasId;
            canvasElement.style.marginTop = '20px';
            
            // Insert after the original chart
            const originalCanvasId = canvasId.replace('Percentage', '');
            const originalCanvas = document.getElementById(originalCanvasId);
            if (originalCanvas && originalCanvas.parentNode) {
                originalCanvas.parentNode.appendChild(canvasElement);
            }
            
            const ctx = canvasElement.getContext('2d');
            
            // Create datasets for each purpose (using percentages)
            const datasets = [];
            let maxPercentage = 0;
            purposes.forEach((purpose, index) => {
                // Calculate percentage data from hourly_data
                const percentageData = Array.from({ length: 24 }, (_, hour) => {
                    const hourData = chartData.hourly_data[hour];
                    const pct = hourData.purposes[purpose] ? hourData.purposes[purpose].percentage : 0;
                    maxPercentage = Math.max(maxPercentage, pct);
                    return pct;
                });
                
                datasets.push({
                    label: purpose,
                    data: percentageData,
                    backgroundColor: colorPalette[index % colorPalette.length].replace('0.8', '0.2'),
                    borderColor: colorPalette[index % colorPalette.length],
                    borderWidth: 2,
                    fill: false,
                    tension: 0.4
                });
            });

            new Chart(ctx, {
                type: 'line',
                data: {
                    labels: Array.from({ length: 24 }, (_, i) => `${i}:00`),
                    datasets: datasets
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: true,
                    interaction: {
                        mode: 'index',
                        intersect: false,
                    },
                    scales: {
                        x: {
                            title: {
                                display: true,
                                text: 'Hour of Day'
                            }
                        },
                        y: {
                            beginAtZero: true,
                            max: maxPercentage * 1.2,
                            title: {
                                display: true,
                                text: 'Percentage of Trips (%)'
                            }
                        }
                    },
                    plugins: {
                        legend: {
                            display: true,
                            position: 'top'
                        },
                        tooltip: {
                            callbacks: {
                                label: function (context) {
                                    const purpose = context.dataset.label;
                                    return `${purpose}: ${context.parsed.y.toFixed(2)}%`;
                                }
                            }
                        }
                    }
                }
            });
        }

        // Create weekday chart
        createPurposeChart('purposeByHourWeekdayChart', data.weekday, 'Weekday');
        createPurposePercentageChart('purposeByHourWeekdayPercentageChart', data.weekday, 'Weekday');
        
        // Create Saturday chart
        createPurposeChart('purposeByHourSaturdayChart', data.saturday, 'Saturday');
        createPurposePercentageChart('purposeByHourSaturdayPercentageChart', data.saturday, 'Saturday');
        
        // Create Sunday chart
        createPurposeChart('purposeByHourSundayChart', data.sunday, 'Sunday');
        createPurposePercentageChart('purposeByHourSundayPercentageChart', data.sunday, 'Sunday');

        // (Removed) Region comparison chart for weekday total trips by region.

    } catch (error) {
        console.error('Error loading purpose by hour:', error);
    }
}



// Initialize dashboard - load all data in parallel
document.addEventListener('DOMContentLoaded', async () => {
    const loadingOverlay = document.getElementById('loading-overlay');
    console.time('Total load time');

    try {
        // Load all indicators in parallel for faster performance
        await Promise.all([
            loadSummaryStats(),
            loadTripsPerPerson(),
            loadModeShare(),
            loadTripStartTime(),
            loadCoverage(),
            loadTripDuration(),
            loadActivityDuration(),
            loadWeekdayCoverage(),
            loadCompletionRates(),
            loadPurposeByHour()
        ]);

        console.timeEnd('Total load time');
        console.log('All indicators loaded successfully!');
    } catch (error) {
        console.error('Error loading dashboard:', error);
    } finally {
        // Hide loading overlay
        setTimeout(() => {
            loadingOverlay.classList.add('hidden');
        }, 300);
    }
});

// Toggle parameter section
function toggleParamSection() {
    const section = document.getElementById('param-section');
    const btn = document.getElementById('param-toggle-btn');
    
    section.classList.toggle('collapsed');
    
    if (section.classList.contains('collapsed')) {
        btn.textContent = '▼';
        btn.classList.remove('rotated');
    } else {
        btn.textContent = '▲';
        btn.classList.add('rotated');
    }
}


