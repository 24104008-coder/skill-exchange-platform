import os
import sys
from datetime import datetime, timezone
from pymongo import MongoClient
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from config import Config
from utils.helpers import format_file_size, get_youtube_embed_info

def create_sample_pdf(filepath, title, subtitle, author, sections):
    """
    Generate an elegant, professional PDF document using ReportLab.
    """
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    doc = SimpleDocTemplate(
        filepath,
        pagesize=letter,
        rightMargin=40,
        leftMargin=40,
        topMargin=40,
        bottomMargin=40
    )

    styles = getSampleStyleSheet()

    # Custom styles
    title_style = ParagraphStyle(
        'DocTitle',
        parent=styles['Heading1'],
        fontName='Helvetica-Bold',
        fontSize=22,
        leading=26,
        textColor=colors.HexColor('#1e1b4b'),
        spaceAfter=6
    )

    subtitle_style = ParagraphStyle(
        'DocSubtitle',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=12,
        leading=16,
        textColor=colors.HexColor('#6366f1'),
        spaceAfter=12
    )

    meta_style = ParagraphStyle(
        'DocMeta',
        parent=styles['Normal'],
        fontName='Helvetica-Oblique',
        fontSize=9,
        leading=12,
        textColor=colors.HexColor('#64748b'),
        spaceAfter=15
    )

    section_heading = ParagraphStyle(
        'SectionHeading',
        parent=styles['Heading2'],
        fontName='Helvetica-Bold',
        fontSize=13,
        leading=17,
        textColor=colors.HexColor('#312e81'),
        spaceBefore=12,
        spaceAfter=6
    )

    body_style = ParagraphStyle(
        'DocBody',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=10,
        leading=14,
        textColor=colors.HexColor('#1f2937'),
        spaceAfter=8
    )

    bullet_style = ParagraphStyle(
        'DocBullet',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=9.5,
        leading=14,
        textColor=colors.HexColor('#374151'),
        leftIndent=15,
        spaceAfter=4
    )

    elements = []

    # Title & Header
    elements.append(Paragraph(title, title_style))
    elements.append(Paragraph(subtitle, subtitle_style))
    elements.append(Paragraph(f"Shared on SkillExchange Hub &bull; Author: {author} &bull; Date: {datetime.now().strftime('%B %Y')}", meta_style))
    elements.append(HRFlowable(width="100%", thickness=1.5, color=colors.HexColor('#6366f1'), spaceAfter=15))

    for sec_title, sec_points in sections:
        elements.append(Paragraph(sec_title, section_heading))
        for point in sec_points:
            elements.append(Paragraph(f"&bull; {point}", bullet_style))
        elements.append(Spacer(1, 8))

    elements.append(Spacer(1, 15))
    elements.append(HRFlowable(width="100%", thickness=0.8, color=colors.HexColor('#e2e8f0'), spaceAfter=10))
    footer_text = "SkillExchange Student Learning Platform &bull; Peer Mentoring & Course Resources"
    elements.append(Paragraph(footer_text, ParagraphStyle('Footer', fontName='Helvetica', fontSize=8, textColor=colors.HexColor('#94a3b8'), alignment=1)))

    doc.build(elements)
    return filepath


