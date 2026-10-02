"""
Retail Store Daily Revenue & Multi-Dimensional Analytics Dashboard
Supports:
- Single & multi-column CSV (.csv) and Excel (.xlsx, .xls) files
- Dynamic column mapping for Date and Metric/Revenue headers
- Automatic multi-column categorical filters (Category, Store, Payment Method, etc.)
- Multi-dimensional breakdown charts & visualizations
- Comprehensive daily trends, moving averages, and cumulative curves
"""
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import os

# --- Page Configuration ---
st.set_page_config(
    page_title="Retail Revenue & Sales Analytics",
    page_icon="🛍️",
    layout="wide"
)

st.title("🛍️ Retail Store Daily Revenue Analytics")
st.markdown("Multi-dimensional retail performance analysis with customizable column mapping, categorical slicing, and trend forecasting.")

# --- Sidebar: Data Loading ---
st.sidebar.header("📁 Data Source")
uploaded_file = st.sidebar.file_uploader(
    "Upload CSV or Excel file",
    type=["csv", "xlsx", "xls"],
    help="Upload any retail dataset (CSV or Excel) with at least a Date and a Numeric/Sales column."
)

@st.cache_data
def load_raw_data(file_source):
    """Loads CSV or Excel data while preserving all columns."""
    if isinstance(file_source, str):
        if file_source.endswith((".xlsx", ".xls")):
            df = pd.read_excel(file_source)
        else:
            df = pd.read_csv(file_source)
    else:
        file_name = file_source.name.lower()
        if file_name.endswith((".xlsx", ".xls")):
            df = pd.read_excel(file_source)
        else:
            df = pd.read_csv(file_source)
            
    # Clean whitespace in column names
    df.columns = [str(c).strip() for c in df.columns]
    return df

# Determine data source
raw_df = None
source_name = ""

if uploaded_file is not None:
    try:
        raw_df = load_raw_data(uploaded_file)
        source_name = uploaded_file.name
        st.sidebar.success(f"Loaded: `{source_name}` ({len(raw_df)} rows, {len(raw_df.columns)} columns)")
    except Exception as e:
        st.sidebar.error(f"Error loading file: {e}")
        st.stop()
else:
    # Check for default files
    sample_files = []
    if os.path.exists("multi_column_retail_sample.xlsx"):
        sample_files.append("multi_column_retail_sample.xlsx")
    if os.path.exists("Revenue_analysis.csv"):
        sample_files.append("Revenue_analysis.csv")
    if os.path.exists("sample_revenue.xlsx"):
        sample_files.append("sample_revenue.xlsx")
        
    if sample_files:
        chosen_sample = st.sidebar.selectbox("Or choose a sample dataset:", sample_files)
        raw_df = load_raw_data(chosen_sample)
        source_name = chosen_sample
        st.sidebar.info(f"Using: `{chosen_sample}` ({len(raw_df)} rows, {len(raw_df.columns)} columns)")
    else:
        st.warning("⚠️ No dataset found. Please upload a CSV or Excel file.")
        st.stop()

if raw_df is None or raw_df.empty:
    st.error("The selected dataset is empty.")
    st.stop()

all_columns = list(raw_df.columns)

# --- Sidebar: Dynamic Column Mapping ---
st.sidebar.header("⚙️ Column Mapping")

# Heuristic auto-detection for Date column
date_candidates = [
    col for col in all_columns
    if any(k in col.lower() for k in ["date", "day", "time", "order_date", "trans_date", "dt"])
]
default_date_idx = all_columns.index(date_candidates[0]) if date_candidates else 0

selected_date_col = st.sidebar.selectbox(
    "Select Date Column 📅",
    options=all_columns,
    index=default_date_idx,
    help="Select the column representing transaction or sales dates."
)

