import pandas as pd
import plotly.graph_objects as go

# Unemployment_URL = 'https://ec.europa.eu/eurostat/api/dissemination/sdmx/3.0/data/dataflow/ESTAT/une_rt_m/1.0/*.*.*.*.*.*?c[freq]=M&c[s_adj]=NSA,SA&c[age]=TOTAL&c[unit]=THS_PER,PC_ACT&c[sex]=T&c[geo]=EU27_2020,EA21,BE,BG,CZ,DK,DE,EE,IE,EL,ES,FR,HR,IT,CY,LV,LT,LU,HU,MT,NL,AT,PL,PT,RO,SI,SK,FI,SE,IS,NO,CH,UK,BA,MK,TR,US,JP&c[TIME_PERIOD]=2026-04,2026-03,2026-02,2026-01,2025-12,2025-11,2025-10,2025-09,2025-08,2025-07,2025-06,2025-05,2025-04,2025-03,2025-02,2025-01,2024-12,2024-11,2024-10,2024-09,2024-08,2024-07,2024-06,2024-05,2024-04,2024-03,2024-02,2024-01,2023-12,2023-11,2023-10,2023-09,2023-08,2023-07,2023-06,2023-05,2023-04,2023-03,2023-02,2023-01,2022-12,2022-11,2022-10,2022-09,2022-08,2022-07,2022-06,2022-05,2022-04,2022-03,2022-02,2022-01&compress=false&format=csvdata&formatVersion=1.0&lang=en&labels=label_only'

Industries_Short_Dict = {
    'Agriculture, forestry and fishing': 'Agriculture & Forestry',
    'Industry (except construction)': 'Industry (excluding construction)',
    'Manufacturing': 'Manufacturing',
    'Construction': 'Construction',
    'Wholesale and retail trade, transport, accommodation and food service activities': 'Trade, transport, and hospitality',
    'Information and communication': 'ICT',
    'Financial and insurance activities': 'Finance & insurance',
    'Real estate activities': 'Real estate',
    'Professional, scientific and technical activities; administrative and support service activities': 'Professional & admin services',
    'Public administration, defence, education, human health and social work activities': 'Public admin, defence, education, health',
    'Arts, entertainment and recreation; other service activities; activities of household and extra-territorial organizations and bodies': 'Arts, entertainment & other services',
    'Total - all NACE activities': 'Total - all NACE activities'
}

def plot_latest_industry_growth_bar(
    df,
    value_col,
    current_quarter,
    yoy=False,
    title=None,
    top_n=None
):
    df = df.copy()

    quarter_fmt = current_quarter.replace("Q", "-Q")

    # map short names if available
    if 'Industries_Short_Dict' in globals():
        df['Industry'] = df['Industry'].map(Industries_Short_Dict).fillna(df['Industry'])

    # ensure correct sorting before pct_change
    df = df.sort_values(['Industry', 'Quarter'])
    df = df[df['Country'] == 'Euro Zone'].copy()

    shift_n = 4 if yoy else 1

    df['Growth'] = df.groupby('Industry')[value_col].pct_change(shift_n) * 100

    # filter to latest quarter
    df = df[df['Quarter'] <= quarter_fmt]
    latest = df['Quarter'].max()
    df = df[df['Quarter'] == latest].dropna(subset=['Growth'])

    df = df.sort_values('Growth')

    if top_n:
        df = df.tail(top_n)

    pos_colour = "#03979d"
    neg_colour = "#eb5e5e"

    colors = [pos_colour if x > 0 else neg_colour for x in df['Growth']]

    fig = go.Figure()

    fig.add_trace(go.Bar(
        y=df['Industry'],
        x=df['Growth'],
        orientation='h',
        marker=dict(
            color=colors,
            line=dict(color='black', width=0.5)
        ),
        hovertemplate="<b>%{y}</b><br>Growth: %{x:.2f}%<extra></extra>"
    ))

    for _, row in df.iterrows():
        fig.add_annotation(
            x=row['Growth'],
            y=row['Industry'],
            text=f"{row['Growth']:.1f}%",
            showarrow=False,
            font=dict(size=13, color='black'),
            xanchor="left" if row['Growth'] >= 0 else "right",
            xshift=5 if row['Growth'] >= 0 else -5
        )

    fig.update_layout(
        xaxis_title="Growth (%)",
        yaxis_title="",
        template="simple_white",
        height=450 + len(df) * 22,
        bargap=0.15,
        xaxis=dict(
            zeroline=True,
            zerolinewidth=2,
            zerolinecolor="gray",
        ),
        yaxis=dict(tickfont=dict(size=13))
    )
    fig.update_xaxes(range=[-4, 4])
    fig.update_layout(
        template='simple_white',
        width=900,
        margin=dict(l=180, r=40, t=80, b=40)
    )

    print(df[['Industry', 'Quarter', value_col, 'Growth']].sort_values('Quarter').tail(20))
    print("Latest quarter used:", latest)
    return fig

