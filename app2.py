import streamlit as st
import pandas as pd
import plotly.express as px
from difflib import SequenceMatcher
from io import BytesIO

# --- Helper functions ---
def normalize_text(s):
    if pd.isna(s):
        return ''
    s = str(s).lower().strip()
    for ch in ['.', ',', '&', 'ltd', 'pvt', 'online', 'india']:
        s = s.replace(ch, ' ')
    s = ' '.join(s.split())
    return s

def similarity(a, b):
    return SequenceMatcher(None, a, b).ratio()

def reconcile(internal_df, bank_df, date_tol_days=2, amount_tol=50, sim_threshold=0.75):
    bank_idx_used = set()
    matches, unmatched_internal = [], []

    # Amount buckets
    bank_by_amount = {}
    for i, b in bank_df.iterrows():
        key = int(round(b['Amount'] / 10))
        bank_by_amount.setdefault(key, []).append((i, b))

    for i, row in internal_df.iterrows():
        int_date = row['Date']
        int_amt = float(row['Amount'])
        key = int(round(int_amt / 10))
        candidate_keys = [key-1, key, key+1]
        best_score, best_match = 0, None

        for k in candidate_keys:
            for j, b in bank_by_amount.get(k, []):
                if j in bank_idx_used:
                    continue
                if abs((int_date - b['Date']).days) <= date_tol_days:
                    sim = similarity(row['Vendor_clean'], b['Vendor_clean'])
                    amt_diff = abs(int_amt - float(b['Amount']))
                    score = sim - (amt_diff / (int_amt + 1)) * 0.25
                    if score > best_score and sim >= sim_threshold:
                        best_score = score
                        best_match = (i, j, b, sim, amt_diff)

        if best_match:
            i_idx, j_idx, b_row, sim, amt_diff = best_match
            bank_idx_used.add(j_idx)
            matches.append({
                'Transaction_ID': internal_df.at[i_idx, 'Transaction_ID'],
                'Internal_Date': internal_df.at[i_idx, 'Date'],
                'Internal_Amount': internal_df.at[i_idx, 'Amount'],
                'Vendor_internal': internal_df.at[i_idx, 'Vendor'],
                'Bank_Ref': b_row['Bank_Ref'],
                'Bank_Date': b_row['Date'],
                'Bank_Amount': b_row['Amount'],
                'Vendor_bank': b_row['Vendor_Name'],
                'Vendor_similarity': sim,
                'Amount_diff': amt_diff,
                'MatchType': 'Fuzzy'
            })
        else:
            unmatched_internal.append(i)

    unmatched_bank = [i for i in bank_df.index if i not in bank_idx_used]

    return (
        pd.DataFrame(matches),
        internal_df.loc[unmatched_internal],
        bank_df.loc[unmatched_bank]
    )

# --- Streamlit UI ---
st.set_page_config(page_title="Bank Reconciliation Dashboard", layout="wide")

st.title("📊 Bank Reconciliation Dashboard")

internal_file = st.file_uploader("Upload Internal CSV", type="csv")
bank_file = st.file_uploader("Upload Bank CSV", type="csv")

