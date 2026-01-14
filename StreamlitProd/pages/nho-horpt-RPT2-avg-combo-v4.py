import streamlit as st
import pandas as pd
import altair as alt
import plotly.express as px
import plotly.io as pio
import gspread
from google.oauth2.service_account import Credentials

# import plotly.graph_objects as go
pio.templates.default = "plotly"

st.set_page_config(page_title="HORPT2: HO Avg Rating & Composite Score", layout="wide")
st.title("📊 HO Avg Rating and Composite Score (HORPT2)")

# Check login
if not st.session_state.get("authenticated", False):
    st.warning("Please log in first from the main page.")
    st.stop()

email = st.session_state["user_email"]
role = st.session_state["user_role"]
st.write(f"**You are logged in under {email} as {role}**")

def get_google_sheets_client():
    """
    Initialize Google Sheets client using service account credentials
    """
    try:
        # Get credentials from Streamlit secrets
        credentials_dict = st.secrets["google_service_account"]
        
        # Define the scope
        scope = [
            "https://spreadsheets.google.com/feeds",
            "https://www.googleapis.com/auth/drive"
        ]
        
        # Create credentials
        credentials = Credentials.from_service_account_info(
            credentials_dict, 
            scopes=scope
        )
        
        # Initialize the client
        client = gspread.authorize(credentials)
        return client
    
    except Exception as e:
        st.error(f"Authentication failed: {str(e)}")
        st.error("Please check your Google service account configuration.")
        return None

@st.cache_data(ttl=300)  # Cache for 5 minutes
def load_nho_data():
    """
    Load NHO data from Google Sheets
    """
    try:
        client = get_google_sheets_client()
        if client is None:
            return pd.DataFrame()
        
        # Get the Google Sheet ID from secrets
        sheet_id = st.secrets["nho_data_sheet_id"]
        
        # Open the sheet
        sheet = client.open_by_key(sheet_id)
        
        # Get the specific worksheet (equivalent to "00-HO-Data-Prime-no-link")
        worksheet = sheet.worksheet("00-HO-Data-Prime-no-link")
        
        # Get all records
        records = worksheet.get_all_records()
        
        # Convert to DataFrame
        df = pd.DataFrame(records)
        
        # Convert timestamp column to datetime
        if 'Timestamp' in df.columns:
            df["Timestamp"] = pd.to_datetime(df["Timestamp"], errors='coerce')
        
        # Convert numeric columns
        numeric_columns = ['Rating', 'composite_score']
        for col in numeric_columns:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce')
        
        # Clean up empty rows
        df = df.dropna(how='all')
        
        return df
    
    except Exception as e:
        st.error(f"Failed to load NHO data from Google Sheets: {str(e)}")
        return pd.DataFrame()

# Load data
with st.spinner("Loading NHO data..."):
    df = load_nho_data()

if df.empty:
    st.error("No NHO data found. Please check your Google Sheets configuration.")
    st.stop()

# Change point

# Filter by user
if role != "admin":
    df = df[df["User email"] == email]

# check if empty
if df.empty:
    st.warning("No data found for the selected user.")
    st.warning("Please log in with a different account from the main page.")
    st.stop()

# Sidebar filters
st.sidebar.header("📅 Filter Options")
start_date = st.sidebar.date_input("Start Date", value=df["Timestamp"].min())
end_date = st.sidebar.date_input("End Date", value=df["Timestamp"].max())

indicators = df["Indicator"].dropna().unique()
selected_indicators = st.sidebar.multiselect("🎯 Select up to 3 Indicators", indicators, max_selections=3)

if role == "admin":
    emails = df["User email"].dropna().unique() # if more than xx, perhaps just ask for input
    selected_emails = st.sidebar.multiselect("🎯 Select up to 3 emails", emails, max_selections=3)
#   selected_emails = st.text_input("Enter user email to filter:").strip().lower()
else:
    selected_emails = ""

# Apply filters
mask = (
    (df["Timestamp"].dt.date >= start_date) &
    (df["Timestamp"].dt.date <= end_date)
)
if selected_indicators:
    mask &= df["Indicator"].isin(selected_indicators)
