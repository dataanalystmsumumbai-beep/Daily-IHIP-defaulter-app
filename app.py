import streamlit as st
import pandas as pd

st.set_page_config(page_title="IHIP Defaulter Tool", layout="wide")
st.title("Daily IHIP Defaulter Analysis")

file = st.file_uploader("Upload IHIP Excel File", type=["xlsx"])

if file is not None:
    try:
        # Step 1: Detect correct header row
        raw = pd.read_excel(file, header=None)
        header_row = 0

        for i, row in raw.iterrows():
            row_str = [str(cell).strip().lower() for cell in row]
            if any("facility name" in cell for cell in row_str):
                header_row = i
                break

        # Step 2: Load actual data
        df = pd.read_excel(file, skiprows=header_row)

        # Step 3: Clean column names
        df.columns = [str(c).replace('\n', ' ').strip() for c in df.columns]

        # Step 4: Find required columns
        def find_col(keyword):
            return next((c for c in df.columns if keyword.lower() in c.lower()), None)

        name_col = find_col('facility name')
        type_col = find_col('facility type')
        report_col = find_col('number of times reported')
        ward_col = next((c for c in df.columns if any(w in c.lower() for w in ['ward', 'zone'])), None)

        if name_col and type_col and report_col:

            # Step 5: Convert reporting column
            df[report_col] = pd.to_numeric(df[report_col], errors='coerce')

            # Step 6: Filter defaulters (0 reporting)
            defaulters = df[df[report_col].fillna(0).astype(float) == 0.0].copy()

            # Step 7: Exact mapping for Facility Type → Category
            category_map = {
                "Dispensary": "Public",
                "Government Medical College Hospital": "Public",
                "IGSL Satellite Laboratory": "Public",
                "Infectious Disease Hospital": "Public",
                "Municipal Hospital": "Public",
                "Other Government Hospitals": "Public",
                "Urban Primary Health Centre": "Public",
                "Private Hospital": "Private",
                "Private Laboratory": "Private"
            }

            defaulters['Category'] = defaulters[type_col].map(category_map).fillna("Other")

            # Step 8: Count summary
            p_count = (defaulters['Category'] == "Private").sum()
            pub_count = (defaulters['Category'] == "Public").sum()

            # Step 9: Display metrics
            col1, col2 = st.columns(2)
            col1.metric("Private Defaulters", p_count)
            col2.metric("Public Defaulters", pub_count)

            # Step 10: Prepare display columns
            show_cols = []
            if ward_col:
                defaulters = defaulters.rename(columns={ward_col: "Ward"})
                show_cols.append("Ward")

            show_cols.extend([name_col, type_col, "Category"])

            # Step 11: Display table
            if not defaulters.empty:
                st.subheader("Defaulter Facilities List")
                st.dataframe(defaulters[show_cols], use_container_width=True, hide_index=True)

                # Download option
                csv = defaulters[show_cols].to_csv(index=False).encode('utf-8')
                st.download_button("Download CSV", csv, "defaulters.csv", "text/csv")

            else:
                st.success("No defaulters found.")

        else:
            st.error("Required columns not found. Check your Excel headers.")

    except Exception as e:
        st.error(f"Error: {e}")
