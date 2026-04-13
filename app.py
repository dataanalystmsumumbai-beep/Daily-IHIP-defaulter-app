import streamlit as st
import pandas as pd
import math

st.set_page_config(page_title="IHIP Defaulter Tool", layout="wide")
st.title("Daily IHIP Defaulter Analysis")

st.subheader("Upload IHIP Forms")

col1, col2, col3 = st.columns(3)

col1.markdown("### S-Form")
s_file = col1.file_uploader(" ", type=["xlsx"], key="s")

col2.markdown("### P-Form")
p_file = col2.file_uploader(" ", type=["xlsx"], key="p")

col3.markdown("### L-Form")
l_file = col3.file_uploader(" ", type=["xlsx"], key="l")

st.markdown("---")

# Contact File Upload
st.subheader("Upload Contact File")
contact_file = st.file_uploader("Upload Contact Details File", type=["xlsx"], key="contact")

# Staff Input
staff_input = st.text_area("Enter Staff Names (comma separated)", placeholder="A, B, C")

st.markdown("---")


def process_file(file, form_name):
    raw = pd.read_excel(file, header=None)

    header_row = 0
    for i, row in raw.iterrows():
        row_str = [str(cell).strip().lower() for cell in row]
        if any("facility name" in cell for cell in row_str):
            header_row = i
            break

    df = pd.read_excel(file, skiprows=header_row)
    df.columns = [str(c).replace('\n', ' ').strip() for c in df.columns]

    def find_col(keyword):
        return next((c for c in df.columns if keyword.lower() in c.lower()), None)

    name_col = find_col('facility name')
    subtype_col = find_col('facility sub-type')
    report_col = find_col('number of times reported')
    ward_col = next((c for c in df.columns if any(w in c.lower() for w in ['ward', 'zone'])), None)

    if not (name_col and subtype_col and report_col):
        return pd.DataFrame(), {}

    df[report_col] = pd.to_numeric(df[report_col], errors='coerce')

    defaulters = df[df[report_col].fillna(0).astype(float) == 0.0].copy()

    category_map = {
        "Dispensary": "PUBLIC",
        "Government Medical College Hospital": "PUBLIC",
        "IGSL Satellite Laboratory": "PUBLIC",
        "Infectious Disease Hospital": "PUBLIC",
        "Municipal Hospital": "PUBLIC",
        "Other Government Hospitals": "PUBLIC",
        "Urban Primary Health Centre": "PUBLIC",
        "Health Post": "PUBLIC",
        "Health Sub Centre": "PUBLIC",
        "Private Hospital": "PRIVATE",
        "Private Laboratory": "PRIVATE"
    }

    defaulters['Category'] = defaulters[subtype_col].map(category_map).fillna("OTHER")

    public_count = (defaulters['Category'] == "PUBLIC").sum()
    private_count = (defaulters['Category'] == "PRIVATE").sum()

    counts = {"PUBLIC": public_count, "PRIVATE": private_count}

    result = pd.DataFrame()

    if ward_col:
        result["WARD"] = (
            defaulters[ward_col]
            .fillna("Not Mentioned")
            .astype(str)
            .str.strip()
            .replace("", "Not Mentioned")
        )
    else:
        result["WARD"] = "Not Mentioned"

    result["Facility Name"] = defaulters[name_col]
    result["Form Type"] = form_name
    result["Category"] = defaulters["Category"]
    result["REMARK"] = ""

    return result, counts


# Process files
dfs = []
form_counts = {}

if s_file:
    df_s, count_s = process_file(s_file, "S FORM")
    dfs.append(df_s)
    form_counts["S FORM"] = count_s

if p_file:
    df_p, count_p = process_file(p_file, "P FORM")
    dfs.append(df_p)
    form_counts["P FORM"] = count_p

if l_file:
    df_l, count_l = process_file(l_file, "L FORM")
    dfs.append(df_l)
    form_counts["L FORM"] = count_l


# 📊 Form-wise Defaulter Category Count
if form_counts:
    st.markdown("## 📊 Form-wise Defaulter Category Count")

    for form, counts in form_counts.items():
        st.markdown(f"### {form}")
        c1, c2 = st.columns(2)
        c1.metric("PUBLIC", counts["PUBLIC"])
        c2.metric("PRIVATE", counts["PRIVATE"])


# 📋 Output 1
if dfs:
    final_df = pd.concat(dfs, ignore_index=True)
    final_df = final_df.sort_values(["WARD", "Facility Name"])

    st.subheader("Defaulter Facilities Combined List")
    st.dataframe(final_df, use_container_width=True, hide_index=True)

    csv = final_df.to_csv(index=False).encode('utf-8')
    st.download_button("Download CSV", csv, "combined_defaulters.csv", "text/csv")

    # 🔥 Output 2 (Contact + Staff)
    if contact_file:
        contact_df = pd.read_excel(contact_file)
        contact_df.columns = [str(c).strip() for c in contact_df.columns]

        name_col_c = next((c for c in contact_df.columns if 'facility' in c.lower()), None)
        person_col = next((c for c in contact_df.columns if 'contact' in c.lower()), None)
        mobile_col = next((c for c in contact_df.columns if 'mobile' in c.lower()), None)

        if name_col_c and person_col and mobile_col:

            merged = final_df.merge(
                contact_df[[name_col_c, person_col, mobile_col]],
                left_on="Facility Name",
                right_on=name_col_c,
                how="left"
            )

            merged.drop(columns=[name_col_c], inplace=True)

            merged.rename(columns={
                person_col: "Contact Person Name",
                mobile_col: "Mobile Number"
            }, inplace=True)

            # Assigned Staff Logic
            if staff_input:
                staff_list = [s.strip() for s in staff_input.split(",") if s.strip()]
                n = len(merged)
                k = len(staff_list)

                if k > 0:
                    block_size = math.ceil(n / k)
                    assigned = []
                    for staff in staff_list:
                        assigned.extend([staff] * block_size)
                    merged["Assigned Staff"] = assigned[:n]
                else:
                    merged["Assigned Staff"] = ""
            else:
                merged["Assigned Staff"] = ""

            # Fill missing contacts
            merged["Contact Person Name"].fillna("Not Available", inplace=True)
            merged["Mobile Number"].fillna("Not Available", inplace=True)

            # 🔥 FINAL COLUMN ORDER FIX
            final_columns = [
                "WARD",
                "Facility Name",
                "Form Type",
                "Category",
                "REMARK",
                "Contact Person Name",
                "Mobile Number",
                "Assigned Staff"
            ]

            merged = merged[final_columns]

            st.subheader("Defaulter List with Contact & Staff")
            st.dataframe(merged, use_container_width=True, hide_index=True)

            csv2 = merged.to_csv(index=False).encode('utf-8')
            st.download_button("Download Full Data", csv2, "final_output.csv", "text/csv")

else:
    st.info("Upload at least one file to see results.")
