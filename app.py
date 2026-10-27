import os
import time
import threading
from flask import Flask, render_template_string, request, redirect, url_for
from werkzeug.utils import secure_filename
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

app = Flask(__name__)
UPLOAD_FOLDER = '/tmp'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Advanced Meet Controller</title>
    <style>
        body { font-family: sans-serif; padding: 20px; text-align: center; background: #121212; color: #e0e0e0; }
        .card { background: #1e1e1e; padding: 20px; border-radius: 8px; max-width: 400px; margin: auto; box-shadow: 0 4px 6px rgba(0,0,0,0.3); }
        input[type="text"], input[type="file"] { width: 90%; padding: 12px; margin: 10px 0; border: 1px solid #333; border-radius: 4px; background: #2a2a2a; color: #fff; font-size: 16px; }
        button { background: #007bff; color: white; padding: 14px 28px; border: none; border-radius: 4px; font-size: 16px; cursor: pointer; width: 95%; margin-top: 10px; font-weight: bold;}
        .status { margin-top: 20px; padding: 12px; background: #2d3748; border-radius: 4px; color: #cbd5e0; font-size: 14px; }
    </style>
</head>
<body>
    <div class="card">
        <h2>🤖 Stealth Meet Bot</h2>
        <form action="/run" method="post" enctype="multipart/form-data">
            <input type="text" name="meet_url" placeholder="Google Meet Link" required>
            <input type="text" name="bot_name" placeholder="Custom Display Name" required>
            <label style="display:block; text-align:left; margin: 10px 0 0 15px; font-size: 12px; color: #aaa;">Upload Audio (.wav or .mp3):</label>
            <input type="file" name="audio_file" accept=".mp3,.wav" required>
            <button type="submit">Deploy Bot</button>
        </form>
        {% if status %}
        <div class="status"><strong>Current State:</strong><br>{{ status }}</div>
        {% endif %}
    </div>
</body>
</html>
"""

BOT_STATUS = "Ready for instructions."

def run_bot(meet_url, bot_name, audio_path):
    global BOT_STATUS
    driver = None
    try:
        BOT_STATUS = "Initializing secure browser environment..."
        chrome_options = Options()
        chrome_options.add_argument("--headless=new")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--use-fake-ui-for-media-stream")
        chrome_options.add_argument(f"--use-file-for-fake-audio-capture={audio_path}")
        
        # Crucial for Render: Points Selenium to Render's hidden Chrome paths
        chrome_options.binary_location = "/usr/bin/google-chrome"
        
        driver = webdriver.Chrome(options=chrome_options)
        driver.get(meet_url)
        time.sleep(5)
        
        BOT_STATUS = f"Setting display name to '{bot_name}'..."
        try:
            name_input = WebDriverWait(driver, 5).until(
                EC.presence_of_element_located((By.XPATH, '//input[@type="text"]'))
            )
            name_input.clear()
            name_input.send_keys(bot_name)
        except:
            pass
            
        BOT_STATUS = "Clicking Join button..."
        join_button = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.XPATH, '//span[contains(text(), "Join") or contains(text(), "Ask")]'))
        )
        join_button.click()
        
        # Waiting room loops
        BOT_STATUS = "⏳ Stuck in Waiting Room. Waiting for Host to admit..."
        in_meeting = False
        timeout = 300 
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            if len(driver.find_elements(By.XPATH, '//button[@aria-label="Leave call"]')) > 0:
                in_meeting = True
                break
            time.sleep(3)
            
        if in_meeting:
            BOT_STATUS = "✅ Admitted! Broadcasting audio file now..."
            time.sleep(60) # Plays for 60 seconds
            BOT_STATUS = "Audio finished. Disconnecting securely..."
        else:
            BOT_STATUS = "❌ Timed out waiting in the waiting room."
            
    except Exception as e:
        BOT_STATUS = f"❌ Error tracking: {str(e)}"
    finally:
        if driver:
            driver.quit()
        if os.path.exists(audio_path):
            os.remove(audio_path)

@app.route('/')
def index():
    return render_template_string(HTML_TEMPLATE, status=BOT_STATUS)

@app.route('/run', methods=['POST'])
def handle_run():
    global BOT_STATUS
    meet_url = request.form.get('meet_url')
    bot_name = request.form.get('bot_name')
    file = request.files.get('audio_file')
    
    if file and meet_url and bot_name:
        filename = secure_filename(file.filename)
        audio_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(audio_path)
        
        threading.Thread(target=run_bot, args=(meet_url, bot_name, audio_path)).start()
        return redirect(url_for('index'))
        
    return render_template_string(HTML_TEMPLATE, status="Missing fields.")

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
  
