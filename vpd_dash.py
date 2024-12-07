from io import BytesIO
from zipfile import ZipFile

import pandas as pd
import plotly.express as px
import requests
import streamlit as st
from colorhash import ColorHash
from pyproj import Proj

url = "https://geodash.vpd.ca/opendata/crimedata_download/AllNeighbourhoods_AllYears/crimedata_csv_AllNeighbourhoods_AllYears.zip"


@st.cache_data
def load_data():
    with (
        requests.get(url) as r,
        ZipFile(BytesIO(r.content)) as z,
        z.open("crimedata_csv_AllNeighbourhoods_AllYears.csv") as f,
    ):
        return pd.read_csv(f)


def main():
    st.set_page_config("Vancouver Crime Data", layout="wide")
    st.title(f"Vancouver Crime Data [:material/download:]({url})")

    data = load_data()

    data["date"] = pd.to_datetime(data[["YEAR", "MONTH", "DAY", "HOUR", "MINUTE"]])

    # Map X and Y to lon and lat
    p = Proj("+proj=utm +zone=10 +datum=WGS84 +units=m +no_defs +type=crs")
    data.X = data.X.replace(0, None)
    data.Y = data.Y.replace(0, None)
    data["lon"], data["lat"] = p(data.X, data.Y, inverse=True, errcheck=True)

    col1, col2, col3 = st.columns(3)

    neighbourhoods = col1.multiselect(
        "Neighbourhoods", options=sorted(data.NEIGHBOURHOOD.dropna().unique())
    )

    crime_types = col2.multiselect("Types of crimes", data.TYPE.unique())

    year_range = col3.slider(
        "Date range",
        data.YEAR.min(),
        data.YEAR.max(),
        (data.YEAR.min(), data.YEAR.max()),
    )

    data = data[
        data.YEAR.between(*year_range)
        & ((not neighbourhoods) | (data.NEIGHBOURHOOD.isin(neighbourhoods)))
        & ((not crime_types) | (data.TYPE.isin(crime_types)))
    ]

    st.subheader("Crimes by year")
    st.plotly_chart(
        px.line(
            data.YEAR.value_counts().reset_index().sort_values("YEAR"),
            x="YEAR",
            y="count",
        )
    )

    st.subheader("Crimes by type")
    st.plotly_chart(
        px.line(
            data[["YEAR", "TYPE"]].value_counts().reset_index().sort_values("YEAR"),
            x="YEAR",
            y="count",
            color="TYPE",
            category_orders={"TYPE": sorted(data.TYPE.dropna().unique())},
            height=800,
        )
    )

    st.subheader("Crimes by neighbourhood")
    st.plotly_chart(
        px.line(
            data[["YEAR", "NEIGHBOURHOOD"]]
            .value_counts()
            .reset_index()
            .sort_values("YEAR"),
            x="YEAR",
            y="count",
            color="NEIGHBOURHOOD",
            category_orders={
                "NEIGHBOURHOOD": sorted(data.NEIGHBOURHOOD.dropna().unique())
            },
            height=800,
        )
    )

    COLOR_COLUMN = "TYPE"
    COLOR_MAP = {k: ColorHash(k).hex for k in data[COLOR_COLUMN].unique()}

    st.subheader("Crimes by type")
    type_data = data.TYPE.value_counts().to_frame()
    type_data["color"] = type_data.index.map(COLOR_MAP)
    st.bar_chart(type_data, horizontal=True, y="count", color="color")

    map_data = data[data["lat"].notna() & data["lon"].notna()]
    map_data["color"] = map_data[COLOR_COLUMN].map(COLOR_MAP)

    st.subheader("Map of crimes")
    st.map(
        map_data.value_counts(["lat", "lon", "color"]).to_frame().reset_index(),
        size="count",
        color="color",
        height=800,
    )


if __name__ == "__main__":
    main()
