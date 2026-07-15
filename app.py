
# ----------------------------------------------------------------
# TAB 2: CONSOLIDATED REPORTING SUMMARY (STRICT ERROR FIX)
# ----------------------------------------------------------------
import pandas as pd
import streamlit as st
from io import BytesIO
import datetime

with tab2:
    st.title("Reporting Summary Status")

    report_date = st.date_input("Select Report Date", datetime.date.today(), key="date_tab2")
    formatted_date = report_date.strftime("%d-%m-%Y")

    sc1, sc2, sc3 = st.columns(3)
    sum_s = sc1.file_uploader("S-Form Summary", type=["xlsx"], key="s_sum")
    sum_p = sc2.file_uploader("P-Form Summary", type=["xlsx"], key="p_sum")
    sum_l = sc3.file_uploader("L-Form Summary", type=["xlsx"], key="l_sum")

    def safe_read_excel(file):
        if file is None: 
            return pd.DataFrame()
        try:
            file.seek(0)
            df = pd.read_excel(file, engine="calamine")
            if df.empty: 
                return df
            if all("Unnamed" in str(c) for c in df.columns[:2]):
                df.columns = df.iloc[0]
                df = df[1:].reset_index(drop=True)
            return df
        except Exception as e:
            st.error(f"Read error: {str(e)}")
            return pd.DataFrame()

    def process_summary_file(file, form_name):
        df = safe_read_excel(file)
        if df.empty: 
            return pd.DataFrame()

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
            master["Blank1"], master["Blank2"] = "", ""

            final_order = [
                "ward",
                "Total Reporting Units_S", "% Of Average Reporting Units_S", "Non Reported Units_S",
                "Blank1",
                "Total Reporting Units_P", "% Of Average Reporting Units_P", "Non Reported Units_P",
                "Blank2",
                "Total Reporting Units_L", "% Of Average Reporting Units_L", "Non Reported Units_L"
            ]
            
            export_df = master[final_order].copy()
            is_not_mapped = export_df["ward"].str.lower().str.replace(" ", "") == "notmapped"
            main_df = export_df[~is_not_mapped].copy()
            not_mapped_df = export_df[is_not_mapped].copy()

            # --- Proper Average/Sum Calculation ---
            sum_data = {"ward": "Total"}
            for col in final_order:
                if col == "ward" or "Blank" in col:
                    sum_data[col] = ""
                    continue
                if "%" in col:
                    sum_data[col] = round(float(main_df[col].mean()), 2)
                elif "Units" in col:
                    sum_data[col] = int(main_df[col].sum())
            
            total_df = pd.DataFrame([sum_data])
            total_df.at[0, "ward"] = "Total"
            
            # Align columns explicitly before concat to prevent structural layout breaks
            total_df = total_df.reindex(columns=final_order)
            final_display_df = pd.concat([main_df, total_df, not_mapped_df], ignore_index=True)

            st.subheader("Consolidated Summary Preview")
            st.dataframe(final_display_df, use_container_width=True)

            # --- Secure Excel Export ---
            output = BytesIO()
            with pd.ExcelWriter(output, engine="xlsxwriter") as writer:
                # Write empty template matching shape to initialize sheet safely
                final_display_df.to_excel(writer, index=False, sheet_name="Summary", startrow=3, header=False)
                workbook, worksheet = writer.book, writer.sheets["Summary"]
                
                # Formats
                title_fmt = workbook.add_format({'bold': True, 'align': 'center', 'valign': 'vcenter', 'font_size': 14, 'border': 1})
                header_fmt = workbook.add_format({'bold': True, 'align': 'center', 'bg_color': '#D9EAD3', 'border': 1})
                sub_fmt = workbook.add_format({'bold': True, 'align': 'center', 'border': 1, 'text_wrap': True, 'bg_color': '#F3F3F3'})
                data_fmt = workbook.add_format({'border': 1, 'align': 'center'})
                total_row_fmt = workbook.add_format({'bold': True, 'border': 1, 'align': 'center', 'bg_color': '#EFEFEF'})
                
                # Headers
                worksheet.merge_range('A1:L1', f"{formatted_date} IHIP S,P & L Reporting Status", title_fmt)
                worksheet.merge_range('B2:D2', 'S-Form Status', header_fmt)
                worksheet.merge_range('F2:H2', 'P-Form Status', header_fmt)
                worksheet.merge_range('J2:L2', 'L-Form Status', header_fmt)

                headers = ["Ward", "Total Reporting Units", "% Of Average", "Non Reported Units", "", 
                           "Total Reporting Units", "% Of Average", "Non Reported Units", "", 
                           "Total Reporting Units", "% Of Average", "Non Reported Units"]
                for i, h in enumerate(headers): 
                    worksheet.write(2, i, h, sub_fmt)

                # --- Error-Safe Write Loop ---
                for row_num in range(len(final_display_df)):
                    row_data = final_display_df.iloc[row_num]
                    is_total = str(row_data["ward"]).strip() == "Total"
                    fmt = total_row_fmt if is_total else data_fmt
                    
                    for col_num in range(len(final_order)):
                        val = row_data[final_order[col_num]]
                        # Stringify representation safe checks
                        if pd.isna(val) or val == "":
                            worksheet.write(row_num + 3, col_num, "", fmt)
                        else:
                            worksheet.write(row_num + 3, col_num, val, fmt)

                worksheet.set_column('A:A', 25)
                worksheet.set_column('B:D', 18)
                worksheet.set_column('E:E', 2)
                worksheet.set_column('F:H', 18)
                worksheet.set_column('I:I', 2)
                worksheet.set_column('J:L', 18)

            st.download_button(
                label=f"📥 Download {formatted_date} Status Report", 
                data=output.getvalue(),
                file_name=f"{formatted_date}_IHIP_S_P_L_Status_Report.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
    else:
        st.info("Upload S, P, and L files to begin.")
