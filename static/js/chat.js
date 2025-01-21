let messages = [];
let inputMessage = '';
let recipient = 'Everyone'; 
let isPrivate = false;
let users = [];
let currentRecipient = 'Everyone';

// Create socket connection
const socket = io();

// Create chat container
const chatContainer = document.createElement('div');
chatContainer.className = 'chat-container';

// Create chat header
const chatHeader = document.createElement('div');
chatHeader.className = 'chat-header';
const welcomeMessage = document.createElement('h1');
welcomeMessage.textContent = `Welcome, ${username}!`;
const logoutButton = document.createElement('button');
logoutButton.textContent = 'Logout';
logoutButton.className = 'logout-btn';
logoutButton.onclick = handleLogout;
chatHeader.appendChild(welcomeMessage);
chatHeader.appendChild(logoutButton);
chatContainer.appendChild(chatHeader);

// Create chat messages container
const chatMessages = document.createElement('div');
chatMessages.className = 'chat-messages';
chatContainer.appendChild(chatMessages);

// Create messages end reference
const messagesEndRef = document.createElement('div');
chatMessages.appendChild(messagesEndRef);

// Create chat form
const chatForm = document.createElement('form');
chatForm.className = 'chat-form';
chatForm.onsubmit = sendMessage;

// Create recipient select
const recipientSelect = document.createElement('select');
recipientSelect.className = 'chat-select';
recipientSelect.required = true;
// onchange event handler to update recipient
recipientSelect.onchange = (e) => {
  recipient = e.target.value; 
};
const defaultOption = document.createElement('option');
defaultOption.value = '';
defaultOption.textContent = 'Select recipient';
recipientSelect.appendChild(defaultOption);
const everyoneOption = document.createElement('option');
everyoneOption.value = 'Everyone';
everyoneOption.textContent = 'Everyone';
recipientSelect.appendChild(everyoneOption);
chatForm.appendChild(recipientSelect);

// Create message input
const messageInput = document.createElement('input');
messageInput.type = 'text';
messageInput.placeholder = 'Type a message...';
messageInput.className = 'chat-input';
messageInput.required = true;
messageInput.oninput = (e) => {
  inputMessage = e.target.value;
};
chatForm.appendChild(messageInput);

// Create send button
const sendButton = document.createElement('button');
sendButton.type = 'submit';
sendButton.className = 'chat-button';
sendButton.textContent = 'Send';
chatForm.appendChild(sendButton);

// Append form to chat container
chatContainer.appendChild(chatForm);
document.getElementById('root').appendChild(chatContainer);

// Socket event listeners
socket.on('connect', () => {
  console.log('Connected to the server');
  socket.emit('join', { username: username });
  socket.emit('get_messages', { recipient: 'Everyone' });
});

socket.on('disconnect', () => {
  console.log('Disconnected from server');
});

socket.on('connect_error', (error) => {
  console.error('Connection error:', error);
  if (error.message === 'Unauthorized') {
    window.location.href = '/login';
  }
});

// Message handler for all incoming messages
socket.on('receive_message', (data) => {
  console.log('Received message:', data); // Debug line
  messages.push(data);
  renderMessages();
});

socket.on('error', (data) => {
  console.error('Socket error:', data); // Debug line
});

socket.on('load_messages', (data) => {
  messages = data.messages;
  renderMessages();
});

socket.on('status', (data) => {
  messages.push({ content: data.msg, isStatus: true });
  renderMessages();
});

// Send message function
function sendMessage(e) {
  e.preventDefault();
  if (inputMessage && currentRecipient) {
    console.log('Sending message:', {
      // Debug line
      message: inputMessage.trim(),
      recipient: currentRecipient,
      is_private: isPrivate,
    });

    socket.emit('send_message', {
      message: inputMessage.trim(),
      recipient: currentRecipient,
      is_private: currentRecipient !== 'Everyone', // Automatically set private based on recipient
    });

    messageInput.value = '';
    inputMessage = '';
  } else {
    console.error('Message or recipient missing', {
      inputMessage,
      currentRecipient,
    });
  }
}

socket.on('message_sent', (data) => {
  console.log('Message sent confirmation:', data); // debug line
  const newMessage = {
    sender: data.sender,
    content: data.content,
    is_private: data.is_private,
    timestamp: data.timestamp,
  };

  messages.push(newMessage);
  renderMessages();
});

// Handle logout
function handleLogout() {
  window.location.href = logoutUrl;
}

// Update recipient select handler
recipientSelect.onchange = (e) => {
  currentRecipient = e.target.value || 'Everyone';
  messages = [];
  socket.emit('get_messages', { recipient: currentRecipient });
};

// Update renderMessages function
function renderMessages() {
  console.log('Rendering messages:', messages); // debug line
  console.log('Current recipient:', currentRecipient); // debug line

  chatMessages.innerHTML = '';

  const filteredMessages = messages.filter((msg) => {
    if (msg.isStatus) {
      return true;
    }

    if (currentRecipient === 'Everyone') {
      return !msg.is_private;
    } else {
      return (
        (msg.sender === currentRecipient && msg.recipient === username) ||
        (msg.sender === username && msg.recipient === currentRecipient)
      );
    }
  });

  console.log('Filtered messages:', filteredMessages); // Debug line

  filteredMessages.forEach((msg) => {
    const messageContainer = document.createElement('div');
    messageContainer.className = `message-container ${
      msg.is_private ? 'private-message' : ''
    } ${msg.sender === username ? 'sent' : 'received'}`;

    const messageContent = document.createElement('p');
    if (msg.isStatus) {
      messageContent.className = 'status-message';
      messageContent.textContent = msg.content;
    } else {
      messageContent.innerHTML = `
          <span class='message-sender'>${msg.sender}:</span> 
          ${msg.content}
          <button class="delete-button" data-id="${msg.id}"> Delete </button>
        `;
    }

    messageContainer.appendChild(messageContent);
    chatMessages.appendChild(messageContainer);
  });

  messagesEndRef.scrollIntoView({ behavior: 'smooth' });
}

// Deletes Chat messages
chatMessages.addEventListener('click', (event) => {
  if (event.target.classList.contains('delete-button')) {
    const messageId = event.target.getAttribute('data-id');
    fetch(`/delete_message/${messageId}`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
    })
      .then((response) => {
        if (response.ok) {
          event.target.closest('.message-container').remove();
        } else {
          console.error('Failed to delete message');
        }
      })
      .catch((error) => console.error('Error:', error));
  }
});

// Fetch users and populate select
const fetchUsers = async () => {
  try {
    const response = await fetch('/api/users');
    if (response.ok) {
      const data = await response.json();
      users = data;
      populateUsers();
    } else if (response.status === 401) {
      window.location.href = '/login';
    }
  } catch (error) {
    console.error('Error fetching users:', error);
  }
};

const populateUsers = () => {
  recipientSelect.innerHTML = '';
  const defaultOption = document.createElement('option');
  defaultOption.value = '';
  defaultOption.textContent = 'Select recipient';
  recipientSelect.appendChild(defaultOption);
  const everyoneOption = document.createElement('option');
  everyoneOption.value = 'Everyone';
  everyoneOption.textContent = 'Everyone';
  recipientSelect.appendChild(everyoneOption);
  users.forEach((user) => {
    const option = document.createElement('option');
    option.value = user;
    option.textContent = user;
    recipientSelect.appendChild(option);
  });
};

// Initialize by fetching users
fetchUsers();