"""
Email Parser Module - IMAP email polling and application extraction
Polls for job applications, extracts attachments, and parses documents
"""

import imaplib
import email
from email.header import decode_header
import os
from typing import List, Dict, Tuple
import json
from datetime import datetime

# ============ EMAIL CONNECTION ============
def connect_to_imap(
    imap_server: str,
    email_user: str,
    email_password: str
) -> imaplib.IMAP4_SSL:
    """
    Connect to IMAP email server
    
    Args:
        imap_server: e.g., 'imap.gmail.com'
        email_user: email address
        email_password: email password or app password
    
    Returns:
        IMAP connection object
    """
    try:
        mail = imaplib.IMAP4_SSL(imap_server)
        mail.login(email_user, email_password)
        print(f"Connected to {imap_server}")
        return mail
    except Exception as e:
        print(f"Failed to connect to email: {e}")
        return None

# ============ EXTRACT ATTACHMENTS ============
def extract_attachments(
    email_message: email.message.Message,
    attachment_dir: str = "/tmp"
) -> List[Dict[str, str]]:
    """
    Extract attachments from email message
    
    Returns:
        List of {'filename': '', 'path': '', 'mime_type': ''}
    """
    attachments = []
    
    for part in email_message.walk():
        if part.get_content_maintype() == 'multipart':
            continue
        
        if part.get('Content-Disposition') is None:
            continue
        
        filename = part.get_filename()
        if filename:
            # Decode filename if needed
            try:
                filename = decode_header(filename)[0][0]
                if isinstance(filename, bytes):
                    filename = filename.decode('utf-8', errors='ignore')
            except:
                pass
            
            # Check if file is allowed type
            allowed_types = ('.pdf', '.docx', '.jpg', '.jpeg', '.png')
            if filename.lower().endswith(allowed_types):
                try:
                    # Save to temporary directory
                    file_path = os.path.join(attachment_dir, filename)
                    file_data = part.get_payload(decode=True)
                    
                    with open(file_path, 'wb') as f:
                        f.write(file_data)
                    
                    attachments.append({
                        'filename': filename,
                        'path': file_path,
                        'mime_type': part.get_content_type(),
                        'size': len(file_data)
                    })
                except Exception as e:
                    print(f"Error saving attachment {filename}: {e}")
    
    return attachments

# ============ PARSE EMAIL ============
def parse_email_message(
    email_message: email.message.Message
) -> Dict[str, any]:
    """
    Parse email message and extract sender, subject, body
    """
    try:
        # Get sender email
        sender_email = email.utils.parseaddr(email_message['From'])[1]
        
        # Get subject
        subject = email_message['Subject']
        if isinstance(subject, email.header.Header):
            subject = str(subject.encode('utf-8'))
        
        # Get body
        body = ""
        if email_message.is_multipart():
            for part in email_message.walk():
                if part.get_content_type() == "text/plain":
                    body = part.get_payload(decode=True).decode('utf-8', errors='ignore')
                    break
        else:
            body = email_message.get_payload(decode=True).decode('utf-8', errors='ignore')
        
        return {
            'from': sender_email,
            'subject': subject,
            'body': body[:500],  # First 500 chars
            'timestamp': email_message['Date']
        }
    except Exception as e:
        print(f"Error parsing email: {e}")
        return {}

