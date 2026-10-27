import os
import time
import threading
from flask import Flask, render_template_string, request, redirect, url_for
from werkzeug.utils import secure_filename
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
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
    <title>Advanced Meet Controller - Production</title>
    <style>
        body { font-family: sans-serif; padding: 20px; text-align: center; background: #121212; color: #e0e0e0; }
        .card { background: #1e1e1e; padding: 20px; border-radius: 8px; max-width: 450px; margin: auto; box-shadow: 0 4px 6px rgba(0,0,0,0.3); }
        input[type="text"], input[type="file"] { width: 90%; padding: 12px; margin: 10px 0; border: 1px solid #333; border-radius: 4px; background: #2a2a2a; color: #fff; font-size: 16px; }
        button { background: #007bff; color: white; padding: 14px 28px; border: none; border-radius: 4px; font-size: 16px; cursor: pointer; width: 95%; margin-top: 10px; font-weight: bold;}
        .status { margin-top: 20px; padding: 12px; background: #2d3748; border-radius: 4px; color: #cbd5e0; font-size: 13px; text-align: left; word-break: break-all; white-space: pre-wrap; font-family: monospace; max-height: 220px; overflow-y: auto;}
    </style>
</head>
<body>
    <div class="card">
        <h2>🤖 Stealth Meet Bot</h2>
        <form action="/run" method="post" enctype="multipart/form-data">
            <input type="text" name="meet_url" placeholder="Google Meet Link" required>
            <input type="text" name="bot_name" placeholder="Custom Display Name" required>
            <label style="display:block; text-align:left; margin: 10px 0 0 15px; font-size: 12px; color: #aaa;">Upload Audio (.wav format only):</label>
            <input type="file" name="audio_file" accept=".wav" required>
            <button type="submit">Deploy Bot</button>
        </form>
        {% if status %}
        <div class="status"><strong>Execution Status:</strong><br>{{ status }}</div>
        {% endif %}
    </div>
</body>
</html>
"""

BOT_STATUS = "Ready for instructions."

def update_status(msg):
    global BOT_STATUS
    BOT_STATUS = msg
    print(f"[MEET BOT LOG] {msg}")

def run_bot(meet_url, bot_name, audio_path):
    driver = None
    try:
        update_status("Configuring Chromium options...")
        chrome_options = Options()
        chrome_options.add_argument("--headless=new")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--use-fake-ui-for-media-stream")
        
        if audio_path and os.path.exists(audio_path):
            update_status(f"Attaching audio file target: {audio_path}")
            chrome_options.add_argument(f"--use-file-for-fake-audio-capture={audio_path}")
            
        # Point directly to native Debian Chromium binaries
        chrome_options.binary_location = "/usr/bin/chromium"
        driver_service = Service(executable_path="/usr/bin/chromedriver")
        
        update_status("Launching local Chromium service (no network download)...")
        driver = webdriver.Chrome(service=driver_service, options=chrome_options)
        
        update_status(f"Navigating to Meet URL: {meet_url}")
        driver.get(meet_url)
        time.sleep(5)
        
        update_status(f"Entering display name: '{bot_name}'...")
        try:
            name_input = WebDriverWait(driver, 8).until(
                EC.presence_of_element_located((By.XPATH, '//input[@type="text"]'))
            )
            name_input.clear()
            name_input.send_keys(bot_name)
            update_status("Display name successfully entered.")
        except Exception as e:
            update_status(f"Name entry skipped/pre-set: {str(e)}")
            
        update_status("Clicking Join / Ask to Join button...")
        join_button = WebDriverWait(driver, 12).until(
            EC.element_to_be_clickable((By.XPATH, '//span[contains(text(), "Join") or contains(text(), "Ask")]'))
        )
        join_button.click()
        update_status("Join action triggered!")
        
        # Waiting room polling loop
        update_status("⏳ Monitoring waiting room for host approval...")
        in_meeting = False
        timeout = 300 
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            leave_buttons = driver.find_elements(By.XPATH, '//button[@aria-label="Leave call"]')
            if len(leave_buttons) > 0:
                in_meeting = True
                break
            time.sleep(5)
            update_status(f"Waiting in lobby... elapsed: {int(time.time() - start_time)}s")
            
        if in_meeting:
            update_status("✅ Admitted! Broadcasting virtual audio stream for 60 seconds...")
            time.sleep(60) 
            update_status("Audio broadcast finished. Disconnecting session...")
        else:
            update_status("❌ Timed out in waiting room (300s limit reached).")
            driver.save_screenshot('/tmp/meet_timeout.png')
            
    except Exception as e:
        error_msg = f"❌ Error encountered: {str(e)}"
        update_status(error_msg)
        if driver:
            try:
                driver.save_screenshot('/tmp/meet_error.png')
                update_status("Saved failure screenshot to /tmp/meet_error.png")
            except:
                pass
    finally:
        if driver:
            try:
                driver.quit()
                update_status("Browser closed successfully.")
            except:
                pass
        if audio_path and os.path.exists(audio_path):
            try:
                os.remove(audio_path)
            except:
                pass

@app.route('/')
def index():
    return render_template_string(HTML_TEMPLATE, status=BOT_STATUS)

@app.route('/run', methods=['POST'])
def handle_run():
    meet_url = request.form.get('meet_url')
    bot_name = request.form.get('bot_name')
    file = request.files.get('audio_file')
    
    if file and meet_url and bot_name:
        if not file.filename.lower().endswith('.wav'):
            return render_template_string(HTML_TEMPLATE, status="❌ Error: Only .wav audio files are accepted.")
            
        filename = secure_filename(file.filename)
        audio_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(audio_path)
        
        update_status("Deployment request accepted. Initializing thread...")
        threading.Thread(target=run_bot, args=(meet_url, bot_name, audio_path)).start()
        return redirect(url_for('index'))
        
    return render_template_string(HTML_TEMPLATE, status="Missing form fields.")

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
    
