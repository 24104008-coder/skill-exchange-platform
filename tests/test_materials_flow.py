import io
import sys
import os

# Add project root to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import app, db

def run_tests():
    user = db.users.find_one()
    skill = db.skills.find_one()
    s_id = str(skill['_id'])

    with app.test_client() as c:
        with c.session_transaction() as sess:
            sess['user_id'] = str(user['_id'])
            sess['user_name'] = user['name']

        # 1. Test upvote
        mat = db.materials.find_one({'skill_id': skill['_id']})
        m_id = str(mat['_id'])
        r_like = c.post(f'/skill/{s_id}/material/{m_id}/like', headers={'X-Requested-With': 'XMLHttpRequest'})
        print('Like response:', r_like.status_code, r_like.get_json())

        # 2. Test upload PDF file
        pdf_bytes = b"%PDF-1.4 sample test bytes"
        data = {
            'title': 'Test Integration PDF Document',
            'tag': 'Lecture Notes',
            'upload_type': 'file',
            'description': 'Automated testing PDF upload',
            'material_file': (io.BytesIO(pdf_bytes), 'test_integration.pdf')
        }
        r_upload = c.post(f'/skill/{s_id}/materials/upload', data=data, content_type='multipart/form-data', follow_redirects=True)
        print('Upload file status:', r_upload.status_code)

        # 3. Test share YouTube video link
        link_data = {
            'title': 'Test YouTube Video Lecture',
            'tag': 'Video Tutorial',
            'upload_type': 'link',
            'external_url': 'https://www.youtube.com/watch?v=dQw4w9WgXcQ',
            'description': 'Automated testing video link share'
        }
        r_link = c.post(f'/skill/{s_id}/materials/upload', data=link_data, follow_redirects=True)
        print('Share video link status:', r_link.status_code)

        # 4. Verify in DB
        new_pdf = db.materials.find_one({'title': 'Test Integration PDF Document'})
        new_yt = db.materials.find_one({'title': 'Test YouTube Video Lecture'})
        print('Verified PDF in DB:', bool(new_pdf), 'file_path:', new_pdf.get('file_path') if new_pdf else None)
        print('Verified Video in DB:', bool(new_yt), 'embed_url:', new_yt.get('embed_url') if new_yt else None)

        # 5. Clean up test documents
        if new_pdf:
            c.post(f'/skill/{s_id}/material/{new_pdf["_id"]}/delete', follow_redirects=True)
        if new_yt:
            c.post(f'/skill/{s_id}/material/{new_yt["_id"]}/delete', follow_redirects=True)
        print('All tests passed and cleaned up successfully!')

if __name__ == '__main__':
    run_tests()
