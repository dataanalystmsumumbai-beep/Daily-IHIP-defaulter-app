import streamlit as st
import pandas as pd
import re

# Page configuration
st.set_page_config(page_title="IHIP Defaulter Analysis", layout="wide")

st.title("Daily IHIP Defaulter Analysis")

uploaded_file = st.file_uploader("Upload IHIP Excel File", type=["xlsx"])

if uploaded_file is not None:
    try:
        # Step 1: Find the header row by searching for 'Facility Name'
        raw_df = pd.read_excel(uploaded_file, header=None)
        header_row = 0
        for i, row in raw_df.iterrows():
            if "Facility Name" in row.astype(str).values:
                header_row = i
                break
        
        # Step 2: Load data with the identified header
        df = pd.read_excel(uploaded_file, skiprows=header_row)
        
        # Clean column names: remove newlines, extra spaces, and convert to lowercase for searching
        df.columns = [re.sub(r'\s+', ' ', str(c)).strip() for c in df.columns]
        
        # Step 3: Map the necessary columns using partial matches
        col_map = {
            'target': next((c for c in df.columns if 'Number of times Reported' in c), None),
            'type': next((c for c in df.columns if 'Facility Type' in c), None),
            'name': next((c for c in df.columns if 'Facility Name' in c), None),
            'ward': next((c for c in df.columns if any(x in c for x in ['Ward', 'Zone'])), None)
        }

        if col_map['target'] and col_map['type']:
            # Step 4: Data Cleaning
            # Convert reporting column to numeric; non-numeric values become NaN
            df[col_map['target']] = pd.to_numeric(df[col_map['target']], errors='coerce')
            
            # Filter for defaulters (reported == 0) and remove empty facility rows
            defaulters = df[df[col_map['target']] == 0].dropna(subset=[col_map['name']]).copy()

            # Step 5: Classification Logic
            # We use a case-insensitive search for the word 'PRIVATE'
            def categorize(val):
                text = str(val).strip().upper()
                if "PRIVATE" in text:
                    return "Private"
                return "Public"

            defaulters['Category'] = defaulters[col_map['type']].apply(categorize)

            # Step 6: Calculations
            private_count = (defaulters['Category'] == "Private").sum()
            public_count = (defaulters['Category'] == "Public").sum()

            # Display Summary
            st.info(f"Summary: Total Private Defaulters: {private_count} | Total Public Defaulters: {public_count}")

            # Prepare the display table
            display_cols = []
            if col_map['ward']:
                defaulters = defaulters.rename(columns={col_map['ward']: "Ward"})
                display_cols.append("Ward")
            
            display_cols.extend([col_map['name'], "Category"])

            if not defaulters.empty:
                st.subheader("Defaulter Facility List")
                st.dataframe(defaulters[display_cols], use_container_width=True, hide_index=True)
                
                # Download Link
                csv = defaulters[display_cols].to_csv(index=False).encode('utf-8')
                st.download_button("Download Data as CSV", csv, "defaulters.csv", "text/csv")
            else:
                st.success("No facilities with 0 reports were found.")
        else:
            st.error("Error: Could not identify 'Facility Type' or 'Reporting' columns in the Excel file.")
            
    except Exception as e:
        st.error(f"Application Error: {e}")
