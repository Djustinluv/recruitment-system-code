"""
Database Models for Ocean Professional Recruitment System
"""
from sqlalchemy import Column, String, Integer, Float, DateTime, Enum, JSON, ForeignKey, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from datetime import datetime
import enum
import uuid

Base = declarative_base()

class Job(Base):
    __tablename__ = "jobs"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    title = Column(String(255), nullable=False)
    description = Column(Text)
    required_certifications = Column(JSON, nullable=False)  # List of cert requirements
    required_skills = Column(JSON)  # List of required skills
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    applicants = relationship("Applicant", back_populates="job")

class StatusEnum(str, enum.Enum):
    QUALIFIED = "qualified"
    NEEDS_REVIEW = "needs_review"
    REJECTED = "rejected"

class Applicant(Base):
    __tablename__ = "applicants"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String(255))
    email = Column(String(255), unique=True)
    phone = Column(String(50))
    nationality = Column(String(100))
    years_experience = Column(Integer, default=0)
    skills = Column(JSON)  # List of skills
    job_id = Column(String, ForeignKey("jobs.id"))
    screening_score = Column(Float, default=0.0)
    status = Column(String, default=StatusEnum.NEEDS_REVIEW)
    extracted_data = Column(JSON)  # AI-parsed fields
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    job = relationship("Job", back_populates="applicants")
    documents = relationship("Document", back_populates="applicant", cascade="all, delete-orphan")
    certifications = relationship("Certification", back_populates="applicant", cascade="all, delete-orphan")

class Document(Base):
    __tablename__ = "documents"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    applicant_id = Column(String, ForeignKey("applicants.id", ondelete="CASCADE"))
    file_name = Column(String(255))
    file_type = Column(String(50))  # pdf, docx, jpg, png
    s3_key = Column(String(255), nullable=False)
    extracted_text = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    applicant = relationship("Applicant", back_populates="documents")

class Certification(Base):
    __tablename__ = "certifications"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    applicant_id = Column(String, ForeignKey("applicants.id", ondelete="CASCADE"))
    name = Column(String(255))
    issue_date = Column(String)  # DD/MM/YYYY
    expiry_date = Column(String)  # DD/MM/YYYY
    status = Column(String, default="missing")  # valid, expired, missing
    document_id = Column(String, ForeignKey("documents.id"))
    
    applicant = relationship("Applicant", back_populates="certifications")

class User(Base):
    __tablename__ = "users"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    username = Column(String(255), unique=True)
    password_hash = Column(String(255))
    role = Column(String, default="hr")  # admin, hr

class AuditLog(Base):
    __tablename__ = "audit_logs"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String)
    action = Column(String(255))
    details = Column(JSON)
    timestamp = Column(DateTime, default=datetime.utcnow)
