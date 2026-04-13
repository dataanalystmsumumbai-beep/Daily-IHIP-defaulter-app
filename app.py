import streamlit as st
import pandas as pd

# Page configuration
st.set_page_config(page_title="IHIP Defaulter Dashboard", layout="wide")

st.title("Daily IHIP Defaulter Analysis")

uploaded_file = st.file_uploader("Upload IHIP Excel File", type=["xlsx"])

if uploaded_file is not None:
    try:
        # Step 1: Automatically find the header row
        # Some files have title rows at the top. We scan for the row containing 'Facility Name'
        raw_data = pd.read_excel(uploaded_file, header=None)
        header_index = 0
        for i, row in raw_data.iterrows():
            if "Facility Name" in row.astype(str).values:
                header_index = i
                break
        
        # Step 2: Read data with the correct header
        df = pd.read_excel(uploaded_file, skiprows=header_index)
        
        # Step 3: Clean column names (remove extra spaces and newlines)
        df.columns = [str(c).strip().replace('\n', ' ') for c in df.columns]
        
        # Step 4: Identify required columns using keywords
        target_col = next((c for c in df.columns if 'Number of times Reported' in c), None)
        type_col = next((c for c in df.columns if 'Facility Type' in c), None)
        name_col = next((c for c in df.columns if 'Facility Name' in c), None)
        ward_col = next((c for c in df.columns if 'Zone' in c or 'Ward' in c), None)

        if target_col and type_col:
            # Ensure the reporting column is treated as a number
            df[target_col] = pd.to_numeric(df[target_col], errors='coerce')
            
            # Filter for facilities that have 0 reports
            defaulters = df[df[target_col] == 0].copy()
            
            # Step 5: Classification Logic based on your table
            # If the word 'private' is found anywhere in the text, it is 'Private'
            # Otherwise, it defaults to 'Public' (covers Dispensary, Municipal, UPHC, etc.)
            def categorize(val):
                clean_val = str(val).lower().strip()
                if 'private' in clean_val:
                    return 'Private'
                return 'Public'

            defaulters[type_col] = defaulters[type_col].apply(categorize)

            # Step 6: Calculate Summary Counts
            private_count = (defaulters[type_col] == 'Private').sum()
            public_count = (defaulters[type_col] == 'Public').sum()

            # Display Summary Bar
            st.info(f"Summary: Total Private Defaulters: {private_count} | Total Public Defaulters: {public_count}")

            # Rename Ward column for cleaner display
            if ward_col:
                defaulters = defaulters.rename(columns={ward_col: 'Ward'})
            
            # Prepare final table
            display_cols = ['Ward', name_col, type_col]
            available_cols = [c for c in display_cols if c in defaulters.columns]

            if not defaulters.empty:
                st.subheader("Defaulter List")
                st.dataframe(defaulters[available_cols], use_container_width=True, hide_index=True)
                
                # Download as CSV
                csv = defaulters[available_cols].to_csv(index=False).encode('utf-8')
                st.download_button("Download Report", csv, "defaulter_report.csv", "text/csv")
            else:
                st.success("No defaulters (0 reports) found in this file.")
        else:
            st.error("Could not find the required columns in your Excel file.")
            
    except Exception as e:
        st.error(f"Error processing file: {e}")
