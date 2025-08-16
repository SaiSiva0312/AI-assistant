import sys
import asyncio
import edge_tts
import os
import time
from playsound import playsound
import speech_recognition as sr
import webbrowser
import datetime
import wikipedia
import requests
import genai_request as ai
from dotenv import load_dotenv
import random
import pyautogui
import pywhatkit as pwk

from PyQt5.QtWidgets import QApplication, QWidget, QVBoxLayout, QTextEdit, QPushButton, QLabel, QHBoxLayout
from PyQt5.QtGui import QFont, QPalette, QColor, QMovie
from PyQt5.QtCore import Qt, QObject, QThread, pyqtSignal, QSize, QPoint, pyqtSlot

# --- Load Environment Variables ---
load_dotenv()

# --- Assistant Backend Logic (Advanced) ---
class AssistantWorker(QObject):
    status_changed = pyqtSignal(str)
    orb_state_changed = pyqtSignal(str)
    new_message = pyqtSignal(str, str)
    finished = pyqtSignal()

    def __init__(self):
        super().__init__()
        self.is_running = True
        self.chat_session = ai.initialize_chat()
        self.VOICES = ["en-US-AnaNeural", "en-GB-SoniaNeural", "en-US-ChristopherNeural"]
        self.current_voice_index = 0
        self.AUDIO_FILE = "response.mp3"

    async def speak(self, text):
        self.new_message.emit("Dex", text)
        try:
            communicate = edge_tts.Communicate(text, self.VOICES[self.current_voice_index])
            await communicate.save(self.AUDIO_FILE)
            playsound(self.AUDIO_FILE)
        except Exception as e:
            print(f"🔴 Speech Error: {e}")
        finally:
            if os.path.exists(self.AUDIO_FILE):
                os.remove(self.AUDIO_FILE)

    def listen(self):
        r = sr.Recognizer()
        with sr.Microphone() as source:
            self.status_changed.emit("Listening...")
            self.orb_state_changed.emit("listening")
            r.pause_threshold = 0.7
            r.adjust_for_ambient_noise(source, duration=1)
            audio = r.listen(source)
        try:
            self.status_changed.emit("Recognizing...")
            self.orb_state_changed.emit("thinking")
            content = r.recognize_google(audio, language='en-in')
            self.new_message.emit("You", content)
            return content.lower()
        except Exception:
            self.orb_state_changed.emit("idle")
            self.status_changed.emit("I didn't catch that. Could you please repeat?")
            return ""

    async def process_command(self, request):
        if not request:
            self.orb_state_changed.emit("idle")
            return

        # --- Advanced Commands ---
        if "hello" in request:
            await self.speak("Hello! How can I help you?")
        elif "time" in request:
            now_time = datetime.datetime.now().strftime("%I:%M %p")
            await self.speak(f"The current time is {now_time}.")
        elif "date" in request:
            today_date = datetime.datetime.now().strftime("%B %d, %Y")
            await self.speak(f"Today's date is {today_date}.")
        elif "wikipedia" in request:
            query = request.replace("wikipedia", "").strip()
            await self.speak(f"Searching Wikipedia for '{query}'.")
            try:
                result = wikipedia.summary(query, sentences=2)
                await self.speak(f"According to Wikipedia, {result}")
            except Exception:
                await self.speak(f"Sorry, I couldn't find any information on '{query}'.")
        # --- UPDATED: Advanced Music Control ---
        elif "play" in request:
            song = request.replace("play", "").strip()
            if song:
                await self.speak(f"Now playing {song} on YouTube.")
                pwk.playonyt(song)
            else:
                await self.speak("What song would you like me to play?")
        elif "change your voice" in request:
            self.current_voice_index = (self.current_voice_index + 1) % len(self.VOICES)
            await self.speak("I've updated my voice. How do I sound?")
        elif "open youtube" in request:
            await self.speak("Opening YouTube.")
            webbrowser.open("https://www.youtube.com")
        elif "search google for" in request:
            query = request.replace("search google for", "").strip()
            await self.speak(f"Searching Google for {query}.")
            webbrowser.open(f"https://www.google.com/search?q={query}")
        elif "weather" in request:
            city = request.split("in ")[-1].strip() if "in " in request else "your current location"
            await self.get_weather(city)
        elif "news" in request:
            await self.get_news()
        elif "take a screenshot" in request:
            await self.speak("Taking a screenshot.")
            screenshot = pyautogui.screenshot()
            screenshot.save(f"screenshot_{time.time()}.png")
            await self.speak("Done. The screenshot has been saved in the script's directory.")
        elif "shutdown the system" in request:
            await self.speak("Are you sure you want to shut down?")
            confirmation = self.listen()
            if "yes" in confirmation:
                await self.speak("Shutting down. Goodbye!")
                os.system("shutdown /s /t 1")
            else:
                await self.speak("Shutdown cancelled.")
        elif "restart the system" in request:
            await self.speak("Are you sure you want to restart?")
            confirmation = self.listen()
            if "yes" in confirmation:
                await self.speak("Restarting now.")
                os.system("shutdown /r /t 1")
            else:
                await self.speak("Restart cancelled.")
        elif "goodbye" in request or "exit" in request:
            await self.speak("Goodbye!")
            self.is_running = False
            self.finished.emit()
        else:
            await self.speak("One moment while I process that.")
            response = ai.send_chat_message(self.chat_session, request)
            await self.speak(response)
        self.orb_state_changed.emit("idle")

    async def get_weather(self, city):
        api_key = os.environ.get("OPENWEATHER_API_KEY")
        if not api_key:
            await self.speak("Weather service is not configured. Please add an API key.")
            return
        base_url = "http://api.openweathermap.org/data/2.5/weather?"
        complete_url = f"{base_url}appid={api_key}&q={city}&units=metric"
        try:
            response = requests.get(complete_url)
            data = response.json()
            if data["cod"] != "404":
                main = data["main"]
                weather_desc = data["weather"][0]["description"]
                temp = main["temp"]
                await self.speak(f"The temperature in {city} is {temp} degrees Celsius with {weather_desc}.")
            else:
                await self.speak("Sorry, I couldn't find the weather for that city.")
        except Exception:
            await self.speak("I'm having trouble fetching the weather right now.")

    async def get_news(self):
        api_key = os.environ.get("NEWSAPI_KEY")
        if not api_key:
            await self.speak("News service is not configured. Please add an API key.")
            return
        base_url = f"https://newsapi.org/v2/top-headlines?country=in&apiKey={api_key}"
        try:
            response = requests.get(base_url)
            data = response.json()
            articles = data.get("articles", [])
            if articles:
                await self.speak("Here are the top 3 news headlines:")
                for i, article in enumerate(articles[:3]):
                    await self.speak(article['title'])
            else:
                await self.speak("Sorry, I couldn't fetch the news right now.")
        except Exception:
            await self.speak("I'm having trouble fetching the news right now.")

    @pyqtSlot()
    def run_single_command(self):
        if self.is_running:
            request = self.listen()
            asyncio.run(self.process_command(request))


