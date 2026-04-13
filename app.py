import streamlit as st
import pandas as pd
from io import BytesIO
import datetime
import openpyxl

st.set_page_config(page_title="IHIP Defaulter & Summary Tool", layout="wide")

# Creating two independent tabs
tab1, tab2 = st.tabs(["Defaulter Analysis", "Reporting Summary"])

# ----------------------------------------------------------------
# TAB 1: ORIGINAL DEFAULTER ANALYSIS CODE (UNTOUCHED LOGIC)
# ----------------------------------------------------------------
with tab1:
    st.title("Daily IHIP Defaulter Analysis")
    
    # ---------------- UPLOAD ----------------
    col1, col2, col3 = st.columns(3)
    s_file = col1.file_uploader("S-Form", type=["xlsx"], key="s_def")
    p_file = col2.file_uploader("P-Form", type=["xlsx"], key="p_def")
    l_file = col3.file_uploader("L-Form", type=["xlsx"], key="l_def")
    
    st.markdown("---")
    contact_file = st.file_uploader("Upload Contact File", type=["xlsx"], key="cont_def")
    staff_input = st.text_input("Enter Staff Names (comma separated) i.e. A,B,C", key="staff_def")
    
    # ---------------- INPUTS ----------------
    report_date = st.text_input("Enter Date (DD-MM-YYYY)", "13-04-2026", key="date_def")
    report_time = st.text_input("Enter Time Only (e.g. 04.05pm)", key="time_def")
    
    # ---------------- AUTO DAY + DATETIME ----------------
    day_name = ""
    try:
        day_name = datetime.datetime.strptime(report_date, "%d-%m-%Y").strftime("%A")
    except:
        day_name = ""
    report_datetime = f"{day_name} {report_date} till {report_time}"
    
    # ---------------- PROCESS ----------------
    def process_file(file, form):
        try:
            with pd.ExcelFile(file) as xls:
                raw = pd.read_excel(xls, header=None)
        except:
            raw = pd.read_excel(file, header=None, engine='openpyxl')

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

    # ---------------- MAIN ----------------
    dfs = []
    if s_file: dfs.append(process_file(s_file, "S FORM"))
    if p_file: dfs.append(process_file(p_file, "P FORM"))
    if l_file: dfs.append(process_file(l_file, "L FORM"))

    if dfs:
        final_df = pd.concat(dfs, ignore_index=True)
        final_df["WARD"] = final_df["WARD"].fillna("Not Mentioned").astype(str)
        final_df["ward_sort"] = final_df["WARD"].apply(lambda x: "ZZZ" if x.strip().lower() == "not mentioned" else x)
        final_df = final_df.sort_values(["ward_sort", "Facility Name"]).drop(columns=["ward_sort"])
        
        out1 = final_df.copy()
        out1.insert(0, "Sr No", range(1, len(out1)+1))
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
        
        if "Mobile Number" in merged.columns:
            merged["Mobile Number"] = merged["Mobile Number"].astype(str).str.replace(".0", "", regex=False)
        for col in ["Contact Person Name", "Mobile Number"]:
            if col not in merged.columns: merged[col] = ""
        merged["Contact Person Name"] = merged["Contact Person Name"].astype(str).replace(["nan",""], "Not Available")
        merged["Mobile Number"] = merged["Mobile Number"].astype(str).replace(["nan",""], "Not Available")

        if staff_input:
            staff = [s.strip() for s in staff_input.split(",") if s.strip()]
            n, k = len(merged), len(staff)
            if k > 0:
                base, extra = n // k, n % k
                assigned = []
                for i, s in enumerate(staff):
                    count = base + (extra if i == k - 1 else 0)
                    assigned.extend([s] * count)
                merged["Assigned Staff"] = assigned
        else:
            merged["Assigned Staff"] = "Not Assigned"

        merged.drop(columns=["key"], inplace=True)
        out2 = merged.copy()
        out2.insert(0, "Sr No", range(1, len(out2)+1))
        st.subheader("Output 2")
        st.dataframe(out2, use_container_width=True)

        def generate_output1_excel(df):
            buf = BytesIO()
            with pd.ExcelWriter(buf, engine='openpyxl') as writer:
                df.to_excel(writer, index=False, startrow=2)
                ws = writer.sheets['Sheet1']
                ws.merge_cells('A1:F1'); ws['A1'] = "IHIP Defaulter"
                ws.merge_cells('A2:F2'); ws['A2'] = report_date
            return buf.getvalue()

        def generate_output2_excel(df, report_datetime):
            buf = BytesIO()
            with pd.ExcelWriter(buf, engine='openpyxl') as writer:
                df.to_excel(writer, index=False, startrow=2)
                ws = writer.sheets['Sheet1']
                ws.merge_cells('A1:I1'); ws['A1'] = "IHIP Defaulter List of S, P & L Form"
                ws.merge_cells('A2:I2'); ws['A2'] = report_datetime
                for row in range(4, ws.max_row + 1): ws[f'G{row}'].number_format = '@'
            return buf.getvalue()

        st.download_button("Download Output 1", generate_output1_excel(out1), f"{report_date}_IHIP Defaulter List of S, P & L Form.xlsx")
        st.download_button("Download Output 2", generate_output2_excel(out2, report_datetime), f"IHIP Defaulter List of S, P & L Form of _{report_datetime}.xlsx")