# Heuristic auto-detection for Revenue/Value column
numeric_candidates = [
    col for col in all_columns
    if col != selected_date_col and any(
        k in col.lower() for k in ["revenue", "sales", "amount", "total", "price", "turnover", "inr", "value", "units"]
    )
]
if not numeric_candidates:
    # Fallback to any column other than the date column
    numeric_candidates = [c for c in all_columns if c != selected_date_col]

default_metric_idx = all_columns.index(numeric_candidates[0]) if numeric_candidates else (1 if len(all_columns) > 1 else 0)

selected_metric_col = st.sidebar.selectbox(
    "Select Metric / Revenue Column 💰",
    options=[c for c in all_columns if c != selected_date_col],
    index=min(default_metric_idx, len(all_columns) - 2) if len(all_columns) > 1 else 0,
    help="Select the numeric column to analyze (e.g., Revenue, Sales, Profit, Units Sold)."
)

# --- Clean & Parse Data ---
df = raw_df.copy()

# Parse Date
df["Parsed_Date"] = pd.to_datetime(df[selected_date_col], format="mixed", dayfirst=True, errors="coerce")
# Parse Metric
df["Clean_Metric"] = pd.to_numeric(
    df[selected_metric_col].astype(str).str.replace(r"[^\d.-]", "", regex=True),
    errors="coerce"
)

# Drop invalid dates/metrics
df = df.dropna(subset=["Parsed_Date", "Clean_Metric"]).copy()
if df.empty:
    st.error("No valid numeric data found for the selected Date and Metric columns.")
    st.stop()

df = df.sort_values("Parsed_Date").reset_index(drop=True)
df["Day_Name"] = df["Parsed_Date"].dt.day_name()
df["Is_Weekend"] = df["Parsed_Date"].dt.dayofweek.isin([5, 6]).map({True: "Weekend", False: "Weekday"})

# --- Sidebar: Dynamic Categorical Filters ---
# Identify non-Date, non-Metric columns that can serve as dimensions (<= 50 unique values)
categorical_cols = [
    col for col in all_columns
    if col not in [selected_date_col, selected_metric_col]
    and df[col].nunique() <= 50
    and df[col].nunique() > 1
]

if categorical_cols:
    st.sidebar.header("🔍 Dimension Filters")
    for cat_col in categorical_cols:
        # Strip string whitespace
        if df[cat_col].dtype == object or isinstance(df[cat_col].dtype, pd.StringDtype):
            df[cat_col] = df[cat_col].astype(str).str.strip()
        
        unique_options = sorted([str(v) for v in df[cat_col].dropna().unique()])
        selected_options = st.sidebar.multiselect(
            f"Filter {cat_col}",
            options=unique_options,
            default=unique_options,
            help=f"Select values to include for {cat_col}"
        )
        if selected_options:
            df = df[df[cat_col].astype(str).isin(selected_options)]
        else:
            df = df.iloc[0:0]

# --- Sidebar: Date Range Filter ---
st.sidebar.header("🗓️ Date Filter")
if not df.empty:
    min_date = df["Parsed_Date"].min().date()
    max_date = df["Parsed_Date"].max().date()

    if min_date != max_date:
        selected_range = st.sidebar.date_input(
            "Select Date Range",
            value=(min_date, max_date),
            min_value=min_date,
            max_value=max_date
        )
        if isinstance(selected_range, (tuple, list)) and len(selected_range) == 2:
            start_date, end_date = selected_range
            df = df[(df["Parsed_Date"].dt.date >= start_date) & (df["Parsed_Date"].dt.date <= end_date)].copy()
    else:
        st.sidebar.caption(f"Single date available: {min_date}")

if df.empty:
    st.warning("⚠️ No records match the selected filters. Please adjust your selections in the sidebar.")
    st.stop()

