// chat.js
document.addEventListener('DOMContentLoaded', () => {
  const socket = io();
  let currentUser = '{{ username }}';
  let currentRecipient = 'Everyone';
  let messages = [];
  let users = [];
  let unreadCounts = {};

  // DOM Elements
  const messagesContainer = document.querySelector('.messages-scroll');
  const messageForm = document.getElementById('message-form');
  const messageInput = document.querySelector('.message-input');
  const recipientsList = document.getElementById('recipients-list');
  const currentRecipientEl = document.querySelector('.current-recipient');

  // Initialize Chat
  function initializeChat() {
    setupEventListeners();
    setupSocketEvents();
    fetchUsers();
    loadMessages(currentRecipient);
  }

  // Event Listeners Setup
  function setupEventListeners() {
    // Message submission
    messageForm.onsubmit = handleMessageSubmit;

    // Recipient selection
    recipientsList.onclick = handleRecipientSelection;

    // Delete message handler
    messagesContainer.addEventListener('click', handleMessageDelete);
  }

  // Socket.IO Event Handlers
  function setupSocketEvents() {
    socket.on('connect', () => {
      console.log('Connected to server');
      socket.emit('join', { username: currentUser });
    });

    socket.on('receive_message', handleIncomingMessage);
    socket.on('load_messages', updateMessageHistory);
    socket.on('update_users', updateRecipientsList);
    socket.on('disconnect', () => console.log('Disconnected'));
    socket.on('error', handleSocketError);
    socket.on('message_sent', handleMessageConfirmation);
  }

  // Message Handling
  function handleMessageSubmit(e) {
    e.preventDefault();
    const content = messageInput.value.trim();

    if (content && currentRecipient) {
      const tempId = Date.now(); // Temporary ID for optimistic UI
      const newMessage = {
        id: tempId,
        sender: currentUser,
        content: content,
        recipient: currentRecipient,
        is_private: currentRecipient !== 'Everyone',
        timestamp: new Date().toISOString(),
        status: 'sending',
      };

      // Optimistic UI update
      messages.push(newMessage);
      renderMessage(newMessage);

      socket.emit('send_message', {
        message: content,
        recipient: currentRecipient,
        is_private: currentRecipient !== 'Everyone',
      });

      messageInput.value = '';
      scrollToBottom();
    }
  }

  function handleIncomingMessage(message) {
    // Update unread counts if not current recipient
    if (
      message.sender !== currentUser &&
      message.recipient !== currentRecipient
    ) {
      incrementUnreadCount(message.sender);
    }

    if (shouldDisplayMessage(message)) {
      messages.push(message);
      renderMessage(message);
      scrollToBottom();
    }
  }

  function handleMessageConfirmation(serverMessage) {
    const index = messages.findIndex((m) => m.id === serverMessage.tempId);
    if (index > -1) {
      messages[index] = serverMessage;
      updateMessageElement(serverMessage);
    }
  }

  // Message Rendering
  function renderMessage(message) {
    const isSent = message.sender === currentUser;
    const timestamp = new Date(message.timestamp).toLocaleTimeString([], {
      hour: '2-digit',
      minute: '2-digit',
    });

    const messageEl = document.createElement('div');
    messageEl.className = `message-bubble ${isSent ? 'sent' : 'received'}`;
    messageEl.dataset.messageId = message.id;
    messageEl.innerHTML = `
          <div class="message-content">${message.content}</div>
          <div class="message-meta">
              <span class="message-time">${timestamp}</span>
              ${
                isSent
                  ? `<span class="message-status">${
                      message.status === 'sending' ? '🕒' : '✓'
                    }</span>`
                  : ''
              }
              ${
                !isSent
                  ? `<button class="delete-button" data-id="${message.id}">×</button>`
                  : ''
              }
          </div>
      `;

    messagesContainer.appendChild(messageEl);
  }

  function updateMessageElement(message) {
    const messageEl = document.querySelector(
      `[data-message-id="${message.id}"]`
    );
    if (messageEl) {
      const statusEl = messageEl.querySelector('.message-status');
      if (statusEl) {
        statusEl.textContent = '✓';
      }
    }
  }

  // Message History Management
  function updateMessageHistory(data) {
    messages = data.messages;
    messagesContainer.innerHTML = '';
    messages.forEach(renderMessage);
    scrollToBottom();
  }

  // Recipient Management
  function handleRecipientSelection(e) {
    const listItem = e.target.closest('.recipient-item');
    if (!listItem) return;

    const recipient = listItem.dataset.recipient;
    if (recipient === currentRecipient) return;

    setActiveRecipient(recipient);
    loadMessages(recipient);
  }

  function setActiveRecipient(recipient) {
    currentRecipient = recipient;
    document.querySelectorAll('.recipient-item').forEach((item) => {
      item.classList.toggle('active', item.dataset.recipient === recipient);
    });
    currentRecipientEl.textContent = recipient;
  }

  // User Management
  async function fetchUsers() {
    try {
      const response = await fetch('/api/users');
      users = await response.json();
      updateRecipientsList(users);
    } catch (error) {
      console.error('Error fetching users:', error);
    }
  }

  function updateRecipientsList(users) {
    recipientsList.innerHTML = '';

    // Add Everyone first
    const everyoneItem = createRecipientItem(
      'Everyone',
      unreadCounts['Everyone'] || 0
    );
    recipientsList.appendChild(everyoneItem);

    // Add other users
    users.forEach((user) => {
      if (user !== currentUser) {
        const item = createRecipientItem(user, unreadCounts[user] || 0);
        recipientsList.appendChild(item);
      }
    });
  }

  function createRecipientItem(username, unread = 0) {
    const item = document.createElement('li');
    item.className = 'recipient-item';
    item.dataset.recipient = username;
    item.innerHTML = `
          <span class="recipient-name">${username}</span>
          ${unread > 0 ? `<span class="unread-count">${unread}</span>` : ''}
      `;
    return item;
  }

  // Message Deletion
  function handleMessageDelete(e) {
    if (e.target.classList.contains('delete-button')) {
      const messageId = e.target.dataset.id;
      fetch(`/delete_message/${messageId}`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
      })
        .then((response) => {
          if (response.ok) {
            e.target.closest('.message-bubble').remove();
          }
        })
        .catch((error) => console.error('Error:', error));
    }
  }

  function scrollToBottom() {
    messagesContainer.scrollTo({
      top: messagesContainer.scrollHeight,
      behavior: 'smooth',
    });
  }

  // Utilities
  function loadMessages(recipient) {
    socket.emit('get_messages', { recipient });
  }

  function shouldDisplayMessage(message) {
    return (
      message.recipient === currentRecipient ||
      message.sender === currentRecipient ||
      (currentRecipient === 'Everyone' && !message.is_private)
    );
  }

  // Ensure handleLogout is defined in the global scope
  window.handleLogout = function () {
    window.location.href = '/logout'; 
  };

  // Error Handling
  function handleSocketError(error) {
    console.error('Socket error:', error);
    if (error.msg === 'Unauthorized') {
      window.location.href = '/login';
    }
  }

  // Initialize the chat
  initializeChat();
});
