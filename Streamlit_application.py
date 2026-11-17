import streamlit as st
import pandas as pd
import plotly.express as px
from plotly.subplots import make_subplots
import plotly.graph_objects as go
import math

class data_options:
    def __init__(self, QorY, data_option, base_year, YoY_year, show_years, show_dip_lines, x_axis_title):
        self.QorY= QorY
        self.data_option = data_option
        self.base_year = base_year
        self.YoY_year = YoY_year
        self.show_years = show_years
        self.show_dip_lines = show_dip_lines
        self.x_axis_title = x_axis_title

def ordinal(n):
    return str(n)+("th" if 4<=n%100<=20 else {1:"st",2:"nd",3:"rd"}.get(n%10, "th"))

def quarter_to_numeric(q): # Converts "1997 Q3" → 1997.5    
    year, qtr = q.split(" ")
    return int(year) + (int(qtr[1]) - 1) / 4  

def numeric_to_quarter(n): # Converts 1997.5 → "1997 Q3"
    year = int(n)
    qtr = int((n - year) * 4) + 1
    return f"{year} Q{qtr}"

def rebase_chain_linked_quarters(df, new_base_year):
    df = df.copy()
    year = df["Quarter"].astype(int)
    keys = [df["Country"], df["Industry"], df["Variable"]]

    # Mean of the base year's values within each Country/Industry/Variable group,
    # broadcast back onto every row of that group
    base_mean = (
        df["Value"]
        .where(year == new_base_year)
        .groupby(keys, dropna=False)
        .transform("mean")
    )

    # Skip groups with no base-year data or a zero base (same behaviour as before)
    valid = base_mean.notna() & (base_mean != 0)
    df.loc[valid, "Value"] = df.loc[valid, "Value"] / base_mean[valid] * 100
    return df

def rebase_chain_linked_years(df, new_base_year):
    df = df.copy()

    def rebase_group(group):
        base_year_values = group[group["Year"] == new_base_year]["Value"]
        if base_year_values.empty or base_year_values.mean() == 0:
            return group
        base_mean = base_year_values.mean()
        group["Value"] = (group["Value"] / base_mean) * 100
        return group

    # Move grouping columns to index to avoid future warnings
    df = df.set_index(["Country", "Variable"])

    df = df.groupby(level=[0,1], group_keys=False).apply(rebase_group)

    return df.reset_index()


# @st.cache_data
def data_format(data, QorY, time_period, data_option, country_options, visType = "2D line graph", quarterly_selection =False, industry_selection = ["Total"]):
    data = data.copy()
    # Filter for time selection
    if QorY == "Quarterly":
        if data_option.base_year != 2020:
            data = rebase_chain_linked_quarters(data, data_option.base_year)
        # Convert the time periods to numeric
        time_period = list(time_period)
        time_period[0] = quarter_to_numeric(time_period[0])
        time_period[1] = quarter_to_numeric(time_period[1])
        if visType == "QoQ": 
            time_period[0] -= 0.25
        elif visType == "YoY":
            time_period[0] -= 1
        print('before')
        print(data)
        print(time_period)
        print(country_options)
        print(data_option.data_option)
        print(industry_selection)
        data = data.query(
        f"Quarter >= {time_period[0]} and Quarter <= {time_period[1]} and Country in {country_options} and Variable == '{data_option.data_option}' and Industry in {industry_selection}")
        print('after')
        print(data)
    elif QorY == "Yearly":
        if data_option.base_year != 2015:
            data = rebase_chain_linked_years(data, data_option.base_year)
        data = data.query(f"Year >= {time_period[0]} and Year <= {time_period[1]} and Country in {country_options}")
        return data
    
    # Data processing for bar graphs
    if visType == "QoQ" or visType == "YoY":
        qoq_data = data.copy()
        if visType == "QoQ":
            # Calculate QoQ Growth (Change from the previous quarter)
            qoq_data["QoQ Growth (%)"] = qoq_data.groupby("Country")["Value"].pct_change().mul(100).round(2)

        if visType == "YoY":
            # Filtering to show only selected quarters in yoy selection
            quarter_map = {1: 0, 2: 0.25, 3: 0.5, 4: 0.75}
            qoq_data["decimal_part"] = qoq_data["Quarter"] % 1
            qoq_data = qoq_data[qoq_data["decimal_part"].isin([quarter_map[quarterly_selection]])]
            qoq_data.drop("decimal_part", axis=1, inplace=True)
            qoq_data["YoY Growth (%)"] = qoq_data.groupby("Country")["Value"].pct_change().mul(100).round(2)
        data = qoq_data
    if not data_option.show_years:
        data = data.copy()
        data["Quarter"] = data["Quarter"].apply(numeric_to_quarter)
    return data

