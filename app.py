"""
Retail Store Daily Revenue Analysis
Supports: CSV (.csv) and Excel (.xlsx, .xls) data sources
Enhanced with interactive Plotly visual analytics:
- Daily revenue trend with 7-day moving average and peak/low annotations
- Cumulative running revenue curve
- Day-over-Day (DoD) % growth rate (positive/negative colored bars)
- Day-of-Week performance & Weekend vs Weekday contribution donut chart
- Revenue distribution histogram and performance tier brackets
- Full dataset viewer with CSV export
"""
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import os

# --- Page Configuration ---
st.set_page_config(
    page_title="Retail Revenue Analytics Dashboard",
    page_icon="🛍️",
    layout="wide"
)

st.title("🛍️ Retail Store Daily Revenue Analytics")
st.markdown("Deep-dive revenue performance, growth trajectories, weekly seasonality, and sales distributions.")

# --- Sidebar: Data Loading ---
st.sidebar.header("📁 Data Source")
uploaded_file = st.sidebar.file_uploader(
    "Upload CSV or Excel file",
    type=["csv", "xlsx", "xls"],
    help="Upload a dataset containing 'Date' and 'Revenue' columns."
)

@st.cache_data
def load_data(file_source):
    if isinstance(file_source, str):
        df = pd.read_csv(file_source)
    else:
        file_name = file_source.name.lower()
        if file_name.endswith((".xlsx", ".xls")):
            df = pd.read_excel(file_source)
        else:
            df = pd.read_csv(file_source)
    
    # Standardize column names (strip whitespace)
    df.columns = [str(c).strip() for c in df.columns]
    
    # Find matching Date and Revenue columns regardless of casing
    col_mapping = {}
    for col in df.columns:
        if col.lower() == "date":
            col_mapping[col] = "Date"
        elif col.lower() == "revenue":
            col_mapping[col] = "Revenue"
    df = df.rename(columns=col_mapping)
    
    if "Date" not in df.columns or "Revenue" not in df.columns:
        return None, "File must contain 'Date' and 'Revenue' columns."
    
    # Clean data types
    df = df.dropna(subset=["Date", "Revenue"])
    df["Date"] = pd.to_datetime(df["Date"], dayfirst=True, errors="coerce")
    df["Revenue"] = pd.to_numeric(df["Revenue"].astype(str).str.replace(r"[^\d.]", "", regex=True), errors="coerce")
    df = df.dropna(subset=["Date", "Revenue"])
    df = df.sort_values("Date").reset_index(drop=True)
    
    # Derived analytical columns
    df["Day_Name"] = df["Date"].dt.day_name()
    df["Is_Weekend"] = df["Date"].dt.dayofweek.isin([5, 6]).map({True: "Weekend", False: "Weekday"})
    df["DoD_Change_Pct"] = df["Revenue"].pct_change() * 100
    df["Cumulative_Revenue"] = df["Revenue"].cumsum()
    df["7_Day_MA"] = df["Revenue"].rolling(window=7, min_periods=1).mean()
    
    return df, None

# Load uploaded file or fallback to default CSV
default_file = "Revenue_analysis.csv"
if uploaded_file is not None:
    df, error = load_data(uploaded_file)
    if error:
        st.error(error)
        st.stop()
    st.sidebar.success(f"Loaded: `{uploaded_file.name}`")
elif os.path.exists(default_file):
    df, error = load_data(default_file)
    if error:
        st.error(error)
        st.stop()
    st.sidebar.info(f"Using default data: `{default_file}`")
else:
    st.warning("⚠️ No data source found. Please upload a CSV or Excel file.")
    st.stop()

# --- Sidebar: Date Range Filter ---
min_date = df["Date"].min().date()
max_date = df["Date"].max().date()

st.sidebar.header("🔍 Filters")
if min_date != max_date:
    selected_range = st.sidebar.date_input(
        "Select Date Range",
        value=(min_date, max_date),
        min_value=min_date,
        max_value=max_date
    )
    if isinstance(selected_range, (tuple, list)) and len(selected_range) == 2:
        start_date, end_date = selected_range
        df = df[(df["Date"].dt.date >= start_date) & (df["Date"].dt.date <= end_date)].copy()
        # Recalculate cumulative revenue on filtered subset
        df["Cumulative_Revenue"] = df["Revenue"].cumsum()
        df["DoD_Change_Pct"] = df["Revenue"].pct_change() * 100
        df["7_Day_MA"] = df["Revenue"].rolling(window=7, min_periods=1).mean()
else:
    st.sidebar.caption(f"Single date available: {min_date}")

if df.empty:
    st.warning("No data found for the selected date range.")
    st.stop()

# --- Metrics Calculations ---
total_revenue = df["Revenue"].sum()
average_revenue = df["Revenue"].mean()
maximum_revenue = df["Revenue"].max()
minimum_revenue = df["Revenue"].min()

peak_row = df.loc[df["Revenue"].idxmax()]
peak_date = peak_row["Date"].strftime("%d-%m-%Y")

lowest_row = df.loc[df["Revenue"].idxmin()]
lowest_date = lowest_row["Date"].strftime("%d-%m-%Y")

