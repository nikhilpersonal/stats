import streamlit as st
import pandas as pd
import plotly.express as px
import nfl_data_py as nfl

# Set the page layout to wide and add a title
st.set_page_config(layout='wide', page_title='NFL Player Statistics Visualization')

# Function to get player statistics
@st.cache_data
def get_player_stats():
    # Fetch data for the desired seasons, including 2024
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
selected_season = st.sidebar.selectbox('Select a Season (Year):', available_seasons)

# Filter data for the selected season
df_season = df[df['season'] == selected_season]

# Get the list of players for the selected season
player_names = df_season[name_column].dropna().unique()
player_names.sort()

# Player selection
selected_player_name = st.sidebar.selectbox('Select a Player:', player_names)

# Filter data for the selected player and season
player_data = df_season[df_season[name_column] == selected_player_name]

# Get player's information
player_info = roster_df[roster_df['full_name'] == selected_player_name].iloc[0]
headshot_url = player_info.get('headshot_url', '')
position = player_info.get('position', 'N/A')
team = player_info.get('team', 'N/A')

# Display player image, information, and metrics inline
st.markdown(f"## {selected_player_name}")
col1, col2 = st.columns([1, 4])

with col1:
    if headshot_url:
        st.image(headshot_url, width=150)
    else:
        st.write("No image available.")

with col2:
    # Display player details
    st.markdown(f"**Position**: {position}")
    st.markdown(f"**Team**: {team}")

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
                'Passing Touchdowns': 'passing_tds',
                'Rushing Touchdowns': 'rushing_tds'
            }
        elif position == 'RB':
            # Total touchdowns (rushing + receiving)
            player_data['total_tds'] = player_data['rushing_tds'] + player_data['receiving_tds']
            metric_stats = {
                'Rushing Yards': 'rushing_yards',
                'Receiving Yards': 'receiving_yards',
                'Total Touchdowns': 'total_tds'
            }
        elif position in ['WR', 'TE']:
            # Total touchdowns (rushing + receiving)
            player_data['total_tds'] = player_data['rushing_tds'] + player_data['receiving_tds']
            metric_stats = {
                'Receiving Yards': 'receiving_yards',
                'Receptions': 'receptions',
                'Total Touchdowns': 'total_tds'
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

            # Metrics display inline with player info
            metric_cols = st.columns(len(metric_stats))
            for i, (metric_name, metric_column) in enumerate(metric_stats.items()):
                # Average over last 3 games
                last_3_avg = last_3_games[metric_column].mean()
                # Season average
                season_avg_metric = season_avg.get(metric_column, 0)
                # Delta
                delta = last_3_avg - season_avg_metric
                metric_cols[i].metric(
                    label=metric_name,
                    value=f"{last_3_avg:.1f}",
                    delta=f"{delta:+.1f}"
                )

# Box Score
st.markdown("### Game-by-Game Stats")
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

# Plotly Chart Inputs
st.markdown("### Performance Over Time")
# Mapping of display names to internal column names
stats_columns = {
    'Passing Yards': 'passing_yards',
    'Passing Touchdowns': 'passing_tds',
    'Interceptions': 'interceptions',
    'Rushing Yards': 'rushing_yards',
    'Rushing Touchdowns': 'rushing_tds',
    'Receiving Yards': 'receiving_yards',
    'Receiving Touchdowns': 'receiving_tds',
    'Receptions': 'receptions',
    'Targets': 'targets',
    'Fumbles Lost': 'fumbles_lost',
    'Fantasy Points PPR': 'fantasy_points_ppr'
}
# Filter out columns that may not be in the data
available_stats = {k: v for k, v in stats_columns.items() if v in player_data.columns}

# Statistic selection
col_stat, col_line = st.columns([2, 1])
with col_stat:
    selected_display_stat = st.selectbox('Select a Statistic to Plot:', list(available_stats.keys()))
with col_line:
    fixed_line_value = st.text_input('Betting Line:', key='betting_line')

selected_category = available_stats[selected_display_stat]

# Create a copy of player_data to avoid SettingWithCopyWarning
plot_data = player_data.copy()

# Plotting with Plotly
import plotly.graph_objects as go

if fixed_line_value:
    try:
        value = float(fixed_line_value)
        # Compute over/under stats
        plot_data['over_line'] = plot_data[selected_category] > value
        weeks_over = plot_data['over_line'].sum()
        total_weeks = plot_data['over_line'].count()

        # Display feedback with a big green arrow if positive
        percentage_over = (weeks_over / total_weeks) * 100 if total_weeks > 0 else 0
        st.markdown("### Betting Line Analysis")
        arrow = "⬆️" if weeks_over > (total_weeks / 2) else "⬇️"
        st.success(f"{arrow} **{selected_player_name} exceeded the line in {weeks_over}/{total_weeks} weeks ({percentage_over:.1f}% of games).**")

        # Create the figure
        fig = go.Figure()

        # Add the player's performance line with conditional marker colors
        fig.add_trace(go.Scatter(
            x=plot_data['week'],
            y=plot_data[selected_category],
            mode='lines+markers',
            marker=dict(
                color=['green' if over else 'red' for over in plot_data['over_line']],
                size=10
            ),
            line=dict(color='blue'),
            name=selected_display_stat
        ))

        # Add horizontal line for betting line
        fig.add_hline(
            y=value,
            line_dash='dash',
            line_color='blue',
            annotation_text=f'Betting Line at {value}',
            annotation_position="top left"
        )

        fig.update_layout(
            title=f'{selected_player_name} - {selected_display_stat} Over Weeks ({selected_season})',
            xaxis_title='Week',
            yaxis_title=selected_display_stat,
            xaxis=dict(tickmode='linear', tick0=1, dtick=1),
            title_x=0.5,
            showlegend=False
        )
    except ValueError:
        st.error('Please enter a valid number for the betting line.')
else:
    # Plotting without betting line using Plotly Express
    fig = px.line(
        plot_data,
        x='week',
        y=selected_category,
        title=f'{selected_player_name} - {selected_display_stat} Over Weeks ({selected_season})',
        markers=True
    )
    fig.update_layout(
        xaxis_title='Week',
        yaxis_title=selected_display_stat,
        xaxis=dict(tickmode='linear', tick0=1, dtick=1),
        title_x=0.5
    )

# Display the plot
st.plotly_chart(fig, use_container_width=True)