def plot_eurozone_industry_growth( # Nvm this looks bad
    df,
    value_col,
    current_quarter,
    Industries_Short_Dict,
    Industries_Short,
    yoy=False,
    industries=None,
):
    euro = df[df['Country'] == 'Euro Zone'].copy()

    euro = euro.sort_values(['Industry', 'Quarter'])

    shift_n = 4 if yoy else 1
    euro['Growth'] = euro.groupby('Industry')[value_col].pct_change(shift_n) * 100

    quarter_fmt = current_quarter.replace("Q", "-Q")
    euro = euro[euro['Quarter'] <= quarter_fmt]

    # --- map to short names ---
    euro['Industry'] = euro['Industry'].map(Industries_Short_Dict).fillna(euro['Industry'])

    if industries is not None:
        euro = euro[euro['Industry'].isin(industries)]

    fig = go.Figure()

    # --- enforce legend order ---
    ordered_industries = [
        ind for ind in Industries_Short
        if ind in euro['Industry'].unique()
    ]

    for industry in ordered_industries:
        d = euro[euro['Industry'] == industry]

        fig.add_trace(go.Scatter(
            x=d['Quarter'],
            y=d['Growth'],
            mode='lines',
            name=industry,
            hovertemplate=(
                "<b>%{fullData.name}</b><br>"
                "Quarter: %{x}<br>"
                "Growth: %{y:.2f}%<extra></extra>"
            )
        ))

    fig.update_layout(
        title=f"Euro Zone Industry {'YoY' if yoy else 'QoQ'} Growth ({value_col})",
        xaxis_title="Quarter",
        yaxis_title="Growth (%)",
        hovermode="x unified",
        legend_title="Industry",
        margin=dict(l=60, r=30, t=80, b=50),
        height=600
    )

    return fig