# Console Output
print("---------- Date-wise Retail Revenue Analysis -----------")
print(f"Total Revenue   : ₹{total_revenue:,.2f}")
print(f"Average Revenue : ₹{average_revenue:,.2f}")
print(f"Maximum Revenue : ₹{maximum_revenue:,.2f} on {peak_date}")
print(f"Minimum Revenue : ₹{minimum_revenue:,.2f} on {lowest_date}")

# --- KPI Cards ---
st.subheader("📊 Key Performance Indicators")
col1, col2, col3, col4, col5 = st.columns(5)

col1.metric("💰 Total Revenue", f"₹{total_revenue:,.2f}")
col2.metric("📈 Daily Average", f"₹{average_revenue:,.2f}")
col3.metric("🏆 Peak Revenue", f"₹{maximum_revenue:,.2f}", help=f"Peak on {peak_date}")
col4.metric("📉 Lowest Revenue", f"₹{minimum_revenue:,.2f}", help=f"Lowest on {lowest_date}")
col5.metric("🗓️ Days Analyzed", f"{len(df)} days")

st.markdown("---")

# --- Tabs for Rich Visualizations ---
tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "📈 Revenue Trends",
    "🚀 Growth & Cumulative",
    "📅 Day-of-Week & Weekends",
    "📊 Revenue Distribution",
    "📋 Data & Export"
])

# ================= TAB 1: REVENUE TRENDS =================
with tab1:
    st.subheader("📈 Daily Revenue & Moving Average Trend")
    show_ma = st.toggle("Show 7-Day Moving Average", value=True)

    fig_trend = go.Figure()

    # Daily Revenue Line & Points
    fig_trend.add_trace(go.Scatter(
        x=df["Date"],
        y=df["Revenue"],
        mode="lines+markers",
        name="Daily Revenue",
        line=dict(color="#1f77b4", width=2.5),
        marker=dict(size=7, color="#1f77b4"),
        hovertemplate="<b>Date:</b> %{x|%d %b %Y}<br><b>Revenue:</b> ₹%{y:,.2f}<extra></extra>"
    ))

    # 7-Day Moving Average Line
    if show_ma:
        fig_trend.add_trace(go.Scatter(
            x=df["Date"],
            y=df["7_Day_MA"],
            mode="lines",
            name="7-Day Moving Avg",
            line=dict(color="#ff7f0e", width=2.5, dash="dash"),
            hovertemplate="<b>Date:</b> %{x|%d %b %Y}<br><b>7-Day Avg:</b> ₹%{y:,.2f}<extra></extra>"
        ))

    # Peak and Lowest Highlights
    fig_trend.add_trace(go.Scatter(
        x=[peak_row["Date"]],
        y=[maximum_revenue],
        mode="markers+text",
        name="Peak Sales Day",
        text=[f"Peak: ₹{maximum_revenue:,.0f}"],
        textposition="top center",
        marker=dict(color="#2ca02c", size=14, symbol="star")
    ))

    fig_trend.add_trace(go.Scatter(
        x=[lowest_row["Date"]],
        y=[minimum_revenue],
        mode="markers+text",
        name="Lowest Sales Day",
        text=[f"Low: ₹{minimum_revenue:,.0f}"],
        textposition="bottom center",
        marker=dict(color="#d62728", size=12, symbol="triangle-down")
    ))

    fig_trend.update_layout(
        title="Daily Revenue Over Time with Trendline",
        xaxis_title="Date",
        yaxis_title="Revenue (₹)",
        hovermode="x unified",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        template="plotly_white",
        height=480
    )
    st.plotly_chart(fig_trend, use_container_width=True)

# ================= TAB 2: GROWTH & CUMULATIVE =================
with tab2:
    col_grow1, col_grow2 = st.columns(2)

    with col_grow1:
        st.subheader("🚀 Cumulative Revenue Trajectory")
        fig_cum = px.area(
            df,
            x="Date",
            y="Cumulative_Revenue",
            title="Total Accumulated Revenue Over Time",
            labels={"Cumulative_Revenue": "Running Total (₹)", "Date": "Date"},
            color_discrete_sequence=["#2b5c8f"]
        )
        fig_cum.update_traces(
            hovertemplate="<b>Date:</b> %{x|%d %b %Y}<br><b>Accumulated:</b> ₹%{y:,.2f}<extra></extra>"
        )
        fig_cum.update_layout(template="plotly_white", height=420)
        st.plotly_chart(fig_cum, use_container_width=True)

    with col_grow2:
        st.subheader("⚡ Day-over-Day (DoD) % Revenue Change")
        dod_df = df.dropna(subset=["DoD_Change_Pct"]).copy()
        dod_df["Color"] = dod_df["DoD_Change_Pct"].apply(lambda x: "Growth (Up)" if x >= 0 else "Decline (Down)")

        fig_dod = px.bar(
            dod_df,
            x="Date",
            y="DoD_Change_Pct",
            color="Color",
            color_discrete_map={"Growth (Up)": "#2ca02c", "Decline (Down)": "#d62728"},
            title="Daily Percentage Fluctuation vs Previous Day",
            labels={"DoD_Change_Pct": "DoD Change (%)", "Date": "Date"}
        )
        fig_dod.update_traces(
            hovertemplate="<b>Date:</b> %{x|%d %b %Y}<br><b>DoD Growth:</b> %{y:+.2f}%<extra></extra>"
        )
        fig_dod.update_layout(template="plotly_white", height=420, legend_title="")
        st.plotly_chart(fig_dod, use_container_width=True)

