import streamlit as st
import pandas as pd
import nfl_data_py as nfl
from streamlit_apex_charts import st_apex_charts

# Set the page layout to wide and add a title
st.set_page_config(layout='wide', page_title='NFL Player Statistics Visualization')

# Apply dark theme using custom CSS
st.markdown(
    """
    <style>
    /* Set background and text colors */
    body {
        background-color: #0e1117;
        color: #c9d1d9;
    }
    /* Adjust sidebar */
    .css-1d391kg {
        background-color: #0e1117;
    }
    /* Adjust input widgets */
    .stSelectbox, .stTextInput {
        color: #c9d1d9;
    }
    /* Adjust headings */
    h1, h2, h3, h4, h5, h6 {
        color: #c9d1d9;
    }
    /* Adjust dataframe */
    .stDataFrame {
        background-color: #212529;
        color: #c9d1d9;
    }
    </style>
    """,
    unsafe_allow_html=True
)

# Function to get player statistics
@st.cache_data
def get_player_stats():
    seasons = list(range(2020, 2025))
    df = nfl.import_weekly_data(seasons)
    return df

# Function to get roster data
@st.cache_data
def get_roster_data():
    seasons = list(range(2020, 2025))
    roster_df = nfl.import_seasonal_rosters(seasons)
    return roster_df

# Load the data
df = get_player_stats()
roster_df = get_roster_data()

# Ensure player_id columns are of the same data type
df['player_id'] = df['player_id'].astype(str)
roster_df['player_id'] = roster_df['player_id'].astype(str)

# Create 'full_name' by combining 'first_name' and 'last_name'
if 'first_name' in roster_df.columns and 'last_name' in roster_df.columns:
    roster_df['full_name'] = roster_df['first_name'] + ' ' + roster_df['last_name']
    name_column = 'full_name'
else:
    st.error("First name and last name columns not found in roster_df.")
    st.stop()

# Merge player data with roster data to get full names, positions, and headshot URLs
df = df.merge(
    roster_df[['player_id', name_column, 'position', 'headshot_url', 'team']],
    on='player_id',
    how='left',
    suffixes=('', '_roster')
)

# Determine which 'position' column to use
if 'position_roster' in df.columns:
    df['position'] = df['position_roster']
    df.drop(columns=['position_roster'], inplace=True)
elif 'position' in df.columns:
    pass
else:
    st.error("'position' column not found after merging.")
    st.stop()

# Remove any duplicate rows
df = df.drop_duplicates()

# Sidebar for year and player selection
st.sidebar.header('Selection')

# Get available seasons
available_seasons = df['season'].unique()
available_seasons.sort()

# Set default selection to 2024 if available
if 2024 in available_seasons:
    default_season_index = list(available_seasons).index(2024)
else:
    default_season_index = 0

selected_season = st.sidebar.selectbox('Select a Season (Year):', available_seasons, index=default_season_index)

# Filter data for the selected season
df_season = df[df['season'] == selected_season]

# Get the list of players for the selected season
player_names = df_season[name_column].dropna().unique()
player_names.sort()

# Set default selection to 'Aaron Rodgers' if available
if 'Aaron Rodgers' in player_names:
    default_player_index = list(player_names).index('Aaron Rodgers')
else:
    default_player_index = 0

selected_player_name = st.sidebar.selectbox('Select a Player:', player_names, index=default_player_index)

# Filter data for the selected player and season
player_data = df_season[df_season[name_column] == selected_player_name]

# Get player's information
player_info = roster_df[roster_df['full_name'] == selected_player_name].iloc[0]
headshot_url = player_info.get('headshot_url', '')
position = player_info.get('position', 'N/A')
team = player_info.get('team', 'N/A')

# Display player image and information centered
st.markdown(f"<h2 style='text-align: center;'>{selected_player_name}</h2>", unsafe_allow_html=True)

if headshot_url:
    st.markdown(f"<div style='text-align: center;'><img src='{headshot_url}' width='150'></div>", unsafe_allow_html=True)
else:
    st.write("No image available.")

st.markdown(f"<p style='text-align: center;'><strong>Position</strong>: {position} | <strong>Team</strong>: {team}</p>", unsafe_allow_html=True)

# Display metrics below the player bio
# Check if data is available
if player_data.empty:
    st.warning('No data available for this player in the selected season.')
