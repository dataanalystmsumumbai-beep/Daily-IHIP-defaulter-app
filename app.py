import streamlit as st
import pandas as pd

st.set_page_config(page_title="IHIP Defaulter Dashboard", layout="wide")

st.title("📊 Daily IHIP Defaulter Analysis")

file = st.file_uploader("Upload IHIP Excel File", type=["xlsx"])

if file is not None:
    try:
        # Step 1: Loading data (flexible on headers)
        df = pd.read_excel(file, skiprows=1)
        
        # Cleaning column names (Removing spaces and hidden characters)
        df.columns = [str(c).strip() for c in df.columns]
        
        # Finding exact column names
        target_col = next((c for c in df.columns if 'Number of times Reported' in c), None)
        ward_col = next((c for c in df.columns if 'Zone' in c or 'Ward' in c), None)
        type_col = next((c for c in df.columns if 'Facility Type' in c), None)
        name_col = next((c for c in df.columns if 'Facility Name' in c), None)

        if target_col and type_col:
            # Filtering for 0 reporting
            defaulters = df[df[target_col] == 0].copy()
            
            # --- LOGIC FOR PRIVATE vs PUBLIC ---
            # This will catch 'Private Hospital', 'Private Laboratory', etc.
            defaulters[type_col] = defaulters[type_col].apply(
                lambda x: 'Private' if 'private' in str(x).lower() else 'Public'
            )

            # --- CALCULATING SUMMARY ---
            total_private = len(defaulters[defaulters[type_col] == 'Private'])
            total_public = len(defaulters[defaulters[type_col] == 'Public'])

            # Displaying Summary in one line
            st.info(f"📍 Summary: Total Private Defaulters: **{total_private}** | Total Public Defaulters: **{total_public}**")

            # Rename Ward Column if found
            if ward_col:
                defaulters = defaulters.rename(columns={ward_col: 'Ward'})
            
            # Final Column selection
            final_cols = ['Ward', name_col, type_col]
            available_cols = [c for c in final_cols if c in defaulters.columns]

            if not defaulters.empty:
                st.subheader("List of Defaulter Facilities")
                st.table(defaulters[available_cols])
                
                # Download Button
                csv = defaulters[available_cols].to_csv(index=False).encode('utf-8')
                st.download_button("Download List as CSV", csv, "defaulters.csv", "text/csv")
            else:
                st.success("Great! Zero defaulters found today.")
        else:
            st.error("Missing columns! Please ensure 'Number of times Reported' and 'Facility Type' columns exist.")
            
    except Exception as e:
        st.error(f"Error processing file: {e}")
