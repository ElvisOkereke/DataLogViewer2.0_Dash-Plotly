import dash
from dash import dcc, html
from dash.dependencies import Input, Output
import pandas as pd
import plotly.graph_objs as go
import base64
import io

# Initialize the Dash app
app = dash.Dash(__name__)

# Define the layout of the app
# Layout
app.layout = html.Div([
    dcc.Upload(
        id='upload-data',
        children=html.Div([
            'Drag and Drop or ',
            html.A('Select Files')
        ]),
        multiple=True
    ),
    # Added input component
    html.Div(id='output-data-upload'),
    html.Label('Number Duplicate of Graphs'),
    dcc.Input(id='duplicate-count', type='number', min=0, max=4, value=0),
    dcc.Graph(id='time-series-chart'),
    html.Div(id='duplicate-graphs-container')
])

# Callback to handle file upload and display data table and chart
@app.callback([
    Output('output-data-upload', 'children'),
    Output('time-series-chart', 'figure'),
    Output('duplicate-graphs-container', 'children')
],
    [Input('upload-data', 'contents'),
     Input('upload-data', 'filename'),
     Input('duplicate-count', 'value')])
def update_output(contents, filename, duplicate_count):
    if contents is not None:
        content_type, content_string = contents[0].split(',')
        decoded = base64.b64decode(content_string)
        df = pd.read_csv(io.StringIO(decoded.decode('utf-8')))
        
        # Display data table
        data_table = html.Div([
            html.H5(filename),
            html.Hr(),
            dcc.Markdown(f"**Column Names:** {', '.join(df.columns)}"),
            html.Table([

                # Header
                html.Thead([
                    html.Tr([html.Th(col) for col in df.columns])
                ]),

                # Body
                html.Tbody([
                    html.Tr([
                        html.Td(df.iloc[i][col]) for col in df.columns
                    ]) for i in range(len(df))
                ])
            ])
        ])
        
        # Generate time series chart
        data = []
        for i, column in enumerate(df.columns):
            if column != 'time':  # Exclude 'time' column
                # Generate x-axis values starting from 0 incrementing by one per data point
                x_values = list(range(len(df)))
                trace = go.Scatter(x=x_values, y=df[column], mode='lines+markers', name=column)
                data.append(trace)
        layout = go.Layout(title='Multivariable Time Series Chart', xaxis=dict(title='Index'), yaxis=dict(title='Value'))
        time_series_chart = {'data': data, 'layout': layout}
        
        # Generate duplicate graphs
        duplicate_graphs = []
        for _ in range(min(duplicate_count, 4)):  # Limit to maximum of 4 duplicates
            duplicate_graphs.append(dcc.Graph(id=f'duplicate-graph-{_}', figure=time_series_chart))
        
        return data_table, time_series_chart, duplicate_graphs
    
    return None, {'data': [], 'layout': {}}, []


if __name__ == '__main__':
    app.run_server(debug=True)
