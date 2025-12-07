import requests
from bs4 import BeautifulSoup
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import os

# =====================================================
# UPDATE THIS EMAIL AGAIN
# =====================================================
RECEIVER_EMAIL = "iammunna32@gmail.com" 
# =====================================================

URL = "https://en.prothomalo.com/opinion/editorial"

def send_debug_email(subject, body):
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
        print(">>> SUCCESS: Email sent successfully!")
        return True
    except Exception as e:
        print(f">>> ERROR: Login or Email failed! Error: {e}")
        return False

def get_news_and_send():
    print("1. Starting Agent...")
    
    # Improved 'Fake' Browser Identity to bypass protection
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    
    try:
        response = requests.get(URL, headers=headers)
        print(f"2. Website Status Code: {response.status_code}") # Should be 200
        
        if response.status_code != 200:
            send_debug_email("Agent Error: Website Blocked", f"Could not access Prothom Alo. Status code: {response.status_code}")
            return

        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Try finding the headline with multiple common class names
        # Prothom Alo changes these sometimes
        link_tag = None
        
        # Strategy A: Look for story-element
        main_div = soup.find('div', class_='story-element')
        if main_div: link_tag = main_div.find('a')
        
        # Strategy B: Look for any big headline if A fails
        if not link_tag:
             h1_tag = soup.find('h1')
             if h1_tag: link_tag = h1_tag.find('a') if h1_tag.name != 'a' else h1_tag

        if link_tag and 'href' in link_tag.attrs:
            news_link = link_tag['href']
            if not news_link.startswith('http'):
                news_link = "https://en.prothomalo.com" + news_link
            
            headline = link_tag.get_text().strip()
            print(f"3. Found Headline: {headline}")
            
            # Fetch Article Content
            article_resp = requests.get(news_link, headers=headers)
            article_soup = BeautifulSoup(article_resp.content, 'html.parser')
            
            content_div = article_soup.find('div', class_='story-content')
            full_text = "Click link to read."
            if content_div:
                paragraphs = content_div.find_all('p')
                full_text = "\n\n".join([p.get_text().strip() for p in paragraphs])
            
            # SEND THE ACTUAL NEWS
            send_debug_email(f"Daily Editorial: {headline}", f"{headline}\n\nLink: {news_link}\n\n{full_text}")
            
        else:
            # SEND ERROR EMAIL
            print("Could not find headline HTML elements.")
            send_debug_email("Agent Warning: Layout Changed", "I went to Prothom Alo, but I couldn't find the main headline. The website layout might have changed.")

    except Exception as e:
        print(f"Crash Error: {e}")
        send_debug_email("Agent Crashed", f"The script crashed with this error: {e}")

if __name__ == "__main__":
    get_news_and_send()
