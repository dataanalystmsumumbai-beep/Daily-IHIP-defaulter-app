import streamlit as st
import pandas as pd
from io import BytesIO

st.set_page_config(page_title="IHIP Defaulter Tool", layout="wide")
st.title("Daily IHIP Defaulter Analysis")

# ---------------- Upload ----------------
col1, col2, col3 = st.columns(3)

s_file = col1.file_uploader("S-Form", type=["xlsx"])
p_file = col2.file_uploader("P-Form", type=["xlsx"])
l_file = col3.file_uploader("L-Form", type=["xlsx"])

st.markdown("---")

contact_file = st.file_uploader("Upload Contact File", type=["xlsx"])
staff_input = st.text_input("Enter Staff Names (comma separated) i.e. A,B,C")

# Manual Inputs
report_date = st.text_input("Enter Date (DD-MM-YYYY)", "13-04-2026")
report_time = st.text_input("Enter Time Only (e.g. 04.05pm)")
import datetime

day_name = ""
try:
    day_name = datetime.datetime.strptime(report_date, "%d-%m-%Y").strftime("%A")
except:
    day_name = ""
    report_datetime = f"{day_name} {report_date} till {report_time}"
    

st.markdown("---")

# ---------------- PROCESS ----------------
def process_file(file, form):
    raw = pd.read_excel(file, header=None)

    header_row = 0
    for i, row in raw.iterrows():
        if "facility name" in str(row).lower():
            header_row = i
            break

    df = pd.read_excel(file, skiprows=header_row)
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

    out = pd.DataFrame()
    out["WARD"] = df[ward].fillna("Not Mentioned") if ward else "Not Mentioned"
    out["Facility Name"] = df[name]
    out["Form Type"] = form
    out["Category"] = df["Category"]
    out["REMARK"] = ""

    return out

# ---------------- MAIN ----------------
dfs = []

if s_file:
    dfs.append(process_file(s_file, "S FORM"))
if p_file:
    dfs.append(process_file(p_file, "P FORM"))
if l_file:
    dfs.append(process_file(l_file, "L FORM"))

if dfs:
    final_df = pd.concat(dfs, ignore_index=True)

    # 🔥 SORT (Not Mentioned last)
    final_df["WARD"] = final_df["WARD"].astype(str)

    final_df["ward_sort"] = final_df["WARD"].apply(
        lambda x: "ZZZ" if x.strip().lower() == "not mentioned" else x
    )

    final_df = final_df.sort_values(["ward_sort", "Facility Name"]).drop(columns=["ward_sort"])

    # ---------------- OUTPUT 1 ----------------
    out1 = final_df.copy()
    out1.insert(0, "Sr No", range(1, len(out1)+1))

    st.subheader("Output 1")
    st.dataframe(out1, use_container_width=True)

    # ---------------- OUTPUT 2 ----------------
    merged = final_df.copy()
    merged["key"] = merged["Facility Name"].astype(str).str.strip().str.lower()

    if contact_file:
        cdf = pd.read_excel(contact_file)
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

    for col in ["Contact Person Name", "Mobile Number"]:
        if col not in merged.columns:
            merged[col] = ""

    merged["Contact Person Name"] = merged["Contact Person Name"].astype(str).replace(["nan",""], "Not Available")
    merged["Mobile Number"] = merged["Mobile Number"].astype(str).replace(["nan",""], "Not Available")

    # 🔥 ASSIGNED STAFF
    if staff_input:
        staff = [s.strip() for s in staff_input.split(",") if s.strip()]
        n = len(merged)
        k = len(staff)

        assigned = []
        if k > 0:
            base = n // k
            extra = n % k
            for i, s in enumerate(staff):
                count = base
                if i == k - 1:
                    count += extra
                assigned.extend([s] * count)

        merged["Assigned Staff"] = assigned
    else:
        merged["Assigned Staff"] = ""

    merged.drop(columns=["key"], inplace=True)

    out2 = merged.copy()
    out2.insert(0, "Sr No", range(1, len(out2)+1))

    st.subheader("Output 2")
    st.dataframe(out2, use_container_width=True)

    # ---------------- EXCEL EXPORT ----------------
    def generate_output1_excel(df):
        output = BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, index=False, startrow=2)
            ws = writer.sheets['Sheet1']

            ws.merge_cells('A1:F1')
            ws['A1'] = "IHIP Defaulter"

            ws.merge_cells('A2:F2')
            ws['A2'] = report_date

        return output.getvalue()

    def generate_output2_excel(df):
        output = BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, index=False, startrow=2)
            ws = writer.sheets['Sheet1']

            ws.merge_cells('A1:I1')
            ws['A1'] = "IHIP not reporting units"

            ws.merge_cells('A2:I2')
            ws['A2'] = report_datetime

        return output.getvalue()

    # DOWNLOAD BUTTONS
    st.download_button(
    "Download Output 1 Excel",
    generate_output1_excel(out1),
    f"{report_date} IHIP Defaulter List of S, P & L Form.xlsx"
)

    st.download_button(
    "Download Output 2 Excel",
    generate_output2_excel(out2),
    f"IHIP Defaulter List of S, P & L Form of {report_datetime}.xlsx"
)

else:
    st.info("Upload files to proceed")
