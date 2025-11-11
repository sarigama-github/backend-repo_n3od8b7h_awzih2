from pydantic import BaseModel, Field, EmailStr
from typing import Optional, List

# Core content schemas for Meysson Engineering

class Contact(BaseModel):
    full_name: str = Field(..., min_length=2, max_length=120, description="Nom complet")
    company: Optional[str] = Field(None, max_length=160, description="Entreprise")
    email: EmailStr
    phone: Optional[str] = Field(None, max_length=50)
    subject: str = Field(..., min_length=3, max_length=160)
    message: str = Field(..., min_length=10, max_length=5000)
    source: Optional[str] = Field(None, description="Origine de la demande")

class Testimonial(BaseModel):
    client_name: str = Field(..., max_length=120)
    company: Optional[str] = Field(None, max_length=160)
    content: str = Field(..., min_length=10, max_length=1500)
    rating: Optional[int] = Field(None, ge=1, le=5)

class Project(BaseModel):
    title: str = Field(..., max_length=160)
    sector: str = Field(..., max_length=120)
    description: str = Field(..., min_length=10, max_length=4000)
    cover_image: Optional[str] = Field(None, description="URL de l'image")
    client: Optional[str] = None
    location: Optional[str] = None
    year: Optional[int] = Field(None, ge=1990, le=2100)

class Article(BaseModel):
    title: str
    slug: str
    excerpt: Optional[str] = None
    content: str
    cover_image: Optional[str] = None
    tags: Optional[List[str]] = None

# Note on collection names:
# Each class maps to a collection with lowercase name: Contact -> "contact", Project -> "project", etc.
