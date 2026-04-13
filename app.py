import streamlit as st
import pandas as pd

st.set_page_config(page_title="IHIP Defaulter Dashboard", layout="wide")

st.title("📊 Daily IHIP Defaulter Analysis")

file = st.file_uploader("Upload IHIP Excel File", type=["xlsx"])

if file is not None:
    try:
        # Step 1: Loading data (skipping 1 row for headers)
        df = pd.read_excel(file, skiprows=1)
        
        # Cleaning column names thoroughly
        df.columns = [str(c).strip() for c in df.columns]
        
        # Finding the right columns by searching for keywords
        target_col = next((c for c in df.columns if 'Number of times Reported' in c), None)
        ward_col = next((c for c in df.columns if 'Zone' in c or 'Ward' in c), None)
        type_col = next((c for c in df.columns if 'Facility Type' in c), None)
        name_col = next((c for c in df.columns if 'Facility Name' in c), None)

        if target_col and type_col:
            # Filtering for 0 reporting
            defaulters = df[df[target_col] == 0].copy()
            
            # --- IMPROVED LOGIC FOR PRIVATE vs PUBLIC ---
            def categorize_facility(val):
                text = str(val).lower().strip()
                # जर 'private' हा शब्द कुठेही सापडला तर तो 'Private'
                if 'private' in text:
                    return 'Private'
                return 'Public'

            defaulters[type_col] = defaulters[type_col].apply(categorize_facility)

            # --- CALCULATING SUMMARY ---
            total_private = len(defaulters[defaulters[type_col] == 'Private'])
            total_public = len(defaulters[defaulters[type_col] == 'Public'])

            # Displaying Summary in a bright box
            st.success(f"📍 Summary: Total Private Defaulters: **{total_private}** | Total Public Defaulters: **{total_public}**")

            # Rename Ward Column to 'Ward'
            if ward_col:
                defaulters = defaulters.rename(columns={ward_col: 'Ward'})
            
            # Final Column selection
            final_cols = ['Ward', name_col, type_col]
            available_cols = [c for c in final_cols if c in defaulters.columns]

            if not defaulters.empty:
                st.subheader("List of Defaulter Facilities")
                # Showing the table without row numbers (index)
                st.dataframe(defaulters[available_cols], use_container_width=True, hide_index=True)
                
                # Download Button
                csv = defaulters[available_cols].to_csv(index=False).encode('utf-8')
                st.download_button("Download List as CSV", csv, "defaulters_list.csv", "text/csv")
            else:
                st.balloons()
                st.success("Great! No defaulters found today.")
        else:
            st.error("Error: Could not find 'Number of times Reported' or 'Facility Type' columns.")
            st.write("Columns found in your file:", list(df.columns))
            
    except Exception as e:
        st.error(f"Error processing file: {e}")
