import requests
from bs4 import BeautifulSoup
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import os

# =====================================================
# CONFIGURATION
# =====================================================
RECEIVER_EMAIL = "iammunna32@gmail.com"  # <--- CHANGE THIS
# =====================================================

SOURCES = [
    {"name": "Mitamot (Opinion)", "url": "https://www.prothomalo.com/opinion"},
    {"name": "Sompadokiyo (Editorial)", "url": "https://www.prothomalo.com/opinion/editorial"}
]

def get_soup(url):
    # We pretend to be a real browser so they don't block us
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'Accept-Language': 'en-US,en;q=0.9,bn;q=0.8'
    }
    try:
        response = requests.get(url, headers=headers)
        response.encoding = 'utf-8'
        if response.status_code == 200:
            return BeautifulSoup(response.content, 'html.parser')
    except Exception as e:
        print(f"Error fetching {url}: {e}")
    return None

def extract_article_text(article_link):
    soup = get_soup(article_link)
    if not soup: return "Could not read article."

    # Strategy: Find the biggest chunk of text
    # 1. Try standard story content div
    content_div = soup.find('div', class_='story-content')
    
    # 2. Try generic article tag
    if not content_div:
        content_div = soup.find('article')
        
    # 3. If generic, grab all paragraphs
    if content_div:
        paragraphs = content_div.find_all('p')
        # Only keep paragraphs that look like sentences (more than 20 chars)
        valid_text = [p.get_text().strip() for p in paragraphs if len(p.get_text()) > 20]
        full_text = "\n\n".join(valid_text)
        return full_text if full_text else "Content is hidden or requires login."
    
    return "Could not extract text structure."

def run_agent():
    print("Agent Started...")
    collected_news = []
    seen_links = set() 

    sender_email = os.environ["EMAIL_USER"]
    sender_pass = os.environ["EMAIL_PASS"]

    for source in SOURCES:
        print(f"Checking source: {source['name']}...")
        soup = get_soup(source['url'])
        
        if soup:
            all_links = soup.find_all('a', href=True)
            found_link = None
            found_title = None

            for link in all_links:
                href = link['href']
                text = link.get_text().strip()
                
                # --- THE FIX IS HERE ---
                # 1. Must contain /opinion/
                # 2. Must NOT contain 'auth', 'api', 'login' (The Login Filter)
                # 3. Text must be long enough to be a headline
                if "/opinion/" in href and "auth" not in href and "api" not in href and len(text) > 5:
                    
                    full_link = "https://www.prothomalo.com" + href if not href.startswith('http') else href
                    
                    # Double check we haven't seen this
                    if full_link not in seen_links:
                        found_link = full_link
                        found_title = text
                        seen_links.add(full_link)
                        break # Stop at the first valid news link
            
            if found_link:
                print(f"Found: {found_title}")
                text_content = extract_article_text(found_link)
                
                collected_news.append({
                    "source": source['name'],
                    "title": found_title,
                    "link": found_link,
                    "body": text_content
                })

    # Send Email if news found
    if collected_news:
        msg = MIMEMultipart()
        msg['From'] = sender_email
        msg['To'] = RECEIVER_EMAIL
        msg['Subject'] = f"Daily Briefing: {len(collected_news)} Articles"

        email_body = "Today's Prothom Alo Collection:\n"
        email_body += "="*30 + "\n\n"

        for news in collected_news:
            email_body += f"SECTION: {news['source']}\n"
            email_body += f"HEADLINE: {news['title']}\n"
            email_body += f"LINK: {news['link']}\n"
            email_body += "-"*10 + "\n"
            email_body += news['body'][:4000] # Cap length to avoid errors
            email_body += "\n\n[...Read full article at link...]\n"
            email_body += "="*30 + "\n\n"

        msg.attach(MIMEText(email_body, 'plain', 'utf-8'))

        try:
            server = smtplib.SMTP('smtp.gmail.com', 587)
            server.starttls()
            server.login(sender_email, sender_pass)
            server.sendmail(sender_email, RECEIVER_EMAIL, msg.as_string())
            server.quit()
            print(">>> SUCCESS: Email sent!")
        except Exception as e:
            print(f">>> ERROR: {e}")
    else:
        print("No valid articles found (Login filter blocked bad links).")

if __name__ == "__main__":
    run_agent()
