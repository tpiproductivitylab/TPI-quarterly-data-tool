# Script made for making visualisation for different datasets

MOBILE_STACK_JS = """
(function() {
    var breakpoint = 600;
    var origLayout = JSON.parse(JSON.stringify(gd.layout)); // snapshot original domains/annotations
    var xaxes = Object.keys(origLayout).filter(function(k){ return /^xaxis\\d*$/.test(k); });
    var yaxes = Object.keys(origLayout).filter(function(k){ return /^yaxis\\d*$/.test(k); });

    function applyLayout() {
        var isMobile = window.innerWidth < breakpoint;

        if (xaxes.length < 2) {
            // Single-panel figure: just tighten margins/fonts, don't touch domains
            Plotly.relayout(gd, {
                'margin.l': isMobile ? 60 : origLayout.margin.l,
                'margin.r': isMobile ? 30 : origLayout.margin.r,
                'font.size': isMobile ? 10 : 12
            });
            return;
        }

        // Two-panel (subplot) figure
        var update = {};
        if (isMobile) {
            update[xaxes[0] + '.domain'] = [0, 1];
            update[xaxes[1] + '.domain'] = [0, 1];
            update[yaxes[0] + '.domain'] = [0.55, 1];
            update[yaxes[1] + '.domain'] = [0, 0.45];
            update['height'] = Math.max(origLayout.height || 500, 900);

            if (origLayout.annotations && origLayout.annotations.length >= 2) {
                var anns = origLayout.annotations.map(function(a, i) {
                    var copy = Object.assign({}, a);
                    if (i === 0) { copy.x = 0.5; copy.y = 1.02; copy.xanchor = 'center'; }
                    if (i === 1) { copy.x = 0.5; copy.y = 0.47; copy.xanchor = 'center'; }
                    return copy;
                });
                update['annotations'] = anns;
            }
            if (origLayout.legend) {
                update['legend.x'] = 0;
                update['legend.y'] = 1.1;
                update['legend.orientation'] = 'h';
            }
        } else {
            // Restore desktop domains/annotations/height exactly as generated
            update[xaxes[0] + '.domain'] = origLayout[xaxes[0]].domain;
            update[xaxes[1] + '.domain'] = origLayout[xaxes[1]].domain;
            update[yaxes[0] + '.domain'] = origLayout[yaxes[0]].domain;
            update[yaxes[1] + '.domain'] = origLayout[yaxes[1]].domain;
            update['height'] = origLayout.height;
            if (origLayout.annotations) update['annotations'] = origLayout.annotations;
        }
        Plotly.relayout(gd, update);
    }

    applyLayout();
    window.addEventListener('resize', applyLayout);
})();
"""

import pandas as pd
import plotly_express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
# import sys
# sys.path.append("../") # So I can import functions from the streamlit script, makes the bargraphs black and white though?
# from Streamlit_application import quarter_to_numeric, numeric_to_quarter

TPI_colours = ["#eb5e5e", "#03979d", "#9c4f8b"] # peachy colour, greeny blue, lighter purple
# TPI_colours = ["#6C2283", "#39A7DF"] # dark purple, blue
TPI_One = "#03979d"
TPI_Two = "#eb5e5e"

def rebase_chain_linked_quarters(data, new_base_year):
    data = data.copy()
    
    # Extract year from Quarter (e.g., 1997.25 -> 1997)
    data["Year"] = data["Quarter"].astype(int)

    def rebase_group(group):
        # Get the mean of the base year for this group
        base_year_values = group[group["Year"] == new_base_year]["Value"]
        if base_year_values.empty or base_year_values.mean() == 0:
            return group  # Skip group if base year is missing or zero
        base_mean = base_year_values.mean()
        group["Value"] = (group["Value"] / base_mean) * 100
        return group

    # Apply rebase per group
    data = data.groupby(["Country", "Industry", "Variable"], group_keys=False).apply(rebase_group)

    # Drop temporary year column
    data = data.drop(columns="Year")

    return data

