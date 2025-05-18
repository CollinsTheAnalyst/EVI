import streamlit as st
import geemap.foliumap as geemap  # type: ignore # or geemap.foliumap depending on your backend
import ee
import pandas as pd
from datetime import date

# Initialize Earth Engine
ee.Initialize(project='ee-collinsmwiti98')

# Load GEE Assets
farmer_data = {
    'homabay': ee.FeatureCollection("projects/ee-collinsmwiti98/assets/homabayfarms"),
}

# Streamlit UI
st.title("NDVI Time Series for Farmers")

# Farmer dropdown
def get_farmer_names(fc):
    return fc.aggregate_array('Farmer').distinct().getInfo()

farmer_names = get_farmer_names(farmer_data['homabay'])
selected_farmer = st.selectbox("Select Farmer", farmer_names)
ndvi_evi = st.selectbox("Select Metric", ["NDVI", "EVI"])
start_date = st.date_input("Start Date", value=date(2023, 1, 1))
end_date = st.date_input("End Date", value=date(2023, 12, 31))

# Convert to ee.Date
ee_start = ee.Date(str(start_date))
ee_end = ee.Date(str(end_date))

# Select farm feature
selected_feature = farmer_data['homabay'].filter(ee.Filter.eq('Farmer', selected_farmer)).first()

# ----------------------------
# 🗺️ SECTION: Display Farm Map
# ----------------------------
st.subheader("Farm Location Map")

Map = geemap.Map(center=[-0.42, 34.7], zoom=10, basemap='HYBRID')
Map.addLayer(selected_feature.geometry(), {'color': 'yellow'}, f"{selected_farmer}'s Farm")
Map.centerObject(selected_feature, 16)
Map.to_streamlit(height=500)

# --------------------------------
# 📈 SECTION: NDVI/EVI Time Series
# --------------------------------
def get_ndvi_timeseries(feature, metric, start, end):
    col = ee.ImageCollection('MODIS/006/MOD13Q1') \
        .filterBounds(feature.geometry()) \
        .filterDate(start, end) \
        .map(lambda img: img.select([metric]).multiply(0.0001).copyProperties(img, ['system:time_start']))

    ts = col.map(lambda img: ee.Feature(None, {
        'date': ee.Date(img.get('system:time_start')).format('YYYY-MM-dd'),
        'value': img.reduceRegion(ee.Reducer.mean(), feature.geometry(), 250).get(metric)
    }))

    features = ts.getInfo()['features']
    dates = [f['properties']['date'] for f in features]
    values = [f['properties']['value'] for f in features]

    df = pd.DataFrame({'Date': dates, metric: values})
    return df

df = get_ndvi_timeseries(selected_feature, ndvi_evi, ee_start, ee_end)

st.subheader(f"{ndvi_evi} Time Series for {selected_farmer}")
st.line_chart(df.set_index("Date"))

# 📥 Download CSV
st.download_button("📥 Download CSV", df.to_csv(index=False), file_name=f"{selected_farmer}_{ndvi_evi}_timeseries.csv")