# --- Daily Aggregated Data ---
# If multiple rows exist on the same date, group by date for trends
daily_df = (
    df.groupby("Parsed_Date", as_index=False)["Clean_Metric"]
    .sum()
    .rename(columns={"Clean_Metric": "Daily_Total"})
    .sort_values("Parsed_Date")
    .reset_index(drop=True)
)
daily_df["DoD_Change_Pct"] = daily_df["Daily_Total"].pct_change() * 100
daily_df["Cumulative_Total"] = daily_df["Daily_Total"].cumsum()
daily_df["7_Day_MA"] = daily_df["Daily_Total"].rolling(window=7, min_periods=1).mean()
daily_df["Day_Name"] = daily_df["Parsed_Date"].dt.day_name()
daily_df["Is_Weekend"] = daily_df["Parsed_Date"].dt.dayofweek.isin([5, 6]).map({True: "Weekend", False: "Weekday"})

# --- Metric Calculations ---
total_value = df["Clean_Metric"].sum()
total_records = len(df)
total_days = len(daily_df)
avg_daily_value = daily_df["Daily_Total"].mean()
max_daily_row = daily_df.loc[daily_df["Daily_Total"].idxmax()]
min_daily_row = daily_df.loc[daily_df["Daily_Total"].idxmin()]

peak_date_str = max_daily_row["Parsed_Date"].strftime("%d-%m-%Y")
low_date_str = min_daily_row["Parsed_Date"].strftime("%d-%m-%Y")

# Metric formatting helper
is_currency = any(k in selected_metric_col.lower() for k in ["revenue", "sales", "amount", "total", "price", "turnover", "inr"])
metric_symbol = "₹" if is_currency else ""

# --- Key Metric Display Cards ---
st.subheader("📊 Key Performance Indicators")
kpi1, kpi2, kpi3, kpi4, kpi5 = st.columns(5)

kpi1.metric(f"💰 Total {selected_metric_col}", f"{metric_symbol}{total_value:,.2f}")
kpi2.metric(f"📈 Daily Average", f"{metric_symbol}{avg_daily_value:,.2f}")
kpi3.metric(f"🏆 Peak Day", f"{metric_symbol}{max_daily_row['Daily_Total']:,.2f}", help=f"Occurred on {peak_date_str}")
kpi4.metric(f"📉 Lowest Day", f"{metric_symbol}{min_daily_row['Daily_Total']:,.2f}", help=f"Occurred on {low_date_str}")
kpi5.metric("🗓️ Days Analyzed", f"{total_days} days", delta=f"{total_records} transactions" if total_records != total_days else None)

st.markdown("---")

# --- Interactive Tabs ---
tab_titles = ["📈 Daily Trends", "🚀 Growth & Cumulative", "📅 Day-of-Week"]
if categorical_cols:
    tab_titles.append("🏷️ Category Breakdown")
tab_titles.extend(["📊 Distribution & Tiers", "📋 Filtered Data & Export"])

tabs = st.tabs(tab_titles)
tab_idx = 0