# --- Main UI Window ---
class DexUI(QWidget):
    start_listening_signal = pyqtSignal()

    def __init__(self):
        super().__init__()
        self.old_pos = self.pos()
        self.initUI()
        self.setup_assistant_thread()

    def initUI(self):
        self.setWindowFlags(Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setGeometry(100, 100, 500, 700)

        self.container = QWidget(self)
        self.container.setGeometry(0, 0, 500, 700)
        self.container.setStyleSheet("""
            background-color: black; 
            border-radius: 20px;
            border: 3px solid transparent;
            border-image: qlineargradient(x1:0, y1:0, x2:1, y2:1, 
                                        stop:0 #00FFFF, stop:1 #F400A1) 3;
        """)
        
        self.main_layout = QVBoxLayout(self.container)
        self.main_layout.setContentsMargins(20, 10, 20, 20)

        title_bar = QWidget()
        title_bar_layout = QHBoxLayout(title_bar)
        title_bar_layout.setContentsMargins(0, 0, 0, 0)
        
        self.title_label = QLabel('D E X')
        self.title_label.setFont(QFont('Inter', 14, QFont.Bold))
        self.title_label.setStyleSheet("color: #E5E7EB; letter-spacing: 3px; background: transparent; border: none;")

        btn_minimize = QPushButton("—")
        btn_close = QPushButton("✕")
        for btn, func in [(btn_minimize, self.showMinimized), (btn_close, self.close)]:
            btn.setFixedSize(30, 30)
            btn.setFont(QFont('Inter', 12))
            btn.setStyleSheet("""
                QPushButton { background-color: transparent; color: #6B7280; border: none; }
                QPushButton:hover { color: white; }
            """)
            btn.clicked.connect(func)
        
        title_bar_layout.addWidget(self.title_label)
        title_bar_layout.addStretch()
        title_bar_layout.addWidget(btn_minimize)
        title_bar_layout.addWidget(btn_close)
        
        self.status_label = QLabel('Click the button to start')
        self.status_label.setFont(QFont('Inter', 12))
        self.status_label.setAlignment(Qt.AlignCenter)
        self.status_label.setStyleSheet("color: #6B7280; background: transparent; border: none;")
        
        self.orb_label = QLabel()
        self.orb_label.setAlignment(Qt.AlignCenter)
        
        self.movie_idle = QMovie("idle.gif")
        self.movie_listening = QMovie("listening.gif")
        self.movie_thinking = QMovie("thinking.gif")
        
        self.orb_label.setMovie(self.movie_idle)
        self.movie_idle.start()
        self.orb_label.setFixedSize(200, 200)
        for movie in [self.movie_idle, self.movie_listening, self.movie_thinking]:
            movie.setScaledSize(QSize(200,200))

        self.chat_display = QTextEdit()
        self.chat_display.setReadOnly(True)
        self.chat_display.setFont(QFont('Inter', 10))
        self.chat_display.setStyleSheet("""
            QTextEdit {
                background-color: #111827;
                border: 1px solid #00FFFF;
                border-radius: 12px;
                padding: 10px;
                color: #F9FAFB;
            }
        """)
        
        self.action_button = QPushButton('Speak')
        self.action_button.setFont(QFont('Inter', 12, QFont.Bold))
        self.action_button.setCursor(Qt.PointingHandCursor)
        self.action_button.setStyleSheet("""
            QPushButton {
                background-color: #00BFFF; color: white; border-radius: 12px;
                padding: 14px; margin-top: 10px; border: none;
            }
            QPushButton:hover { background-color: #ff2a6d ; }
        """)
        self.action_button.clicked.connect(self.trigger_listen)
        
        self.main_layout.addWidget(title_bar)
        self.main_layout.addWidget(self.status_label)
        self.main_layout.addWidget(self.orb_label, alignment=Qt.AlignCenter)
        self.main_layout.addWidget(self.chat_display)
        self.main_layout.addWidget(self.action_button)
        
        self.set_orb_state("idle")

    def setup_assistant_thread(self):
        self.thread = QThread()
        self.worker = AssistantWorker()
        self.worker.moveToThread(self.thread)

        self.worker.status_changed.connect(self.status_label.setText)
        self.worker.orb_state_changed.connect(self.set_orb_state)
        self.worker.new_message.connect(self.add_message)
        self.worker.finished.connect(self.close)
        
        self.start_listening_signal.connect(self.worker.run_single_command)
        
        self.thread.start()
        self.add_message("Dex", "Hello! I'm ready. Click the button to speak.")
        self.set_orb_state("idle")

    def trigger_listen(self):
        self.start_listening_signal.emit()

    def add_message(self, sender, message):
        align = "right" if sender.lower() == 'you' else "left"
        bg_color = "#374151" if sender.lower() == 'you' else "#00BFFF"
        text_color = "white" if sender.lower() == 'you' else "black"
        
        formatted_message = f"""
        <div style='text-align: {align}; margin-bottom: 12px;'>
            <span style='background-color: {bg_color}; color: {text_color}; padding: 10px 15px; border-radius: 18px; display: inline-block; max-width: 75%; font-weight: 500;'>
                {message}
            </span>
        </div>
        """
        self.chat_display.append(formatted_message)

    def set_orb_state(self, state):
        if state == 'listening':
            self.orb_label.setMovie(self.movie_listening)
            self.movie_listening.start()
        elif state == 'thinking':
            self.orb_label.setMovie(self.movie_thinking)
            self.movie_thinking.start()
        else: # idle
            self.orb_label.setMovie(self.movie_idle)
            self.movie_idle.start()

    def mousePressEvent(self, event):
        self.old_pos = event.globalPos()

    def mouseMoveEvent(self, event):
        delta = QPoint(event.globalPos() - self.old_pos)
        self.move(self.x() + delta.x(), self.y() + delta.y())
        self.old_pos = event.globalPos()

    def closeEvent(self, event):
        if self.thread.isRunning():
            self.worker.is_running = False
            self.thread.quit()
            self.thread.wait()
        event.accept()

if __name__ == '__main__':
    app = QApplication(sys.argv)
    ex = DexUI()
    ex.show()
    sys.exit(app.exec_())
