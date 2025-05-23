document.addEventListener('DOMContentLoaded', function() {
    const modeButtons = document.querySelectorAll('.mode-btn');
    const inputField = document.getElementById('inputValue');
    const fileUploadWrapper = document.querySelector('.file-upload-wrapper');
    const fileUpload = document.getElementById('fileUpload');
    const startBtn = document.getElementById('startBtn');
    const progressContainer = document.getElementById('progressContainer');
    const progressFill = document.getElementById('progressFill');
    const progressPercent = document.getElementById('progressPercent');
    const currentFile = document.getElementById('currentFile');
    const chatMessages = document.getElementById('chatMessages');
    const userMessageInput = document.getElementById('userMessage');
    const sendMessageBtn = document.getElementById('sendMessageBtn');


    const userMessage = document.getElementById('userMessage');
    const startVoiceBtn = document.getElementById('startVoiceBtn');

if ('webkitSpeechRecognition' in window) {
    const recognition = new webkitSpeechRecognition();
    recognition.lang = 'en-US'; 
    recognition.continuous = false;
    recognition.interimResults = false;

    startVoiceBtn.addEventListener('click', () => {
        recognition.start();
    });

    recognition.onresult = (event) => {
        const transcript = event.results[0][0].transcript;
        userMessage.value = transcript; 
    };

    recognition.onerror = (event) => {
        console.error('Voice recognition error occurred:', event.error);
    };
} else {
    alert('The browser does not support voice recognition.');
}




    let currentMode = 'single_url';

    // Set mode
    modeButtons.forEach(button => {
        button.addEventListener('click', function() {
            modeButtons.forEach(btn => btn.classList.remove('active'));
            this.classList.add('active');
            currentMode = this.dataset.mode;
            
            if (currentMode === 'upload') {
                inputField.style.display = 'none';
                fileUploadWrapper.style.display = 'block';
            } else {
                inputField.style.display = 'block';
                fileUploadWrapper.style.display = 'none';
                
                if (currentMode === 'single_url') {
                    inputField.placeholder = 'Enter YouTube URL...';
                } else if (currentMode === 'playlist') {
                    inputField.placeholder = 'Enter YouTube Playlist URL...';
                } else if (currentMode === 'topic') {
                    inputField.placeholder = 'Enter search topic...';
                }
            }
        });
    });

    // Start processing
    startBtn.addEventListener('click', function() {
        const formData = new FormData();
        const inputValue = currentMode === 'upload' ? fileUpload.files[0] : inputField.value;
        
        if (!inputValue) {
            alert('Please enter a valid input');
            return;
        }
        
        if (currentMode === 'upload') {
            formData.append('file', inputValue);
        } else {
            formData.append('input', inputValue);
        }
        
        formData.append('mode', currentMode);
        
        startBtn.disabled = true;
        startBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Processing...';
        progressContainer.classList.add('visible');
        
        fetch('/start', {
            method: 'POST',
            body: formData
        })
        .then(response => response.json())
        .then(data => {
            if (data.status.includes('❌')) {
                alert(data.status);
                startBtn.disabled = false;
                startBtn.innerHTML = '<i class="fas fa-play"></i> Process';
                progressContainer.classList.remove('visible');
            } else {
                trackProgress();
            }
        })
        .catch(error => {
            console.error('Error:', error);
            startBtn.disabled = false;
            startBtn.innerHTML = '<i class="fas fa-play"></i> Process';
            progressContainer.classList.remove('visible');
        });
    });

    // Track progress
    function trackProgress() {
        const progressInterval = setInterval(() => {
            fetch('/progress')
                .then(response => response.json())
                .then(data => {
                    if (data.status === 'complete' || data.status === 'unknown') {
                        clearInterval(progressInterval);
                        progressFill.style.width = '100%';
                        progressPercent.textContent = '100%';
                        currentFile.textContent = 'Processing complete';
                        startBtn.disabled = false;
                        startBtn.innerHTML = '<i class="fas fa-play"></i> Process';
                        
                        setTimeout(() => {
                            progressContainer.classList.remove('visible');
                        }, 3000);
                    } else {
                        const percent = Math.round(data.progress);
                        progressFill.style.width = `${percent}%`;
                        progressPercent.textContent = `${percent}%`;
                        currentFile.textContent = data.currentFile || 'Processing...';
                    }
                });
        }, 1000);
    }

    // Chat functionality
    sendMessageBtn.addEventListener('click', sendMessage);
    userMessageInput.addEventListener('keypress', function(e) {
        if (e.key === 'Enter') sendMessage();
    });

    function sendMessage() {
        const message = userMessageInput.value.trim();
        if (message) {
            addMessage('user', message);
            userMessageInput.value = '';
            
            // Show typing indicator
            const typingIndicator = document.createElement('div');
            typingIndicator.className = 'message bot-message';
            typingIndicator.innerHTML = `
                <div class="typing-indicator">
                    <span></span>
                    <span></span>
                    <span></span>
                </div>
            `;
            chatMessages.appendChild(typingIndicator);
            chatMessages.scrollTop = chatMessages.scrollHeight;
            
            fetch('/chat', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ message: message })
            })
            .then(response => response.json())
            .then(data => {
                // Remove typing indicator
                chatMessages.removeChild(typingIndicator);
                addMessage('bot', data.reply);
            })
            .catch(error => {
                chatMessages.removeChild(typingIndicator);
                addMessage('bot', 'Error: ' + error.message);
            });
        }
    }



    function addMessage(sender, text) {
        const messageDiv = document.createElement('div');
        messageDiv.className = `message ${sender}-message`;

        let displayText = text;

        
        const urlRegex = /(https?:\/\/[^\s]+)/g;

        if (sender === 'bot') {
            displayText = displayText.replace(urlRegex, (url) => {
                if (url.match(/\.(png|jpg|jpeg|gif)$/i) || url.includes('/api/images/')) {
                    return `<img src="${url}" alt="image" style="max-width: 100%; border-radius: 8px;">`;
                } else {
                    return `<a href="${url}" target="_blank">${url}</a>`;
                }
            });

            displayText = displayText
                .replace(/\n/g, '<br>')
                .replace(/(Q\d+:)/g, '<br><b>$1</b>')
                .replace(/(Answer:)/g, '<br><b>$1</b>');
        }

        messageDiv.innerHTML = `
            <span>${displayText}</span>
            <button class="speak-btn">🔊</button>
        `;
        chatMessages.appendChild(messageDiv);
        chatMessages.scrollTop = chatMessages.scrollHeight;
    }



    chatMessages.addEventListener('click', function(e) {
        if (e.target.classList.contains('speak-btn')) {
            const message = e.target.parentElement.querySelector('span').innerText;
            fetch('/speak', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ text: message })
            })
            .then(response => response.json())
            .then(data => {
                const audio = new Audio('data:audio/mp3;base64,' + data.audio);
                audio.play();
            })
            .catch(error => console.error('Error:', error));
        }
    });

});