from io import BytesIO
from zipfile import ZipFile

import pandas as pd
import requests
import streamlit as st
from colorhash import ColorHash
from pyproj import Proj


@st.cache_data
def load_data():
    url = "https://geodash.vpd.ca/opendata/crimedata_download/AllNeighbourhoods_AllYears/crimedata_csv_AllNeighbourhoods_AllYears.zip"

    with (
        requests.get(url) as r,
        ZipFile(BytesIO(r.content)) as z,
        z.open("crimedata_csv_AllNeighbourhoods_AllYears.csv") as f,
    ):
        return pd.read_csv(f)


def main():
    st.title("Vancouver Crime Data")

    data = load_data()

    if st.checkbox("Show raw data"):
        st.subheader("Raw data")
        st.write(data)

    data["date"] = pd.to_datetime(data[["YEAR", "MONTH", "DAY", "HOUR", "MINUTE"]])

    # Map X and Y to lon and lat
    p = Proj("+proj=utm +zone=10 +datum=WGS84 +units=m +no_defs +type=crs")
    data.X = data.X.replace(0, None)
    data.Y = data.Y.replace(0, None)
    data["lon"], data["lat"] = p(data.X, data.Y, inverse=True, errcheck=True)

    year_range = st.slider(
        "Year range",
        data.YEAR.min(),
        data.YEAR.max(),
        (data.YEAR.min(), data.YEAR.max()),
    )

    crime_types = st.multiselect("Types of crimes", data.TYPE.unique())

    data = data[
        data.YEAR.between(*year_range)
        & ((not crime_types) | (data.TYPE.isin(crime_types)))
    ]

    st.subheader("Crimes by hour")
    st.bar_chart(data.HOUR.value_counts())

    st.subheader("Crimes by year")
    st.bar_chart(data.YEAR.value_counts())

    COLOR_COLUMN = "TYPE"
    COLOR_MAP = {k: ColorHash(k).hex for k in data[COLOR_COLUMN].unique()}

    st.subheader("Crimes by type")
    type_data = data.TYPE.value_counts().to_frame()
    type_data["color"] = type_data.index.map(COLOR_MAP)
    st.bar_chart(type_data, y="count", color="color")

    map_data = data[data["lat"].notna() & data["lon"].notna()]
    map_data["color"] = map_data[COLOR_COLUMN].map(COLOR_MAP)

    st.subheader("Map of crimes")
    st.map(
        map_data.value_counts(["lat", "lon", "color"]).to_frame().reset_index(),
        size="count",
        color="color",
    )


if __name__ == "__main__":
    main()
