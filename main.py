import requests
from bs4 import BeautifulSoup
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import os
import datetime

# =====================================================
# SETTINGS: CHANGE THE EMAIL BELOW
# =====================================================
RECEIVER_EMAIL = "put_the_other_person_email@gmail.com"  # <--- CHANGE THIS!
# =====================================================

URL = "https://en.prothomalo.com/opinion/editorial"

def get_news():
    print("Connecting to Prothom Alo...")
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
    
    try:
        # 1. Go to the Editorial Page
        response = requests.get(URL, headers=headers)
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # 2. Find the main story link
        # We look for the main story element on the page
        main_div = soup.find('div', class_='story-element')
        if not main_div:
            # Backup method if website layout changes
            main_div = soup.find('div', class_='story_content')
            
        if not main_div:
            print("Could not find the article list.")
            return None, None
            
        link_tag = main_div.find('a')
        if not link_tag:
            return None, None
            
        news_link = link_tag['href']
        headline = link_tag.get_text().strip()
        
        # Fix the link if it doesn't have "https"
        if not news_link.startswith('http'):
            news_link = "https://en.prothomalo.com" + news_link
            
        print(f"Found Article: {headline}")
        
        # 3. Go to the specific Article Page to copy text
        article_resp = requests.get(news_link, headers=headers)
        article_soup = BeautifulSoup(article_resp.content, 'html.parser')
        
        # 4. Extract the paragraphs
        content_div = article_soup.find('div', class_='story-content')
        if not content_div:
            content_div = article_soup.find('article')
            
        if content_div:
            paragraphs = content_div.find_all('p')
            # Join paragraphs with 2 spaces for easy reading
            full_text = "\n\n".join([p.get_text().strip() for p in paragraphs])
            return headline, full_text
        else:
            return headline, "Could not extract text. Please click the link to read."

    except Exception as e:
        print(f"Error occurred: {e}")
        return None, None

def send_email(headline, news_body):
    sender_email = os.environ["EMAIL_USER"]
    sender_pass = os.environ["EMAIL_PASS"]
    
    msg = MIMEMultipart()
    msg['From'] = sender_email
    msg['To'] = RECEIVER_EMAIL
    msg['Subject'] = f"Daily Editorial: {headline}"
    
    # Create the email content
    email_content = f"""
    TODAY'S EDITORIAL
    
    Headline: {headline}
    
    {news_body}
    
    ---------------------------
    This news was collected automatically.
    """
    
    msg.attach(MIMEText(email_content, 'plain', 'utf-8'))
    
    try:
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(sender_email, sender_pass)
        server.sendmail(sender_email, RECEIVER_EMAIL, msg.as_string())
        server.quit()
        print("Email Sent Successfully!")
    except Exception as e:
        print(f"Email Failed: {e}")

if __name__ == "__main__":
    headline, body = get_news()
    if headline and body:
        send_email(headline, body)
    else:
        print("No news found or scraped.")
