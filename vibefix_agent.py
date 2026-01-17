import os
import json
import re
import time
from pathlib import Path
from dotenv import load_dotenv
from google import genai
from google.genai import types
from playwright.sync_api import sync_playwright # <--- NEW IMPORT

# 1. SETUP & SECRETS
load_dotenv()
api_key = os.getenv("GOOGLE_API_KEY")
if not api_key:
    raise ValueError("❌ API Key not found! Check your .env file.")

client = genai.Client(api_key=api_key)

# Define paths
HTML_FILE = Path("broken_button.html")
SCREENSHOT_BEFORE = Path("before_fix.png")
SCREENSHOT_AFTER = Path("after_fix.png")

# Helper function to get the file URL for the browser
def get_file_url(file_path):
    return file_path.absolute().as_uri()

def run_agent():
    print("🚀 VibeFix Agent Started...")

    with sync_playwright() as p:
        # 1. THE EYES: Launch Browser
        print("👀 Launching browser to inspect the site...")
        browser = p.chromium.launch(headless=False) # Set headless=True to hide the browser window
        page = browser.new_page()
        
        # Load the local HTML file
        page.goto(get_file_url(HTML_FILE))
        
        # Take "Before" Screenshot
        page.screenshot(path=SCREENSHOT_BEFORE)
        print(f"📸 Screenshot taken: {SCREENSHOT_BEFORE}")

        # 2. THE BRAIN: Send to Gemini
        print("🧠 Analyzing visual bugs with Gemini 2.0...")
        
        with open(HTML_FILE, 'r') as f:
            code_content = f.read()
            
        image_bytes = SCREENSHOT_BEFORE.read_bytes()

        prompt = """
        You are VibeFix, a Senior UI Designer obsessed with modern aesthetics.
        I have provided a screenshot and the source code.

        TASK:
        1. Critique the design. Does the button look like a standard 'Primary Action'? 
           (e.g., Light yellow is bad for primary buttons. Prefer strong colors like Blue, Green, or Black).
        2. Identify the CSS selector.
        3. Generate a MODERN CSS block. 
           - Change the background-color to a professional color (e.g., #007BFF, #28A745, or #333).
           - Ensure the text color contrasts perfectly (e.g., White text on dark background).

        OUTPUT FORMAT:
        Structure:
        {
            "diagnosis": "The button looks washed out and weak...",
            "css_selector": ".btn-primary",
            "full_fixed_css_block": ".btn-primary {\n    background-color: #0056b3;\n    color: #ffffff;\n    ... }"
        }
        """

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
            
            # Parse Response
            result = json.loads(response.text)
            print(f"\n✅ DIAGNOSIS: {result['diagnosis']}")
            
            # 3. THE HANDS: Apply the Fix
            selector = result['css_selector']
            new_code = result['full_fixed_css_block']
            
            # Use Regex to replace the code
            pattern = re.compile(re.escape(selector) + r"\s*\{.*?\}", re.DOTALL)
            
            if pattern.search(code_content):
                fixed_content = pattern.sub(new_code, code_content)
                
                with open(HTML_FILE, 'w') as f:
                    f.write(fixed_content)
                print(f"🛠️  Fix Applied to {HTML_FILE}!")
                
                # 4. VERIFICATION: Reload and Check
                print("🔄 Reloading browser to verify fix...")
                page.reload()
                time.sleep(1) # Give it a second to render
                page.screenshot(path=SCREENSHOT_AFTER)
                print(f"📸 Verification Screenshot taken: {SCREENSHOT_AFTER}")
                
            else:
                print(f"⚠️ Could not find selector '{selector}' in code.")

        except Exception as e:
            print(f"❌ Error during processing: {e}")

        # Close browser
        browser.close()
        print("\n✨ Mission Complete. Check 'after_fix.png' to see the result!")

if __name__ == "__main__":
    run_agent()