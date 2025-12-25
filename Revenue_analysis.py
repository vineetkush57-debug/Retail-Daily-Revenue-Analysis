""""
" Retail Store Daily Revenue Analysis 
● From: Minor 1 – Pandas 
● Extension: Analyze daily revenue → peak sales days. 
● Add-ons: Line plots, stats report. 
● Difficulty: Easy"
"""
import streamlit as st
import pandas as  pd
import matplotlib.pyplot as plt

df = pd.read_csv("Revenue_analysis.csv")

df["Date"] = pd.to_datetime(df["Date"], dayfirst=True)
df = df.sort_values("Date")

st.title("Revenue Analysis")

Average_revenue = df["Revenue"].mean()
maximum_revenue = df["Revenue"].max()
minimum_revenue = df["Revenue"].min()


print("---------- Date vise retail revenue anylsis -----------")
print(f"Average revenue : {Average_revenue}")
print(f"Maximum revenue : {maximum_revenue}")
print(f"Minimum revenue : {minimum_revenue}" )

peak_day = df.loc[df["Revenue"].idxmax(), "Date"]
print(f"Peak sales day is : {peak_day}")

st.subheader("📊 Revenue Summary")

col1, col2, col3, col4 = st.columns(4)

col1.metric("Average Revenue", f"₹{Average_revenue:.2f}")
col2.metric("Maximum Revenue", f"₹{maximum_revenue}")
col3.metric("Minimum Revenue", f"₹{minimum_revenue}")
col4.metric("Peak Day", peak_day.strftime("%d-%m-%Y"))


st.write(f"➡️ Average Revenue: {Average_revenue}")
st.write(f"💵Maximum Revenue: {maximum_revenue}")
st.write(f"😊Minimum Revenue: {minimum_revenue}")
st.write(f"🎗️Peak Sales Day: {peak_day}")


if st.button("📈show line chart"):
    st.subheader("Daily Revenue - Line Chart")
    st.line_chart(df.set_index("Date")["Revenue"])
    st.success("Your line chart has been created ✅")

if st.button("🚀Show full table :"):
    st.dataframe(df)
    st.success("You full table is here ⬆️")






















