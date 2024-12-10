from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

db = SQLAlchemy()

chat_users = db.Table(
    'chat_users',
    db.Column('chat_id', db.Interger, db.ForeignKey('chat.id'), primary_key=True),
    db.Column('user_id', db.Interger, db.ForeignKey('user.id'), primary_key=True)
)

class User(db.Model):
    __tablename__= 'user'
    id = db.Column(db.Interger, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password = db.Column(db.String(120), nullable=False)