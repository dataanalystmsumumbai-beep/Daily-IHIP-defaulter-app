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
# TAB 2: CONSOLIDATED REPORTING SUMMARY (FINAL WITH BOLD TOTAL & BORDERS)
# ----------------------------------------------------------------
import pandas as pd
import streamlit as st
from io import BytesIO
import datetime

with tab2:
    st.title("Reporting Summary Status")

    report_date = st.date_input("Select Report Date", datetime.date.today())
    formatted_date = report_date.strftime("%d-%m-%Y")

    sc1, sc2, sc3 = st.columns(3)
    sum_s = sc1.file_uploader("S-Form Summary", type=["xlsx"], key="s_sum")
    sum_p = sc2.file_uploader("P-Form Summary", type=["xlsx"], key="p_sum")
    sum_l = sc3.file_uploader("L-Form Summary", type=["xlsx"], key="l_sum")

    def safe_read_excel(file):
        if file is None: return pd.DataFrame()
        try:
            file.seek(0)
            df = pd.read_excel(file, engine="calamine")
            if df.empty: return df
            if all("Unnamed" in str(c) for c in df.columns[:2]):
                df.columns = df.iloc[0]
                df = df[1:].reset_index(drop=True)
            return df
        except Exception as e:
            st.error(f"Read error: {str(e)}")
            return pd.DataFrame()

    def process_summary_file(file, form_name):
        df = safe_read_excel(file)
        if df.empty: return pd.DataFrame()

        raw_cols = {c: str(c).replace(" ", "").lower() for c in df.columns}
        def find_fuzzy_col(keywords):
            for original_name, clean_name in raw_cols.items():
                if any(k in clean_name for k in keywords):
                    return original_name
            return None

        ward_col = find_fuzzy_col(["admin", "ward"])
        total_col = find_fuzzy_col(["totalreporting"])
        perc_col = find_fuzzy_col(["%ofaverage", "averagereporting"])
        non_rep_col = find_fuzzy_col(["neverreported", "nonreported"])

        if not (ward_col and total_col and perc_col and non_rep_col):
            st.error(f"❌ Missing columns in {form_name}")
            return pd.DataFrame()

        df = df[[ward_col, total_col, perc_col, non_rep_col]].copy()
        df.columns = ["ward", "Total Reporting Units", "% Of Average Reporting Units", "Non Reported Units"]

        df["ward"] = df["ward"].astype(str).str.strip()
        df = df[df["ward"].str.lower() != "nan"]
        
        for col in ["Total Reporting Units", "% Of Average Reporting Units", "Non Reported Units"]:
            df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)

        return df

    if sum_s and sum_p and sum_l:
        ds = process_summary_file(sum_s, "S-Form")
        dp = process_summary_file(sum_p, "P-Form")
        dl = process_summary_file(sum_l, "L-Form")

        if not ds.empty and not dp.empty and not dl.empty:
            m1 = pd.merge(ds, dp, on="ward", how="outer", suffixes=("_S", "_P"))
            master = pd.merge(m1, dl, on="ward", how="outer")
            
            master.rename(columns={
                "Total Reporting Units": "Total Reporting Units_L",
                "% Of Average Reporting Units": "% Of Average Reporting Units_L",
                "Non Reported Units": "Non Reported Units_L"
            }, inplace=True)

            master = master.fillna(0).sort_values("ward")
            master["Blank1"] = ""
            master["Blank2"] = ""

            final_order = [
                "ward",
                "Total Reporting Units_S", "% Of Average Reporting Units_S", "Non Reported Units_S",
                "Blank1",
                "Total Reporting Units_P", "% Of Average Reporting Units_P", "Non Reported Units_P",
                "Blank2",
                "Total Reporting Units_L", "% Of Average Reporting Units_L", "Non Reported Units_L"
            ]
            
            export_df = master[final_order]

            # Logic for Not Mapped and Bold Total
            is_not_mapped = export_df["ward"].str.lower().str.replace(" ", "") == "notmapped"
            not_mapped_df = export_df[is_not_mapped]
            main_df = export_df[~is_not_mapped]

            # Calculate Totals (Sum for Units, Average for Percentage)
            sum_data = {"ward": "Total"}
            for col in final_order:
                if col == "ward": continue
                if "Units" in col:
                    sum_data[col] = main_df[col].sum()
                elif "%" in col:
                    sum_data[col] = round(main_df[col].mean(), 2)
                else:
                    sum_data[col] = ""
            
            total_df = pd.DataFrame([sum_data])
            final_display_df = pd.concat([main_df, total_df, not_mapped_df], ignore_index=True)

            st.subheader("Consolidated Summary Preview")
            st.dataframe(final_display_df, use_container_width=True)

            # Excel Export with Full Formatting
            output = BytesIO()
            with pd.ExcelWriter(output, engine="xlsxwriter") as writer:
                final_display_df.to_excel(writer, index=False, sheet_name="Summary", startrow=3, header=False)
                
                workbook = writer.book
                worksheet = writer.sheets["Summary"]
                
                # --- FORMATS ---
                title_fmt = workbook.add_format({'bold': True, 'align': 'center', 'valign': 'vcenter', 'font_size': 14, 'border': 1})
                header_fmt = workbook.add_format({'bold': True, 'align': 'center', 'bg_color': '#D9EAD3', 'border': 1})
                sub_fmt = workbook.add_format({'bold': True, 'align': 'center', 'border': 1, 'text_wrap': True, 'bg_color': '#F3F3F3'})
                data_fmt = workbook.add_format({'border': 1, 'align': 'center'})
                total_row_fmt = workbook.add_format({'bold': True, 'border': 1, 'align': 'center', 'bg_color': '#EFEFEF'})
                
                # --- LAYOUT ---
                main_title = f"{formatted_date} IHIP S,P & L Reporting Status"
                worksheet.merge_range('A1:L1', main_title, title_fmt)

                worksheet.merge_range('B2:D2', 'S-Form Status', header_fmt)
                worksheet.merge_range('F2:H2', 'P-Form Status', header_fmt)
                worksheet.merge_range('J2:L2', 'L-Form Status', header_fmt)

                display_headers = ["Ward", "Total Reporting Units", "% Of Average", "Non Reported Units", "", 
                                   "Total Reporting Units", "% Of Average", "Non Reported Units", "", 
                                   "Total Reporting Units", "% Of Average", "Non Reported Units"]
                
                for col_num, col_name in enumerate(display_headers):
                    worksheet.write(2, col_num, col_name, sub_fmt)

                # --- APPLY BORDERS & BOLD TOTAL ---
                # Data starts from row 3 (0-indexed)
                for row_num in range(len(final_display_df)):
                    current_row_idx = row_num + 3
                    row_data = final_display_df.iloc[row_num]
                    
                    # Check if this is the "Total" row to apply bold format
                    is_total_row = str(row_data["ward"]).strip() == "Total"
                    fmt_to_use = total_row_fmt if is_total_row else data_fmt
                    
                    for col_num in range(len(final_order)):
                        val = row_data[final_order[col_num]]
                        worksheet.write(current_row_idx, col_num, val, fmt_to_use)

                # Column Widths
                worksheet.set_column('A:A', 25)
                worksheet.set_column('B:D', 18)
                worksheet.set_column('E:E', 2) # Blank
                worksheet.set_column('F:H', 18)
                worksheet.set_column('I:I', 2) # Blank
                worksheet.set_column('J:L', 18)

            final_file_name = f"{formatted_date} IHIP S,P & L Status Report.xlsx"
            st.download_button(
                label=f"📥 Download {final_file_name}",
                data=output.getvalue(),
                file_name=final_file_name,
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
    else:
        st.info("Upload S, P, and L files to begin.")
