# Display columns
show_cols = []

if ward_col:
    defaulters = defaulters.rename(columns={ward_col: "Ward"})
    show_cols.append("Ward")

show_cols.extend([name_col, "Category"])

# Show table
if not defaulters.empty:
    st.subheader("Defaulter Facilities List")
    st.dataframe(defaulters[show_cols], use_container_width=True, hide_index=True)

    csv = defaulters[show_cols].to_csv(index=False).encode('utf-8')
    st.download_button("Download CSV", csv, "defaulters.csv", "text/csv")

else:
    st.success("No defaulters found.")
