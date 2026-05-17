from http import client
import json
import subprocess

import eel
import os
import sqlite3
import re
import time
import webbrowser
from playsound import playsound
import pyautogui

from engine.command import speak
from engine.config import ASSISTANT_NAME, LLM_KEY
from engine.db import cursor, conn
from engine.helper import extract_yt_term, markdown_to_text, remove_words
from pipes import quote
from hugchat import hugchat
import pywhatkit as kit
import pvporcupine
import pyaudio
import struct
# playing assistant sound function
conn = sqlite3.connect("jarvis.db")
cursor = conn.cursor()
@eel.expose
def playAssistantSound():
    music_dir = "www\\assets\\vendore\\texllate\\audio\\www_assets_audio_start_sound.mp3"
    playsound(music_dir)

def openCommand(query):
    query = query.replace(ASSISTANT_NAME, "")
    query = query.replace("open ", "")
    query.lower()

    app_name = query.strip().lower()

    if app_name != "":
        try:
            cursor.execute('SELECT path FROM sys_command WHERE name IN (?)', (app_name,))
            results = cursor.fetchall()

            if len(results) != 0:
                speak("Opening "+query)
                os.startfile(results[0][0])
            elif len(results) == 0:
                cursor.execute('SELECT url FROM web_command WHERE name IN (?)', (app_name,))
                results = cursor.fetchall()
                if len(results) != 0:
                    speak("Opening "+query)
                    webbrowser.open(results[0][0])

                else:
                    speak("opening "+query)
                    try:
                        os.system('start '+query)
                    except:
                        speak("not found")
        except:
            speak("some thing went wrong")



def PlayYoutube(query):
    search_term = extract_yt_term(query)
    
    # Agar Regex se mil gaya toh sahi hai
    if search_term:
        speak("Playing " + search_term + " on YouTube")
        kit.playonyt(search_term)
    else:
        # Fallback: Agar upar wala fail ho jaye, toh manually keywords hata do
        # Isse code kabhi crash nahi hoga
        clean_query = query.lower().replace("playing", "").replace("play", "").replace("on youtube", "").strip()
        
        if clean_query:
            speak("Playing " + clean_query + " on YouTube")
            kit.playonyt(clean_query)
        else:
            speak("Sir, I couldn't understand what to play. Please try again.")


def hotword():
    porcupine = None
    paud=None
    audio_stream = None
    try:
        porcupine = pvporcupine.create(keywords=["jarvis","alexa"])
        paud=pyaudio.PyAudio()
        audio_stream=paud.open(rate=porcupine.sample_rate, channels=1, format=pyaudio.paInt16, input=True, frames_per_buffer=porcupine.frame_length)
        while True:
            keyword=audio_stream.read(porcupine.frame_length)
            keyword=struct.unpack_from("h"*porcupine.frame_length,keyword)
            keyword_index=porcupine.process(keyword)
            if keyword_index>=0:
                print("Hotword Detected")
                
                import pyautogui as autogui
                autogui.keyDown("win")
                autogui.press("j")
                time.sleep(2)
                autogui.keyUp("win")

    except:
        if porcupine is not None:
            porcupine.delete()
        if audio_stream is not None:
            audio_stream.close()
        if paud is not None:
            paud.terminate()

# find contacts
def findContact(query):
    
    
    words_to_remove = [ASSISTANT_NAME, 'make', 'a', 'to', 'phone', 'call', 'send', 'message', 'whatsapp', 'video']
    query = remove_words(query, words_to_remove)

    try:
        query = query.strip().lower()
        cursor.execute("SELECT mobile_no FROM contacts WHERE LOWER(name) LIKE ? OR LOWER(name) LIKE ?", ('%' + query + '%', query + '%'))
        results = cursor.fetchall()
        print(results[0][0])
        mobile_number_str = str(results[0][0])
        if not mobile_number_str.startswith('+91'):
            mobile_number_str = '+91' + mobile_number_str

        return mobile_number_str, query
    except:
        speak('not exist in contacts')
        return 0, 0
    
def whatsApp(mobile_no, message, flag, name):

    if flag == 'message':
        target_tab = 13
        jarvis_message = "message send successfully to "+name

    elif flag == 'call':
        target_tab = 6
        message = ''
        jarvis_message = "calling to "+name

    else:
        target_tab = 6
        message = ''
        jarvis_message = "staring video call with "+name

    # Encode the message for URL
    encoded_message = quote(message)

    # Construct the URL
    whatsapp_url = f"whatsapp://send?phone={mobile_no}&text={encoded_message}"

    # Construct the full command
    full_command = f'start "" "{whatsapp_url}"'

    # Open WhatsApp with the constructed URL using cmd.exe
    subprocess.run(full_command, shell=True)
    time.sleep(5)
    
    
    pyautogui.hotkey('ctrl', 'f')

    for i in range(1, target_tab):
        pyautogui.hotkey('tab')

    pyautogui.hotkey('enter')
    speak(jarvis_message)



