import streamlit as st
import pandas as pd
from io import BytesIO

# =========================================================
# PAGE SETUP
# =========================================================

st.set_page_config(page_title="IHIP Defaulter Tool", layout="wide")
st.title("Daily IHIP Defaulter Analysis")

# =========================================================
# SAFE EXCEL READER (IMPORTANT FIX)
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
# OUTPUT 1 & 2 INPUTS
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
# OUTPUT 3 INPUTS (SEPARATE)
# =========================================================

st.subheader("📊 Output 3 Inputs (Ward Comparison)")

col4, col5, col6 = st.columns(3)

s_file_3 = col4.file_uploader("S-Form (Output 3)", type=["xlsx"])
p_file_3 = col5.file_uploader("P-Form (Output 3)", type=["xlsx"])
l_file_3 = col6.file_uploader("L-Form (Output 3)", type=["xlsx"])

output3_date = st.text_input("Enter Output 3 Date (DD-MM-YYYY)", "13-04-2026")

st.markdown("---")

# =========================================================
# PROCESS FUNCTION (OUTPUT 1 & 2)
# =========================================================

def process_file(file, form):

    raw = safe_read_excel(file,)

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

if ward:
    df["WARD"] = df[ward]
else:
    df["WARD"] = "Not Mentioned"

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

    out = pd.DataFrame()
    out["WARD"] = df[ward].fillna("Not Mentioned") if ward else "Not Mentioned"
    out["Facility Name"] = df[name]
    out["Form Type"] = form
    out["Category"] = df["Category"]
    out["REMARK"] = ""

    return out

# =========================================================
# OUTPUT 1
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

    def excel1(df):
        output = BytesIO()
        with pd.ExcelWriter(output, engine="openpyxl") as writer:
            df.to_excel(writer, index=False, startrow=2)
            ws = writer.sheets["Sheet1"]
            ws.merge_cells("A1:G1")
            ws["A1"] = "IHIP Defaulter Report"
            ws.merge_cells("A2:G2")
            ws["A2"] = report_date
        return output.getvalue()

    st.download_button("Download Output 1", excel1(out1), "output1.xlsx")

    # =====================================================
    # OUTPUT 2
    # =====================================================

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

            merged = merged.merge(cdf[["key", person, mobile]], on="key", how="left")

            merged.rename(columns={person: "Contact Person Name", mobile: "Mobile Number"}, inplace=True)

    for col in ["Contact Person Name", "Mobile Number"]:
        if col not in merged.columns:
            merged[col] = ""

    merged["Contact Person Name"] = merged["Contact Person Name"].astype(str).replace(["nan",""], "Not Available")
    merged["Mobile Number"] = merged["Mobile Number"].astype(str).replace(["nan",""], "Not Available")

    if staff_input:
        staff = [s.strip() for s in staff_input.split(",") if s.strip()]
        n = len(merged)
        k = len(staff)

        assigned = []
        if k > 0:
            base = n // k
            extra = n % k
            for i, s in enumerate(staff):
                count = base + (1 if i == k - 1 else 0)
                assigned.extend([s] * count)

        merged["Assigned Staff"] = assigned
    else:
        merged["Assigned Staff"] = ""

    merged.drop(columns=["key"], inplace=True)
    merged["REMARK"] = ""

    out2 = merged.copy()
    out2.insert(0, "Sr No", range(1, len(out2) + 1))

    st.subheader("Output 2")
    st.dataframe(out2, use_container_width=True)

    def excel2(df):
        output = BytesIO()
        with pd.ExcelWriter(output, engine="openpyxl") as writer:
            df.to_excel(writer, index=False, startrow=2)
            ws = writer.sheets["Sheet1"]
            ws.merge_cells("A1:J1")
            ws["A1"] = "IHIP Not Reporting Units"
            ws.merge_cells("A2:J2")
            ws["A2"] = report_datetime
        return output.getvalue()

    st.download_button("Download Output 2", excel2(out2), "output2.xlsx")

# =========================================================
# OUTPUT 3 (FULL FIXED SAFE VERSION)
# =========================================================

st.markdown("---")
st.subheader("Ward Wise Comparison (S / P / L)")

def process_simple(file, prefix):
    df = safe_read_excel(file)
    df.columns = [str(c).strip() for c in df.columns]

    ward_col = next((c for c in df.columns if "ward" in c.lower()), None)

    if not ward_col:
        return pd.DataFrame()

    temp = df[[ward_col]].copy()
    temp.columns = [f"{prefix}_Ward"]
    temp[f"{prefix}_Ward"] = temp[f"{prefix}_Ward"].fillna("Not Mentioned")

    return temp.sort_values(by=f"{prefix}_Ward").reset_index(drop=True)


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

    st.subheader("Output 3")
    st.dataframe(output3, use_container_width=True)

    def excel3(df):
        output = BytesIO()
        with pd.ExcelWriter(output, engine="openpyxl") as writer:
            df.to_excel(writer, index=False, startrow=2)
            ws = writer.sheets["Sheet1"]
            ws.merge_cells("A1:L1")
            ws["A1"] = "Ward Wise Comparison"
            ws.merge_cells("A2:L2")
            ws["A2"] = output3_date
        return output.getvalue()

    st.download_button("Download Output 3", excel3(output3), "output3.xlsx")

else:
    st.info("Upload S/P/L files for Output 3")
