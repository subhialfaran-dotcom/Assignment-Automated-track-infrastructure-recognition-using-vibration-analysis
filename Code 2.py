import os
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
import dash
from dash import dcc, html, Input, Output
import tkinter as tk
from tkinter import filedialog

# Data Loading 
root = tk.Tk()
root.withdraw()

files = {
    "latitude": None,
    "longitude": None,
    "vibration1": None,
    "vibration2": None,
    "speed": None
}

def load_file(key):
    file_path = filedialog.askopenfilename(filetypes=[("CSV Files", "*.csv")])
    if file_path:
        files[key] = file_path
        print(f"{key.capitalize()} file loaded: {file_path}")

print("Select Latitude File");   load_file("latitude")
print("Select Longitude File");  load_file("longitude")
print("Select Vibration 1 File");load_file("vibration1")
print("Select Vibration 2 File");load_file("vibration2")
print("Select Speed File");      load_file("speed")

# Load each CSV into a DataFrame
dataframes = {}
for key, file_path in files.items():
    if file_path:
        df = pd.read_csv(file_path, header=None, names=[key])
        df["timestamp"] = df.index
        dataframes[key] = df
    else:
        print(f"{key.capitalize()} file not selected.")

# Create GPS DataFrame by merging latitude and longitude.

if "latitude" in dataframes and "longitude" in dataframes:
    df_gps = pd.merge(dataframes["latitude"], dataframes["longitude"], on="timestamp")
    df_gps = df_gps.rename(columns={"latitude": "Latitude", "longitude": "Longitude"})
    df_gps["PointIndex"] = df_gps.index
else:
    print("Latitude or Longitude data is missing.")
    df_gps = pd.DataFrame(columns=["Latitude", "Longitude", "PointIndex"])

# Merge the two vibration signals on timestamp

if "vibration1" in dataframes and "vibration2" in dataframes:
    df_vibration_merged = pd.merge(
        dataframes["vibration1"],
        dataframes["vibration2"],
        on="timestamp"
    )
else:
    print("Vibration data files are missing.")
    df_vibration_merged = pd.DataFrame()

# Segmentation 
dt_vibration = 0.002
segment_duration_seconds = 10
segment_length = int(segment_duration_seconds / dt_vibration)

if not df_vibration_merged.empty:
    num_segments = len(df_vibration_merged) // segment_length
    segments = []
    for i in range(num_segments):
        seg = df_vibration_merged.iloc[
            i * segment_length : (i + 1) * segment_length
        ][["vibration1", "vibration2"]].values
        segments.append(seg)
    segments = np.array(segments)
else:
    segments = np.array([])

# Grade 4 Labeling 

LABEL_DIST_M = 20  

def haversine_m(lat1, lon1, lat2, lon2):
    R = 6371000.0
    lat1 = np.radians(lat1); lon1 = np.radians(lon1)
    lat2 = np.radians(lat2); lon2 = np.radians(lon2)
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    a = np.sin(dlat/2.0)**2 + np.cos(lat1)*np.cos(lat2)*np.sin(dlon/2.0)**2
    return 2 * R * np.arcsin(np.sqrt(a))

def min_dist_to_set(lat, lon, set_lat, set_lon):
    d = haversine_m(lat, lon, set_lat, set_lon)
    return float(np.min(d))

print("Select Data 1 folder (converted_coordinates_*.csv)")
data1_dir = filedialog.askdirectory(title="Select Data 1 folder")
if not data1_dir:
    raise FileNotFoundError("No Data 1 folder selected.")

bridge_path = os.path.join(data1_dir, "converted_coordinates_Resultat_Bridge.csv")
joint_path  = os.path.join(data1_dir, "converted_coordinates_Resultat_RailJoint.csv")
turn_path   = os.path.join(data1_dir, "converted_coordinates_Turnout.csv")

def load_events(path, category):
    df = pd.read_csv(path)
    df.columns = df.columns.str.strip()

    colmap = {c.lower(): c for c in df.columns}
    latc = colmap.get("latitude") or colmap.get("lat")
    lonc = colmap.get("longitude") or colmap.get("lon") or colmap.get("lng")

    if latc is None or lonc is None:
        raise ValueError(f"{category}: Missing lat/lon columns in {df.columns.tolist()}")

    df[latc] = pd.to_numeric(df[latc], errors="coerce")
    df[lonc] = pd.to_numeric(df[lonc], errors="coerce")
    df = df.dropna(subset=[latc, lonc]).rename(columns={latc: "Latitude", lonc: "Longitude"})
    df["Category"] = category
    return df[["Latitude", "Longitude", "Category"]]

events = {
    "Bridge": load_events(bridge_path, "Bridge"),
    "RailJoint": load_events(joint_path, "RailJoint"),
    "Turnout": load_events(turn_path, "Turnout"),
}

