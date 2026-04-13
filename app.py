import streamlit as st
import pandas as pd
from io import BytesIO

st.set_page_config(page_title="IHIP Defaulter Tool", layout="wide")
st.title("Daily IHIP Defaulter Analysis")

# =====================================================
# SAFE EXCEL READER
# =====================================================
def safe_read_excel(file):
    try:
        return pd.read_excel(file, engine="openpyxl")
    except:
        return pd.read_excel(file)

# =====================================================
# ================= OUTPUT 1 & 2 INPUT =================
# =====================================================
st.header("Output 1 & 2")

col1, col2, col3 = st.columns(3)

s_file = col1.file_uploader("S-Form (O1/O2)", type=["xlsx"])
p_file = col2.file_uploader("P-Form (O1/O2)", type=["xlsx"])
l_file = col3.file_uploader("L-Form (O1/O2)", type=["xlsx"])

st.markdown("---")

contact_file = st.file_uploader("Upload Contact File", type=["xlsx"])
staff_input = st.text_input("Enter Staff Names (comma separated)")

report_date = st.text_input("Enter Date", "13-04-2026")
report_datetime = st.text_input("Enter Date-Time", "Monday 13-04-2026")

# =====================================================
# PROCESS OUTPUT 1 & 2
# =====================================================
def process_file(file, form):

    df = safe_read_excel(file)
    df.columns = [str(c).strip() for c in df.columns]

    def find_col(k):
        return next((c for c in df.columns if k in c.lower()), None)

    name = find_col("facility name")
    subtype = find_col("facility sub-type")
    report = find_col("number of times reported")
    ward = next((c for c in df.columns if "ward" in c.lower() or "zone" in c.lower()), None)

    if name is None:
        df["Facility Name"] = ""
        name = "Facility Name"
    if subtype is None:
        df["Facility Sub-Type"] = ""
        subtype = "Facility Sub-Type"
    if report is None:
        df["Number of Times Reported"] = 0
        report = "Number of Times Reported"
    if ward is None:
        df["WARD"] = "Not Mentioned"
        ward = "WARD"

    df[report] = pd.to_numeric(df[report], errors="coerce").fillna(0)
    df = df[df[report] == 0].copy()

    category_map = {
        "Dispensary": "PUBLIC",
        "Municipal Hospital": "PUBLIC",
        "Urban Primary Health Centre": "PUBLIC",
        "Health Post": "PUBLIC",
        "Health Sub Centre": "PUBLIC",
        "Private Hospital": "PRIVATE",
        "Private Laboratory": "PRIVATE"
    }

    df["Category"] = df[subtype].map(category_map).fillna("OTHER")

    out = pd.DataFrame()
    out["WARD"] = df[ward].astype(str)
    out["Facility Name"] = df[name].astype(str)
    out["Form Type"] = form
    out["Category"] = df["Category"]
    out["REMARK"] = ""

    return out

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
    out1.insert(0, "Sr No", range(1, len(out1)+1))

    st.subheader("Output 1")
    st.dataframe(out1, use_container_width=True)

    # ---------------- OUTPUT 2 ----------------
    merged = final_df.copy()
    merged["key"] = merged["Facility Name"].astype(str).str.strip().str.lower()

    if contact_file:
        cdf = safe_read_excel(contact_file)
        cdf.columns = [str(c).strip() for c in cdf.columns]

        name_c = next((c for c in cdf.columns if "facility" in c.lower()), None)
        person = next((c for c in cdf.columns if "contact" in c.lower()), None)
        mobile = next((c for c in cdf.columns if "mobile" in c.lower()), None)

        if name_c and person and mobile:
            cdf["key"] = cdf[name_c].astype(str).str.strip().str.lower()

            merged = merged.merge(
                cdf[["key", person, mobile]],
                on="key",
                how="left"
            )

            merged.rename(columns={
                person: "Contact Person Name",
                mobile: "Mobile Number"
            }, inplace=True)

    if "Contact Person Name" not in merged.columns:
        merged["Contact Person Name"] = ""
    if "Mobile Number" not in merged.columns:
        merged["Mobile Number"] = ""

    merged["Contact Person Name"] = merged["Contact Person Name"].fillna("Not Available")
    merged["Mobile Number"] = merged["Mobile Number"].fillna("Not Available")

    if staff_input:
        staff = [s.strip() for s in staff_input.split(",") if s.strip()]
        if staff:
            merged["Assigned Staff"] = (staff * ((len(merged)//len(staff))+1))[:len(merged)]
        else:
            merged["Assigned Staff"] = ""
    else:
        merged["Assigned Staff"] = ""

    merged.drop(columns=["key"], inplace=True)

    out2 = merged.copy()
    out2.insert(0, "Sr No", range(1, len(out2)+1))

    st.subheader("Output 2")
    st.dataframe(out2, use_container_width=True)

# =====================================================
# ================= OUTPUT 3 (SEPARATE INPUTS) =========
# =====================================================
st.markdown("---")
st.header("Output 3 - Ward Reporting Comparison")

colA, colB, colC = st.columns(3)

s3 = colA.file_uploader("S Form (O3)", type=["xlsx"])
p3 = colB.file_uploader("P Form (O3)", type=["xlsx"])
l3 = colC.file_uploader("L Form (O3)", type=["xlsx"])

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

if s3 and p3 and l3:

    s_df = process_o3(s3, "S")
    p_df = process_o3(p3, "P")
    l_df = process_o3(l3, "L")

    def safe_sum(x):
        return pd.to_numeric(x, errors="coerce").fillna(0).sum()

    col1, col2, col3 = st.columns(3)
    col1.metric("S Non Reporting", int(safe_sum(s_df.iloc[:, -1])))
    col2.metric("P Non Reporting", int(safe_sum(p_df.iloc[:, -1])))
    col3.metric("L Non Reporting", int(safe_sum(l_df.iloc[:, -1])))

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

else:
    st.info("Upload files for Output 1 & 2")