def quarter_to_numeric(q):
    year, qtr = q.split(" ")
    return int(year) + (int(qtr[1]) - 1) / 4  # Converts "1997 Q3" → 1997.5

def numeric_to_quarter(n):
    year = int(n)
    qtr = int((n - year) * 4) + 1
    return f"{year} Q{qtr}"

def line_graph(data, yAxisTitle, legendTitle, quarter):
    fig = px.line(
        data, 
        x="Quarter", 
        y=data.columns.drop("Quarter").tolist(), 
        title="",
        labels={"value": f"{yAxisTitle}", "variable": f"{legendTitle}"},
        color_discrete_sequence=TPI_colours
    )

    tickvals = [q for q in data['Quarter'] if q.endswith(f"Q{quarter}")]
    fig.update_xaxes(tickvals=tickvals)

    # Add variable (trace name) to hovertemplate
    for trace in fig.data:
        trace.hovertemplate = (
            "<b>%{fullData.name}</b><br>"
            "<b>Quarter</b>: %{x}<br>"
            "<b>Value</b>: %{y:.2f}"
            "<extra></extra>"
        )

    return fig

def qoq(data, title, legendTitle):
        # data = data[['Quarter', 'OPH']]
        # data["quarter_numeric"] = data["Quarter"].apply(quarter_to_numeric)
        # data = data[(data["quarter_numeric"] >= 2022 - 0.25) & (data["quarter_numeric"] <= 2024.75)]
        # data = data.drop('quarter_numeric', axis=1)
        data = data.melt(id_vars = "Quarter", var_name = f"{legendTitle}")
        data["QoQ Growth (%)"] = data.groupby(f"{legendTitle}")["value"].pct_change().mul(100).round(2)

        data = data.dropna()
        fig = px.bar(data, 
                     x="Quarter", 
                     y="QoQ Growth (%)", 
                     color=f"{legendTitle}",
                     color_discrete_sequence=TPI_colours,
                     barmode="group", 
                     title=f"{title}")
        # fig.update_layout(showlegend=False)
        fig.update_xaxes(title=None)
        return fig

def double_qoq(data, data_two, title, legendTitle, leftTitle, rightTitle):
        # data = data[['Quarter', 'OPH']]
        # data["quarter_numeric"] = data["Quarter"].apply(quarter_to_numeric)
        # data = data[(data["quarter_numeric"] >= 2022 - 0.25) & (data["quarter_numeric"] <= 2024.75)]
        # data = data.drop('quarter_numeric', axis=1)
        data = data.melt(id_vars = "Quarter", var_name = f"{legendTitle}")
        data["QoQ Growth (%)"] = data.groupby(f"{legendTitle}")["value"].pct_change().mul(100).round(2)
        data = data.dropna()

        data_two = data_two.melt(id_vars = "Quarter", var_name = f"{legendTitle}")
        data_two["QoQ Growth (%)"] = data_two.groupby(f"{legendTitle}")["value"].pct_change().mul(100).round(2)
        data_two = data_two.dropna()

        # Create subplots with 1 row and 2 columns
        fig = make_subplots(
            rows=1, cols=2, 
            subplot_titles=[f"{leftTitle}", f"{rightTitle}"]
        )

        # Add the first bar chart to the first subplot
        fig1 = px.bar(data, 
                     x="Quarter", 
                     y="QoQ Growth (%)", 
                     color=f"{legendTitle}",
                     color_discrete_sequence=TPI_colours,
                     barmode="group", 
                     title=f"{title}")

        # Add the second bar chart to the second subplot
        fig2 = px.bar(data_two, 
                     x="Quarter", 
                     y="QoQ Growth (%)", 
                     color=f"{legendTitle}",
                     color_discrete_sequence=TPI_colours,
                     barmode="group", 
                     title=f"{title}")
        
        for trace in fig1.data:
            fig.add_trace(trace, row=1, col=1)
        legend_labels = set(trace.name for trace in fig1.data)
        for trace in fig2.data:
            if trace.name in legend_labels:
                trace.showlegend = False  # Hide from legend
            else:
                legend_labels.add(trace.name)
            fig.add_trace(trace, row=1, col=2)

        for trace in fig.data:
            trace.hovertemplate = (
                "<b>Quarter</b>: %{x}<br>"
                "<b>QoQ Growth</b>: %{y:.2f}%"
                "<extra></extra>"
            )

        # Update layout for the subplots
        fig.update_layout(
            title=title,
            # xaxis_title="Quarter",
            yaxis_title="QoQ Growth (%)",
            legend_title="Method",
            barmode="group",  # Group bars within each subplot
        )

        # Update x-axis titles for each subplot
        fig.update_xaxes(title_text="", row=1, col=1)
        fig.update_xaxes(title_text="", row=1, col=2)

        # Update y-axis titles for each subplot
        fig.update_yaxes(title_text="QoQ Growth (%)", row=1, col=1)
        fig.update_yaxes(title_text="QoQ Growth (%)", row=1, col=2)

        return fig