def run_seed():
    client = MongoClient(Config.MONGO_URI, serverSelectionTimeoutMS=5000)
    db = client[Config.DATABASE_NAME]

    # Ensure upload directory exists
    base_upload_dir = Config.UPLOAD_FOLDER
    os.makedirs(base_upload_dir, exist_ok=True)

    # Make sure skills have owner_id and owner_name synced
    skills = list(db.skills.find())
    print(f"Found {len(skills)} skills in database.")

    for s in skills:
        owner_id = s.get('owner_id')
        owner_name = s.get('owner_name')
        mentor = s.get('mentor')
        if not owner_id and isinstance(mentor, dict) and mentor.get('user_id'):
            owner_id = mentor.get('user_id')
            owner_name = mentor.get('name')
            db.skills.update_one({'_id': s['_id']}, {'$set': {'owner_id': owner_id, 'owner_name': owner_name}})

    # Fetch users for attribution
    users = list(db.users.find())
    alex = next((u for u in users if 'alex' in u.get('email', '').lower()), users[0] if users else None)
    sarah = next((u for u in users if 'sarah' in u.get('email', '').lower()), users[1] if len(users) > 1 else users[0])
    rohan = next((u for u in users if 'rohan' in u.get('email', '').lower()), users[2] if len(users) > 2 else users[0])
    emily = next((u for u in users if 'emily' in u.get('email', '').lower()), users[3] if len(users) > 3 else users[0])

    # Remove existing materials to reseed cleanly
    db.materials.delete_many({})
    print("Cleared existing course materials.")

    seeded_count = 0

    for s in skills:
        title = s.get('title', '')
        s_id = s['_id']
        s_dir = os.path.join(base_upload_dir, str(s_id))
        os.makedirs(s_dir, exist_ok=True)

        materials_to_add = []

        if 'python' in title.lower():
            # 1. Real PDF Cheat Sheet
            pdf_filename = "Python_OOP_Fundamentals_Cheatsheet.pdf"
            pdf_path = os.path.join(s_dir, pdf_filename)
            create_sample_pdf(
                pdf_path,
                title="Python OOP & Data Structures Lab Guide",
                subtitle="Core Principles, Class Architecture, Magic Methods & Exercises",
                author=s.get('owner_name', 'Alex Chen'),
                sections=[
                    ("1. Core Object-Oriented Principles", [
                        "Encapsulation: Bundle data (attributes) and behavior (methods) together.",
                        "Inheritance: Derive specialized classes from parent base classes.",
                        "Polymorphism: Treat derived classes uniformly via duck typing or overrides.",
                        "Abstraction: Hide internal implementation using clean public interfaces."
                    ]),
                    ("2. Essential Dunder Methods (__init__, __str__, __repr__)", [
                        "__init__(self, ...): Constructor initializing instance attributes.",
                        "__repr__(self): Unambiguous representation primarily for developers and debugging.",
                        "__str__(self): Readable, user-friendly representation for printing.",
                        "__eq__(self, other): Custom equality comparison based on attributes."
                    ]),
                    ("3. Best Practices for College Lab Exercises", [
                        "Always use type hints for clarity: def calculate_grade(scores: list[float]) -> str:",
                        "Prefer composition over deep inheritance hierarchies where feasible.",
                        "Use docstrings (PEP 257) on all public functions and classes."
                    ])
                ]
            )
            file_size_formatted = format_file_size(os.path.getsize(pdf_path))
            materials_to_add.append({
                "skill_id": s_id,
                "uploader_id": alex['_id'] if alex else s.get('owner_id'),
                "uploader_name": alex['name'] if alex else s.get('owner_name', 'Alex Chen'),
                "uploader_role": "Course Mentor",
                "title": "Python OOP Fundamentals & Lab Cheat Sheet",
                "description": "Comprehensive reference document covering class definitions, inheritance patterns, dunder methods, and clean coding best practices.",
                "material_type": "pdf",
                "file_path": f"{s_id}/{pdf_filename}",
                "file_name": pdf_filename,
                "file_size": file_size_formatted,
                "file_ext": "pdf",
                "external_url": None,
                "embed_url": None,
                "tag": "Cheat Sheet",
                "likes": [str(sarah['_id']) if sarah else "1", str(rohan['_id']) if rohan else "2"],
                "downloads_count": 14,
                "views_count": 42,
                "created_at": datetime.now(timezone.utc)
            })

            # 2. Video Lecture
            yt_url = "https://www.youtube.com/watch?v=ZDa-Z5JzLYM"
            embed_url, _ = get_youtube_embed_info(yt_url)
            materials_to_add.append({
                "skill_id": s_id,
                "uploader_id": alex['_id'] if alex else s.get('owner_id'),
                "uploader_name": alex['name'] if alex else s.get('owner_name', 'Alex Chen'),
                "uploader_role": "Course Mentor",
                "title": "Corey Schafer: Python OOP Video Tutorial",
                "description": "Watch this in-depth video lecture walking through practical Python classes, instances, class variables, and static methods.",
                "material_type": "video",
                "file_path": None,
                "file_name": None,
                "file_size": "Video Tutorial",
                "file_ext": "mp4",
                "external_url": yt_url,
                "embed_url": embed_url,
                "tag": "Video Tutorial",
                "likes": [str(sarah['_id']) if sarah else "1", str(emily['_id']) if emily else "3"],
                "downloads_count": 0,
                "views_count": 89,
                "created_at": datetime.now(timezone.utc)
            })

            # 3. Lab Practice Problems (Document)
            doc_filename = "Python_Practice_Lab_Exercises.txt"
            doc_path = os.path.join(s_dir, doc_filename)
            with open(doc_path, 'w', encoding='utf-8') as f:
                f.write("""Python OOP Lab Practice Problems
=====================================
Problem 1: Bank Account Management System
- Create a BankAccount class with balance, account_number, and owner_name.
- Implement deposit(amount), withdraw(amount), and get_statement() methods.
- Prevent negative withdrawals and overdraft fees.

Problem 2: Student Gradebook System
- Implement Student, Course, and Department classes.
- Compute weighted GPAs and print formatted transcript tables.
""")
            materials_to_add.append({
                "skill_id": s_id,
                "uploader_id": sarah['_id'] if sarah else s.get('owner_id'),
                "uploader_name": sarah['name'] if sarah else "Sarah Miller",
                "uploader_role": "Student Peer",
                "title": "Hands-on OOP Practice Lab Exercises",
                "description": "Two lab challenges to practice implementing class hierarchies and exception handling before our next peer session.",
                "material_type": "document",
                "file_path": f"{s_id}/{doc_filename}",
                "file_name": doc_filename,
                "file_size": format_file_size(os.path.getsize(doc_path)),
                "file_ext": "txt",
                "external_url": None,
                "embed_url": None,
                "tag": "Lab Exercise",
                "likes": [str(alex['_id']) if alex else "1"],
                "downloads_count": 8,
                "views_count": 21,
                "created_at": datetime.now(timezone.utc)
            })

        elif 'flask' in title.lower() or 'web' in title.lower():
            # Flask PDF
            pdf_filename = "Flask_Web_Architecture_Guide.pdf"
            pdf_path = os.path.join(s_dir, pdf_filename)
            create_sample_pdf(
                pdf_path,
                title="Flask Web Architecture & Routing Guide",
                subtitle="Blueprints, Jinja2 Templating, Session Security & MongoDB Access",
                author=s.get('owner_name', 'Alex Chen'),
                sections=[
                    ("1. Application Structure", [
                        "Separation of concerns: models for data, templates for presentation, utils for helpers.",
                        "Environment configuration via python-dotenv for secret keys and Mongo URIs.",
                        "Custom template filters for human-readable dates and file sizes."
                    ]),
                    ("2. Jinja2 Templating Power", [
                        "Use base.html as the primary shell with sticky navigation and flash messaging.",
                        "Employ block inheritance: {% extends 'base.html' %} and {% block content %}.",
                        "Safe URL routing using url_for('route_function_name', **params)."
                    ]),
                    ("3. Session Security & Flash Notifications", [
                        "Never store unhashed passwords in session cookies.",
                        "Flash categories: 'success' (green), 'danger' (red), 'info' (blue), 'warning' (amber)."
                    ])
                ]
            )
            materials_to_add.append({
                "skill_id": s_id,
                "uploader_id": alex['_id'] if alex else s.get('owner_id'),
                "uploader_name": alex['name'] if alex else s.get('owner_name', 'Alex Chen'),
                "uploader_role": "Course Mentor",
                "title": "Flask Web Development Architecture Guide",
                "description": "Essential architecture diagram and blueprint guide for designing multi-page Flask web applications with MongoDB.",
                "material_type": "pdf",
                "file_path": f"{s_id}/{pdf_filename}",
                "file_name": pdf_filename,
                "file_size": format_file_size(os.path.getsize(pdf_path)),
                "file_ext": "pdf",
                "external_url": None,
                "embed_url": None,
                "tag": "Slide Deck",
                "likes": [str(rohan['_id']) if rohan else "1", str(sarah['_id']) if sarah else "2"],
                "downloads_count": 23,
                "views_count": 65,
                "created_at": datetime.now(timezone.utc)
            })

            # Flask Video
            yt_url = "https://www.youtube.com/watch?v=Z1RJmh_OqeA"
            embed_url, _ = get_youtube_embed_info(yt_url)
            materials_to_add.append({
                "skill_id": s_id,
                "uploader_id": rohan['_id'] if rohan else s.get('owner_id'),
                "uploader_name": rohan['name'] if rohan else "Rohan Patel",
                "uploader_role": "Student Peer",
                "title": "FreeCodeCamp: Python Flask Full Course Tutorial",
                "description": "Comprehensive video lecture demonstrating routes, Jinja templates, dynamic URLs, forms, and database connections.",
                "material_type": "video",
                "file_path": None,
                "file_name": None,
                "file_size": "Video Tutorial",
                "file_ext": "mp4",
                "external_url": yt_url,
                "embed_url": embed_url,
                "tag": "Video Tutorial",
                "likes": [str(alex['_id']) if alex else "1"],
                "downloads_count": 0,
                "views_count": 78,
                "created_at": datetime.now(timezone.utc)
            })

        elif 'design' in title.lower() or 'figma' in title.lower() or 'illustration' in title.lower():
            # UI/UX PDF
            pdf_filename = "UI_UX_Design_System_Principles.pdf"
            pdf_path = os.path.join(s_dir, pdf_filename)
            create_sample_pdf(
                pdf_path,
                title="UI/UX Design Systems & Figma Guide",
                subtitle="Visual Hierarchy, Typography Tokens, 8pt Grid & Component States",
                author=s.get('owner_name', 'Sarah Miller'),
                sections=[
                    ("1. Design Tokens & Color Harmony", [
                        "Primary & Secondary palettes: choose cohesive 60-30-10 distribution.",
                        "Functional shades: Success (emerald), Warning (amber), Danger (rose).",
                        "High contrast text: ensure WCAG AA (4.5:1) minimum ratio."
                    ]),
                    ("2. The 8pt Spatial Grid", [
                        "Scale margins, gutters, and padding in multiples of 8 (8px, 16px, 24px, 32px).",
                        "Consistent component heights (buttons: 40px, 48px, inputs: 44px)."
                    ]),
                    ("3. Prototyping & Micro-interactions", [
                        "Use smart animate in Figma for fluid page transitions.",
                        "Include hover, focus, active, and disabled states for all interactable elements."
                    ])
                ]
            )
            materials_to_add.append({
                "skill_id": s_id,
                "uploader_id": sarah['_id'] if sarah else s.get('owner_id'),
                "uploader_name": sarah['name'] if sarah else s.get('owner_name', 'Sarah Miller'),
                "uploader_role": "Course Mentor",
                "title": "UI/UX Design System & Figma Wireframing Guide",
                "description": "Curated handbook explaining spatial grids, typography hierarchy, accessible colors, and responsive layout tricks.",
                "material_type": "pdf",
                "file_path": f"{s_id}/{pdf_filename}",
                "file_name": pdf_filename,
                "file_size": format_file_size(os.path.getsize(pdf_path)),
                "file_ext": "pdf",
                "external_url": None,
                "embed_url": None,
                "tag": "Lecture Notes",
                "likes": [str(alex['_id']) if alex else "1", str(emily['_id']) if emily else "2"],
                "downloads_count": 19,
                "views_count": 51,
                "created_at": datetime.now(timezone.utc)
            })

            # Figma Video
            yt_url = "https://www.youtube.com/watch?v=c9Wg6Cb_YlU"
            embed_url, _ = get_youtube_embed_info(yt_url)
            materials_to_add.append({
                "skill_id": s_id,
                "uploader_id": emily['_id'] if emily else s.get('owner_id'),
                "uploader_name": emily['name'] if emily else "Emily Watson",
                "uploader_role": "Student Peer",
                "title": "Figma UI/UX Design Essentials Course",
                "description": "Video tutorial covering vector paths, auto-layout 5.0, components, and wireframing modern mobile interfaces.",
                "material_type": "video",
                "file_path": None,
                "file_name": None,
                "file_size": "Video Tutorial",
                "file_ext": "mp4",
                "external_url": yt_url,
                "embed_url": embed_url,
                "tag": "Video Tutorial",
                "likes": [str(sarah['_id']) if sarah else "1"],
                "downloads_count": 0,
                "views_count": 44,
                "created_at": datetime.now(timezone.utc)
            })

        elif 'data' in title.lower() or 'ai' in title.lower() or 'intelligence' in title.lower() or 'machine' in title.lower():
            # Data Science / AI PDF
            pdf_filename = "Data_Science_and_ML_Lab_Guide.pdf"
            pdf_path = os.path.join(s_dir, pdf_filename)
            create_sample_pdf(
                pdf_path,
                title="Data Science & ML Quick Reference Manual",
                subtitle="NumPy Array Vectorization, Pandas DataFrames & Model Evaluation",
                author=s.get('owner_name', 'Rohan Patel'),
                sections=[
                    ("1. NumPy Vectorization & Array Operations", [
                        "Always avoid raw Python for-loops over numeric matrices.",
                        "Broadcasting: automatically expand arrays with compatible dimensions.",
                        "Boolean indexing: df[df['score'] > 85] for blazingly fast filtering."
                    ]),
                    ("2. Exploratory Data Analysis with Pandas", [
                        "df.info() and df.describe() for quick statistical distributions.",
                        "Handling nulls: df.dropna() vs df.fillna(df.mean()).",
                        "Groupby operations: df.groupby('department')['rating'].agg(['mean', 'count'])."
                    ]),
                    ("3. Supervised Model Evaluation", [
                        "Classification metrics: Accuracy, Precision, Recall, F1-Score, ROC-AUC.",
                        "Cross-validation: 5-fold KFold split to prevent overfitting."
                    ])
                ]
            )
            materials_to_add.append({
                "skill_id": s_id,
                "uploader_id": rohan['_id'] if rohan else s.get('owner_id'),
                "uploader_name": rohan['name'] if rohan else s.get('owner_name', 'Rohan Patel'),
                "uploader_role": "Course Mentor",
                "title": "Data Science & NumPy Vectorization Lab Notes",
                "description": "Handy laboratory reference sheet for Pandas data wrangling, missing data imputation, and model performance metrics.",
                "material_type": "pdf",
                "file_path": f"{s_id}/{pdf_filename}",
                "file_name": pdf_filename,
                "file_size": format_file_size(os.path.getsize(pdf_path)),
                "file_ext": "pdf",
                "external_url": None,
                "embed_url": None,
                "tag": "Lecture Notes",
                "likes": [str(alex['_id']) if alex else "1"],
                "downloads_count": 16,
                "views_count": 39,
                "created_at": datetime.now(timezone.utc)
            })

            # ML Video
            yt_url = "https://www.youtube.com/watch?v=aircAruvnKk"
            embed_url, _ = get_youtube_embed_info(yt_url)
            materials_to_add.append({
                "skill_id": s_id,
                "uploader_id": alex['_id'] if alex else s.get('owner_id'),
                "uploader_name": alex['name'] if alex else "Alex Chen",
                "uploader_role": "Student Peer",
                "title": "3Blue1Brown: Neural Networks Visual Introduction",
                "description": "The gold standard visual deep-dive into how neural networks, weights, biases, and activation functions actually work.",
                "material_type": "video",
                "file_path": None,
                "file_name": None,
                "file_size": "Video Tutorial",
                "file_ext": "mp4",
                "external_url": yt_url,
                "embed_url": embed_url,
                "tag": "Video Tutorial",
                "likes": [str(rohan['_id']) if rohan else "1", str(sarah['_id']) if sarah else "2"],
                "downloads_count": 0,
                "views_count": 112,
                "created_at": datetime.now(timezone.utc)
            })

        else:
            # Generic Course Material PDF
            pdf_filename = "Course_Study_Guide_and_Summary.pdf"
            pdf_path = os.path.join(s_dir, pdf_filename)
            create_sample_pdf(
                pdf_path,
                title=f"{title} - Study Guide",
                subtitle="Key Concepts, Learning Roadmap, and Peer Mentoring Notes",
                author=s.get('owner_name', 'Student Mentor'),
                sections=[
                    ("1. Foundation & Goals", [
                        "Comprehensive overview of key terminologies and introductory concepts.",
                        "Step-by-step roadmap to progress from beginner to confident practitioner."
                    ]),
                    ("2. Practical Applications", [
                        "Real-world case studies and project opportunities.",
                        "Collaborative exercises designed for peer-to-peer mentoring sessions."
                    ])
                ]
            )
            materials_to_add.append({
                "skill_id": s_id,
                "uploader_id": s.get('owner_id') or (alex['_id'] if alex else None),
                "uploader_name": s.get('owner_name', 'Student Mentor'),
                "uploader_role": "Course Mentor",
                "title": f"{title} - Study Guide & Notes",
                "description": f"Curated notes and learning milestones shared for students taking {title}.",
                "material_type": "pdf",
                "file_path": f"{s_id}/{pdf_filename}",
                "file_name": pdf_filename,
                "file_size": format_file_size(os.path.getsize(pdf_path)),
                "file_ext": "pdf",
                "external_url": None,
                "embed_url": None,
                "tag": "Study Guide",
                "likes": [str(sarah['_id']) if sarah else "1"],
                "downloads_count": 7,
                "views_count": 18,
                "created_at": datetime.now(timezone.utc)
            })

        if materials_to_add:
            db.materials.insert_many(materials_to_add)
            seeded_count += len(materials_to_add)

    print(f"Successfully seeded {seeded_count} course materials across {len(skills)} skills!")

if __name__ == '__main__':
    run_seed()
