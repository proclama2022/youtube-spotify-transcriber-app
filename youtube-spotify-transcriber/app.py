import streamlit as st
import youtube_dl
import spotipy
from spotipy.oauth2 import SpotifyClientCredentials
import speech_recognition as sr
import os
from pydub import AudioSegment
import tempfile
import requests

# Spotify credentials
SPOTIPY_CLIENT_ID = '9d31313479d64f2e9f0dddb780527774'
SPOTIPY_CLIENT_SECRET = 'e7e040261d4241cf8a7c6f31207d2422'

# Initialize Spotify client
sp = spotipy.Spotify(auth_manager=SpotifyClientCredentials(
    client_id=SPOTIPY_CLIENT_ID,
    client_secret=SPOTIPY_CLIENT_SECRET
))

# Streamlit app layout
st.title("YouTube & Spotify Transcriber")
st.write("Extract text from YouTube videos or Spotify podcasts")
st.write("App is running...")  # Debug message

# Input fields
source_type = st.selectbox("Select source type", ["YouTube", "Spotify"])
media_url = st.text_input("Enter URL")

# Transcription function
def transcribe_audio(audio_file):
    recognizer = sr.Recognizer()
    with sr.AudioFile(audio_file) as source:
        audio = recognizer.record(source)
    try:
        text = recognizer.recognize_google(audio)
        return text
    except sr.UnknownValueError:
        return "Could not understand audio"
    except sr.RequestError:
        return "API unavailable"

# Download and process media
if st.button("Transcribe"):
    if media_url:
        with st.spinner("Processing..."):
            try:
                if source_type == "YouTube":
                    # YouTube processing
                    ydl_opts = {
                        'format': 'bestaudio/best',
                        'postprocessors': [{
                            'key': 'FFmpegExtractAudio',
                            'preferredcodec': 'wav',
                            'preferredquality': '192',
                        }],
                        'outtmpl': os.path.join(tempfile.gettempdir(), '%(id)s.%(ext)s'),
                    }
                    
                    with youtube_dl.YoutubeDL(ydl_opts) as ydl:
                        info = ydl.extract_info(media_url, download=True)
                        audio_file = ydl.prepare_filename(info)
                    
                    # Convert to WAV if needed
                    if not audio_file.endswith('.wav'):
                        sound = AudioSegment.from_file(audio_file)
                        audio_file = audio_file.replace(os.path.splitext(audio_file)[1], '.wav')
                        sound.export(audio_file, format="wav")
                    
                    # Transcribe audio
                    transcription = transcribe_audio(audio_file)
                    
                elif source_type == "Spotify":
                    # Spotify processing
                    try:
                        # Extract episode ID from URL
                        episode_id = media_url.split('/')[-1].split('?')[0]
                        
                        # Get episode metadata
                        episode = sp.episode(episode_id)
                        audio_url = episode['audio_preview_url']
                        
                        if not audio_url:
                            st.error("This episode doesn't have an available audio preview")
                            transcription = "Audio preview not available"
                        else:
                            # Download audio
                            with tempfile.NamedTemporaryFile(suffix='.mp3', delete=False) as tmp_file:
                                response = requests.get(audio_url)
                                tmp_file.write(response.content)
                                audio_file = tmp_file.name
                                
                            # Convert to WAV
                            sound = AudioSegment.from_file(audio_file)
                            wav_file = audio_file.replace('.mp3', '.wav')
                            sound.export(wav_file, format="wav")
                            
                            # Transcribe audio
                            transcription = transcribe_audio(wav_file)
                            
                            # Clean up temporary files
                            os.unlink(audio_file)
                            os.unlink(wav_file)
                            
                        # Download audio
                        with tempfile.NamedTemporaryFile(suffix='.mp3', delete=False) as tmp_file:
                            response = requests.get(audio_url)
                            tmp_file.write(response.content)
                            audio_file = tmp_file.name
                            
                        # Convert to WAV
                        sound = AudioSegment.from_file(audio_file)
                        wav_file = audio_file.replace('.mp3', '.wav')
                        sound.export(wav_file, format="wav")
                        
                        # Transcribe audio
                        transcription = transcribe_audio(wav_file)
                        
                        # Clean up temporary files
                        os.unlink(audio_file)
                        os.unlink(wav_file)
                        
                    except Exception as e:
                        st.error(f"Error processing Spotify episode: {str(e)}")
                        transcription = "Transcription failed"
                
                # Display results
                st.success("Transcription complete!")
                st.text_area("Transcription", transcription, height=300)
                
                # Download button
                st.download_button(
                    label="Download Transcription",
                    data=transcription,
                    file_name="transcription.txt",
                    mime="text/plain"
                )
                
            except Exception as e:
                st.error(f"Error: {str(e)}")
    else:
        st.warning("Please enter a valid URL")