def yoy(data):
        data = data[['Quarter', 'OPH']]
        data["Quarter"] = data["Quarter"].apply(quarter_to_numeric)
        data = data[(data["Quarter"] >= 2020.75 - 1) & (data["Quarter"] <= 2024.75)]
        data = data.melt(id_vars = "Quarter", var_name = "Measure")
        quarter_map = {1: 0, 2: 0.25, 3: 0.5, 4: 0.75}
        data['decimal_part'] = data['Quarter'] % 1
        data = data[data['decimal_part'].isin([quarter_map[4]])]
        data.drop('decimal_part', axis=1, inplace=True)
        data["YoY Growth (%)"] = data.groupby("Measure")["value"].pct_change().mul(100).round(2)
        data["Quarter"] = data["Quarter"].apply(numeric_to_quarter)

        data = data.dropna()
        fig = px.bar(data, x="Quarter", y="YoY Growth (%)", color="Measure",
                barmode="group", title="Q4 YOY Growth")
        fig.update_layout(showlegend=False)
        fig.update_xaxes(showtitle=False)
        return fig

def horizontal_bar(data, title):
    data = data.copy()
    data = data.dropna()
    data.drop(data.index[0], inplace=True)
    data = data.sort_values(by='Contribution')
    fig = go.Figure()

    fig.add_trace(go.Bar(
        y=data['Industry'],
        x=data['Contribution'],
        orientation='h',
        marker=dict(
            color=[TPI_One if x > 0 else TPI_Two for x in data['Contribution']],
            line=dict(color='black', width=0.5)
        ), 
        width=[w / max(data['Size']) * 0.9 for w in data['Size']],  # Normalise bar thickness
    ))

    pos_data = data[data['Contribution'] >= 0]
    neg_data = data[data['Contribution'] < 0]

    # Positive annotations
    for i, row in pos_data.iterrows():
        fig.add_annotation(
            x=row['Contribution'],
            y=row['Industry'],
            text=f"{row['Contribution']:.1%}",
            showarrow=False,
            font=dict(size=14, color='black'),
            xanchor="left",
            xshift=5,  # spacing from end of bar
            yshift=0
        )

    # Negative annotations
    for i, row in neg_data.iterrows():
        fig.add_annotation(
            x=row['Contribution'],
            y=row['Industry'],
            text=f"{row['Contribution']:.1%}",
            showarrow=False,
            font=dict(size=14, color='black'),
            xanchor="right",
            xshift=0,  # spacing from end of bar
            yshift=0
        )

    fig.update_layout(
        title=f'{title}',
        xaxis_title='Contribution to OPH, percentage point change',
        yaxis_title='',
        bargap=0.15,
        template='simple_white',
        height=400 + len(data) * 20,
        xaxis=dict(
            tickformat=".1%",
            zeroline=True,
            zerolinewidth=2,
            zerolinecolor='gray'
        ),
        yaxis=dict(
            tickfont=dict(
                size=15,
            )
        )
    )
    return fig

