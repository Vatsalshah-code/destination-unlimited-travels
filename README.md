# 🛂 Visa & Passport Client Document Management System

A secure, enterprise-grade **Client Document Intake and Management System** designed for visa consultants, immigration attorneys, and passport processing agencies. Built with **FastAPI**, **SQLite (WAL mode)**, and a modern responsive interface.

---

## 🌟 Key Features & Workflow Architecture

### 1. Single Shareable Client Link
- **Public URL**: `http://127.0.0.1:8000/upload-documents`
- Anyone receiving this link can easily submit their application without needing to create an account first.
- Collects:
  - Full Name, Email Address, Mobile Number, Date of Birth, Residential Address
  - Service Required: *Passport Application*, *Passport Renewal*, *Visa Application*, *Visa Renewal*, *Other*
  - Country of Travel & Application / Reference Number

### 2. Designated & Validated Document Upload Center
- **Dedicated Upload Slots**:
  1. **Passport** (Front bio-data & address pages)
  2. **Aadhaar Card** (e-Aadhaar or front/back scan)
  3. **PAN Card**
  4. **Passport-Size Photograph**
  5. **Bank Documents** (3-6 months statement)
  6. **Previous Visa** (if applicable)
  7. **Supporting Documents** (*Supports multiple files*: flight itinerary, hotel booking, invitation letter, employment proof, NOC, tax returns)
- **Live Metadata & Validation**:
  - Validates allowed extensions: `.pdf`, `.jpg`, `.jpeg`, `.png`, `.webp`
  - Enforces file size limits (up to 10 MB per file)
  - Displays document category badge, original file name, formatted file size (KB/MB), upload status, and date/time.

### 3. Automatic Client Record & Unique Sequenced ID
- Generates a unique sequenced Client ID for every submission:
  ```text
  VISA-2026-0001
  VISA-2026-0002
  VISA-2026-0003 ...
  ```
- **Strict Isolation Guarantee**:
  - PERSONAL DATA → SERVICE DETAILS → UPLOADED DOCUMENTS → SUBMISSION TIMESTAMP → STATUS
  - Files are stored in a dedicated, isolated private disk folder: `data/secure_storage/{client_id}/`
  - **Zero Cross-Contamination**: Documents belonging to Client A can **never** accidentally leak or appear in Client B's record.

### 4. Privacy & Consent Compliance
- Prominent privacy policy disclosure explaining how sensitive identity documents and financial records are protected.
- Explicit consent confirmation checkbox required before submission.
- Client IP address and timestamp recorded for legal compliance.

### 5. Client Submission Confirmation & Status Tracking
- **Success Page**: Displays celebratory green checkmark, prominent **Client ID** with a 1-click copy button, full application summary, and printable/downloadable receipt.
- **Self-Service Tracker** (`/track`): Clients can track the live processing status of their application at any time using their Client ID and registered phone/email.

### 6. Private Staff Admin Dashboard
- **Access Route**: `http://127.0.0.1:8000/admin/dashboard`
- **Default Staff Credentials**:
  - **Email**: `admin@visaflow.com`
  - **Password**: `Admin@12345`
- **Metrics Overview**: Real-time counter cards for Total Submissions, New Applications, Under Staff Review, Documents Pending/Action Required, and Completed Files.
- **Search & Filters**:
  - Instant live search by Client ID, Name, Email, Mobile, Reference Number, or Country.
  - Filter by Service required.
  - Filter by Application Status (`New`, `Documents Pending`, `Under Review`, `Additional Documents Required`, `Submitted`, `Completed`).
