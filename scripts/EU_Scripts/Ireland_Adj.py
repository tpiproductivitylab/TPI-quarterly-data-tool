import pandas as pd
import plotly.graph_objects as go
import plotly.express as px

def plot_productivity(country_productivity, EuroZone_Productivity, key_countries):

    EUROZONE_ADJUSTED = 'Euro Area Adjusted'

    ez_adj = EuroZone_Productivity.copy()
    ez_adj['Country'] = EUROZONE_ADJUSTED

    countries = country_productivity[country_productivity['Country'].isin(key_countries)].copy()

    prod = pd.concat([
        ez_adj[['Country', 'Quarter', 'output_per_hour']].rename(
            columns={'output_per_hour': 'Value'}
        ),
        countries[['Country', 'Quarter', 'productivity']].rename(
            columns={'productivity': 'Value'}
        ),
    ])
    base = prod[prod['Quarter'].dt.year == 2010].groupby('Country')['Value'].mean()
    prod['Value'] = prod.apply(lambda row: (row['Value'] / base[row['Country']]) * 100, axis=1)

    tickvals = prod[prod['Quarter'].dt.quarter == 2]['Quarter'].dt.to_timestamp().unique()
    prod['Quarter'] = prod['Quarter'].dt.to_timestamp()

    fig = px.line(
        prod,
        x='Quarter',
        y='Value',
        color='Country',
    )

    fig.update_layout(
        # title='Output per Hour Worked',
        hovermode='closest',
        legend_title=None,
        xaxis_title=None,
        yaxis_title=None,
        template='plotly_white'
    )
    fig.update_xaxes(
        dtick="M3",
        tickformat="%Y-Q%q"
    )

    for trace in fig.data:
        trace.hovertemplate = (
            "<b>%{fullData.name}</b><br>"
            "Quarter: %{x|%Y-Q%q}<br>"
            "Index: %{y:.1f}<br>"
            "<extra></extra>"
        )
    fig.update_xaxes(tickvals=tickvals, tickformat="%Y-Q%q")
    return fig 

def apply_employment_growth_to_hours(EuroZone_Hours_raw, employment_df, countries, base_quarter, target_quarter):
    """
    For countries with missing/unreliable Hours-worked data (e.g. Luxembourg,
    Belgium), estimate the target quarter's Hours by scaling the last known
    Hours value by the growth rate in persons employed between base_quarter
    and target_quarter.

    employment_df must have columns: Country, Quarter (PeriodIndex, freq='Q'), Employment
    """
    df = EuroZone_Hours_raw.copy()

    for country in countries:
        emp_base = employment_df.loc[
            (employment_df["Country"] == country) & (employment_df["Quarter"] == base_quarter),
            "Employment"
        ]
        emp_target = employment_df.loc[
            (employment_df["Country"] == country) & (employment_df["Quarter"] == target_quarter),
            "Employment"
        ]

        if emp_base.empty or emp_target.empty:
            print(f"[WARNING] Missing employment data for {country} in {base_quarter} or {target_quarter} — skipping")
            continue

        growth_rate = emp_target.values[0] / emp_base.values[0]

        hours_base = df.loc[
            (df["Country"] == country) & (df["Quarter"] == base_quarter),
            "Hours"
        ]

        if hours_base.empty:
            print(f"[WARNING] No existing Hours value for {country} in {base_quarter} — cannot extrapolate")
            continue

        estimated_hours = hours_base.values[0] * growth_rate

        # Drop any existing row for the target quarter (in case it's a placeholder/NaN), then add the estimate
        df = df[~((df["Country"] == country) & (df["Quarter"] == target_quarter))]

        new_row = pd.DataFrame({
            "Country": [country],
            "Quarter": [target_quarter],
            "Hours": [estimated_hours]
        })
        df = pd.concat([df, new_row], ignore_index=True)

        print(
            f"[{country}] employment growth {base_quarter}->{target_quarter}: "
            f"{(growth_rate - 1) * 100:.2f}% -> estimated Hours: {estimated_hours:.2f}"
        )

    return df

