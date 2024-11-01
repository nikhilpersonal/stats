import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import nfl_data_py as nfl
import openai
from openai import OpenAI
from streamlit_chat import message  # For chat interface

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
   
  
    }
    /* Adjust headings */
    h1, h2, h3, h4, h5, h6 {
        color: #c9d1d9;
    }
    /* Adjust dataframe */
    .stDataFrame {
        background-color: #161b22;
        color: #c9d1d9;
    }
    /* Scrollbar */
    ::-webkit-scrollbar {
        width: 8px;
    }
    ::-webkit-scrollbar-track {
        background: #0e1117;
    }
    ::-webkit-scrollbar-thumb {
        background: #161b22;
        border-radius: 4px;
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
    
@st.cache_data
def get_schedule_data():
    seasons = [selected_season]  # Only get data for the selected season
    schedule_df = nfl.import_schedules(seasons)
    return schedule_df
    
# Function to get roster data
@st.cache_data
def get_roster_data():
    seasons = list(range(2024, 2025))
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
                    <p style='margin: 0; color: {"#28a745" if delta >= 0 else "#dc3545"};'>{delta:+.1f} vs Season Avg</p>
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

    # Plotting with Plotly
    fig = go.Figure()
    config = {'staticPlot': True}
    
    if fixed_line_value:
        try:
            value = float(fixed_line_value)
            # Compute over/under stats
            plot_data['over_line'] = plot_data[selected_category] > value
            weeks_over = plot_data['over_line'].sum()
            total_weeks = plot_data['over_line'].count()

            # Display feedback with a big green arrow if positive
            percentage_over = (weeks_over / total_weeks) * 100 if total_weeks > 0 else 0
            arrow = "⬆️" if weeks_over > (total_weeks / 2) else "⬇️"
            st.success(f"{arrow} **{selected_player_name} exceeded the line in {weeks_over}/{total_weeks} weeks ({percentage_over:.1f}% of games).**")

            # Add the player's performance line with conditional marker colors
            fig.add_trace(go.Scatter(
                x=plot_data['week'],
                y=plot_data[selected_category],
                mode='lines+markers',
                marker=dict(
                    color=['#28a745' if over else '#dc3545' for over in plot_data['over_line']],
                    size=8,
                    line=dict(width=1, color='white')
                ),
                line=dict(color='#1f77b4', width=3),
                name=selected_display_stat,
                hovertemplate='<b>Week %{x}</b><br>' + f'{selected_display_stat}: ' + '%{y}<extra></extra>'
            ))

            fig.add_hline(
                y=value,
                line_dash='dash',
                line_color='yellow',
                annotation_text=f'Betting Line at {value}',
                annotation_position="top left",
                annotation_font_color='yellow',
                annotation_bgcolor='#0e1117'
            )

            # Show "Generate AI Insight" button
            if st.button("Generate AI Insight"):
                with st.spinner("Generating AI Insight..."):
                    # Perform calculations before the API call to limit tokens
                    recent_performance = last_3_games[selected_category].mean()
                    season_performance = player_data[selected_category].mean()
                    total_games = player_data.shape[0]
                    games_over_line = plot_data[plot_data[selected_category] > float(fixed_line_value)].shape[0]
                    percentage_over_line = (games_over_line / total_games) * 100 if total_games > 0 else 0
    
                    # Get the next opponent
                    # Get schedule data
                    # Get schedule data
                    schedule_df = get_schedule_data()
                    schedule_season = schedule_df[schedule_df['season'] == selected_season]
    
                    # Get weeks played so far
                    weeks_played = player_data['week'].astype(int).unique()
                    weeks_played.sort()
                    if len(weeks_played) > 0:
                        last_week_played = weeks_played.max()
                    else:
                        last_week_played = 0
    
                    # Find next game
                    team_schedule = schedule_season[
                        ((schedule_season['home_team'] == team) | (schedule_season['away_team'] == team)) &
                        (schedule_season['week'] > last_week_played)
                    ].sort_values('week')
    
                    if not team_schedule.empty:
                        next_game = team_schedule.iloc[0]
                        next_week = next_game['week']
                        if next_game['home_team'] == team:
                            opponent_team = next_game['away_team']
                        else:
                            opponent_team = next_game['home_team']
                    else:
                        opponent_team = None
    
                    if opponent_team:
                        # Get opponent's defensive stats up to the current week
                        # Calculate points allowed per game by the opponent defense
                        opponent_games = schedule_season[
                            ((schedule_season['home_team'] == opponent_team) | (schedule_season['away_team'] == opponent_team)) &
                            (schedule_season['week'] <= last_week_played)
                        ]
    
                        if not opponent_games.empty:
                            # Calculate points allowed by opponent_team in each game
                            def calculate_points_allowed(row):
                                if row['home_team'] == opponent_team:
                                    return row['away_score']
                                else:
                                    return row['home_score']
    
                            opponent_games['points_allowed'] = opponent_games.apply(calculate_points_allowed, axis=1)
                            avg_points_allowed = opponent_games['points_allowed'].mean()
                        else:
                            avg_points_allowed = 0
    
                        # Get all games where the opponent_team was playing defense
                        opponent_defense_games = df_season[
                            (df_season['opponent_team'] == opponent_team) &  # They played against the opponent_team
                            (df_season['week'] <= last_week_played)  # Only up to the last week played
                        ]
    
                        # Calculate total offensive stats per team per week against the opponent_team
                        offensive_stats = opponent_defense_games.groupby(['team', 'week']).agg({
                            'passing_yards': 'sum',
                            'rushing_yards': 'sum',
                            'receiving_yards': 'sum',
                        }).reset_index()
    
                        total_defensive_games = offensive_stats['week'].nunique()
    
                        if total_defensive_games > 0:
                            # Now calculate average yards allowed per game
                            avg_passing_yards_allowed = offensive_stats['passing_yards'].mean()
                            avg_rushing_yards_allowed = offensive_stats['rushing_yards'].mean()
                            avg_receiving_yards_allowed = offensive_stats['receiving_yards'].mean()
                        else:
                            avg_passing_yards_allowed = 0
                            avg_rushing_yards_allowed = 0
                            avg_receiving_yards_allowed = 0
                    else:
                        opponent_team = "Unknown"
                        avg_points_allowed = "N/A"
                        avg_passing_yards_allowed = "N/A"
                        avg_rushing_yards_allowed = "N/A"
                        avg_receiving_yards_allowed = "N/A"
    
                    # Prepare a concise prompt
                    prompt = f"""
        You are a sports analyst.
    
        Provide a concise analysis on the likelihood of {selected_player_name} ({position}, {team}) exceeding {float(fixed_line_value)} {selected_display_stat} in the upcoming game against {opponent_team}.
    
        Consider the following statistics:
    
        - **Average {selected_display_stat} over the last 3 games**: {recent_performance:.1f}
        - **Season average {selected_display_stat}**: {season_performance:.1f}
        - **Percentage of games over {float(fixed_line_value)} {selected_display_stat}**: {percentage_over_line:.1f}%
        - **Total games played this season**: {total_games}
    
        Opponent's defensive stats:
    
        - {opponent_team} allows an average of:
        - **Passing yards allowed per game**: {avg_passing_yards_allowed:.1f}
        - **Rushing yards allowed per game**: {avg_rushing_yards_allowed:.1f}
        - **Receiving yards allowed per game**: {avg_receiving_yards_allowed:.1f}
        - **Points allowed per game**: {avg_points_allowed:.1f}
    
        Do not mention previous injuries or factors not included in the data.
    
        Conclude with a clear and concise recommendation on whether it is likely or unlikely that {selected_player_name} will exceed the betting line, supported by the data provided. Bold the key statistics in your response.
        """
    
                    
    
                    # Initialize OpenAI API
                    key = st.secrets["OPENAI_API_KEY"]
                    client=OpenAI(api_key=st.secrets.OPENAI_API_KEY)
    
                    # Make API call to OpenAI GPT
                    try:
                        stream = client.chat.completions.create(
                            model="gpt-4o",
                            messages=[
                                {'role': 'system', 'content': 'you are a helpful assistant'},
                                {"role": "user", "content": prompt}
                            ],
                            
                            temperature=0.7,
                            n=1,
                            stop=None,
                            stream=True
                        )
                        response = st.write_stream(stream)
                    except Exception as e:
                        st.error(f"An error occurred: {e}")


        except ValueError:
            st.error('Please enter a valid number for the betting line.')
            # Plot without betting line
            fig.add_trace(go.Scatter(
                x=plot_data['week'],
                y=plot_data[selected_category],
                mode='lines+markers',
                marker=dict(color='#1f77b4', size=8),
                line=dict(color='#1f77b4', width=3),
                name=selected_display_stat,
                hovertemplate='<b>Week %{x}</b><br>' + f'{selected_display_stat}: ' + '%{y}<extra></extra>'
            ))
    else:
        # Plot without betting line
        fig.add_trace(go.Scatter(
            x=plot_data['week'],
            y=plot_data[selected_category],
            mode='lines+markers',
            marker=dict(color='#1f77b4', size=8),
            line=dict(color='#1f77b4', width=3),
            name=selected_display_stat,
            hovertemplate='<b>Week %{x}</b><br>' + f'{selected_display_stat}: ' + '%{y}<extra></extra>'
        ))

    # Update the chart layout
    fig.update_layout(
        title={
            'text': f'{selected_player_name} - {selected_display_stat} Over Weeks ({selected_season})',
            'y':0.9,
            'x':0.5,
            'xanchor': 'center',
            'yanchor': 'top'},
        xaxis_title='Week',
        yaxis_title=selected_display_stat,
        xaxis=dict(
            tickmode='linear',
            tick0=1,
            dtick=1,
            showgrid=False,
            color='#c9d1d9'
        ),
        yaxis=dict(
            showgrid=True,
            gridcolor='#444',
            zerolinecolor='#444',
            color='#c9d1d9'
        ),
        plot_bgcolor='#0e1117',
        paper_bgcolor='#0e1117',
        font=dict(size=14, color='#c9d1d9'),
        hovermode='x unified',
        margin=dict(l=40, r=40, t=80, b=40),
        showlegend=False
    )

    # Update axes
    fig.update_xaxes(title_font=dict(size=16), tickfont=dict(size=12))
    fig.update_yaxes(title_font=dict(size=16), tickfont=dict(size=12))

    # Display the interactive chart
    chart_placeholder.plotly_chart(fig, use_container_width=True)


    # AI Insight Generation
    #if fixed_line_value:
        
