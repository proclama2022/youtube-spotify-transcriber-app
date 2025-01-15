import streamlit as st
import yt_dlp as youtube_dl
import os
from pydub import AudioSegment
import tempfile
from openai import OpenAI
import time
import shutil

# Validate required secrets
required_secrets = ['OPENAI_API_KEY']
missing_secrets = [secret for secret in required_secrets if secret not in st.secrets]

if missing_secrets:
    st.error(f"Missing required secrets: {', '.join(missing_secrets)}")
    st.stop()

# Initialize OpenAI client
client = OpenAI(api_key=st.secrets['OPENAI_API_KEY'])

# Streamlit app layout
st.title("YouTube Transcriber")
st.write("Extract text from YouTube videos")

# Input fields
media_url = st.text_input("Enter YouTube URL")
language = st.selectbox("Select audio language", ["auto", "en", "it", "fr", "es", "de"])

# Transcription function using Whisper
def transcribe_audio(audio_file, language="auto"):
    try:
        # Check file size
        file_size = os.path.getsize(audio_file)
        max_size = 25 * 1024 * 1024  # 25MB
        
        if file_size > max_size:
            # Split audio into chunks
            st.write("Audio file is too large, splitting into chunks...")
            audio = AudioSegment.from_file(audio_file)
            chunk_length = 10 * 60 * 1000  # 10 minutes in milliseconds
            chunks = [audio[i:i + chunk_length] for i in range(0, len(audio), chunk_length)]
            
            transcriptions = []
            for i, chunk in enumerate(chunks):
                st.write(f"Processing chunk {i+1}/{len(chunks)}...")
                chunk_file = f"{audio_file}_chunk{i}.mp3"
                chunk.export(chunk_file, format="mp3")
                
                with open(chunk_file, "rb") as audio_data:
                    transcript = client.audio.transcriptions.create(
                        model="whisper-1",
                        file=audio_data,
                        language=language if language != "auto" else None
                    )
                    transcriptions.append(transcript.text)
                
                # Clean up chunk file
                try:
                    if os.path.exists(chunk_file):
                        os.unlink(chunk_file)
                except Exception as e:
                    print(f"Error deleting chunk file: {str(e)}")
            
            return "\n".join(transcriptions)
        else:
            # Process single file
            with open(audio_file, "rb") as audio:
                transcript = client.audio.transcriptions.create(
                    model="whisper-1",
                    file=audio,
                    language=language if language != "auto" else None
                )
                return transcript.text
    except Exception as e:
        st.error(f"Transcription error: {str(e)}")
        return None
    finally:
        try:
            if os.path.exists(audio_file):
                os.unlink(audio_file)
        except Exception as e:
            print(f"Error deleting audio file: {str(e)}")

# Process media when button is clicked
if st.button("Transcribe"):
    if media_url:
        with st.spinner("Processing..."):
            try:
                start_time = time.time()
                temp_dir = tempfile.mkdtemp()
                temp_files = []
                
                # YouTube download options
                ydl_opts = {
                    'format': 'bestaudio/best',
                    'postprocessors': [{
                        'key': 'FFmpegExtractAudio',
                        'preferredcodec': 'mp3',
                        'preferredquality': '192',
                    }],
                    'outtmpl': os.path.join(temp_dir, '%(id)s.%(ext)s'),
                    'quiet': True,
                    'no_warnings': True,
                    'keepvideo': True,
                    'noplaylist': True,
                    'restrictfilenames': True,
                    'retries': 3,
                    'fragment_retries': 3,
                    'skip_unavailable_fragments': True,
                }
                
                # Download and process YouTube audio
                with youtube_dl.YoutubeDL(ydl_opts) as ydl:
                    info = ydl.extract_info(media_url, download=True)
                    audio_file = ydl.prepare_filename(info)
                    temp_files.append(audio_file)
                
                # Convert to MP3 if needed
                if not audio_file.endswith('.mp3'):
                    mp3_file = None
                    try:
                        st.write(f"Starting MP3 conversion process...")
                        st.write(f"Source file: {audio_file}")
                        
                        # Verify source file exists
                        if not os.path.exists(audio_file):
                            st.error(f"Source file not found at: {audio_file}")
                            st.write("Current working directory:", os.getcwd())
                            st.write("Directory contents:", os.listdir(os.path.dirname(audio_file)))
                            raise FileNotFoundError(f"Source file {audio_file} not found")
                        
                        # Create MP3 file path
                        mp3_file = audio_file.replace(os.path.splitext(audio_file)[1], '.mp3')
                        st.write(f"Target MP3 file: {mp3_file}")
                        
                        # Convert to MP3
                        st.write("Starting audio conversion...")
                        sound = AudioSegment.from_file(audio_file)
                        st.write("Audio loaded successfully, exporting to MP3...")
                        sound.export(mp3_file, format="mp3")
                        
                        # Verify conversion succeeded
                        if not os.path.exists(mp3_file):
                            st.error("MP3 conversion failed - output file not created")
                            st.write("Checking directory:", os.path.dirname(mp3_file))
                            st.write("Directory contents:", os.listdir(os.path.dirname(mp3_file)))
                            raise Exception("MP3 conversion failed - output file not created")
                        
                        st.success("MP3 conversion completed successfully")
                        
                        # Update audio file reference
                        temp_files.append(mp3_file)
                        audio_file = mp3_file
                        st.write(f"Updated audio file reference to: {audio_file}")
                        
                    except Exception as e:
                        st.error(f"Error converting audio: {str(e)}")
                        st.write("Error details:", str(e))
                        
                        # Clean up any created files
                        st.write("Cleaning up temporary files...")
                        for f in [audio_file, mp3_file]:
                            try:
                                if f and os.path.exists(f):
                                    st.write(f"Deleting file: {f}")
                                    os.unlink(f)
                                else:
                                    st.write(f"File not found: {f}")
                            except Exception as cleanup_error:
                                st.write(f"Error during cleanup of {f}: {str(cleanup_error)}")
                        st.stop()
                
                # Transcribe audio
                transcription = transcribe_audio(audio_file, language)
                
                if transcription:
                    # Display results
                    st.success(f"Transcription complete! (Took {time.time() - start_time:.2f} seconds)")
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
                st.stop()
            finally:
                # Clean up temporary directory
                try:
                    if os.path.exists(temp_dir):
                        shutil.rmtree(temp_dir)
                except Exception as e:
                    print(f"Error deleting temporary directory {temp_dir}: {str(e)}")
    else:
        st.warning("Please enter a valid YouTube URL")