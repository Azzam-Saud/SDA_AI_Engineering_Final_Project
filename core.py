import re
import yt_dlp
import os
import requests
from dotenv import load_dotenv
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import FAISS
from langchain_openai import OpenAIEmbeddings
from langchain.schema import Document
from langchain_community.chat_models import ChatOpenAI
from langchain.memory import ConversationBufferMemory
from langchain.chains import RetrievalQA
from langchain.agents import initialize_agent, AgentType, Tool
from langchain_core.messages import HumanMessage
from openai import OpenAI
import openai
import base64


# Load environment variables from .env file
load_dotenv()

# Get API keys from environment variables
openai_api_key = os.getenv("OPENAI_API_KEY")
api_key = os.getenv('IDEOGRAM')

# Initialize OpenAI embeddings
embeddings = OpenAIEmbeddings()

# Downloads audio from YouTube URL and saves as MP3
def download_audio(youtube_url, output_path):
    ydl_opts = {
        'format': 'bestaudio/best',
        'outtmpl': output_path,
        'cookies': '/home/ubuntu/cookies.txt',
        'postprocessors': [{'key': 'FFmpegExtractAudio', 'preferredcodec': 'mp3', 'preferredquality': '192'}],
        'quiet': True
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        ydl.download([youtube_url])

# Extracts all URLs from text
def extract_youtube_links(text):
    pattern = r'(https?://[^\s]+)'
    return re.findall(pattern, text)

# Initialize OpenAI client
client = OpenAI(api_key=openai_api_key)

# Transcribes audio file using OpenAI's Whisper
def transcribe_audio_openai(file_path):
    with open(file_path, "rb") as audio_file:
        response = client.audio.transcriptions.create(
            model="whisper-1",
            file=audio_file,
            response_format="text"  # Return plain text only
        )
    return response

# Splits text into chunks for processing
def split_text(text, chunk_size=500, chunk_overlap=100):
    splitter = RecursiveCharacterTextSplitter(chunk_size=chunk_size, chunk_overlap=chunk_overlap, length_function=len)
    return splitter.split_text(text)

# Processes videos: downloads, transcribes, chunks text, and stores embeddings
def process_videos_and_store(links, user_id):
    all_documents = []
    for idx, url in enumerate(links):
        output_mp3 = f"video_{idx}"
        if os.path.isfile(url) and url.endswith('.mp3'):
            full_text = transcribe_audio_openai(url)
        else:
            download_audio(url, output_mp3) 
            full_text = transcribe_audio_openai(f'{output_mp3}.mp3')

        chunks = split_text(full_text)
        for chunk_id, chunk_text in enumerate(chunks):
            doc = Document(page_content=chunk_text.lower(), metadata={"source": url, "video_name": output_mp3, "chunk_id": chunk_id})
            all_documents.append(doc)

    if all_documents:
        vectorstore = FAISS.from_documents(all_documents, embeddings)
        vectorstore.save_local(f"faiss_index_user_{user_id}")

# Checks if YouTube video is 30 minutes or shorter
def is_valid_duration(url):
    try:
        with yt_dlp.YoutubeDL({'quiet': True}) as ydl:
            info_dict = ydl.extract_info(url, download=False)
            duration_seconds = info_dict.get('duration', 0)
            return duration_seconds <= 1800  # 30 minutes
    except Exception as e:
        print(f"Error checking duration for {url}: {e}")
        return False

# Appends message to user's chat history file
def save_chat_history(user_id, sender, message):
    with open(f'chat_history_{user_id}.txt', 'a') as f:
        f.write(f"{sender}: {message}\n")

# Converts text to speech using OpenAI's TTS
def generate_speech(text, voice='alloy', model='gpt-4o-mini-tts'):
    response = openai.audio.speech.create(
        model=model,
        voice=voice,
        input=text
    )
    audio_content = response.content
    audio_base64 = base64.b64encode(audio_content).decode('utf-8')
    return audio_base64


quiz_data = {} # Use this dec because if you need show the answer quiz
memory = ConversationBufferMemory(memory_key="chat_history", return_messages=True) # Use memory to remember you


# Creates and configures conversational AI agent for user session
def get_agent_for_session(user_id): 
    # Load or create FAISS vector store for user
    faiss_path = f"faiss_index_user_{user_id}"
    if os.path.exists(faiss_path):
        vectorstore = FAISS.load_local(faiss_path, embeddings, allow_dangerous_deserialization=True)
    else:
        vectorstore = FAISS.from_texts([], embeddings)
        vectorstore.save_local(faiss_path)



    # Configure retriever and LLM
    retriever = vectorstore.as_retriever(search_type="similarity", search_kwargs={"k": 2}) # Use only 2 chunk
    llm = ChatOpenAI(model_name="gpt-4.1", openai_api_key=openai_api_key, temperature=0)
    
    # Set up QA chain
    qa_chain = RetrievalQA.from_chain_type(llm=llm, retriever=retriever, chain_type="map_reduce", memory=memory)

    # Answers questions based on stored documents
    def learning_function(query):
        return qa_chain.run(query)

    # Creates concise summary of stored documents
    def summarize_function(_):
        docs = vectorstore.similarity_search("", k=1000)# That mean select all chunk because generate good summarize
        text = " ".join([doc.page_content for doc in docs])
        prompt = (
        "Please create a small and very small the simple main  mind map from the following text. \n\n"
        f"{text}"
        )
        response = llm.invoke([HumanMessage(content=prompt)])
        return response.content

    # Generates title based on document content because Used to generate image
    def generate_title_with_ai(ـ):
        summary = summarize_function(None) 
        prompt = f"Generate a short, catchy, and relevant title for the following summary:\n\n{summary}\n\nTitle:"

        response = client.chat.completions.create(
            model="gpt-4.1",
            messages=[
                {"role": "system", "content": "You are a helpful assistant that writes concise, relevant titles."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=20,
            temperature=0.5,
        )
        title = response.choices[0].message.content.strip()
        return title

    # Generates mindmap image using Ideogram API
    def mindmap_image_function(_):
        short_text = generate_title_with_ai(None)
        prompt = f"Draw very small maind map aboute : \n\n{short_text}."

        endpoint = "https://api.ideogram.ai/v1/ideogram-v3/generate"
        headers = {"Api-Key": api_key}
        
        files = {
            'prompt': (None, prompt),
            'rendering_speed': (None, 'QUALITY'),
            'aspect_ratio': (None, '16x9'),
            'style_type': (None, 'GENERAL')
        }

        response = requests.post(endpoint, headers=headers, files=files)

        if response.status_code == 200:
            data = response.json()
            image_url = data['data'][0]['url']
            return f"🖼️ Mindmap image generated! View here: {image_url}"
        else:
            return f"❌ Error generating mindmap image: {response.text}"
        


    # Generates quiz based on document content
    def generate_quiz_from_text(_):
        global quiz_data
        all_docs = vectorstore.similarity_search("", k=1000) # That mean select all chunk because generate random quiz
        full_text = " ".join([doc.page_content for doc in all_docs])

        quiz_prompt = f"""
        You are a smart teacher. Based on the following content, create 10 multiple-choice and true/false questions.
        For EACH question, provide:
        1. The question
        2. Four answer options (a, b, c, d)
        3. The correct answer letter
        
        Content: {full_text}
        \n
        Format your response exactly like this:
        1- Question 1?
        a) Option1
        b) Option2
        c) Option3
        d) Option4
        Answer: b
        \n
        2- Question 2?
        a) True
        b) False
        Answer: a
        \n
        Continue with all 10 questions.
        """

        response = llm.invoke([HumanMessage(content=quiz_prompt)])
        
        quiz_text = response.content
        
        if user_id not in quiz_data:
            quiz_data[user_id] = {}
        quiz_data[user_id]["full_quiz"] = quiz_text
        
        user_quiz = re.sub(r'Answer: [a-d](\n|$)', r'\1', quiz_text)
        
        memory.chat_memory.add_user_message("Generate Quiz")
        memory.chat_memory.add_ai_message(user_quiz)
        
        return user_quiz

    # Retrieves quiz answers
    def get_quiz_answers(_):
        global quiz_data
        if user_id in quiz_data and "full_quiz" in quiz_data[user_id]:
            return f"✅ Here are the questions with answers:\n\n{quiz_data[user_id]['full_quiz']}"
        return "❌ No quiz has been generated yet. Please generate a quiz first."




    # Define agent tools
    tools = [
        Tool(
        name="LearningTool",
        func=learning_function,
        description=(
        "Search for the answers only in the provided documents."
        "DO NOT answer based on your own knowledge or assumptions."
        "Be honest with the user, and tell him that he is not mentioned in the file."
        "Even if the person asking you is asking about the same topic, if you don’t find it, tell him I didn’t find it. Be very nervous."
        "If the answer is not found in the documents, say 'I couldn’t find that information in the provided videos and stop.'"
    )
    ),
    Tool(
        name="QuizTool",
        func=generate_quiz_from_text,
        description="Use this tool when the user requests a test, such as Test me or Give me a test only about the document, do not write the question and answers outside the document."
    ),
    Tool(name="MindMapImageTool", 
        func=mindmap_image_function, 
        description="Create a visual that contains the main points."),

    Tool(name="SummarizeTool", 
        func=summarize_function, 
        description="If the user wants a summary, return clean formatted summary without extra wrapping."),
    

        Tool(name="QuizAnswerTool", 
            func=get_quiz_answers, 
            description=(
            "Get the latest quiz questions and answers. "
            "If you need answers, send them to the user. "
            "If the user I need answer, correct him. "
            "How many questions did he get out of the total."
        ))
    ]



    # Initialize and return agent
    agent = initialize_agent(
        tools=tools,
        llm=llm,
        agent=AgentType.CHAT_CONVERSATIONAL_REACT_DESCRIPTION,
        memory=memory,
        verbose=True,
        handle_parsing_errors=True
    )
    return agent, memory