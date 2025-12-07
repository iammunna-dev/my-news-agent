import requests
from bs4 import BeautifulSoup
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import os
import google.generativeai as genai
import json
import re

# =====================================================
# CONFIGURATION
# =====================================================
RECEIVER_EMAIL = "iammunna32@gmail.com"  # <--- CHANGE THIS
# =====================================================

genai.configure(api_key=os.environ["GEMINI_API_KEY"])

def send_email(subject, body_html):
    """Sends a formatted HTML email."""
    try:
        sender_email = os.environ["EMAIL_USER"]
        sender_pass = os.environ["EMAIL_PASS"]
        
        msg = MIMEMultipart('alternative')
        msg['From'] = sender_email
        msg['To'] = RECEIVER_EMAIL
        msg['Subject'] = subject

        # Attach HTML content
        msg.attach(MIMEText(body_html, 'html', 'utf-8'))
        
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(sender_email, sender_pass)
        server.sendmail(sender_email, RECEIVER_EMAIL, msg.as_string())
        server.quit()
        print(">>> SUCCESS: Email Sent.")
    except Exception as e:
        print(f">>> CRITICAL ERROR: Could not send email. {e}")

def get_soup(url):
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
    try:
        response = requests.get(url, headers=headers)
        response.encoding = 'utf-8'
        return BeautifulSoup(response.content, 'html.parser')
    except:
        return None

def clean_ai_json(text):
    """Removes Markdown formatting if AI adds it"""
    text = text.replace("```json", "").replace("```", "").strip()
    return text

def ask_ai_to_filter(links_list, limit):
    """Asks Gemini to pick the best news links"""
    model = genai.GenerativeModel('gemini-1.5-flash')
    
    # We send a simplified list to save tokens
    simple_list = [{"text": x['text'], "url": x['url']} for x in links_list[:50]]
    
    prompt = f"""
    I have a list of website links. identify the top {limit} most relevant NEWS articles or OPINION pieces.
    Ignore 'Login', 'Sign up', 'Facebook', 'Latest Collection', 'Topic'.
    
    Return a JSON list of strings (URLs only). 
    Example: ["https://site.com/news/1", "https://site.com/news/2"]
    
    Data:
    {json.dumps(simple_list)}
    """
    
    try:
        response = model.generate_content(prompt)
        clean_text = clean_ai_json(response.text)
        return json.loads(clean_text)
    except Exception as e:
        print(f"AI Brain Error: {e}")
        return []

def extract_content(url):
    soup = get_soup(url)
    if not soup: return "Error", "Link broken."
    
    h1 = soup.find('h1')
    title = h1.get_text().strip() if h1 else "Unknown Title"
    
    # Grab all text
    paragraphs = soup.find_all('p')
    clean_text = [p.get_text().strip() for p in paragraphs if len(p.get_text()) > 40]
    body = "<br><br>".join(clean_text) # Use HTML breaks
    
    if len(body) < 100: body = "<i>Content could not be extracted automatically. Please click the link to read.</i>"
    
    return title, body

def run_agent():
    print("Agent Started...")
    final_data = []
    seen_urls = set()
    
    sources = [
        {"url": "https://www.prothomalo.com/opinion", "limit": 10, "name": "Opinion"},
        {"url": "https://www.prothomalo.com/opinion/editorial", "limit": 3, "name": "Editorial"}
    ]

    for source in sources:
        soup = get_soup(source['url'])
        if not soup: continue

        # 1. Gather Links
        raw_links = []
        for a in soup.find_all('a', href=True):
            href = a['href']
            text = a.get_text().strip()
            if len(text) > 5 and "auth" not in href:
                full_link = "https://www.prothomalo.com" + href if not href.startswith('http') else href
                raw_links.append({"text": text, "url": full_link})
        
        # 2. Ask AI
        print(f"Asking AI to pick {source['limit']} articles from {source['name']}...")
        selected_urls = ask_ai_to_filter(raw_links, source['limit'])
        
        # 3. Process
        for link in selected_urls:
            if link not in seen_urls:
                print(f"Reading: {link}")
                title, body = extract_content(link)
                final_data.append({"type": source['name'], "title": title, "link": link, "body": body})
                seen_urls.add(link)

    # --- GENERATE EMAIL ---
    if final_data:
        html_body = f"<h2>Daily Briefing ({len(final_data)} Articles)</h2><hr>"
        for item in final_data:
            html_body += f"<h3>[{item['type']}] {item['title']}</h3>"
            html_body += f"<p><a href='{item['link']}' style='color:blue; font-weight:bold;'>Click to Read Original</a></p>"
            html_body += f"<div style='background:#f9f9f9; padding:10px; border-left:4px solid #ccc;'>{item['body'][:3000]}...</div><br><hr>"
        
        send_email(f"Daily News ({len(final_data)})", html_body)
    else:
        # FALLBACK: If AI found nothing, send raw links so you get SOMETHING
        debug_html = "<h2>Agent Report: AI Found 0 Articles</h2>"
        debug_html += "<p>The AI analyzed the page but didn't return any valid links. Here are the raw links I saw:</p>"
        send_email("Agent Report: No News", debug_html)

if __name__ == "__main__":
    run_agent()
