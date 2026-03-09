"""
Verification Engine - Certification verification and applicant screening
"""
from datetime import datetime
from typing import Dict, List, Any, Tuple
import json

# ============ CERTIFICATION VERIFICATION ============
def verify_certifications(
    applicant_certs: List[Dict],
    job_requirements: List[Dict],
    applicant_experience: int = 0
) -> Tuple[Dict, float]:
    """
    Verify applicant certifications against job requirements
    Returns verification result and compliance score
    
    Args:
        applicant_certs: [{'name': 'BOSIET', 'issue_date': '01/01/2020', 'expiry_date': '01/01/2025'}]
        job_requirements: [{'name': 'BOSIET', 'level': 'Any', 'expiry_check': True}]
        applicant_experience: years of experience
    
    Returns:
        Tuple of (verification_details, compliance_score)
    """
    verification = {
        'total_required': len(job_requirements),
        'total_valid': 0,
        'total_expired': 0,
        'total_missing': 0,
        'certs': []
    }
    
    today = datetime.now()
    
    # Check each required certification
    for req in job_requirements:
        cert_name = req.get('name')
        
        # Find matching applicant cert
        matching_cert = next(
            (c for c in applicant_certs if c.get('name', '').lower() == cert_name.lower()),
            None
        )
        
        if not matching_cert:
            # Certificate missing
            verification['total_missing'] += 1
            verification['certs'].append({
                'name': cert_name,
                'status': 'missing',
                'issue_date': None,
                'expiry_date': None,
                'is_valid': False
            })
        else:
            # Check expiry
            try:
                expiry_date = datetime.strptime(matching_cert['expiry_date'], '%d/%m/%Y')
                is_valid = expiry_date > today
            except:
                is_valid = False
            
            if is_valid:
                verification['total_valid'] += 1
            else:
                verification['total_expired'] += 1
            
            verification['certs'].append({
                'name': cert_name,
                'status': 'valid' if is_valid else 'expired',
                'issue_date': matching_cert.get('issue_date'),
                'expiry_date': matching_cert.get('expiry_date'),
                'is_valid': is_valid
            })
    
    # Calculate compliance score (percentage of valid certs)
    compliance_score = (verification['total_valid'] / verification['total_required'] * 100) if verification['total_required'] > 0 else 0
    
    return verification, compliance_score

# ============ SCREENING ALGORITHM ============
def calculate_screening_score(
    applicant_data: Dict[str, Any],
    job_requirements: Dict[str, Any],
    certification_score: float
) -> Tuple[float, str]:
    """
    Calculate overall screening score using weighted criteria
    
    Scoring breakdown:
    - Experience: 30%
    - Certifications: 40%
    - Skills: 20%
    - Document Validity: 10%
    
    Returns:
        Tuple of (total_score, recommendation)
    """
    scores = {
        'experience_score': 0,
        'certification_score': 0,
        'skill_score': 0,
        'document_score': 0
    }
    
    # ============ EXPERIENCE SCORE (30%) ============
    applicant_exp = applicant_data.get('years_experience', 0)
    required_exp = job_requirements.get('required_experience', 5)
    
    if applicant_exp >= required_exp:
        scores['experience_score'] = 30  # Full score
    else:
        scores['experience_score'] = (applicant_exp / required_exp) * 30
    
    # ============ CERTIFICATION SCORE (40%) ============
    scores['certification_score'] = (certification_score / 100) * 40
    
    # ============ SKILL SCORE (20%) ============
    applicant_skills = applicant_data.get('skills', [])
    required_skills = job_requirements.get('required_skills', [])
    
    if required_skills:
        matched_skills = sum(
            1 for skill in required_skills
            if skill.lower() in [s.lower() for s in applicant_skills]
        )
        scores['skill_score'] = (matched_skills / len(required_skills)) * 20
    else:
        scores['skill_score'] = 20  # No skills required
    
    # ============ DOCUMENT VALIDITY SCORE (10%) ============
    # Check if critical documents are present
    documents = applicant_data.get('documents', [])
    required_doc_types = job_requirements.get('required_documents', ['resume', 'certificate'])
    
    valid_docs = sum(1 for doc in documents if doc.get('file_type') in required_doc_types)
    if required_doc_types:
        scores['document_score'] = (valid_docs / len(required_doc_types)) * 10
    else:
        scores['document_score'] = 10
    
    # ============ TOTAL SCORE ============
    total_score = (
        scores['experience_score'] +
        scores['certification_score'] +
        scores['skill_score'] +
        scores['document_score']
    )
    
    # ============ RECOMMENDATION ============
    if total_score >= 75:
        recommendation = 'qualified'
    elif total_score >= 60:
        recommendation = 'needs_review'
    else:
        recommendation = 'rejected'
    
    return total_score, recommendation

