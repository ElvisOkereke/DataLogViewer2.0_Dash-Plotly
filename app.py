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
app.layout = html.Div(
    style={
        'backgroundColor': '#222',  # Background color
        'color': '#eee',  # Text color
        'padding': '20px',
        'height': '100vh',  # Set height to 100% of viewport height
        'width': '100vw',   # Set width to 100% of viewport width
    },
    children=[
    dcc.Upload(
        id='upload-data',
        children=html.Div([
            'Drag and Drop or ',
            html.A('Select Files')
        ]),style={
            'width': '100%',
            'height': '60px',
            'lineHeight': '60px',
            'borderWidth': '1px',
            'borderStyle': 'dashed',
            'borderRadius': '5px',
            'textAlign': 'center',
            'margin': '10px'
        },
        # Allow multiple files to be uploaded, but this doesnt actually do anything except stop an error weirdly
        multiple=True
    ),
   # Added input component
        html.Label('Add Duplicate Graphs ', style={'color': '#bbb'}),  # Text color
        dcc.Input(id='duplicate-count', type='number', min=0, max=4, value=0, style={'color': '#bbb'}),  # Text color
        html.Div(id='output-data-upload'),
        dcc.Graph(
            id='time-series-chart',
            style={
                'backgroundColor': '#333',  # Chart background color
                'color': '#eee',  # Text color
                'display': 'none'  # Initially hide the graph
            }
        ),
        html.Div(id='duplicate-graphs-container')
    ]
)

# Validate time format
def validate_time_format(time_str):
    try:
        pd.to_datetime(time_str)
        return True
    except ValueError:
        return False

# Callback to handle file upload and display data table and chart
@app.callback([
    Output('output-data-upload', 'children'),
    Output('time-series-chart', 'figure'),
    Output('time-series-chart', 'style'),  # Output for updating graph style
    Output('duplicate-graphs-container', 'children')
],
    [Input('upload-data', 'contents'),
     Input('upload-data', 'filename'),
     Input('duplicate-count', 'value')])
def update_output(contents, filename, duplicate_count):
    if contents is not None:
        content_type, content_string = contents[0].split(',')
        decoded = base64.b64decode(content_string)
        try:
            df = pd.read_csv(io.StringIO(decoded.decode('utf-8')))
            
            # Check time format in 'time' column
            if 'time' in df.columns and not all(df['time'].apply(validate_time_format)):
                error_message = html.Div([
                    html.H5('Error: Invalid time format'),
                    html.P('The "time" column contains invalid time values. Please ensure that time values are in a valid format.'),
                ])
                return error_message, {'data': [], 'layout': {}}, {'display': 'none'}, []

            # Display data table in a scrollable div
            data_table = html.Div(
                style={'overflowX': 'auto'},
                children=[
                    html.H4(filename),
                    html.Hr(),
                    html.Div(
                        style={'overflowY': 'auto', 'height': '400px'},
                        children=html.Table([
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
                    )
                ]
            )
            
            # Generate time series chart
            data = []
            for i, column in enumerate(df.columns):
                if column != 'time':  # Exclude 'time' column
                    # Generate x-axis values starting from 0 incrementing by one per data point
                    x_values = list(range(len(df)))
                    trace = go.Scatter(x=x_values, y=df[column], mode='lines+markers', name=column)
                    data.append(trace)
            layout = go.Layout(
                title='Multivariable Time Series Chart',
                xaxis=dict(title='Index', tickfont=dict(color='#ffffff')),  # Set x-axis tick text color to white
                yaxis=dict(title='Value', tickfont=dict(color='#ffffff')),  # Set y-axis tick text color to white
                paper_bgcolor='#222',  # Set plot background color to dark mode
                plot_bgcolor='#222',  # Set plot background color to dark mode
                font=dict(color='#ffffff')  # Set all text color to white
            )
            time_series_chart = {'data': data, 'layout': layout}
            
            # Generate duplicate graphs
            duplicate_graphs = []
            for _ in range(min(duplicate_count, 4)):  # Limit to maximum of 4 duplicates
                duplicate_graphs.append(dcc.Graph(id=f'duplicate-graph-{_}', figure=time_series_chart))
            
            return data_table, time_series_chart, {'display': 'block'}, duplicate_graphs
        
        except Exception as e:
            error_message = html.Div([
                html.H3('Error: Unable to process file (This is most likely happening because one of the columns is an invalid format, check the values in the "time" column)'),
                html.H5(str(e)),
            ])
            return error_message, {'data': [], 'layout': {}}, {'display': 'none'}, []

    return None, {'data': [], 'layout': {}}, {'display': 'none'}, []


if __name__ == '__main__':
    app.run_server(debug=True)