def OPH(data, title, inside_threshold_frac=0.5):
    data = data.copy()
    data['Output per hour worked'] *= 100
    data['GVA'] *= 100
    data['Hours worked'] *= 100

    fig = make_subplots(
        rows=1, cols=2,
        shared_yaxes=True,
        horizontal_spacing=0.05,
        subplot_titles=(
            "Change in <b>output per hour worked</b>",
            "Change in <b>GVA</b> and <b>hours worked</b>"
        )
    )

    left_chart_data = data.sort_values(by='Output per hour worked', ascending=False).reset_index(drop=True)

    max_abs_left = left_chart_data['Output per hour worked'].abs().max() if not left_chart_data.empty else 1.0
    threshold_left = inside_threshold_frac * max_abs_left

    left_text = left_chart_data['Output per hour worked'].map(lambda x: f"{x:.1f}%")
    left_textposition = ['inside' if abs(x) >= threshold_left else 'outside' for x in left_chart_data['Output per hour worked']]
    left_textfont_color = ['white' if pos == 'inside' else 'black' for pos in left_textposition]

    fig.add_trace(
        go.Bar(
            x=left_chart_data['Output per hour worked'],
            y=left_chart_data['Industry'],
            orientation='h',
            name='Productivity',
            marker_color=TPI_colours[0],
            text=left_text,
            textposition=left_textposition,
            textfont=dict(color=left_textfont_color, size=12),
            textangle=0,
            hovertemplate=(
                "<b>%{y}<br></b>"
                "<b>Productivity</b>: %{x:.1f}%<extra></extra>"
            )
        ),
        row=1, col=1
    )

    max_abs_right = max(data['GVA'].abs().max(), data['Hours worked'].abs().max()) if not data.empty else 1.0
    threshold_right = inside_threshold_frac * max_abs_right

    gva_text = data['GVA'].map(lambda x: f"{x:.1f}%")
    gva_textposition = ['inside' if abs(x) >= threshold_right else 'outside' for x in data['GVA']]
    gva_textfont_color = ['white' if pos == 'inside' else 'black' for pos in gva_textposition]

    hours_text = data['Hours worked'].map(lambda x: f"{x:.1f}%")
    hours_textposition = ['inside' if abs(x) >= threshold_right else 'outside' for x in data['Hours worked']]
    hours_textfont_color = ['white' if pos == 'inside' else 'black' for pos in hours_textposition]

    fig.add_trace(
        go.Bar(
            x=data['GVA'],
            y=data['Industry'],
            orientation='h',
            name='GVA',
            marker_color=TPI_colours[1],
            text=gva_text,
            textposition=gva_textposition,
            textfont=dict(color=gva_textfont_color, size=12),
            textangle=0,
            cliponaxis=False,
            hovertemplate=(
                "<b>%{y}<br></b>"
                "<b>GVA</b>: %{x:.1f}%<extra></extra>"
            )
        ),
        row=1, col=2
    )

    fig.add_trace(
        go.Bar(
            x=data['Hours worked'],
            y=data['Industry'],
            orientation='h',
            name='Hours Worked',
            marker_color=TPI_colours[2],
            text=hours_text,
            textposition=hours_textposition,
            textfont=dict(color=hours_textfont_color, size=12),
            textangle=0,
            cliponaxis=False,
            hovertemplate=(
                "<b>%{y}<br></b>"
                "<b>Hours worked</b>: %{x:.1f}%<extra></extra>"
            )
        ),
        row=1, col=2
    )

    fig.update_layout(
        height=1000,
        barmode='group',
        title_text=f'{title}',
        showlegend=True,
        legend=dict(x=0.65, y=1.1, orientation='h'),
        margin=dict(l=120, r=20, t=60, b=20),
        template='simple_white',
        uniformtext=dict(minsize=12, mode='show')
    )

    fig.update_xaxes(title_text="", zeroline=True, row=1, col=1, tickformat=".1f")
    fig.update_xaxes(title_text="", zeroline=True, row=1, col=2, tickformat=".1f")
    fig.update_yaxes(autorange='reversed')

    return fig