# ================= TAB 1: DAILY TRENDS =================
with tabs[tab_idx]:
    tab_idx += 1
    st.subheader(f"📈 Daily {selected_metric_col} Trend & Moving Average")
    
    col_t1, col_t2 = st.columns([3, 1])
    with col_t2:
        show_ma = st.toggle("7-Day Moving Average", value=True)
        slice_by_dim = "None"
        if categorical_cols:
            slice_by_dim = st.selectbox("Split Lines by Dimension:", ["None"] + categorical_cols)
    
    with col_t1:
        if slice_by_dim != "None":
            # Multi-line trend split by category
            dim_trend_df = (
                df.groupby(["Parsed_Date", slice_by_dim])["Clean_Metric"]
                .sum()
                .reset_index()
            )
            fig_trend = px.line(
                dim_trend_df,
                x="Parsed_Date",
                y="Clean_Metric",
                color=slice_by_dim,
                markers=True,
                title=f"Daily {selected_metric_col} by {slice_by_dim}",
                labels={"Parsed_Date": "Date", "Clean_Metric": selected_metric_col}
            )
            fig_trend.update_traces(
                hovertemplate=f"<b>Date:</b> %{{x|%d %b %Y}}<br><b>{slice_by_dim}:</b> %{{data.name}}<br><b>Value:</b> {metric_symbol}%{{y:,.2f}}<extra></extra>"
            )
        else:
            fig_trend = go.Figure()
            # Daily total line
            fig_trend.add_trace(go.Scatter(
                x=daily_df["Parsed_Date"],
                y=daily_df["Daily_Total"],
                mode="lines+markers",
                name="Daily Total",
                line=dict(color="#1f77b4", width=2.5),
                marker=dict(size=7, color="#1f77b4"),
                hovertemplate=f"<b>Date:</b> %{{x|%d %b %Y}}<br><b>Total:</b> {metric_symbol}%{{y:,.2f}}<extra></extra>"
            ))
            # Moving average line
            if show_ma:
                fig_trend.add_trace(go.Scatter(
                    x=daily_df["Parsed_Date"],
                    y=daily_df["7_Day_MA"],
                    mode="lines",
                    name="7-Day Moving Avg",
                    line=dict(color="#ff7f0e", width=2.5, dash="dash"),
                    hovertemplate=f"<b>Date:</b> %{{x|%d %b %Y}}<br><b>7-Day Avg:</b> {metric_symbol}%{{y:,.2f}}<extra></extra>"
                ))
            # Peak and low pins
            fig_trend.add_trace(go.Scatter(
                x=[max_daily_row["Parsed_Date"]],
                y=[max_daily_row["Daily_Total"]],
                mode="markers+text",
                name="Peak Day",
                text=[f"Peak: {metric_symbol}{max_daily_row['Daily_Total']:,.0f}"],
                textposition="top center",
                marker=dict(color="#2ca02c", size=14, symbol="star")
            ))
            fig_trend.add_trace(go.Scatter(
                x=[min_daily_row["Parsed_Date"]],
                y=[min_daily_row["Daily_Total"]],
                mode="markers+text",
                name="Lowest Day",
                text=[f"Low: {metric_symbol}{min_daily_row['Daily_Total']:,.0f}"],
                textposition="bottom center",
                marker=dict(color="#d62728", size=12, symbol="triangle-down")
            ))

        fig_trend.update_layout(
            xaxis_title="Date",
            yaxis_title=f"{selected_metric_col} ({metric_symbol})" if metric_symbol else selected_metric_col,
            hovermode="x unified" if slice_by_dim == "None" else "closest",
            template="plotly_white",
            height=460
        )
        st.plotly_chart(fig_trend, width="stretch")

# ================= TAB 2: GROWTH & CUMULATIVE =================
with tabs[tab_idx]:
    tab_idx += 1
    col_grow1, col_grow2 = st.columns(2)

    with col_grow1:
        st.subheader("🚀 Cumulative Total Trajectory")
        fig_cum = px.area(
            daily_df,
            x="Parsed_Date",
            y="Cumulative_Total",
            title=f"Total Accumulated {selected_metric_col} Over Time",
            labels={"Cumulative_Total": f"Cumulative {selected_metric_col}", "Parsed_Date": "Date"},
            color_discrete_sequence=["#2b5c8f"]
        )
        fig_cum.update_traces(
            hovertemplate=f"<b>Date:</b> %{{x|%d %b %Y}}<br><b>Cumulative:</b> {metric_symbol}%{{y:,.2f}}<extra></extra>"
        )
        fig_cum.update_layout(template="plotly_white", height=420)
        st.plotly_chart(fig_cum, width="stretch")

    with col_grow2:
        st.subheader("⚡ Day-over-Day (DoD) % Fluctuation")
        dod_df = daily_df.dropna(subset=["DoD_Change_Pct"]).copy()
        dod_df["Color"] = dod_df["DoD_Change_Pct"].apply(lambda x: "Growth (Up)" if x >= 0 else "Decline (Down)")

        fig_dod = px.bar(
            dod_df,
            x="Parsed_Date",
            y="DoD_Change_Pct",
            color="Color",
            color_discrete_map={"Growth (Up)": "#2ca02c", "Decline (Down)": "#d62728"},
            title="Daily % Growth vs Previous Day",
            labels={"DoD_Change_Pct": "DoD Change (%)", "Parsed_Date": "Date"}
        )
        fig_dod.update_traces(
            hovertemplate="<b>Date:</b> %{x|%d %b %Y}<br><b>DoD Change:</b> %{y:+.2f}%<extra></extra>"
        )
        fig_dod.update_layout(template="plotly_white", height=420, legend_title="")
        st.plotly_chart(fig_dod, width="stretch")

