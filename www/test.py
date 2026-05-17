from google import genai

client = genai.Client(api_key="AIzaSyDLxxi2m68-8YiketcZTErrHNZnrJNrZ3s")

try:
    # List mein se naya model name use kar rahe hain
    response = client.models.generate_content(
        model="gemini-2.5-flash", 
        contents="Jarvis online hai?"
    )
    print(f"✅ Success: {response.text}")
except Exception as e:
    print(f"Error: {e}")