import streamlit as st
import pandas as pd

st.set_page_config(page_title="Final IHIP Tool", layout="wide")

st.title("Daily IHIP Defaulter Analysis")

file = st.file_uploader("Upload IHIP Excel File", type=["xlsx"])

if file is not None:
    try:
        # 1. Scanning file to find the correct header row automatically
        raw_df = pd.read_excel(file, header=None)
        header_index = 0
        for i, row in raw_df.iterrows():
            if "Facility Name" in row.astype(str).values:
                header_index = i
                break
        
        # 2. Reading file with detected header
        df = pd.read_excel(file, skiprows=header_index)
        df.columns = [str(c).strip() for c in df.columns]

        # 3. Finding required columns
        name_col = next((c for c in df.columns if 'Facility Name' in c), None)
        type_col = next((c for c in df.columns if 'Facility Type' in c), None)
        target_col = next((c for c in df.columns if 'Number of times Reported' in c), None)
        ward_col = next((c for c in df.columns if 'Zone' in c or 'Ward' in c), None)

        if target_col and type_col:
            # Convert reporting column to numbers, invalid entries become NaN
            df[target_col] = pd.to_numeric(df[target_col], errors='coerce').fillna(0)
            
            # Filtering for 0 reporting (treating any float 0.0 or int 0 as defaulter)
            defaulters = df[df[target_col] == 0].copy()

            # 4. Strict Categorization Logic
            def get_category(val):
                s = str(val).strip().upper()
                if 'PRIVATE' in s:
                    return 'Private'
                return 'Public'

            defaulters['Category'] = defaulters[type_col].apply(get_category)

            # 5. Counts
            p_count = (defaulters['Category'] == 'Private').sum()
            pub_count = (defaulters['Category'] == 'Public').sum()

            # Display Summary Line
            st.info(f"Summary: Total Private Defaulters: {p_count} | Total Public Defaulters: {pub_count}")

            # Prepare Display Table
            if ward_col:
                defaulters = defaulters.rename(columns={ward_col: 'Ward'})
            
            display_columns = ['Ward', name_col, 'Category']
            final_cols = [c for c in display_columns if c in defaulters.columns]

            if not defaulters.empty:
                st.subheader("Defaulter List")
                st.dataframe(defaulters[final_cols], use_container_width=True, hide_index=True)
                
                # CSV Download
                csv = defaulters[final_cols].to_csv(index=False).encode('utf-8')
                st.download_button("Download CSV", csv, "defaulters.csv", "text/csv")
            else:
                st.success("No facilities with 0 reporting found.")
        else:
            st.error("Required columns not found. Please check Excel headers.")
            
    except Exception as e:
        st.error(f"System Error: {e}")