# ================= TAB 3: DAY-OF-WEEK & WEEKENDS =================
with tabs[tab_idx]:
    tab_idx += 1
    col_dow1, col_dow2 = st.columns([1.6, 1.2])

    days_order = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
    dow_df = (
        daily_df.groupby("Day_Name")["Daily_Total"]
        .agg(Average_Value="mean", Total_Value="sum", Day_Count="count")
        .reindex(days_order)
        .dropna()
        .reset_index()
    )

    with col_dow1:
        st.subheader("📅 Average Daily Sales by Day of Week")
        fig_dow = px.bar(
            dow_df,
            x="Day_Name",
            y="Average_Value",
            color="Average_Value",
            color_continuous_scale="Blues",
            title=f"Average {selected_metric_col} by Weekday",
            labels={"Average_Value": f"Average ({metric_symbol})", "Day_Name": "Day"}
        )
        fig_dow.update_traces(
            hovertemplate=f"<b>%{{x}}:</b> {metric_symbol}%{{y:,.2f}}<extra></extra>"
        )
        fig_dow.update_layout(template="plotly_white", height=420)
        st.plotly_chart(fig_dow, width="stretch")

    with col_dow2:
        st.subheader("🍕 Weekend vs Weekday Contribution")
        weekend_df = daily_df.groupby("Is_Weekend")["Daily_Total"].sum().reset_index()

        fig_pie = px.pie(
            weekend_df,
            names="Is_Weekend",
            values="Daily_Total",
            hole=0.45,
            color="Is_Weekend",
            color_discrete_map={"Weekend": "#ff7f0e", "Weekday": "#1f77b4"},
            title=f"Total {selected_metric_col} Share"
        )
        fig_pie.update_traces(
            textinfo="percent+label",
            hovertemplate=f"<b>%{{label}}:</b> {metric_symbol}%{{value:,.2f}} (%{{percent}})<extra></extra>"
        )
        fig_pie.update_layout(template="plotly_white", height=420)
        st.plotly_chart(fig_pie, width="stretch")

# ================= TAB 4: CATEGORY BREAKDOWN (IF AVAILABLE) =================
if categorical_cols:
    with tabs[tab_idx]:
        tab_idx += 1
        st.subheader("🏷️ Dimensional Category Breakdown")
        
        target_cat = st.selectbox("Select Dimension to Analyze:", categorical_cols, index=0)
        
        cat_agg = (
            df.groupby(target_cat)["Clean_Metric"]
            .agg(Total="sum", Average="mean", Count="count")
            .reset_index()
            .sort_values("Total", ascending=False)
        )

        col_c1, col_c2 = st.columns([1.4, 1.0])
        with col_c1:
            fig_cat_bar = px.bar(
                cat_agg,
                x=target_cat,
                y="Total",
                color="Total",
                color_continuous_scale="Viridis",
                title=f"Total {selected_metric_col} by {target_cat}",
                labels={"Total": f"Total {selected_metric_col}", target_cat: target_cat}
            )
            fig_cat_bar.update_traces(
                hovertemplate=f"<b>%{{x}}:</b> {metric_symbol}%{{y:,.2f}}<extra></extra>"
            )
            fig_cat_bar.update_layout(template="plotly_white", height=420)
            st.plotly_chart(fig_cat_bar, width="stretch")

        with col_c2:
            fig_cat_pie = px.pie(
                cat_agg,
                names=target_cat,
                values="Total",
                hole=0.4,
                title=f"{target_cat} Share (%)"
            )
            fig_cat_pie.update_traces(
                textinfo="percent+label",
                hovertemplate=f"<b>%{{label}}:</b> {metric_symbol}%{{value:,.2f}} (%{{percent}})<extra></extra>"
            )
            fig_cat_pie.update_layout(template="plotly_white", height=420)
            st.plotly_chart(fig_cat_pie, width="stretch")

        st.write(f"### 📋 {target_cat} Summary Table")
        st.dataframe(
            cat_agg.style.format({
                "Total": f"{metric_symbol}{{:,.2f}}",
                "Average": f"{metric_symbol}{{:,.2f}}",
                "Count": "{:,}"
            }),
            width="stretch"
        )

