import dash
from dash import dcc, html
from dash.dependencies import Input, Output
import pandas as pd
import plotly.graph_objs as go
import sqlite3
import os

DB_FILE = "gpu_log.db"
REFRESH_INTERVAL = 30 * 1000  # in milliseconds (30s)

# Create Dash app
app = dash.Dash(__name__)
app.title = "GPU Monitoring Dashboard"

# Layout
app.layout = html.Div([
    html.H1("GPU Monitoring Dashboard", style={"textAlign": "center"}),

    dcc.Interval(id="interval-update", interval=REFRESH_INTERVAL, n_intervals=0),

    dcc.Dropdown(id="gpu-selector", placeholder="Select a GPU to view", style={"width": "300px", "margin": "auto"}),

    dcc.Graph(id="temp-graph"),
    dcc.Graph(id="util-graph"),
    dcc.Graph(id="mem-graph"),
    dcc.Graph(id="power-graph"),
    dcc.Graph(id="fan-graph"),

    html.H3("Active GPU Processes"),
    html.Div(id="process-table", style={"padding": "10px"})
])


# Load data from SQLite
def load_data():
    if not os.path.exists(DB_FILE):
        return pd.DataFrame()

    try:
        conn = sqlite3.connect(DB_FILE)
        df_stats = pd.read_sql_query("SELECT * FROM gpu_stats", conn)
        df_procs = pd.read_sql_query("SELECT * FROM gpu_processes", conn)

        # Group processes per GPU stats record
        grouped_procs = df_procs.groupby("gpu_id").apply(
            lambda g: g[["pid", "name", "used_memory_MB"]].to_dict(orient="records")
        ).to_dict()

        df_stats["processes"] = df_stats["id"].apply(lambda x: grouped_procs.get(x, []))

        conn.close()
        return df_stats

    except Exception as e:
        print("❌ Failed to read from SQLite:", e)
        return pd.DataFrame()


@app.callback(
    Output("gpu-selector", "options"),
    Output("gpu-selector", "value"),
    Input("interval-update", "n_intervals")
)
def update_gpu_dropdown(_):
    df = load_data()
    if df.empty:
        return [], None
    gpu_ids = sorted(df["gpu_index"].unique())
    options = [{"label": f"GPU {i}", "value": i} for i in gpu_ids]
    return options, gpu_ids[0]


@app.callback(
    Output("temp-graph", "figure"),
    Output("util-graph", "figure"),
    Output("mem-graph", "figure"),
    Output("power-graph", "figure"),
    Output("fan-graph", "figure"),
    Output("process-table", "children"),
    Input("interval-update", "n_intervals"),
    Input("gpu-selector", "value")
)
def update_graphs(_, selected_gpu):
    df = load_data()
    if df.empty or selected_gpu is None:
        return [go.Figure()] * 5 + [html.Div("No data available")]

    df = df[df["gpu_index"] == selected_gpu]
    df["timestamp"] = pd.to_datetime(df["timestamp"])

    # Temperature
    temp_fig = go.Figure(go.Scatter(x=df["timestamp"], y=df["temperature_C"], mode="lines+markers"))
    temp_fig.update_layout(title="Temperature (°C)", xaxis_title="Time", yaxis_title="Temp")

    # Utilization
    util_fig = go.Figure(go.Scatter(x=df["timestamp"], y=df["gpu_utilization"], mode="lines+markers"))
    util_fig.update_layout(title="GPU Utilization (%)", xaxis_title="Time", yaxis_title="Utilization")

    # Memory
    mem_fig = go.Figure(go.Scatter(x=df["timestamp"], y=df["memory_used_MB"], mode="lines+markers"))
    mem_fig.update_layout(title="Memory Usage (MB)", xaxis_title="Time", yaxis_title="Memory Used")

    # Power
    power_fig = go.Figure(go.Scatter(x=df["timestamp"], y=df["power_usage_W"], mode="lines+markers"))
    power_fig.update_layout(title="Power Usage (W)", xaxis_title="Time", yaxis_title="Power (W)")

    # Fan Speed
    fan_fig = go.Figure(go.Scatter(x=df["timestamp"], y=df["fan_speed_percent"], mode="lines+markers"))
    fan_fig.update_layout(title="Fan Speed (%)", xaxis_title="Time", yaxis_title="Fan Speed")

    # Process Table
    latest_entry = df.sort_values("timestamp", ascending=False).iloc[0]
    processes = latest_entry.get("processes", [])
    if not processes:
        process_table = html.Div("No active GPU processes.")
    else:
        process_table = html.Table([
            html.Tr([html.Th("PID"), html.Th("Name"), html.Th("Used Memory (MB)")])
        ] + [
            html.Tr([
                html.Td(p["pid"]),
                html.Td(p["name"]),
                html.Td(p["used_memory_MB"])
            ]) for p in processes
        ])

    return temp_fig, util_fig, mem_fig, power_fig, fan_fig, process_table


if __name__ == "__main__":
    app.run(debug=True)
