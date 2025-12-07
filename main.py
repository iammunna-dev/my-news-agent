import requests
from bs4 import BeautifulSoup
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import os

# =====================================================
# ENTER THE RECEIVER EMAIL HERE
# =====================================================
RECEIVER_EMAIL = "iammunna32@gmail.com" 
# =====================================================

URL = "https://en.prothomalo.com/opinion/editorial"

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
        print(">>> SUCCESS: Email sent.")
    except Exception as e:
        print(f">>> ERROR: Email failed! {e}")

def get_news_and_send():
    print("Scanning Prothom Alo...")
    headers = {'User-Agent': 'Mozilla/5.0'}
    
    try:
        response = requests.get(URL, headers=headers)
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # --- NEW FINDING METHOD ---
        # Instead of looking for a class, we look for any link 
        # that looks like an editorial article.
        found_link = None
        found_title = None
        
        # Find all links on the page
        all_links = soup.find_all('a', href=True)
        
        for link in all_links:
            href = link['href']
            text = link.get_text().strip()
            
            # Logic: If the link contains "/opinion/editorial/" AND is long (meaning it's an article, not a menu button)
            # AND it has a headline text.
            if "/opinion/editorial/" in href and len(href) > 40 and text:
                found_link = href
                found_title = text
                break # We found the first (latest) one, stop looking.
        
        if found_link:
            # Fix link if it's missing https
            if not found_link.startswith('http'):
                found_link = "https://en.prothomalo.com" + found_link
                
            print(f"Found: {found_title}")
            
            # Go to the article
            article_resp = requests.get(found_link, headers=headers)
            article_soup = BeautifulSoup(article_resp.content, 'html.parser')
            
            # Get paragraphs
            paragraphs = article_soup.find_all('p')
            full_text = "\n\n".join([p.get_text().strip() for p in paragraphs])
            
            if len(full_text) < 50:
                full_text = "Could not scrape text automatically. Please check the link."

            # Send the email
            send_email(f"Daily News: {found_title}", f"{found_title}\n\nLink: {found_link}\n\n{full_text}")
            
        else:
            send_email("Agent Error", "I scanned the page but couldn't identify a specific article link. The website structure is very unusual today.")

    except Exception as e:
        send_email("Agent Crashed", f"Error: {e}")

if __name__ == "__main__":
    get_news_and_send()
