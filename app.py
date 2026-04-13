import streamlit as st
import pandas as pd

st.set_page_config(page_title="IHIP Defaulter App", layout="wide")

st.title("📊 Daily IHIP Defaulter Report")

uploaded_file = st.file_uploader("Upload your Facilitywise Report (Excel)", type=["xlsx"])

if uploaded_file is not None:
    try:
        # Reading Excel - skipping the first title row
        df = pd.read_excel(uploaded_file, skiprows=1)
        
        # Cleaning column names
        df.columns = df.columns.str.strip()
        
        target_col = 'Number of times Reported'
        
        if target_col in df.columns:
            # Filtering facilities that have 0 reports
            defaulters = df[df[target_col] == 0]
            
            st.warning(f"Total Defaulters Found: {len(defaulters)}")
            
            # Columns you wanted to see
            display_cols = ['Zone/Administartive Ward Name', 'Facility Name', 'Facility Type']
            
            # Show only columns that exist in the file
            valid_cols = [c for c in display_cols if c in df.columns]
            
            if not defaulters.empty:
                st.table(defaulters[valid_cols])
            else:
                st.success("No defaulters found! All facilities have reported.")
        else:
            st.error(f"Could not find column: {target_col}")
            
    except Exception as e:
        st.error(f"An error occurred: {e}")