# ----------------------------------------------------------------
# TAB 2: CONSOLIDATED REPORTING SUMMARY (Style Error Fix & English Only)
# ----------------------------------------------------------------
import openpyxl # Make sure openpyxl is imported at the top of your app.py

with tab2:
    st.title("Reporting Summary Status")
    
    sc1, sc2, sc3 = st.columns(3)
    sum_s = sc1.file_uploader("S-Form Summary", type=["csv", "xlsx"], key="s_sum")
    sum_p = sc2.file_uploader("P-Form Summary", type=["csv", "xlsx"], key="p_sum")
    sum_l = sc3.file_uploader("L-Form Summary", type=["csv", "xlsx"], key="l_sum")

    def process_summary_file(file, form_name):
        df = pd.DataFrame()
        try:
            if file.name.lower().endswith('.csv'):
                df = pd.read_csv(file)
            else:
                df = pd.read_excel(file)
        except Exception as e:
            # Fallback for IHIP Excel files with corrupted fill styles
            if "Fill" in str(e) or "openpyxl" in str(e).lower():
                try:
                    file.seek(0) # Reset file pointer
                    wb = openpyxl.load_workbook(file, read_only=True, data_only=True)
                    ws = wb.active
                    data = list(ws.values)
                    if data:
                        df = pd.DataFrame(data[1:], columns=data[0])
                    else:
                        st.error(f"The file {form_name} appears to be empty.")
                        return pd.DataFrame()
                except Exception as fallback_e:
                    st.error(f"Error reading {form_name} (Fallback failed): {str(fallback_e)}")
                    return pd.DataFrame()
            else:
                st.error(f"Error reading {form_name}: {str(e)}")
                return pd.DataFrame()
        
        if df.empty:
            return pd.DataFrame()

        # Clean column names
        df.columns = [" ".join(str(c).split()) for c in df.columns]
        
        def find_col(k):
            return next((c for c in df.columns if k.lower() in c.lower()), None)
            
        ward_col = find_col("ward")
        total_col = find_col("total")
        perc_col = find_col("%") 
        
        if not (ward_col and total_col and perc_col):
            st.error(f"Required columns not found in {form_name}. Available columns: {', '.join(df.columns)}")
            return pd.DataFrame()
            
        df = df[[ward_col, total_col, perc_col]].copy()
        df.rename(columns={
            ward_col: "ward", 
            total_col: "Total Units",
            perc_col: "% Reporting"
        }, inplace=True)
        
        for col in ["Total Units", "% Reporting"]:
            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
        
        df["ward"] = df["ward"].astype(str).str.strip()
        return df[df["ward"] != "nan"]

    if sum_s and sum_p and sum_l:
        ds = process_summary_file(sum_s, "S-Form")
        dp = process_summary_file(sum_p, "P-Form")
        dl = process_summary_file(sum_l, "L-Form")
        
        if ds.empty or dp.empty or dl.empty:
            st.warning("Data processing failed. Please check the error messages above.")
        else:
            master = pd.merge(ds, dp, on="ward", how="outer", suffixes=("_S", "_P"))
            master = pd.merge(master, dl, on="ward", how="outer").fillna(0)
            master.rename(columns={"Total Units": "Total Units_L", "% Reporting": "% Reporting_L"}, inplace=True)
            
            master = master.sort_values("ward")
            master["Blank1"] = ""; master["Blank2"] = ""
            
            cols_order = [
                "ward", "Total Units_S", "% Reporting_S", "Blank1",
                "Total Units_P", "% Reporting_P", "Blank2",
                "Total Units_L", "% Reporting_L"
            ]
            export_df = master[cols_order]

            st.subheader("Summary Preview")
            st.dataframe(export_df, use_container_width=True)
            
            try:
                sum_buf = BytesIO()
                with pd.ExcelWriter(sum_buf, engine='xlsxwriter') as writer:
                    export_df.to_excel(writer, index=False, sheet_name='Summary', startrow=3, header=False)
                    
                    workbook = writer.book
                    worksheet = writer.sheets['Summary']
                    
                    bold_center = workbook.add_format({'bold': True, 'align': 'center', 'border': 1})
                    header_fmt = workbook.add_format({'bold': True, 'align': 'center', 'bg_color': '#F2F2F2', 'border': 1})

                    worksheet.merge_range('B1:C1', 'Non reporting units', bold_center)
                    worksheet.merge_range('F1:G1', 'Non reporting units', bold_center)
                    worksheet.merge_range('I1:J1', 'Non reporting units', bold_center)

                    worksheet.merge_range('B2:C2', 'S-Form', bold_center)
                    worksheet.merge_range('F2:G2', 'P-Form', bold_center)
                    worksheet.merge_range('I2:J2', 'L-Form', bold_center)

                    sub_headers = ['ward', 'Total Units', '% Reporting', '', 'Total Units', '% Reporting', '', 'Total Units', '% Reporting']
                    for col_num, header in enumerate(sub_headers):
                        if header:
                            worksheet.write(2, col_num, header, header_fmt)

                st.success("File generated successfully! Click the button below to download.")
                st.download_button(
                    label="📥 Download Summary Excel",
                    data=sum_buf.getvalue(),
                    file_name="Reporting_Summary.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    key="download_summary_btn"
                )
            except Exception as e:
                st.error(f"Error generating Excel file: {str(e)}")
    else:
        st.info("Please upload all three (S, P, L) summary files.")
