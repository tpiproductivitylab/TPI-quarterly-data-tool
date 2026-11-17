import pandas as pd
import numpy as np
import certifi
import ssl
from urllib.request import urlopen

country_code_map = {
    "EU27_2020": "European Union",
    "EA": "Euro Area",  
    "BE": "Belgium",
    "BG": "Bulgaria",
    "CZ": "Czechia",
    "DK": "Denmark",
    "DE": "Germany",
    "EE": "Estonia",
    "IE": "Ireland",
    "EL": "Greece",  
    "ES": "Spain",
    "FR": "France",
    "HR": "Croatia",
    "IT": "Italy",
    "CY": "Cyprus",
    "LV": "Latvia",
    "LT": "Lithuania",
    "LU": "Luxembourg",
    "HU": "Hungary",
    "MT": "Malta",
    "NL": "Netherlands",
    "AT": "Austria",
    "PL": "Poland",
    "PT": "Portugal",
    "RO": "Romania",
    "SI": "Slovenia",
    "SK": "Slovakia",
    "FI": "Finland",
    "SE": "Sweden",
    "NO": "Norway"  
}

sector_code_map = {
    "TOTAL": "Total - all NACE activities",
    "A": "Agriculture, forestry and fishing",
    "B-E": "Industry (except construction)",
    "C": "Manufacturing",
    "F": "Construction",
    "G-I": "Wholesale and retail trade, transport, accommodation and food service activities",
    "J": "Information and communication",
    "K": "Financial and insurance activities",
    "L": "Real estate activities",
    "M_N": "Professional, scientific and technical activities; administrative and support service activities",
    "O-Q": "Public administration, defence, education, human health and social work activities",
    "R-U": "Arts, entertainment and recreation; other service activities; activities of household and extra-territorial organizations and bodies"
}

pd.set_option('future.no_silent_downcasting', True)
def quarter_to_numeric(q):
    if not isinstance(q, str) or "Q" not in q:
        print(f"Unexpected format: {q}")

    try:
        year, qtr = q.split(" ")
    except:
        # Remove trailing spaces
        q = q.strip()
        year, qtr = q.split(" ")
    return int(year) + (int(qtr[1]) - 1) / 4  # Converts "1997 Q3" → 1997.5

def read_csv_from_url(url):
    ssl_context = ssl.create_default_context(cafile=certifi.where())
    with urlopen(url, context=ssl_context) as response:
        return pd.read_csv(response)

def EU_GVA_Process(country_code_map, sector_code_map):
    url = 'https://ec.europa.eu/eurostat/api/dissemination/sdmx/3.0/data/dataflow/ESTAT/namq_10_a10/1.0?format=csvdata&compress=false&,POPTRT&c[GEO]=EU27_2020,EA,DK,DE,IE,ES,FR,IT,NL,PL,RO,FI,NO&c[UNIT]=CLV_I20&c[S_ADJ]=SCA&c[TIME_PERIOD]=ge:1997+le:2030'
    EU_GVA = read_csv_from_url(url)
    # EU_GVA = pd.read_csv('../src/EU GVA with industries.csv')
    EU_GVA["TIME_PERIOD"] = EU_GVA["TIME_PERIOD"].str.replace("-", " ", regex=False)
    EU_GVA = EU_GVA[["TIME_PERIOD", "geo", "nace_r2", "OBS_VALUE"]]
    EU_GVA = EU_GVA.rename(columns={"TIME_PERIOD": "Quarter", "geo": "Country", "nace_r2": "Industry", "OBS_VALUE": "Value"})
    EU_GVA["Country"] = EU_GVA["Country"].replace(country_code_map)
    EU_GVA["Industry"] = EU_GVA["Industry"].replace(sector_code_map)
    EU_GVA["Variable"] = "GVA"
    EU_GVA["Industry"] = EU_GVA["Industry"].str.replace("Total - all NACE activities", "Total", regex=False)
    EU_GVA["Industry"] = EU_GVA["Industry"].str.replace("Wholesale and retail trade, transport, accommodation and food service activities", "Trade & Hospitality", regex=False)
    EU_GVA["Industry"] = EU_GVA["Industry"].str.replace("Financial and insurance activities", "Finance and insurance", regex=False)
    EU_GVA["Industry"] = EU_GVA["Industry"].str.replace("Real estate activities", "Real estate", regex=False)
    EU_GVA["Industry"] = EU_GVA["Industry"].str.replace("Professional, scientific and technical activities; administrative and support service activities", "Professional & Admin Services", regex=False)
    EU_GVA["Industry"] = EU_GVA["Industry"].str.replace("Public administration, defence, education, human health and social work activities", "Public Services", regex=False)
    EU_GVA["Industry"] = EU_GVA["Industry"].str.replace("Arts, entertainment and recreation; other service activities; activities of household and extra-territorial organizations and bodies", "Arts & Other Services", regex=False)
    EU_GVA["Country"] = EU_GVA["Country"].str.replace("Euro area (EA11-1999, EA12-2001, EA13-2007, EA15-2008, EA16-2009, EA17-2011, EA18-2014, EA19-2015, EA20-2023)", "Euro area", regex=False)
    EU_GVA["Country"] = EU_GVA["Country"].str.replace("European Union - 27 countries (from 2020)", "European Union", regex=False)
    return EU_GVA