# ============ POLL EMAILS ============
def poll_emails(
    imap_server: str,
    email_user: str,
    email_password: str,
    search_criteria: str = '(UNSEEN)',
    subject_filter: str = 'Job Application'
) -> List[Dict]:
    """
    Poll IMAP mailbox for emails and extract applications
    
    Args:
        search_criteria: IMAP search criteria (e.g., '(UNSEEN)', '(SINCE 2024-03-01)')
        subject_filter: Filter emails by subject line
    
    Returns:
        List of application data with attachments
    """
    mail = connect_to_imap(imap_server, email_user, email_password)
    if not mail:
        return []
    
    applications = []
    
    try:
        # Select inbox
        mail.select('INBOX')
        
        # Search for emails
        status, messages = mail.search(None, search_criteria)
        
        message_ids = messages[0].split()
        print(f"Found {len(message_ids)} emails")
        
        for message_id in message_ids:
            try:
                # Fetch email
                status, msg_data = mail.fetch(message_id, '(RFC822)')
                email_message = email.message_from_bytes(msg_data[0][1])
                
                # Parse email
                parsed = parse_email_message(email_message)
                
                # Filter by subject if needed
                if subject_filter and subject_filter.lower() not in parsed.get('subject', '').lower():
                    continue
                
                # Extract attachments
                attachments = extract_attachments(email_message)
                
                if attachments:
                    applications.append({
                        'email': parsed.get('from'),
                        'subject': parsed.get('subject'),
                        'body': parsed.get('body'),
                        'timestamp': parsed.get('timestamp'),
                        'attachments': attachments
                    })
                    
                    # Mark as read
                    mail.store(message_id, '+FLAGS', '\\Seen')
            
            except Exception as e:
                print(f"Error processing message {message_id}: {e}")
                continue
    
    except Exception as e:
        print(f"Error polling emails: {e}")
    
    finally:
        mail.close()
        mail.logout()
    
    return applications

# ============ BATCH PROCESS EMAILS ============
def process_email_applications(
    applications: List[Dict],
    document_parser
) -> List[Dict]:
    """
    Process list of email applications
    Parse documents and extract applicant data
    
    Args:
        applications: List from poll_emails()
        document_parser: Function to parse documents
    
    Returns:
        List of processed applications with extracted data
    """
    processed = []
    
    for app in applications:
        applicant_data = {
            'email': app['email'],
            'source': 'email',
            'received_at': app['timestamp'],
            'documents': [],
            'extracted_data': {}
        }
        
        # Process each attachment
        for attachment in app.get('attachments', []):
            try:
                # Parse document
                parse_result = document_parser(attachment['path'])
                
                applicant_data['documents'].append({
                    'filename': attachment['filename'],
                    'type': attachment['mime_type'],
                    'extracted_text': parse_result.get('text', '')[:200]
                })
                
                # Extract fields
                fields = parse_result.get('fields', {})
                applicant_data['extracted_data'].update(fields)
                
                # Clean up temp file
                try:
                    os.remove(attachment['path'])
                except:
                    pass
            
            except Exception as e:
                print(f"Error processing attachment {attachment['filename']}: {e}")
                continue
        
        if applicant_data['documents']:
            processed.append(applicant_data)
    
    return processed

# ============ SETUP EMAIL POLLING TASK (Celery) ============
"""
To integrate with Celery for automated polling:

from celery import shared_task
from .email_parser import poll_emails, process_email_applications
from .document_parser import parse_document
from .models import Applicant, Document

@shared_task
def poll_and_process_emails():
    '''
    Celery task to poll emails and process applications
    Schedule this with celery beat every 5 minutes
    '''
    applications = poll_emails(
        imap_server=os.getenv('IMAP_SERVER'),
        email_user=os.getenv('EMAIL_USER'),
        email_password=os.getenv('EMAIL_PASSWORD'),
        search_criteria='(UNSEEN)',
        subject_filter='Job Application'
    )
    
    processed = process_email_applications(applications, parse_document)
    
    # Save to database
    for app in processed:
        try:
            applicant = Applicant(
                email=app['email'],
                name=app['extracted_data'].get('name', 'Unknown'),
                phone=app['extracted_data'].get('phone'),
                nationality=app['extracted_data'].get('nationality'),
                years_experience=app['extracted_data'].get('years_experience', 0),
                skills=app['extracted_data'].get('skills', []),
                extracted_data=app['extracted_data']
            )
            session.add(applicant)
            session.commit()
            
            # Save documents
            for doc in app['documents']:
                document = Document(
                    applicant_id=applicant.id,
                    file_name=doc['filename'],
                    file_type=doc['type'],
                    s3_key='',  # Would be S3 path
                    extracted_text=doc['extracted_text']
                )
                session.add(document)
            session.commit()
        
        except Exception as e:
            print(f"Error saving applicant {app['email']}: {e}")
            continue
    
    return f"Processed {len(processed)} email applications"
"""
