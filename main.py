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
    # Get 10 articles from Opinion
    {"url": "https://www.prothomalo.com/opinion", "limit": 10, "type": "OPINION"},
    # Get 3 articles from Editorial
    {"url": "https://www.prothomalo.com/opinion/editorial", "limit": 3, "type": "EDITORIAL"}
]

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

def get_article_content(url):
    """ Digs into the article and forces text extraction """
    soup = get_soup(url)
    if not soup: return None, None
    
    # 1. Get Headline
    h1 = soup.find('h1')
    title = h1.get_text().strip() if h1 else "No Title"
    
    # 2. Get Text (Aggressive Search)
    # Strategy: Find the div with the most paragraph text
    article_body = soup.find('div', class_='story-content')
    if not article_body:
        article_body = soup.find('div', class_='story-element')
    
    # Fallback: Just grab all P tags on the page if specific div is missing
    if not article_body:
        article_body = soup

    paragraphs = article_body.find_all('p')
    
    # Filter: Drop short lines (menus, ads, captions)
    clean_paragraphs = []
    for p in paragraphs:
        text = p.get_text().strip()
        if len(text) > 30: # Only keep sentences longer than 30 chars
            clean_paragraphs.append(text)
            
    full_text = "\n\n".join(clean_paragraphs)
    
    return title, full_text

def run_agent():
    print("Agent Started...")
    final_news_list = []
    seen_urls = set()

    sender_email = os.environ["EMAIL_USER"]
    sender_pass = os.environ["EMAIL_PASS"]

    for source in SOURCES:
        print(f"Scanning {source['type']}...")
        soup = get_soup(source['url'])
        if not soup: continue

        # Find all links
        all_links = soup.find_all('a', href=True)
        count = 0
        
        for link in all_links:
            if count >= source['limit']: break
            
            href = link['href']
            
            # --- STRICT FILTERS ---
            # 1. Must NOT be the "Collection/Latest" page (The garbage filter)
            if "collection" in href or "topic" in href: continue
            
            # 2. Must likely be an article (contain opinion section)
            if "/opinion/" not in href: continue
            
            full_link = "https://www.prothomalo.com" + href if not href.startswith('http') else href
            
            if full_link not in seen_urls:
                # Go get the content
                title, body = get_article_content(full_link)
                
                # 3. CONTENT CHECK: If body is empty or too short, it's not news. Skip it.
                if body and len(body) > 200: 
                    final_news_list.append({
                        "type": source['type'],
                        "title": title,
                        "link": full_link,
                        "body": body
                    })
                    seen_urls.add(full_link)
                    count += 1
                    print(f"   -> Collected: {title[:20]}...")

    # --- SEND EMAIL ---
    if final_news_list:
        msg = MIMEMultipart()
        msg['From'] = sender_email
        msg['To'] = RECEIVER_EMAIL
        msg['Subject'] = f"Daily News ({len(final_news_list)} Articles)"

        # Build clean email structure
        email_body = f"Here are your {len(final_news_list)} articles for today:\n"
        email_body += "="*50 + "\n\n"

        for i, item in enumerate(final_news_list, 1):
            email_body += f"ARTICLE #{i} [{item['type']}]\n"
            email_body += f"HEADLINE: {item['title']}\n"
            email_body += f"LINK: {item['link']}\n"
            email_body += "-"*30 + "\n"
            email_body += item['body'][:5000] # First 5000 chars
            email_body += "\n\n" + "="*50 + "\n\n"

        msg.attach(MIMEText(email_body, 'plain', 'utf-8'))

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
        print("Scanned sources but strict filters rejected everything.")

if __name__ == "__main__":
    run_agent()
