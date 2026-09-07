
import streamlit as st
import pandas as pd
import plotly.express as px
import requests
from io import StringIO
import country_converter as coco


# ============================================================
# PAGE CONFIGURATION
# ============================================================

st.set_page_config(
    page_title="Country Development Dashboard",
    page_icon="🌍",
    layout="wide"
)


# ============================================================
# DATA LOADING FUNCTION
# ============================================================

@st.cache_data
def load_data():

    # --------------------------------------------------------
    # Our World in Data:
    # Life expectancy vs GDP per capita
    # --------------------------------------------------------

    life_gdp_url = (
        "https://ourworldindata.org/grapher/"
        "life-expectancy-vs-gdp-per-capita.csv"
        "?v=1&csvType=full&useColumnShortNames=false"
    )

    # --------------------------------------------------------
    # Our World in Data:
    # Population
    # --------------------------------------------------------

    population_url = (
        "https://ourworldindata.org/grapher/"
        "population.csv"
        "?v=1&csvType=full&useColumnShortNames=false"
    )

    # Browser-style / OWID User-Agent
    headers = {
        "User-Agent": "Our World In Data data fetch/1.0"
    }

    # Download Life Expectancy + GDP dataset
    life_response = requests.get(
        life_gdp_url,
        headers=headers,
        timeout=60
    )
    life_response.raise_for_status()

    life_gdp = pd.read_csv(
        StringIO(life_response.text)
    )

    # Download population dataset
    pop_response = requests.get(
        population_url,
        headers=headers,
        timeout=60
    )
    pop_response.raise_for_status()

    population = pd.read_csv(
        StringIO(pop_response.text)
    )

    # --------------------------------------------------------
    # Identify important columns
    # --------------------------------------------------------

    # The OWID dataset contains:
    # Entity, Code, Year, Life expectancy, GDP per capita

    life_gdp = life_gdp.rename(
        columns={
            "Entity": "country",
            "Code": "code",
            "Year": "year"
        }
    )

    # Detect life expectancy and GDP columns automatically
    life_col = [
        c for c in life_gdp.columns
        if "Life expectancy" in c
    ][0]

    gdp_col = [
        c for c in life_gdp.columns
        if "GDP per capita" in c
    ][0]

    life_gdp = life_gdp.rename(
        columns={
            life_col: "lifeExp",
            gdp_col: "gdpPercap"
        }
    )

    # --------------------------------------------------------
    # Prepare population data
    # --------------------------------------------------------

    population = population.rename(
        columns={
            "Entity": "country",
            "Code": "code",
            "Year": "year"
        }
    )

    # Find population column
    population_columns = [
        c for c in population.columns
        if c not in ["country", "code", "year"]
    ]

    population_col = population_columns[0]

    population = population.rename(
        columns={
            population_col: "pop"
        }
    )

    # Keep only required columns
    population = population[
        ["country", "code", "year", "pop"]
    ]

    # Remove duplicate country-year records
    population = population.drop_duplicates(
        subset=["code", "year"]
    )

    # --------------------------------------------------------
    # Merge life expectancy/GDP with population
    # --------------------------------------------------------

    df = pd.merge(
        life_gdp[
            ["country", "code", "year", "lifeExp", "gdpPercap"]
        ],
        population,
        on=["country", "code", "year"],
        how="left"
    )

    # --------------------------------------------------------
    # Add continent information
    # --------------------------------------------------------

    df["continent"] = coco.convert(
        df["code"],
        to="continent"
    )

    # country_converter can return "not found"
    # Replace those values with missing
    df["continent"] = df["continent"].replace(
        "not found",
        pd.NA
    )

    # Remove rows with missing values required by dashboard
    df = df.dropna(
        subset=[
            "country",
            "year",
            "lifeExp",
            "gdpPercap",
            "pop",
            "continent"
        ]
    )

    # Make sure numeric columns are numeric
    df["year"] = pd.to_numeric(
        df["year"],
        errors="coerce"
    )

    df["lifeExp"] = pd.to_numeric(
        df["lifeExp"],
        errors="coerce"
    )

    df["gdpPercap"] = pd.to_numeric(
        df["gdpPercap"],
        errors="coerce"
    )

    df["pop"] = pd.to_numeric(
        df["pop"],
        errors="coerce"
    )

    # Remove invalid values
    df = df.dropna(
        subset=[
            "year",
            "lifeExp",
            "gdpPercap",
            "pop"
        ]
    )

    # GDP must be positive because log scale is used
    df = df[df["gdpPercap"] > 0]

    # Sort data
    df = df.sort_values(
        ["country", "year"]
    )

    return df


