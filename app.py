# ---------------- OUTPUT 3 (WARD COMPARISON MODULE) ----------------

st.markdown("## Ward Wise Comparison (S / P / L Forms)")

# Date input for Output 3
output3_date = st.text_input("Enter Output 3 Date (DD-MM-YYYY)", "13-04-2026")

# ---------------- PROCESS FUNCTION ----------------
def process_simple(file, form_prefix):
    df = pd.read_excel(file)

    df.columns = [str(c).strip() for c in df.columns]

    ward_col = next((c for c in df.columns if "ward" in c.lower()), None)
    report_col = next((c for c in df.columns if "report" in c.lower()), None)

    if not ward_col:
        return pd.DataFrame()

    df = df[[ward_col]].copy()
    df.columns = [f"{form_prefix}_Ward"]

    df[f"{form_prefix}_Ward"] = df[f"{form_prefix}_Ward"].fillna("Not Mentioned")

    # Sorting A-Z
    df = df.sort_values(by=f"{form_prefix}_Ward")

    return df.reset_index(drop=True)

# ---------------- RUN ONLY IF FILES UPLOADED ----------------
if s_file and p_file and l_file:

    s_df = process_simple(s_file, "S")
    p_df = process_simple(p_file, "P")
    l_df = process_simple(l_file, "L")

    # ---------------- ALIGN ROW LENGTHS ----------------
    max_len = max(len(s_df), len(p_df), len(l_df))

    s_df = s_df.reindex(range(max_len)).fillna("")
    p_df = p_df.reindex(range(max_len)).fillna("")
    l_df = l_df.reindex(range(max_len)).fillna("")

    # ---------------- BLANK COLUMNS ----------------
    blank1 = pd.DataFrame([""] * max_len, columns=[""])
    blank2 = pd.DataFrame([""] * max_len, columns=[""])

    # ---------------- FINAL MERGE (9 COLUMNS) ----------------
    output3 = pd.concat([s_df, blank1, p_df, blank2, l_df], axis=1)

    # Sr No
    output3.insert(0, "Sr No", range(1, len(output3) + 1))

    # ---------------- DISPLAY ----------------
    st.subheader("Output 3 - Ward Wise Comparison")
    st.dataframe(output3, use_container_width=True)

    # ---------------- EXCEL EXPORT ----------------
    def generate_output3_excel(df):
        output = BytesIO()

        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, index=False, startrow=2)

            ws = writer.sheets['Sheet1']

            ws.merge_cells('A1:I1')
            ws['A1'] = "Ward Wise Comparison Report (S / P / L)"

            ws.merge_cells('A2:I2')
            ws['A2'] = f"Date: {output3_date}"

        return output.getvalue()

    st.download_button(
        "Download Output 3 Excel",
        generate_output3_excel(output3),
        "output3.xlsx"
    )

else:
    st.info("Upload S, P, L files to generate Output 3")
