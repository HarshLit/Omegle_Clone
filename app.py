from flask import Flask, render_template, request, session
from flask_socketio import SocketIO, emit, join_room, leave_room, disconnect
import random
import string

# Initialize Flask and SocketIO
app = Flask(__name__)
app.config['SECRET_KEY'] = 'your_secret_key_here'
socketio = SocketIO(app)

# Data structures to manage waiting users and active chat sessions
waiting_users = set()
active_chats = {}
user_count = 0  # Keep track of connected users

# Function to generate a unique room ID
def generate_room_id():
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))

# Route for the homepage
@app.route('/')
def index():
    global user_count
    user_count += 1  # Increment user count
    return render_template('index.html', online_count=user_count)

# SocketIO event handler for a user joining
@socketio.on('join')
def on_join():
    user_id = request.sid
    partner_id = None

    # Try to pair the new user with a waiting user
    if waiting_users:
        partner_id = waiting_users.pop()

    # Generate a room ID for the chat
    room_id = generate_room_id()

    # Add the new user and their partner to the active_chats dictionary
    active_chats[user_id] = {'partner_id': partner_id, 'room_id': room_id}
    if partner_id:
        active_chats[partner_id] = {'partner_id': user_id, 'room_id': room_id}

    # Emit 'chat_start' event to both users
    socketio.emit('chat_start', room=room_id, to=user_id)
    if partner_id:
        socketio.emit('chat_start', room=room_id, to=partner_id)

# SocketIO event handler for incoming messages
@socketio.on('message')
def handle_message(data):
    user_id = request.sid
    if user_id in active_chats:
        room_id = active_chats[user_id]['room_id']
        socketio.emit('message', data=data, room=room_id, skip_sid=True)  # Send to everyone in the room

# SocketIO event handler for disconnect events
@socketio.on('disconnect')
def on_disconnect():
    global user_count
    user_id = request.sid
    if user_id in waiting_users:
        waiting_users.remove(user_id)
    elif user_id in active_chats:
        partner_id = active_chats[user_id]['partner_id']
        room_id = active_chats[user_id]['room_id']
        del active_chats[user_id]
        if partner_id in active_chats:
            del active_chats[partner_id]
        socketio.emit('chat_end', room=room_id, skip_sid=True)  # Notify everyone in the room
        user_count -= 1  # Decrement user count

# Start the Flask app and SocketIO server
if __name__ == '__main__':
    from os import environ
    port = int(environ.get("PORT", 5000))
    socketio.run(app, host='0.0.0.0', port=port)