# ============ GENERATE VERIFICATION REPORT ============
def generate_verification_report(
    applicant_id: str,
    applicant_data: Dict[str, Any],
    job_requirements: Dict[str, Any],
    certification_verification: Dict
) -> Dict[str, Any]:
    """
    Generate comprehensive verification and screening report
    """
    cert_score = (
        certification_verification['total_valid'] / certification_verification['total_required'] * 100
        if certification_verification['total_required'] > 0
        else 0
    )
    
    screening_score, recommendation = calculate_screening_score(
        applicant_data,
        job_requirements,
        cert_score
    )
    
    report = {
        'applicant_id': applicant_id,
        'timestamp': datetime.utcnow().isoformat(),
        'screening': {
            'total_score': round(screening_score, 2),
            'recommendation': recommendation,
            'score_breakdown': {
                'experience': applicant_data.get('years_experience', 0),
                'certifications_valid': certification_verification['total_valid'],
                'certifications_expired': certification_verification['total_expired'],
                'certifications_missing': certification_verification['total_missing'],
                'skills_matched': len([s for s in applicant_data.get('skills', [])]),
                'documents_valid': len(applicant_data.get('documents', []))
            }
        },
        'certification_details': certification_verification,
        'flags': []
    }
    
    # ============ RED FLAGS ============
    if certification_verification['total_expired'] > 0:
        report['flags'].append({
            'type': 'expired_certifications',
            'severity': 'high',
            'message': f"{certification_verification['total_expired']} certificate(s) expired"
        })
    
    if certification_verification['total_missing'] > 0:
        report['flags'].append({
            'type': 'missing_certifications',
            'severity': 'medium',
            'message': f"{certification_verification['total_missing']} certificate(s) missing"
        })
    
    if applicant_data.get('years_experience', 0) < job_requirements.get('required_experience', 5):
        report['flags'].append({
            'type': 'insufficient_experience',
            'severity': 'medium',
            'message': f"Experience below requirement ({applicant_data.get('years_experience', 0)} vs {job_requirements.get('required_experience', 5)} required)"
        })
    
    return report

# ============ BATCH SCREENING ============
def screen_applicants_batch(
    applicants: List[Dict],
    job_requirements: Dict
) -> List[Dict]:
    """
    Screen multiple applicants for a job position
    """
    results = []
    
    for applicant in applicants:
        # Verify certs
        cert_verification, cert_score = verify_certifications(
            applicant.get('certifications', []),
            job_requirements.get('required_certifications', []),
            applicant.get('years_experience', 0)
        )
        
        # Generate report
        report = generate_verification_report(
            applicant.get('id'),
            applicant,
            job_requirements,
            cert_verification
        )
        
        results.append(report)
    
    # Sort by score (highest first)
    results.sort(key=lambda x: x['screening']['total_score'], reverse=True)
    
    return results

# ============ DUPLICATE DETECTION ============
def detect_duplicate_applicant(
    email: str,
    existing_applicants: List[Dict],
    similarity_threshold: float = 0.8
) -> bool:
    """
    Check if applicant already exists in system
    Uses email as primary key
    """
    for applicant in existing_applicants:
        if applicant.get('email', '').lower() == email.lower():
            return True
    return False