def generate(current_quarter):
    path = 'scripts/EU_Figures'

    key_countries = [
        'Euro Zone', 'European Union', 'Germany', 'France', 'Italy', 'Spain', 'Netherlands', 
    ]
    # 'Ireland',

    key_industries = [
        'Total - all NACE activities', 'Manufacturing', 'Industry (except construction)', 'Construction'
    ]

    Industries_Short_Dict = {
        'Agriculture, forestry and fishing': 'Agriculture & Forestry',
        'Industry (except construction)': 'Industry (excluding construction)',
        'Manufacturing': 'Manufacturing',
        'Construction': 'Construction',
        'Wholesale and retail trade, transport, accommodation and food service activities': 'Trade, transport, and hospitality',
        'Information and communication': 'ICT',
        'Financial and insurance activities': 'Finance & insurance',
        'Real estate activities': 'Real estate',
        'Professional, scientific and technical activities; administrative and support service activities': 'Professional & admin services',
        'Public administration, defence, education, human health and social work activities': 'Public admin, defence, education, health',
        'Arts, entertainment and recreation; other service activities; activities of household and extra-territorial organizations and bodies': 'Arts, entertainment & other services',
        'Total - all NACE activities': 'Total - all NACE activities'
    }

    Industries_Short = [
        'Agriculture & Forestry',
        'Industry (excluding construction)',
        'Manufacturing',
        'Construction',
        'Trade, transport, and hospitality',
        'ICT',
        'Finance & insurance',
        # 'Real estate',  # Removed real estate because it skews the data so much
        'Professional & admin services',
        'Public admin, defence, education, health',
        'Arts, entertainment & other services',
        'Total - all NACE activities'
    ]

    GVA_Chained_URL = 'https://ec.europa.eu/eurostat/api/dissemination/sdmx/3.0/data/dataflow/ESTAT/namq_10_a10/1.0/*.*.*.*.*.*?c[freq]=Q&c[unit]=CLV_I20&c[s_adj]=SCA&c[nace_r2]=TOTAL,A,B-E,C,F,G-I,J,K,L,M_N,O-Q,R-U&c[na_item]=B1G&c[geo]=EU27_2020,EA,EA21,EA20,EA19,EA12,BE,BG,CZ,DK,DE,EE,IE,EL,ES,FR,HR,IT,CY,LV,LT,LU,HU,MT,NL,AT,PL,PT,RO,SI,SK,FI,SE,NO,CH,UK,BA,ME,MK,AL,RS,TR,XK&c[TIME_PERIOD]=2026-Q1,2025-Q4,2025-Q3,2025-Q2,2025-Q1,2024-Q4,2024-Q3,2024-Q2,2024-Q1,2023-Q4,2023-Q3,2023-Q2,2023-Q1,2022-Q4,2022-Q3,2022-Q2,2022-Q1,2021-Q4,2021-Q3,2021-Q2,2021-Q1,2020-Q4,2020-Q3,2020-Q2,2020-Q1&compress=false&format=csvdata&formatVersion=1.0&lang=en&labels=label_only'

    GVA_Chained = pd.read_csv(GVA_Chained_URL, usecols=['unit', 'nace_r2', 'geo', 'TIME_PERIOD', 'OBS_VALUE']).rename(columns={
            "nace_r2": "Industry",
            "geo": "Country",
            "TIME_PERIOD": "Quarter",
            "OBS_VALUE": "Value"
        })

    GVA_Chained['Country'] = GVA_Chained['Country'].replace({
        'Euro area – 21 countries (from 2026)': 'Euro Zone',
        'European Union - 27 countries (from 2020)': 'European Union'                                           
    })

    print(GVA_Chained['Industry'].unique().tolist())

    Hours_Jobs_URL = 'https://ec.europa.eu/eurostat/api/dissemination/sdmx/3.0/data/dataflow/ESTAT/namq_10_a10_e/1.0/*.*.*.*.*.*?c[freq]=Q&c[unit]=THS_HW,THS_JOB&c[nace_r2]=TOTAL,A,B-E,C,F,G-I,J,K,L,M_N,O-Q,R-U&c[s_adj]=SCA&c[na_item]=EMP_DC&c[geo]=EU27_2020,EA,EA21,EA20,EA19,EA12,BE,BG,CZ,DK,DE,EE,IE,EL,ES,FR,HR,IT,CY,LV,LT,LU,HU,MT,NL,AT,PL,PT,RO,SI,SK,FI,SE,IS,NO,CH,UK,ME,MK,RS&c[TIME_PERIOD]=2026-Q1,2025-Q4,2025-Q3,2025-Q2,2025-Q1,2024-Q4,2024-Q3,2024-Q2,2024-Q1,2023-Q4,2023-Q3,2023-Q2,2023-Q1,2022-Q4,2022-Q3,2022-Q2,2022-Q1,2021-Q4,2021-Q3,2021-Q2,2021-Q1,2020-Q4,2020-Q3,2020-Q2,2020-Q1&compress=false&format=csvdata&formatVersion=1.0&lang=en&labels=label_only'

    Hours_Jobs = pd.read_csv(Hours_Jobs_URL, usecols=['unit', 'nace_r2', 'geo', 'TIME_PERIOD', 'OBS_VALUE']).rename(columns={
            "nace_r2": "Industry",
            "geo": "Country",
            "TIME_PERIOD": "Quarter",
            "OBS_VALUE": "Value"
        })

    Hours_Jobs['Country'] = Hours_Jobs['Country'].replace({
        'Euro area – 21 countries (from 2026)': 'Euro Zone',
        'European Union - 27 countries (from 2020)': 'European Union'                                           
    })

    Hours = Hours_Jobs[Hours_Jobs['unit'] == 'Thousand hours worked'].drop(['unit'], axis=1)
    Jobs = Hours_Jobs[Hours_Jobs['unit'] == 'Thousand jobs'].drop(['unit'], axis=1)

    GVA_per_Hour = GVA_Chained.merge(
        Hours,
        on=['Country', 'Industry', 'Quarter'],
        suffixes=('_GVA', '_Hours')
    ).assign(GVA_per_Hour=lambda df: (df['Value_GVA'] / df['Value_Hours']) * 1000)[['Country', 'Industry', 'Quarter', 'GVA_per_Hour']]

    GVA_per_Job = GVA_Chained.merge(
        Jobs,
        on=['Country', 'Industry', 'Quarter'],
        suffixes=('_GVA', '_Jobs')
    ).assign(GVA_per_Job=lambda df: (df['Value_GVA'] / df['Value_Jobs']) * 1000)[['Country', 'Industry', 'Quarter', 'GVA_per_Job']]


    def rebase_to_2020(df, value_col):
        base = (
            df[df['Quarter'].str.startswith('2020')]
            .groupby(['Country', 'Industry'])[value_col]
            .mean()
            .rename('base')
        )
        return (
            df.join(base, on=['Country', 'Industry'])
            .assign(**{value_col: lambda d: (d[value_col] / d['base']) * 100})
            .drop(columns='base')
        )

    def add_growth(df, value_col):
        filtered = (
            df[df['Country'].isin(key_countries) & df['Industry'].isin(key_industries)]
            .copy()
            .sort_values(['Country', 'Industry', 'Quarter'])
        )
        filtered['QoQ'] = filtered.groupby(['Country', 'Industry'])[value_col].pct_change(1) * 100
        filtered['YoY'] = filtered.groupby(['Country', 'Industry'])[value_col].pct_change(4) * 100
        return filtered


    GVA_per_Hour_idx = rebase_to_2020(GVA_per_Hour, 'GVA_per_Hour')
    GVA_per_Job_idx = rebase_to_2020(GVA_per_Job, 'GVA_per_Job')

    with pd.ExcelWriter(f'{path}/Sectoral_Productivity.xlsx', engine='openpyxl') as writer:
        add_growth(GVA_per_Hour_idx, 'GVA_per_Hour').to_excel(writer, sheet_name='Condensed - GVA per Hour', index=False)
        add_growth(GVA_per_Job_idx, 'GVA_per_Job').to_excel(writer, sheet_name='Condensed - GVA per Job', index=False)
        GVA_Chained.to_excel(writer, sheet_name='GVA_Chained', index=False)
        Hours.to_excel(writer, sheet_name='Thousand hours worked', index=False)
        Jobs.to_excel(writer, sheet_name='Thousand jobs', index=False)
        GVA_per_Hour.to_excel(writer, sheet_name='Sectoral GVA per Hour', index=False)
        GVA_per_Job.to_excel(writer, sheet_name='Sectoral GVA per Job', index=False)
        GVA_per_Hour_idx.to_excel(writer, sheet_name='GVA per Hour (2020=100)', index=False)
        GVA_per_Job_idx.to_excel(writer, sheet_name='GVA per Job (2020=100)', index=False)

    # print(GVA_per_Hour_idx)
    # print(GVA_per_Job_idx)

    low_colour = '#9c4f8b'   # red
    high_colour = '#03979d'  # green

    # latest_quarter = GVA_per_Hour_idx['Quarter'].max()  # 2026-Q1
    # latest_quarter = '2025-Q4'
    latest_quarter = current_quarter.replace("Q", "-Q")

    # industry_order = [Industries_Short[k] for k in Industries_Short if k in heatmap_data.columns or True]

    heatmap_data = (
        GVA_per_Hour_idx[GVA_per_Hour_idx['Country'].isin(key_countries)]
        .sort_values(['Country', 'Industry', 'Quarter'])
        .assign(QoQ=lambda df: df.groupby(['Country', 'Industry'])['GVA_per_Hour'].pct_change(1) * 100)
        .query('Quarter == @latest_quarter')
        .assign(Industry=lambda df: df['Industry'].map(Industries_Short_Dict).fillna(df['Industry']))
        .pivot(index='Country', columns='Industry', values='QoQ')
    )

    # Order columns by Industries_Short insertion order, order rows by key_countries
    heatmap_data = heatmap_data.reindex(columns=Industries_Short)
    heatmap_data = heatmap_data.reindex(index=key_countries[::-1])

    colorscale = [
        [0.0, low_colour],
        [0.5, '#ffffff'],
        [1.0, high_colour],
    ]

    fig = go.Figure(data=go.Heatmap(
        z=heatmap_data.values,
        x=heatmap_data.columns.tolist(),
        y=heatmap_data.index.tolist(),
        colorscale=colorscale,
        zmid=0,
        text=heatmap_data.values.round(1),
        texttemplate='%{text}%',
        textfont=dict(size=14),
        hovertemplate='<b>%{y}</b><br>%{x}<br>%{z:.2f}%<extra></extra>',
        showscale=False,
        xgap=2,
        ygap=2,
    ))

    fig.update_layout(
        xaxis=dict(
            tickangle=-35,
            side='top',
        ),
        margin=dict(l=120, r=40, t=180, b=40),
        height=500 + len(key_countries) * 20,
    )

    # fig.show()
    fig.write_image(f"{path}/images/2026-Q1-Figure-1.png", width=1200, height=600, scale=2)
    fig.write_html(f"{path}/html/2026-Q1-Figure-1.html")

    # fig = plot_eurozone_industry_growth(
    #     GVA_per_Hour_idx,
    #     value_col='GVA_per_Hour',
    #     current_quarter=current_quarter,
    #     Industries_Short_Dict=Industries_Short_Dict,
    #     Industries_Short=Industries_Short,
    #     yoy=False,
    # )
    # fig.show()

    fig = plot_latest_industry_growth_bar(
        GVA_per_Hour_idx,
        value_col="GVA_per_Hour",
        current_quarter=current_quarter,
        yoy=False
    )
    fig.write_image(f"{path}/images/2026-Q1-Figure-3.png", width=1000, height=600, scale=2)
    fig.write_html(f"{path}/html/2026-Q1-Figure-3.html")
