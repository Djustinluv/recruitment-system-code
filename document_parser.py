"""
Document Parser Module - OCR and NLP for Resume and Certification Parsing
Uses SpaCy for NER, PyTesseract for OCR, pdfplumber for PDF extraction
"""

import spacy
import pytesseract
from PIL import Image
import pdfplumber
from docx import Document as DocxDocument
import re
from typing import Dict, List, Any

# Load SpaCy model
nlp = spacy.load("en_core_web_sm")

# ============ PDF EXTRACTION ============
def extract_text_from_pdf(file_path: str) -> str:
    """Extract text from PDF files"""
    try:
        with pdfplumber.open(file_path) as pdf:
            text = '\n'.join(
                page.extract_text() for page in pdf.pages 
                if page.extract_text()
            )
        return text
    except Exception as e:
        print(f"Error extracting PDF: {e}")
        return ""

# ============ DOCX EXTRACTION ============
def extract_text_from_docx(file_path: str) -> str:
    """Extract text from DOCX files"""
    try:
        doc = DocxDocument(file_path)
        text = '\n'.join(para.text for para in doc.paragraphs)
        return text
    except Exception as e:
        print(f"Error extracting DOCX: {e}")
        return ""

# ============ OCR FOR IMAGES ============
def ocr_image_to_text(image_path: str) -> str:
    """Extract text from images using OCR"""
    try:
        image = Image.open(image_path)
        text = pytesseract.image_to_string(image)
        return text
    except Exception as e:
        print(f"Error OCR image: {e}")
        return ""

# ============ EXTRACT TEXT BY FILE TYPE ============
def extract_text(file_path: str) -> str:
    """Extract text from any file type"""
    ext = file_path.split('.')[-1].lower()
    
    if ext == 'pdf':
        return extract_text_from_pdf(file_path)
    elif ext == 'docx':
        return extract_text_from_docx(file_path)
    elif ext in ['jpg', 'jpeg', 'png']:
        return ocr_image_to_text(file_path)
    else:
        return ""

# ============ RESUME PARSING ============
def parse_resume(text: str, job_skills: List[str] = None) -> Dict[str, Any]:
    """
    Parse resume/CV text and extract structured data
    """
    doc = nlp(text)
    
    extracted = {
        'name': None,
        'email': None,
        'phone': None,
        'nationality': None,
        'years_experience': 0,
        'skills': [],
        'certifications': []
    }
    
    # ============ NER EXTRACTION ============
    for ent in doc.ents:
        # Extract person name
        if ent.label_ == 'PERSON' and not extracted['name']:
            extracted['name'] = ent.text
        
        # Extract nationality
        elif ent.label_ == 'GPE' and not extracted['nationality']:
            extracted['nationality'] = ent.text
        
        # Extract years of experience from DATE entities
        elif ent.label_ == 'DATE' and 'years' in ent.text.lower():
            match = re.search(r'(\d+)\s+years?', ent.text, re.IGNORECASE)
            if match:
                extracted['years_experience'] = int(match.group(1))
    
    # ============ REGEX EXTRACTION ============
    # Email
    email_match = re.search(r'[\w\.-]+@[\w\.-]+\.\w+', text)
    if email_match:
        extracted['email'] = email_match.group(0)
    
    # Phone
    phone_match = re.search(r'(\+\d{1,3}[- ]?)?\d{3}[- ]?\d{4}[- ]?\d{4}', text)
    if phone_match:
        extracted['phone'] = phone_match.group(0)
    
    # ============ SKILLS EXTRACTION ============
    if job_skills:
        for skill in job_skills:
            if skill.lower() in text.lower():
                extracted['skills'].append(skill)
    else:
        # Extract from Skills section
        skills_section = re.search(
            r'Skills:(.*?)(?=Certifications:|Experience:|$)',
            text,
            re.DOTALL | re.IGNORECASE
        )
        if skills_section:
            skills_text = skills_section.group(1)
            extracted['skills'] = [
                skill.strip() for skill in skills_text.split(',')
                if skill.strip()
            ]
    
    # ============ CERTIFICATIONS EXTRACTION ============
    # Pattern: Name: Issued DD/MM/YYYY, Expires DD/MM/YYYY
    cert_pattern = r'-\s*(.*?):\s*(?:Issued\s+)?(\d{1,2}/\d{1,2}/\d{4}),\s*(?:Expires?\s+)?(\d{1,2}/\d{1,2}/\d{4})'
    cert_matches = re.findall(cert_pattern, text, re.IGNORECASE)
    
    for name, issue_date, expiry_date in cert_matches:
        extracted['certifications'].append({
            'name': name.strip(),
            'issue_date': issue_date,
            'expiry_date': expiry_date
        })
    
    return extracted

