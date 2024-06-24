import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from nba_api.stats.endpoints import playergamelog
from nba_api.stats.static import players

st.set_page_config(
    page_title="Betting - NFL",
    page_icon="🏀",
    layout="wide",
)

# Function to get player ID
def get_player_id(player_name):
    nba_players = players.get_players()
    player = [player for player in nba_players if player['full_name'] == player_name][0]
    return player['id']

# Function to get game logs for a player
def get_player_game_logs(player_name, season):
    player_id = get_player_id(player_name)
    game_log = playergamelog.PlayerGameLog(player_id=player_id, season=season)
    df = game_log.get_data_frames()[0]
    return df

# Streamlit app
st.title('NBA Player Stats Viewer')

# Get list of all NBA players
all_players = players.get_players()
player_names = [player['full_name'] for player in all_players]

# Dropdown to select player
selected_player = st.selectbox('Select a player', player_names)

# List of stats to choose from
stats = ['PTS', 'AST', 'REB', 'STL', 'BLK', 'FG3M', 'FG_PCT', 'FT_PCT']

# Dropdown to select stat
selected_stat = st.selectbox('Select a stat', stats)

# Input for threshold value
threshold = st.number_input('Enter threshold value', value=0.0, step=0.1)

# Button to fetch and display data
if st.button('Show Stats'):
    # Fetch data
    df = get_player_game_logs(selected_player, '2023-24')
    
    # Sort by date and get last 10 games
    df['GAME_DATE'] = pd.to_datetime(df['GAME_DATE'])
    df = df.sort_values('GAME_DATE', ascending=False).head(10)
    
    # Create plot
    fig = go.Figure()

    # Add line for player stats
    fig.add_trace(go.Scatter(x=df['GAME_DATE'], y=df[selected_stat], mode='lines+markers', name=selected_stat))

    # Add horizontal line for threshold
    fig.add_shape(
        type="line",
        x0=df['GAME_DATE'].min(),
        y0=threshold,
        x1=df['GAME_DATE'].max(),
        y1=threshold,
        line=dict(color="Red", width=2, dash="dash"),
    )

    # Update layout
    fig.update_layout(
        title=f'{selected_player} - Last 10 Games {selected_stat}',
        xaxis_title='Game Date',
        yaxis_title=selected_stat,
        showlegend=True
    )
    
    # Display plot
    st.plotly_chart(fig)

    # Display raw data
    st.write(df[['GAME_DATE', 'MATCHUP', selected_stat]])