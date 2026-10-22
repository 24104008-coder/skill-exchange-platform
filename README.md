# Student Skill Sharing Platform 🎓⚡

A collaborative, peer-to-peer web application built as a college laboratory project. This platform empowers college students to showcase their technical and creative skills, connect with fellow classmates for 1-on-1 peer mentoring, exchange learning requests, and leave verified ratings and reviews.

---

## 🌟 Key Features

1. **Authentication & Session Management**
   - Secure student registration with full name, college email, department, study year, and bio.
   - Password hashing using Werkzeug.
   - Session-based authentication using native Flask sessions (No JWT, No external auth services).

2. **Student Profile Management**
   - View student profile cards with bio, department, study year, and member stats.
   - Edit personal details and customize profile image avatars.
   - Track statistics: total skills offered, total sessions completed, and active requests.

3. **Skills Marketplace & Exploration**
   - Create, view, update, and delete skill listings with difficulty levels (`Beginner`, `Intermediate`, `Advanced`).
   - Categorized under: *Programming*, *Web Development*, *Mobile Development*, *Database*, *Data Science*, *AI*, *Design*, *Communication*, *Marketing*, etc.
   - Real-time case-insensitive keyword search and multi-parameter filtering.

4. **Peer Skill Requests & Collaboration Workflow**
   - Send personalized learning requests with introductory notes.
   - Skill owners can **Accept** or **Decline** requests.
   - Participants can mark ongoing sessions as **Completed**.
   - Built-in validation prevents duplicate requests and self-requests.

5. **Ratings & Review System**
   - Students who complete a learning session can submit a **1 to 5 star rating** and feedback comment.
   - Average ratings and dynamic star displays are updated on each skill details page.
   - Prevention of duplicate reviews for the same completed session.

6. **Interactive Student Dashboard**
   - Welcome banner with department & year.
   - Stat metric widgets (Skills Offered, Requests Sent, Pending Requests, Completed Sessions, Materials Shared).
   - "My Skills Offered" management interface with quick Edit/Delete actions.
   - "My Shared Course Materials" tracker and campus skill recommendations.

7. **Course Learning Materials & Media Hub (PDFs, Videos & Interactive Previews)**
   - Students and mentors can share PDFs, lecture slides, video tutorials, lab manuals, and study guides inside each course/skill.
   - **Interactive In-Browser Media Modal**: Preview PDFs with built-in viewer and watch videos (HTML5 or YouTube embeds) directly on the page without leaving.
   - **Direct Downloads & View Tracking**: Secure download handler with view and download metrics tracking.
   - **Helpful Reaction System**: Peer students can upvote helpful learning materials with instant count updates.
   - **Type & Keyword Filtering**: Filter course materials by *PDFs & Notes*, *Videos*, *Lab Tasks*, and *Links & Code*, with instant real-time search.
   - **Role Attribution**: Clear badges identifying whether material was contributed by the *Course Mentor* or a *Student Peer*.

---

## 🛠️ Technology Stack

- **Backend Framework**: Python 3.11+ / Flask
- **Database**: MongoDB (via `pymongo` / MongoDB Atlas or Local MongoDB)
- **Templating Engine**: Jinja2 (server-side rendering)
- **Frontend**: Pure HTML5 & Modern Custom Vanilla CSS (No Bootstrap, No Tailwind, No React, No Node.js)
- **Security**: Werkzeug Security (`generate_password_hash`, `check_password_hash`)
- **Configuration**: `python-dotenv`

---

## 📂 Project Structure

```
skill-exchange-platform/
│
├── app.py                      # Main Flask application with all route handlers
├── config.py                   # Centralized configuration & environment variables
├── requirements.txt            # Python dependencies
├── .env                        # Active environment configuration
├── .env.example                # Example environment configuration
├── README.md                   # Project documentation
│
├── models/                     # MongoDB Data Access Layer
│   ├── __init__.py
│   ├── user_model.py           # User management, auth, profile updates
│   ├── skill_model.py          # Skill CRUD, search & filtering
│   ├── request_model.py        # Learning request workflow & status transitions
│   └── review_model.py         # Star ratings & peer reviews
│
├── templates/                  # Jinja2 HTML Templates
│   ├── base.html               # Global layout, sticky navbar, flash messages, footer
│   ├── index.html              # Homepage with hero, features, and how it works
│   ├── login.html              # Student login page
│   ├── register.html           # Student registration page
│   ├── dashboard.html          # Student dashboard & metrics
│   ├── profile.html            # Profile viewing & editing
│   ├── skills.html             # Skills exploration with search & filters
│   ├── add_skill.html          # Create new skill offering
│   ├── edit_skill.html         # Edit existing skill offering
│   ├── skill_details.html      # Skill details, teacher card, ratings & request box
│   ├── requests.html           # Sent & Received request management + Review modal
│   ├── reviews.html            # Public testimonials gallery
│   ├── 404.html                # Friendly 404 error page
│   └── 500.html                # Friendly 500 error page
│
├── static/
│   ├── css/
│   │   └── style.css           # Modern custom CSS design system
│   └── images/
│
└── utils/
    ├── __init__.py
    └── helpers.py              # Login decorator, date formatters, Mongo indexes & seeder
```

---

## ⚙️ System Requirements

- **Python**: Version 3.10, 3.11, or 3.12+
- **MongoDB**: MongoDB 5.0+ (Local Community Edition or MongoDB Atlas cloud cluster)
- **Operating System**: Windows / macOS / Linux