def New_GDP(data, provisional_countries=None):
    if provisional_countries is None:
        provisional_countries = []

    fig = px.bar(
        data,
        x="Growth",
        y="Country",
        orientation="h",
        color="Sign",
        color_discrete_map={"Negative": "red", "Positive": "teal"},
        text="Growth"
    )

    # Add star to provisional countries
    tickvals = data["Country"].tolist()
    ticktext = [
        country + "*" if country in provisional_countries else country
        for country in tickvals
    ]

    fig.update_traces(
        texttemplate="%{text:.1f}%",
        textposition="inside",
        hovertemplate=(
            "<b>%{y}</b><br>"
            "<b>Growth</b>: %{x:.1f}%"
            "<extra></extra>"
        )
    )

    fig.update_layout(
        xaxis_title="Growth Rate (%)",
        yaxis_title="",
        showlegend=False
    )

    # Override y-axis labels
    fig.update_yaxes(tickvals=tickvals, ticktext=ticktext)

    return fig

def write_mobile_html(fig, path, post_script=None, **kwargs):
    html_str = fig.to_html(
        include_plotlyjs="cdn",
        full_html=True,
        config={"responsive": True, "displayModeBar": False},
        post_script=post_script,
        **kwargs
    )
    # Inject viewport meta tag right after <head>
    html_str = html_str.replace(
        "<head>",
        '<head><meta name="viewport" content="width=device-width, initial-scale=1">',
        1
    )
    with open(path, "w", encoding="utf-8") as f:
        f.write(html_str)

# Imports - the figure number is the figure number from the ONS blog
# Figure 6
OPH_Industries = pd.read_excel('../src/New-release/Figure6.xlsx', skiprows=11, usecols=[0,1, 2], names=["Industry", "Contribution", "Size"])
# Figure 7
OPH_Breakdown = pd.read_excel('../src/New-release/Figure7.xlsx', skiprows=6, usecols=[0,1,2,3])
# Figure 4
OPW_Comparison = pd.read_csv('../src/New-release/Figure4.csv', skiprows=7, usecols=[0,1,2], names=["Quarter", "LFS Output per hour worked", "RTI + SE (exc working proprietors) Output per hour worked"])
# Figure 5
OPH_Comparison = pd.read_csv('../src/New-release/Figure5.csv', skiprows=7, usecols=[0,1,2], names=["Quarter", "LFS Output per hour worked", "RTI + SE (exc working proprietors) Output per hour worked"])
# # Figure 1
# Flash_Estimate_OPH = pd.read_csv('../src/New-release/Figure1.csv', skiprows=7, usecols=[0,1,2,3], names=["Quarter", "Gross Value Added", "Hours Worked", "Output Per Hour"])

# Figure 1 - no figure 1 this release (Q2 2026)
# Flash_Estimate_OPH["Quarter"] = Flash_Estimate_OPH["Quarter"].str.replace(r"(Q\d) (\d{4})", r"\2 \1", regex=True)
# base_value = Flash_Estimate_OPH.loc[Flash_Estimate_OPH["Quarter"] == "2007 Q1", "Gross Value Added"].iloc[0]
# Flash_Estimate_OPH["Gross Value Added"] = (Flash_Estimate_OPH["Gross Value Added"] / base_value) * 100

# base_value = Flash_Estimate_OPH.loc[Flash_Estimate_OPH["Quarter"] == "2007 Q1", "Hours Worked"].iloc[0]
# Flash_Estimate_OPH["Hours Worked"] = (Flash_Estimate_OPH["Hours Worked"] / base_value) * 100

