from flask import Flask, render_template, request, redirect, session, flash, send_from_directory, jsonify,url_for,send_file
import smtplib # TO SEND OTPS THROUGH EMAILS
from email.mime.text import MIMEText # MIMES FOR EMAIL
from email.mime.multipart import MIMEMultipart
import random # TO GENERATE OTP
import secrets 
import os # FRO SECURING API KEYS ETC..
from flask_mysqldb import MySQL
from pydub import AudioSegment
from werkzeug.security import generate_password_hash,check_password_hash # FOR HASHING (ENCRPTION) OF USERS PASSWORDS
from spotipy import Spotify
from spotipy.oauth2 import SpotifyClientCredentials
import librosa # FOR REMIXING MUSICS
import requests
import soundfile as sf
from werkzeug.utils import secure_filename
import subprocess
from googleapiclient.discovery import build
from pytube import YouTube




app = Flask(__name__)
app.secret_key = secrets.token_hex(16) # TO SECURE THE SESION DATA

# Database Configuration
app.config['MYSQL_HOST'] = 'localhost'
app.config['MYSQL_USER'] = 'root'
app.config['MYSQL_PASSWORD'] = os.getenv('mysql_password')
app.config['MYSQL_DB'] = 'music'

mysql = MySQL(app)

@app.route('/')
def index():
    return render_template('index.html')
@app.route('/about')
def about():
    return render_template('about.html')
@app.route('/signup')
def signup():
    return render_template('signup.html')

@app.route('/send-email', methods=['POST'])
def send_email():
    try:
        name = request.form.get('name')
        recipient = request.form.get('recipient')

        # Store name and recipient in session for later use
        session['name'] = name
        session['recipient'] = recipient

        smtp_server = 'smtp.gmail.com'
        smtp_port = 587
        sender_email = os.getenv('Sender_email')
        app_password = os.getenv('APP_PASSWORD')  
        otp = random.randint(100000, 999999)
        session['otp'] = str(otp)

        msg = MIMEMultipart() # GENERATE THE OTP AND SEND IT TO USERS MAIL USING SMTP PROTOCOL . CAN BE DONE ONLY BY CREATING AN APP AND BY USING THE APP PASSWORD OR ELSE GOOGLE WILL BLOCK THE MESSAGES THINGING THE MAIL HAS A SPAM.
        msg['From'] = sender_email
        msg['To'] = recipient
        msg['Subject'] = "Radium Music - Your OTP"

        body = f"""
        Hi {name},

        Welcome to Radium Music!

        Your OTP is: {otp}

        Please use this OTP to complete your registration.
        """
        msg.attach(MIMEText(body, 'plain'))

        with smtplib.SMTP(smtp_server, smtp_port) as server:
            server.starttls()
            server.login(sender_email, app_password) # LOGIN TO THE SERVER BY PROVIDIND PROPER CREDENTIALS .
            server.send_message(msg)

        flash("Email sent successfully! Please check your inbox for the OTP.", "success")
        return redirect('/signup')

    except Exception as e:
        flash("Error sending email. Please try again.", "error") # ALWAYS HANDLE EXCEPTION CAREFULLY
        return redirect('/signup')
    

@app.route('/validateotp', methods=['POST'])
def validateotp():
    entered_otp = request.form.get('otp')
    stored_otp = session.get('otp')
    
    if not stored_otp:
        flash("Please request a new OTP.", "error")
        return redirect('/signup')

    if stored_otp == entered_otp:
       
        session['username'] = session.get('name')  
        session['email'] = session.get('recipient') 
        
        flash("OTP verified successfully! Please set your password.", "success")
        session.pop('otp', None)
        return redirect('/signup')
    else:
        flash("Invalid OTP. Please try again.", "error")
        return redirect('/signup')

@app.route('/pswd', methods=['POST'])
def cpswd():
    username = session.get('username')
    email = session.get('email')
    password = request.form.get('password')
    cp = request.form.get('confirm_password')

    if not username or not email:
        flash("Please complete the registration process from the beginning!", "error")
        return redirect('/signup')

    if not password:
        flash("Please enter a password!", "error")
        return redirect('/signup')

    if password == cp:
        # Hash the password
        hashed_password = generate_password_hash(password, method='pbkdf2:sha256')

        try:
            # Insert data into the users table
            cursor = mysql.connection.cursor()
            insert_query = """
                INSERT INTO users (username, email, password)
                VALUES (%s, %s, %s)
                """
            cursor.execute(insert_query, (username, email, hashed_password))
            mysql.connection.commit()
            cursor.close()

            # Clear all registration-related session data
            session.pop('username', None)
            session.pop('email', None)
            session.pop('name', None)
            session.pop('recipient', None)

            flash("Registration successful! Please log in.", "success")
            return redirect('/signin')
        except Exception as e:
            print(f"Error: {e}")
            flash("An error occurred. Please try again later.", "error")
            return redirect('/signup')
    else:
        flash("Passwords do not match!", "error")
        return redirect('/signup')


@app.route('/signin')
def signin():
    return render_template('signin.html')

@app.route('/signin_function', methods=[ 'POST'])
def login():
        email = request.form['email']
        password = request.form['password']

        if not email or not password:
            flash("Please fill out all fields!", "error")
            return redirect('/signin')

        cursor = mysql.connection.cursor()
        cursor.execute('SELECT * FROM users WHERE email = %s', (email,))
        user = cursor.fetchone()
        print(user)
    

        if user and check_password_hash(user[3], password):

            # session['username'] = user['username']
            flash("Successfully signed in","success")
            print("SUCCESSFULLY REGISTERED!!!")
            return redirect('/signin')
        else:
            flash("Invalid email or password!", "error")

        return render_template('signin.html')

    



