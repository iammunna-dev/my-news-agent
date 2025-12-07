import requests
from bs4 import BeautifulSoup
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import os
import google.generativeai as genai
import json
import time

# =====================================================
# CONFIGURATION
# =====================================================
RECEIVER_EMAIL = "iammunna32@gmail.com"  # <--- CHANGE THIS
# =====================================================

# Initialize Gemini
genai.configure(api_key=os.environ["GEMINI_API_KEY"])

def get_soup(url):
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    try:
        response = requests.get(url, headers=headers)
        response.encoding = 'utf-8'
        return BeautifulSoup(response.content, 'html.parser')
    except:
        return None

def ask_ai_to_filter_links(links_list, limit):
    """
    Sends the raw list of links to Gemini and asks it to pick the real news.
    """
    model = genai.GenerativeModel('gemini-1.5-flash')
    
    # We create a prompt that feeds the raw data to the AI
    prompt = f"""
    I have a list of links from the Prothom Alo Opinion page. 
    I need you to identify the ACTUAL news articles / opinion pieces.
    Ignore links to 'Login', 'Facebook', 'Twitter', 'Collections', 'Images', or 'Ads'.
    
    Return exactly {limit} links that seem to be the most recent/important articles.
    
    Return ONLY a valid JSON list of strings (URLs). Do not write any other text.
    
    Here is the list:
    {json.dumps(links_list)}
    """
    
    try:
        response = model.generate_content(prompt)
        # Clean up response (sometimes AI adds markdown backticks)
        clean_text = response.text.replace("```json", "").replace("```", "").strip()
        return json.loads(clean_text)
    except Exception as e:
        print(f"AI Brain Error: {e}")
        return []

def extract_content(url):
    """
    Visits the chosen URL and grabs text.
    """
    soup = get_soup(url)
    if not soup: return "Error loading page."
    
    # 1. Title
    h1 = soup.find('h1')
    title = h1.get_text().strip() if h1 else "Unknown Title"
    
    # 2. Body - Brute Force Paragraph Collection
    # This grabs all text, preventing layout issues
    paragraphs = soup.find_all('p')
    clean_text = []
    for p in paragraphs:
        t = p.get_text().strip()
        # Filter junk: simple heuristic, sentences > 40 chars
        if len(t) > 40:
            clean_text.append(t)
            
    full_body = "\n\n".join(clean_text)
    if not full_body: full_body = "Could not extract text. Click link to read."
    
    return title, full_body

def run_smart_agent():
    print("Agent Started (AI Powered)...")
    final_email_data = []
    seen_urls = set()
    
    sender_email = os.environ["EMAIL_USER"]
    sender_pass = os.environ["EMAIL_PASS"]

    sources = [
        {"url": "https://www.prothomalo.com/opinion", "limit": 10, "type": "OPINION"},
        {"url": "https://www.prothomalo.com/opinion/editorial", "limit": 3, "type": "EDITORIAL"}
    ]

    for source in sources:
        print(f"Scanning {source['type']}...")
        soup = get_soup(source['url'])
        if not soup: continue

        # 1. Harvest ALL links on the page
        raw_links = []
        for a in soup.find_all('a', href=True):
            href = a['href']
            text = a.get_text().strip()
            
            # Basic pre-cleaning to save AI tokens (remove obvious junk)
            if len(text) > 5 and "http" not in href and "login" not in href:
                full_link = "https://www.prothomalo.com" + href if not href.startswith('http') else href
                raw_links.append({"text": text, "url": full_link})
        
        # 2. Ask Gemini to pick the winners
        # We slice raw_links[:60] to avoid sending too much data, sending top 60 links is enough to find top 10 news
        print("Asking Gemini to identify news...")
        ai_selected_urls = ask_ai_to_filter_links(raw_links[:60], source['limit'])
        
        print(f"Gemini selected {len(ai_selected_urls)} articles.")

        # 3. Process the chosen ones
        for link in ai_selected_urls:
            # AI sometimes returns just the relative path, fix it
            if not link.startswith("http"):
                link = "https://www.prothomalo.com" + link

            if link not in seen_urls:
                print(f"Reading: {link}")
                title, body = extract_content(link)
                
                final_email_data.append({
                    "type": source['type'],
                    "title": title,
                    "link": link,
                    "body": body
                })
                seen_urls.add(link)

    # --- SEND EMAIL ---
    if final_email_data:
        msg = MIMEMultipart()
        msg['From'] = sender_email
        msg['To'] = RECEIVER_EMAIL
        msg['Subject'] = f"AI Daily News ({len(final_email_data)} Articles)"

        body_str = f"Your AI Agent collected {len(final_email_data)} articles:\n"
        body_str += "="*50 + "\n\n"

        for item in final_email_data:
            body_str += f"[{item['type']}] {item['title']}\n"
            body_str += f"LINK: {item['link']}\n"
            body_str += "-"*20 + "\n"
            body_str += item['body'][:4000]
            body_str += "\n\n" + "="*50 + "\n\n"

        msg.attach(MIMEText(body_str, 'plain', 'utf-8'))

        try:
            server = smtplib.SMTP('smtp.gmail.com', 587)
            server.starttls()
            server.login(sender_email, sender_pass)
            server.sendmail(sender_email, RECEIVER_EMAIL, msg.as_string())
            server.quit()
            print(">>> SUCCESS: Email Sent.")
        except Exception as e:
            print(f">>> ERROR: {e}")
    else:
        print("AI could not find any valid news.")

if __name__ == "__main__":
    run_smart_agent()
