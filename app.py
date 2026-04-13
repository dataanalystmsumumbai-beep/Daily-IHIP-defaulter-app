import streamlit as st
import pandas as pd
from io import BytesIO

# =========================================================
# PAGE SETUP
# =========================================================

st.set_page_config(page_title="IHIP Defaulter Tool", layout="wide")
st.title("Daily IHIP Defaulter Analysis")

# =========================================================
# SAFE EXCEL READER
# =========================================================

def safe_read_excel(file):
    try:
        return pd.read_excel(file, engine="openpyxl")
    except Exception:
        try:
            return pd.read_excel(file, engine="xlrd")
        except Exception:
            return pd.read_excel(file, engine="python")

# =========================================================
# INPUTS OUTPUT 1 & 2
# =========================================================

col1, col2, col3 = st.columns(3)

s_file = col1.file_uploader("S-Form (Output 1/2)", type=["xlsx"])
p_file = col2.file_uploader("P-Form (Output 1/2)", type=["xlsx"])
l_file = col3.file_uploader("L-Form (Output 1/2)", type=["xlsx"])

st.markdown("---")

contact_file = st.file_uploader("Upload Contact File", type=["xlsx"])
staff_input = st.text_input("Enter Staff Names (comma separated)")

report_date = st.text_input("Enter Date (DD-MM-YYYY)", "13-04-2026")
report_datetime = st.text_input("Enter Full Date-Time", "")

st.markdown("---")

# =========================================================
# OUTPUT 3 INPUTS
# =========================================================

st.subheader("Output 3 Inputs")

col4, col5, col6 = st.columns(3)

s_file_3 = col4.file_uploader("S-Form (Output 3)", type=["xlsx"])
p_file_3 = col5.file_uploader("P-Form (Output 3)", type=["xlsx"])
l_file_3 = col6.file_uploader("L-Form (Output 3)", type=["xlsx"])

output3_date = st.text_input("Output 3 Date", "13-04-2026")

st.markdown("---")

# =========================================================
# PROCESS FUNCTION (OUTPUT 1/2)
# =========================================================

def process_file(file, form):

    raw = safe_read_excel(file)

    header_row = 0
    for i, row in raw.iterrows():
        if "facility name" in str(row).lower():
            header_row = i
            break

    df = safe_read_excel(file)
    df.columns = [str(c).strip() for c in df.columns]

    def find_col(k):
        return next((c for c in df.columns if k in c.lower()), None)

    name = find_col("facility name")
    subtype = find_col("facility sub-type")
    report = find_col("number of times reported")
    ward = next((c for c in df.columns if "ward" in c.lower() or "zone" in c.lower()), None)

    if not (name and subtype and report):
        return pd.DataFrame()

    df[report] = pd.to_numeric(df[report], errors="coerce")
    df = df[df[report].fillna(0) == 0].copy()

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

    df["Category"] = df[subtype].map(category_map).fillna("OTHER")

    if ward:
        df["WARD"] = df[ward]
    else:
        df["WARD"] = "Not Mentioned"

    out = pd.DataFrame()
    out["WARD"] = df["WARD"]
    out["Facility Name"] = df[name]
    out["Form Type"] = form
    out["Category"] = df["Category"]
    out["REMARK"] = ""

    return out

# =========================================================
# OUTPUT 1 + 2
# =========================================================

dfs = []

if s_file:
    dfs.append(process_file(s_file, "S FORM"))
if p_file:
    dfs.append(process_file(p_file, "P FORM"))
if l_file:
    dfs.append(process_file(l_file, "L FORM"))

if dfs:

    final_df = pd.concat(dfs, ignore_index=True)

    # SAFE WARD FIX
    if "WARD" not in final_df.columns:
        final_df["WARD"] = "Not Mentioned"

    final_df["WARD"] = final_df["WARD"].astype(str)

    final_df["ward_sort"] = final_df["WARD"].apply(
        lambda x: "ZZZ" if x.strip().lower() == "not mentioned" else x
    )

    final_df = final_df.sort_values(["ward_sort", "Facility Name"]).drop(columns=["ward_sort"])

    out1 = final_df.copy()
    out1.insert(0, "Sr No", range(1, len(out1) + 1))

    st.subheader("Output 1")
    st.dataframe(out1, use_container_width=True)

    # OUTPUT 2
    merged = final_df.copy()
    merged["key"] = merged["Facility Name"].astype(str).str.strip().str.lower()

    merged["Contact Person Name"] = ""
    merged["Mobile Number"] = ""
    merged["Assigned Staff"] = ""

    merged["REMARK"] = ""

    out2 = merged.copy()
    out2.insert(0, "Sr No", range(1, len(out2) + 1))

    st.subheader("Output 2")
    st.dataframe(out2, use_container_width=True)

# =========================================================
# OUTPUT 3
# =========================================================

st.subheader("Output 3")

def process_simple(file, prefix):
    df = safe_read_excel(file)
    df.columns = [str(c).strip() for c in df.columns]

    ward_col = next((c for c in df.columns if "ward" in c.lower()), None)

    if not ward_col:
        return pd.DataFrame()

    temp = df[[ward_col]].copy()
    temp.columns = [f"{prefix}_Ward"]

    temp[f"{prefix}_Ward"] = temp[f"{prefix}_Ward"].fillna("Not Mentioned")

    return temp.reset_index(drop=True)

if s_file_3 and p_file_3 and l_file_3:

    s_df = process_simple(s_file_3, "S")
    p_df = process_simple(p_file_3, "P")
    l_df = process_simple(l_file_3, "L")

    max_len = max(len(s_df), len(p_df), len(l_df))

    s_df = s_df.reindex(range(max_len)).fillna("")
    p_df = p_df.reindex(range(max_len)).fillna("")
    l_df = l_df.reindex(range(max_len)).fillna("")

    blank1 = pd.DataFrame([""] * max_len, columns=["BLANK_1"])
    blank2 = pd.DataFrame([""] * max_len, columns=["BLANK_2"])

    output3 = pd.concat([s_df, blank1, p_df, blank2, l_df], axis=1)

    output3 = output3.loc[:, ~output3.columns.duplicated()]

    output3.insert(0, "Sr No", range(1, len(output3) + 1))

    st.dataframe(output3, use_container_width=True)

else:
    st.info("Upload Output 3 files")
