# Let's create dummy datasets and output the exact files as requested.
# File 1: Defaulter Analysis .xlsm (macro-enabled workbook structure using openpyxl or just saved as .xlsm since openpyxl allows saving as .xlsm)
# File 2: Reporting Summary .csv

import pandas as pd
import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side

# Create sample data for Defaulter Analysis
defaulter_data = {
    "Sr No": [1, 2, 3, 4, 5],
    "WARD": ["Ward A", "Ward A", "Ward B", "Ward C", "Ward C"],
    "Facility Name": ["Public Clinic 1", "Private Lab X", "Dispensary 2", "General Hospital", "Health Post Y"],
    "Form Type": ["S FORM", "P FORM", "L FORM", "S FORM", "L FORM"],
    "Category": ["PUBLIC", "PRIVATE", "PUBLIC", "PUBLIC", "PUBLIC"],
    "Contact Person Name": ["John Doe", "Jane Smith", "Not Available", "Dr. Robert", "Alice Brown"],
    "Mobile Number": ["9876543210", "9123456789", "Not Available", "9811223344", "9765432109"],
    "Assigned Staff": ["Staff A", "Staff B", "Staff A", "Staff B", "Staff A"],
    "REMARK": ["", "", "", "", ""]
}
df_defaulter = pd.DataFrame(defaulter_data)

# Save as .xlsm using openpyxl
wb = openpyxl.Workbook()
ws = wb.active
ws.title = "Defaulter List"

# Styles
font_title = Font(name="Calibri", size=14, bold=True)
font_header = Font(name="Calibri", size=11, bold=True)
font_data = Font(name="Calibri", size=11)

fill_title = PatternFill(start_color="E7E6E6", end_color="E7E6E6", fill_type="solid")
fill_header = PatternFill(start_color="D9EAD3", end_color="D9EAD3", fill_type="solid")

thin_border = Border(
    left=Side(style='thin', color='A6A6A6'),
    right=Side(style='thin', color='A6A6A6'),
    top=Side(style='thin', color='A6A6A6'),
    bottom=Side(style='thin', color='A6A6A6')
)

align_center = Alignment(horizontal='center', vertical='center')

# Title rows
ws.merge_cells("A1:I1")
ws["A1"] = "IHIP Defaulter"
ws["A1"].font = font_title
ws["A1"].fill = fill_title
ws["A1"].alignment = align_center

ws.merge_cells("A2:I2")
ws["A2"] = "Daily IHIP Defaulter Analysis"
ws["A2"].font = font_title
ws["A2"].fill = fill_title
ws["A2"].alignment = align_center

# Headers
headers = list(df_defaulter.columns)
for col_num, header in enumerate(headers, 1):
    cell = ws.cell(row=3, column=col_num)
    cell.value = header
    cell.font = font_header
    cell.fill = fill_header
    cell.alignment = align_center
    cell.border = thin_border

# Data rows
for row_num, row_data in enumerate(df_defaulter.values, 4):
    for col_num, val in enumerate(row_data, 1):
        cell = ws.cell(row=row_num, column=col_num)
        cell.value = val
        cell.font = font_data
        cell.alignment = align_center
        cell.border = thin_border

# Column widths
ws.column_dimensions['A'].width = 8
ws.column_dimensions['B'].width = 15
ws.column_dimensions['C'].width = 30
ws.column_dimensions['D'].width = 15
ws.column_dimensions['E'].width = 15
ws.column_dimensions['F'].width = 25
ws.column_dimensions['G'].width = 20
ws.column_dimensions['H'].width = 20
ws.column_dimensions['I'].width = 15

xlsm_path = "Daily_IHIP_Defaulter_Analysis.xlsm"
wb.save(xlsm_path)

# Create sample data for Reporting Summary
summary_data = {
    "ward": ["Ward A", "Ward B", "Ward C", "Total", "Not Mapped"],
    "Total Reporting Units_S": [10, 8, 12, 30, 0],
    "% Of Average Reporting Units_S": [85.5, 90.0, 78.2, 84.57, 0],
    "Non Reported Units_S": [2, 1, 3, 6, 0],
    "Blank1": ["", "", "", "", ""],
    "Total Reporting Units_P": [15, 12, 18, 45, 0],
    "% Of Average Reporting Units_P": [92.1, 88.5, 95.0, 91.87, 0],
    "Non Reported Units_P": [1, 2, 0, 3, 0],
    "Blank2": ["", "", "", "", ""],
    "Total Reporting Units_L": [5, 6, 7, 18, 0],
    "% Of Average Reporting Units_L": [80.0, 85.0, 90.0, 85.0, 0],
    "Non Reported Units_L": [1, 1, 0, 2, 0]
}
df_summary = pd.DataFrame(summary_data)
csv_path = "Reporting_Summary_Status.csv"
df_summary.to_csv(csv_path, index=False)

print(f"Generated {xlsm_path} and {csv_path}")