# ================= TAB 3: DAY-OF-WEEK & WEEKENDS =================
with tab3:
    col_dow1, col_dow2 = st.columns([1.6, 1.2])

    days_order = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
    dow_df = (
        df.groupby("Day_Name")["Revenue"]
        .agg(Average_Revenue="mean", Total_Revenue="sum", Order_Count="count")
        .reindex(days_order)
        .dropna()
        .reset_index()
    )

    with col_dow1:
        st.subheader("📅 Average Revenue by Day of Week")
        fig_dow = px.bar(
            dow_df,
            x="Day_Name",
            y="Average_Revenue",
            color="Average_Revenue",
            color_continuous_scale="Blues",
            title="Staffing & Demand Guide (Avg Sales per Weekday)",
            labels={"Average_Revenue": "Avg Revenue (₹)", "Day_Name": "Day of Week"}
        )
        fig_dow.update_traces(
            hovertemplate="<b>%{x}:</b> ₹%{y:,.2f}<extra></extra>"
        )
        fig_dow.update_layout(template="plotly_white", height=420)
        st.plotly_chart(fig_dow, use_container_width=True)

    with col_dow2:
        st.subheader("🍕 Weekend vs Weekday Revenue Share")
        weekend_df = df.groupby("Is_Weekend")["Revenue"].sum().reset_index()

        fig_pie = px.pie(
            weekend_df,
            names="Is_Weekend",
            values="Revenue",
            hole=0.45,
            color="Is_Weekend",
            color_discrete_map={"Weekend": "#ff7f0e", "Weekday": "#1f77b4"},
            title="Revenue Contribution Split"
        )
        fig_pie.update_traces(
            textinfo="percent+label",
            hovertemplate="<b>%{label}:</b> ₹%{value:,.2f} (%{percent})<extra></extra>"
        )
        fig_pie.update_layout(template="plotly_white", height=420)
        st.plotly_chart(fig_pie, use_container_width=True)

# ================= TAB 4: DISTRIBUTION & TIERS =================
with tab4:
    col_dist1, col_dist2 = st.columns(2)

    with col_dist1:
        st.subheader("📊 Daily Revenue Distribution & Frequency")
        fig_hist = px.histogram(
            df,
            x="Revenue",
            nbins=10,
            marginal="box",
            title="Histogram & Box Plot of Daily Sales",
            labels={"Revenue": "Daily Revenue (₹)"},
            color_discrete_sequence=["#9467bd"]
        )
        fig_hist.update_layout(template="plotly_white", height=420)
        st.plotly_chart(fig_hist, use_container_width=True)

    with col_dist2:
        st.subheader("🏷️ Sales Performance Tiers")
        
        # Categorize revenue into business tiers
        def categorize_tier(rev):
            if rev >= 20000:
                return "🌟 High (> ₹20k)"
            elif rev >= 13000:
                return "⚡ Medium (₹13k - ₹20k)"
            else:
                return "💤 Low (< ₹13k)"
        
        tier_df = df.copy()
        tier_df["Tier"] = tier_df["Revenue"].apply(categorize_tier)
        tier_counts = tier_df["Tier"].value_counts().reset_index()
        tier_counts.columns = ["Tier", "Days_Count"]

        fig_tier = px.bar(
            tier_counts,
            x="Tier",
            y="Days_Count",
            color="Tier",
            color_discrete_sequence=px.colors.qualitative.Safe,
            title="Number of Days in Each Revenue Bracket",
            labels={"Days_Count": "Number of Days"}
        )
        fig_tier.update_layout(template="plotly_white", height=420, showlegend=False)
        st.plotly_chart(fig_tier, use_container_width=True)

# ================= TAB 5: RAW DATA & EXPORT =================
with tab5:
    st.subheader("📋 Filtered Dataset with Analytics")
    display_df = df[["Date", "Day_Name", "Is_Weekend", "Revenue", "Cumulative_Revenue", "DoD_Change_Pct"]].copy()
    display_df["Date"] = display_df["Date"].dt.strftime("%Y-%m-%d")
    
    st.dataframe(
        display_df.style.format({
            "Revenue": "₹{:,.2f}",
            "Cumulative_Revenue": "₹{:,.2f}",
            "DoD_Change_Pct": "{:+.2f}%"
        }),
        use_container_width=True
    )
    
    # CSV Export Button
    csv_data = display_df.to_csv(index=False).encode("utf-8")
    st.download_button(
        label="⬇️ Download Analyzed Data as CSV",
        data=csv_data,
        file_name="retail_revenue_analyzed.csv",
        mime="text/csv"
    )
