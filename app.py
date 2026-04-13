import streamlit as st
import pandas as pd

st.set_page_config(page_title="IHIP Defaulter Tool", layout="wide")
st.title("Daily IHIP Defaulter Analysis")

st.subheader("Upload IHIP Forms")

col1, col2, col3 = st.columns(3)

col1.markdown("### S-Form")
s_file = col1.file_uploader(" ", type=["xlsx"], key="s")

col2.markdown("### P-Form")
p_file = col2.file_uploader(" ", type=["xlsx"], key="p")

col3.markdown("### L-Form")
l_file = col3.file_uploader(" ", type=["xlsx"], key="l")

st.markdown("---")

def process_file(file, form_name):
    raw = pd.read_excel(file, header=None)

    header_row = 0
    for i, row in raw.iterrows():
        row_str = [str(cell).strip().lower() for cell in row]
        if any("facility name" in cell for cell in row_str):
            header_row = i
            break

    df = pd.read_excel(file, skiprows=header_row)
    df.columns = [str(c).replace('\n', ' ').strip() for c in df.columns]

    def find_col(keyword):
        return next((c for c in df.columns if keyword.lower() in c.lower()), None)

    name_col = find_col('facility name')
    subtype_col = find_col('facility sub-type')
    report_col = find_col('number of times reported')
    ward_col = next((c for c in df.columns if any(w in c.lower() for w in ['ward', 'zone'])), None)

    if not (name_col and subtype_col and report_col):
        return pd.DataFrame(), pd.DataFrame()

    df[report_col] = pd.to_numeric(df[report_col], errors='coerce')

    # Total count (ward-wise)
    total = df.groupby(ward_col)[name_col].count().reset_index()
    total.columns = ["WARD", "Total"]

    # Defaulters
    defaulters = df[df[report_col].fillna(0).astype(float) == 0.0].copy()

    non_reporting = defaulters.groupby(ward_col)[name_col].count().reset_index()
    non_reporting.columns = ["WARD", "Non-Reporting"]

    # Merge
    summary = pd.merge(total, non_reporting, on="WARD", how="left").fillna(0)
    summary["Non-Reporting"] = summary["Non-Reporting"].astype(int)
    summary["Reporting"] = summary["Total"] - summary["Non-Reporting"]

    # Category mapping
    category_map = {
        "Dispensary": "PUBLIC",
        "Government Medical College Hospital": "PUBLIC",
        "IGSL Satellite Laboratory": "PUBLIC",
        "Infectious Disease Hospital": "PUBLIC",
        "Municipal Hospital": "PUBLIC",
        "Other Government Hospitals": "PUBLIC",
        "Urban Primary Health Centre": "PUBLIC",
        "Health Post": "PUBLIC",
        "Health Sub Centre": "PUBLIC",
        "Private Hospital": "PRIVATE",
        "Private Laboratory": "PRIVATE"
    }

    defaulters['Category'] = defaulters[subtype_col].map(category_map).fillna("OTHER")

    result = pd.DataFrame()
    result["WARD"] = defaulters[ward_col]
    result["Facility Name"] = defaulters[name_col]
    result["Form Type"] = form_name
    result["Category"] = defaulters["Category"]
    result["REMARK"] = ""

    return result, summary


dfs = []
summaries = {}

if s_file:
    df_s, sum_s = process_file(s_file, "S FORM")
    dfs.append(df_s)
    summaries["S FORM"] = sum_s

if p_file:
    df_p, sum_p = process_file(p_file, "P FORM")
    dfs.append(df_p)
    summaries["P FORM"] = sum_p

if l_file:
    df_l, sum_l = process_file(l_file, "L FORM")
    dfs.append(df_l)
    summaries["L FORM"] = sum_l

# 🔥 Show Ward-wise Summary
if summaries:
    st.subheader("Ward-wise Reporting Summary")

    for form, summary_df in summaries.items():
        st.markdown(f"### {form}")
        st.dataframe(summary_df, use_container_width=True, hide_index=True)

# 🔥 Combined Defaulter List
if dfs:
    final_df = pd.concat(dfs, ignore_index=True)
    final_df = final_df.sort_values(["WARD", "Facility Name"])

    st.subheader("Defaulter Facilities Combined List")
    st.dataframe(final_df, use_container_width=True, hide_index=True)

    csv = final_df.to_csv(index=False).encode('utf-8')
    st.download_button("Download CSV", csv, "combined_defaulters.csv", "text/csv")

else:
    st.info("Upload at least one file to see results.")
