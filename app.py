import streamlit as st
import pandas as pd
from io import BytesIO

# =========================================================
# PAGE
# =========================================================

st.set_page_config(page_title="IHIP Tool", layout="wide")
st.title("Daily IHIP Defaulter Analysis")

# =========================================================
# SAFE EXCEL READER (FIXED)
# =========================================================

def safe_read_excel(file):
    try:
        return pd.read_excel(file, engine="openpyxl")
    except Exception:
        try:
            return pd.read_excel(file, engine="xlrd")
        except Exception:
            return pd.read_excel(file)

# =========================================================
# OUTPUT 1/2 INPUTS
# =========================================================

col1, col2, col3 = st.columns(3)

s_file = col1.file_uploader("S Form (O1/O2)", type=["xlsx"])
p_file = col2.file_uploader("P Form (O1/O2)", type=["xlsx"])
l_file = col3.file_uploader("L Form (O1/O2)", type=["xlsx"])

st.markdown("---")

contact_file = st.file_uploader("Contact File", type=["xlsx"])
staff_input = st.text_input("Staff Names")

report_date = st.text_input("Report Date", "13-04-2026")
report_datetime = st.text_input("Report DateTime", "")

# =========================================================
# OUTPUT 3 INPUTS (SEPARATE)
# =========================================================

st.subheader("Output 3 - Upload Files")

col4, col5, col6 = st.columns(3)

s_file_3 = col4.file_uploader("S Form (O3)", type=["xlsx"])
p_file_3 = col5.file_uploader("P Form (O3)", type=["xlsx"])
l_file_3 = col6.file_uploader("L Form (O3)", type=["xlsx"])

output3_date = st.text_input("Output 3 Date", "13-04-2026")

st.markdown("---")

# =========================================================
# PROCESS O1/O2
# =========================================================

def process_file(file, form):

    df = safe_read_excel(file)
    df.columns = [str(c).strip() for c in df.columns]

    def find_col(k):
        return next((c for c in df.columns if k in c.lower()), None)

    name = find_col("facility name")
    subtype = find_col("facility sub-type")
    report = find_col("number of times reported")
    ward = find_col("ward") or find_col("zone")

    if not name:
        return pd.DataFrame()

    df["WARD"] = df[ward] if ward else "Not Mentioned"

    df["Category"] = "OTHER"
    if subtype:
        df["Category"] = df[subtype]

    out = pd.DataFrame()
    out["WARD"] = df["WARD"]
    out["Facility Name"] = df[name]
    out["Form Type"] = form
    out["Category"] = df["Category"]
    out["REMARK"] = ""

    return out

# =========================================================
# OUTPUT 1 & 2
# =========================================================

dfs = []

if s_file:
    dfs.append(process_file(s_file, "S"))
if p_file:
    dfs.append(process_file(p_file, "P"))
if l_file:
    dfs.append(process_file(l_file, "L"))

if dfs:

    final_df = pd.concat(dfs, ignore_index=True)

    if "WARD" not in final_df.columns:
        final_df["WARD"] = "Not Mentioned"

    final_df["WARD"] = final_df["WARD"].astype(str)

    out1 = final_df.copy()
    out1.insert(0, "Sr No", range(1, len(out1) + 1))

    st.subheader("Output 1")
    st.dataframe(out1, use_container_width=True)

    # OUTPUT 2 (simple stable)
    out2 = final_df.copy()
    out2.insert(0, "Sr No", range(1, len(out2) + 1))
    out2["Contact"] = ""
    out2["Mobile"] = ""
    out2["Assigned Staff"] = ""
    out2["REMARK"] = ""

    st.subheader("Output 2")
    st.dataframe(out2, use_container_width=True)

# =========================================================
# OUTPUT 3 (FIXED + DOWNLOAD ADDED)
# =========================================================

st.subheader("Output 3 (Ward Comparison)")

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

    blank1 = pd.DataFrame([""] * max_len, columns=[" "])
    blank2 = pd.DataFrame([""] * max_len, columns=["  "])

    output3 = pd.concat([s_df, blank1, p_df, blank2, l_df], axis=1)

    output3.insert(0, "Sr No", range(1, len(output3) + 1))

    st.dataframe(output3, use_container_width=True)

    # ================= DOWNLOAD =================

    def excel_o3(df):
        output = BytesIO()
        with pd.ExcelWriter(output, engine="openpyxl") as writer:
            df.to_excel(writer, index=False, startrow=2)
            ws = writer.sheets["Sheet1"]
            ws["A1"] = "Ward Wise Comparison"
            ws["A2"] = output3_date
        return output.getvalue()

    st.download_button(
        "Download Output 3 Excel",
        excel_o3(output3),
        "output3.xlsx"
    )

else:
    st.info("Upload S, P, L files for Output 3")
