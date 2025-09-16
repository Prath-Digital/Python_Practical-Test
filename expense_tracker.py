# expense_tracker.py
import os
from datetime import datetime

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import streamlit as st

# -------------------------
# ExpenseTracker Class
# -------------------------
class ExpenseTracker:
    def __init__(self, csv_path="expenses.csv"):
        self.csv_path = csv_path
        self.columns = ["Date", "Amount", "Category", "Description"]
        self.df = self._load_or_create()

    def _load_or_create(self):
        if os.path.exists(self.csv_path):
            df = pd.read_csv(self.csv_path)
            df["Date"] = pd.to_datetime(df["Date"], errors="coerce")
            df["Amount"] = pd.to_numeric(df["Amount"], errors="coerce")
            df = df.dropna(subset=["Date", "Amount"])
            return df[self.columns]
        else:
            return pd.DataFrame(columns=self.columns)


    def save(self):
        df = self.df.copy()
        df["Date"] = pd.to_datetime(df["Date"]).dt.strftime("%Y-%m-%d")
        df.to_csv(self.csv_path, index=False)

    def add_expense(self, date, amount, category, description=""):
        if amount is None:
            raise ValueError("Amount required")
        try:
            amount = float(amount)
        except:
            raise ValueError("Amount must be numeric")
        if amount <= 0:
            raise ValueError("Amount must be positive")
        date = pd.to_datetime(date).date()
        new_row = {
            "Date": pd.to_datetime(date),
            "Amount": amount,
            "Category": str(category).strip(),
            "Description": str(description).strip(),
        }
        self.df = pd.concat([self.df, pd.DataFrame([new_row])], ignore_index=True)
        self.save()

    def get_summary(self):
        if self.df.empty:
            return {
                "total": 0.0,
                "average": 0.0,
                "median": 0.0,
                "count": 0,
                "by_category": pd.DataFrame(columns=["Category", "Total", "Average", "Count"]),
            }
        total = float(self.df["Amount"].sum())
        average = float(self.df["Amount"].mean())
        median = float(np.median(self.df["Amount"].values))
        count = int(self.df.shape[0])
        by_cat = (
            self.df.groupby("Category")["Amount"]
            .agg(Total="sum", Average="mean", Count="count")
            .reset_index()
            .sort_values("Total", ascending=False)
        )
        return {"total": total, "average": average, "median": median, "count": count, "by_category": by_cat}

    def filter_expenses(self, category=None, start_date=None, end_date=None, min_amount=None, max_amount=None):
        df = self.df.copy()
        if category and category != "All":
            df = df[df["Category"] == category]
        if start_date:
            df = df[df["Date"] >= pd.to_datetime(start_date)]
        if end_date:
            df = df[df["Date"] <= pd.to_datetime(end_date)]
        if min_amount is not None:
            df = df[df["Amount"] >= float(min_amount)]
        if max_amount is not None:
            df = df[df["Amount"] <= float(max_amount)]
        return df.sort_values("Date")

    def generate_report(self, save_path="expense_report_summary.csv"):
        summary = self.get_summary()
        by_cat = summary["by_category"]
        by_cat.to_csv(save_path, index=False)
        return by_cat

# -------------------------
# Streamlit UI
# -------------------------
st.set_page_config(page_title="Smart Expense Tracker", layout="wide")

st.title("💸 Smart Expense Tracker")
st.markdown("Log expenses, analyze spending patterns, filter transactions, and visualize trends.")

tracker = ExpenseTracker(csv_path="expenses.csv")

