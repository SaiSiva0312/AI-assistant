import asyncio
import edge_tts
import os
import time
from playsound import playsound
import re # Import the regular expression module

import speech_recognition as sr
import webbrowser
import datetime
import wikipedia
import pyautogui
import requests
import json
import genai_request as ai
# Import the updated AI requesue
import google.generativeai as genai
# Make sure to load environment variables
from dotenv import load_dotenv
load_dotenv()


genai.configure(api_key=os.environ.get("GOOGLE_API_KEY"))
model = genai.GenerativeModel('gemini-1.5-flash')

VOICES = [
    "en-US-AnaNeural",      # Female (US)
    "en-GB-SoniaNeural",    # Female (UK)
    "en-US-ChristopherNeural", # Male (US)
    "en-AU-NatashaNeural",  # Female (Australia)
]
current_voice_index = 2
AUDIO_FILE = "response.mp3" # Temporary file to store the speech

async def speak(text):
    """
    Generates speech from text using Edge TTS, saves it to a file,
    plays it, and then cleans up the file.
    """
    global current_voice_index
    print(f"Dex: {text}")
    
    try:
        # Create a Communicate object with the selected voice and text
        communicate = edge_tts.Communicate(text, VOICES[current_voice_index])
        # Save the audio to the file
        await communicate.save(AUDIO_FILE)
        
        # Play the audio file
        playsound(AUDIO_FILE)
        
    except Exception as e:
        print(f"🔴 An error occurred during speech generation: {e}")
    finally:
        # Ensure the temporary audio file is removed
        if os.path.exists(AUDIO_FILE):
            os.remove(AUDIO_FILE)

def listen_for_audio():
    """Listens for any audio, converts it to text, and returns it."""
    r = sr.Recognizer()
    with sr.Microphone() as source:
        print("\nListening...")
        r.pause_threshold = 0.5
        audio = r.listen(source)

    try:
        print("Recognizing...")
        content = r.recognize_google(audio, language='en-in')
        print(f"You said: {content}")
        return content.lower()
    except sr.UnknownValueError:
        return ""
    except sr.RequestError as e:
        print(f"Could not request results; {e}")
        return ""
    except Exception as e:
        print(e)
        return ""

# --- Advanced Feature Functions (Unchanged) ---
def get_weather(city):
    api_key = os.environ.get("OPENWEATHER_API_KEY")
    if not api_key: return "Weather service is not configured."
    base_url = "http://api.openweathermap.org/data/2.5/weather?"
    complete_url = f"{base_url}appid={api_key}&q={city}&units=metric"
    try:
        response = requests.get(complete_url)
        data = response.json()
        if data["cod"] != "404":
            main = data["main"]; weather_desc = data["weather"][0]["description"]; temp = main["temp"]
            return f"The temperature in {city} is {temp} degrees Celsius with {weather_desc}."
        else: return "Sorry, I couldn't find the weather for that city."
    except Exception: return "Sorry, I'm having trouble fetching the weather right now."

def get_news():
    api_key = os.environ.get("NEWSAPI_KEY")
    if not api_key: return "News service is not configured."
    base_url = f"https://newsapi.org/v2/top-headlines?country=in&apiKey={api_key}"
    try:
        response = requests.get(base_url)
        data = response.json()
        articles = data.get("articles", [])
        if articles:
            headlines = ["Here are the top 5 news headlines from India:"]
            for i, article in enumerate(articles[:5]):
                headlines.append(f"Headline {i+1}: {article['title']}")
            return "\n".join(headlines)
        else: return "Sorry, I couldn't fetch the news right now."
    except Exception: return "Sorry, I'm having trouble fetching the news."

def manage_todo_list(request):
    if "add" in request or "new task" in request:
        task = request.replace("add", "").replace("new task", "").replace("to my to-do list", "").strip()
        if task:
            with open("todo.txt", "a") as file: file.write(task + "\n")
            return f"Okay, I've added '{task}' to your to-do list."
        else: return "What task should I add?"
    elif "what are my tasks" in request or "show my tasks" in request:
        try:
            with open("todo.txt", "r") as file: tasks = file.read()
            return "Here are the tasks on your to-do list:\n" + tasks if tasks else "Your to-do list is empty."
        except FileNotFoundError: return "You don't have a to-do list yet."

