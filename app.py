import streamlit as st
import pandas as pd
from io import BytesIO
import datetime

st.set_page_config(page_title="IHIP Defaulter & Summary Tool", layout="wide")

tab1, tab2 = st.tabs(["Defaulter Analysis", "Reporting Summary"])

# ==============================
# TAB 1 - DEFAULTER ANALYSIS
# ==============================
with tab1:
    st.title("Daily IHIP Defaulter Analysis")

    col1, col2, col3 = st.columns(3)
    s_file = col1.file_uploader("S-Form", type=["xlsx"], key="s_def")
    p_file = col2.file_uploader("P-Form", type=["xlsx"], key="p_def")
    l_file = col3.file_uploader("L-Form", type=["xlsx"], key="l_def")

    st.markdown("---")
    contact_file = st.file_uploader("Upload Contact File", type=["xlsx"], key="cont_def")
    staff_input = st.text_input("Enter Staff Names (comma separated)", key="staff_def")

    report_date = st.text_input("Enter Date (DD-MM-YYYY)", "13-04-2026")
    report_time = st.text_input("Enter Time (e.g. 04.05pm)")

    try:
        day_name = datetime.datetime.strptime(report_date, "%d-%m-%Y").strftime("%A")
    except:
        day_name = ""

    report_datetime = f"{day_name} {report_date} till {report_time}"

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

        df["Category"] = df[subtype].astype(str)

        out = pd.DataFrame()
        out["WARD"] = df[ward].fillna("Not Mentioned") if ward else "Not Mentioned"
        out["Facility Name"] = df[name]
        out["Form Type"] = form
        out["Category"] = df["Category"]
        out["REMARK"] = ""
        return out

    dfs = []
    if s_file: dfs.append(process_file(s_file, "S FORM"))
    if p_file: dfs.append(process_file(p_file, "P FORM"))
    if l_file: dfs.append(process_file(l_file, "L FORM"))

    if dfs:
        final_df = pd.concat(dfs, ignore_index=True)

        final_df["WARD"] = final_df["WARD"].fillna("Not Mentioned")

        out1 = final_df.copy()
        out1.insert(0, "Sr No", range(1, len(out1) + 1))

        st.subheader("Output 1")
        st.dataframe(out1, use_container_width=True)

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
                merged = merged.merge(cdf[["key", person, mobile]], on="key", how="left")
                merged.rename(columns={person: "Contact Person Name", mobile: "Mobile Number"}, inplace=True)

        # FIX MOBILE FORMAT
        if "Mobile Number" in merged.columns:
            merged["Mobile Number"] = (
                merged["Mobile Number"]
                .astype(str)
                .str.replace(r"\.0$", "", regex=True)
            )

        for col in ["Contact Person Name", "Mobile Number"]:
            if col not in merged.columns:
                merged[col] = ""

        merged.fillna("Not Available", inplace=True)

        # staff allocation
        if staff_input:
            staff = [s.strip() for s in staff_input.split(",") if s.strip()]
            n, k = len(merged), len(staff)

            if k > 0:
                base, extra = divmod(n, k)
                assigned = []

                for i, s in enumerate(staff):
                    count = base + (1 if i < extra else 0)
                    assigned.extend([s] * count)

                merged["Assigned Staff"] = assigned
        else:
            merged["Assigned Staff"] = "Not Assigned"

        merged.drop(columns=["key"], inplace=True)

        out2 = merged.copy()
        out2.insert(0, "Sr No", range(1, len(out2) + 1))

        st.subheader("Output 2")
        st.dataframe(out2, use_container_width=True)

        # -------------------------
        # EXCEL EXPORT FUNCTIONS
        # -------------------------
        def generate_output1_excel(df):
            buf = BytesIO()
            with pd.ExcelWriter(buf, engine="openpyxl") as writer:
                df.to_excel(writer, index=False, startrow=2)
                ws = writer.sheets["Sheet1"]
                ws.merge_cells("A1:F1")
                ws["A1"] = "IHIP Defaulter"
            buf.seek(0)
            return buf

        def generate_output2_excel(df, report_datetime):
            buf = BytesIO()
            with pd.ExcelWriter(buf, engine="openpyxl") as writer:
                df.to_excel(writer, index=False, startrow=2)
                ws = writer.sheets["Sheet1"]
                ws.merge_cells("A1:I1")
                ws["A1"] = "IHIP Defaulter List"
                ws.merge_cells("A2:I2")
                ws["A2"] = report_datetime
            buf.seek(0)
            return buf

        # ✅ FIXED INDENTATION HERE (IMPORTANT)
        st.download_button(
            "Download Output 1",
            data=generate_output1_excel(out1),
            file_name=f"{report_date}_output1.xlsx"
        )

        st.download_button(
            "Download Output 2",
            data=generate_output2_excel(out2, report_datetime),
            file_name=f"{report_date}_output2.xlsx"
        )

# ==============================
# TAB 2 - SUMMARY
# ==============================
with tab2:
    st.title("Reporting Summary Status")

    sc1, sc2, sc3 = st.columns(3)
    sum_s = sc1.file_uploader("S Summary", type=["csv", "xlsx"])
    sum_p = sc2.file_uploader("P Summary", type=["csv", "xlsx"])
    sum_l = sc3.file_uploader("L Summary", type=["csv", "xlsx"])

    def process_summary_file(file):
        try:
            if file.name.endswith(".csv"):
                df = pd.read_csv(file)
            else:
                df = pd.read_excel(file, engine="openpyxl")
        except Exception as e:
            st.error(str(e))
            return pd.DataFrame()

        df.columns = [" ".join(str(c).split()) for c in df.columns]

        def find(k):
            return next((c for c in df.columns if k.lower() in c.lower()), None)

        ward = find("ward")
        total = find("total reporting units")
        perc = find("% of average")
        never = find("never reported")

        if not all([ward, total, perc, never]):
            st.error("Missing columns")
            return pd.DataFrame()

        df = df[[ward, total, perc, never]]
        df.columns = ["ward", "Total", "Percent", "Never"]

        return df

    if sum_s and sum_p and sum_l:
        ds = process_summary_file(sum_s)
        dp = process_summary_file(sum_p)
        dl = process_summary_file(sum_l)

        if not ds.empty and not dp.empty and not dl.empty:
            st.success("Files loaded successfully")
