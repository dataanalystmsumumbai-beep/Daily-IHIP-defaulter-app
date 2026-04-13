import streamlit as st
import pandas as pd

# Setting up the page
st.set_page_config(page_title="IHIP Defaulter Dashboard", layout="wide")

st.title("Daily IHIP Defaulter Analysis")

uploaded_file = st.file_uploader("Upload IHIP Excel File", type=["xlsx"])

if uploaded_file is not None:
    try:
        # Load excel and skip the first row
        df = pd.read_excel(uploaded_file, skiprows=1)
        
        # Cleaning column names for any hidden spaces
        df.columns = [str(c).strip() for c in df.columns]
        
        # Searching for necessary columns using keywords
        target_col = next((c for c in df.columns if 'Number of times Reported' in c), None)
        ward_col = next((c for c in df.columns if 'Zone' in c or 'Ward' in c), None)
        type_col = next((c for c in df.columns if 'Facility Type' in c), None)
        name_col = next((c for c in df.columns if 'Facility Name' in c), None)

        if target_col and type_col:
            # Filtering facilities with 0 reports
            defaulters = df[df[target_col] == 0].copy()
            
            # Function based on your specific table
            def categorize_facility(val):
                text = str(val).strip().lower()
                # If 'private hospital' or 'private laboratory' is found in the text
                if 'private hospital' in text or 'private laboratory' in text:
                    return 'Private'
                # All other types from your table fall under 'Public'
                return 'Public'

            # Applying the categorization logic
            defaulters[type_col] = defaulters[type_col].apply(categorize_facility)

            # Calculating Summary Counts
            private_count = (defaulters[type_col] == 'Private').sum()
            public_count = (defaulters[type_col] == 'Public').sum()

            # Displaying the summary line as requested
            st.info(f"Summary: Total Private Defaulters: {private_count} | Total Public Defaulters: {public_count}")

            # Renaming Ward column for cleaner display
            if ward_col:
                defaulters = defaulters.rename(columns={ward_col: 'Ward'})
            
            # Displaying selected columns
            display_list = ['Ward', name_col, type_col]
            final_available_cols = [c for c in display_list if c in defaulters.columns]

            if not defaulters.empty:
                st.subheader("Defaulter Facility List")
                st.dataframe(defaulters[final_available_cols], use_container_width=True, hide_index=True)
                
                # Option to download the result
                csv_data = defaulters[final_available_cols].to_csv(index=False).encode('utf-8')
                st.download_button("Download Report as CSV", csv_data, "defaulters_report.csv", "text/csv")
            else:
                st.success("No facilities with 0 reporting found.")
        else:
            st.error("Required columns missing. Please ensure your Excel has 'Number of times Reported' and 'Facility Type'.")
            
    except Exception as e:
        st.error(f"Error processing the file: {e}")
