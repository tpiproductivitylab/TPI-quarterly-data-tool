import pandas as pd
import plotly.express as px

def generate():

    prod_url = 'https://ec.europa.eu/eurostat/api/dissemination/sdmx/3.0/data/dataflow/ESTAT/namq_10_lp_ulc/1.0/*.*.*.*.*?c[freq]=Q&c[unit]=I10&c[s_adj]=SCA&c[na_item]=RLPR_HW&c[geo]=EU27_2020,EA,EA21,EA20,EA19,EA12,BE,BG,CZ,DK,DE,EE,IE,EL,ES,FR,HR,IT,CY,LV,LT,LU,HU,MT,NL,AT,PL,PT,RO,SI,SK,FI,SE,IS,NO,CH,UK,ME,MK,RS,XK&c[TIME_PERIOD]=2026-Q2,2026-Q1,2025-Q4,2025-Q3,2025-Q2,2025-Q1,2024-Q4,2024-Q3,2024-Q2,2024-Q1,2023-Q4,2023-Q3,2023-Q2,2023-Q1,2022-Q4,2022-Q3,2022-Q2,2022-Q1,2021-Q4,2021-Q3,2021-Q2,2021-Q1,2020-Q4,2020-Q3,2020-Q2,2020-Q1,2019-Q4,2019-Q3,2019-Q2,2019-Q1,2018-Q4,2018-Q3,2018-Q2,2018-Q1,2017-Q4,2017-Q3,2017-Q2,2017-Q1,2016-Q4,2016-Q3,2016-Q2,2016-Q1,2015-Q4,2015-Q3,2015-Q2,2015-Q1,2014-Q4,2014-Q3,2014-Q2,2014-Q1,2013-Q4,2013-Q3,2013-Q2,2013-Q1,2012-Q4,2012-Q3,2012-Q2,2012-Q1,2011-Q4,2011-Q3,2011-Q2,2011-Q1,2010-Q4,2010-Q3,2010-Q2,2010-Q1&compress=false&format=csvdata&formatVersion=1.0&lang=en&labels=label_only'

    prod = pd.read_csv(prod_url, usecols=['geo', 'TIME_PERIOD', 'OBS_VALUE']).rename(columns={
                "geo": "Country",
                "TIME_PERIOD": "Quarter",
                "OBS_VALUE": "Value"
            })

    prod['Country'] = prod['Country'].replace({
            'Euro area – 21 countries (from 2026)': 'Euro Zone',
            'European Union - 27 countries (from 2020)': 'European Union'                                           
        })

    # Ensure quarters are ordered correctly
    prod['Quarter'] = pd.PeriodIndex(prod['Quarter'], freq='Q').to_timestamp()

    key_countries = [
        'Euro Zone',
        'European Union',
        'Germany',
        'France',
        'Italy',
        'Spain',
        'Netherlands',
    ]

    prod['Country'] = pd.Categorical(
        prod['Country'],
        categories=key_countries,
        ordered=True
    )

    prod = prod.sort_values(['Country', 'Quarter'])

    fig = px.line(
        prod,
        x='Quarter',
        y='Value',
        color='Country',
    )

    fig.update_layout(
        hovermode='closest',
        legend_title='Country',
        xaxis_title=None,
        yaxis_title=None
    )
    fig.update_xaxes(
        dtick="M3",           # every quarter
        tickformat="%Y-Q%q"   # 2025-Q1, 2025-Q2, etc.
    )

    for trace in fig.data:
        trace.hovertemplate = (
            "<b>%{fullData.name}</b><br>"
            "Quarter: %{x|%Y-Q%q}<br>"
            "Index: %{y:.1f}<br>"
            "<extra></extra>"
        )

    path = 'scripts/EU_Figures'
    fig.write_image(f"{path}/images/2026-Q2-Figure-2.png", width=1400, height=800, scale=2)
    fig.write_html(f"{path}/html/2026-Q2-Figure-2.html")