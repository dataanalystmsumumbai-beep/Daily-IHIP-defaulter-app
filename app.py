import streamlit as st
import pandas as pd

# Basic Page Setup
st.set_page_config(page_title="IHIP Analysis", layout="wide")
st.title("Daily IHIP Defaulter Analysis")

uploaded_file = st.file_uploader("Upload IHIP Excel File", type=["xlsx"])

if uploaded_file is not None:
    try:
        # Step 1: Smart Header Detection
        # We scan for the row containing 'Facility Name' to start reading correctly
        raw_data = pd.read_excel(uploaded_file, header=None)
        header_row_index = 0
        for i, row in raw_data.iterrows():
            if "Facility Name" in row.astype(str).values:
                header_row_index = i
                break
        
        # Step 2: Read data from the detected header row
        df = pd.read_excel(uploaded_file, skiprows=header_row_index)
        
        # Clean column names (remove spaces and hidden characters)
        df.columns = [str(c).strip() for c in df.columns]

        # Step 3: Identify required columns
        name_col = next((c for c in df.columns if 'Facility Name' in c), None)
        type_col = next((c for c in df.columns if 'Facility Type' in c), None)
        report_col = next((c for c in df.columns if 'Number of times Reported' in c), None)
        ward_col = next((c for c in df.columns if 'Zone' in c or 'Ward' in c), None)

        if name_col and type_col and report_col:
            # Ensure report column is numeric and drop rows where Facility Name is empty
            df[report_col] = pd.to_numeric(df[report_col], errors='coerce')
            df = df.dropna(subset=[name_col])
            
            # Filter Defaulters (Reporting Count == 0)
            defaulters = df[df[report_col] == 0].copy()

            # Step 4: Classification Logic (Case-insensitive keyword search)
            # This covers: Private Hospital, Private Laboratory, etc.
            def classify(val):
                v = str(val).upper()
                if "PRIVATE" in v:
                    return "Private"
                return "Public"

            defaulters['Category'] = defaulters[type_col].apply(classify)

            # Step 5: Calculate Summary
            private_count = (defaulters['Category'] == "Private").sum()
            public_count = (defaulters['Category'] == "Public").sum()

            # Display Summary Line
            st.info(f"Summary: Total Private Defaulters: {private_count} | Total Public Defaulters: {public_count}")

            # Prepare Table for Display
            if ward_col:
                defaulters = defaulters.rename(columns={ward_col: "Ward"})
            
            # Select final columns to show
            final_display_cols = []
            if ward_col: final_display_cols.append("Ward")
            final_display_cols.extend([name_col, "Category"])
            
            if not defaulters.empty:
                st.subheader("List of Defaulter Facilities")
                st.dataframe(defaulters[final_display_cols], use_container_width=True, hide_index=True)
                
                # CSV Download functionality
                csv = defaulters[final_display_cols].to_csv(index=False).encode('utf-8')
                st.download_button("Download Report", csv, "defaulter_list.csv", "text/csv")
            else:
                st.success("No defaulters found in the uploaded file.")
        else:
            st.error(f"Columns missing! Found: {list(df.columns)}")

    except Exception as e:
        st.error(f"An unexpected error occurred: {e}")