def SIC_Code_Combine(dataset, letters):
    if len(letters) == 1:
        x = False
        combined = letters[0]
    else:
        x = True
        combined = "".join(letters)

    letter = letters[0]
    filtered_data = dataset.filter(like=f'Part of {letter}', axis=1)
    if filtered_data.empty:
        filtered_data = dataset.filter(like=f'{letter}', axis=1)

    filtered_data = filtered_data.copy()
    filtered_data.insert(0, 'Quarter', dataset['SIC 2007 section'])

    if x:
        for letter in letters[1:]:
            temp = dataset.filter(like=f'Part of {letter}', axis=1)
            if temp.empty:
                temp = dataset.filter(like=f'{letter}', axis=1)
            # Ensure we’re concatenating full copies
            filtered_data = pd.concat([filtered_data, temp.copy()], axis=1, ignore_index=False)

    filtered_data = filtered_data.copy()
    filtered_data.set_index("Quarter", inplace=True)

    # Perform calculations
    filtered_data["Summed"] = filtered_data.sum(axis=1)
    ref_value = filtered_data.loc[filtered_data.index.str.startswith("2022"), "Summed"].mean()
    filtered_data[f"{combined}"] = (filtered_data["Summed"] / ref_value) * 100

    return filtered_data[[f"{combined}"]]

# All data imports:
# UK
# https://www.ons.gov.uk/employmentandlabourmarket/peopleinwork/labourproductivity/datasets/outputperhourworkedbydivisionuk
UK_GVA_Division = pd.read_excel('../src/prodbydivoph.xlsx', sheet_name='Table_23', header=4)
# Data from figure 1 and 3 from https://www.ons.gov.uk/employmentandlabourmarket/peopleinwork/labourproductivity/articles/ukproductivityintroduction/julytoseptember2025andapriltojune2025
Flash_Estimate_OPH = pd.read_csv('../src/OPH Flash Estimate.csv', skiprows=7, usecols=[0,2], names=["Quarter", "Output Per Hour"])
Flash_Estimate_OPW = pd.read_csv('../src/OPW Flash Estimate.csv', skiprows=7, usecols=[0,2], names=["Quarter", "Output Per Worker"])

# US
# https://www.bls.gov/productivity/
# 'Major sectors labor productivity' in the bottom right in most requested tables
# When updating data remember to update columns used (usecols) because new quarter column will be added
US_data = pd.read_excel('../src/labor-productivity-major-sectors.xlsx', sheet_name='Quarterly', usecols='A,C,D, GW:LJ', skiprows=2)

