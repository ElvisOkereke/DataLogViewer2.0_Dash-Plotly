import dash
from dash import dcc, html
from dash.dependencies import Input, Output
import pandas as pd
import plotly.graph_objs as go
import base64
import io
import dash_bootstrap_components as dbc
from dash.dependencies import State
from dash.dependencies import Input, Output, State, ALL, MATCH

# Initialize the Dash app with Bootstrap stylesheet
app = dash.Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP])

server = app.server

# Define the layout of the app
app.layout = html.Div(
    style={
        'backgroundColor': '#222',
        'color': '#eee',
        'padding': '20px',
        'height': 'auto',  # Change to auto for responsive height
        'minHeight': '100vh',  # Ensure minimum height is 100% of viewport height
        'width': 'auto',
        'overflowY': 'auto'
    },
    children=[
        html.H1('DataLogViewer 2.0', style={'textAlign': 'center', 'color': '#F7AB0A'}),
         # Buttons to open modals
        html.Div(
            [
                dbc.Button("Login", id="open-login", n_clicks=0, style={'margin': '5px'}),
                dbc.Button("Register", id="open-register", n_clicks=0, style={'margin': '5px'}),
            ]
        ),
        # Upload component
        dcc.Upload(
            id='upload-data',
            children=html.Div(['Drag and Drop or ', html.A('Select Files')]),
            style={
                'width': '100%',
                'height': '60px',
                'lineHeight': '60px',
                'borderWidth': '1px',
                'borderStyle': 'dashed',
                'borderRadius': '5px',
                'textAlign': 'center',
                'margin': '10px'
            },
            multiple=True
        ),
        # Input component for duplicate graphs
        html.Label('Add Duplicate Graphs ', style={'color': '#bbb'}),
        dcc.Input(id='duplicate-count', type='number', min=0, max=4, value=0,style={
                'backgroundColor': '#333',
                'color': '#fff',
                'border': '1px solid #555',
                'margin': '10px',
                'marginBottom': '10px'
            }),
        html.Div(id='output-data-upload'),
        dcc.Graph(
            id='time-series-chart',
            style={'backgroundColor': '#333', 'color': '#eee', 'display': 'none'}
        ),
        html.Div(id='duplicate-graphs-container'),

       

        # Login modal
        dbc.Modal(
            [
                dbc.ModalHeader("Login"),
                dbc.ModalBody([
                    dbc.Input(id="login-username", placeholder="Username", type="text"),
                    dbc.Input(id="login-password", placeholder="Password", type="password", style={'marginTop': '10px'}),
                ]),
                dbc.ModalFooter(
                    dbc.Button("Submit", id={"type": "login-submit", "index": 0}, className="ml-auto")
                ),
            ],
            id="login-modal",
            is_open=False,
        ),

        # Register modal
        dbc.Modal(
            [
                dbc.ModalHeader("Register"),
                dbc.ModalBody([
                    dbc.Input(id="register-username", placeholder="Username", type="text"),
                    dbc.Input(id="register-password", placeholder="Password", type="password", style={'marginTop': '10px'}),
                    dbc.Input(id="register-email", placeholder="Email", type="email", style={'marginTop': '10px'}),
                ]),
                dbc.ModalFooter(
                    dbc.Button("Submit", id={"type": "register-submit", "index": 0}, className="ml-auto")
                ),
            ],
            id="register-modal",
            is_open=False,
        ),
    ]
)

# Callback to toggle login modal
@app.callback(
    Output("login-modal", "is_open"),
    [Input("open-login", "n_clicks"), Input({"type": "login-submit", "index": ALL}, "n_clicks")],
    [State("login-modal", "is_open")]
)
def toggle_login_modal(n_open, n_submit, is_open):
    if n_open or any(n_submit):
        return not is_open
    return is_open

# Callback to toggle register modal
@app.callback(
    Output("register-modal", "is_open"),
    [Input("open-register", "n_clicks"), Input({"type": "register-submit", "index": ALL}, "n_clicks")],
    [State("register-modal", "is_open")]
)
def toggle_register_modal(n_open, n_submit, is_open):
    if n_open or any(n_submit):
        return not is_open
    return is_open

# Combined callback for handling file upload, login, and registration
@app.callback(
    [
        Output('output-data-upload', 'children'),
        Output('time-series-chart', 'figure'),
        Output('time-series-chart', 'style'),  # Output for updating graph style
        Output('duplicate-graphs-container', 'children')
    ],
    [
        Input('upload-data', 'contents'),
        Input('upload-data', 'filename'),
        Input('duplicate-count', 'value'),
        Input({"type": "login-submit", "index": ALL}, "n_clicks"),
        Input({"type": "register-submit", "index": ALL}, "n_clicks")
    ],
    [
        State("login-username", "value"),
        State("login-password", "value"),
        State("register-username", "value"),
        State("register-password", "value"),
        State("register-email", "value")
    ]
)
def update_output(contents, filename, duplicate_count, n_login_clicks, n_register_clicks,
                  login_username, login_password, register_username, register_password, register_email):
    ctx = dash.callback_context

    if not ctx.triggered:
        return None, {'data': [], 'layout': {}}, {'display': 'none'}, []

    button_id = ctx.triggered[0]['prop_id'].split('.')[0]

    if "login-submit" in button_id and any(n_login_clicks):
        # Authentication logic goes here (e.g., verify credentials)
        return html.Div(f"Logged in as {login_username}"), {'data': [], 'layout': {}}, {'display': 'none'}, []

    elif "register-submit" in button_id and any(n_register_clicks):
        # Registration logic goes here (e.g., create a new user)
        return html.Div(f"Registered with username {register_username} and email {register_email}"), {'data': [], 'layout': {}}, {'display': 'none'}, []

    elif contents is not None:
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
                        children=
                            
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

def validate_time_format(time_str):
    try:
        pd.to_datetime(time_str)
        return True
    except ValueError:
        return False

if __name__ == '__main__':
    app.run_server(debug=True)
