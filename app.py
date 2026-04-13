import streamlit as st
import pandas as pd

# Page configuration
st.set_page_config(page_title="IHIP Defaulter Dashboard", layout="wide")

st.title("Daily IHIP Defaulter Analysis")

uploaded_file = st.file_uploader("Upload IHIP Excel File", type=["xlsx"])

if uploaded_file is not None:
    try:
        # Read Excel - skipping 1st row for headers
        df = pd.read_excel(uploaded_file, skiprows=1)
        
        # Clean column names
        df.columns = [str(c).strip() for c in df.columns]
        
        # Identify key columns
        target_col = next((c for c in df.columns if 'Number of times Reported' in c), None)
        ward_col = next((c for c in df.columns if 'Zone' in c or 'Ward' in c), None)
        type_col = next((c for c in df.columns if 'Facility Type' in c), None)
        name_col = next((c for c in df.columns if 'Facility Name' in c), None)

        if target_col and type_col:
            # Filter rows with 0 reporting
            defaulters = df[df[target_col] == 0].copy()
            
            # Dictionary based on the table you provided
            facility_mapping = {
                'Dispensary': 'Public',
                'Government Medical College Hospital': 'Public',
                'IGSL Satellite Laboratory': 'Public',
                'Infectious Disease Hospital': 'Public',
                'Municipal Hospital': 'Public',
                'Other Government Hospitals': 'Public',
                'Private Hospital': 'Private',
                'Private Laboratory': 'Private',
                'Urban Primary Health Centre': 'Public'
            }

            def map_facility_type(val):
                cleaned_val = str(val).strip()
                # Return mapping if exists, otherwise default to 'Public'
                return facility_mapping.get(cleaned_val, 'Public')

            defaulters[type_col] = defaulters[type_col].apply(map_facility_type)

            # Summary Counts
            count_private = len(defaulters[defaulters[type_col] == 'Private'])
            count_public = len(defaulters[defaulters[type_col] == 'Public'])

            # Display Summary
            st.info(f"Summary: Total Private Defaulters: {count_private} | Total Public Defaulters: {count_public}")

            # Rename Ward Column
            if ward_col:
                defaulters = defaulters.rename(columns={ward_col: 'Ward'})
            
            # Final table setup
            display_columns = ['Ward', name_col, type_col]
            final_available = [c for c in display_columns if c in defaulters.columns]

            if not defaulters.empty:
                st.subheader("Defaulter List")
                st.dataframe(defaulters[final_available], use_container_width=True, hide_index=True)
                
                # CSV Download
                csv_data = defaulters[final_available].to_csv(index=False).encode('utf-8')
                st.download_button("Download CSV", csv_data, "defaulters.csv", "text/csv")
            else:
                st.success("No defaulters found.")
        else:
            st.error("Required columns missing in Excel.")
            
    except Exception as e:
        st.error(f"Error: {e}")
