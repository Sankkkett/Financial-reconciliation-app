# 📊 Bank Reconciliation Dashboard

A smart and interactive **Streamlit-based Bank Reconciliation App** that automatically matches internal financial transactions with bank statement entries using fuzzy logic, vendor similarity scoring, date tolerance, and amount bucketing.

## 📊Dashboard 
![Financial-Reconciliation Dashboard]()

🔗 **Live App:** https://bank-reconciliation-app.streamlit.app/

---

## 🚀 Features

### ✅ Intelligent Reconciliation Engine
- Fuzzy vendor name matching using `SequenceMatcher`
- Date tolerance (user controlled)
- Amount tolerance with optimized bucket-based filtering
- Custom scoring model for accurate matching
- Generates:
  - ✔️ Matched transactions  
  - ✔️ Unmatched internal records  
  - ✔️ Unmatched bank records  

---

## 📊 Interactive Dashboard

The app includes:
- Summary metrics (Match %, total transactions)
- Match vs Unmatched breakdown (Pie Chart)
- Top unmatched vendors (Bar Chart)
- Daily transaction trends (Line Chart)
- Detailed “Match Comparison” view for selected transactions

---

## 📁 Input File Requirements

### Internal CSV Format
🔗 **Internal_expenses_large.csv** 

### Bank CSV Format
🔗 **Bank_statement_large.csv**  

The app automatically:
- Converts dates  
- Cleans vendor names  
- Standardizes text  
- Handles missing values  

---

## 🧠 Matching Logic Overview

### Vendor Normalization
- Lowercase text  
- Remove punctuation  
- Remove common keywords

- Trim extra spaces  

### Vendor Similarity
similarity = SequenceMatcher(None, a, b).ratio()

### Amount Bucketing
bucket = round(amount / 10)
- Used to reduce search space.

### Match Scoring
score = vendor_similarity - (amount_diff / (amount + 1)) * 0.25


### Final Match Selected When:
- Date difference ≤ tolerance  
- Vendor similarity ≥ threshold  
- Highest score wins  

---

## 🛠 Tech Stack

| Component | Technology |
|----------|------------|
| UI       | Streamlit |
| Data     | Pandas |
| Matching | difflib (SequenceMatcher) |
| Charts   | Plotly Express |
| Backend  | Python |





