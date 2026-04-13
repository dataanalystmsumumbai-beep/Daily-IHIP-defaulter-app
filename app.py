import streamlit as st
import pandas as pd

st.set_page_config(page_title="IHIP Defaulter App", layout="wide")

st.title("📊 Daily IHIP Defaulter Report")
st.write("Upload your Excel file to find facilities with 0 reporting.")

file = st.file_uploader("Upload Excel File", type=["xlsx"])

if file is not None:
    try:
        # Loading file - Reading with flexibility
        df = pd.read_excel(file, skiprows=1)
        
        # Standardizing column names (removing spaces and making it clean)
        df.columns = [str(c).strip() for c in df.columns]
        
        # Defining the columns we are looking for
        # We use 'in' logic to find columns even if names are slightly different
        target_col = next((c for c in df.columns if 'Number of times Reported' in c), None)
        ward_col = next((c for c in df.columns if 'Zone/Administartive Ward' in c or 'Ward Name' in c), None)
        type_col = next((c for c in df.columns if 'Facility Type' in c), None)
        name_col = next((c for c in df.columns if 'Facility Name' in c), None)

        if target_col:
            # Filtering for 0 reporting
            defaulters = df[df[target_col] == 0].copy()
            
            # --- CUSTOM LOGIC STARTS ---
            
            # 1. Rename Ward Column to 'Ward'
            if ward_col:
                defaulters = defaulters.rename(columns={ward_col: 'Ward'})
            
            # 2. Logic for Private vs Public
            if type_col:
                defaulters[type_col] = defaulters[type_col].apply(
                    lambda x: 'Private' if 'private' in str(x).lower() else 'Public'
                )
            
            # --- CUSTOM LOGIC ENDS ---

            st.warning(f"Total Defaulters Found: {len(defaulters)}")
            
            # Final table columns
            final_cols = ['Ward', name_col, type_col]
            # Keeping only existing columns to avoid errors
            available_final_cols = [c for c in final_cols if c in defaulters.columns]
            
            if not defaulters.empty:
                st.table(defaulters[available_final_cols])
                
                # Download as CSV
                csv = defaulters[available_final_cols].to_csv(index=False).encode('utf-8')
                st.download_button("Download List as CSV", csv, "defaulters.csv", "text/csv")
            else:
                st.success("Great! No defaulters (0 reporting) found.")
        else:
            st.error("Target column 'Number of times Reported' not found. Please check your file headers.")
            st.write("Columns found in your file:", list(df.columns))
            
    except Exception as e:
        st.error(f"Something went wrong: {e}")