# European data API call
url = 'https://ec.europa.eu/eurostat/api/dissemination/sdmx/3.0/data/dataflow/ESTAT/namq_10_lp_ulc/1.0?format=csvdata&compress=false&,POPTRT&c[GEO]=EU27_2020,EA,DK,DE,IE,ES,FR,IT,NL,PL,RO,FI,NO&c[UNIT]=I20&c[S_ADJ]=SCA&c[TIME_PERIOD]=ge:1997+le:2030'
#url = 'https://ec.europa.eu/eurostat/api/dissemination/sdmx/3.0/data/dataflow/ESTAT/namq_10_lp_ulc/1.0?format=csvdata&compress=false&,POPTRT&c[GEO]=EU27_2020&c[UNIT]=I20&c[S_ADJ]=SCA&c[TIME_PERIOD]=ge:1997+le:2030'
EU_OPH_OPW = read_csv_from_url(url)
EU_OPH_OPW = EU_OPH_OPW.rename(columns={"TIME_PERIOD": "Quarter", "na_item": "Variable", "geo": "Country", "OBS_VALUE": "Value"})
EU_OPH_OPW["Quarter"] = EU_OPH_OPW["Quarter"].str.replace("-", " ", regex=False)
EU_OPH_OPW["Country"] = EU_OPH_OPW["Country"].replace(country_code_map)
EU_OPH_OPW["Variable"] = EU_OPH_OPW["Variable"].replace({"RLPR_HW": "Output Per Hour", "RLPR_PER": "Output Per Worker"})
EU_OPH_OPW = EU_OPH_OPW[["Quarter", "Variable", "Country", "Value"]]

Dataset = EU_GVA_Process(country_code_map, sector_code_map)
Dataset = pd.concat([Dataset, EU_OPH_OPW])

# UK GVA
UK_GVA_Division = UK_GVA_Division.drop([0,1])
SIC_Codes = ['A', 'L', 'C', 'F', ['G', 'H', 'I'], 'J', 'K', ['M', 'N'], ['O', 'P', 'Q'], ['B', 'C', 'D', 'E']]
SIC_Codes_Dict = {'A to T (excluding imputed rental)': 'Total', 'A': 'Agriculture, forestry and fishing', 'L': 'Real estate', 'C': 'Manufacturing', 'F': 'Construction', 'GHI': 'Trade & Hospitality', 'J': 'Information and communication', 'K': 'Finance and insurance', 'MN': 'Professional & Admin Services', 'OPQ': 'Public Services', 'BCDE': 'Industry (except construction)'}
SIC_Code_Data = UK_GVA_Division.filter(like='A to T', axis=1)
SIC_Code_Data.insert(0, 'Quarter', UK_GVA_Division['SIC 2007 section'])
for code in SIC_Codes:
    temp = SIC_Code_Combine(UK_GVA_Division, code)
    SIC_Code_Data = SIC_Code_Data.merge(temp, on='Quarter', how='left')
SIC_Code_Data = SIC_Code_Data.rename(columns=SIC_Codes_Dict)
SIC_Code_Data["Year"] = SIC_Code_Data["Quarter"].str[:4].astype(int)

# Find the rebasing factor (Average of 2020 values)
base_2020 = SIC_Code_Data[SIC_Code_Data["Year"] == 2020].iloc[:, 1:-1].mean()

# Rebase all values so that 2020 = 100
SIC_Code_Data.iloc[:, 1:-1] = (SIC_Code_Data.iloc[:, 1:-1] / base_2020) * 100
SIC_Code_Data = SIC_Code_Data.drop("Year", axis=1)

# Format for long form data
SIC_Code_Data = SIC_Code_Data.melt(id_vars=["Quarter"], var_name="Industry", value_name="Value").dropna()
SIC_Code_Data["Country"] = "UK"
SIC_Code_Data["Variable"] = "GVA"

# Flash Estimate ONS Data
# OPH:
Flash_Estimate_OPH["Quarter"] = Flash_Estimate_OPH["Quarter"].str.replace(r"(Q\d) (\d{4})", r"\2 \1", regex=True)

