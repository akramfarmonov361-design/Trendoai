import google.generativeai as genai
import os
from dotenv import load_dotenv

load_dotenv()

api_key = os.getenv('GEMINI_API_KEY')
print(f'API KEY looks like: {api_key[:10] if api_key else None}...')

genai.configure(api_key=api_key)
print('\n=== Available Gemini Models ===')
try:
    models = genai.list_models()
    count = 0
    for m in models:
        if 'gemini' in m.name:
            print(m.name)
            count += 1
            if count > 15: break
except Exception as e:
    print('Failed to list models:', str(e))

print('\n=== Testing generate_content ===')
try:
    m = genai.GenerativeModel('gemini-2.5-flash')
    print('Testing gemini-2.5-flash:')
    print(m.generate_content('salom').text)
    print('✅ SUCCESS!')
except Exception as e:
    print('❌ FAILED with gemini-2.5-flash:', type(e).__name__, str(e))

try:
    m = genai.GenerativeModel('gemini-3.1-flash-lite-preview')
    print('Testing gemini-3.1-flash-lite-preview:')
    print(m.generate_content('salom').text)
    print('✅ SUCCESS!')
except Exception as e:
    print('❌ FAILED with gemini-3.1-flash-lite-preview:', type(e).__name__, str(e))
