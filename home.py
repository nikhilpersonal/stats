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
        background-color: #161b22;
        color: #c9d1d9;
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
                    size=10,
                    line=dict(width=1, color='white')
                ),
                line=dict(color='#1f77b4', width=3),
                name=selected_display_stat
            ))

            # Add horizontal line for betting line
            fig.add_hline(
                y=value,
                line_dash='dash',
                line_color='yellow',
                annotation_text=f'Betting Line at {value}',
                annotation_position="top left",
                annotation_font_color='yellow',
                annotation_bgcolor='#0e1117'
            )

        except ValueError:
            st.error('Please enter a valid number for the betting line.')
            # Plot without betting line
            fig.add_trace(go.Scatter(
                x=plot_data['week'],
                y=plot_data[selected_category],
                mode='lines+markers',
                marker=dict(color='#1f77b4', size=8),
                line=dict(color='#1f77b4', width=3),
                name=selected_display_stat
            ))
    else:
        # Plot without betting line
        fig.add_trace(go.Scatter(
            x=plot_data['week'],
            y=plot_data[selected_category],
            mode='lines+markers',
            marker=dict(color='#1f77b4', size=8),
            line=dict(color='#1f77b4', width=3),
            name=selected_display_stat
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
        template = "plotly_dark"
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

    # Update hover label
    fig.update_traces(hovertemplate='<b>Week %{x}</b><br>' + f'{selected_display_stat}: ' + '%{y}<extra></extra>')

    # Display the plot in the placeholder
    chart_placeholder.plotly_chart(fig, config=config, use_container_width=True)