if selected_emails:
    mask &= df["User email"].isin(selected_emails)

filtered = df[mask]

if filtered.empty:
    st.warning("No data found for the selected filters.")
    # st.warning("Please select at least one indicator.")
    st.stop()

# Total unique session count
total_unique_sessions = filtered["sess6digit"].nunique()
st.metric(label="Total Unique Sessions: ", value=total_unique_sessions)

# Average Rating and Composite Score
mean_ratings = filtered["Rating"].mean()
rounded_mean_ratings = round(mean_ratings, 2)  # Round to 2 decimal places
st.metric("Average Rating: ", rounded_mean_ratings)

mean_compscores = filtered["composite_score"].mean()
rounded_mean_compscores = round(mean_compscores, 2)  # Round to 2 decimal places
st.metric("Average Composite Score: ", rounded_mean_compscores)

# Group data and create the line chart
grouped_data = filtered.groupby([filtered['Timestamp'].dt.date, 'Indicator']).agg(
    Count=('sess6digit', 'nunique'),
    Compscore=('composite_score', 'mean'),
    Nrating=('Rating', 'mean')
    ).reset_index().rename(columns={'Timestamp': 'Date'})

# Group by Date and Indicator and aggregate composite_score -- old code
# grouped_data = filtered.groupby([filtered['Timestamp'].dt.date, 'Indicator'])['composite_score'].agg(['mean', 'min', 'max']).reset_index().rename(columns={"Timestamp": "Date", "Indicator": "Indicator", "mean": "Avg", "min": "Min" , "max": "Max"})
   
st.subheader("Aggregated Rating and Composite-Score Statistics")
st.dataframe(grouped_data)

st.subheader(" 📆 Avg Ratings and Composite-Scores Over Time for Selected Indicators")
    # Create columns
col1, col2 = st.columns(2)
col3, col4 = st.columns(2)

# Line Rating in the first column
with col1:
      # st.subheader(" 📆 Line Chart: ")
      line_fig1 = px.line(grouped_data,
                      x='Date',
                      y='Nrating',
                      color='Indicator',  # Color lines by indicator
                      title='Line Chart -- Mean Rating Over Time',
                      # trendline="ols"
       )
      #line_fig.update_layout(width=844, height=390, autosize=False)
      st.plotly_chart(line_fig1, use_container_width=True)
    
      # Scatter plot in the second column
with col2:
      # st.subheader("📆 Scatter Chart: ")
      scatter_fig1 = px.scatter(grouped_data,
                      x='Date',
                      y='Nrating',
                      color ='Indicator',  # Color lines by indicator
                      # trendline="ols",
                      title='Scatter - Mean Rating Over Time'
                      )
      #scatter_fig.update_layout(width=844, height=390, autosize=False)
      st.plotly_chart(scatter_fig1, use_container_width=True)      

with col3:
      # st.subheader(" 📆 Line Chart: ")
      line_fig2 = px.line(grouped_data,
                      x='Date',
                      y='Compscore',
                      color='Indicator',  # Color lines by indicator
                      title='Line Chart -- Mean composite_score Over Time',
                      # trendline="ols"
       )
      #line_fig.update_layout(width=844, height=390, autosize=False)
      st.plotly_chart(line_fig2, use_container_width=True)
    
      # Scatter plot in the second column
with col4:
      # st.subheader("📆 Scatter Chart: ")
      scatter_fig2 = px.scatter(grouped_data,
                      x='Date',
                      y='Compscore',
                      color ='Indicator',  # Color lines by indicator
                      # trendline="ols",
                      title='Scatter - Mean composite_score Over Time'
                      )
      #scatter_fig.update_layout(width=844, height=390, autosize=False)
      st.plotly_chart(scatter_fig2, use_container_width=True)

# save original code
# chart = alt.Chart(summary).mark_bar().encode(
#    x=alt.X("Indicator:N", sort="-y", title="Indicator"),
#    y=alt.Y("Avg:Q", title="Average composite_score"),
#    tooltip=["Indicator", "Avg", "Min", "Max", "composite_scores"]
# ).properties(
#    width=500,
#    height=300
#)

# st.altair_chart(chart, use_container_width=True)

