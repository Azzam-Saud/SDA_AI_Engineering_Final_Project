

from flask import Flask, render_template, request, jsonify, session
from flask_session import Session
from core import process_videos_and_store, extract_youtube_links, is_valid_duration, get_agent_for_session, save_chat_history, download_audio,generate_speech
import yt_dlp
import uuid
import os
import time
import threading
import datetime
# Initialize Flask application
app = Flask(__name__)

# Configure Flask session settings
app.secret_key = 'supersecret'
app.config['SESSION_TYPE'] = 'filesystem'
Session(app)

# Set up upload folder configuration
UPLOAD_FOLDER = './uploads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# Global dictionary to store processing progress
processing_status = {}

def process_with_progress(links, user_id):
    """
    Processes video links with progress tracking and timing estimation.
    Args:
        links: List of video URLs or file paths to process
        user_id: Unique identifier for the user session
    """
    start_time = time.time()
    
    # Initialize progress tracking for this user
    processing_status[user_id] = {
        'total': len(links),
        'completed': 0,
        'current_file': '',
        'start_time': start_time,
        'estimated_completion': None
    }
    
    all_files = []
    for i, url in enumerate(links):
        # Update current file being processed
        processing_status[user_id]['current_file'] = url if url.startswith('http') else os.path.basename(url)
        
        # Process file or URL
        if url.startswith('http'):
            # For YouTube URLs - download audio
            output_mp3 = f'./uploads/{user_id}_{i}'
            download_audio(url, output_mp3)
            all_files.append(f"{output_mp3}.mp3")
        else:
            # For uploaded files
            all_files.append(url)
        
        # Update progress counters
        processing_status[user_id]['completed'] += 1
        
        # Calculate estimated completion time
        elapsed = time.time() - start_time
        avg_time_per_file = elapsed / processing_status[user_id]['completed']
        remaining_files = processing_status[user_id]['total'] - processing_status[user_id]['completed']
        estimated_remaining_seconds = avg_time_per_file * remaining_files
        
        if remaining_files > 0:
            completion_time = datetime.datetime.now() + datetime.timedelta(seconds=estimated_remaining_seconds)
            processing_status[user_id]['estimated_completion'] = completion_time.strftime('%H:%M:%S')
    
    # Process all files after downloading is complete
    process_videos_and_store(all_files, user_id)
    
    # Mark processing as complete
    end_time = time.time()
    total_time = end_time - start_time
    processing_status[user_id]['status'] = 'complete'
    processing_status[user_id]['total_time'] = f"{total_time:.2f} seconds"

@app.route('/')
def index():
    """
    Main index route that initializes user session.
    Returns:
        Rendered index.html template
    """
    if 'user_id' not in session:
        session['user_id'] = str(uuid.uuid4())
    return render_template('index.html')

@app.route('/start', methods=['POST'])
def start():
    """
    Handles processing start requests based on different input modes.
    Returns:
        JSON response with processing status
    """
    mode = request.form.get('mode')
    input_value = request.form.get('input')
    user_id = session['user_id']
    links = []

    if mode == 'upload':
        # Handle file upload mode
        file = request.files.get('file')
        if not file:
            return jsonify({'status': '❌ No file uploaded.'})
        upload_dir = './uploads'
        os.makedirs(upload_dir, exist_ok=True)
        file_path = os.path.join(upload_dir, file.filename)
        file.save(file_path)
        links.append(file_path)

    else:
        if mode == 'topic':
            # Handle topic search mode (YouTube search)
            from langchain_community.tools import YouTubeSearchTool
            search_tool = YouTubeSearchTool()
            results = search_tool.run(f'{input_value},6')
            raw_links = extract_youtube_links(results)
            for url in raw_links:
                if len(links) >= 3:
                    break
                if is_valid_duration(url):
                    links.append(url)

        elif mode == 'playlist':
            # Handle YouTube playlist mode
            if not input_value.startswith("http"):
                return jsonify({'status': '❌ Invalid playlist URL.'})
            ydl_opts = {'quiet': True, 'extract_flat': True, 'force_generic_extractor': True}
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info_dict = ydl.extract_info(input_value, download=False)
                all_links = [entry['url'] for entry in info_dict.get('entries', []) if 'url' in entry]
            for url in all_links:
                if is_valid_duration(url):
                    links.append(url)

        elif mode == 'single_url':
            # Handle single YouTube URL mode
            if not input_value.startswith("http"):
                return jsonify({'status': '❌ Invalid video URL.'})
            if is_valid_duration(input_value):
                links.append(input_value)
            else:
                return jsonify({'status': '❌ Video exceeds 30 minutes.'})

    if not links:
        return jsonify({'status': '❌ No suitable links found.'})

    # Start processing in a background thread
    processing_thread = threading.Thread(target=process_with_progress, args=(links, user_id))
    processing_thread.daemon = True
    processing_thread.start()
    
    return jsonify({
        'status': '✅ Processing started! You will see progress updates.',
        'totalFiles': len(links)
    })

@app.route('/progress', methods=['GET'])
def get_progress():
    """
    Provides progress updates for ongoing processing.
    Returns:
        JSON response with current progress status
    """
    user_id = session.get('user_id')
    if not user_id or user_id not in processing_status:
        return jsonify({
            'status': 'unknown',
            'progress': 0,
            'message': 'No processing in progress'
        })
    
    status = processing_status[user_id]
    progress_percent = (status['completed'] / status['total']) * 100 if status['total'] > 0 else 0
    
    return jsonify({
        'status': 'processing' if status.get('status') != 'complete' else 'complete',
        'progress': progress_percent,
        'currentFile': status['current_file'],
        'completedFiles': status['completed'],
        'totalFiles': status['total'],
        'estimatedCompletion': status.get('estimated_completion'),
        'elapsedTime': f"{time.time() - status['start_time']:.2f} seconds",
        'totalTime': status.get('total_time')
    })

@app.route('/chat', methods=['POST'])
def chat():
    """
    Handles chat messages from users and returns AI responses.
    Returns:
        JSON response with AI reply
    """
    user_message = request.json['message']
    user_id = session['user_id']
    agent, _ = get_agent_for_session(user_id)

    # Save user message to chat history
    save_chat_history(user_id, "User", user_message)
    
    try:
        # Get AI response using the agent
        response = agent.run(user_message)
    except Exception as e:
        print(f"❌ Error extracting playlist: {str(e)}")
        return jsonify({'status': f'❌ Error extracting playlist: {str(e)}'})

    # Save AI response to chat history
    save_chat_history(user_id, "Bot", response)
    
    return jsonify({'reply': response})

@app.route('/speak', methods=['POST'])
def speak():
    """
    Converts text to speech and returns audio data.
    Returns:
        JSON response with base64 encoded audio
    """
    text = request.json['text']
    audio_base64 = generate_speech(text)
    return jsonify({'audio': audio_base64})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)