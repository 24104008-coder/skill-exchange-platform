import urllib.request
import urllib.parse
import http.cookiejar
import uuid

cj = http.cookiejar.CookieJar()
opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj))

# 1. Login
login_data = urllib.parse.urlencode({'email': 'alex.chen@college.edu', 'password': 'password123'}).encode('utf-8')
opener.open('http://127.0.0.1:5000/login', data=login_data)

# 2. Upload file via multipart/form-data
boundary = uuid.uuid4().hex
lines = []
def add_field(name, value):
    lines.append(f'--{boundary}')
    lines.append(f'Content-Disposition: form-data; name="{name}"')
    lines.append('')
    lines.append(value)

add_field('title', 'Exam Preparation Cheatsheet and Formula Sheet')
add_field('tag', 'Cheat Sheet')
add_field('upload_type', 'file')
add_field('description', 'Key formulas and quick revision points before the college midterm lab test.')

lines.append(f'--{boundary}')
lines.append('Content-Disposition: form-data; name="material_file"; filename="exam_prep_cheatsheet.pdf"')
lines.append('Content-Type: application/pdf')
lines.append('')
lines.append('%PDF-1.4 sample pdf content for verification')
lines.append(f'--{boundary}--')
lines.append('')

body = '\r\n'.join(lines).encode('utf-8')
req = urllib.request.Request(
    'http://127.0.0.1:5000/skill/6ac8cd8632a39e4f7af5e303/materials/upload',
    data=body,
    headers={'Content-Type': f'multipart/form-data; boundary={boundary}'}
)

resp = opener.open(req)
print('PDF Uploaded successfully, status URL:', resp.geturl())

# 3. Check course details contains the newly uploaded cheat sheet
req = urllib.request.Request('http://127.0.0.1:5000/skill/6ac8cd8632a39e4f7af5e303')
page = opener.open(req).read().decode('utf-8')
print('Newly uploaded PDF cheat sheet is present on page:', 'Exam Preparation Cheatsheet and Formula Sheet' in page)
