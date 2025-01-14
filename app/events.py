from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_user, login_required, logout_user, current_user
from .model import User, Message, db  
from . import socketio  

main = Blueprint('main', __name__)

@main.route('/')
def index():
    if current_user.is_authenticated:
        return redirect(url_for('main.chat', username=current_user.username))
    return redirect(url_for('main.login'))

@main.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('main.chat', username=current_user.username))
   
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = User.query.filter_by(username=username).first()
        if user and user.check_password(password):
            login_user(user)
            return redirect(url_for('main.chat', username=user.username))
        else:
            flash('Invalid username or password', 'error')
   
    return render_template('login.html')

@main.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('main.chat', username=current_user.username))
   
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']
       
        if User.query.filter_by(username=username).first():
            flash('Username already exists', 'error')
            return redirect(url_for('main.register'))
       
        if User.query.filter_by(email=email).first():
            flash('Email already exists', 'error')
            return redirect(url_for('main.register'))
       
        user = User(username=username, email=email)
        user.set_password(password)
        db.session.add(user)
        db.session.commit()
       
        flash('Registration successful. Please log in.', 'success')
        return redirect(url_for('main.login'))
   
    return render_template('register.html')

@main.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('main.index'))

@main.route('/chat/<username>')
@login_required
def chat(username):
    if username != current_user.username:
        flash('You can only access your own chat.', 'error')
        return redirect(url_for('main.chat', username=current_user.username))
    return render_template('chat.html', username=username)

@main.route('/api/users')
@login_required
def get_users():
    users = User.query.all()
    return jsonify([user.username for user in users if user != current_user])

@main.route('/delete_message/<int:message_id>', methods=['POST'])
@login_required
def delete_message(message_id):
    message = Message.query.get(message_id)
    if message and (message.sender_id == current_user.id or message.recipient_id == current_user.id):
        db.session.delete(message)
        db.session.commit()
        return jsonify({'success': True}), 200
    return jsonify({'success': False, 'error': 'Message not found or permission denied'}), 404
