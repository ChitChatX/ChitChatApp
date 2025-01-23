from flask import Flask, render_template, request, session, jsonify, redirect, url_for, flash
from flask_socketio import SocketIO, emit, join_room, leave_room
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from flask_dance.contrib.google import make_google_blueprint, google 
from flask_dance.consumer.storage.sqla import OAuthConsumerMixin
from flask_dance.consumer import oauth_authorized 
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
import os

os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'  # Only for development

app = Flask(__name__)
app.config['SECRET_KEY'] = 'my_secret_key'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///chat.db'
app.config['GOOGLE_OAUTH_CLIENT_ID'] = "1055905942300-ec4fab1bupsu4em5u6jcj52hmlcgkgvc.apps.googleusercontent.com"
app.config['GOOGLE_OAUTH_CLIENT_SECRET'] = "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"

db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'
socketio = SocketIO(app)

google_bp = make_google_blueprint(
    client_id=app.config['GOOGLE_OAUTH_CLIENT_ID'],
    client_secret=app.config['GOOGLE_OAUTH_CLIENT_SECRET'],
    scope=[
        "https://www.googleapis.com/auth/userinfo.email",
        "https://www.googleapis.com/auth/userinfo.profile",
        "openid"
    ]
)
app.register_blueprint(google_bp, url_prefix='/login')

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(128))

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

class OAuth(OAuthConsumerMixin, db.Model):
    user_id = db.Column(db.Integer, db.ForeignKey(User.id))
    provider_user_id = db.Column(db.String(255), unique=True, nullable=False)
    user = db.relationship(User)

class Message(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    sender_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    recipient_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    content = db.Column(db.String(500), nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    is_private = db.Column(db.Boolean, default=False)

    sender = db.relationship('User', foreign_keys=[sender_id], backref='sent_messages')
    recipient = db.relationship('User', foreign_keys=[recipient_id], backref='received_messages')

with app.app_context():
    db.create_all()

@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))

@oauth_authorized.connect_via(google_bp)
def google_logged_in(blueprint, token):
    resp = google.get("/oauth2/v2/userinfo")
    if resp.ok:
        google_info = resp.json()
        google_user_id = str(google_info['id'])

        query = OAuth.query.filter_by(provider=blueprint.name, provider_user_id=google_user_id)
        try:
            oauth = query.one()
        except:
            oauth = OAuth(provider=blueprint.name, provider_user_id=google_user_id, token=token)

        if oauth.user:
            login_user(oauth.user)

        else:
            user = User(username=google_info['name'], email=google_info['email'])
            oauth.user = user
            db.session.add_all([user, oauth])
            db.session.commit()
            login_user(user)


        return False

    flash("Failed to sign in with Google.", 'error')
    return False