if internal_file and bank_file:
    internal = pd.read_csv(internal_file)
    bank = pd.read_csv(bank_file)

    # Cleaning
    internal['Date'] = pd.to_datetime(internal['Date'], dayfirst=True, errors='coerce') #chnage1
    bank['Date'] = pd.to_datetime(bank['Date'], dayfirst=True, errors='coerce')
    internal['Vendor_clean'] = internal['Vendor'].apply(normalize_text)
    bank['Vendor_clean'] = bank['Vendor_Name'].apply(normalize_text)
    internal['Amount'] = pd.to_numeric(internal['Amount'], errors='coerce').fillna(0).astype(float)
    bank['Amount'] = pd.to_numeric(bank['Amount'], errors='coerce').fillna(0).astype(float)
    internal['Transaction_ID'] = internal['Transaction_ID'].astype(str)
    bank['Bank_Ref'] = bank['Bank_Ref'].astype(str)

    # Params
    st.sidebar.header("⚙️ Matching Parameters")
    date_tol = st.sidebar.slider("Date tolerance (days)", 0, 10, 2)
    amount_tol = st.sidebar.slider("Amount tolerance", 0, 500, 50)
    sim_threshold = st.sidebar.slider("Vendor similarity threshold", 0.0, 1.0, 0.75)

    if st.button("🚀 Run Reconciliation"):
        matches_df, unmatched_internal, unmatched_bank = reconcile(internal, bank, date_tol, amount_tol, sim_threshold)

        # Tabs
        tab1, tab2, tab3, tab4 = st.tabs(["📊 Dashboard", "✅ Matches", "⚠️ Unmatched Internal", "⚠️ Unmatched Bank"])

        with tab1:
            st.subheader("📌 Summary Metrics")
            col1, col2, col3, col4 = st.columns(4)
            col1.metric("Internal Txns", len(internal))
            col2.metric("Bank Txns", len(bank))
            col3.metric("Matches", len(matches_df))
            match_percent = round((len(matches_df) / len(internal)) * 100, 2)
            col4.metric("Match %", f"{match_percent}%")

            # Pie chart Match vs Unmatched
            status_counts = {
                "Matches": len(matches_df),
                "Unmatched Internal": len(unmatched_internal),
                "Unmatched Bank": len(unmatched_bank)
            }
            pie = px.pie(
                names=list(status_counts.keys()),
                values=list(status_counts.values()),
                title="Match vs Unmatched Overview"
            )
            st.plotly_chart(pie, use_container_width=True)

            # Vendor mismatches
            if not unmatched_internal.empty:
                top_vendors = unmatched_internal['Vendor'].value_counts().head(10).reset_index()
                top_vendors.columns = ['Vendor', 'Unmatched_Count']
                bar = px.bar(top_vendors, x='Vendor', y='Unmatched_Count', title="Top Unmatched Vendors")
                st.plotly_chart(bar, use_container_width=True)

            # Trend chart
            internal_trend = internal.groupby('Date')['Amount'].sum().reset_index()
            bank_trend = bank.groupby('Date')['Amount'].sum().reset_index()
            internal_trend['Source'] = "Internal"
            bank_trend['Source'] = "Bank"
            trend = pd.concat([internal_trend, bank_trend])
            line = px.line(trend, x='Date', y='Amount', color='Source', title="Transaction Trends Over Time")
            st.plotly_chart(line, use_container_width=True)

        with tab2:
            st.subheader("✅ Matches Found")
            st.dataframe(matches_df)

            if not matches_df.empty:
              st.subheader("🔍 Detailed Comparison of a Selected Match")
            # Select a match
            match_ids = matches_df['Transaction_ID'].tolist()
            selected_id = st.selectbox("Select Transaction ID", match_ids)

            selected_match = matches_df[matches_df['Transaction_ID'] == selected_id].iloc[0]

            col1, col2 = st.columns(2)

            with col1:
                st.markdown("**Internal Transaction**")
                st.write({
                    "Transaction_ID": selected_match['Transaction_ID'],
                    "Date": selected_match['Internal_Date'],
                    "Amount": selected_match['Internal_Amount'],
                    "Vendor": selected_match['Vendor_internal']
                })

        with col2:
            st.markdown("**Bank Transaction**")
            st.write({
                "Bank_Ref": selected_match['Bank_Ref'],
                "Date": selected_match['Bank_Date'],
                "Amount": selected_match['Bank_Amount'],
                "Vendor": selected_match['Vendor_bank'],
                "Vendor Similarity": round(selected_match['Vendor_similarity'], 2),
                "Amount Difference": round(selected_match['Amount_diff'], 2)
            })

        with tab3:
            st.subheader("⚠️ Unmatched Internal Transactions")
            st.dataframe(unmatched_internal)

        with tab4:
            st.subheader("⚠️ Unmatched Bank Transactions")
            st.dataframe(unmatched_bank)
