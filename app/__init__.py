import os
from flask import Flask, session
from flask_session import Session
from flask_socketio import SocketIO
from dotenv import load_dotenv

load_dotenv()

socketio = SocketIO()

def create_app():
    app = Flask(__name__)
    
    app.config['SECRET_KEY'] = 'SECRET_KEY'
    app.config["SESSION_TYPE"] = "filesystem"
    Session(app)
    
    socketio.init_app(app)
    
    from app.routes import main_bp
    app.register_blueprint(main_bp)
    return app