def apply_persons_index_to_missing_persons(
    EuroZone_Persons_raw,
    EuroZone_Persons_Index_raw,
    base_quarter,
    target_quarter
):
    """
    For countries with missing persons-employed data in the target quarter,
    estimate persons employed by scaling the last known persons-employed
    value by the growth rate in the persons-employed index.

    EuroZone_Persons_raw must have columns:
    Country, Quarter, Persons

    EuroZone_Persons_Index_raw must have columns:
    Country, Quarter, Persons_Index
    """

    df = EuroZone_Persons_raw.copy()

    # Only estimate countries where the target-quarter persons data is missing
    countries = df.loc[
        ~df["Country"].isin(
            df.loc[
                df["Quarter"] == target_quarter,
                "Country"
            ]
        ),
        "Country"
    ].unique()

    for country in countries:

        # Persons employed in the base quarter
        persons_base = df.loc[
            (df["Country"] == country) &
            (df["Quarter"] == base_quarter),
            "Persons"
        ]

        if persons_base.empty:
            print(
                f"[WARNING] No existing Persons value for {country} "
                f"in {base_quarter} — cannot extrapolate"
            )
            continue

        # Index in base quarter
        index_base = EuroZone_Persons_Index_raw.loc[
            (EuroZone_Persons_Index_raw["Country"] == country) &
            (EuroZone_Persons_Index_raw["Quarter"] == base_quarter),
            "Persons_Index"
        ]

        # Index in target quarter
        index_target = EuroZone_Persons_Index_raw.loc[
            (EuroZone_Persons_Index_raw["Country"] == country) &
            (EuroZone_Persons_Index_raw["Quarter"] == target_quarter),
            "Persons_Index"
        ]

        if index_base.empty or index_target.empty:
            print(
                f"[WARNING] Missing persons index data for {country} "
                f"in {base_quarter} or {target_quarter} — skipping"
            )
            continue

        # Growth implied by the persons-employed index
        growth_rate = index_target.values[0] / index_base.values[0]

        # Estimate target-quarter persons employed
        estimated_persons = persons_base.values[0] * growth_rate

        # Add the estimated target-quarter value
        new_row = pd.DataFrame({
            "Country": [country],
            "Quarter": [target_quarter],
            "Persons": [estimated_persons]
        })

        df = pd.concat([df, new_row], ignore_index=True)

        print(
            f"[{country}] persons index growth {base_quarter}->{target_quarter}: "
            f"{(growth_rate - 1) * 100:.2f}% "
            f"-> estimated Persons: {estimated_persons:.2f}"
        )

    return df

def backfill_missing_countries(df, value_col, label=""):
    """
    Some countries occasionally drop out of the latest Eurostat release
    before trickling back in on a later refresh. This backfills any country
    present in the previous quarter but missing from the latest quarter,
    using that country's previous-quarter value.

    IMPORTANT: this must be run independently on every GVA/Hours frame that
    feeds into a total (e.g. both `merged` and `merged_IE`) using each
    frame's own latest/previous quarter and country set. Previously this was
    only computed once (on `merged`) and re-used implicitly, so `merged_IE`
    never got backfilled — silently understating the unadjusted Eurozone
    total whenever a non-Ireland country was missing from the latest quarter.
    """
    latest = df["Quarter"].max()
    previous = latest - 1

    latest_countries = set(df.loc[df["Quarter"] == latest, "Country"])
    previous_countries = set(df.loc[df["Quarter"] == previous, "Country"])
    missing = previous_countries - latest_countries

    print(f"\n[{label}] latest quarter: {latest}")
    print(f"[{label}] previous quarter: {previous}")
    print(f"[{label}] countries missing from latest: {missing}")

    for country in missing:
        prev_val = df[
            (df["Country"] == country) &
            (df["Quarter"] == previous)
        ][value_col].values[0]

        new_row = pd.DataFrame({
            "Country": [country],
            "Quarter": [latest],
            value_col: [prev_val]
        })
        df = pd.concat([df, new_row], ignore_index=True)

    return df