# ============================================================
# LOAD DATA
# ============================================================

try:
    df = load_data()

except Exception as e:
    st.error(
        "Unable to load the Our World in Data datasets."
    )
    st.exception(e)
    st.stop()


# ============================================================
# TITLE
# ============================================================

st.title("🌍 Country Development Dashboard")

st.markdown(
    """
Explore the relationship between **GDP per capita, life expectancy,
population and continent** using data from Our World in Data.
"""
)


# ============================================================
# SIDEBAR FILTERS
# ============================================================

st.sidebar.header("🔎 Filters")

# ------------------------------------------------------------
# Year filter
# ------------------------------------------------------------

years = sorted(
    df["year"].astype(int).unique()
)

selected_year = st.sidebar.select_slider(
    "Year",
    options=years,
    value=years[-1]
)

# ------------------------------------------------------------
# Continent filter
# ------------------------------------------------------------

continents = sorted(
    df["continent"].dropna().unique()
)

selected_continents = st.sidebar.multiselect(
    "Continent",
    options=continents,
    default=continents
)

# ------------------------------------------------------------
# Minimum population filter
# ------------------------------------------------------------

population_max = int(
    df["pop"].max()
)

population_step = max(
    int(population_max / 100),
    1
)

min_population = st.sidebar.slider(
    "Minimum Population",
    min_value=0,
    max_value=population_max,
    value=0,
    step=population_step,
    format="%d"
)


# ============================================================
# FILTER DATA
# ============================================================

filtered = df[
    (df["year"].astype(int) == selected_year)
    & (df["continent"].isin(selected_continents))
    & (df["pop"] >= min_population)
].copy()


# ============================================================
# CHECK WHETHER DATA EXISTS
# ============================================================

if filtered.empty:

    st.warning(
        "No countries match the selected filters. "
        "Please adjust the continent or population filter."
    )

    st.stop()


# ============================================================
# KPI CARDS
# ============================================================

col1, col2, col3 = st.columns(3)

# Number of countries
country_count = filtered["country"].nunique()

# Median life expectancy
median_life_exp = filtered["lifeExp"].median()

# Total population
total_population = filtered["pop"].sum()

col1.metric(
    "Countries Shown",
    f"{country_count:,}"
)

col2.metric(
    "Median Life Expectancy",
    f"{median_life_exp:.1f} years"
)

col3.metric(
    "Total Population",
    f"{total_population / 1e9:.2f} B"
)


# ============================================================
# MAIN SCATTER CHART
# ============================================================

st.subheader("GDP per Capita vs Life Expectancy")

fig = px.scatter(
    filtered,
    x="gdpPercap",
    y="lifeExp",
    size="pop",
    color="continent",
    hover_name="country",
    log_x=True,
    size_max=60,
    title=(
        f"GDP per Capita vs Life Expectancy - "
        f"{selected_year}"
    ),
    labels={
        "gdpPercap": "GDP per Capita",
        "lifeExp": "Life Expectancy (years)",
        "pop": "Population",
        "continent": "Continent"
    }
)

fig.update_layout(
    height=600
)

st.plotly_chart(
    fig,
    use_container_width=True
)


# ============================================================
# DRILL-DOWN SECTION
# ============================================================

st.subheader("🔍 Drill Down into a Country")

available_countries = sorted(
    filtered["country"].unique()
)

country_pick = st.selectbox(
    "Choose a country",
    available_countries
)

country_hist = df[
    df["country"] == country_pick
].sort_values("year")


# ------------------------------------------------------------
# Country life expectancy chart
# ------------------------------------------------------------

fig2 = px.line(
    country_hist,
    x="year",
    y="lifeExp",
    markers=True,
    title=(
        f"Life Expectancy Over Time - "
        f"{country_pick}"
    ),
    labels={
        "year": "Year",
        "lifeExp": "Life Expectancy (years)"
    }
)

fig2.update_layout(
    height=450
)

st.plotly_chart(
    fig2,
    use_container_width=True
)


# ============================================================
# DATA SOURCE
# ============================================================

st.markdown("---")

st.caption(
    "Data source: Our World in Data — "
    "Life expectancy vs. GDP per capita and population datasets."
)


# Lab 4 update: Dashboard version controlled using Git and GitHub.