# Change to 2020 = 100
Flash_Estimate_OPH["Year"] = Flash_Estimate_OPH["Quarter"].str[:4].astype(int)
base_2020 = Flash_Estimate_OPH[Flash_Estimate_OPH["Year"] == 2020].iloc[:, 1:-1].mean()
Flash_Estimate_OPH.iloc[:, 1:-1] = (Flash_Estimate_OPH.iloc[:, 1:-1] / base_2020) * 100
Flash_Estimate_OPH = Flash_Estimate_OPH.drop("Year", axis=1)

# OPW:
Flash_Estimate_OPW["Quarter"] = Flash_Estimate_OPW["Quarter"].str.replace(r"(Q\d) (\d{4})", r"\2 \1", regex=True)

# Change to 2020 = 100
Flash_Estimate_OPW["Year"] = Flash_Estimate_OPW["Quarter"].str[:4].astype(int)
base_2020 = Flash_Estimate_OPW[Flash_Estimate_OPW["Year"] == 2020].iloc[:, 1:-1].mean()
Flash_Estimate_OPW.iloc[:, 1:-1] = (Flash_Estimate_OPW.iloc[:, 1:-1] / base_2020) * 100
Flash_Estimate_OPW = Flash_Estimate_OPW.drop("Year", axis=1)

Flash_Estimate_Data = Flash_Estimate_OPH.merge(Flash_Estimate_OPW, on='Quarter')
Flash_Estimate_Data = Flash_Estimate_Data.melt(id_vars=["Quarter"], var_name="Variable", value_name="Value")
Flash_Estimate_Data['Country'] = 'UK'
Flash_Estimate_Data['Industry'] = 'Total'

# Import all Quarterly US productivity data since Q1 1997 (consistent with ONS data)
US_data = US_data.loc[US_data['Sector'] == 'Business sector']
US_data = US_data.loc[US_data['Units'] == 'Index (2017=100)']

# Reformat data
US_data.replace("N.A.", np.nan, inplace=True)
US_data = US_data.melt(id_vars=["Sector", "Measure", "Units"], var_name="Quarter", value_name="Value")
US_data = US_data.pivot_table(index=["Quarter"], columns="Measure", values="Value").reset_index()
US_data = US_data[["Quarter", "Real value-added output", "Output per worker", "Labor productivity"]]

US_data["Year"] = US_data["Quarter"].str[:4].astype(int)

# Find the rebasing factor (Average of 2020 values)
base_2020 = US_data[US_data["Year"] == 2020].iloc[:, 1:-1].mean()

# Rebase all values so that 2020 = 100
US_data.iloc[:, 1:-1] = (US_data.iloc[:, 1:-1] / base_2020) * 100
US_data = US_data.drop("Year", axis=1)

US_data = US_data.rename(columns={"Real value-added output": "GVA", "Output per worker": "OPW", "Labor productivity": "OPH"})
# For some reason the US data is stored as objects so you have to convert them to be stored as floats to display the data in plotly
US_data = US_data.melt(id_vars=['Quarter'], var_name='Variable', value_name='Value')
US_data["Value"] = pd.to_numeric(US_data["Value"], errors="coerce")
US_data['Country'] = 'US'
US_data = US_data[['Quarter', 'Variable', 'Country', 'Value', ]] # doesnt matter what order !

# Concatenate all data together
Dataset = pd.concat([Dataset, SIC_Code_Data, Flash_Estimate_Data, US_data])

Dataset["Variable"] = (
    Dataset['Variable']
    .replace('OPH', 'Output Per Hour')
    .replace('OPW', 'Output Per Worker')
    .replace('GVA', 'Gross Value Added'))

Dataset["Quarter"] = Dataset["Quarter"].apply(quarter_to_numeric) 
Dataset["Industry"] = Dataset["Industry"].fillna("Total")
Dataset.to_csv("../out/Long_Dataset.csv", index=False)
