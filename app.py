import streamlit as st
import pandas as pd
from io import BytesIO

# =====================================================
# APP SETUP
# =====================================================

st.set_page_config(page_title="IHIP Tool", layout="wide")
st.title("Daily IHIP Defaulter Analysis")

# =====================================================
# SAFE READER
# =====================================================

def safe_read_excel(file):
    try:
        return pd.read_excel(file, engine="openpyxl")
    except:
        return pd.read_excel(file)

# =====================================================
# ================= OUTPUT 1 & 2 ======================
# =====================================================

st.header("📊 Output 1 & 2 Input")

col1, col2, col3 = st.columns(3)

s1 = col1.file_uploader("S Form (O1/O2)", type=["xlsx"])
p1 = col2.file_uploader("P Form (O1/O2)", type=["xlsx"])
l1 = col3.file_uploader("L Form (O1/O2)", type=["xlsx"])

def process_basic(file, form):

    df = safe_read_excel(file)
    df.columns = [str(c).strip() for c in df.columns]

    ward = next((c for c in df.columns if "ward" in c.lower()), None)
    facility = next((c for c in df.columns if "facility" in c.lower()), None)

    out = pd.DataFrame()
    out["WARD"] = df[ward] if ward else "Not Mentioned"
    out["Facility Name"] = df[facility] if facility else ""
    out["Form Type"] = form

    return out

if s1 and p1 and l1:

    dfs = [
        process_basic(s1, "S"),
        process_basic(p1, "P"),
        process_basic(l1, "L")
    ]

    final = pd.concat(dfs, ignore_index=True)

    st.subheader("Output 1")
    st.dataframe(final)

    out2 = final.copy()
    out2["Contact"] = ""
    out2["Mobile"] = ""

    st.subheader("Output 2")
    st.dataframe(out2)

# =====================================================
# ================= OUTPUT 3 (SEPARATE INPUT) =========
# =====================================================

st.markdown("---")
st.header("📊 Output 3 Input (Reporting %)")

col4, col5, col6 = st.columns(3)

s2 = col4.file_uploader("S Form (O3)", type=["xlsx"])
p2 = col5.file_uploader("P Form (O3)", type=["xlsx"])
l2 = col6.file_uploader("L Form (O3)", type=["xlsx"])

def process_o3(file, prefix):

    df = safe_read_excel(file)
    df.columns = [str(c).strip() for c in df.columns]

    ward_col = "A D M I N I S T R A T I V E W A R D"
    total_col = next((c for c in df.columns if "total reporting" in c.lower()), None)
    percent_col = next((c for c in df.columns if "% of average" in c.lower()), None)
    never_col = next((c for c in df.columns if "never reported reporting units for selected period" in c.lower()), None)

    out = pd.DataFrame()

    out[f"{prefix}_Ward"] = df[ward_col] if ward_col in df.columns else ""
    out[f"{prefix}_Total"] = df[total_col] if total_col else ""
    out[f"{prefix}_%"] = df[percent_col] if percent_col else ""
    out[f"{prefix}_Never"] = df[never_col] if never_col else 0

    return out

if s2 and p2 and l2:

    s_df = process_o3(s2, "S")
    p_df = process_o3(p2, "P")
    l_df = process_o3(l2, "L")

    # SUM DISPLAY ONLY
    def safe_sum(x):
        return pd.to_numeric(x, errors="coerce").fillna(0).sum()

    colA, colB, colC = st.columns(3)

    colA.metric("S Non Reporting", int(safe_sum(s_df.iloc[:, -1])))
    colB.metric("P Non Reporting", int(safe_sum(p_df.iloc[:, -1])))
    colC.metric("L Non Reporting", int(safe_sum(l_df.iloc[:, -1])))

    max_len = max(len(s_df), len(p_df), len(l_df))

    s_df = s_df.reindex(range(max_len)).fillna("")
    p_df = p_df.reindex(range(max_len)).fillna("")
    l_df = l_df.reindex(range(max_len)).fillna("")

    blank1 = pd.DataFrame([""] * max_len, columns=[" "])
    blank2 = pd.DataFrame([""] * max_len, columns=["  "])

    output3 = pd.concat([s_df, blank1, p_df, blank2, l_df], axis=1)

    st.subheader("Output 3")
    st.dataframe(output3)

    # DOWNLOAD
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
