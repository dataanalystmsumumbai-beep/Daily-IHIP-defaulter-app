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

# Contact File
st.subheader("Upload Contact File")
contact_file = st.file_uploader("Upload Contact Details File", type=["xlsx"])

# Staff Input
staff_input = st.text_area("Enter Staff Names (comma separated)", placeholder="A, B, C")

st.markdown("---")


def process_file(file, form_name):
    raw = pd.read_excel(file, header=None)

    header_row = 0
    for i, row in raw.iterrows():
        if "facility name" in str(row).lower():
            header_row = i
            break

    df = pd.read_excel(file, skiprows=header_row)
    df.columns = [str(c).strip() for c in df.columns]

    def find_col(keyword):
        return next((c for c in df.columns if keyword in c.lower()), None)

    name_col = find_col("facility name")
    subtype_col = find_col("facility sub-type")
    report_col = find_col("number of times reported")
    ward_col = next((c for c in df.columns if "ward" in c.lower() or "zone" in c.lower()), None)

    if not (name_col and subtype_col and report_col):
        return pd.DataFrame(), {}

    df[report_col] = pd.to_numeric(df[report_col], errors="coerce")

    defaulters = df[df[report_col].fillna(0) == 0].copy()

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

    defaulters["Category"] = defaulters[subtype_col].map(category_map).fillna("OTHER")

    counts = {
        "PUBLIC": (defaulters["Category"] == "PUBLIC").sum(),
        "PRIVATE": (defaulters["Category"] == "PRIVATE").sum()
    }

    result = pd.DataFrame()
    result["WARD"] = defaulters[ward_col].fillna("Not Mentioned") if ward_col else "Not Mentioned"
    result["Facility Name"] = defaulters[name_col]
    result["Form Type"] = form_name
    result["Category"] = defaulters["Category"]
    result["REMARK"] = ""

    return result, counts


dfs = []
form_counts = {}

if s_file:
    df_s, c = process_file(s_file, "S FORM")
    dfs.append(df_s)
    form_counts["S FORM"] = c

if p_file:
    df_p, c = process_file(p_file, "P FORM")
    dfs.append(df_p)
    form_counts["P FORM"] = c

if l_file:
    df_l, c = process_file(l_file, "L FORM")
    dfs.append(df_l)
    form_counts["L FORM"] = c


# 📊 Counts
if form_counts:
    st.markdown("## 📊 Form-wise Defaulter Category Count")
    for form, c in form_counts.items():
        c1, c2 = st.columns(2)
        c1.metric(f"{form} PUBLIC", c["PUBLIC"])
        c2.metric(f"{form} PRIVATE", c["PRIVATE"])


# 📋 Output 1
if dfs:
    final_df = pd.concat(dfs, ignore_index=True)
    final_df = final_df.sort_values(["WARD", "Facility Name"])

    st.subheader("Defaulter Facilities Combined List")
    st.dataframe(final_df, use_container_width=True)

    # 🔥 Output 2 SAFE
    merged = final_df.copy()

    if contact_file:
        contact_df = pd.read_excel(contact_file)
        contact_df.columns = [str(c).strip() for c in contact_df.columns]

        name_col = next((c for c in contact_df.columns if "facility" in c.lower()), None)
        person_col = next((c for c in contact_df.columns if "contact" in c.lower()), None)
        mobile_col = next((c for c in contact_df.columns if "mobile" in c.lower()), None)

        if name_col and person_col and mobile_col:
            merged = merged.merge(
                contact_df[[name_col, person_col, mobile_col]],
                left_on="Facility Name",
                right_on=name_col,
                how="left"
            ).drop(columns=[name_col])

            merged.rename(columns={
                person_col: "Contact Person Name",
                mobile_col: "Mobile Number"
            }, inplace=True)

    # ✅ ensure columns exist
    for col in ["Contact Person Name", "Mobile Number"]:
        if col not in merged.columns:
            merged[col] = ""

    # clean values
    merged["Contact Person Name"] = merged["Contact Person Name"].astype(str).replace(["nan", ""], "Not Available")
    merged["Mobile Number"] = merged["Mobile Number"].astype(str).replace(["nan", ""], "Not Available")

    # Assigned Staff
    if staff_input:
        staff = [s.strip() for s in staff_input.split(",") if s.strip()]
        n = len(merged)
        k = len(staff)

        if k > 0:
            block = math.ceil(n / k)
            merged["Assigned Staff"] = (staff * block)[:n]
        else:
            merged["Assigned Staff"] = ""
    else:
        merged["Assigned Staff"] = ""

    # 🔥 FINAL SAFE COLUMN ORDER
    final_columns = [
        "WARD", "Facility Name", "Form Type", "Category", "REMARK",
        "Contact Person Name", "Mobile Number", "Assigned Staff"
    ]

    for col in final_columns:
        if col not in merged.columns:
            merged[col] = ""

    merged = merged[final_columns]

    st.subheader("Defaulter List with Contact & Staff")
    st.dataframe(merged, use_container_width=True)

else:
    st.info("Upload at least one file")
