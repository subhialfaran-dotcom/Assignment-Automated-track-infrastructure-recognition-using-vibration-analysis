import os
import pandas as pd
import plotly.graph_objects as go

# File paths
base_path = r"C:\Users\subhi\Downloads\Assigment 4\Data 1"

files = {
    "Bridge": os.path.join(base_path, "converted_coordinates_Resultat_Bridge.csv"),
    "RailJoint": os.path.join(base_path, "converted_coordinates_Resultat_RailJoint.csv"),
    "Turnout": os.path.join(base_path, "converted_coordinates_Turnout.csv"),
}

marker_styles = {
    "Bridge": {"color": "red", "size": 10},
    "RailJoint": {"color": "blue", "size": 8},
    "Turnout": {"color": "green", "size": 12},
}
# Load data
data_frames = []

for category, path in files.items():
    df = pd.read_csv(path)
    df = df[["Latitude", "Longitude"]].copy()
    df["Latitude"] = pd.to_numeric(df["Latitude"], errors="coerce")
    df["Longitude"] = pd.to_numeric(df["Longitude"], errors="coerce")
    df = df.dropna(subset=["Latitude", "Longitude"])
    df["Category"] = category
    data_frames.append(df)
    print(f"Loaded {category}: {len(df)} rows")

data = pd.concat(data_frames, ignore_index=True)

# Create map
fig = go.Figure()

for category, style in marker_styles.items():
    category_data = data[data["Category"] == category]

    fig.add_trace(go.Scattermapbox(
        lat=category_data["Latitude"],
        lon=category_data["Longitude"],
        mode="markers",
        marker=dict(color=style["color"], size=style["size"]),
        name=category
    ))

fig.update_layout(
    mapbox_style="open-street-map",
    title="Infrastructure Events (Data 1)",
    width=1200,
    height=800,
    mapbox=dict(
        zoom=10,
        center=dict(
            lat=data["Latitude"].mean(),
            lon=data["Longitude"].mean()
        )
    )
)
fig.show()
fig.write_html("map_data1.html")
print("Saved: map_data1.html")
