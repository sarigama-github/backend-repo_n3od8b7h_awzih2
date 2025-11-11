import os
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, EmailStr, Field
from typing import Optional
from datetime import datetime, timezone
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
def read_root():
    return {"message": "Meysson Engineering API"}


@app.get("/api/hello")
def hello():
    return {"message": "Hello from the backend API!"}


@app.get("/test")
def test_database():
    """Test endpoint to check if database is available and accessible"""
    response = {
        "backend": "✅ Running",
        "database": "❌ Not Available",
        "database_url": None,
        "database_name": None,
        "connection_status": "Not Connected",
        "collections": []
    }

    try:
        # Try to import database module
        from database import db

        if db is not None:
            response["database"] = "✅ Available"
            response["database_url"] = "✅ Configured"
            response["database_name"] = db.name if hasattr(db, 'name') else "✅ Connected"
            response["connection_status"] = "Connected"

            # Try to list collections to verify connectivity
            try:
                collections = db.list_collection_names()
                response["collections"] = collections[:10]  # Show first 10 collections
                response["database"] = "✅ Connected & Working"
            except Exception as e:
                response["database"] = f"⚠️  Connected but Error: {str(e)[:50]}"
        else:
            response["database"] = "⚠️  Available but not initialized"

    except ImportError:
        response["database"] = "❌ Database module not found (run enable-database first)"
    except Exception as e:
        response["database"] = f"❌ Error: {str(e)[:50]}"

    # Check environment variables
    import os
    response["database_url"] = "✅ Set" if os.getenv("DATABASE_URL") else "❌ Not Set"
    response["database_name"] = "✅ Set" if os.getenv("DATABASE_NAME") else "❌ Not Set"

    return response


# ====== Contact Endpoint ======
class ContactPayload(BaseModel):
    full_name: str = Field(..., min_length=2, max_length=120)
    company: Optional[str] = Field(None, max_length=160)
    email: EmailStr
    phone: Optional[str] = Field(None, max_length=50)
    subject: str = Field(..., min_length=3, max_length=160)
    message: str = Field(..., min_length=10, max_length=5000)
    source: Optional[str] = None


@app.post("/api/contact")
def create_contact(payload: ContactPayload):
    # 1) Persist to database
    try:
        from database import create_document
        from schemas import Contact
        contact_doc = Contact(**payload.model_dump())
        doc_id = create_document("contact", contact_doc)
    except Exception as e:
        # We still continue to email, but report DB issue in response
        doc_id = None
        db_error = str(e)
    else:
        db_error = None

    # 2) Send email notification via SMTP if configured
    smtp_host = os.getenv("SMTP_HOST")
    smtp_port = int(os.getenv("SMTP_PORT", "587"))
    smtp_user = os.getenv("SMTP_USER")
    smtp_pass = os.getenv("SMTP_PASS")
    smtp_to = os.getenv("SMTP_TO") or smtp_user

    email_status = "skipped"
    if smtp_host and smtp_user and smtp_pass and smtp_to:
        try:
            msg = MIMEMultipart()
            msg["From"] = smtp_user
            msg["To"] = smtp_to
            msg["Subject"] = f"[Meysson Engineering] Nouveau contact: {payload.subject}"

            html = f"""
            <h2>Nouveau message de contact</h2>
            <p><strong>Nom:</strong> {payload.full_name}</p>
            <p><strong>Entreprise:</strong> {payload.company or '-'} </p>
            <p><strong>Email:</strong> {payload.email}</p>
            <p><strong>Téléphone:</strong> {payload.phone or '-'} </p>
            <p><strong>Objet:</strong> {payload.subject}</p>
            <p><strong>Message:</strong><br/>{payload.message.replace('\n','<br/>')}</p>
            <hr/>
            <p>Source: {payload.source or 'site web'}</p>
            <p>Horodatage: {datetime.now(timezone.utc).isoformat()}</p>
            <p>ID en base: {doc_id or '- (non enregistré)'} </p>
            """
            msg.attach(MIMEText(html, "html"))

            with smtplib.SMTP(smtp_host, smtp_port, timeout=20) as server:
                server.starttls()
                server.login(smtp_user, smtp_pass)
                server.sendmail(smtp_user, [smtp_to], msg.as_string())
            email_status = "sent"
        except Exception as e:
            email_status = f"error: {str(e)[:120]}"

    return {
        "ok": True,
        "stored_id": doc_id,
        "email_status": email_status,
        "db_error": db_error
    }


# ====== Schemas endpoint (for internal viewers) ======
@app.get("/schema")
def get_schema_definitions():
    try:
        import inspect
        import schemas as schemas_module
        from pydantic import BaseModel as _BM
        result = {}
        for name, obj in vars(schemas_module).items():
            if inspect.isclass(obj) and issubclass(obj, _BM) and obj.__module__ == schemas_module.__name__:
                result[name] = obj.model_json_schema()
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
