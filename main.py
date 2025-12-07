import requests
from bs4 import BeautifulSoup
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import os

# =====================================================
# CONFIGURATION
# =====================================================
# REPLACE THIS WITH THE REAL EMAIL ADDRESS
RECEIVER_EMAIL = "iammunna32@gmail.com" 
# =====================================================

# Define sources and how many articles to grab from each
SOURCES = [
    {
        "name": "Mitamot (Opinion) - Top 10", 
        "url": "https://www.prothomalo.com/opinion", 
        "limit": 10
    },
    {
        "name": "Sompadokiyo (Editorial) - Top 3", 
        "url": "https://www.prothomalo.com/opinion/editorial", 
        "limit": 3
    }
]

def get_soup(url):
    """Downloads the page pretending to be a browser"""
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    try:
        response = requests.get(url, headers=headers)
        response.encoding = 'utf-8' # Force Bengali encoding
        if response.status_code == 200:
            return BeautifulSoup(response.content, 'html.parser')
    except Exception as e:
        print(f"Error fetching {url}: {e}")
    return None

def extract_article_details(article_link):
    """Goes to the article link and extracts Headline + Body"""
    soup = get_soup(article_link)
    if not soup: return "Error", "Could not read article."

    # 1. Try to find the Headline (H1)
    headline_tag = soup.find('h1')
    headline = headline_tag.get_text().strip() if headline_tag else "No Headline Found"

    # 2. Try to find the Body Text
    content_div = soup.find('div', class_='story-content')
    if not content_div: content_div = soup.find('article')
    
    full_text = "Read full story at the link."
    if content_div:
        paragraphs = content_div.find_all('p')
        # Join paragraphs that are actual sentences
        valid_text = [p.get_text().strip() for p in paragraphs if len(p.get_text()) > 10]
        if valid_text:
            full_text = "\n\n".join(valid_text)

    return headline, full_text

def run_agent():
    print("Agent Started...")
    collected_news = []
    
    # We use a set to ensure we don't pick the same article twice
    seen_urls = set()

    sender_email = os.environ["EMAIL_USER"]
    sender_pass = os.environ["EMAIL_PASS"]

    for source in SOURCES:
        print(f"Scanning: {source['name']}...")
        soup = get_soup(source['url'])
        
        if soup:
            # Get all links
            links = soup.find_all('a', href=True)
            count = 0
            
            for link in links:
                # Stop if we reached the limit (10 or 3)
                if count >= source['limit']:
                    break

                href = link['href']
                
                # --- FILTERING LOGIC ---
                # 1. Ignore Login/Social Media links
                if any(x in href for x in ['auth', 'api', 'facebook', 'twitter', 'login']):
                    continue

                # 2. Ensure it is a substantial link (likely an article)
                # Prothom Alo article links are usually long
                if len(href) > 30: 
                    full_link = "https://www.prothomalo.com" + href if not href.startswith('http') else href
                    
                    if full_link not in seen_urls:
                        # Go to the article to get the Real Title and Text
                        print(f"-> Fetching: {full_link}")
                        real_title, real_body = extract_article_details(full_link)
                        
                        # Only add if we actually found a title (filters out menu links)
                        if real_title and real_title != "No Headline Found":
                            collected_news.append({
                                "source": source['name'],
                                "title": real_title,
                                "link": full_link,
                                "body": real_body
                            })
                            seen_urls.add(full_link)
                            count += 1
                            print(f"   Saved ({count}/{source['limit']})")

    # --- SEND EMAIL ---
    if collected_news:
        msg = MIMEMultipart()
        msg['From'] = sender_email
        msg['To'] = RECEIVER_EMAIL
        msg['Subject'] = f"Daily News Feed ({len(collected_news)} Articles)"

        email_body = f"Here is your daily collection of {len(collected_news)} articles:\n"
        email_body += "="*40 + "\n\n"

        for i, news in enumerate(collected_news, 1):
            email_body += f"#{i} [{news['source']}]\n"
            email_body += f"HEADLINE: {news['title']}\n"
            email_body += f"LINK: {news['link']}\n"
            email_body += "-"*10 + "\n"
            # Show first 1000 characters only to keep email readable
            email_body += news['body'][:1000] 
            email_body += "...\n\n[Click Link to Read Full]\n"
            email_body += "="*40 + "\n\n"

        msg.attach(MIMEText(email_body, 'plain', 'utf-8'))

        try:
            server = smtplib.SMTP('smtp.gmail.com', 587)
            server.starttls()
            server.login(sender_email, sender_pass)
            server.sendmail(sender_email, RECEIVER_EMAIL, msg.as_string())
            server.quit()
            print(">>> SUCCESS: Email sent successfully!")
        except Exception as e:
            print(f">>> ERROR: Could not send email. {e}")
    else:
        print("Scanned pages but found NO valid articles. Layout might have changed drastically.")

if __name__ == "__main__":
    run_agent()