import time
from google import genai
from google.api_core import exceptions

# --- GLOBAL INITIALIZATION (Handshake ek baar = 3 Second Speed) ---
# Isse login baar-baar nahi hoga, isliye speed fast rahegi
client = genai.Client(api_key=LLM_KEY)

def geminai(query):
    """
    Jarvis AI ka main brain function jo 503 error ko handle karta hai.
    """
    try:
        # Query cleanup
        query = query.replace(ASSISTANT_NAME, "").replace("search", "").strip()
        if not query:
            return

        # --- ATTEMPT 1: Primary Model (Gemini 2.5 Flash) ---
        try:
            response = client.models.generate_content(
                model="gemini-2.5-flash",
                contents=f"Context: Your name is Jarvis. Keep responses very short and helpful. User: {query}"
            )
        
        # Agar server busy hai (503) ya limit khatam (429)
        except (exceptions.ServiceUnavailable, exceptions.ResourceExhausted):
            print("Jarvis: High demand on main server. Switching to backup...")
            time.sleep(1) # Chota sa break taaki server settle ho jaye
            
            # --- ATTEMPT 2: Backup Model (Gemini 2.0 Flash Lite) ---
            # Ye model aksar khali hota hai aur jaldi reply deta hai
            response = client.models.generate_content(
                model="gemini-2.0-flash-lite",
                contents=f"You are Jarvis. Be brief. User: {query}"
            )

        # Output logic
        if response.text:
            filter_text = markdown_to_text(response.text)
            print(f"Jarvis: {filter_text}")
            speak(filter_text)
            
    except Exception as e:
        print(f"Gemini Global Error: {e}")
        speak("Sir, I am having trouble connecting to the neural network. Please try again in a moment.")

def markdown_to_text(text):
    """
    Ye function response se faltu symbols (*, #) hata deta hai taaki speak sahi kare.
    """
    import re
    # Remove bold/italic symbols
    clean_text = re.sub(r'[*_#]', '', text)
    # Remove extra spaces
    clean_text = clean_text.strip()
    return clean_text

        
# Settings Modal 



# Assistant name
@eel.expose
def assistantName():
    name = ASSISTANT_NAME
    return name


@eel.expose
def personalInfo():
    try:
        cursor.execute("SELECT * FROM info")
        results = cursor.fetchall()
        jsonArr = json.dumps(results[0])
        eel.getData(jsonArr)
        return 1    
    except:
        print("no data")


@eel.expose
def updatePersonalInfo(name, designation, mobileno, email, city):
    cursor.execute("SELECT COUNT(*) FROM info")
    count = cursor.fetchone()[0]

    if count > 0:
        # Update existing record
        cursor.execute(
            '''UPDATE info 
               SET name=?, designation=?, mobileno=?, email=?, city=?''',
            (name, designation, mobileno, email, city)
        )
    else:
        # Insert new record if no data exists
        cursor.execute(
            '''INSERT INTO info (name, designation, mobileno, email, city) 
               VALUES (?, ?, ?, ?, ?)''',
            (name, designation, mobileno, email, city)
        )

    conn.commit()
    personalInfo()
    return 1



@eel.expose
def displaySysCommand():
    cursor.execute("SELECT * FROM sys_command")
    results = cursor.fetchall()
    jsonArr = json.dumps(results)
    eel.displaySysCommand(jsonArr)
    return 1


@eel.expose
def deleteSysCommand(id):
    cursor.execute("DELETE FROM sys_command WHERE id = ?", (id,))
    conn.commit()


@eel.expose
def addSysCommand(key, value):
    cursor.execute(
        '''INSERT INTO sys_command VALUES (?, ?, ?)''', (None,key, value))
    conn.commit()


@eel.expose
def displayWebCommand():
    cursor.execute("SELECT * FROM web_command")
    results = cursor.fetchall()
    jsonArr = json.dumps(results)
    eel.displayWebCommand(jsonArr)
    return 1


@eel.expose
def addWebCommand(key, value):
    cursor.execute(
        '''INSERT INTO web_command VALUES (?, ?, ?)''', (None, key, value))
    conn.commit()


@eel.expose
def deleteWebCommand(id):
    cursor.execute("DELETE FROM web_command WHERE Id = ?", (id,))
    conn.commit()


@eel.expose
def displayPhoneBookCommand():
    cursor.execute("SELECT * FROM contacts")
    results = cursor.fetchall()
    jsonArr = json.dumps(results)
    eel.displayPhoneBookCommand(jsonArr)
    return 1


@eel.expose
def deletePhoneBookCommand(id):
    cursor.execute("DELETE FROM contacts WHERE Id = ?", (id,))
    conn.commit()


@eel.expose
def InsertContacts(Name, MobileNo, Email, City):
    cursor.execute(
        '''INSERT INTO contacts VALUES (?, ?, ?, ?, ?)''', (None,Name, MobileNo, Email, City))
    conn.commit()






    