@st.cache_data
def multi_data_format(data, industry):
    plot_data = data.query(f"Industry == '{industry}'")
    return plot_data

def make_fig(data, visType, data_option, second_plot, second_data, show_legend):
    data = data.copy()
    if data_option.show_years:
        def decimal_to_quarter_label(value):
            if isinstance(value, (float, int)):
                year = int(value)
                fraction = round((value - year) * 4)
                quarter = {0: "Q1", 1: "Q2", 2: "Q3", 3: "Q4"}.get(fraction, "Q?")
                return f"{year} {quarter}"
            elif isinstance(value, str) and "Q" in value:
                return value  
            else:
                return str(value)  
        data["QuarterLabel"] = data["Quarter"].apply(decimal_to_quarter_label)
    else:
        data["QuarterLabel"] = data["Quarter"]
    TPI_colours = ["#eb5e5e", "#39A7DF","#6C2283", "#03969D"]
    if second_plot:  # remove - could move colour code to quarterly fig function and put in as a parameter, so it is run less
        countries = list(set(data["Country"]).union(set(second_data["Country"]))) # All countries in both lists
        print(data["Country"])
        print(second_data["Country"])
    else: # Need this to account for if second plot isn"t selected
        countries = list(data["Country"].unique())

    if len(countries) <= 4:
        country_colours = {country: TPI_colours[i % len(TPI_colours)] for i, country in enumerate(countries)}
    else:
        colour_palette = px.colors.qualitative.Dark2  # Choose a Plotly color set
        country_colours = {country: colour_palette[i % len(colour_palette)] for i, country in enumerate(countries)}
    
    if visType == "QoQ":
        fig = px.bar(data, 
                    x="Quarter", 
                    y="QoQ Growth (%)", 
                    color="Country",
                    color_discrete_map=country_colours,
                    barmode="group", 
                    title=f"Quarter on quarter comparison of {data_option.data_option} (chain linked values {data_option.base_year} = 100)",
                    custom_data=["QuarterLabel"])
        fig.update_layout(xaxis_title=f"{data_option.x_axis_title}")
        fig.update_traces(
            hovertemplate="%{customdata[0]}<br>Country: %{fullData.name}<br>Value: %{y:.2f}<extra></extra>"
        )
    elif visType == "YoY":
        fig = px.bar(data, 
                    x="Quarter", 
                    y="YoY Growth (%)", 
                    color="Country",
                    color_discrete_map=country_colours,
                    barmode="group", 
                    title=f"Year on year comparison of {data_option.data_option} for Q{data_option.YoY_year} of each year selected (chain linked values {data_option.base_year} = 100)",
                    custom_data=["QuarterLabel"])
        fig.update_layout(xaxis_title=f"{data_option.x_axis_title}")
        fig.update_traces(
            hovertemplate="%{customdata[0]}<br>Country: %{fullData.name}<br>Value: %{y:.2f}<extra></extra>"
        )

    elif visType == "3D line graph":
        # Extract years from quarters
        data["Year"] = data["Quarter"].apply(lambda x: int(x.split()[0]))
        
        # Create the line plot
        fig = px.line_3d(data, x="Country", y="Year", z="Value", color="Country")

        # Customise layout with explicit axis labels
        fig.update_layout(
            title=f"{data_option.QorY} comparison of {data_option.data_option} ({data_option.base_year} = 100)",
            scene=dict(camera=dict(eye=dict(x=1.7, y=1.7, z=1.7)), 
                       zaxis_title=f"{data_option.data_option}"),  # Move camera further away
            width=1000,
            height=500
        )
        fig.update_traces(line=dict(width=5))

    elif visType == "2D line graph":
        fig = px.line(data, 
                x="Quarter", 
                y="Value", 
                color="Country",
                color_discrete_map=country_colours,
                title=f"{data_option.QorY} comparison of {data_option.data_option} ({data_option.base_year} = 100)",
                labels={"value": f"{data_option.data_option}", "variable": "Countries"},
                custom_data=["QuarterLabel"])
        fig.update_layout(
            yaxis=dict(
                title=dict(
                    text=f"{data_option.data_option}"
                )
            ),
            xaxis_title=f"{data_option.x_axis_title}"
        )
        fig.update_traces(
            hovertemplate="%{customdata[0]}<br>Country: %{fullData.name}<br>Value: %{y:.2f}<extra></extra>"
        )

        if data_option.show_dip_lines:
            visible_quarters = data["Quarter"].unique().tolist() 
            if not data_option.show_years:
                highlighted_quarters = ["2007 Q4", "2009 Q2", "2019 Q4", "2021 Q1"]  # Quarters highlighted with verticle lines
            else:
                highlighted_quarters = ["2007.75", "2009.25", "2019.75", "2021"]  # Quarters highlighted with verticle lines
            for quarter in highlighted_quarters:
                if quarter in visible_quarters:
                    fig.add_vline(x=quarter, line_dash="dash", line_color="red")
    elif visType == "Dummy bar graph":
        fig = px.bar(data, 
                    x="Quarter",
                    y="Value",
                    color="Country",
                    color_discrete_map=country_colours,
                    title="")

    if not show_legend:
        for trace in fig.data:
            trace.showlegend = False
    if second_plot:
        return fig.data
    else:
        return fig

