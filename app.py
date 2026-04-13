import streamlit as st
import pandas as pd

# Page setup
st.set_page_config(page_title="IHIP Defaulter App", layout="wide")

st.title("📊 Daily IHIP Defaulter Report")
st.write("Upload the Excel file to analyze reporting status.")

uploaded_file = st.file_uploader("Choose an Excel file", type=["xlsx"])

if uploaded_file is not None:
    try:
        # Reading Excel - skipping the first title row
        df = pd.read_excel(uploaded_file, skiprows=1)
        
        # Cleaning column names
        df.columns = df.columns.str.strip()
        
        target_col = 'Number of times Reported'
        ward_col = 'Zone/Administartive Ward Name'
        type_col = 'Facility Type'
        name_col = 'Facility Name'
        
        if target_col in df.columns:
            # Filtering facilities that have 0 reports
            defaulters = df[df[target_col] == 0].copy()
            
            # --- APPLYING YOUR REQUESTED CHANGES ---
            
            # 1. Rename 'Zone/Administartive Ward Name' to 'Ward'
            if ward_col in defaulters.columns:
                defaulters = defaulters.rename(columns={ward_col: 'Ward'})
            
            # 2. Change Facility Type logic: 'Private' if it contains Private, else 'Public'
            if type_col in defaulters.columns:
                defaulters[type_col] = defaulters[type_col].apply(
                    lambda x: 'Private' if 'private' in str(x).lower() else 'Public'
                )
            
            # ---------------------------------------

            st.warning(f"Total Defaulters Found: {len(defaulters)}")
            
            # Final columns to show
            final_display_cols = ['Ward', name_col, type_col]
            
            # Filter only those columns that actually exist now
            show_cols = [c for c in final_display_cols if c in defaulters.columns]
            
            if not defaulters.empty:
                st.table(defaulters[show_cols])
                
                # Download Option
                csv = defaulters[show_cols].to_csv(index=False).encode('utf-8')
                st.download_button("Download Defaulter List", csv, "defaulters.csv", "text/csv")
            else:
                st.success("No defaulters found! All facilities have reported.")
        else:
            st.error(f"Could not find column: {target_col}")
            
    except Exception as e:
        st.error(f"An error occurred: {e}")