# ============ CERTIFICATION PARSING (SCANNED) ============
def parse_certification(text: str) -> Dict[str, Any]:
    """
    Parse scanned certification/document and extract certificate details
    """
    doc = nlp(text)
    
    extracted = {
        'cert_name': None,
        'issue_date': None,
        'expiry_date': None
    }
    
    # ============ NER FOR DATES ============
    dates = [ent.text for ent in doc.ents if ent.label_ == 'DATE']
    if len(dates) >= 2:
        extracted['issue_date'] = dates[0]
        extracted['expiry_date'] = dates[1]
    elif len(dates) == 1:
        extracted['expiry_date'] = dates[0]
    
    # ============ REGEX FOR DATES (FALLBACK) ============
    date_matches = re.findall(r'\d{1,2}/\d{1,2}/\d{4}', text)
    if len(date_matches) >= 2:
        extracted['issue_date'] = date_matches[0]
        extracted['expiry_date'] = date_matches[1]
    elif len(date_matches) == 1 and not extracted['expiry_date']:
        extracted['expiry_date'] = date_matches[0]
    
    # ============ CERTIFICATION NAME EXTRACTION ============
    cert_match = re.search(r'Certificate:\s*(.*?)(?:\n|$)', text, re.IGNORECASE)
    if cert_match:
        extracted['cert_name'] = cert_match.group(1).strip()
    
    # ============ CUSTOM OFFSHORE CERT PATTERNS ============
    offshore_certs = {
        'BOSIET': r'\bBOSIET\b',
        'HUET': r'\bHUET\b',
        'ASNT': r'\bASNT\b',
        'OFFSHORE MEDICAL': r'(?:OFFSHORE|MEDIC)[A-Z\s]*',
        'STCW': r'\bSTCW\b',
        'SOLAS': r'\bSOLAS\b'
    }
    
    for cert_name, pattern in offshore_certs.items():
        if re.search(pattern, text, re.IGNORECASE):
            extracted['cert_name'] = cert_name
            break
    
    return extracted

# ============ MAIN DOCUMENT PARSER ============
def parse_document(file_path: str) -> Dict[str, Any]:
    """
    Main function to parse any document type
    Determines if it's a resume/CV or certification and parses accordingly
    """
    ext = file_path.split('.')[-1].lower()
    text = extract_text(file_path)
    
    if not text:
        return {
            'status': 'error',
            'message': 'Could not extract text from document',
            'fields': {}
        }
    
    # ============ DETERMINE DOCUMENT TYPE ============
    # Check if it's a certification or resume
    is_certification = (
        'certificate' in text.lower() or
        'issued' in text.lower() or
        'expires' in text.lower()
    )
    
    if is_certification:
        fields = parse_certification(text)
    else:
        fields = parse_resume(text)
    
    return {
        'status': 'success',
        'text': text[:500],  # First 500 chars for preview
        'fields': fields
    }

# ============ BATCH PARSING ============
def parse_documents_batch(file_paths: List[str]) -> List[Dict[str, Any]]:
    """Parse multiple documents in batch"""
    results = []
    for file_path in file_paths:
        result = parse_document(file_path)
        results.append(result)
    return results

# ============ SKILL MATCHING ============
def match_skills_to_requirements(extracted_skills: List[str], required_skills: List[str]) -> Dict[str, Any]:
    """
    Match applicant skills to job requirements
    Returns matching skills and proficiency score
    """
    matched = []
    missing = []
    
    for skill in required_skills:
        if skill.lower() in [s.lower() for s in extracted_skills]:
            matched.append(skill)
        else:
            missing.append(skill)
    
    score = len(matched) / len(required_skills) * 100 if required_skills else 0
    
    return {
        'matched_skills': matched,
        'missing_skills': missing,
        'match_percentage': score
    }
