import streamlit as st
import pandas as pd
from io import BytesIO
import datetime

# Page Configuration
st.set_page_config(page_title="IHIP Tools Dashboard", layout="wide")

# Creating Two Independent Tabs
tab1, tab2 = st.tabs(["Defaulter Analysis Tool", "Consolidated Reporting Summary"])

# ---------------------------------------------------------
# TAB 1: DEFAULTER ANALYSIS TOOL (Existing Code)
# ---------------------------------------------------------
with tab1:
    st.title("Daily IHIP Defaulter Analysis")

    # UPLOAD SECTION
    col1, col2, col3 = st.columns(3)
    s_file = col1.file_uploader("S-Form (Defaulter)", type=["xlsx"])
    p_file = col2.file_uploader("P-Form (Defaulter)", type=["xlsx"])
    l_file = col3.file_uploader("L-Form (Defaulter)", type=["xlsx"])

    st.markdown("---")
    contact_file = st.file_uploader("Upload Contact File", type=["xlsx"])
    staff_input = st.text_input("Enter Staff Names (comma separated) i.e. A,B,C", key="staff_def")

    report_date = st.text_input("Enter Date (DD-MM-YYYY)", "13-04-2026", key="date_def")
    report_time = st.text_input("Enter Time Only (e.g. 04.05pm)", key="time_def")

    day_name = ""
    try:
        day_name = datetime.datetime.strptime(report_date, "%d-%m-%Y").strftime("%A")
    except:
        day_name = ""
    report_datetime = f"{day_name} {report_date} till {report_time}"

    def process_file_defaulter(file, form):
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
            "Dispensary": "PUBLIC", "Government Medical College Hospital": "PUBLIC",
            "IGSL Satellite Laboratory": "PUBLIC", "Infectious Disease Hospital": "PUBLIC",
            "Municipal Hospital": "PUBLIC", "Other Government Hospitals": "PUBLIC",
            "Urban Primary Health Centre": "PUBLIC", "Health Post": "PUBLIC",
            "Health Sub Centre": "PUBLIC", "Private Hospital": "PRIVATE",
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

    # Execution for Tab 1
    dfs_def = []
    if s_file: dfs_def.append(process_file_defaulter(s_file, "S FORM"))
    if p_file: dfs_def.append(process_file_defaulter(p_file, "P FORM"))
    if l_file: dfs_def.append(process_file_defaulter(l_file, "L FORM"))

    if dfs_def:
        final_df_def = pd.concat(dfs_def, ignore_index=True)
        final_df_def["WARD"] = final_df_def["WARD"].fillna("Not Mentioned").astype(str)
        final_df_def["ward_sort"] = final_df_def["WARD"].apply(lambda x: "ZZZ" if x.strip().lower() == "not mentioned" else x)
        final_df_def = final_df_def.sort_values(["ward_sort", "Facility Name"]).drop(columns=["ward_sort"])
        
        out1 = final_df_def.copy()
        out1.insert(0, "Sr No", range(1, len(out1)+1))
        st.subheader("Defaulter Output 1")
        st.dataframe(out1, use_container_width=True)

        # Output 2 logic with contact merge
        merged = final_df_def.copy()
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
        
        if "Mobile Number" in merged.columns:
            merged["Mobile Number"] = merged["Mobile Number"].astype(str).str.replace(".0", "", regex=False)
        for col in ["Contact Person Name", "Mobile Number"]:
            if col not in merged.columns: merged[col] = "Not Available"
        
        # Staff assignment
        if staff_input:
            staff = [s.strip() for s in staff_input.split(",") if s.strip()]
            if len(staff) > 0:
                n, k = len(merged), len(staff)
                base, extra = n // k, n % k
                assigned = []
                for i, s in enumerate(staff):
                    count = base + (1 if i < extra else 0)
                    assigned.extend([s] * count)
                merged["Assigned Staff"] = assigned
        else:
            merged["Assigned Staff"] = "Not Assigned"
        
        merged.drop(columns=["key"], inplace=True)
        out2 = merged.copy()
        out2.insert(0, "Sr No", range(1, len(out2)+1))
        st.subheader("Defaulter Output 2")
        st.dataframe(out2, use_container_width=True)

        # Excel Export Functions for Tab 1
        def get_excel_output1(df):
            buf = BytesIO()
            with pd.ExcelWriter(buf, engine='openpyxl') as writer:
                df.to_excel(writer, index=False, startrow=2)
                ws = writer.sheets['Sheet1']
                ws.merge_cells('A1:F1'); ws['A1'] = "IHIP Defaulter"
                ws.merge_cells('A2:F2'); ws['A2'] = report_date
            return buf.getvalue()

        st.download_button("Download Defaulter Output 1", get_excel_output1(out1), f"Defaulter_List_{report_date}.xlsx")