---

## 🚀 Installation & Setup Guide

### 1. Clone or Open the Project
Open your terminal (PowerShell, Command Prompt, or bash) in the project directory:
```bash
cd "d:\skill exchange platform"
```

### 2. Create and Activate a Virtual Environment

**On Windows (PowerShell / Command Prompt):**
```powershell
python -m venv venv
venv\Scripts\activate
```

**On macOS / Linux:**
```bash
python3 -m venv venv
source venv/bin/activate
```

### 3. Install Required Dependencies
```bash
pip install -r requirements.txt
```

### 4. Configure Environment Variables (`.env`)
The `.env` file is pre-configured with MongoDB Atlas connection string. You can modify it if using local MongoDB:
```ini
MONGO_URI=mongodb+srv://24104008_db_user:Bala123@cluster0.mifx6pq.mongodb.net/
DATABASE_NAME=student_skill_sharing
SECRET_KEY=student_skill_sharing_secret_key_2026_super_secure
FLASK_ENV=development
FLASK_DEBUG=1
```

*(For local MongoDB instance: `MONGO_URI=mongodb://localhost:27017/`)*

---

## 🏃 Running the Application

Start the Flask server:
```bash
python app.py
```

Open your browser and navigate to:
👉 **[http://127.0.0.1:5000](http://127.0.0.1:5000/)**

---

## 🧪 Optional: Populating Sample Demo Data

To quickly populate sample college student accounts, skills, and sample completed reviews for testing:

**Option A: Via CLI Command**
```bash
python app.py seed
```

**Option B: Via Browser URL**
While the server is running, visit:
👉 **`http://127.0.0.1:5000/seed-data`**

### Sample Demo Accounts:
| Name | Email | Password | Department |
| :--- | :--- | :--- | :--- |
| **Alex Chen** | `alex.chen@college.edu` | `password123` | Computer Science & Engineering |
| **Sarah Miller** | `sarah.m@college.edu` | `password123` | Design & Media |
| **Rohan Patel** | `rohan.p@college.edu` | `password123` | Data Science & AI |
| **Emily Watson** | `emily.w@college.edu` | `password123` | Business Administration |

---

## 🗄️ Database Architecture

The application connects to a MongoDB database named `student_skill_sharing` with 4 collections:

1. **`users`**
   - `_id`: `ObjectId` (Primary Key)
   - `name`: `String`
   - `email`: `String` (Indexed, Unique)
   - `password_hash`: `String` (Werkzeug PBKDF2 / SHA256)
   - `department`: `String`
   - `year`: `String`
   - `bio`: `String`
   - `profile_image`: `String`
   - `skills_offered`: `Integer`
   - `skills_learned`: `Integer`
   - `created_at`: `DateTime`

2. **`skills`**
   - `_id`: `ObjectId`
   - `title`: `String` (Text Indexed)
   - `description`: `String` (Text Indexed)
   - `category`: `String` (Indexed)
   - `level`: `String` (Indexed)
   - `owner_id`: `ObjectId` (Indexed)
   - `owner_name`: `String`
   - `created_at`: `DateTime`

3. **`requests`**
   - `_id`: `ObjectId`
   - `skill_id`: `ObjectId` (Indexed)
   - `skill_title`: `String`
   - `sender_id`: `ObjectId` (Indexed)
   - `sender_name`: `String`
   - `receiver_id`: `ObjectId` (Indexed)
   - `receiver_name`: `String`
   - `message`: `String`
   - `status`: `String` (`Pending` | `Accepted` | `Rejected` | `Completed`)
   - `reviewed`: `Boolean`
   - `created_at`: `DateTime`
   - `completed_at`: `DateTime`

4. **`reviews`**
   - `_id`: `ObjectId`
   - `skill_id`: `ObjectId` (Indexed)
   - `request_id`: `ObjectId` (Indexed, Unique)
   - `reviewer_id`: `ObjectId`
   - `reviewer_name`: `String`
   - `rating`: `Integer` (1 to 5)
   - `comment`: `String`
   - `created_at`: `DateTime`

---

## 🧭 Application Workflow

```
[ Visitor / Student ]
       │
       ├──► Register / Login ──► Flask Session Created
       │
       ├──► Explore Skills (Search by Keyword, Category, Level)
       │         │
       │         └──► View Skill Details ──► Send Learning Request
       │
       ├──► Dashboard
       │         ├──► Offer New Skill (Add / Edit / Delete)
       │         └──► View Learning Metrics
       │
       └──► Requests Center
                 ├──► Received: Accept or Decline Request
                 ├──► Accepted: Mark Session Completed
                 └──► Completed: Submit 1-5 Star Rating & Review
```

---

## 🔒 Security & Access Control

- **Password Safety**: Passwords are never stored in plain text and are salted & hashed using Werkzeug security.
- **Access Control Decorator**: Protected routes use the custom `@login_required` decorator to prevent unauthorized access.
- **Resource Authorization**: Students can only edit/delete their own skills, accept/reject requests sent to them, and review sessions they participated in.
- **Input Sanitization & Safe ObjectIds**: Safe conversion and regex escaping protect against NoSQL injection and malformed input crashes.

---

## 🎓 College Lab Evaluation Summary

- Single unified Flask application with Jinja2 templating.
- Pure custom CSS without external frameworks (No Bootstrap / Tailwind).
- Native session handling without complex JWT client overhead.
- Direct PyMongo driver integration with MongoDB Atlas cloud database.
