import dash
from dash import dcc, html
from dash.dependencies import Input, Output, State
import pandas as pd
import plotly.graph_objs as go
import sqlite3
import os

# DB_FILE = "gpu_log.db"
DB_FILE = "mock_gpu_log.db"
REFRESH_INTERVAL = 30 * 1000  # in milliseconds (5s)

# Create Dash app
app = dash.Dash(__name__)
app.title = "GPU Monitoring Dashboard"

# Layout
app.layout = html.Div(style={'backgroundColor': '#f0f2f5'}, children=[
    html.Div(style={'backgroundColor': 'white', 'padding': '20px', 'borderRadius': '5px', 'margin': '20px'}, children=[
        html.H1("GPU Monitoring Dashboard", style={"textAlign": "center", "fontFamily": "Arial"}),

        dcc.Interval(id="interval-update", interval=REFRESH_INTERVAL, n_intervals=0),

        dcc.Dropdown(id="gpu-selector", placeholder="Select a GPU to view",
                     style={"width": "50%", "margin": "20px auto"}),

        dcc.Graph(id="temp-graph"),
        dcc.Graph(id="util-graph"),
        dcc.Graph(id="mem-graph"),
        dcc.Graph(id="power-graph"),
        dcc.Graph(id="fan-graph"),

        html.H3("Active GPU Processes", style={"textAlign": "center", "fontFamily": "Arial", 'marginTop': '30px'}),
        html.Div(id="process-table", style={"padding": "10px", "maxWidth": "800px", "margin": "auto"})
    ])
])


# Load data from SQLite
def load_data():
    if not os.path.exists(DB_FILE):
        return pd.DataFrame()

    try:
        conn = sqlite3.connect(f"file:{DB_FILE}?mode=ro", uri=True)  # Read-only mode for safety
        df_stats = pd.read_sql_query("SELECT * FROM gpu_stats", conn)
        df_procs = pd.read_sql_query("SELECT * FROM gpu_processes", conn)

        if df_procs.empty:
            df_stats["processes"] = [[] for _ in range(len(df_stats))]
            conn.close()
            return df_stats

        # Group processes per GPU stats record
        grouped_procs = df_procs.groupby("gpu_id").apply(
            lambda g: g[["pid", "name", "used_memory_MB"]].to_dict(orient="records"),
        ).to_dict()

        df_stats["processes"] = df_stats["id"].map(grouped_procs).fillna('').apply(list)

        conn.close()
        return df_stats

    except Exception as e:
        print("❌ Failed to read from SQLite:", e)
        return pd.DataFrame()


@app.callback(
    Output("gpu-selector", "options"),
    Output("gpu-selector", "value"),
    Input("interval-update", "n_intervals"),
    State("gpu-selector", "value")  # ✅ تغییر ۱: خواندن مقدار فعلی بدون ایجاد وابستگی
)
def update_gpu_dropdown(_, current_value):
    df = load_data()
    if df.empty:
        return [], None

    gpu_ids = sorted(df["gpu_index"].unique())
    options = [{"label": f"GPU {i}", "value": i} for i in gpu_ids]

    # ✅ تغییر ۲: منطق جدید برای حفظ مقدار انتخاب شده
    # اگر کاربر قبلا گزینه‌ای را انتخاب کرده و آن گزینه هنوز معتبر است، آن را حفظ کن
    if current_value is not None and current_value in gpu_ids:
        return options, current_value

    # در غیر این صورت (اولین بارگذاری)، مقدار پیش‌فرض را انتخاب کن
    default_value = options[0]['value'] if options else None
    return options, default_value


@app.callback(
    [Output("temp-graph", "figure"),
     Output("util-graph", "figure"),
     Output("mem-graph", "figure"),
     Output("power-graph", "figure"),
     Output("fan-graph", "figure"),
     Output("process-table", "children")],
    [Input("interval-update", "n_intervals"),
     Input("gpu-selector", "value")]
)
def update_graphs(_, selected_gpu):
    if selected_gpu is None:
        empty_fig = go.Figure().update_layout(title="Please select a GPU", xaxis={'visible': False},
                                              yaxis={'visible': False})
        return [empty_fig] * 5 + [html.Div("Please select a GPU to view data.", style={'textAlign': 'center'})]

    df = load_data()
    if df.empty:
        empty_fig = go.Figure().update_layout(title="No Data Available", xaxis={'visible': False},
                                              yaxis={'visible': False})
        return [empty_fig] * 5 + [
            html.Div("No data available. Is the mock generator running?", style={'textAlign': 'center'})]

    df_gpu = df[df["gpu_index"] == selected_gpu].copy()
    if df_gpu.empty:
        empty_fig = go.Figure().update_layout(title=f"No Data for GPU {selected_gpu}", xaxis={'visible': False},
                                              yaxis={'visible': False})
        return [empty_fig] * 5 + [html.Div(f"No data available for GPU {selected_gpu}.", style={'textAlign': 'center'})]

    df_gpu["timestamp"] = pd.to_datetime(df_gpu["timestamp"])

    def create_figure(y_data, title, y_title):
        fig = go.Figure(go.Scatter(x=df_gpu["timestamp"], y=y_data, mode="lines+markers", line=dict(width=2)))
        fig.update_layout(
            title=title,
            xaxis_title="Time",
            yaxis_title=y_title,
            margin=dict(l=40, r=20, t=40, b=30),
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)',
            font=dict(family="Arial")
        )
        return fig

    temp_fig = create_figure(df_gpu["temperature_C"], f"Temperature (°C) - GPU {selected_gpu}", "Temp (°C)")
    util_fig = create_figure(df_gpu["gpu_utilization"], f"GPU Utilization (%) - GPU {selected_gpu}", "Utilization (%)")
    mem_fig = create_figure(df_gpu["memory_used_MB"], f"Memory Usage (MB) - GPU {selected_gpu}", "Memory (MB)")
    power_fig = create_figure(df_gpu["power_usage_W"], f"Power Usage (W) - GPU {selected_gpu}", "Power (W)")
    fan_fig = create_figure(df_gpu["fan_speed_percent"], f"Fan Speed (%) - GPU {selected_gpu}", "Fan Speed (%)")

    latest_entry = df_gpu.sort_values("timestamp", ascending=False).iloc[0]
    processes = latest_entry.get("processes", [])
    if not processes:
        process_table = html.Div("No active GPU processes.", style={'textAlign': 'center', 'marginTop': '10px'})
    else:
        header = [html.Thead(html.Tr([html.Th("PID"), html.Th("Name"), html.Th("Used Memory (MB)")]))]
        body = [html.Tbody([
            html.Tr([
                html.Td(p["pid"]),
                html.Td(p["name"]),
                html.Td(p["used_memory_MB"])
            ]) for p in processes
        ])]
        process_table = html.Table(header + body,
                                   style={'width': '100%', 'borderCollapse': 'collapse', 'marginTop': '10px'})

    return temp_fig, util_fig, mem_fig, power_fig, fan_fig, process_table


if __name__ == "__main__":
    app.run(debug=True)