# base_value = Flash_Estimate_OPH.loc[Flash_Estimate_OPH["Quarter"] == "2007 Q1", "Output Per Hour"].iloc[0]
# Flash_Estimate_OPH["Output Per Hour"] = (Flash_Estimate_OPH["Output Per Hour"] / base_value) * 100

# Flash_Estimate_OPH["Quarter"] = Flash_Estimate_OPH["Quarter"].apply(quarter_to_numeric)
# Flash_Estimate_OPH = Flash_Estimate_OPH[(Flash_Estimate_OPH['Quarter'] >= 2007) & (Flash_Estimate_OPH['Quarter'] <= 2026)]
# Flash_Estimate_OPH["Quarter"] = Flash_Estimate_OPH["Quarter"].apply(numeric_to_quarter)
# fig = line_graph(Flash_Estimate_OPH, "", "", 1)
# #fig.show()
# fig.write_image("../out/figures-images/Figure 1 - 2026 Flash Estimate.png", width=1200, height=800, scale=2)
# fig.write_html("../out/figures-html/2026-Q1-Figure-1.html")

# Figure 3
fig = horizontal_bar(OPH_Industries, "")
fig.update_layout(hovermode=False)
fig.write_image("../out/figures-images/Figure 3 - Contribution to OPH by Industry.png", width=1200, height=800, scale=2)
# fig.write_html("../out/figures-html/2026-Q2-Figure-3.html", config={"responsive": True}, post_script=MOBILE_STACK_JS,)
write_mobile_html(fig, "../out/figures-html/2026-Q2-Figure-3-2.html")
#fig.show()

# Figure 4
fig = OPH(OPH_Breakdown, "")
fig.write_image("../out/figures-images/Figure 4 - OPH GVA HW.png", width=1200, height=800, scale=2)
# fig.write_html("../out/figures-html/2026-Q2-Figure-4.html", config={"responsive": True}, post_script=MOBILE_STACK_JS,)
write_mobile_html(fig, "../out/figures-html/2026-Q2-Figure-4-2.html")
#fig.show()

# Figure 1
OPW_Comparison["Quarter"] = OPW_Comparison["Quarter"].str.replace(r"(Q\d) (\d{4})", r"\2 \1", regex=True)
OPW_Comparison['Quarter'] = OPW_Comparison['Quarter'].apply(quarter_to_numeric)
OPW_Difference = OPW_Comparison.copy()
OPW_Difference['difference'] = OPW_Difference['LFS Output per hour worked'] - OPW_Difference['RTI + SE (exc working proprietors) Output per hour worked']

preCovidOPW = OPW_Comparison.copy()
preCovidOPW = preCovidOPW[(preCovidOPW['Quarter'] >= 2014.75) & (preCovidOPW['Quarter'] <= 2019)]
preCovidOPW['Quarter'] = preCovidOPW['Quarter'].apply(numeric_to_quarter)

postCovidOPW = OPW_Comparison.copy()
postCovidOPW = postCovidOPW[(postCovidOPW['Quarter'] >= 2021.25) & (postCovidOPW['Quarter'] <= 2026.25)]
postCovidOPW['Quarter'] = postCovidOPW['Quarter'].apply(numeric_to_quarter)

fig = double_qoq(preCovidOPW, postCovidOPW, "", "legend", "Output per worker pre-COVID", "Output per worker post-COVID")
fig.write_image("../out/figures-images/Figure 1 - OPW - LFS vs RTI - double.png", width=1200, height=800, scale=2)
# fig.write_html("../out/figures-html/2026-Q2-Figure-1.html", config={"responsive": True}, post_script=MOBILE_STACK_JS,)
write_mobile_html(fig, "../out/figures-html/2026-Q2-Figure-1-2.html")
#fig.show()

# Figure 2
OPH_Comparison["Quarter"] = OPH_Comparison["Quarter"].str.replace(r"(Q\d) (\d{4})", r"\2 \1", regex=True)
OPH_Comparison['Quarter'] = OPH_Comparison['Quarter'].apply(quarter_to_numeric)

