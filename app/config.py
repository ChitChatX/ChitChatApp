import os

class Config:
    SECRET_KEY = "secretkey"
    SQLALCHEMY_DATABASE_URI = "sqlite:///chat.db"
    GOOGLE_0AUTH_CLIENT_ID = ""
    GOOGLE_0AUTH_CLIENT_SECRET = ""
    OAUTHLIB_INSECURE_TRANSPORT = "1" # Only for Development