import streamlit as st
import nfl_data_py as nfl
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

# Load player stats for the current season
seasons = [2023]
player_stats = nfl.import_weekly_data(seasons)

# Create a list of unique player names
player_names = player_stats['player_display_name'].unique()

# Streamlit app
st.title('AI Stats chat')





ai = st.text_input("Enter Text")

openai.api_key = st.secrets.OPENAI_API_KEY


def chatgpt_call(text_input, prompt):
    # Create the full prompt
    full_prompt = f"{prompt}\n\n{text_input}"

    # Make the API call to GPT-4 (or GPT-3.5 if that's what you have access to)
    response = openai.Completion.create(
        engine="gpt-4o",  # or "text-davinci-003" if you don't have access to GPT-4
        prompt=full_prompt,
        max_tokens=150,  # Adjust the number of tokens based on your needs
        n=1,
        stop=None,
        temperature=0.7
    )

    # Extract the response text
    output_text = response.choices[0].text.strip()
    
    return output_text