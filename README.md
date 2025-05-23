# 📹 VidTalk

VidTalk is a web application that allows users to upload or process YouTube videos and interact with them using AI. The system can extract audio, transcribe it to text, and enable chat-based questions about the video's content.

---

## 🚀 Features

- 🔗 **Video URL:** Process a single YouTube video
- 📜 **Playlist:** Process a full YouTube playlist
- 🔍 **Search Topic:** Search and download videos by topic
- ⬆️ **Upload File:** Upload audio/video files manually
- 💬 **Chatbot:** Ask questions about the processed content
- 📈 **Progress Bar:** Real-time processing status tracking

---

## 🛠️ Tech Stack

- **Backend:** Flask (Python)
- **Frontend:** HTML, CSS (Poppins, Font Awesome), JavaScript
- **AI:** Speech-to-Text, NLP processing
- **Containerization:** Docker-ready

---

## ⚙️ Setup Instructions

### 1️⃣ Clone the repository:

```bash
git clone https://github.com/Ahmad-Alsubhi/Project_VidTalk.git
cd Project_VidTalk
```

### 2️⃣ Create virtual environment & install dependencies:

```bash
python -m venv venv
source venv/bin/activate  # Mac/Linux
# OR
venv\Scripts\activate    # Windows

pip install -r requirements.txt

mkdir .env > Openai  and  ideogram  
```

### 3️⃣ Run the app:

```bash
python app.py
```

Access the app at:  
🌐 http://127.0.0.1:5000/

### 🐳 Docker Option:

```bash
docker build -t vidtalk .
docker run -p 5000:5000 vidtalk
```

---

## 📂 Project Structure

```
Project_VidTalk/
├── static/
│   ├── styles.css
│   └── script.js
├── templates/
│   └── index.html
├── uploads/
├── app.py
├── core.py
├── requirements.txt
├── Dockerfile
├── runtime.txt
├── README.md
└── Project Documentation (PDF)
```

---

## ✅ Future Improvements

- Add user authentication
- Enhance error handling
- Support more languages for transcription

---

## 📄 License

This project is for educational purposes.
