from flask_socketio import emit, join_room, leave_room
from .model import User, Message, db  # Import your models
from flask_login import current_user
from . import socketio  # Import socketio instance

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
            recipient = sender  # To mark it as a public message
            is_private = False
        else:
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

        if recipient_username == 'Everyone':
            emit('receive_message', message_data, broadcast=True)
        else:
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
            messages = Message.query.filter(
                db.and_(
                    Message.is_private == False,
                    Message.recipient_id == Message.sender_id  # This indicates a public message
                )
            ).order_by(Message.timestamp).all()
        else:
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

        message_list = [{
            'id': msg.id,
            'sender': msg.sender.username,
            'recipient': 'Everyone' if msg.sender_id == msg.recipient_id else msg.recipient.username,
            'content': msg.content,
            'timestamp': msg.timestamp.isoformat(),
            'is_private': msg.is_private
        } for msg in messages]

        emit('load_messages', {'messages': message_list})

    except Exception as e:
        emit('error', {'msg': f'Error fetching messages: {str(e)}'})