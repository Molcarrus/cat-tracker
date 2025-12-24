# app.py
import os
import sqlite3
import base64
from datetime import datetime, timezone
from flask import Flask, render_template, request, redirect, url_for, g

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max
app.config['DATABASE'] = 'database.db'

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


# ============== DATABASE ==============

def get_db():
    if 'db' not in g:
        g.db = sqlite3.connect(app.config['DATABASE'])
        g.db.row_factory = sqlite3.Row
    return g.db


@app.teardown_appcontext
def close_db(error):
    db = g.pop('db', None)
    if db is not None:
        db.close()


def init_db():
    db = get_db()
    
    db.execute('''
        CREATE TABLE IF NOT EXISTS cats (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE,
            description TEXT,
            image_data TEXT,
            image_type TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    db.execute('''
        CREATE TABLE IF NOT EXISTS sightings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            cat_id INTEGER NOT NULL,
            date TEXT NOT NULL,
            location TEXT,
            notes TEXT,
            image_data TEXT,
            image_type TEXT,
            FOREIGN KEY (cat_id) REFERENCES cats (id) ON DELETE CASCADE
        )
    ''')
    
    db.execute('''
        CREATE TABLE IF NOT EXISTS cat_photos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            cat_id INTEGER NOT NULL,
            image_data TEXT NOT NULL,
            image_type TEXT NOT NULL,
            caption TEXT,
            photo_date TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (cat_id) REFERENCES cats (id) ON DELETE CASCADE
        )
    ''')
    
    db.commit()


@app.before_request
def before_request():
    init_db()


# ============== HELPER FUNCTIONS ==============

def get_utc_now():
    """Get current UTC time as ISO string"""
    return datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')


def get_utc_today():
    """Get today's date in UTC"""
    return datetime.now(timezone.utc).strftime('%Y-%m-%d')


def file_to_base64(file):
    """Convert uploaded file to base64 string"""
    if file and file.filename and allowed_file(file.filename):
        file_data = file.read()
        base64_data = base64.b64encode(file_data).decode('utf-8')
        ext = file.filename.rsplit('.', 1)[1].lower()
        mime_types = {
            'jpg': 'image/jpeg',
            'jpeg': 'image/jpeg',
            'png': 'image/png',
            'gif': 'image/gif',
            'webp': 'image/webp'
        }
        image_type = mime_types.get(ext, 'image/jpeg')
        return base64_data, image_type
    return None, None


def get_image_src(image_data, image_type):
    """Create data URI for image"""
    if image_data and image_type:
        return f"data:{image_type};base64,{image_data}"
    return None


def normalize_datetime(dt_string):
    """Convert various datetime formats to ISO format for JavaScript"""
    if not dt_string:
        return None
    
    # Already in ISO format with Z
    if dt_string.endswith('Z'):
        return dt_string
    
    # Try different formats
    formats = [
        '%Y-%m-%dT%H:%M:%S',
        '%Y-%m-%d %H:%M:%S',
        '%Y-%m-%d %H:%M',
        '%Y-%m-%d',
    ]
    
    for fmt in formats:
        try:
            dt = datetime.strptime(dt_string, fmt)
            # Return as ISO format with Z (UTC indicator)
            return dt.strftime('%Y-%m-%dT%H:%M:%SZ')
        except ValueError:
            continue
    
    return dt_string


def combine_date_time(date_str, time_str):
    """Combine date and time strings into ISO format"""
    if not date_str:
        return None
    
    if time_str:
        return f"{date_str}T{time_str}:00Z"
    else:
        return f"{date_str}T00:00:00Z"


def get_all_cat_photos(cat_id):
    """Get all photos for a cat from both gallery and sightings"""
    db = get_db()
    
    # Get manually uploaded photos
    gallery_photos = db.execute('''
        SELECT 
            id,
            'gallery' as source,
            image_data,
            image_type,
            caption,
            photo_date,
            created_at,
            NULL as location,
            NULL as notes
        FROM cat_photos 
        WHERE cat_id = ?
    ''', (cat_id,)).fetchall()
    
    # Get sighting photos
    sighting_photos = db.execute('''
        SELECT 
            id,
            'sighting' as source,
            image_data,
            image_type,
            notes as caption,
            date as photo_date,
            date as created_at,
            location,
            notes
        FROM sightings 
        WHERE cat_id = ? AND image_data IS NOT NULL
    ''', (cat_id,)).fetchall()
    
    # Combine all photos
    all_photos = []
    
    for p in gallery_photos:
        photo = dict(p)
        photo['image_src'] = get_image_src(p['image_data'], p['image_type'])
        photo['iso_date'] = normalize_datetime(p['photo_date']) or normalize_datetime(p['created_at'])
        all_photos.append(photo)
    
    for p in sighting_photos:
        photo = dict(p)
        photo['image_src'] = get_image_src(p['image_data'], p['image_type'])
        photo['iso_date'] = normalize_datetime(p['photo_date'])
        all_photos.append(photo)
    
    # Sort by date (newest first)
    all_photos.sort(key=lambda x: x['iso_date'] or '', reverse=True)
    
    return all_photos


# ============== ROUTES ==============

@app.route('/')
def home():
    db = get_db()
    
    cats = db.execute('SELECT * FROM cats ORDER BY name').fetchall()
    
    # Get today's sightings (we'll filter on client side for proper timezone)
    # Get last 24 hours of sightings to be safe
    sightings = db.execute('''
        SELECT sightings.*, cats.name as cat_name, 
               cats.image_data as cat_image_data, 
               cats.image_type as cat_image_type
        FROM sightings 
        JOIN cats ON sightings.cat_id = cats.id
        ORDER BY sightings.date DESC
        LIMIT 50
    ''').fetchall()
    
    cats_with_images = []
    for cat in cats:
        cat_dict = dict(cat)
        cat_dict['image_src'] = get_image_src(cat['image_data'], cat['image_type'])
        cats_with_images.append(cat_dict)
    
    sightings_with_images = []
    for s in sightings:
        s_dict = dict(s)
        s_dict['cat_image_src'] = get_image_src(s['cat_image_data'], s['cat_image_type'])
        s_dict['sighting_image_src'] = get_image_src(s['image_data'], s['image_type'])
        s_dict['iso_date'] = normalize_datetime(s['date'])
        sightings_with_images.append(s_dict)
    
    return render_template('home.html',
                           cats=cats_with_images,
                           sightings=sightings_with_images,
                           utc_now=get_utc_now())


@app.route('/log-sighting', methods=['POST'])
def log_sighting():
    cat_id = request.form.get('cat_id')
    location = request.form.get('location', '')
    notes = request.form.get('notes', '')
    
    image_data = None
    image_type = None
    if 'image' in request.files:
        file = request.files['image']
        image_data, image_type = file_to_base64(file)
    
    if cat_id:
        db = get_db()
        db.execute(
            'INSERT INTO sightings (cat_id, date, location, notes, image_data, image_type) VALUES (?, ?, ?, ?, ?, ?)',
            (cat_id, get_utc_now(), location, notes, image_data, image_type)
        )
        db.commit()
    
    return redirect(url_for('home'))


@app.route('/remove-sighting/<int:sighting_id>', methods=['POST'])
def remove_sighting(sighting_id):
    db = get_db()
    db.execute('DELETE FROM sightings WHERE id = ?', (sighting_id,))
    db.commit()
    return redirect(url_for('home'))


@app.route('/quick-add-cat', methods=['POST'])
def quick_add_cat():
    name = request.form.get('name', '').strip()
    
    if name:
        db = get_db()
        try:
            db.execute('INSERT INTO cats (name, created_at) VALUES (?, ?)', (name, get_utc_now()))
            db.commit()
        except sqlite3.IntegrityError:
            pass
    
    return redirect(url_for('home'))


@app.route('/cats')
def cats_list():
    db = get_db()
    cats = db.execute('''
        SELECT cats.*, COUNT(sightings.id) as sighting_count
        FROM cats
        LEFT JOIN sightings ON cats.id = sightings.cat_id
        GROUP BY cats.id
        ORDER BY cats.name
    ''').fetchall()
    
    cats_with_images = []
    for cat in cats:
        cat_dict = dict(cat)
        cat_dict['image_src'] = get_image_src(cat['image_data'], cat['image_type'])
        
        gallery_count = db.execute(
            'SELECT COUNT(*) as count FROM cat_photos WHERE cat_id = ?',
            (cat['id'],)
        ).fetchone()['count']
        
        sighting_photo_count = db.execute(
            'SELECT COUNT(*) as count FROM sightings WHERE cat_id = ? AND image_data IS NOT NULL',
            (cat['id'],)
        ).fetchone()['count']
        
        cat_dict['photo_count'] = gallery_count + sighting_photo_count
        
        cats_with_images.append(cat_dict)
    
    return render_template('cats.html', cats=cats_with_images)


@app.route('/add-cat', methods=['POST'])
def add_cat():
    name = request.form.get('name', '').strip()
    description = request.form.get('description', '').strip()
    
    if not name:
        return redirect(url_for('cats_list'))
    
    image_data = None
    image_type = None
    
    if 'image' in request.files:
        file = request.files['image']
        image_data, image_type = file_to_base64(file)
    
    db = get_db()
    try:
        db.execute(
            'INSERT INTO cats (name, description, image_data, image_type, created_at) VALUES (?, ?, ?, ?, ?)',
            (name, description, image_data, image_type, get_utc_now())
        )
        db.commit()
    except sqlite3.IntegrityError:
        pass
    
    return redirect(url_for('cats_list'))


@app.route('/cats/<int:cat_id>')
def view_cat(cat_id):
    db = get_db()
    
    cat = db.execute('SELECT * FROM cats WHERE id = ?', (cat_id,)).fetchone()
    
    if not cat:
        return redirect(url_for('cats_list'))
    
    cat_dict = dict(cat)
    cat_dict['image_src'] = get_image_src(cat['image_data'], cat['image_type'])
    
    sightings = db.execute('''
        SELECT * FROM sightings 
        WHERE cat_id = ? 
        ORDER BY date DESC 
        LIMIT 50
    ''', (cat_id,)).fetchall()
    
    sightings_with_images = []
    for s in sightings:
        s_dict = dict(s)
        s_dict['image_src'] = get_image_src(s['image_data'], s['image_type'])
        s_dict['iso_date'] = normalize_datetime(s['date'])
        sightings_with_images.append(s_dict)
    
    sighting_count = db.execute(
        'SELECT COUNT(*) as count FROM sightings WHERE cat_id = ?',
        (cat_id,)
    ).fetchone()['count']
    
    all_photos = get_all_cat_photos(cat_id)
    
    last_sighting = db.execute(
        'SELECT date FROM sightings WHERE cat_id = ? ORDER BY date DESC LIMIT 1',
        (cat_id,)
    ).fetchone()
    last_seen_iso = normalize_datetime(last_sighting['date']) if last_sighting else None
    
    return render_template('cat_detail.html',
                           cat=cat_dict,
                           sightings=sightings_with_images,
                           sighting_count=sighting_count,
                           photos=all_photos,
                           last_seen_iso=last_seen_iso)


@app.route('/cats/<int:cat_id>/edit', methods=['POST'])
def edit_cat(cat_id):
    name = request.form.get('name', '').strip()
    description = request.form.get('description', '').strip()
    
    if not name:
        return redirect(url_for('view_cat', cat_id=cat_id))
    
    db = get_db()
    
    if 'image' in request.files:
        file = request.files['image']
        if file and file.filename:
            image_data, image_type = file_to_base64(file)
            if image_data:
                db.execute(
                    'UPDATE cats SET name = ?, description = ?, image_data = ?, image_type = ? WHERE id = ?',
                    (name, description, image_data, image_type, cat_id)
                )
                db.commit()
                return redirect(url_for('view_cat', cat_id=cat_id))
    
    db.execute(
        'UPDATE cats SET name = ?, description = ? WHERE id = ?',
        (name, description, cat_id)
    )
    db.commit()
    return redirect(url_for('view_cat', cat_id=cat_id))


@app.route('/cats/<int:cat_id>/remove-profile-photo', methods=['POST'])
def remove_profile_photo(cat_id):
    db = get_db()
    db.execute(
        'UPDATE cats SET image_data = NULL, image_type = NULL WHERE id = ?',
        (cat_id,)
    )
    db.commit()
    return redirect(url_for('view_cat', cat_id=cat_id))


@app.route('/cats/<int:cat_id>/delete', methods=['POST'])
def delete_cat(cat_id):
    db = get_db()
    db.execute('DELETE FROM cat_photos WHERE cat_id = ?', (cat_id,))
    db.execute('DELETE FROM sightings WHERE cat_id = ?', (cat_id,))
    db.execute('DELETE FROM cats WHERE id = ?', (cat_id,))
    db.commit()
    return redirect(url_for('cats_list'))


# ============== GALLERY ROUTES ==============

@app.route('/cats/<int:cat_id>/photos/add', methods=['POST'])
def add_cat_photos(cat_id):
    db = get_db()
    
    cat = db.execute('SELECT * FROM cats WHERE id = ?', (cat_id,)).fetchone()
    if not cat:
        return redirect(url_for('cats_list'))
    
    caption = request.form.get('caption', '').strip()
    photo_date = request.form.get('photo_date', '').strip()
    photo_time = request.form.get('photo_time', '').strip()
    
    # Combine date and time into ISO format
    iso_date = combine_date_time(photo_date, photo_time) if photo_date else get_utc_now()
    
    if 'photos' in request.files:
        files = request.files.getlist('photos')
        
        for file in files:
            if file and file.filename:
                image_data, image_type = file_to_base64(file)
                if image_data:
                    db.execute('''
                        INSERT INTO cat_photos (cat_id, image_data, image_type, caption, photo_date, created_at)
                        VALUES (?, ?, ?, ?, ?, ?)
                    ''', (cat_id, image_data, image_type, caption, iso_date, get_utc_now()))
    
    db.commit()
    return redirect(url_for('view_cat', cat_id=cat_id))


@app.route('/cats/<int:cat_id>/photos/<source>/<int:photo_id>/delete', methods=['POST'])
def delete_cat_photo(cat_id, source, photo_id):
    db = get_db()
    
    if source == 'gallery':
        db.execute('DELETE FROM cat_photos WHERE id = ? AND cat_id = ?', (photo_id, cat_id))
    elif source == 'sighting':
        db.execute('UPDATE sightings SET image_data = NULL, image_type = NULL WHERE id = ? AND cat_id = ?', (photo_id, cat_id))
    
    db.commit()
    return redirect(url_for('view_cat', cat_id=cat_id))


@app.route('/cats/<int:cat_id>/photos/<source>/<int:photo_id>/set-profile', methods=['POST'])
def set_profile_photo(cat_id, source, photo_id):
    db = get_db()
    
    if source == 'gallery':
        photo = db.execute(
            'SELECT * FROM cat_photos WHERE id = ? AND cat_id = ?',
            (photo_id, cat_id)
        ).fetchone()
    elif source == 'sighting':
        photo = db.execute(
            'SELECT * FROM sightings WHERE id = ? AND cat_id = ?',
            (photo_id, cat_id)
        ).fetchone()
    else:
        return redirect(url_for('view_cat', cat_id=cat_id))
    
    if photo and photo['image_data']:
        db.execute(
            'UPDATE cats SET image_data = ?, image_type = ? WHERE id = ?',
            (photo['image_data'], photo['image_type'], cat_id)
        )
        db.commit()
    
    return redirect(url_for('view_cat', cat_id=cat_id))


@app.route('/history')
def history():
    db = get_db()
    
    sightings = db.execute('''
        SELECT sightings.*, cats.name as cat_name,
               cats.image_data as cat_image_data,
               cats.image_type as cat_image_type
        FROM sightings 
        JOIN cats ON sightings.cat_id = cats.id
        ORDER BY sightings.date DESC
        LIMIT 100
    ''').fetchall()
    
    sightings_list = []
    for s in sightings:
        s_dict = dict(s)
        s_dict['cat_image_src'] = get_image_src(s['cat_image_data'], s['cat_image_type'])
        s_dict['sighting_image_src'] = get_image_src(s['image_data'], s['image_type'])
        s_dict['iso_date'] = normalize_datetime(s['date'])
        sightings_list.append(s_dict)
    
    total_count = db.execute('SELECT COUNT(*) as count FROM sightings').fetchone()['count']
    
    return render_template('history.html', sightings=sightings_list, total=total_count)


if __name__ == '__main__':
    app.run(debug=True, port=5000)
