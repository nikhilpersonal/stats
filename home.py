import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import nfl_data_py as nfl

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
    /* Adjust plotly charts */
    .modebar {
        background-color: #0e1117;
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

    # Define m
