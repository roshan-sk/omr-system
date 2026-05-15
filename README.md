# OMR Analyzer

An automated **Optical Mark Recognition (OMR)** system that scans and evaluates answer sheets using computer vision. Upload a scanned OMR sheet, define your answer key, and get instant results — built with a Flask backend and an Angular frontend.

---

## Output Video (Screen Recording)

[Watch] https://drive.google.com/file/d/1ndV8RtW0VKe0rEy36soJnlGWDVMWnPlh/view?usp=sharing

[PDF Support Output Recoding] https://drive.google.com/file/d/1B1A60PcKLP7RLSbgZMXNQ8zPL_WKMOSZ/view?usp=sharing

## Project Structure

| Folder | Description |
|---|---|
| `omr-backend/` | Flask REST API + OpenCV OMR processing engine |
| `omr-frontend/` | Angular 21 SPA with upload, results, answer key, and user management |

---

## Tech Stack

| Layer | Technology |
|---|---|
| Backend | Python, Flask, OpenCV, NumPy |
| Frontend | Angular 21, TypeScript, Node.js |
| Image Processing | OpenCV (`cv2`) |

---

## Getting Started

### Prerequisites

Make sure you have the following installed before proceeding:

- **Python** 3.9+
- **Node.js** 18+ and **npm**
- **Git**

---

### 1. Clone the Repository

```bash
git clone https://github.com/roshan-sk/omr-analyzer.git
cd omr-analyzer
```

---

### 2. Backend Setup (`omr-backend/`)

```bash
cd omr-backend
```

#### Create and activate a virtual environment (recommended)

```bash
# Windows
python -m venv venv
venv\Scripts\activate

# macOS / Linux
python -m venv venv
source venv/bin/activate
```

#### Install Python dependencies

```bash
pip install -r requirements.txt
```

If `requirements.txt` is not present, install core packages manually:

```bash
pip install flask flask-sqlalchemy flask-jwt-extended flask-cors pymysql opencv-python numpy Pillow openpyxl werkzeug python-dotenv
```

#### Configure environment variables

Copy the example env file and fill in your values:

```bash
cp .env.example .env
```

Then open `.env` and set the required fields:

```dotenv
# Required — set a strong random string for each
SECRET_KEY=your_secret_key_here
APP_SECRET_KEY=your_app_secret_key_here
JWT_SECRET_KEY=your_jwt_secret_key_here

# Database connection string
# SQLite example:    sqlite:///omr.db
# PostgreSQL example: postgresql://user:password@localhost:5432/omrdb
DATABASE_URL=sqlite:///omr.db

# Folder where uploaded OMR images are saved (relative to backend root)
UPLOAD_FOLDER=uploads

# JWT configuration — safe to leave as-is for local development
JWT_TOKEN_LOCATION=headers,cookies
JWT_COOKIE_CSRF_PROTECT=False
JWT_ACCESS_TOKEN_EXPIRES=3600
JWT_COOKIE_SECURE=False
JWT_COOKIE_SAMESITE=Lax
JWT_ACCESS_COOKIE_NAME=access_token_cookie
JWT_ALGORITHM=HS256
```

> **Tip:** Generate secure keys with: `python -c "import secrets; print(secrets.token_hex(32))"`

#### Initialize the database & create admin user

After configuring your `.env`, run the seed script once to create the default admin account:

```bash
python seed_admin.py
```

This will create the following admin user if one doesn't already exist:

| Field | Value |
|---|---|
| Email | `admin@gmail.com` |
| Password | `Admin@1234` |
| Role | `ADMIN` |

> **Important:** Change the admin password after your first login.

#### Run the Flask server

```bash
python app.py
```

The backend will start at `http://localhost:5000`

---

### 3. Frontend Setup (`omr-frontend/`)

Open a **new terminal** and navigate to the frontend folder:

```bash
cd omr-frontend
```

#### Install Node dependencies

```bash
npm install
```

#### Install Angular CLI globally (if not already installed)

```bash
npm install -g @angular/cli
```

#### Run the Angular development server

```bash
ng serve
```

The frontend will be available at `http://localhost:4200`

---

## Usage
1. Open http://localhost:4200 in your browser.
2. Log in using your credentials to continue.
3. Upload a scanned OMR answer sheet image.
4. Define or select an answer key.
5. Submit to view automated evaluation results.

---

> **Note:** Although the OMR sheet includes **level bubble** (e.g. Junior, Intermediate, Senior), the system currently evaluates all sheets using the **Intermediate (default)** answer key only. Level-specific evaluation will be supported in a future update.