def per_country(merged, merged_IE, Ireland_GVA, EuroZone_Hours_raw, EuroZone_Productivity, EuroZone_Productivity_IE):

    # Unadjusted — Eurostat Ireland as-is
    country_unadj = pd.merge(
        merged_IE,
        EuroZone_Hours_raw[["Country", "Quarter", "Hours"]],
        on=["Country", "Quarter"],
        how="inner"
    )

    # Adjusted — swap Ireland for CSO version, label separately
    ireland_adj = Ireland_GVA[["Country", "Quarter", "Value"]].copy()
    ireland_adj["Country"] = "Ireland_Adjusted"

    # Save Ireland GVA comparison
    ireland_unadj = merged_IE[
        merged_IE["Country"] == "Ireland"
    ][["Quarter", "Value"]].copy()

    ireland_unadj = ireland_unadj.rename(columns={
        "Value": "Unadjusted_GVA"
    })

    ireland_adj_csv = Ireland_GVA[
        ["Quarter", "Value"]
    ].copy()

    ireland_adj_csv = ireland_adj_csv.rename(columns={
        "Value": "Adjusted_GVA"
    })

    ireland_gva_comparison = pd.merge(
        ireland_unadj,
        ireland_adj_csv,
        on="Quarter",
        how="outer"
    )

    ireland_gva_comparison.to_csv(
        "scripts/EU_Figures/ireland_gva_comparison.csv",
        index=False
    )

    gva_adjusted = pd.concat([
        merged_IE[merged_IE["Country"] != "Ireland"],
        ireland_adj
    ])

    hours_adj = EuroZone_Hours_raw.copy()
    hours_adj.loc[hours_adj["Country"] == "Ireland", "Country"] = "Ireland_Adjusted"

    country_adj = pd.merge(
        gva_adjusted,
        hours_adj[["Country", "Quarter", "Hours"]],
        on=["Country", "Quarter"],
        how="inner"
    )

    combined = pd.concat([
        country_adj,
        country_unadj[country_unadj["Country"] == "Ireland"]
    ], ignore_index=True)

    combined["productivity"] = (combined["Value"] / combined["Hours"]) * 1000
    combined = combined.sort_values(["Country", "Quarter"]).reset_index(drop=True)
    combined["QoQ"] = combined.groupby("Country")["productivity"].pct_change() * 100
    combined["YoY"] = combined.groupby("Country")["productivity"].pct_change(4) * 100
    combined = combined[["Country", "Quarter", "productivity", "QoQ", "YoY"]]

    # Aggregate Eurozone rows
    ez_adj = EuroZone_Productivity[["Quarter", "output_per_hour", "output_per_hour_QoQ", "output_per_hour_YoY"]].copy()
    ez_adj["Country"] = "Eurozone_Adjusted"

    # NOTE: EuroZone_Productivity_IE's productivity columns are now named
    # output_per_hour / output_per_hour_QoQ / output_per_hour_YoY to match
    # EuroZone_Productivity's naming convention (previously productivity/QoQ/YoY).
    ez_unadj = EuroZone_Productivity_IE[["Quarter", "output_per_hour", "output_per_hour_QoQ", "output_per_hour_YoY"]].copy()
    ez_unadj["Country"] = "Eurozone"

    combined = pd.concat([
        combined,
        ez_adj[["Country", "Quarter", "output_per_hour", "output_per_hour_QoQ", "output_per_hour_YoY"]],
        ez_unadj[["Country", "Quarter", "output_per_hour", "output_per_hour_QoQ", "output_per_hour_YoY"]]
    ]).sort_values(["Country", "Quarter"]).reset_index(drop=True)

    return combined.round(2)


