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
    # Top 10 from Opinion
    {"url": "https://www.prothomalo.com/opinion", "limit": 10, "type": "OPINION"},
    # Top 3 from Editorial
    {"url": "https://www.prothomalo.com/opinion/editorial", "limit": 3, "type": "EDITORIAL"}
]

def send_email(subject, body):
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
        print(">>> SUCCESS: Email Sent.")
    except Exception as e:
        print(f">>> ERROR: Email failed. {e}")

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

def extract_text_brute_force(url):
    """ Grabs text even if layout is weird """
    soup = get_soup(url)
    if not soup: return "Link broken or inaccessible."

    # 1. Get Headline
    h1 = soup.find('h1')
    title = h1.get_text().strip() if h1 else "Unknown Headline"

    # 2. BRUTE FORCE TEXT EXTRACTION
    # We grab ALL paragraphs in the document
    paragraphs = soup.find_all('p')
    
    clean_text = []
    for p in paragraphs:
        text = p.get_text().strip()
        # Filter: Only keep sentences (longer than 40 chars) to avoid menus/footer junk
        if len(text) > 40:
            clean_text.append(text)
            
    full_body = "\n\n".join(clean_text)
    
    if len(full_body) < 100:
        full_body = "Could not auto-copy text. Please click the link to read."
        
    return title, full_body

def run_agent():
    print("Agent Started...")
    collected_items = []
    seen_urls = set()

    for source in SOURCES:
        soup = get_soup(source['url'])
        if not soup:
            collected_items.append({"type": "ERROR", "title": f"Could not load {source['url']}", "link": source['url'], "body": ""})
            continue

        all_links = soup.find_all('a', href=True)
        count = 0
        
        for link in all_links:
            if count >= source['limit']: break
            href = link['href']
            
            # --- FILTERS ---
            # 1. Must be opinion section
            # 2. Must NOT be 'collection' (garbage) or 'auth' (login)
            if "/opinion/" in href and "collection" not in href and "auth" not in href:
                
                full_link = "https://www.prothomalo.com" + href if not href.startswith('http') else href
                
                if full_link not in seen_urls:
                    print(f"Reading: {full_link}")
                    # Go get the text
                    title, body = extract_text_brute_force(full_link)
                    
                    collected_items.append({
                        "type": source['type'],
                        "title": title,
                        "link": full_link,
                        "body": body
                    })
                    seen_urls.add(full_link)
                    count += 1

    # --- FINAL EMAIL GENERATION ---
    if collected_items:
        email_body = f"Daily News Report ({len(collected_items)} Items)\n"
        email_body += "="*50 + "\n\n"

        for item in collected_items:
            email_body += f"[{item['type']}] {item['title']}\n"
            email_body += f"LINK: {item['link']}\n"
            email_body += "-"*30 + "\n"
            email_body += item['body'][:4000] # Limit to 4000 chars per article
            email_body += "\n\n" + "="*50 + "\n\n"
        
        send_email(f"Daily News: {len(collected_items)} Articles", email_body)
    
    else:
        # If nothing found, send a failure report so you know it ran
        send_email("Agent Report: 0 Articles Found", "I scanned the website but found no valid links matching the criteria. The website layout might be completely different.")

if __name__ == "__main__":
    run_agent()
