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

# Common function to process file
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
        return pd.DataFrame()

    df[report_col] = pd.to_numeric(df[report_col], errors='coerce')

    defaulters = df[df[report_col].fillna(0).astype(float) == 0.0].copy()

    category_map = {
        "Dispensary": "PUBLIC",
        "Government Medical College Hospital": "PUBLIC",
        "IGSL Satellite Laboratory": "PUBLIC",
        "Infectious Disease Hospital": "PUBLIC",
        "Municipal Hospital": "PUBLIC",
        "Other Government Hospitals": "PUBLIC",
        "Urban Primary Health Centre": "PUBLIC",
        "Private Hospital": "PRIVATE",
        "Private Laboratory": "PRIVATE"
    }

    defaulters['Category'] = defaulters[subtype_col].map(category_map).fillna("OTHER")

    # Standard output format
    result = pd.DataFrame()
    
    if ward_col:
        result["WARD"] = defaulters[ward_col]
    else:
        result["WARD"] = ""

    result["Facility Name"] = defaulters[name_col]
    result["Form Type"] = form_name
    result["Category"] = defaulters["Category"]
    result["REMARK"] = ""

    return result

# Process all files
dfs = []

if s_file:
    dfs.append(process_file(s_file, "S FORM"))

if p_file:
    dfs.append(process_file(p_file, "P FORM"))

if l_file:
    dfs.append(process_file(l_file, "L FORM"))

# Combine all
if dfs:
    final_df = pd.concat(dfs, ignore_index=True)

    # Sort for clean look
    final_df = final_df.sort_values(["WARD", "Facility Name"])

    st.subheader("Defaulter Facilities Combined List")
    st.dataframe(final_df, use_container_width=True, hide_index=True)

    csv = final_df.to_csv(index=False).encode('utf-8')
    st.download_button("Download CSV", csv, "combined_defaulters.csv", "text/csv")

else:
    st.info("Upload at least one file to see results.")
