import streamlit as st
import nfl_data_py as nfl
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go


st.set_page_config(
    page_title="Betting - NFL",
    page_icon="🏈",
    layout="wide",
)
# Load player stats for the current season
seasons = [2023]
player_stats = nfl.import_weekly_data(seasons)

# Create a list of unique player names
player_names = player_stats['player_display_name'].unique()

# Streamlit app
st.title('NFL Player Stats Visualization')

# Dropdown for player name
selected_player = st.selectbox('Select Player', player_names)

# Filter data for the selected player
player_data = player_stats[player_stats['player_display_name'] == selected_player]

# Sort by season and week to get the latest games
player_data = player_data.sort_values(by=['season', 'week'], ascending=[False, False])

# Get the last 5 games
last_5_games = player_data.head(5)

# Determine which stats have non-"none" values in the last 5 games
valid_stats = last_5_games.columns[(last_5_games != "none").any()].difference(['player_id', 'player_display_name', 'season', 'week'])

# Dropdown for stat, filtered to show only valid stats
selected_stat = st.selectbox('Select Stat', valid_stats)

# Input for fixed red line value
fixed_red_line = st.number_input('Enter value for red line', value=3.5)

# Sort by week in ascending order
last_5_games = last_5_games.sort_values(by='week', ascending=True)

# Plotting with Plotly
fig = px.line(last_5_games, x='week', y=selected_stat, markers=True, title=f'Last 5 Games of {selected_stat} for {selected_player}')
fig.update_layout(xaxis_title='Week', yaxis_title=selected_stat)

# Add fixed red line
fig.add_shape(
    go.layout.Shape(
        type="line",
        x0=last_5_games['week'].min(),
        x1=last_5_games['week'].max(),
        y0=fixed_red_line,
        y1=fixed_red_line,
        line=dict(color="red", width=2, dash="dash"),
    )
)

if st.button("Show Stats"):
# Show the plot in Streamlit
    st.plotly_chart(fig)

    # Display the data table
    st.write(last_5_games[['week', selected_stat]])