@app.route('/')
def index():
    if current_user.is_authenticated:
        return redirect(url_for('chat', username=current_user.username))
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('chat', username=current_user.username))
    
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = User.query.filter_by(username=username).first()
        if user and user.check_password(password):
            login_user(user)
            return redirect(url_for('chat', username=user.username))
        else:
            flash('Invalid username or password', 'error')
    
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('chat', username=current_user.username))
    
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']
        
        if User.query.filter_by(username=username).first():
            flash('Username already exists', 'error')
            return redirect(url_for('register'))
        
        if User.query.filter_by(email=email).first():
            flash('Email already exists', 'error')
            return redirect(url_for('register'))
        
        user = User(username=username, email=email)
        user.set_password(password)
        db.session.add(user)
        db.session.commit()
        
        flash('Registration successful. Please log in.', 'success')
        return redirect(url_for('login'))
    
    return render_template('register.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('index'))

@app.route('/chat/<username>')
@login_required
def chat(username):
    if username != current_user.username:
        flash('You can only access your own chat.', 'error')
        return redirect(url_for('chat', username=current_user.username))
    return render_template('chat.html', username=username)

@app.route('/chat')
@login_required
def chat_redirect():
    return redirect(url_for('chat', username=current_user.username))

@app.route('/api/users')
@login_required
def get_users():
    users = User.query.all()
    return jsonify([user.username for user in users if user != current_user])

@app.route('/delete_message/<int:message_id>', methods=['POST'])
@login_required
def delete_message(message_id):
    message = Message.query.get(message_id)
    if message and (message.sender_id == current_user.id or message.recipient_id == current_user.id):
        db.session.delete(message)
        db.session.commit()
        return jsonify({'success': True}), 200
    return jsonify({'success': False, 'error': 'Message not found or permission denied'}), 404

@socketio.on('join')
def on_join(data):
    username = data['username']
    room = username
    join_room(room)
    emit('status', {'msg': f'{username} has entered the chat'}, broadcast=True)

@socketio.on('leave')
def on_leave(data):
    username = data['username']
    room = username
    leave_room(room)
    emit('status', {'msg': f'{username} has left the chat'}, broadcast=True)

def update_users():
    users = [user.username for user in User.query.all()]
    emit('update_users', users, broadcast=True)

@socketio.on('send_message')
def send_message(data):
    try:
        sender = current_user
        recipient_username = data.get('recipient', 'Everyone')
        content = data.get('message', '').strip()
        is_private = data.get('is_private', False)

        if not content:
            emit('error', {'msg': 'Message content cannot be empty'})
            return

        if recipient_username == 'Everyone':
            # Public message handling
            recipient = sender  # To mark it as a public message
            is_private = False
        else:
            # Private message handling
            recipient = User.query.filter_by(username=recipient_username).first()
            if not recipient:
                emit('error', {'msg': f'Recipient {recipient_username} not found'}, room=sender.username)
                return

        # Save the message to the database
        message = Message(
            sender_id=sender.id,
            recipient_id=recipient.id,
            content=content,
            is_private=is_private
        )
        db.session.add(message)
        db.session.commit()

        # Emit the message
        message_data = {
            'id': message.id,
            'sender': sender.username,
            'recipient': recipient_username,
            'content': content,
            'timestamp': message.timestamp.isoformat(),
            'is_private': is_private
        }

        # For public messages, broadcast to everyone
        if recipient_username == 'Everyone':
            emit('receive_message', message_data, broadcast=True)
        else:
            # For private messages, send only to sender and recipient
            emit('receive_message', message_data, room=sender.username)
            if sender.username != recipient.username:
                emit('receive_message', message_data, room=recipient.username)

    except Exception as e:
        emit('error', {'msg': f'Error sending message: {str(e)}'})


@socketio.on('get_messages')
def get_messages(data):
    try:
        recipient_username = data.get('recipient', 'Everyone')
        user_id = current_user.id

        if not recipient_username:
            emit('error', {'msg': 'Recipient is required'})
            return

        if recipient_username == 'Everyone':
            # Retrieve public messages
            messages = Message.query.filter(
                db.and_(
                    Message.is_private == False,
                    Message.recipient_id == Message.sender_id  # This indicates a public message
                )
            ).order_by(Message.timestamp).all()
        else:
            # Retrieve private messages between current user and selected recipient
            recipient = User.query.filter_by(username=recipient_username).first()
            if not recipient:
                emit('error', {'msg': f'Recipient {recipient_username} not found'})
                return

            messages = Message.query.filter(
                db.and_(
                    Message.is_private == True,
                    db.or_(
                        db.and_(
                            Message.sender_id == user_id,
                            Message.recipient_id == recipient.id
                        ),
                        db.and_(
                            Message.sender_id == recipient.id,
                            Message.recipient_id == user_id
                        )
                    )
                )
            ).order_by(Message.timestamp).all()

        # Format messages
        message_list = [{
            'id': msg.id,
            'sender': msg.sender.username,
            'recipient': 'Everyone' if msg.sender_id == msg.recipient_id else msg.recipient.username,
            'content': msg.content,
            'timestamp': msg.timestamp.isoformat(),
            'is_private': msg.is_private
        } for msg in messages]

        print(f"Sending messages for {recipient_username}: {len(message_list)} messages") # Debug line
        emit('load_messages', {'messages': message_list})

    except Exception as e:
        print(f"Error in get_messages: {str(e)}") # Debug line
        emit('error', {'msg': f'Error fetching messages: {str(e)}'})



if __name__ == '__main__':
    socketio.run(app, debug=True)