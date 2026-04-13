import streamlit as st
import pandas as pd
from io import BytesIO

# =========================================================
# APP CONFIG
# =========================================================

st.set_page_config(page_title="IHIP Tool", layout="wide")
st.title("Daily IHIP Defaulter Analysis")

# =========================================================
# SAFE EXCEL READER (NO OPENPYXL CRASH)
# =========================================================

def safe_read_excel(file):
    try:
        return pd.read_excel(file, engine="openpyxl")
    except:
        return pd.read_excel(file)

# =========================================================
# FILE UPLOADS
# =========================================================

col1, col2, col3 = st.columns(3)

s_file = col1.file_uploader("S Form", type=["xlsx"])
p_file = col2.file_uploader("P Form", type=["xlsx"])
l_file = col3.file_uploader("L Form", type=["xlsx"])

st.markdown("---")

# =========================================================
# OUTPUT 1 + OUTPUT 2 (SIMPLIFIED + SAFE)
# =========================================================

def process_basic(file, form):

    df = safe_read_excel(file)
    df.columns = [str(c).strip() for c in df.columns]

    ward_col = next((c for c in df.columns if "ward" in c.lower()), None)
    facility_col = next((c for c in df.columns if "facility" in c.lower()), None)

    out = pd.DataFrame()

    if ward_col:
        out["WARD"] = df[ward_col]
    else:
        out["WARD"] = "Not Mentioned"

    if facility_col:
        out["Facility Name"] = df[facility_col]
    else:
        out["Facility Name"] = ""

    out["Form Type"] = form
    out["REMARK"] = ""

    return out

# =========================================================
# MAIN DATA BUILD
# =========================================================

dfs = []

if s_file:
    dfs.append(process_basic(s_file, "S"))
if p_file:
    dfs.append(process_basic(p_file, "P"))
if l_file:
    dfs.append(process_basic(l_file, "L"))

if dfs:

    final_df = pd.concat(dfs, ignore_index=True)

    # ================= OUTPUT 1 =================
    out1 = final_df.copy()
    out1.insert(0, "Sr No", range(1, len(out1) + 1))

    st.subheader("Output 1")
    st.dataframe(out1, use_container_width=True)

    # ================= OUTPUT 2 =================
    out2 = final_df.copy()
    out2.insert(0, "Sr No", range(1, len(out2) + 1))
    out2["Contact"] = ""
    out2["Mobile"] = ""
    out2["Assigned Staff"] = ""

    st.subheader("Output 2")
    st.dataframe(out2, use_container_width=True)

# =========================================================
# OUTPUT 3 (WARD COMPARISON - FINAL STABLE)
# =========================================================

st.markdown("---")
st.subheader("Output 3 - Ward Wise Comparison")

def process_o3(file, prefix):

    df = safe_read_excel(file)
    df.columns = [str(c).strip() for c in df.columns]

    ward_col = "A D M I N I S T R A T I V E W A R D"
    total_col = next((c for c in df.columns if "total reporting" in c.lower()), None)
    percent_col = next((c for c in df.columns if "% of average" in c.lower()), None)

    out = pd.DataFrame()

    out[f"{prefix}_Ward"] = df[ward_col] if ward_col in df.columns else ""
    out[f"{prefix}_Total"] = df[total_col] if total_col else ""
    out[f"{prefix}_%"] = df[percent_col] if percent_col else ""

    return out

if s_file and p_file and l_file:

    s_df = process_o3(s_file, "S")
    p_df = process_o3(p_file, "P")
    l_df = process_o3(l_file, "L")

    max_len = max(len(s_df), len(p_df), len(l_df))

    s_df = s_df.reindex(range(max_len)).fillna("")
    p_df = p_df.reindex(range(max_len)).fillna("")
    l_df = l_df.reindex(range(max_len)).fillna("")

    blank1 = pd.DataFrame([""] * max_len, columns=[" "])
    blank2 = pd.DataFrame([""] * max_len, columns=["  "])

    output3 = pd.concat([s_df, blank1, p_df, blank2, l_df], axis=1)

    output3.insert(0, "Sr No", range(1, len(output3) + 1))

    st.subheader("Output 3")
    st.dataframe(output3, use_container_width=True)

    # ================= DOWNLOAD =================

    def to_excel(df):
        output = BytesIO()
        with pd.ExcelWriter(output, engine="openpyxl") as writer:
            df.to_excel(writer, index=False)
        return output.getvalue()

    st.download_button(
        "Download Output 3",
        to_excel(output3),
        "output3.xlsx"
    )

else:
    st.info("Upload S, P, L files for Output 3")
