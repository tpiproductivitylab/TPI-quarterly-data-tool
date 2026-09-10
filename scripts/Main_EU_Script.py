import os
import ssl
from pathlib import Path

import certifi
import pandas as pd
from EU_Scripts import EU_Line, Euro_Blog_Processing, Ireland_Adj, Sectoral_Productivity

ssl._create_default_https_context = lambda: ssl.create_default_context(cafile=certifi.where())

repo_root = Path(__file__).resolve().parent.parent
os.chdir(repo_root)

current_quarter = "2026Q2"
Ireland_Adj.generate(current_quarter)  # Makes OPH_Figures
# Euro_Blog_Processing.generate(current_quarter)  # EU Figures
# Sectoral_Productivity.generate(current_quarter)  # Makes sectoral_productivity

# EU_Line.generate() - stopped using

out_path = Path(__file__).resolve().parent / 'EU_Figures'
with pd.ExcelWriter(f"{out_path}/{current_quarter}_EU_Figures.xlsx", engine="openpyxl") as writer:

    for file in [f"{out_path}/EU_Figures.xlsx", f"{out_path}/OPH_Figures.xlsx"]:
        sheets = pd.read_excel(file, sheet_name=None)

        for sheet_name, df in sheets.items():
            df.to_excel(writer, sheet_name=sheet_name, index=False)