# RapidAPI Configuration
RAPIDAPI_HOST = os.getenv('rAPIDAPI_HOST')
RAPIDAPI_KEY = os.getenv('rAPIDAPI_KEY')


@app.route('/search', methods=['GET', 'POST'])
def search():
    if request.method == 'POST':
        query = request.form.get('query', '').strip()
        if not query:
            flash("Please provide a search term.", "error")
            return render_template('search.html')

        # API request to RapidAPI s Spotify search endpoint
        url = f"https://{RAPIDAPI_HOST}/search/?type=multi&offset=0&limit=2&numberOfTopResults=5"
        headers = {
            "x-rapidapi-host": RAPIDAPI_HOST,
            "x-rapidapi-key": RAPIDAPI_KEY
        }
        params = {"q": query}

        try:
            response = requests.get(url, headers=headers, params=params)
            response.raise_for_status()
            data = response.json()

            # Extract track information safely
            tracks = []
            for item in data["tracks"]["items"]:
                track_info = {
                    "title": item.get("data", {}).get("name", "Unknown Title"),
                    "url": item.get("data", {}).get("uri", "#")
                }
                tracks.append(track_info)

            if not tracks:
                flash("No results found for your search.", "error")
                return render_template('search.html', query=query)

            return render_template('results.html', tracks=tracks, query=query)

        except requests.exceptions.RequestException as e:
            flash(f"Error fetching data from Spotify: {e}", "error")
            return render_template('search.html')

    return render_template('search.html')







API_KEY = os.getenv('aPI_KEY') # api key to access contents of youtube 



app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['REMIX_FOLDER'] = 'remixes'

# Ensure upload and remix folders exist
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
os.makedirs(app.config['REMIX_FOLDER'], exist_ok=True)

# YouTube API key for search function

youtube = build('youtube', 'v3', developerKey=API_KEY)


def download_audio_with_ytdlp(video_id):
    try:
        # Video URL
        video_url = f"https://www.youtube.com/watch?v={video_id}"
        print(f"Downloading from: {video_url}") # download the searched video first and then extract the music out of it
        
        # Output file path
        output_file = os.path.join(app.config['UPLOAD_FOLDER'], f"{video_id}.mp3")
        
        # yt-dlp command to download audio
        command = [
            "yt-dlp", "--extract-audio", "--audio-format", "mp3",
            "--output", output_file, video_url
        ]
        subprocess.run(command, check=True)
        
        return output_file
    except subprocess.CalledProcessError as e:
        print(f"Error downloading audio with yt-dlp: {str(e)}")
        return None


def remix_audio(file_path):
    # Load the audio file
    y, sr = librosa.load(file_path)

    # 1. Increase volume
    y = y * 1.2  # Boost volume by 20%

    # 2. Speed up the audio slightly
    y_speed = librosa.effects.time_stretch(y, rate=1.4)  # Speed up by 10%

    # 3. Pitch shift the audio
    y_pitched = librosa.effects.pitch_shift(y_speed, sr=sr, n_steps=3)  # Shift pitch up by 3 semitones

    # Normalize the audio
    y_pitched = librosa.util.normalize(y_pitched)

    # Save remixed audio to the REMIX_FOLDER
    output_path = os.path.join(app.config['REMIX_FOLDER'], 'remixed_audio.wav')
    sf.write(output_path, y_pitched, sr)  # Save the final audio

    print(f"Remixed audio saved to: {output_path}")
    return output_path


@app.route('/remix', methods=['POST'])
def remix():
    video_id = request.form.get('video_id')
    
    # Download audio
    audio_file = download_audio_with_ytdlp(video_id)
    if not audio_file:
        return jsonify({'error': 'Failed to download audio'}), 400
    
    # Remix audio
    remixed_file = remix_audio(audio_file)
    
    # Clean up original audio file
    os.remove(audio_file)
    
    # Render the remix result page
    return render_template(
        'remix_result.html',
        message="Your remixed song is now created!",
        audio_file=remixed_file
    )


@app.route('/remix_search')
def remix_search():
    return render_template('remix_search.html')


def search_youtube(query):
    """
    Searches YouTube for videos matching the given query.

    Args:
        query (str): The search query.

    Returns:
        list: A list of video details.
    """
    try:
        # Use YouTube API to search for videos
        request = youtube.search().list(
            part="snippet",
            maxResults=10,  # Number of results to return
            q=query,
            type="video"  # Restrict search to videos only
        )
        response = request.execute()

        # Return the list of items (videos)
        return response.get('items', [])
    except Exception as e:
        print(f"Error during YouTube search: {str(e)}")
        return []


@app.route('/rsearch', methods=['POST'])
def rsearch():
    query = request.form.get('query')
    if not query:
        return jsonify({'error': 'No query provided'}), 400
    
    # Search YouTube using the API
    try:
        search_results = search_youtube(query)
        results = [
            {
                "id": {"videoId": item['id']['videoId']},
                "snippet": {
                    "title": item['snippet']['title'],
                    "thumbnails": {
                        "default": {"url": item['snippet']['thumbnails']['default']['url']}
                    }
                }
            }
            for item in search_results
        ]
        return jsonify(results)
    except Exception as e:
        print(f"Error fetching YouTube search results: {str(e)}")
        return jsonify({'error': 'Failed to fetch YouTube search results'}), 500


@app.route('/get_remixed_audio')
def get_remixed_audio():
    audio_path = os.path.join(app.config['REMIX_FOLDER'], 'remixed_audio.wav')
    return send_file(audio_path, mimetype='audio/wav')




if __name__ == "__main__":
    app.run(debug=True)

