import pandas as pd

country_code_map = {
    "EU27_2020": "European Union",
    "EA21": "Euro Area",  
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


def EU_GVA_Process(country_code_map, sector_code_map):
    url = 'https://ec.europa.eu/eurostat/api/dissemination/sdmx/3.0/data/dataflow/ESTAT/namq_10_a10/1.0?format=csvdata&compress=false&,POPTRT&c[GEO]=EU27_2020,EA21,DK,DE,IE,ES,FR,IT,NL,PL,BE,RO,FI,NO&c[UNIT]=CLV_I20&c[S_ADJ]=SCA&c[TIME_PERIOD]=ge:1997+le:2030'
    EU_GVA = pd.read_csv(url)
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
    EU_GVA["Country"] = EU_GVA["Country"].str.replace("Euro area – 21 countries (from 2026)", "Euro area", regex=False)
    EU_GVA["Country"] = EU_GVA["Country"].str.replace("European Union - 27 countries (from 2020)", "European Union", regex=False)
    return EU_GVA

def generate(current_quarter):
    # url = 'https://ec.europa.eu/eurostat/api/dissemination/sdmx/3.0/data/dataflow/ESTAT/namq_10_lp_ulc/1.0?format=csvdata&compress=false&,POPTRT&c[GEO]=EU27_2020&c[UNIT]=I20&c[S_ADJ]=SCA&c[TIME_PERIOD]=ge:1997+le:2030'
    # EU_OPH_OPW = pd.read_csv(url)
    # EU_OPH_OPW = EU_OPH_OPW.rename(columns={"TIME_PERIOD": "Quarter", "na_item": "Variable", "geo": "Country", "OBS_VALUE": "Value"})
    # EU_OPH_OPW["Quarter"] = EU_OPH_OPW["Quarter"].str.replace("-", " ", regex=False)
    # EU_OPH_OPW["Country"] = EU_OPH_OPW["Country"].replace(country_code_map)
    # EU_OPH_OPW["Variable"] = EU_OPH_OPW["Variable"].replace({"RLPR_HW": "Output Per Hour", "RLPR_PER": "Output Per Worker"})
    # EU_OPH_OPW = EU_OPH_OPW[["Quarter", "Variable", "Country", "Value"]]

    # Dataset = EU_GVA_Process(country_code_map, sector_code_map)

    # Productivity (2020=100)
    Prod_URL = "https://ec.europa.eu/eurostat/api/dissemination/sdmx/3.0/data/dataflow/ESTAT/namq_10_lp_ulc/1.0/*.*.*.*.*?c[freq]=Q&c[unit]=I20&c[s_adj]=SCA&c[na_item]=RLPR_PER,RLPR_HW&c[geo]=EU27_2020,EA21,DE,IE,ES,FR,IT,NL,PL,BE&c[TIME_PERIOD]=2026-Q2,2026-Q1,2025-Q4,2025-Q3,2025-Q2,2025-Q1,2024-Q4,2024-Q3,2024-Q2,2024-Q1,2023-Q4,2023-Q3,2023-Q2,2023-Q1,2022-Q4,2022-Q3,2022-Q2,2022-Q1,2021-Q4,2021-Q3,2021-Q2,2021-Q1,2020-Q4,2020-Q3,2020-Q2,2020-Q1,2019-Q4,2019-Q3,2019-Q2,2019-Q1,2018-Q4,2018-Q3,2018-Q2,2018-Q1&compress=false&format=csvdata&formatVersion=2.0&lang=en&labels=name"

    Productivity = pd.read_csv(Prod_URL)

    Productivity = Productivity[
        ["National accounts indicator (ESA 2010)",
        "Geopolitical entity (reporting)",
        "TIME_PERIOD",
        "OBS_VALUE"]
    ].rename(columns={
        "National accounts indicator (ESA 2010)": "Indicator",
        "Geopolitical entity (reporting)": "Country",
        "TIME_PERIOD": "Quarter",
        "OBS_VALUE": "Value"
    })

    Productivity["Indicator"] = Productivity["Indicator"].replace({
        "Real labour productivity per hour worked": "Labour productivity (per hour worked)",
        "Real labour productivity per person": "Labour productivity (per worker)"
    })

    # GVA (2020=100)
    GVA_URL = "https://ec.europa.eu/eurostat/api/dissemination/sdmx/3.0/data/dataflow/ESTAT/namq_10_a10/1.0/*.*.*.*.*.*?c[freq]=Q&c[unit]=CLV_I20&c[s_adj]=SCA&c[nace_r2]=TOTAL&c[na_item]=B1G&c[geo]=EU27_2020,EA21,DE,IE,ES,FR,IT,NL,PL,BE&c[TIME_PERIOD]=2026-Q1,2025-Q4,2025-Q3,2025-Q2,2025-Q1,2024-Q4,2024-Q3,2024-Q2,2024-Q1,2023-Q4,2023-Q3,2023-Q2,2023-Q1,2022-Q4,2022-Q3,2022-Q2,2022-Q1,2021-Q4,2021-Q3,2021-Q2,2021-Q1,2020-Q4,2020-Q3,2020-Q2,2020-Q1,2019-Q4,2019-Q3,2019-Q2,2019-Q1,2018-Q4,2018-Q3,2018-Q2,2018-Q1&compress=false&format=csvdata&formatVersion=2.0&lang=en&labels=name"

    GVA = pd.read_csv(GVA_URL)

    GVA = GVA[
        ["National accounts indicator (ESA 2010)",
        "Geopolitical entity (reporting)",
        "TIME_PERIOD",
        "OBS_VALUE"]
    ].rename(columns={
        "National accounts indicator (ESA 2010)": "Indicator",
        "Geopolitical entity (reporting)": "Country",
        "TIME_PERIOD": "Quarter",
        "OBS_VALUE": "Value"
    })

    GVA["Indicator"] = GVA["Indicator"].replace({
        "Value added, gross": "Real gross value added"
    })

    # Persons employed (2015=100)
    Persons_URL = "https://ec.europa.eu/eurostat/api/dissemination/sdmx/3.0/data/dataflow/ESTAT/namq_10_a10_e/1.0/*.*.*.*.*.*?c[freq]=Q&c[unit]=I15_PER&c[nace_r2]=TOTAL&c[s_adj]=SCA&c[na_item]=EMP_DC&c[geo]=EU27_2020,EA21,DE,IE,ES,FR,IT,NL,PL,BE&c[TIME_PERIOD]=2026-Q1,2025-Q4,2025-Q3,2025-Q2,2025-Q1,2024-Q4,2024-Q3,2024-Q2,2024-Q1,2023-Q4,2023-Q3,2023-Q2,2023-Q1,2022-Q4,2022-Q3,2022-Q2,2022-Q1,2021-Q4,2021-Q3,2021-Q2,2021-Q1,2020-Q4,2020-Q3,2020-Q2,2020-Q1,2019-Q4,2019-Q3,2019-Q2,2019-Q1,2018-Q4,2018-Q3,2018-Q2,2018-Q1&compress=false&format=csvdata&formatVersion=2.0&lang=en&labels=name"

    Persons = pd.read_csv(Persons_URL)

    Persons = Persons[
        ["Unit of measure",
        "Geopolitical entity (reporting)",
        "TIME_PERIOD",
        "OBS_VALUE"]
    ].rename(columns={
        "Unit of measure": "Indicator",
        "Geopolitical entity (reporting)": "Country",
        "TIME_PERIOD": "Quarter",
        "OBS_VALUE": "Value"
    })

    Persons["Indicator"] = Persons["Indicator"].replace({
        "Index, 2015=100 (based on persons)": "Persons employed"
    })

    # Hours worked (2015=100)
    Hours_URL = "https://ec.europa.eu/eurostat/api/dissemination/sdmx/3.0/data/dataflow/ESTAT/namq_10_a10_e/1.0/*.*.*.*.*.*?c[freq]=Q&c[unit]=I15_HW&c[nace_r2]=TOTAL&c[s_adj]=SCA&c[na_item]=EMP_DC&c[geo]=EU27_2020,EA21,DE,IE,ES,FR,IT,NL,PL,BE&c[TIME_PERIOD]=2026-Q2,2026-Q1,2025-Q4,2025-Q3,2025-Q2,2025-Q1,2024-Q4,2024-Q3,2024-Q2,2024-Q1,2023-Q4,2023-Q3,2023-Q2,2023-Q1,2022-Q4,2022-Q3,2022-Q2,2022-Q1,2021-Q4,2021-Q3,2021-Q2,2021-Q1,2020-Q4,2020-Q3,2020-Q2,2020-Q1,2019-Q4,2019-Q3,2019-Q2,2019-Q1,2018-Q4,2018-Q3,2018-Q2,2018-Q1&compress=false&format=csvdata&formatVersion=2.0&lang=en&labels=name"

    Hours = pd.read_csv(Hours_URL)

    Hours = Hours[
        ["Unit of measure",
        "Geopolitical entity (reporting)",
        "TIME_PERIOD",
        "OBS_VALUE"]
    ].rename(columns={
        "Unit of measure": "Indicator",
        "Geopolitical entity (reporting)": "Country",
        "TIME_PERIOD": "Quarter",
        "OBS_VALUE": "Value"
    })

    Hours["Indicator"] = Hours["Indicator"].replace({
        "Index, 2015=100 (based on hours worked)": "Total hours worked"
    })

    Euro_Table = pd.concat([Productivity, GVA, Persons, Hours])
    Euro_Table["Country"] = Euro_Table["Country"].replace({'European Union - 27 countries (from 2020)': "European Union",
                                                        "Euro area – 21 countries (from 2026)": "Euro Area"})

    Euro_Table["Quarter"] = pd.PeriodIndex(Euro_Table["Quarter"], freq="Q")
    Euro_Table = Euro_Table.sort_values(["Country", "Indicator", "Quarter"])

    base_2018 = (
        Euro_Table[Euro_Table["Quarter"].dt.year == 2018]
        .groupby(["Country", "Indicator"])["Value"]
        .mean()
    )

    Euro_Table["Value"] = (
        Euro_Table["Value"] /
        Euro_Table.set_index(["Country","Indicator"]).index.map(base_2018)
    ) * 100

    Euro_Table["QoQ"] = (
        Euro_Table.groupby(["Country", "Indicator"])["Value"]
        .pct_change() * 100
    )


    Euro_Table["YoY"] = (
        Euro_Table.groupby(["Country", "Indicator"])["Value"]
        .pct_change(4) * 100
    )

    baseline_2019q4 = (
        Euro_Table[Euro_Table["Quarter"] == "2019Q4"]
        .set_index(["Country", "Indicator"])["Value"]
    )

    Euro_Table["Pre_Covid"] = (
        Euro_Table["Value"]
        / Euro_Table.set_index(["Country", "Indicator"]).index.map(baseline_2019q4)
        - 1
    ) * 100


    Euro_Table = Euro_Table.round(2)
    Euro_Table = Euro_Table.drop(columns='Value')

    # Euro_Area_Table = Euro_Table[Euro_Table['Country'] == 'Euro Area']
    # quarters = pd.PeriodIndex(['2025Q4', '2025Q3', '2025Q2', '2025Q1'], freq='Q')
    # Euro_Area_Table = Euro_Area_Table[Euro_Area_Table['Quarter'].isin(quarters)]
    # Euro_Area_Table.to_excel('EU_Figures/Euro_Area_Figures.xlsx', index=False)

    # Euro_Table = Euro_Table[Euro_Table['Quarter'] == '2025Q4']
    # Euro_Table.to_excel('EU_Figures/European_Figures.xlsx', index=False)
    print(Euro_Table)
    Euro_Table.to_csv('testtesttest.csv', index=False)
    Euro_Area_Table = Euro_Table[Euro_Table['Country'] == 'Euro Area']
    print(Euro_Area_Table)

    # quarters = pd.PeriodIndex(
    #     ['2026Q1,', '2025Q4', '2025Q3', '2025Q2', '2025Q1'],  # remove
    #     freq='Q'
    # )

    initial_quarter = "2025Q1"

    quarters = pd.period_range(
        start=initial_quarter,
        end=current_quarter,
        freq="Q"
    )

    Euro_Area_Table = Euro_Area_Table[
        Euro_Area_Table['Quarter'].isin(quarters)
    ]

    European_Figures = Euro_Table[
        Euro_Table['Quarter'] == current_quarter
    ]

    with pd.ExcelWriter('scripts/EU_Figures/EU_Figures.xlsx',
                        engine='openpyxl') as writer:

        Euro_Area_Table.to_excel(
            writer,
            sheet_name='Euro Area Figures',
            index=False
        )

        European_Figures.to_excel(
            writer,
            sheet_name='EU Productivity Figures',
            index=False
        )