ev_by_cat = {
    "Bridge": (events["Bridge"]["Latitude"].to_numpy(), events["Bridge"]["Longitude"].to_numpy()),
    "RailJoint": (events["RailJoint"]["Latitude"].to_numpy(), events["RailJoint"]["Longitude"].to_numpy()),
    "Turnout": (events["Turnout"]["Latitude"].to_numpy(), events["Turnout"]["Longitude"].to_numpy()),
}

# Map GPS points to segment index
gps_dt = 0.05
gps_points_per_segment = int(segment_duration_seconds / gps_dt)  

if not df_gps.empty:
    df_gps["Latitude"] = pd.to_numeric(df_gps["Latitude"], errors="coerce")
    df_gps["Longitude"] = pd.to_numeric(df_gps["Longitude"], errors="coerce")
    df_gps = df_gps.dropna(subset=["Latitude", "Longitude"]).reset_index(drop=True)
    df_gps["PointIndex"] = df_gps.index

segment_labels = ["Other"] * (segments.shape[0] if segments.size else 0)

priority = ["Bridge", "RailJoint", "Turnout"] 

if segments.size and not df_gps.empty:
    for seg_idx in range(segments.shape[0]):
        start_gps = seg_idx * gps_points_per_segment
        end_gps = min((seg_idx + 1) * gps_points_per_segment, len(df_gps))

        if start_gps >= end_gps:
            segment_labels[seg_idx] = "Other"
            continue

        gps_slice = df_gps.iloc[start_gps:end_gps]

        best_label = "Other"
        best_dist = 1e18

    
        for lat, lon in zip(gps_slice["Latitude"].to_numpy(), gps_slice["Longitude"].to_numpy()):
            for cat in priority:
                c_lat, c_lon = ev_by_cat[cat]
                dmin = min_dist_to_set(lat, lon, c_lat, c_lon)
                if dmin < best_dist:
                    best_dist = dmin
                    best_label = cat

        segment_labels[seg_idx] = best_label if best_dist <= LABEL_DIST_M else "Other"

label_df = pd.DataFrame({
    "SegmentIndex": np.arange(len(segment_labels)),
    "Label": segment_labels
})
label_df.to_csv("segment_labels.csv", index=False)
print("Saved: segment_labels.csv")

counts = label_df["Label"].value_counts()
percent = label_df["Label"].value_counts(normalize=True) * 100
print("\nLabel distribution:")
for label in counts.index:
    print(f"{label}: {counts[label]} segments ({percent[label]:.2f}%)")

#  Dash App 
if not df_gps.empty:
    map_fig = px.scatter_mapbox(
        df_gps,
        lat="Latitude",
        lon="Longitude",
        zoom=10,
        title="GPS Points with Vibration Data"
    )
    map_fig.update_layout(mapbox_style="open-street-map", height=600)
else:
    map_fig = go.Figure()
    map_fig.update_layout(title="No GPS Data Available", height=600)

# Create an initial empty vibration plot figure.
vib_empty_fig = go.Figure()
vib_empty_fig.update_layout(
    title="Vibration Signal",
    xaxis_title="Time (s)",
    yaxis_title="Acceleration"
)

# Initialize Dash app.
app = dash.Dash(__name__)

app.layout = html.Div([
    html.Div([
        dcc.Graph(id="gps-map", figure=map_fig)
    ], style={"width": "48%", "display": "inline-block", "vertical-align": "top"}),

    html.Div([
        dcc.Graph(id="vibration-plot", figure=vib_empty_fig)
    ], style={"width": "48%", "display": "inline-block", "vertical-align": "top"})
])


@app.callback(
    Output("vibration-plot", "figure"),
    [Input("gps-map", "clickData")]
)
def update_vibration_plot(clickData):
    if clickData is None:
        return vib_empty_fig

    if segments.size == 0:
        return vib_empty_fig

    try:
        # Use pointIndex 
        point_index = clickData["points"][0]["pointIndex"]

        # Map GPS point index to vibration segment index (10-second segments)
        seg_index = int(point_index // gps_points_per_segment)

        # Clamp to valid range
        if seg_index < 0:
            seg_index = 0
        if seg_index >= len(segments):
            seg_index = len(segments) - 1

        selected_segment = segments[seg_index]

        time_axis = np.arange(segment_length) * dt_vibration

        # Label for the segment
        label = segment_labels[seg_index] if seg_index < len(segment_labels) else "Other"

        vib_fig = go.Figure()
        vib_fig.add_trace(go.Scatter(
            x=time_axis,
            y=selected_segment[:, 0],
            mode="lines",
            name="Vibration Channel 1"
        ))
        vib_fig.add_trace(go.Scatter(
            x=time_axis,
            y=selected_segment[:, 1],
            mode="lines",
            name="Vibration Channel 2"
        ))
        vib_fig.update_layout(
            title=f"Vibration Signal — Segment {seg_index} — Label: {label}",
            xaxis_title="Time (s)",
            yaxis_title="Acceleration"
        )
        return vib_fig

    except Exception as e:
        print("Callback error:", e)
        return vib_empty_fig


if __name__ == "__main__":
    print("Dash app is running at: http://127.0.0.1:8060")
    app.run(debug=False, port=8060, use_reloader=False)



