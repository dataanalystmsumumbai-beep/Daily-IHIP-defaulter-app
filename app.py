import streamlit as st
import pandas as pd
from io import BytesIO
import datetime

st.set_page_config(page_title="IHIP Defaulter & Summary Tool", layout="wide")

# Creating two independent tabs
tab1, tab2 = st.tabs(["Defaulter Analysis", "Reporting Summary"])

# ----------------------------------------------------------------
# TAB 1: ORIGINAL DEFAULTER ANALYSIS CODE (No Changes Made)
# ----------------------------------------------------------------
with tab1:
    st.title("Daily IHIP Defaulter Analysis")

    col1, col2, col3 = st.columns(3)
    s_file = col1.file_uploader("S-Form", type=["xlsx"], key="s_def")
    p_file = col2.file_uploader("P-Form", type=["xlsx"], key="p_def")
    l_file = col3.file_uploader("L-Form", type=["xlsx"], key="l_def")

    st.markdown("---")
    contact_file = st.file_uploader("Upload Contact File", type=["xlsx"], key="cont_def")
    staff_input = st.text_input("Enter Staff Names (comma separated) i.e. A,B,C", key="staff_def")

    report_date = st.text_input("Enter Date (DD-MM-YYYY)", "13-04-2026", key="date_def")
    report_time = st.text_input("Enter Time Only (e.g. 04.05pm)", key="time_def")

    day_name = ""
    try:
        day_name = datetime.datetime.strptime(report_date, "%d-%m-%Y").strftime("%A")
    except:
        day_name = ""
    report_datetime = f"{day_name} {report_date} till {report_time}"

    def process_file(file, form):
        # Defaulter logic needs to be robust against openpyxl errors too
        try:
            raw = pd.read_excel(file, header=None, engine='openpyxl')
        except:
            raw = pd.read_excel(file, header=None) # Fallback

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
            return buf.getvalue()

        st.download_button("Download Output 1", generate_output1_excel(out1), f"{report_date}_Def.xlsx")
        st.download_button("Download Output 2", generate_output2_excel(out2, report_datetime), f"Def_List_{report_datetime}.xlsx")

# ----------------------------------------------------------------
# TAB 2: CONSOLIDATED REPORTING SUMMARY (Fixed TypeError)
# ----------------------------------------------------------------
with tab2:
    st.title("Reporting Summary Status")
    
    sc1, sc2, sc3 = st.columns(3)
    sum_s = sc1.file_uploader("S-Form Summary", type=["csv", "xlsx"], key="s_sum")
    sum_p = sc2.file_uploader("P-Form Summary", type=["csv", "xlsx"], key="p_sum")
    sum_l = sc3.file_uploader("L-Form Summary", type=["csv", "xlsx"], key="l_sum")

    def process_summary_file(file):
        if file.name.lower().endswith('.csv'):
            df = pd.read_csv(file)
        else:
            # FIX: Openpyxl cha error yenar nahi yasathi read_excel madhe engine handle kele aahe
            try:
                # Try reading with default engine, if fails use backup
                df = pd.read_excel(file)
            except Exception as e:
                # Fallback to handle style errors (Common in openpyxl)
                st.warning(f"Formatting issues in {file.name}, reading data only.")
                df = pd.read_excel(file, engine='openpyxl')
        
        # Normalize column names
        df.columns = [" ".join(str(c).split()) for c in df.columns]
        
        def find_col(k):
            return next((c for c in df.columns if k.lower() in c.lower()), None)
            
        ward_col = find_col("w a r d") or find_col("ward")
        total_col = find_col("total reporting units")
        perc_col = find_col("% of average")
        never_col = find_col("never reported")
        
        if not (ward_col and total_col and perc_col and never_col):
            st.error(f"Required columns not found in {file.name}")
            return pd.DataFrame()
            
        df = df[[ward_col, total_col, perc_col, never_col]].copy()
        df.rename(columns={
            ward_col: "ward", total_col: "Total Reporting Units",
            perc_col: "% Of Average Reporting Units",
            never_col: "Never Reported Reporting Units"
        }, inplace=True)
        
        for col in ["Total Reporting Units", "% Of Average Reporting Units", "Never Reported Reporting Units"]:
            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
        
        df["ward"] = df["ward"].astype(str).str.strip()
        return df[df["ward"] != "nan"]

    if sum_s and sum_p and sum_l:
        ds = process_summary_file(sum_s)
        dp = process_summary_file(sum_p)
        dl = process_summary_file(sum_l)
        
        if not ds.empty and not dp.empty and not dl.empty:
            master = pd.merge(ds, dp, on="ward", how="outer", suffixes=("_S", "_P"))
            master = pd.merge(master, dl, on="ward", how="outer").fillna(0)
            master.rename(columns={
                "Total Reporting Units": "Total Reporting Units_L",
                "% Of Average Reporting Units": "% Of Average Reporting Units_L",
                "Never Reported Reporting Units": "Never Reported Reporting Units_L"
            }, inplace=True)
            
            master = master.sort_values("ward")
            
            total_row = {"ward": "Total"}
            for sfx in ["_S", "_P", "_L"]:
                total_row[f"Total Reporting Units{sfx}"] = master[f"Total Reporting Units{sfx}"].sum()
                total_row[f"% Of Average Reporting Units{sfx}"] = master[f"% Of Average Reporting Units{sfx}"].mean()
                total_row[f"Never Reported Reporting Units{sfx}"] = master[f"Never Reported Reporting Units{sfx}"].sum()
            
            final_df_sum = pd.concat([master, pd.DataFrame([total_row])], ignore_index=True)
            final_df_sum["Blank1"] = ""; final_df_sum["Blank2"] = ""
            
            cols_order = [
                "ward",
                "Total Reporting Units_S", "% Of Average Reporting Units_S", "Never Reported Reporting Units_S", "Blank1",
                "Total Reporting Units_P", "% Of Average Reporting Units_P", "Never Reported Reporting Units_P", "Blank2",
                "Total Reporting Units_L", "% Of Average Reporting Units_L", "Never Reported Reporting Units_L"
            ]
            
            export_df = final_df_sum[cols_order]
            st.subheader("Summary Preview")
            st.dataframe(export_df, use_container_width=True)
            
            sum_buf = BytesIO()
            with pd.ExcelWriter(sum_buf, engine='xlsxwriter') as writer:
                export_df.to_excel(writer, index=False, sheet_name='Summary')
                workbook = writer.book
                worksheet = writer.sheets['Summary']
                header_fmt = workbook.add_format({'bold': True, 'bg_color': '#D7E4BC', 'border': 1})
                for col_num, value in enumerate(export_df.columns.values):
                    worksheet.write(0, col_num, value, header_fmt)

            st.download_button("Download Summary Excel", sum_buf.getvalue(), "Reporting_Summary.xlsx")
    else:
        st.info("Upload all three summary files to proceed.")
