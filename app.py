import streamlit as st
import pandas as pd
from io import BytesIO
import openpyxl

st.set_page_config(page_title="IHIP Defaulter Tool", layout="wide")
st.title("Daily IHIP Defaulter Analysis")

# =====================================================
# SAFE EXCEL READER (FIXED OPENPYXL ERROR)
# =====================================================
def safe_read_excel(file):
    try:
        return pd.read_excel(file, engine="openpyxl")
    except:
        try:
            wb = openpyxl.load_workbook(file, data_only=True)
            ws = wb.active

            data = list(ws.values)
            if not data:
                return pd.DataFrame()

            cols = data[0]
            rows = data[1:]

            return pd.DataFrame(rows, columns=cols)
        except:
            return pd.DataFrame()

# =====================================================
# OUTPUT 1 & 2 INPUT
# =====================================================
st.header("Output 1 & 2")

col1, col2, col3 = st.columns(3)

s_file = col1.file_uploader("S-Form (O1/O2)", type=["xlsx"])
p_file = col2.file_uploader("P-Form (O1/O2)", type=["xlsx"])
l_file = col3.file_uploader("L-Form (O1/O2)", type=["xlsx"])

contact_file = st.file_uploader("Upload Contact File", type=["xlsx"])
staff_input = st.text_input("Enter Staff Names (comma separated)")

report_date = st.text_input("Enter Date", "13-04-2026")
report_datetime = st.text_input("Enter Date-Time", "Monday 13-04-2026")

# =====================================================
# PROCESS FUNCTION (OUTPUT 1 & 2)
# =====================================================
def process_file(file, form):

    df = safe_read_excel(file)

    if df.empty:
        return pd.DataFrame()

    df.columns = [str(c).strip() for c in df.columns]

    def find_col(k):
        return next((c for c in df.columns if k in c.lower()), None)

    name = find_col("facility name")
    subtype = find_col("facility sub-type")
    report = find_col("number of times reported")
    ward = next((c for c in df.columns if "ward" in c.lower() or "zone" in c.lower()), None)

    if name is None:
        name = df.columns[0]
    if subtype is None:
        subtype = df.columns[1] if len(df.columns) > 1 else df.columns[0]
    if report is None:
        df["temp_report"] = 0
        report = "temp_report"
    if ward is None:
        df["WARD"] = "Not Mentioned"
        ward = "WARD"

    df[report] = pd.to_numeric(df[report], errors="coerce").fillna(0)
    df = df[df[report] == 0]

    df["Category"] = "OTHER"

    out = pd.DataFrame()
    out["WARD"] = df[ward].astype(str)
    out["Facility Name"] = df[name].astype(str)
    out["Form Type"] = form
    out["Category"] = df["Category"]
    out["REMARK"] = ""

    return out

# =====================================================
# MAIN OUTPUT 1 & 2
# =====================================================
dfs = []

if s_file:
    dfs.append(process_file(s_file, "S FORM"))
if p_file:
    dfs.append(process_file(p_file, "P FORM"))
if l_file:
    dfs.append(process_file(l_file, "L FORM"))

if dfs:

    final_df = pd.concat(dfs, ignore_index=True)

    # ---------------- OUTPUT 1 ----------------
    out1 = final_df.copy()
    out1.insert(0, "Sr No", range(1, len(out1) + 1))

    st.subheader("Output 1")
    st.dataframe(out1, use_container_width=True)

    # ---------------- OUTPUT 2 ----------------
    merged = final_df.copy()

    if contact_file:
        cdf = safe_read_excel(contact_file)

        if not cdf.empty:
            cdf.columns = [str(c).strip() for c in cdf.columns]

    # ---------------- STAFF ----------------
    if staff_input:
        staff = [s.strip() for s in staff_input.split(",") if s.strip()]
        if staff:
            merged["Assigned Staff"] = (staff * ((len(merged)//len(staff))+1))[:len(merged)]
        else:
            merged["Assigned Staff"] = ""
    else:
        merged["Assigned Staff"] = ""

    out2 = merged.copy()
    out2.insert(0, "Sr No", range(1, len(out2) + 1))

    st.subheader("Output 2")
    st.dataframe(out2, use_container_width=True)

else:
    st.info("Upload files for Output 1 & 2")

# =====================================================
# OUTPUT 3 INPUT
# =====================================================
st.markdown("---")
st.header("Output 3 - Ward Analysis")

colA, colB, colC = st.columns(3)

s3 = colA.file_uploader("S Form (O3)", type=["xlsx"])
p3 = colB.file_uploader("P Form (O3)", type=["xlsx"])
l3 = colC.file_uploader("L Form (O3)", type=["xlsx"])

def process_o3(file, prefix):

    df = safe_read_excel(file)

    if df.empty:
        return pd.DataFrame()

    df.columns = [str(c).strip() for c in df.columns]

    ward_col = next((c for c in df.columns if "ward" in c.lower()), None)
    total_col = next((c for c in df.columns if "total reporting" in c.lower()), None)
    percent_col = next((c for c in df.columns if "% of average" in c.lower()), None)
    never_col = next((c for c in df.columns if "never reported" in c.lower()), None)

    out = pd.DataFrame()
    out[f"{prefix}_Ward"] = df[ward_col] if ward_col else ""
    out[f"{prefix}_Total"] = df[total_col] if total_col else ""
    out[f"{prefix}_%"] = df[percent_col] if percent_col else ""
    out[f"{prefix}_Never"] = df[never_col] if never_col else 0

    return out

if s3 and p3 and l3:

    s_df = process_o3(s3, "S")
    p_df = process_o3(p3, "P")
    l_df = process_o3(l3, "L")

    max_len = max(len(s_df), len(p_df), len(l_df))

    s_df = s_df.reindex(range(max_len)).fillna("")
    p_df = p_df.reindex(range(max_len)).fillna("")
    l_df = l_df.reindex(range(max_len)).fillna("")

    blank1 = pd.DataFrame([""] * max_len, columns=[" "])
    blank2 = pd.DataFrame([""] * max_len, columns=["  "])

    output3 = pd.concat([s_df, blank1, p_df, blank2, l_df], axis=1)

    st.subheader("Output 3")
    st.dataframe(output3, use_container_width=True)

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
