import os
from dotenv import load_dotenv

import requests
from flask import Flask, session, abort, redirect, request, render_template, url_for
from google.oauth2 import id_token
from google_auth_oauthlib.flow import Flow
from pip._vendor import cachecontrol
from google.auth.transport.requests import Request
from functools import wraps

load_dotenv()

GOOGLE_CLIENT_ID = os.getenv("client_id")
GOOGLE_CLIENT_SECRET = os.getenv("client_secret")
GOOGLE_REDIRECT_URI = os.getenv("redirect_uri")

app = Flask("__name__")
app.secret_key = GOOGLE_CLIENT_SECRET

# to bypass 0auth https rule, make sure to remove in production 
os.environ["OAUTHLIB_INSECURE_TRANSPORT"] = "1"

flow = Flow.from_client_config(
    {
        "web": {
            "client_id": GOOGLE_CLIENT_ID,
            "project_id": "phonic-arcana-444420-h0",
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
            "client_secret": GOOGLE_CLIENT_SECRET,
            "redirect_uris": [
                GOOGLE_REDIRECT_URI,
                ]
        }
    },
    scopes=["https://www.googleapis.com/auth/userinfo.email", "https://www.googleapis.com/auth/userinfo.profile", "openid"]
)
flow.redirect_uri = GOOGLE_REDIRECT_URI


def login_is_required(function):
    @wraps(function)
    def wrapper(*args, **kwargs):
        if "google_id" not in session:
            return abort(401)  # Authorization required
        return function()
    return wrapper

@app.route("/login")
def login():
    authorization_url, state = flow.authorization_url()
    session["state"] = state
    return redirect(authorization_url)


@app.route("/chat")
@login_is_required
def chat():
    return render_template("chat.html", user_name = session.get("name"))


@app.route("/callback")
def callback():
    flow.fetch_token(authorization_response=request.url)

    if not session["state"] == request.args["state"]:
        abort(500)  # State doesnt match

    credentials = flow.credentials
    request_session = requests.session()
    cached_session = cachecontrol.CacheControl(request_session)
    token_request = Request(session=cached_session)

    id_info = id_token.verify_oauth2_token(
         id_token=credentials._id_token,
         request=token_request,
         audience=GOOGLE_CLIENT_ID,
    )

    session["google_id"] = id_info.get("sub")
    session["name"] = id_info.get("name")
    return redirect(url_for("chat"))

@app.route("/")
def index():
    if 'google_id' in session:
        return redirect(url_for("chat"))
    return render_template("login.html")

@app.route("/logout")
def logout():
    session.clear()
    return redirect("/")

if __name__ == "__main__":
    app.run(debug=True)