# ---------------------------------------------------------
# TAB 2: CONSOLIDATED REPORTING SUMMARY (New Tool)
# ---------------------------------------------------------
with tab2:
    st.title("Reporting Summary Status")
    
    sc1, sc2, sc3 = st.columns(3)
    sum_s = sc1.file_uploader("S-Form Summary File", type=["csv", "xlsx"])
    sum_p = sc2.file_uploader("P-Form Summary File", type=["csv", "xlsx"])
    sum_l = sc3.file_uploader("L-Form Summary File", type=["csv", "xlsx"])

    def process_summary(file):
        df = pd.read_csv(file) if file.name.endswith('.csv') else pd.read_excel(file)
        df.columns = [str(c).strip() for c in df.columns]
        
        # Original Column Names
        ward_orig = "A D M I N I S T R A T I V E W A R D"
        total_orig = "Total Reporting Units"
        perc_orig = "% Of Average Reporting Units"
        never_orig = "Never Reported Reporting Units For Selected Period"
        
        # Select and Rename
        df = df[[ward_orig, total_orig, perc_orig, never_orig]].copy()
        df.rename(columns={
            ward_orig: "ward",
            total_orig: "Total Reporting Units",
            perc_orig: "% Of Average Reporting Units",
            never_orig: "Never Reported Reporting Units"
        }, inplace=True)
        return df

    if sum_s and sum_p and sum_l:
        ds = process_summary(sum_s)
        dp = process_summary(sum_p)
        dl = process_summary(sum_l)
        
        # Merge all forms on ward
        master = pd.merge(ds, dp, on="ward", how="outer", suffixes=("_S", "_P"))
        master = pd.merge(master, dl, on="ward", how="outer")
        master.rename(columns={
            "Total Reporting Units": "Total Reporting Units_L",
            "% Of Average Reporting Units": "% Of Average Reporting Units_L",
            "Never Reported Reporting Units": "Never Reported Reporting Units_L"
        }, inplace=True)
        
        master = master.sort_values("ward").fillna(0)

        # Create Total Row
        total_data = {"ward": "Total"}
        for sfx in ["_S", "_P", "_L"]:
            total_data[f"Total Reporting Units{sfx}"] = master[f"Total Reporting Units{sfx}"].sum()
            total_data[f"% Of Average Reporting Units{sfx}"] = master[f"% Of Average Reporting Units{sfx}"].mean()
            total_data[f"Never Reported Reporting Units{sfx}"] = master[f"Never Reported Reporting Units{sfx}"].sum()
        
        df_total_row = pd.DataFrame([total_data])
        final_summary = pd.concat([master, df_total_row], ignore_index=True)

        # Add Blank Columns
        final_summary["Blank1"] = ""
        final_summary["Blank2"] = ""

        # Column Ordering: Ward | S_Data | Blank | P_Data | Blank | L_Data
        cols = ["ward", 
                "Total Reporting Units_S", "% Of Average Reporting Units_S", "Never Reported Reporting Units_S",
                "Blank1",
                "Total Reporting Units_P", "% Of Average Reporting Units_P", "Never Reported Reporting Units_P",
                "Blank2",
                "Total Reporting Units_L", "% Of Average Reporting Units_L", "Never Reported Reporting Units_L"]
        
        export_df = final_summary[cols].copy()
        
        st.subheader("Consolidated Summary Preview")
        st.dataframe(export_df, use_container_width=True)

        # Excel Export logic for Tab 2
        sum_buf = BytesIO()
        with pd.ExcelWriter(sum_buf, engine='xlsxwriter') as writer:
            export_df.to_excel(writer, index=False, sheet_name='Summary_Status')
            workbook = writer.book
            worksheet = writer.sheets['Summary_Status']
            # Bold Header and Total Row
            header_format = workbook.add_format({'bold': True, 'bg_color': '#D7E4BC', 'border': 1})
            total_format = workbook.add_format({'bold': True, 'bg_color': '#F2F2F2', 'border': 1})
            
            for col_num, value in enumerate(export_df.columns.values):
                worksheet.write(0, col_num, value, header_format)
            
            last_row = len(export_df)
            for col_num, value in enumerate(export_df.iloc[-1].values):
                worksheet.write(last_row, col_num, value, total_format)

        st.download_button("Download Consolidated Summary Excel", sum_buf.getvalue(), "Reporting_Summary_Status.xlsx")
    else:
        st.info("Upload S, P, and L files in this section to generate the summary.")