# ================= TAB 5: DISTRIBUTION & TIERS =================
with tabs[tab_idx]:
    tab_idx += 1
    col_dist1, col_dist2 = st.columns(2)

    with col_dist1:
        st.subheader(f"📊 Daily {selected_metric_col} Distribution")
        fig_hist = px.histogram(
            daily_df,
            x="Daily_Total",
            nbins=12,
            marginal="box",
            title="Histogram & Box Plot (Daily Performance Density)",
            labels={"Daily_Total": f"Daily {selected_metric_col}"},
            color_discrete_sequence=["#9467bd"]
        )
        fig_hist.update_layout(template="plotly_white", height=420)
        st.plotly_chart(fig_hist, width="stretch")

    with col_dist2:
        st.subheader("🏷️ Performance Tiers")
        
        # Calculate dynamic quantile tiers
        q33 = daily_df["Daily_Total"].quantile(0.33)
        q66 = daily_df["Daily_Total"].quantile(0.66)
        
        def calculate_tier(val):
            if val >= q66:
                return f"🌟 High (≥ {metric_symbol}{q66:,.0f})"
            elif val >= q33:
                return f"⚡ Medium ({metric_symbol}{q33:,.0f} - {metric_symbol}{q66:,.0f})"
            else:
                return f"💤 Low (< {metric_symbol}{q33:,.0f})"
        
        tier_series = daily_df["Daily_Total"].apply(calculate_tier)
        tier_counts = tier_series.value_counts().reset_index()
        tier_counts.columns = ["Tier", "Days_Count"]

        fig_tier = px.bar(
            tier_counts,
            x="Tier",
            y="Days_Count",
            color="Tier",
            color_discrete_sequence=px.colors.qualitative.Safe,
            title="Days Count in Each Performance Bracket",
            labels={"Days_Count": "Number of Days"}
        )
        fig_tier.update_layout(template="plotly_white", height=420, showlegend=False)
        st.plotly_chart(fig_tier, width="stretch")

# ================= TAB 6: FILTERED DATA & EXPORT =================
with tabs[tab_idx]:
    tab_idx += 1
    st.subheader("📋 Filtered Dataset with Derived Metrics")
    
    # Format dates nicely for display
    display_df = df.copy()
    display_df[selected_date_col] = display_df["Parsed_Date"].dt.strftime("%Y-%m-%d")
    # Drop internal helper columns from raw view
    clean_display = display_df.drop(columns=["Parsed_Date", "Clean_Metric"], errors="ignore")

    st.dataframe(
        clean_display,
        width="stretch"
    )
    
    # CSV Export Button
    csv_data = clean_display.to_csv(index=False).encode("utf-8")
    st.download_button(
        label="⬇️ Download Filtered Data as CSV",
        data=csv_data,
        file_name="retail_analytics_filtered.csv",
        mime="text/csv"
    )
