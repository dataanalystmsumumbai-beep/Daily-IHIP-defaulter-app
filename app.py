import streamlit as st
import pandas as pd

st.set_page_config(page_title="IHIP Defaulter Tool", layout="wide")
st.title("Daily IHIP Defaulter Analysis")

# ---------------- Upload ----------------
col1, col2, col3 = st.columns(3)

s_file = col1.file_uploader("S-Form", type=["xlsx"])
p_file = col2.file_uploader("P-Form", type=["xlsx"])
l_file = col3.file_uploader("L-Form", type=["xlsx"])

st.markdown("---")

contact_file = st.file_uploader("Upload Contact File", type=["xlsx"])
staff_input = st.text_input("Enter Staff Names (comma separated)")

# ---------------- PROCESS ----------------
def process_file(file, form):
    raw = pd.read_excel(file, header=None)

    header_row = 0
    for i, row in raw.iterrows():
        if "facility name" in str(row).lower():
            header_row = i
            break

    df = pd.read_excel(file, skiprows=header_row)
    df.columns = [str(c).strip() for c in df.columns]

    def find_col(k):
        return next((c for c in df.columns if k in c.lower()), None)

    name = find_col("facility name")
    subtype = find_col("facility sub-type")
    report = find_col("number of times reported")
    ward = next((c for c in df.columns if "ward" in c.lower() or "zone" in c.lower()), None)

    if not (name and subtype and report):
        return pd.DataFrame()

    df[report] = pd.to_numeric(df[report], errors="coerce")

    df = df[df[report].fillna(0) == 0].copy()

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

    df["Category"] = df[subtype].map(category_map).fillna("OTHER")

    out = pd.DataFrame()
    out["WARD"] = df[ward].fillna("Not Mentioned") if ward else "Not Mentioned"
    out["Facility Name"] = df[name]
    out["Form Type"] = form
    out["Category"] = df["Category"]
    out["REMARK"] = ""

    return out

# ---------------- MAIN ----------------
dfs = []

if s_file:
    dfs.append(process_file(s_file, "S FORM"))
if p_file:
    dfs.append(process_file(p_file, "P FORM"))
if l_file:
    dfs.append(process_file(l_file, "L FORM"))

if dfs:
    final_df = pd.concat(dfs, ignore_index=True)

    # SORT BY WARD
    final_df["WARD"] = final_df["WARD"].astype(str)
    final_df = final_df.sort_values(["WARD", "Facility Name"])

    # ---------------- OUTPUT 1 ----------------
    out1 = final_df[["WARD","Facility Name","Form Type","Category","REMARK"]]
    out1.insert(0, "Sr No", range(1, len(out1)+1))

    st.subheader("Output 1: Defaulter List")
    st.dataframe(out1, use_container_width=True)

    csv1 = out1.to_csv(index=False).encode("utf-8")
    st.download_button("Download Output 1", csv1, "output1.csv", "text/csv")

    # ---------------- OUTPUT 2 ----------------
    merged = final_df.copy()

    # CLEAN MATCH KEY
    merged["key"] = merged["Facility Name"].astype(str).str.strip().str.lower()

    if contact_file:
        cdf = pd.read_excel(contact_file)
        cdf.columns = [str(c).strip() for c in cdf.columns]

        name_c = next((c for c in cdf.columns if "facility" in c.lower()), None)
        person = next((c for c in cdf.columns if "contact" in c.lower()), None)
        mobile = next((c for c in cdf.columns if "mobile" in c.lower()), None)

        if name_c and person and mobile:
            cdf["key"] = cdf[name_c].astype(str).str.strip().str.lower()

            merged = merged.merge(
                cdf[["key", person, mobile]],
                on="key",
                how="left"
            )

            merged.rename(columns={
                person: "Contact Person Name",
                mobile: "Mobile Number"
            }, inplace=True)

    # ensure columns
    for col in ["Contact Person Name", "Mobile Number"]:
        if col not in merged.columns:
            merged[col] = ""

    merged["Contact Person Name"] = merged["Contact Person Name"].astype(str).replace(["nan",""], "Not Available")
    merged["Mobile Number"] = merged["Mobile Number"].astype(str).replace(["nan",""], "Not Available")

    # -------- ASSIGNED STAFF (BLOCK LOGIC) --------
    if staff_input:
        staff = [s.strip() for s in staff_input.split(",") if s.strip()]
        n = len(merged)
        k = len(staff)

        assigned = []

        if k > 0:
            base = n // k
            extra = n % k

            for i, s in enumerate(staff):
                count = base
                if i == k - 1:
                    count += extra
                assigned.extend([s] * count)

        merged["Assigned Staff"] = assigned
    else:
        merged["Assigned Staff"] = ""

    merged.drop(columns=["key"], inplace=True)

    cols = [
        "WARD","Facility Name","Form Type","Category","REMARK",
        "Contact Person Name","Mobile Number","Assigned Staff"
    ]

    for c in cols:
        if c not in merged.columns:
            merged[c] = ""

    out2 = merged[cols]
    out2.insert(0, "Sr No", range(1, len(out2)+1))

    st.subheader("Output 2: With Contact & Staff")
    st.dataframe(out2, use_container_width=True)

    csv2 = out2.to_csv(index=False).encode("utf-8")
    st.download_button("Download Output 2", csv2, "output2.csv", "text/csv")

else:
    st.info("Upload files to proceed")