def create_quarterly_fig(data, show_legend, data_option, visType, second_plot, second_data):
    data = data.dropna()
    industries = data["Industry"].unique()
    if len(industries) > 1:  # If multiple industries are selected for GVA
        cols = 2
        rows = math.ceil(len(industries) / cols) # Rounds to nearest integer to calculate amount of rows
        fig = make_subplots(rows=rows, cols=cols, subplot_titles=industries)
        for i, industry in enumerate(industries):
            row = (i // cols) + 1  # Determine row position
            col = (i % cols) + 1  # Determine column position
            industry_data = multi_data_format(data, industry)
            figs = make_fig(industry_data, visType, data_option, second_plot, second_data, show_legend)
            for trace in figs.data:
                trace.showlegend = i == 0  # Show legend only for first subplot
                fig.add_trace(trace, row=row, col=col)
            fig.update_layout(showlegend=show_legend,
                        legend=dict(
                        title="Countries",
                        orientation="v",
                        yanchor="middle", y=0.5,
                        xanchor="left", x=1.02,
                        bgcolor="rgba(255,255,255,0.7)",
                        font=dict(size=12),
                    ),
                    height=300 * rows)
        fig.update_layout(title=f"Gross Value Added by industry ({data_option.base_year} = 100)")  
    elif second_plot:
        if visType == "3D line graph":  # Has to be "scene" instead of "xy" for 3d plot
            fig=make_subplots(rows=1, cols=2, specs=[[{"type": "scene"}, {"type": "scene"}]])
        else:
            fig=make_subplots(rows=1, cols=2, specs=[[{"type": "xy"}, {"type": "xy"}]])

        for trace in make_fig(data, visType, data_option, second_plot, second_data, True):
            # trace.showlegend = False
            fig.add_trace(trace, row=1, col=1)
        for trace in make_fig(second_data, visType, data_option, second_plot, data, False):
            # trace.showlegend = False
            fig.add_trace(trace, row=1, col=2)
        
        if visType != "3D line graph":
            # Determine missing countries (ones in second plot but not first)
            missing_countries = list(set(second_data["Country"]) - set(data["Country"]))
            
            if visType == "QoQ" or visType == "YoY":  # If it is displaying a bar graph
                # Generate hidden traces for missing countries
                # for trace in make_fig(dummy_df, "Dummy bar graph", data_option, second_plot, second_data, show_legend):
                #     trace.visible = "legendonly"  # Hide from graph but keep in legend
                #     fig.add_trace(trace, row=1, col=1)

                countries = list(set(data["Country"]).union(set(second_data["Country"]))) # All countries in both lists
                TPI_colours = ["#eb5e5e", "#39A7DF","#6C2283", "#03969D"]
                if len(countries) <= 4:
                    country_colours = {country: TPI_colours[i % len(TPI_colours)] for i, country in enumerate(countries)}
                else:
                    colour_palette = px.colors.qualitative.Dark2  # Choose a Plotly color set
                    country_colours = {country: colour_palette[i % len(colour_palette)] for i, country in enumerate(countries)}

                selected_quarter = list(data["Quarter"])
                for country in missing_countries:
                    trace = go.Bar(
                        x=[selected_quarter[0]],  # Temp fix - if its in the data selected, it isnt visible on x axis
                        y=[0],
                        name=country,
                        marker=dict(color=country_colours[country]),
                        visible="legendonly",
                        showlegend=True
                    )
                    fig.add_trace(trace, row=1, col=1)
                fig.update_layout( 
                    xaxis_title=f"{data_option.x_axis_title}",
                    yaxis_title=f"{data_option.data_option}",
                    xaxis2_title=f"{data_option.x_axis_title}",
                    yaxis2_title=f"{data_option.data_option}",
                )
            else:  # If it is displaying a 2d line graph
                countries = list(set(data["Country"]).union(set(second_data["Country"]))) # All countries in both lists
                TPI_colours = ["#eb5e5e", "#39A7DF","#6C2283", "#03969D"]
                if len(countries) <= 4:
                    country_colours = {country: TPI_colours[i % len(TPI_colours)] for i, country in enumerate(countries)}
                else:
                    colour_palette = px.colors.qualitative.Dark2  # Choose a Plotly color set
                    country_colours = {country: colour_palette[i % len(colour_palette)] for i, country in enumerate(countries)}
                selected_quarter = list(data["Quarter"])

                for country in missing_countries:
                    trace = go.Scatter(
                        x=[selected_quarter[0]],  # Temp fix - if its in the data selected, it isnt visible on x axis
                        y=[100],
                        mode="lines",
                        name=country,
                        line=dict(color=country_colours.get(country, "#000000")),
                        visible="legendonly",
                        showlegend=True
                    )
                    fig.add_trace(trace, row=1, col=1)
                    
                if data_option.show_dip_lines:
                    visible_quarters = data["Quarter"].unique().tolist() 
                    visible_quarters_two = second_data["Quarter"].unique().tolist() 
                    if not data_option.show_years:
                        highlighted_quarters = ["2007 Q4", "2009 Q2", "2019 Q4", "2021 Q1"]  # Quarters highlighted with verticle lines
                    else:
                        highlighted_quarters = ["2007.75", "2009.25", "2019.75", "2021"]  # Quarters highlighted with verticle lines
                    for quarter in highlighted_quarters:
                        if quarter in visible_quarters:
                            fig.add_vline(x=quarter, line_dash="dash", line_color="red", row=1, col=1)
                        if quarter in visible_quarters_two:
                            fig.add_vline(x=quarter, line_dash="dash", line_color="red", row=1, col=2)
    else:
        fig = make_fig(data, visType, data_option, second_plot, second_data, show_legend)
    if not second_plot:
        fig.update_layout(showlegend=show_legend)
    return fig

def create_yearly_fig(data, show_legend, second_plot, second_data, data_option):
    def yearly_line_graph(data, country_colours):
        return px.line(data, 
        x="Year", 
        y="Value", 
        color="Country",
        color_discrete_map=country_colours,
        title="GDP per Hour Worked Over Time (2015=100)").data
    if second_plot:
        countries = list(set(data["Country"]).union(set(second_data["Country"]))) # All countries in both lists
        TPI_colours = ["#eb5e5e", "#39A7DF","#6C2283", "#03969D"]
        # country_colours = {}
        if len(countries) <= 4:
            country_colours = {country: TPI_colours[i % len(TPI_colours)] for i, country in enumerate(countries)}
        else:
            colour_palette = px.colors.qualitative.Dark2  # Choose a Plotly color set
            country_colours = {country: colour_palette[i % len(colour_palette)] for i, country in enumerate(countries)}

        fig=make_subplots(rows=1, cols=2)
        for trace in yearly_line_graph(data, country_colours):
            fig.add_trace(trace, row=1, col=1)
        for trace in yearly_line_graph(second_data, country_colours):
            trace.showlegend = False
            fig.add_trace(trace, row=1, col=2)
    
        # Determine missing countries (ones in second plot but not first)
        missing_countries = list(set(second_data["Country"]) - set(data["Country"]))
        for country in missing_countries:
            trace = go.Scatter(
                x=["2020 Q1"],  # Fake data
                y=[0],
                mode="lines",
                name=country,
                line=dict(color=country_colours.get(country, "#000000")),
                visible="legendonly",
                showlegend=True
            )
            fig.add_trace(trace, row=1, col=1)
    else:
        fig = px.line(data, 
        x="Year", 
        y="Value", 
        color="Country",
        title=f"GDP per Hour Worked Over Time ({data_option.base_year}=100)")
        fig.update_layout(showlegend=show_legend)
    return fig

def update_selection(option):
    if st.session_state.selected == option:  # If clicked again, deselect
        st.session_state.selected = None
    else:
        st.session_state.selected = option

def multiY_plot(data, quarter, country_selection, base_year):
    st.sidebar.divider()
    st.sidebar.subheader("Configure layout")
    show_years = st.sidebar.toggle(label="Show years instead of quarters", value=False)
    if base_year != 2020:
        data = rebase_chain_linked_quarters(data, base_year)
    quarter = list(quarter)
    quarter[0] = quarter_to_numeric(quarter[0])
    quarter[1] = quarter_to_numeric(quarter[1])
    OPH = data.query(
            f"Quarter >= {quarter[0]} and Quarter <= {quarter[1]} and Country == '{country_selection}' and Variable == 'Output Per Hour'").copy()

    OPW = data.query(
            f"Quarter >= {quarter[0]} and Quarter <= {quarter[1]} and Country == '{country_selection}' and Variable == 'Output Per Worker'").copy()

    GVA = data.query(
            f"Quarter >= {quarter[0]} and Quarter <= {quarter[1]} and Country == '{country_selection}' and Variable == 'Gross Value Added' and Industry == 'Total'").copy()
    if not show_years:
        OPH['Quarter'] = OPH['Quarter'].apply(numeric_to_quarter)
        OPW['Quarter'] = OPW['Quarter'].apply(numeric_to_quarter)
        GVA['Quarter'] = GVA['Quarter'].apply(numeric_to_quarter)

    quarters = OPH['Quarter']

    fig = go.Figure()

    # Profit trace (left y-axis, green)
    fig.add_trace(go.Scatter(
        x=quarters, y=OPH['Value'], name="OPH",
        yaxis="y", mode="lines+markers",
        line=dict(color="green")
    ))

    # Orders trace (left overlay, orange)
    fig.add_trace(go.Scatter(
        x=quarters, y=OPW['Value'], name="OPW",
        yaxis="y2", mode="lines+markers",
        line=dict(color="orange")
    ))

    # Sales trace (right y-axis, blue)
    fig.add_trace(go.Scatter(
        x=quarters, y=GVA['Value'], name="GVA",
        yaxis="y3", mode="lines+markers",
        line=dict(color="dodgerblue")
    ))

    # Layout with multiple y-axes
    fig.update_layout(
        title_text=f"OPH vs OPW vs GVA for {country_selection}",
        xaxis=dict(
            title="Quarters",
            showgrid=False
        ),
        yaxis=dict(
            title=dict(
                text="Output Per Hour",
                font=dict(color="green")
            ),
            tickfont=dict(color="green"),
            side="left",
            position=0,
        ),
        yaxis2=dict(
            title=dict(
                text="Output Per Worker",
                font=dict(color="orange")
            ),
            tickfont=dict(color="orange"),
            overlaying="y",
            side="left",
            position=0.06,
            showgrid=False
        ),
        yaxis3=dict(
            title=dict(
                text="Gross Value Added",
                font=dict(color="dodgerblue")
            ),
            tickfont=dict(color="dodgerblue"),
            overlaying="y",
            side="right",
            position=1,
            showgrid=False
        ),
        legend=dict(
            x=0.5,
            y=1.15,
            xanchor="center",
            orientation="h"
        ),
        margin=dict(t=100),
    )
    return fig

def multi_y_mode(quarterly_data, key):
    QorY = st.sidebar.radio(
        label="Select data to plot",
        options=["Quarterly"],
        captions=[
            "Quarterly labour productivity",
        ],
        key=f"QorY_MultiY_{key}"
        )
    quarters = quarterly_data["Quarter"].unique()
    quarters = [numeric_to_quarter(x) for x in quarters]
    quarter = st.sidebar.select_slider(label = "Quarterly slider", options = quarters, value=(quarters[0], quarters[-1]), label_visibility="collapsed", key=f"Q_Slider_multiy_{key}")
    countries = quarterly_data["Country"].unique()
    countries = sorted(countries, key=lambda x: (x not in ["UK", "US", "Euro Area", "European Union"], x))
    country_selection = st.sidebar.selectbox(label= "Select Country", options=countries, key=f"Country_Option_multi_y_{key}")
    base_year_options = list(range(1997, 2025))
    base_year = st.sidebar.selectbox(label="Change the base year? (default set to 2020)", options=base_year_options, index=base_year_options.index(2020), key=f"base_year_multiY_{key}")
    return QorY, quarter, country_selection, base_year

def apply_size(fig, size_factor=1.0):
    width = int(600 * size_factor)
    height = int(400 * size_factor)
    fig.update_layout(width=width, height=height)
    return fig

def visualisation_selection(quarterly_data, yearly_data, key, lock_quarterly):
    st.sidebar.divider()
    st.sidebar.subheader("Select data to plot")
    # multiY_option = st.sidebar.radio(  # Changed my mind about this
    #     label="Select visualisation mode:",
    #     options=["Multiple Countries", "Single Country"],
    #     key=f"MultiY_{key}"
    # )
    # if multiY_option == "Single Country":
    #     QorY, quarter, country_selection, base_year = multi_y_mode(quarterly_data, key)
    #     return QorY, quarter, None, None, None, None, country_selection, "multiY", base_year

    if lock_quarterly:
        QorY = st.sidebar.radio(
            label="Select data to plot",
            options=["Yearly"],
            captions=[
                "Yearly labour productivity",
            ],
            key=f"QorY_{key}"
            )
    else:
        QorY = st.sidebar.radio(
            label="Select data to plot",
            options=["Quarterly", "Yearly"],
            captions=[
                "Quarterly labour productivity",
                "Yearly labour productivity",
            ],
            key=f"QorY_{key}"
        )
    if QorY == "Quarterly":
        st.session_state.show_quarter_slider_two = True
    elif QorY == "Yearly":
        st.session_state.show_yearly_slider_two = True
    
    # Quarter time series selection
    quarterly_option = None
    quarter = None
    industry_selection = ["Total"]
    if st.session_state.show_quarter_slider_two:
        quarters = quarterly_data["Quarter"].unique()
        quarters = [numeric_to_quarter(x) for x in quarters]
        quarter = st.sidebar.select_slider(label = "Quarterly slider", options = quarters, value=(quarters[0], quarters[-1]), label_visibility="collapsed", key=f"Q_Slider_{key}")
        quarterly_options = ["Output Per Hour", "Output Per Worker", "Gross Value Added"]
        quarterly_option = st.sidebar.selectbox(label= "Select data", options=quarterly_options, key=f"Q_Option_{key}")
        industry_selection = ["Total"]
        if quarterly_option == "Gross Value Added":
            industry_options = quarterly_data["Industry"].unique()
            industry_options = industry_options[~pd.isna(industry_options)] 
            industry_selection = st.sidebar.multiselect(label="Select industry", options=industry_options, default=["Total"], key=f"Industry_Selection_{key}")

    # Year time series selection
    yearly_option = None
    year = None
    if st.session_state.show_yearly_slider_two:
        year = st.sidebar.slider(label="Yearly slider!", min_value=yearly_data["Year"].iat[0], max_value=max(yearly_data["Year"]), value=[yearly_data["Year"].iat[0], max(yearly_data["Year"])], label_visibility="collapsed", key=f"Y_Slider_{key}")
        if year[0] == year[1]:
            year = [year[0], year[0] + 1] if year[0] < max(yearly_data["Year"]) else [year[0] - 1, year[0]]
        yearly_option = yearly_options = ["Output per hour"]
        st.sidebar.selectbox(label= "Select data", options=yearly_options, key=f"Y_Option_{key}")

    quarterly_selection = None
    if QorY == "Quarterly":
        countries = quarterly_data["Country"].unique()
        countries = sorted(countries, key=lambda x: (x not in ["UK", "US", "Euro Area", "European Union"], x))
        default_options = ["UK", "US", "Germany", "France", "Italy", "Spain"]
        country_selection = st.sidebar.multiselect(label = "Select countries to display", options = countries, default=default_options, key=f"country_selection_{key}")

        # Only show data options below if quarterly format is selected
        st.sidebar.write("Select data view options")
        st.sidebar.write("Line graph")
        st.sidebar.checkbox("2D line graph", 
        value=(st.session_state.selected == "2D line graph"), 
        on_change=lambda opt="2D line graph": update_selection(opt), key=f"2d_line_graph{key}")

        if len(industry_selection) == 1:
            st.sidebar.checkbox("3D line graph", 
            value=(st.session_state.selected == "3D line graph"), 
            on_change=lambda opt="3D line graph": update_selection(opt), key=f"3d_line_graph{key}")

        st.sidebar.write("Bar graph")
        st.sidebar.checkbox("Quarter on quarter", 
        value=(st.session_state.selected == "Quarter on quarter"), 
        on_change=lambda opt="Quarter on quarter": update_selection(opt), key=f"qoq_graph{key}")

        st.sidebar.checkbox("Year on year", 
        value=(st.session_state.selected == "Year on year"), 
        on_change=lambda opt="Year on year": update_selection(opt), key=f"yoy_graph{key}")
        if st.session_state.selected == "Year on year":
            quarterly_selection = st.sidebar.selectbox(label= "Specific quarter comparison", options=[1, 2, 3, 4], key=f"quarterly_selection_{key}")

    elif QorY == "Yearly":
        # Extract country names by removing the option part
        countries= yearly_data["Country"].unique()

        default_options = ["US", "UK", "Germany", "France", "Italy", "Spain"]
        country_selection = st.sidebar.multiselect(label = "Select countries to display", options = countries, default=default_options, key=f"country_selection_{key}")

    visType = "2D line graph"
    if st.session_state.selected == "Quarter on quarter":
        visType = "QoQ"
    elif st.session_state.selected == "Year on year":
        visType = "YoY"
    elif st.session_state.selected == "2D line graph":
        visType = "2D line graph"
    elif st.session_state.selected == "3D line graph":
        visType = "3D line graph"

    if QorY == "Quarterly":
        data_option = quarterly_option
    elif QorY == "Yearly":
        data_option = yearly_option
    
    # Base year selecter 
    base_year_options = list(range(1997, 2025))
    base_year = st.sidebar.selectbox(label="Change the base year? (default set to 2020)", options=base_year_options, index=base_year_options.index(2020), key=f"base_year_{key}")
    return QorY, quarter, data_option, industry_selection, year, quarterly_selection, country_selection, visType, base_year

@st.cache_data
def load_data():
    yearly_data = pd.read_csv("out/OPH_Processed.csv")
    quarterly_data = pd.read_csv("out/Long_Dataset.csv")
    return quarterly_data, yearly_data

def initialise_app():
    # Set session state variables
    st.session_state.show_quarter_slider = False
    st.session_state.show_yearly_slider = False
    st.session_state.show_quarter_slider_two = False
    st.session_state.show_yearly_slider_two = False
    if "selected" not in st.session_state:
        st.session_state.selected = "2D line graph"

    # Set page configuration
    st.set_page_config(layout="wide", page_title="TPI Quarterly Data Tool")
    # Page formatting
    st.sidebar.html("<a href='https://lab.productivity.ac.uk' alt='The Productivity Lab'></a>")
    st.logo("static/logo.png", link="https://lab.productivity.ac.uk/", icon_image=None)

def export_data_button(data):
    # Export functionality
    if st.sidebar.button("Export Selected Data"):
        @st.cache_data
        def convert_df(df):
            return df.to_csv(index=False).encode("utf-8")
        
        csv = convert_df(data)
        st.sidebar.download_button(
            label="Download data as CSV",
            data=csv,
            file_name="productivity_data.csv",
            mime="text/csv",
        )

def create_refresh_button():
    if st.sidebar.button("Reset To Default Settings"):
        # Use JavaScript to refresh the entire page
        js_code = """
        <script>
            window.parent.location.reload();
        </script>
        """
        st.components.v1.html(js_code, height=0, width=0)

def main_code():
    # Load datasets
    quarterly_data, yearly_data = load_data()

    # First plot
    key = 1
    QorY, quarter, data_option, industry_selection, year, quarterly_selection, country_selection, visType, base_year = visualisation_selection(quarterly_data, yearly_data, key, False)
    if visType == "multiY":
        multiY = True
    else:
        multiY = False
    if not multiY:
        if QorY == "Quarterly":
            data = quarterly_data
        elif QorY == "Yearly":
            data = yearly_data

        second_plot = False
        # Second plot options
        if len(industry_selection) == 1:
            st.sidebar.divider()
            second_plot = st.sidebar.toggle(label="Show a second plot side by side")
            if second_plot:
                key = 2  # Need a key for duplicated streamlit components (the sidebar options)
                if QorY == "Yearly":
                    lock_quarterly = True
                else:
                    lock_quarterly = False
                QorY_two, quarter_two, data_option_two, industry_selection_two, year_two, quarterly_selection_two, country_selection_two, visType_two, base_year_two = visualisation_selection(quarterly_data, yearly_data, key, lock_quarterly)

        #Figure formatting tools
        st.sidebar.divider()
        st.sidebar.subheader("Configure layout")
        show_legend = st.sidebar.toggle(label="Show legend", value=True)
        hide_grid_lines = True
        if visType == "2D line graph" and QorY == "Quarterly" and len(industry_selection) == 1:
            show_dip_lines = st.sidebar.toggle(label="Show verticle lines for major dips in productivity", value=False)
        else:
            show_dip_lines = False
        if QorY == "Quarterly" and visType != '3D line graph':
            show_years = st.sidebar.toggle(label="Show years instead of quarters", value=False)
            hide_grid_lines = st.sidebar.toggle(label="Hide grid lines", value=False)
            hide_grid_lines = not hide_grid_lines  # Has to be the other way round
        else:
            show_years = False
        if show_years:
            x_axis_title = 'Year'
        else:
            x_axis_title = 'Quarter'
        
        # Load main content (not in sidebars)
        st.header("TPI Quarterly Data Tool for US, UK and European labour productivity")
        plot_one_data_option = data_options(QorY, data_option, base_year, quarterly_selection, show_years, show_dip_lines, x_axis_title)
        if second_plot:
            plot_two_data_option = data_options(QorY_two, data_option_two, base_year_two, quarterly_selection_two, show_years, show_dip_lines, x_axis_title)
        if QorY == "Quarterly":
            formatted_data = data_format(data, QorY, quarter, plot_one_data_option, country_selection, visType, quarterly_selection, industry_selection)
            formatted_data_two = None
            if second_plot:
                formatted_data_two = data_format(data, QorY_two, quarter_two, plot_two_data_option, country_selection_two, visType_two, quarterly_selection_two, industry_selection_two)
            fig = create_quarterly_fig(formatted_data, show_legend, plot_one_data_option, visType, second_plot, formatted_data_two)
            if second_plot:
                fig.update_layout(title=f"Side-by-side comparison of {plot_one_data_option.data_option} against {plot_two_data_option.data_option}")  # remove - change this
        else:
            formatted_data = data_format(data, QorY, year, plot_one_data_option, country_selection, False)
            formatted_data_two = None
            if second_plot:
                formatted_data_two = data_format(data, QorY_two, year_two, plot_two_data_option, country_selection_two, False)
            fig = create_yearly_fig(formatted_data, show_legend, second_plot, formatted_data_two, plot_one_data_option) 
        
        # Provides a button to download data
        export_data_button(data)
        create_refresh_button()
    else:
        fig = multiY_plot(quarterly_data, quarter, country_selection, base_year)

    size = st.query_params.get("size")
    if size:
        fig = apply_size(fig, float(st.query_params["size"]))
    figure = st.empty()
    # Display the figure
    if fig:
        fig.update_layout(showlegend=show_legend)
        fig.update_yaxes(showgrid=hide_grid_lines)
        # Save session state variables and load figure
        with st.spinner("Loading visualisation"):
            st.session_state.fig = fig
            figure.plotly_chart(st.session_state.fig, width='stretch',                 
                config={
                    "toImageButtonOptions": {
                        "format": "png",
                        "filename": f"{visType}",
                        "height": 600,
                        "width": 1300,
                        "scale": 5
                    }
                })

def main():
    # Initialise app
    initialise_app()

    tab1, tab2 = st.tabs(["Quarterly Data Tool", "About this tool"])
    with tab1:
        main_code()
    with tab2:
        st.markdown(
            """
            ## TPI Quarterly Data Tool
            **Developed by the [TPI Productivity Lab](https://lab.productivity.ac.uk/), this tool allows for the quick creation of graphs of quarterly and yearly productivity data on a national scale.**

            **For more information about the sources and methods for this tool, read the accompanying document linked [here](https://doi.org/10.48420/29230796/)**

            ### Customisation Options
            #### Data options
            - **Quarterly or Yearly selection**: Allows for the option of data to be shown as either quarterly or yearly
            - **Select time period**: change the time period selected
            - **Select data**: choose the productivity measure to be visualised
            - **Choose countries**: choose the countries selected from a large list containing many European countries, as well as the US
            #### Quarterly data specific options
            ##### Quarterly 2D line graph
            - Plots all selected data as a line graph
            - GVA provides data options for multiple sectors:
                - If only sector is selected, a single graph will be displayed
                - If multiple are selected, multiple plots will be displayed side by side
                - More information about the sectoral options is shown in the sources and methods and document
            ##### Quarterly 3D line graph
            - Plots all selected data as a 3D line graph
            ##### QoQ bar graph
            - Plots all selected data as a bar graph showing Quarter on Quarter (QoQ) change as a percentage
            ##### YOY bar graph
            - Plots all selected data as a bar graph showing Year on Year (YoY) change as a percentage
            - Allows for selection of the specific quarter to be compared (if the 4th quarter is selected, it will show percentage change of the indicator selected between the 4th quarters of the years selected)
            #### Formatting
            - **Show legend**: Choose whether the legend is to be shown in the visualisation
            - **Show verticle lines for major dips in productivity**: Choose whether to show verticle lines positioned before and after the 2007 recession and covid-19
            - **Show years instead of quarters**: Choose to show the x-axis of the visualisation as years instead of quarters - the data represented is still quarterly data but it can make the visualisation clearer
            - **Hide grid lines**: Choose to not display horizontal grid lines in the visualisation
            """
        )


if __name__ == "__main__":
    main()