preCovidOPH = OPH_Comparison.copy()
preCovidOPH = preCovidOPH[(preCovidOPH['Quarter'] >= 2014.75) & (preCovidOPH['Quarter'] <= 2019)]
preCovidOPH['Quarter'] = preCovidOPH['Quarter'].apply(numeric_to_quarter)

postCovidOPH = OPH_Comparison.copy()
postCovidOPH = postCovidOPH[(postCovidOPH['Quarter'] >= 2021.25) & (postCovidOPH['Quarter'] <= 2026.25)]
postCovidOPH['Quarter'] = postCovidOPH['Quarter'].apply(numeric_to_quarter)

fig = double_qoq(preCovidOPH, postCovidOPH, "", "legend", "Output per hour worked pre-COVID", "Output per hour worked post-COVID")
fig.write_image("../out/figures-images/Figure 2 - OPH - LFS vs RTI - double.png", width=1200, height=800, scale=2)
# fig.write_html("../out/figures-html/2026-Q2-Figure-2.html", config={"responsive": True}, post_script=MOBILE_STACK_JS,)
write_mobile_html(fig, "../out/figures-html/2026-Q2-Figure-2-2.html")
# fig.show()


# Figure 5 data:
# Data taken from https://www.ons.gov.uk/economy/grossdomesticproductgdp/datasets/uksecondestimateofgdpdatatables
# Gross domestic product at market prices: Chained volume measure in A2 AGGREGATES sheet
# Table 4: Percentage change, latest quarter on previous quarter

# Figure 5
UK_GDP = pd.read_excel('../src/New-release/Q2_GDP.xlsx')
fig = px.bar(UK_GDP, x='Quarter', y='GDP', color_discrete_sequence=[TPI_One])
fig.update_traces(
    text=UK_GDP['GDP'].map(lambda x: f"{x:.1f}%"),
    textposition='outside',
    textfont=dict(size=12),
    cliponaxis=False,
    hovertemplate="<b>%{x} GDP growth</b>: %{y}%"
)
#fig.show()
fig.write_image("../out/figures-images/Figure 5 - UK Quarterly GDP.png", width=1200, height=600, scale=2)
fig.write_html("../out/figures-html/2026-Q2-Figure-5.html")

# # Data from:
# # https://data-explorer.oecd.org/vis?df[ds]=DisseminateFinalDMZ&df[id]=DSD_NAMAIN1%40DF_QNA_EXPENDITURE_GROWTH_OECD&df[ag]=OECD.SDD.NAD&dq=Q..CAN%2BDEU%2BFRA%2BGBR%2BITA%2BJPN%2BUSA%2BOECD%2BG7%2BEA20.S1..B1GQ......G1.&pd=2024-Q1%2C&to[TIME_PERIOD]=false&ly[cl]=TIME_PERIOD&ly[rw]=REF_AREA&vw=tb
GDP_data = pd.read_csv('../src/New-release/OECD GDP.csv')

# Figure 6
GDP_data = GDP_data[['Reference area', 'TIME_PERIOD', 'OBS_VALUE']].rename(columns={'TIME_PERIOD': 'Quarter', 'Reference area': 'Country', 'OBS_VALUE': 'Growth'})
GDP_data = GDP_data[GDP_data['Quarter'] == '2026-Q2']
GDP_data = GDP_data.sort_values(by="Growth", ascending=True).round(1)
GDP_data["Sign"] = GDP_data["Growth"].apply(lambda x: "Negative" if x < 0 else "Positive")
provisional_countries = ['Canada', 'Germany']
fig = New_GDP(GDP_data, provisional_countries)
#fig.show()
fig.write_image("../out/figures-images/Figure 6 - Q2 G7 GDP.png", width=1200, height=800, scale=2)
fig.write_html("../out/figures-html/2026-Q2-Figure-6.html")
