from flask import Flask
from flask_socketio import SocketIO
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_dance.contrib.google import make_google_blueprint
from . model import db
from .routes import main_bp
from .events import socketio

db = SQLAlchemy()
socketio = SocketIO()
login_manager = LoginManager()


def create_app():
    app = Flask(__name__)
    app.config.from_object('config.Config')
    
    #Extensions
    db.init_app(app)
    socketio.init_app(app)
    login_manager.init_app(app)
    
    #Blueprints
    app.register_blueprint(main_bp)
    return app

def register_google_blueprint(app):
    google_bp = make_google_blueprint(app)(
        client_id=app.config("GOOGLE_0AUTH_CLIENT_ID"),
        client_secret=app.config("GOOGLE_0AUTH_CLIENT_SECRET"),
        scope=[
            "https://www.googleapis.com/auth/userinfo.email", "https://www.googleapis.com/auth/userinfo.profile", "openid"
        ]  
    )
    app.register_blueprint(google_bp, url_prefix="/login")