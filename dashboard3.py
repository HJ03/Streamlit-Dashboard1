import streamlit as st
from pymongo import MongoClient
import plotly.express as px
import pandas as pd
import pytz

st.set_page_config(page_title="Dashboard 3", page_icon=":eagle:", layout="wide")

st.title(":bar_chart: Analysis")
st.markdown('<style>div.block-container{padding-top:2rem;}', unsafe_allow_html=True)


# MongoDB connection
client = MongoClient("mongodb://65.2.116.84:27017/")
db = client["production"]

# Pipeline for MongoDB aggregation
pipeline = [
    {
        "$lookup": {
            "from": "serviceplans",
            "localField": "servicePlan",  # Foreign key in collection1
            "foreignField": "_id",
            "as": "servicePlansData"
        }
    },
    {
        "$lookup": {
            "from": "users",
            "localField": "user",  # Foreign key in collection1
            "foreignField": "_id",
            "as": "user_data"
        }
    },
    {
        "$unwind": "$user_data"  # Unwind the array created by $lookup
    },
    {
        "$lookup": {
            "from": "clients",
            "localField": "user_data.client",  # Foreign key in collection2
            "foreignField": "_id",
            "as": "client_name"
        }
    },
    {
        "$project": {
            "_id": 0,
            # "state":"$state",
            "date":"$createdAt",
            "courseName": {"$arrayElemAt": ["$servicePlansData.name", 0]},
            "coursePrice": {"$arrayElemAt": ["$servicePlansData.basePrice", 0]},
            "userName": "$user_data.name",
            "userEmail": "$user_data.email",
            "clientName": {"$arrayElemAt": ["$client_name.name", 0]},
            # Add more desired columns if needed
        }
    }
]

# MongoDB aggregation result
result = list(db.serviceplanrequests.aggregate(pipeline))
df_raw = pd.DataFrame(result)

# Data preprocessing
df = df_raw[["date", "courseName", "coursePrice", "clientName"]]
df['date'] = pd.to_datetime(df['date'])
original_timezone = pytz.utc
indian_timezone = pytz.timezone('Asia/Kolkata')
df['date'] = df['date'].dt.tz_localize(original_timezone).dt.tz_convert(indian_timezone)
df['month'] = df['date'].dt.month
df['year'] = df['date'].dt.year

# Default year for initial display
current_year = pd.Timestamp.now().year

# Sidebar options
clients = sorted(df['clientName'].astype(str).unique())
selected_client = st.sidebar.selectbox('Select Client:', [''] + clients)

# Show or hide year dropdown based on whether a client is selected
if selected_client:
    years = [''] + sorted(df['year'].unique())
    selected_year = st.sidebar.selectbox('Select Year:', years, index=years.index(current_year) + 1 if current_year in years else 0)
else:
    selected_year = ''

# Filter data based on sidebar selections
filtered_df = df[(df['clientName'] == selected_client) & (df['year'] == selected_year)]

# Line chart showing total sales by client for all years
fig_line_chart = px.line(df.groupby(['year', 'month', 'clientName']).sum('coursePrice').reset_index(),
                         x='month', y='coursePrice', color='clientName', facet_col='year',
                         labels={'coursePrice': 'Total Sales (Rupees)'},  # Update y-axis label
                         title='Total Monthly Sales by Client for All Years')

# Format y-axis as rupees
fig_line_chart.update_layout(yaxis_tickprefix='₹', yaxis_ticksuffix='')  # Add rupee symbol as prefix

# Display the initial line chart unless both client and year are selected
if not (selected_client and selected_year):
    st.plotly_chart(fig_line_chart, use_container_width=True)
else:
    # Display the top and bottom selling charts only when both client and year are selected
    # Set the title for course analysis with Markdown for smaller size
    st.markdown(f'## Course Analysis of {selected_client} for Year {selected_year}', unsafe_allow_html=True)

    # Bar chart showing top selling courses
    fig_bar_chart_top = px.bar(filtered_df.groupby('courseName').size().reset_index(name='count').nlargest(10, 'count'),
                               x='courseName', y='count', color='count',
                               labels={'count': 'Count'},
                               title='Top 10 Selling Courses')

    # Add count values on the top bar chart
    fig_bar_chart_top.update_traces(texttemplate='%{y}', textposition='inside')

    # Bar chart showing bottom selling courses
    fig_bar_chart_bottom = px.bar(filtered_df.groupby('courseName').size().reset_index(name='count').nsmallest(10, 'count'),
                                  x='courseName', y='count', color='count',
                                  labels={'count': 'Count'},
                                  title='Bottom 10 Selling Courses')

    # Add count values on the bottom bar chart
    fig_bar_chart_bottom.update_traces(texttemplate='%{y}', textposition='inside')

    # Display top and bottom selling charts
    st.plotly_chart(fig_bar_chart_top, use_container_width=True)
    st.plotly_chart(fig_bar_chart_bottom, use_container_width=True)

    # Sidebar option to select a specific course
    courses = sorted(filtered_df['courseName'].astype(str).unique())
    selected_course = st.sidebar.selectbox('Select Course:', [''] + courses)

    if selected_course:
        # Filter data based on the selected course
        filtered_course_df = filtered_df[filtered_df['courseName'] == selected_course]

        # Line chart showing monthly sales of the selected course
        fig_course_chart = px.line(filtered_course_df.groupby('month').sum('coursePrice').reset_index(),
                                   x='month', y='coursePrice',
                                   labels={'coursePrice': f'Sales of {selected_course} (Rupees)'},
                                   title=f'Monthly Sales of {selected_course} for {selected_client} in {selected_year}')

        # Format y-axis as rupees
        fig_course_chart.update_layout(yaxis_tickprefix='₹', yaxis_ticksuffix='')  # Add rupee symbol as prefix

        # Update x-axis ticks to display actual month names
        month_names = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
        fig_course_chart.update_xaxes(tickmode='array', tickvals=list(range(1, 13)), ticktext=month_names)

        # Display the course chart
        st.plotly_chart(fig_course_chart, use_container_width=True)