else:
    # Convert week number to integer for sorting
    player_data['week'] = player_data['week'].astype(int)
    player_data = player_data.sort_values(['week'])

    # Remove any duplicate rows in player_data
    player_data = player_data.drop_duplicates(subset=['season', 'week'])

    # Define metrics based on position
    position = position.upper()
    if position == 'QB':
        metric_stats = {
            'Passing Yards': 'passing_yards',
            'Passing TDs': 'passing_tds',
            'Rushing TDs': 'rushing_tds'
        }
    elif position == 'RB':
        # Total touchdowns (rushing + receiving)
        player_data['total_tds'] = player_data['rushing_tds'] + player_data['receiving_tds']
        metric_stats = {
            'Rushing Yards': 'rushing_yards',
            'Receiving Yards': 'receiving_yards',
            'Total TDs': 'total_tds'
        }
    elif position in ['WR', 'TE']:
        # Total touchdowns (rushing + receiving)
        player_data['total_tds'] = player_data['rushing_tds'] + player_data['receiving_tds']
        metric_stats = {
            'Receiving Yards': 'receiving_yards',
            'Receptions': 'receptions',
            'Total TDs': 'total_tds'
        }
    else:
        metric_stats = {}

    # Calculate averages over last 3 games and season
    if not metric_stats:
        st.warning('No metrics available for this position.')
    else:
        # Calculate averages
        last_3_games = player_data.tail(3)
        season_avg = player_data.mean(numeric_only=True)

        # Display metrics below the player bio
        st.markdown("<h3 style='text-align: center;'>Recent Performance (last 3 games)</h3>", unsafe_allow_html=True)
        for metric_name, metric_column in metric_stats.items():
            # Average over last 3 games
            last_3_avg = last_3_games[metric_column].mean()
            # Season average
            season_avg_metric = season_avg.get(metric_column, 0)
            # Delta
            delta = last_3_avg - season_avg_metric

            # Display metric with styling
            st.markdown(f"""
                <div style='text-align: center; margin-bottom: 10px;'>
                    <h4>{metric_name}</h4>
                    <p style='font-size: 24px; margin: 0;'>{last_3_avg:.1f}</p>
                    <p style='margin: 0; color: {"green" if delta >= 0 else "red"};'>{delta:+.1f} vs Season Avg</p>
                </div>
            """, unsafe_allow_html=True)

    # Box Score
    st.markdown("<h3 style='text-align: center;'>Game-by-Game Stats</h3>", unsafe_allow_html=True)
    # Select columns to display
    box_score_columns = [
        'week', 'game_date', 'opponent_team', 'fantasy_points_ppr',
        'passing_yards', 'passing_tds', 'interceptions',
        'rushing_yards', 'rushing_tds',
        'receiving_yards', 'receiving_tds', 'receptions', 'targets'
    ]
    # Filter columns that exist in player_data
    box_score_columns = [col for col in box_score_columns if col in player_data.columns]
    box_score_df = player_data[box_score_columns]
    box_score_df = box_score_df.sort_values('week')
    box_score_df.set_index('week', inplace=True)

    # Format date column if it exists
    if 'game_date' in box_score_df.columns:
        box_score_df['game_date'] = pd.to_datetime(box_score_df['game_date']).dt.strftime('%Y-%m-%d')

    st.dataframe(box_score_df)

    # Create a container for the chart
    chart_container = st.container()

    with chart_container:
        st.markdown("<h3 style='text-align: center;'>Performance Over Time</h3>", unsafe_allow_html=True)
        # Create a placeholder for the chart
        chart_placeholder = st.empty()

    # Betting Line Input Below the Chart (but code-wise before chart creation)
    st.markdown("<h3 style='text-align: center;'>Betting Line Analysis</h3>", unsafe_allow_html=True)
    fixed_line_value = st.text_input('Enter Betting Line (Optional):', key='betting_line')

    # Select statistic to plot
    selected_display_stat = st.selectbox('Select a Statistic to Plot:', list(metric_stats.keys()))
    selected_category = metric_stats[selected_display_stat]

    # Create a copy of player_data to avoid SettingWithCopyWarning
    plot_data = player_data.copy()

    # Prepare data for ApexCharts
    weeks = plot_data['week'].tolist()
    stats_values = plot_data[selected_category].tolist()

    # Initialize chart options
    options = {
        "chart": {
            "type": "line",
            "height": 350,
            "background": '#0e1117',
            "toolbar": {
                "show": False
            },
            "zoom": {
                "enabled": False
            }
        },
        "theme": {
            "mode": "dark"
        },
        "stroke": {
            "curve": "smooth",
            "width": 2
        },
        "xaxis": {
            "categories": weeks,
            "title": {
                "text": "Week",
                "style": {
                    "color": "#c9d1d9"
                }
            },
            "labels": {
                "style": {
                    "colors": "#c9d1d9"
                }
            }
        },
        "yaxis": {
            "title": {
                "text": selected_display_stat,
                "style": {
                    "color": "#c9d1d9"
                }
            },
            "labels": {
                "style": {
                    "colors": "#c9d1d9"
                }
            }
        },
        "title": {
            "text": f"{selected_player_name} - {selected_display_stat} Over Weeks ({selected_season})",
            "align": 'center',
            "style": {
                "fontSize": '16px',
                "color": "#c9d1d9"
            }
        },
        "markers": {
            "size": 6,
            "colors": ["#007bff"],
            "strokeColors": "#fff",
            "strokeWidth": 2,
            "hover": {
                "size": 8
            }
        },
        "tooltip": {
            "theme": "dark"
        },
        "grid": {
            "borderColor": "#444",
            "xaxis": {
                "lines": {
                    "show": False
                }
            },
            "yaxis": {
                "lines": {
                    "show": True
                }
            }
        }
    }

    # Data series
    series = [{
        "name": selected_display_stat,
        "data": stats_values
    }]

    # Add betting line if provided
    if fixed_line_value:
        try:
            value = float(fixed_line_value)
            # Compute over/under stats
            over_line = [val > value for val in stats_values]
            weeks_over = sum(over_line)
            total_weeks = len(over_line)

            # Display feedback with a big green arrow if positive
            percentage_over = (weeks_over / total_weeks) * 100 if total_weeks > 0 else 0
            arrow = "⬆️" if weeks_over > (total_weeks / 2) else "⬇️"
            st.success(f"{arrow} **{selected_player_name} exceeded the line in {weeks_over}/{total_weeks} weeks ({percentage_over:.1f}% of games).**")

            # Update markers color based on over/under
            colors = ['#28a745' if over else '#dc3545' for over in over_line]
            options['markers']['colors'] = colors

            # Add betting line annotation
            options['annotations'] = {
                "yaxis": [{
                    "y": value,
                    "borderColor": "#ffff00",
                    "label": {
                        "borderColor": "#ffff00",
                        "style": {
                            "color": "#0e1117",
                            "background": "#ffff00"
                        },
                        "text": f"Betting Line: {value}"
                    }
                }]
            }

        except ValueError:
            st.error('Please enter a valid number for the betting line.')

    # Display the chart using ApexCharts
    st_apex_charts(options=options, series=series)