- **Comprehensive Actions**:
  - **Open Complete Record**: Full modal drawer showing applicant info, uploaded documents, notes, and audit history.
  - **In-Browser Secure Viewer**: Inline streaming preview for PDFs and Images without exposing files to public URLs.
  - **Secure Download**: Direct download with original filenames.
  - **Download All as ZIP Archive**: Bundles all documents for the client into an organized ZIP package ready for embassy submission.
  - **Status Updater**: Update status with an optional staff note and automatic email notification to client.
  - **Internal Notes**: Private staff notes with timestamp and author.
  - **Direct Client Contact**: One-click WhatsApp link, direct phone call link, and customized email dispatch modal.
  - **Audit Trail**: Detailed log of who viewed, downloaded, or updated any client record.
  - **Export CSV**: Download complete applicant register in CSV format.
  - **Permanent Purge**: Securely delete client record and remove all private files from disk.

---

## 📁 Directory Structure

```text
visa-doc-system/
├── app/
│   ├── config.py                 # System configuration, paths, upload rules, statuses
│   ├── database.py               # SQLite schema, WAL mode, indexing, seed admin
│   ├── main.py                   # FastAPI app, static mounts, routers, error handlers
│   ├── models.py                 # Pydantic validation schemas
│   ├── security.py               # PBKDF2 password hashing, session tokens, path sanitizer
│   ├── routes/
│   │   ├── admin_routes.py       # Admin dashboard, document streaming, ZIP, status APIs
│   │   └── public_routes.py      # Public upload form, tracking, multipart intake
│   ├── services/
│   │   ├── audit_service.py      # Compliance logging
│   │   ├── client_service.py     # Sequenced ID generator, search, filter, lifecycle
│   │   ├── notification_service.py # Automated confirmation emails & admin alerts
│   │   └── storage.py            # Secure isolated disk storage & ZIP archive manager
│   ├── static/
│   │   ├── css/styles.css        # Responsive custom stylesheet
│   │   └── js/
│   │       ├── admin_dashboard.js # Admin dashboard live search, filters, modals
│   │       ├── client_form.js    # Client upload validation & multipart submission
│   │       └── tracking.js       # Client status tracker & progress stepper
│   └── templates/
│       ├── admin_dashboard.html  # Protected admin dashboard
│       ├── admin_login.html      # Staff login
│       ├── base.html             # Shared responsive layout
│       ├── client_form.html      # Public client upload form
│       ├── submission_success.html # Confirmation screen & receipt
│       └── tracking.html         # Application status lookup
├── data/
│   ├── secure_storage/           # Strictly private folder: data/secure_storage/{client_id}/
│   └── visa_system.db            # SQLite database with WAL mode
├── tests/
│   └── test_full_workflow.py     # 11 automated end-to-end integration tests
├── seed_demo_data.py             # Realistic applicant demo data generator
├── run.py                        # Uvicorn server launcher
└── README.md                     # Documentation
```

---

## 🚀 Running the System

### 1. Start the Server
```bash
python run.py
```
Or directly using Uvicorn:
```bash
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

### 2. Available Endpoints

| Purpose | URL | Access |
| :--- | :--- | :--- |
| **Public Upload Form** | [http://127.0.0.1:8000/upload-documents](http://127.0.0.1:8000/upload-documents) | Public |
| **Status Tracker** | [http://127.0.0.1:8000/track](http://127.0.0.1:8000/track) | Public |
| **Admin Dashboard** | [http://127.0.0.1:8000/admin/dashboard](http://127.0.0.1:8000/admin/dashboard) | Staff Login |
| **Staff Login** | [http://127.0.0.1:8000/admin/login](http://127.0.0.1:8000/admin/login) | Public |
| **Interactive API Docs**| [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs) | Developer |

---

## 🧪 Running Automated Tests

Run the comprehensive pytest suite covering all 11 requirements:
```bash
python -m pytest tests/test_full_workflow.py -v
```

All 11 tests pass with 100% success rate:
- Public form rendering
- Client 1 submission and isolated storage
- Client 2 submission and directory separation
- Client self-service tracking and access verification
- Unauthorized document access blocking (401)
- Admin login, table queries, search, and service filtering
- Document inline streaming & download
- Packaging all client documents into a ZIP archive
- Status updating and staff internal notes
- CSV register export
- Permanent client record deletion and file purging
