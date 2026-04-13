import streamlit as st
import pandas as pd

st.set_page_config(page_title="IHIP Defaulter Tool", layout="wide")
st.title("📊 Daily IHIP Defaulter Analysis")

file = st.file_uploader("Upload IHIP Excel File", type=["xlsx"])

if file is not None:
    try:
        # १. योग्य हेडर शोधणे (Facility Name जिथे आहे ती ओळ शोधतो)
        raw = pd.read_excel(file, header=None)
        header_row = 0
        for i, row in raw.iterrows():
            if "Facility Name" in row.astype(str).values:
                header_row = i
                break
        
        # २. डेटा लोड करणे
        df = pd.read_excel(file, skiprows=header_row)
        
        # ३. कॉलमची नावे स्वच्छ करणे (Spaces आणि Newlines काढणे)
        df.columns = [str(c).replace('\n', ' ').strip() for c in df.columns]
        
        # ४. महत्त्वाचे कॉलम्स शोधणे
        name_col = next((c for c in df.columns if 'Facility Name' in c), None)
        type_col = next((c for c in df.columns if 'Facility Type' in c), None)
        report_col = next((c for c in df.columns if 'Number of times Reported' in c), None)
        ward_col = next((c for c in df.columns if any(w in c for w in ['Ward', 'Zone'])), None)

        if name_col and type_col and report_col:
            # ५. रिपोर्टिंग कॉलमला नंबरमध्ये बदलणे
            df[report_col] = pd.to_numeric(df[report_col], errors='coerce').fillna(-1)
            
            # ६. फक्त ० रिपोर्टिंग असणाऱ्या ओळी निवडणे
            defaulters = df[df[report_col] == 0].copy()

            # ७. 'Private' आणि 'Public' वर्गीकरण (Fuzzy Match)
            def classify(val):
                v = str(val).upper().strip()
                if "PRIVATE" in v: # Private Hospital/Laboratory साठी
                    return "Private"
                return "Public" # बाकी सर्व (Dispensary, GMC, इ.) साठी

            defaulters['Category'] = defaulters[type_col].apply(classify)

            # ८. मोजणी (Counts)
            p_count = (defaulters['Category'] == "Private").sum()
            pub_count = (defaulters['Category'] == "Public").sum()

            # ९. रिझल्ट दाखवणे
            st.info(f"📍 Summary: Total Private Defaulters: {p_count} | Total Public Defaulters: {pub_count}")

            # डिस्प्ले टेबल तयार करणे
            show_cols = []
            if ward_col:
                defaulters = defaulters.rename(columns={ward_col: "Ward"})
                show_cols.append("Ward")
            show_cols.extend([name_col, "Category"])

            if not defaulters.empty:
                st.subheader("List of Defaulter Facilities")
                st.dataframe(defaulters[show_cols], use_container_width=True, hide_index=True)
                
                csv = defaulters[show_cols].to_csv(index=False).encode('utf-8')
                st.download_button("Download CSV", csv, "defaulters.csv", "text/csv")
            else:
                st.success("No defaulters found.")
        else:
            st.error("Required columns not found. Check your Excel headers.")

    except Exception as e:
        st.error(f"Error: {e}")
