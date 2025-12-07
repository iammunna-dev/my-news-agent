import requests
from bs4 import BeautifulSoup
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import os

# =====================================================
# CONFIGURATION
# =====================================================
RECEIVER_EMAIL = "iammunna32@gmail.com" 
# =====================================================

SOURCES = [
    {"name": "Opinion Page", "url": "https://www.prothomalo.com/opinion"},
    {"name": "Editorial Page", "url": "https://www.prothomalo.com/opinion/editorial"}
]

def send_email(subject, body):
    """Sends an email using GitHub Secrets"""
    try:
        sender_email = os.environ["EMAIL_USER"]
        sender_pass = os.environ["EMAIL_PASS"]
        
        msg = MIMEMultipart()
        msg['From'] = sender_email
        msg['To'] = RECEIVER_EMAIL
        msg['Subject'] = subject
        msg.attach(MIMEText(body, 'plain', 'utf-8'))
        
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(sender_email, sender_pass)
        server.sendmail(sender_email, RECEIVER_EMAIL, msg.as_string())
        server.quit()
        print(f">>> EMAIL SENT: {subject}")
    except Exception as e:
        print(f">>> EMAIL FAILED: {e}")

def get_soup(url):
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    try:
        response = requests.get(url, headers=headers)
        response.encoding = 'utf-8'
        if response.status_code == 200:
            return BeautifulSoup(response.content, 'html.parser')
    except Exception as e:
        print(f"Error fetching {url}: {e}")
    return None

def extract_text(url):
    soup = get_soup(url)
    if not soup: return "Read at link."
    
    # Try generic article finding
    content_div = soup.find('div', class_='story-content')
    if not content_div: content_div = soup.find('article')
    
    if content_div:
        paragraphs = content_div.find_all('p')
        text = "\n\n".join([p.get_text().strip() for p in paragraphs if len(p.get_text()) > 20])
        return text if len(text) > 50 else "Content too short. Please click link."
    return "Could not extract text."

def run_agent():
    print("Agent Started...")
    collected_news = []
    seen_links = set()

    for source in SOURCES:
        print(f"Scanning {source['name']}...")
        soup = get_soup(source['url'])
        
        if soup:
            # Get all links
            links = soup.find_all('a', href=True)
            
            for link in links:
                href = link['href']
                text = link.get_text().strip()
                
                # LOGIC:
                # 1. Must be in /opinion/ section
                # 2. No 'auth' or 'api' (Login pages)
                # 3. Text must exist and be longer than 5 chars
                if "/opinion/" in href and "auth" not in href and "api" not in href and len(text) > 5:
                    
                    full_link = "https://www.prothomalo.com" + href if not href.startswith('http') else href
                    
                    if full_link not in seen_links:
                        print(f"-> Found: {text}")
                        body_text = extract_text(full_link)
                        
                        collected_news.append({
                            "source": source['name'],
                            "title": text,
                            "link": full_link,
                            "body": body_text
                        })
                        seen_links.add(full_link)
                        break # Stop after finding the top story for this section

    # --- DECISION TIME ---
    if collected_news:
        # We found news!
        email_body = "TODAY'S BRIEFING:\n" + "="*30 + "\n\n"
        for item in collected_news:
            email_body += f"SOURCE: {item['source']}\n"
            email_body += f"TITLE: {item['title']}\n"
            email_body += f"LINK: {item['link']}\n"
            email_body += "-"*15 + "\n"
            email_body += item['body'][:3000]
            email_body += "\n\n" + "="*30 + "\n\n"
            
        send_email(f"Daily News ({len(collected_news)} Articles)", email_body)
        
    else:
        # We found NOTHING. Send an alert email.
        debug_msg = "The Agent ran but found 0 articles matching the criteria.\n"
        debug_msg += "Please check the website layout or the GitHub Action logs."
        send_email("Agent Report: No News Found", debug_msg)

if __name__ == "__main__":
    run_agent()
