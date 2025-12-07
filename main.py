import requests
from bs4 import BeautifulSoup
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import os
import time

# =====================================================
# CONFIGURATION
# =====================================================
RECEIVER_EMAIL = "iammunna32@gmail.com"  # <--- CHANGE THIS
# =====================================================

# The two sources you want to track
SOURCES = [
    {"name": "Opinion (Mitamot)", "url": "https://www.prothomalo.com/opinion"},
    {"name": "Editorial (Sompadokiyo)", "url": "https://www.prothomalo.com/opinion/editorial"}
]

def get_soup(url):
    """Helper function to download a page and make it readable"""
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
    try:
        response = requests.get(url, headers=headers)
        response.encoding = 'utf-8' # Force Bengali text support
        if response.status_code == 200:
            return BeautifulSoup(response.content, 'html.parser')
    except Exception as e:
        print(f"Error fetching {url}: {e}")
    return None

def extract_article_text(article_link):
    """Goes to the specific article link and copies the text"""
    soup = get_soup(article_link)
    if not soup: return "Could not read article."

    # Try to find the main content area
    content_div = soup.find('div', class_='story-content')
    if not content_div:
        content_div = soup.find('div', class_='story-element')
    
    # If specific div not found, fall back to the whole body (messier but safer)
    if not content_div:
        content_div = soup
        
    paragraphs = content_div.find_all('p')
    # Filter: Keep paragraphs longer than 30 chars to avoid ads/menu items
    valid_text = [p.get_text().strip() for p in paragraphs if len(p.get_text()) > 30]
    
    return "\n\n".join(valid_text)

def run_agent():
    print("Agent Started...")
    collected_news = []
    seen_links = set() # To prevent duplicates if the same news is on both pages

    sender_email = os.environ["EMAIL_USER"]
    sender_pass = os.environ["EMAIL_PASS"]

    # --- LOOP THROUGH SOURCES ---
    for source in SOURCES:
        print(f"Checking: {source['name']}...")
        soup = get_soup(source['url'])
        
        if soup:
            # Find the first valid article link
            all_links = soup.find_all('a', href=True)
            found_link = None
            found_title = None

            for link in all_links:
                href = link['href']
                text = link.get_text().strip()
                
                # Logic: Must contain /opinion/, must be long (an article), and not be a section header
                if "/opinion/" in href and len(href) > 30 and text:
                    full_link = "https://www.prothomalo.com" + href if not href.startswith('http') else href
                    
                    # Check if we already found this link in the previous source
                    if full_link not in seen_links:
                        found_link = full_link
                        found_title = text
                        seen_links.add(full_link)
                        break # Stop after finding the top story
            
            if found_link:
                print(f"Found Article: {found_title}")
                text_content = extract_article_text(found_link)
                
                # Add to our collection
                collected_news.append({
                    "source": source['name'],
                    "title": found_title,
                    "link": found_link,
                    "body": text_content
                })
            else:
                print(f"No new link found for {source['name']}")

    # --- SEND EMAIL ---
    if collected_news:
        msg = MIMEMultipart()
        msg['From'] = sender_email
        msg['To'] = RECEIVER_EMAIL
        msg['Subject'] = f"Daily Briefing: {len(collected_news)} Articles Found"

        # Construct Email Body
        email_body = "Here is today's opinion and editorial collection:\n"
        email_body += "="*40 + "\n\n"

        for news in collected_news:
            email_body += f"SOURCE: {news['source']}\n"
            email_body += f"HEADLINE: {news['title']}\n"
            email_body += f"LINK: {news['link']}\n"
            email_body += "-"*20 + "\n"
            email_body += news['body'][:3000] # Limit text to first 3000 chars to prevent email cutoff
            email_body += "\n\n[...Read full article at link...]\n"
            email_body += "="*40 + "\n\n"

        msg.attach(MIMEText(email_body, 'plain', 'utf-8'))

        try:
            server = smtplib.SMTP('smtp.gmail.com', 587)
            server.starttls()
            server.login(sender_email, sender_pass)
            server.sendmail(sender_email, RECEIVER_EMAIL, msg.as_string())
            server.quit()
            print(">>> SUCCESS: Combined email sent!")
        except Exception as e:
            print(f">>> ERROR: Could not send email. {e}")
    else:
        print("No articles were successfully scraped from either source.")

if __name__ == "__main__":
    run_agent()