# Sidebar: Add + Filters
with st.sidebar:
    st.header("Add / Filter")
    st.subheader("Add a new expense")
    with st.form("add_expense_form", clear_on_submit=True):
        date = st.date_input("Date", value=datetime.today())
        amount = st.number_input("Amount (₹)", min_value=0.0, format="%.2f")
        existing_cats = sorted(list(set(tracker.df["Category"].dropna().unique()))) if not tracker.df.empty else []
        default_cats = ["Food", "Transport", "Utilities", "Shopping", "Entertainment", "Other"]
        categories = list(dict.fromkeys(existing_cats + default_cats))
        category = st.selectbox("Category", options=["All"] + categories, index=categories.index("Food") + 1 if "Food" in categories else 0)
        description = st.text_input("Description (optional)")
        add_btn = st.form_submit_button("Add Expense")
        if add_btn:
            try:
                if category == "All":
                    category = "Other"
                tracker.add_expense(date=date, amount=amount, category=category, description=description)
                st.success("Expense added.")
            except Exception as e:
                st.error(f"Error: {e}")

    st.markdown("---")
    st.subheader("Filters")
    f_category = st.selectbox("Filter by Category", options=["All"] + categories)
    f_start = st.date_input("Start Date", value=None, key="start_date")
    f_end = st.date_input("End Date", value=None, key="end_date")
    f_min = st.number_input("Min Amount", value=0.0, format="%.2f", key="min_amount")
    f_max = st.number_input("Max Amount", value=0.0, format="%.2f", key="max_amount")
    if f_max == 0.0:
        f_max = None
    if st.button("Apply Filters"):
        st.rerun()

    st.markdown("---")
    if st.button("Download CSV of current data"):
        csv_buf = tracker.df.copy()
        csv_buf["Date"] = pd.to_datetime(csv_buf["Date"]).dt.strftime("%Y-%m-%d")
        towrite = csv_buf.to_csv(index=False).encode()
        st.download_button("Download expenses.csv", data=towrite, file_name="expenses.csv", mime="text/csv")

# Apply filters
start_date = f_start if f_start else None
end_date = f_end if f_end else None
min_amount = f_min if f_min > 0 else None
max_amount = f_max if f_max else None
filtered_df = tracker.filter_expenses(category=f_category, start_date=start_date, end_date=end_date, min_amount=min_amount, max_amount=max_amount)

# Metrics
summary = tracker.get_summary()
col1, col2, col3, col4 = st.columns(4)
col1.metric("Total Spent", f"₹ {summary['total']:.2f}")
col2.metric("Average Expense", f"₹ {summary['average']:.2f}")
col3.metric("Median Expense", f"₹ {summary['median']:.2f}")
col4.metric("Transactions", f"{summary['count']}")

# Table
st.subheader("Filtered Transactions")
st.dataframe(filtered_df.sort_values("Date", ascending=False).reset_index(drop=True))
csv_bytes = filtered_df.copy()
csv_bytes["Date"] = pd.to_datetime(csv_bytes["Date"]).dt.strftime("%Y-%m-%d")
st.download_button("Download Filtered CSV", data=csv_bytes.to_csv(index=False), file_name="filtered_expenses.csv")

# Visualizations
st.subheader("Visualizations")
# Bar chart
if not summary["by_category"].empty:
    fig1, ax1 = plt.subplots(figsize=(8, 4))
    sns.barplot(data=summary["by_category"], x="Category", y="Total", ax=ax1)
    ax1.set_title("Total spend by category")
    plt.xticks(rotation=45)
    st.pyplot(fig1)
# Line chart
if not tracker.df.empty:
    df_time = tracker.df.copy()
    df_time["YearMonth"] = df_time["Date"].dt.to_period("M").dt.to_timestamp()
    monthly = df_time.groupby("YearMonth")["Amount"].sum().reset_index()
    fig2, ax2 = plt.subplots(figsize=(10, 4))
    ax2.plot(monthly["YearMonth"], monthly["Amount"], marker="o")
    ax2.set_title("Monthly spending")
    plt.xticks(rotation=45)
    st.pyplot(fig2)
# Pie chart
if not summary["by_category"].empty:
    pie_data = summary["by_category"]
    fig3, ax3 = plt.subplots(figsize=(6, 6))
    ax3.pie(pie_data["Total"], labels=pie_data["Category"], autopct="%1.1f%%", startangle=140)
    ax3.set_title("Spending distribution by category")
    st.pyplot(fig3)
# Histogram
if not tracker.df.empty:
    fig4, ax4 = plt.subplots(figsize=(8, 4))
    ax4.hist(tracker.df["Amount"], bins=20)
    ax4.set_title("Distribution of expense amounts")
    st.pyplot(fig4)

st.markdown("---")
st.subheader("Category-wise Summary")
st.table(summary["by_category"].head(20))

# Actions
colA, colB = st.columns(2)
with colA:
    if st.button("Generate summary CSV report"):
        savepath = "expense_report_summary.csv"
        report = tracker.generate_report(save_path=savepath)
        st.success(f"Report saved to {savepath}.")
        st.download_button("Download Report CSV", data=report.to_csv(index=False), file_name=savepath)
with colB:
    if st.button("Reset all data (Deletes expenses.csv)"):
        if os.path.exists(tracker.csv_path):
            os.remove(tracker.csv_path)
        tracker.df = tracker._load_or_create()
        st.success("All data cleared.")
        st.rerun()
