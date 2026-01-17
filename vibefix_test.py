import os
import json
from pathlib import Path
from dotenv import load_dotenv
from google import genai
from google.genai import types
import re # Add this at the top with your other imports

# 1. LOAD SECRETS
# This looks for the .env file and loads it into the system environment
load_dotenv() 

# Now access the key safely
api_key = os.getenv("GOOGLE_API_KEY")

if not api_key:
    raise ValueError("❌ API Key not found! Check your .env file.")

client = genai.Client(api_key=api_key)

# 2. LOAD ASSETS
# Read the broken code
with open('broken_button.html', 'r') as f:
    code_content = f.read()

# Read the screenshot
image_path = Path('screenshot.png')
if not image_path.exists():
    raise FileNotFoundError(f"❌ Image not found at {image_path.absolute()}")

image_bytes = image_path.read_bytes()

# 3. THE PROMPT
# We give it the EYES (Image) and the BRAIN (Code)
prompt = """
You are VibeFix, an autonomous UI repair agent.
I have provided a screenshot and the source code.

TASK:
1. Identify the visual accessibility issue (contrast, alignment, overlap).
2. Find the CSS selector responsible.
3. Generate the FIXED CSS properties.

# UPDATE THIS PART OF YOUR PROMPT
OUTPUT FORMAT:
Structure:
{
    "diagnosis": "Brief description...",
    "css_selector": ".btn-primary",
    "full_fixed_css_block": ".btn-primary {\n    background-color: #FFEB3B;\n    color: #000000;\n    padding: 10px 20px;\n    border: none;\n    border-radius: 4px;\n    font-weight: bold;\n    cursor: pointer;\n}"
}
"""

# 4. RUN THE AGENT
print("🤖 VibeFix is looking at your code...")

try:
    response = client.models.generate_content(
        model='gemini-2.0-flash',
        contents=[
            prompt,
            types.Part.from_bytes(data=image_bytes, mime_type='image/png'),
            code_content
        ],
        config=types.GenerateContentConfig(
            response_mime_type='application/json'
        )
    )

    # 5. RESULTS (Print raw response for debugging)
    # print(response.text) 

    # 6. PARSE THE AGENT'S WORK
    try:
        result = json.loads(response.text)
        
        print(f"\n✅ DIAGNOSIS: {result['diagnosis']}")
        print(f"🎯 SELECTOR:  {result['css_selector']}")
        # FIX: We now print 'full_fixed_css_block' instead of 'fixed_css'
        print(f"🛠️  NEW CODE:  \n{result['full_fixed_css_block']}") 
        
        # 7. THE "HANDS": APPLY THE FIX
        try:
            selector = result['css_selector']
            new_code_block = result['full_fixed_css_block']
            
            with open('broken_button.html', 'r') as f:
                original_content = f.read()

            # REGEX FIX: Safer way to find the specific CSS block
            # re.escape ensures dots (.) don't break the match
            pattern = re.compile(re.escape(selector) + r"\s*\{.*?\}", re.DOTALL)
            
            if pattern.search(original_content):
                fixed_content = pattern.sub(new_code_block, original_content)
                
                with open('broken_button.html', 'w') as f:
                    f.write(fixed_content)
                    
                print(f"\n✨ SUCCESS: 'broken_button.html' has been updated!")
                print("👉 Go refresh your browser. The button should be yellow and black.")
            else:
                print(f"\n⚠️ WARNING: Could not find '{selector}' in the HTML file.")
                print("Make sure the selector in the JSON matches the code exactly.")

        except KeyError as e:
            print(f"JSON Key Error: {e} - The AI didn't output the key we expected.")

    except json.JSONDecodeError:
        print("⚠️ AI failed to return valid JSON.")

except Exception as e:
    print(f"\n❌ SYSTEM ERROR:\n{e}")