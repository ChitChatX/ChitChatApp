from flask_socketio import join_room, leave_room, emit
import socketio

active_rooms = {}  # In-memory dictionary to track rooms {room_id: [users]}

@socketio.on('join_room')
def handle_join_room(data):
    room = data.get('room')
    username = data.get('username')
    if room not in active_rooms:
        active_rooms[room] = []
    if username not in active_rooms[room]:
        active_rooms[room].append(username)
    join_room(room)
    emit('system_message', {'message': f'{username} has joined the room.'}, room=room)



@socketio.on('leave_room')
def handle_leave_room(data):
    room = data.get('room')
    username = data.get('username')

    if room in active_rooms and username in active_rooms[room]:
        active_rooms[room].remove(username)
        if not active_rooms[room]:  # Remove room if empty
            del active_rooms[room]
    leave_room(room)
    emit('system_message', {'message': f'{username} has left the room.'}, room=room)


@socketio.on('send_message')
def handle_send_message(data):
    room = data.get('room')
    message = data.get('message')
    timestamp = data.get('timestamp')
    sender = data.get('sender')
    emit('receive_message', {
        'message': message,
        'timestamp': timestamp,
        'sender': sender
    }, room=room)

