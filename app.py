import dash
from dash import dcc, html
from dash.dependencies import Input, Output, State, ALL
import pandas as pd
import plotly.graph_objs as go
import base64
import io
import dash_bootstrap_components as dbc
import flask
from flask import Flask, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
import logging
import time
import requests
from requests.exceptions import ConnectionError

# Initialize the Flask server
server = flask.Flask(__name__)

server.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///users.db'
server.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Setup logging
logging.basicConfig(level=logging.DEBUG)

db = SQLAlchemy(server)

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(150), nullable=False, unique=True)
    password = db.Column(db.String(150), nullable=False)
    email = db.Column(db.String(150), nullable=False, unique=True)

# Initialize database
with server.app_context():
    db.create_all()

@server.route('/register', methods=['POST'])
def register():
    data = request.json
    logging.debug(f"Register data received: {data}")
    hashed_password = generate_password_hash(data['password'], method='sha256')
    new_user = User(username=data['username'], password=hashed_password, email=data['email'])

    try:
        db.session.add(new_user)
        db.session.commit()
        return jsonify({'message': 'User registered successfully!'}), 201
    except Exception as e:
        logging.error(f"Error occurred: {e}")
        return jsonify({'message': 'User already exists'}), 409

@server.route('/login', methods=['POST'])
def login():
    data = request.json
    user = User.query.filter_by(username=data['username']).first()

    if not user or not check_password_hash(user.password, data['password']):
        return jsonify({'message': 'Invalid credentials'}), 401

    return jsonify({'message': 'Logged in successfully!'}), 200

@server.route('/users', methods=['GET'])
def list_users():
    users = User.query.all()
    user_list = [{'username': user.username, 'email': user.email} for user in users]
    return jsonify(user_list)

# Initialize the Dash app with Bootstrap stylesheet
app = dash.Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP], server=server)

# Define the layout of the app
app.layout = html.Div(
    style={
        'backgroundColor': '#222',
        'color': '#eee',
        'padding': '20px',
        'height': 'auto',
        'minHeight': '100vh',
        'width': 'auto',
        'overflowY': 'auto'
    },
    children=[
        html.H1('DataLogViewer 2.0', style={'textAlign': 'center', 'color': '#F7AB0A'}),
        html.Div([
            dbc.Button("Login", id="open-login", n_clicks=0, style={'margin': '5px'}),
            dbc.Button("Register", id="open-register", n_clicks=0, style={'margin': '5px'}),
        ]),
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
        html.Label('Add Duplicate Graphs ', style={'color': '#bbb'}),
        dcc.Input(id='duplicate-count', type='number', min=0, max=4, value=0, style={
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


@app.callback(
    [
        Output('output-data-upload', 'children'),
        Output('time-series-chart', 'figure'),
        Output('time-series-chart', 'style'),
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
@server.route("/")
def update_output(contents, filename, duplicate_count, login_submit, register_submit, login_username, login_password, register_username, register_password, register_email):
    ctx = dash.callback_context

    if not ctx.triggered:
        return None, {'data': [], 'layout': {}}, {'display': 'none'}, []

    button_id = ctx.triggered[0]['prop_id'].split('.')[0]

    if button_id == 'login-submit' and login_username and login_password:
        login_data = {
            'username': login_username,
            'password': login_password
        }
        response = requests.post('http://127.0.0.1:5000/login', json=login_data)
        if response.status_code == 200:
            return html.Div(f"Logged in as {login_username}"), {'data': [], 'layout': {}}, {'display': 'none'}, []
        else:
            return html.Div("Login failed"), {'data': [], 'layout': {}}, {'display': 'none'}, []

    elif button_id == 'register-submit' and register_username and register_password and register_email:
        register_data = {
            'username': register_username,
            'password': register_password,
            'email': register_email
        }
        response = requests.post('http://127.0.0.1:5000/register', json=register_data)
        if response.status_code == 201:
            return html.Div(f"Registered with username {register_username} and email {register_email}"), {'data': [], 'layout': {}}, {'display': 'none'}, []
        else:
            return html.Div("Registration failed"), {'data': [], 'layout': {}}, {'display': 'none'}, []

    elif contents is not None:
        content_type, content_string = contents[0].split(',')
        decoded = base64.b64decode(content_string)
        try:
            df = pd.read_csv(io.StringIO(decoded.decode('utf-8')))
            if 'time' in df.columns and not all(df['time'].apply(validate_time_format)):
                error_message = html.Div([
                    html.H5('Error: Invalid time format'),
                    html.P('The "time" column contains invalid time values. Please ensure that time values are in a valid format.'),
                ])
                return error_message, {'data': [], 'layout': {}}, {'display': 'none'}, []

            data_table = html.Div(
                style={'overflowX': 'auto'},
                children=[
                    html.H4(filename),
                    html.Hr(),
                    html.Div(
                        style={'overflowY': 'auto', 'height': '400px'},
                        children=html.Table([
                            html.Thead([html.Tr([html.Th(col) for col in df.columns])]),
                            html.Tbody([
                                html.Tr([html.Td(df.iloc[i][col]) for col in df.columns]) for i in range(len(df))
                            ])
                        ])
                    )
                ]
            )
            data = []
            for i, column in enumerate(df.columns):
                if column != 'time':
                    x_values = list(range(len(df)))
                    trace = go.Scatter(x=x_values, y=df[column], mode='lines+markers', name=column)
                    data.append(trace)
            layout = go.Layout(
                title='Multivariable Time Series Chart',
                xaxis=dict(title='Index', tickfont=dict(color='#ffffff')),
                yaxis=dict(title='Value', tickfont=dict(color='#ffffff')),
                paper_bgcolor='#222',
                plot_bgcolor='#222',
                font=dict(color='#ffffff')
            )
            time_series_chart = {'data': data, 'layout': layout}
            duplicate_graphs = []
            for _ in range(min(duplicate_count, 4)):
                duplicate_graphs.append(dcc.Graph(id=f'duplicate-graph-{_}', figure=time_series_chart))
            return data_table, time_series_chart, {'display': 'block'}, duplicate_graphs

        except Exception as e:
            error_message = html.Div([
                html.H3('Error: Unable to process file'),
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

# Ensure the Flask server is running before starting the Dash app
def wait_for_server(url, timeout=30):
    start_time = time.time()
    while True:
        try:
            response = requests.get(url)
            if response.status_code == 200:
                print("Server is up and running")
                break
        except ConnectionError:
            if time.time() - start_time > timeout:
                raise ConnectionError(f"Server not available at {url} after {timeout} seconds")
            time.sleep(1)

# Ensure the Flask server is running before starting the Dash app
wait_for_server("http://127.0.0.1:5000/users")

# Run the Dash app
if __name__ == '__main__':
    app.run_server(debug=True)