def generate(current_quarter):
    employment_df = pd.read_csv('scripts/EU_persons.csv')[['geo', 'TIME_PERIOD', 'OBS_VALUE']].rename(columns={
        'geo': 'Country',
        'TIME_PERIOD': 'Quarter',
        'OBS_VALUE': 'Employment'
    })
    employment_df['Quarter'] = pd.PeriodIndex(employment_df['Quarter'], freq='Q')
    print(employment_df)

    Ireland_GVA = pd.read_csv('https://ws.cso.ie/public/api.restful/PxStat.Data.Cube_API.ReadDataset/NAQ06/CSV/1.0/en', usecols=["STATISTIC","Statistic Label","TLIST(Q1)","Quarter","C02937V03552","Sector","UNIT","VALUE"])

    Ireland_GVA = Ireland_GVA[
        Ireland_GVA['Sector'] == 'Other sectors excluding the foreign-owned multinational enterprise dominated sector'
    ]
    Ireland_GVA = Ireland_GVA[
        Ireland_GVA['Statistic Label'] == 'GVA at Current Basic Prices (Seasonally Adjusted)'
    ]
    Ireland_GVA = Ireland_GVA[['Quarter', 'VALUE']].rename(columns={'VALUE': 'nominal_value'})
    Ireland_GVA["Quarter"] = pd.PeriodIndex(Ireland_GVA["Quarter"], freq="Q")
    Ireland_GVA = Ireland_GVA.sort_values("Quarter").reset_index(drop=True)

    # Extended TIME_PERIOD back to 2010-Q1
    EuroZone_URL = 'https://ec.europa.eu/eurostat/api/dissemination/sdmx/3.0/data/dataflow/ESTAT/namq_10_gdp/1.0/*.*.*.*.*?c[freq]=Q&c[unit]=CP_MEUR,PD20_EUR&c[s_adj]=SCA&c[na_item]=B1G&c[geo]=BE,BG,DE,EE,IE,EL,ES,FR,HR,IT,CY,LV,LT,LU,MT,NL,AT,PT,SI,SK,FI&c[TIME_PERIOD]=ge:2010-Q1&compress=false&format=csvdata&formatVersion=2.0&lang=en&labels=name'
    EuroZone = pd.read_csv(EuroZone_URL)
    EuroZone = EuroZone[['Unit of measure', 'Geopolitical entity (reporting)', 'TIME_PERIOD', 'OBS_VALUE']].rename(columns={
        'Geopolitical entity (reporting)': "Country",
        'TIME_PERIOD': 'Quarter',
        'OBS_VALUE': 'Value'
    })
    EuroZone["Quarter"] = pd.PeriodIndex(EuroZone["Quarter"], freq="Q")

    nominal = EuroZone[EuroZone["Unit of measure"] == "Current prices, million euro"].rename(columns={"Value": "nominal_gva"})
    deflator = EuroZone[EuroZone["Unit of measure"] == "Price index (implicit deflator), 2020=100, euro"].rename(columns={"Value": "deflator"})

    # Get Ireland's Eurostat deflator to apply to the CSO adjusted Ireland GVA
    ireland_deflator = deflator[deflator["Country"] == "Ireland"][["Quarter", "deflator"]]

    Ireland_GVA = pd.merge(Ireland_GVA, ireland_deflator, on="Quarter", how="inner")
    Ireland_GVA["Value"] = (Ireland_GVA["nominal_value"] / Ireland_GVA["deflator"]) * 100
    Ireland_GVA = Ireland_GVA[
        (Ireland_GVA["Quarter"] >= "2010Q1") &
        (Ireland_GVA["Quarter"] <= current_quarter)
    ]
    Ireland_GVA['Country'] = 'Ireland'
    Ireland_GVA = Ireland_GVA[['Country', 'Quarter', 'Value']]

    # base_2020 = Ireland_GVA[Ireland_GVA["Quarter"].dt.year == 2020]["Value"].mean()
    # base_2023 = Ireland_GVA[Ireland_GVA["Quarter"].dt.year == 2023]["Value"].mean()
    # scale_factor = base_2020 / base_2023

    # Ireland_GVA["Value"] = Ireland_GVA["Value"] * scale_factor
    Ireland_GVA = Ireland_GVA[
        (Ireland_GVA["Quarter"] >= "2010Q1") &
        (Ireland_GVA["Quarter"] <= current_quarter)
    ]
    Ireland_GVA['Country'] = 'Ireland'
    Ireland_GVA = Ireland_GVA[['Country', 'Quarter', 'Value']]
    print("Ireland GVA:")
    print(Ireland_GVA)

    merged = pd.merge(
        nominal[["Country", "Quarter", "nominal_gva"]],
        deflator[["Country", "Quarter", "deflator"]],
        on=["Country", "Quarter"],
        how="inner"
    )
    merged["Value"] = (merged["nominal_gva"] / merged["deflator"]) * 100
    merged = merged[merged["Country"] != "Ireland"]
    merged = merged[['Country', 'Quarter', 'Value']]
    print("\nGVA country counts before:")
    print(merged.groupby("Quarter")["Country"].nunique())

    # Backfill any country missing from the latest quarter (adjusted / merged)
    merged = backfill_missing_countries(merged, "Value", label="merged (adjusted GVA)")

    print("\nGVA country counts after:")
    print(merged.groupby("Quarter")["Country"].nunique())

    EuroZone_GVA = pd.concat([Ireland_GVA, merged]).groupby("Quarter")["Value"].sum().reset_index().rename(columns={"Value": "GVA"})

    # Extended TIME_PERIOD back to 2010-Q1
    Hours_URL = 'https://ec.europa.eu/eurostat/api/dissemination/sdmx/3.0/data/dataflow/ESTAT/namq_10_a10_e/1.0/*.*.*.*.*.*?c[freq]=Q&c[unit]=THS_HW&c[nace_r2]=TOTAL&c[s_adj]=SCA&c[na_item]=EMP_DC&c[geo]=BE,BG,DE,EE,IE,EL,ES,FR,HR,IT,CY,LV,LT,LU,MT,NL,AT,PT,SI,SK,FI&c[TIME_PERIOD]=ge:2010-Q1&compress=false&format=csvdata&formatVersion=2.0&lang=en&labels=name'
    EuroZone_Hours_raw = pd.read_csv(Hours_URL)[['Geopolitical entity (reporting)', 'TIME_PERIOD', 'OBS_VALUE']].rename(columns={
        'Geopolitical entity (reporting)': "Country",
        'TIME_PERIOD': 'Quarter',
        'OBS_VALUE': 'Hours'
    })
    EuroZone_Hours_raw["Quarter"] = pd.PeriodIndex(EuroZone_Hours_raw["Quarter"], freq="Q")

    # print("Before:")
    # print(EuroZone_Hours_raw.groupby("Quarter")["Country"].nunique())
    EuroZone_Hours_raw = apply_employment_growth_to_hours(
        EuroZone_Hours_raw,
        employment_df,
        countries=['Belgium', 'Luxembourg'],
        base_quarter=pd.Period('2026Q1', freq='Q'),
        target_quarter=pd.Period('2026Q2', freq='Q')
    )

    # Backfill any country missing from the latest quarter (Hours)
    # EuroZone_Hours_raw = backfill_missing_countries(EuroZone_Hours_raw, "Hours", label="EuroZone_Hours_raw")

    # print("After:")
    # print(EuroZone_Hours_raw.groupby("Quarter")["Country"].nunique())

    EuroZone_Hours = EuroZone_Hours_raw.groupby("Quarter")["Hours"].sum().reset_index()

    Persons_URL = 'https://ec.europa.eu/eurostat/api/dissemination/sdmx/3.0/data/dataflow/ESTAT/namq_10_a10_e/1.0/*.*.*.*.*.*?c[freq]=Q&c[unit]=THS_PER&c[nace_r2]=TOTAL&c[s_adj]=SCA&c[na_item]=EMP_DC&c[geo]=EA21&c[TIME_PERIOD]=ge:2010-Q1&compress=false&format=csvdata&formatVersion=2.0&lang=en&labels=name'

    EuroZone_Persons_raw = pd.read_csv(Persons_URL)[
        ['Geopolitical entity (reporting)', 'TIME_PERIOD', 'OBS_VALUE']
    ].rename(columns={
        'Geopolitical entity (reporting)': "Country",
        'TIME_PERIOD': 'Quarter',
        'OBS_VALUE': 'Persons'
    })

    EuroZone_Persons_raw["Quarter"] = pd.PeriodIndex(
        EuroZone_Persons_raw["Quarter"],
        freq="Q"
    )

    EuroZone_Productivity = pd.merge(
        EuroZone_GVA,
        EuroZone_Hours,
        on="Quarter"
    )

    EuroZone_Productivity = pd.merge(
        EuroZone_Productivity,
        EuroZone_Persons_raw.groupby("Quarter")["Persons"].sum().reset_index(),
        on="Quarter"
    )
    EuroZone_Productivity = (
            EuroZone_Productivity
            .sort_values("Quarter")
            .reset_index(drop=True)
        )
    

    EuroZone_Productivity["output_per_hour"] = (
        EuroZone_Productivity["GVA"] /
        EuroZone_Productivity["Hours"]
    ) * 1000

    EuroZone_Productivity["output_per_hour_QoQ"] = (
        EuroZone_Productivity["output_per_hour"].pct_change() * 100
    )

    EuroZone_Productivity["output_per_hour_YoY"] = (
        EuroZone_Productivity["output_per_hour"].pct_change(4) * 100
    )
    

    EuroZone_Productivity["output_per_worker"] = (
        EuroZone_Productivity["GVA"] /
        EuroZone_Productivity["Persons"]
    ) * 1000

    EuroZone_Productivity["output_per_worker_QoQ"] = (
        EuroZone_Productivity["output_per_worker"].pct_change() * 100
    )


    EuroZone_Productivity["output_per_worker_YoY"] = (
        EuroZone_Productivity["output_per_worker"].pct_change(4) * 100
    )

    q4_2019 = EuroZone_Productivity[
        EuroZone_Productivity["Quarter"] == pd.Period("2019Q4")
    ].iloc[0]

    EuroZone_Productivity["output_per_hour_vs_Q4_2019"] = (
        EuroZone_Productivity["output_per_hour"] /
        q4_2019["output_per_hour"] - 1
    ) * 100

    EuroZone_Productivity["output_per_worker_vs_Q4_2019"] = (
        EuroZone_Productivity["output_per_worker"] /
        q4_2019["output_per_worker"] - 1
    ) * 100

    # QoQ
    EuroZone_Productivity["GVA_QoQ"] = (
        EuroZone_Productivity["GVA"].pct_change() * 100
    )

    EuroZone_Productivity["Hours_QoQ"] = (
        EuroZone_Productivity["Hours"].pct_change() * 100
    )

    EuroZone_Productivity["Persons_QoQ"] = (
        EuroZone_Productivity["Persons"].pct_change() * 100
    )

    # YoY
    EuroZone_Productivity["GVA_YoY"] = (
        EuroZone_Productivity["GVA"].pct_change(4) * 100
    )

    EuroZone_Productivity["Hours_YoY"] = (
        EuroZone_Productivity["Hours"].pct_change(4) * 100
    )

    EuroZone_Productivity["Persons_YoY"] = (
        EuroZone_Productivity["Persons"].pct_change(4) * 100
    )

    # Q vs Q4 2019
    EuroZone_Productivity["GVA_vs_Q4_2019"] = (
        EuroZone_Productivity["GVA"] / q4_2019["GVA"] - 1
    ) * 100

    EuroZone_Productivity["Hours_vs_Q4_2019"] = (
        EuroZone_Productivity["Hours"] / q4_2019["Hours"] - 1
    ) * 100

    EuroZone_Productivity["Persons_vs_Q4_2019"] = (
        EuroZone_Productivity["Persons"] / q4_2019["Persons"] - 1
    ) * 100

    EuroZone_Productivity = EuroZone_Productivity.round(2)

    # Extended TIME_PERIOD back to 2010-Q1
    EuroZone_URL_IE = 'https://ec.europa.eu/eurostat/api/dissemination/sdmx/3.0/data/dataflow/ESTAT/namq_10_gdp/1.0/*.*.*.*.*?c[freq]=Q&c[unit]=CP_MEUR,PD20_EUR&c[s_adj]=SCA&c[na_item]=B1G&c[geo]=BE,BG,DE,EE,IE,EL,ES,FR,HR,IT,CY,LV,LT,LU,MT,NL,AT,PT,SI,SK,FI&c[TIME_PERIOD]=ge:2010-Q1&compress=false&format=csvdata&formatVersion=2.0&lang=en&labels=name'
    EuroZone_IE = pd.read_csv(EuroZone_URL_IE)[['Unit of measure', 'Geopolitical entity (reporting)', 'TIME_PERIOD', 'OBS_VALUE']].rename(columns={
        'Geopolitical entity (reporting)': "Country",
        'TIME_PERIOD': 'Quarter',
        'OBS_VALUE': 'Value'
    })
    EuroZone_IE["Quarter"] = pd.PeriodIndex(EuroZone_IE["Quarter"], freq="Q")

    nominal_IE = EuroZone_IE[EuroZone_IE["Unit of measure"] == "Current prices, million euro"].rename(columns={"Value": "nominal_gva"})
    deflator_IE = EuroZone_IE[EuroZone_IE["Unit of measure"] == "Price index (implicit deflator), 2020=100, euro"].rename(columns={"Value": "deflator"})

    merged_IE = pd.merge(
        nominal_IE[["Country", "Quarter", "nominal_gva"]],
        deflator_IE[["Country", "Quarter", "deflator"]],
        on=["Country", "Quarter"],
        how="inner"
    )
    merged_IE["Value"] = (merged_IE["nominal_gva"] / merged_IE["deflator"]) * 100
    merged_IE = merged_IE[['Country', 'Quarter', 'Value']]

    print("\nGVA_IE country counts before:")
    print(merged_IE.groupby("Quarter")["Country"].nunique())

    # FIX: previously merged_IE (unadjusted, Ireland-included) never received
    # the same missing-country backfill that `merged` got. That silently
    # understated the unadjusted Eurozone total whenever a non-Ireland
    # country dropped out of the latest Eurostat release, making the
    # adjusted-vs-unadjusted gap look smaller than the Ireland swap alone
    # should produce. Run the same backfill here, independently, since
    # merged_IE has its own country set (it includes Ireland).
    merged_IE = backfill_missing_countries(merged_IE, "Value", label="merged_IE (unadjusted GVA)")

    print("\nGVA_IE country counts after:")
    print(merged_IE.groupby("Quarter")["Country"].nunique())

    EuroZone_GVA_IE = merged_IE.groupby("Quarter")["Value"].sum().reset_index().rename(columns={"Value": "GVA"})

    EuroZone_Productivity_IE = pd.merge(
        EuroZone_GVA_IE,
        EuroZone_Hours,
        on="Quarter"
    )

    EuroZone_Productivity_IE = pd.merge(
        EuroZone_Productivity_IE,
        EuroZone_Persons_raw.groupby("Quarter")["Persons"].sum().reset_index(),
        on="Quarter"
    )

    EuroZone_Productivity_IE = (
        EuroZone_Productivity_IE
        .sort_values("Quarter")
        .reset_index(drop=True)
    )

    EuroZone_Productivity_IE["output_per_hour"] = (
        EuroZone_Productivity_IE["GVA"] /
        EuroZone_Productivity_IE["Hours"]
    ) * 1000

    EuroZone_Productivity_IE["output_per_hour_QoQ"] = (
        EuroZone_Productivity_IE["output_per_hour"].pct_change() * 100
    )

    EuroZone_Productivity_IE["output_per_hour_YoY"] = (
        EuroZone_Productivity_IE["output_per_hour"].pct_change(4) * 100
    )

    EuroZone_Productivity_IE["output_per_worker"] = (
        EuroZone_Productivity_IE["GVA"] /
        EuroZone_Productivity_IE["Persons"]
    ) * 1000

    EuroZone_Productivity_IE["output_per_worker_QoQ"] = (
        EuroZone_Productivity_IE["output_per_worker"].pct_change() * 100
    )

    EuroZone_Productivity_IE["output_per_worker_YoY"] = (
        EuroZone_Productivity_IE["output_per_worker"].pct_change(4) * 100
    )

    q4_2019_IE = EuroZone_Productivity_IE[
        EuroZone_Productivity_IE["Quarter"] == pd.Period("2019Q4")
    ].iloc[0]

    EuroZone_Productivity_IE["output_per_hour_vs_Q4_2019"] = (
        EuroZone_Productivity_IE["output_per_hour"] /
        q4_2019_IE["output_per_hour"] - 1
    ) * 100

    EuroZone_Productivity_IE["output_per_worker_vs_Q4_2019"] = (
        EuroZone_Productivity_IE["output_per_worker"] /
        q4_2019_IE["output_per_worker"] - 1
    ) * 100

    # QoQ
    EuroZone_Productivity_IE["GVA_QoQ"] = (
        EuroZone_Productivity_IE["GVA"].pct_change() * 100
    )

    EuroZone_Productivity_IE["Hours_QoQ"] = (
        EuroZone_Productivity_IE["Hours"].pct_change() * 100
    )

    EuroZone_Productivity_IE["Persons_QoQ"] = (
        EuroZone_Productivity_IE["Persons"].pct_change() * 100
    )

    # YoY
    EuroZone_Productivity_IE["GVA_YoY"] = (
        EuroZone_Productivity_IE["GVA"].pct_change(4) * 100
    )

    EuroZone_Productivity_IE["Hours_YoY"] = (
        EuroZone_Productivity_IE["Hours"].pct_change(4) * 100
    )

    EuroZone_Productivity_IE["Persons_YoY"] = (
        EuroZone_Productivity_IE["Persons"].pct_change(4) * 100
    )

    # Q vs Q4 2019
    EuroZone_Productivity_IE["GVA_vs_Q4_2019"] = (
        EuroZone_Productivity_IE["GVA"] / q4_2019_IE["GVA"] - 1
    ) * 100

    EuroZone_Productivity_IE["Hours_vs_Q4_2019"] = (
        EuroZone_Productivity_IE["Hours"] / q4_2019_IE["Hours"] - 1
    ) * 100

    EuroZone_Productivity_IE["Persons_vs_Q4_2019"] = (
        EuroZone_Productivity_IE["Persons"] / q4_2019_IE["Persons"] - 1
    ) * 100

    EuroZone_Productivity_IE = EuroZone_Productivity_IE.round(2)

    # Sanity check: the adjusted vs. unadjusted Eurozone GVA gap (latest
    # quarter) should equal the Ireland CSO-vs-Eurostat gap almost exactly,
    # since Ireland is the only country that differs between the two frames.
    latest_q = EuroZone_GVA["Quarter"].max()
    adj_total = EuroZone_GVA.loc[EuroZone_GVA["Quarter"] == latest_q, "GVA"].values[0]
    unadj_total = EuroZone_GVA_IE.loc[EuroZone_GVA_IE["Quarter"] == latest_q, "GVA"].values[0]
    total_gap = adj_total - unadj_total

    ireland_adj_val = Ireland_GVA.loc[Ireland_GVA["Quarter"] == latest_q, "Value"].values
    ireland_unadj_val = merged_IE.loc[
        (merged_IE["Country"] == "Ireland") & (merged_IE["Quarter"] == latest_q), "Value"
    ].values
    if len(ireland_adj_val) and len(ireland_unadj_val):
        ireland_gap = ireland_adj_val[0] - ireland_unadj_val[0]
        print(f"\n[Sanity check] Total adjusted-unadjusted GVA gap: {total_gap:.2f}")
        print(f"[Sanity check] Ireland-only GVA gap: {ireland_gap:.2f}")
        if abs(total_gap - ireland_gap) > 1:
            print(
                f"[WARNING] Gap mismatch of {total_gap - ireland_gap:.2f} — "
                "a non-Ireland country likely differs between merged and merged_IE."
            )

    # # Per-country productivity (adjusted Ireland)
    country_productivity = per_country(merged, merged_IE, Ireland_GVA, EuroZone_Hours_raw, EuroZone_Productivity, EuroZone_Productivity_IE)

    with pd.ExcelWriter("scripts/EU_Figures/OPH_Figures.xlsx", engine="openpyxl") as writer:
        EuroZone_Productivity.to_excel(writer, sheet_name="Adjusted Eurozone GVApH", index=False)
        EuroZone_Productivity_IE.to_excel(writer, sheet_name="Unadjusted Eurozone GVApH", index=False)
        country_productivity.to_excel(writer, sheet_name="Country GVApH", index=False)


    key_countries = [
            'Germany', 'France', 'Italy', 'Spain', 'Netherlands',
        ]
    path = 'scripts/EU_Figures'
    fig = plot_productivity(country_productivity, EuroZone_Productivity, key_countries)
    fig.write_image(f"{path}/images/2026-Q2-Figure-2.png", width=1400, height=800, scale=2)
    fig.write_html(f"{path}/html/2026-Q2-Figure-2.html")