# --- Main Process (Now Asynchronous) ---
async def main_process():
    """Main async function to run the assistant."""
    global current_voice_index
    chat_session = ai.initialize_chat()
    if not chat_session: return

    await speak("Assistant activated with neural voices. How can I help you?")

    while True:
        request = listen_for_audio()
        if not request: continue

        # --- Process the command ---
        if "hello" in request:
            await speak("Hello there! How can I assist you?")
        
        elif "change your voice" in request:
            current_voice_index = (current_voice_index + 1) % len(VOICES)
            await speak(f"I have changed my voice to {VOICES[current_voice_index]}. How do I sound?")

        elif "play music" in request:
            await speak("Playing a random song on YouTube.")
            webbrowser.open("https://www.youtube.com/watch?v=dQw4w9WgXcQ&ab_channel=RickAstley")

        elif "time" in request:
            now_time = datetime.datetime.now().strftime("%I:%M %p")
            await speak(f"The current time is {now_time}")

        elif "date" in request:
            today_date = datetime.datetime.now().strftime("%B %d, %Y")
            await speak(f"Today's date is {today_date}")

        elif "open youtube" in request:
            await speak("Opening YouTube.")
            webbrowser.open("https://www.youtube.com")

        elif "search google for" in request:
            search_query = request.replace("search google for", "").strip()
            await speak(f"Searching Google for {search_query}")
            webbrowser.open(f"https://www.google.com/search?q={search_query}")

        elif "wikipedia" in request:
            search_query = request.replace("wikipedia", "").strip()
            await speak(f"Searching Wikipedia for {search_query}")
            try:
                result = wikipedia.summary(search_query, sentences=2)
                await speak("According to Wikipedia...")
                await speak(result)
            except Exception as e:
                await speak(f"Sorry, I couldn't find anything on Wikipedia for {search_query}.")

        # --- UPDATED: Image Generation Command ---
        elif "generate image" in request:
            image_description = re.sub(r'generate image of|generate image', '', request).strip()
            
            if not image_description:
                await speak("Of course. What would you like an image of?")
                image_description = listen_for_audio()
                if not image_description:
                    await speak("I didn't catch that. Cancelling the request.")
                    continue

            await speak(f"Okay, generating an image of {image_description}...")
            
            image_prompt = (f"Create a URL for a high-quality image of '{image_description}'. "
                            f"Use this exact format: https://source.unsplash.com/1920x1080/?<query>. "
                            f"Replace <query> with 2-3 relevant English keywords from my request, separated by commas.")
            
            url_response = ai.send_chat_message(chat_session, image_prompt)
            url_match = re.search(r'https?://\S+', url_response)

            if url_match:
                final_url = url_match.group()
                await speak("I've found an image for you. Now, I'll save it to your desktop.")
                
                try:
                    desktop_path = os.path.join(os.path.expanduser('~'), 'Desktop')
                    if not os.path.exists(desktop_path):
                        desktop_path = os.getcwd()
                        await speak("I could not find your desktop, so I will save it in the current folder.")

                    image_response = requests.get(final_url, stream=True)
                    image_response.raise_for_status()

                    safe_filename = re.sub(r'[\\/*?:"<>|]', "", image_description).replace(" ", "_")
                    file_path = os.path.join(desktop_path, f"{safe_filename}_{int(time.time())}.jpg")

                    with open(file_path, 'wb') as f:
                        for chunk in image_response.iter_content(chunk_size=812):
                            f.write(chunk)
                    
                    await speak(f"Done. The image has been saved to your desktop.")

                except requests.exceptions.RequestException as e:
                    await speak("Sorry, I had a problem downloading the image.")
                    print(f"🔴 Download error: {e}")
                except Exception as e:
                    await speak("Sorry, I encountered an error while saving the image.")
                    print(f"🔴 File saving error: {e}")
            else:
                await speak("I'm sorry, I wasn't able to create the image URL.")
                print(f"Debug: AI response was '{url_response}'")

        elif "weather" in request:
            if "in " in request: city = request.split("in ")[-1].strip()
            else: city = "your location" 
            response_text = get_weather(city)
            await speak(response_text)
        
        elif "news" in request:
            response_text = get_news()
            await speak(response_text)

        elif "to-do list" in request or "task" in request:
            response_text = manage_todo_list(request)
            await speak(response_text)

        elif "take a screenshot" in request:
            await speak("Taking a screenshot.")
            screenshot = pyautogui.screenshot()
            screenshot.save(f"screenshot_{time.time()}.png")
            await speak("Done. I've saved it in the script's directory.")

        elif "shutdown the system" in request:
            await speak("Are you sure you want to shut down the system?")
            confirmation = listen_for_audio()
            if "yes" in confirmation:
                await speak("Shutting down. Goodbye!")
                os.system("shutdown /s /t 1")
            else:
                await speak("Shutdown cancelled.")

        elif "restart the system" in request:
            await speak("Are you sure you want to restart the system?")
            confirmation = listen_for_audio()
            if "yes" in confirmation:
                await speak("Restarting now. See you soon!")
                os.system("shutdown /r /t 1")
            else:
                await speak("Restart cancelled.")

        elif "goodbye" in request or "exit" in request or "quit" in request:
            await speak("Goodbye! Have a great day.")
            break

        # --- General Chat Fallback ---
        else:
            print(f"Sending to AI: '{request}'")
            response = ai.send_chat_message(chat_session, request)
            await speak(response)

if __name__ == "__main__":
    # Run the asynchronous main function
    asyncio.run(main_process())
