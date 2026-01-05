# app.py
import os
import base64
from datetime import datetime, timezone
from flask import Flask, render_template, request, redirect, url_for, g
from urllib.parse import urlparse

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max

# Database configuration
# Use PostgreSQL if DATABASE_URL is set (production), otherwise SQLite (local dev)
DATABASE_URL = os.environ.get('DATABASE_URL')

if DATABASE_URL:
    # PostgreSQL
    import psycopg2
    from psycopg2.extras import RealDictCursor
    DB_TYPE = 'postgresql'
else:
    # SQLite for local development
    import sqlite3
    DB_TYPE = 'sqlite'
    DATABASE_PATH = 'database.db'

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


# ============== DATABASE ==============

def get_db():
    if 'db' not in g:
        if DB_TYPE == 'postgresql':
            g.db = psycopg2.connect(DATABASE_URL, cursor_factory=RealDictCursor)
        else:
            g.db = sqlite3.connect(DATABASE_PATH)
            g.db.row_factory = sqlite3.Row
    return g.db


@app.teardown_appcontext
def close_db(error):
    db = g.pop('db', None)
    if db is not None:
        db.close()


def init_db():
    db = get_db()
    cur = db.cursor()
    
    if DB_TYPE == 'postgresql':
        # PostgreSQL syntax
        cur.execute('''
            CREATE TABLE IF NOT EXISTS cats (
                id SERIAL PRIMARY KEY,
                name TEXT NOT NULL UNIQUE,
                description TEXT,
                image_data TEXT,
                image_type TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        cur.execute('''
            CREATE TABLE IF NOT EXISTS sightings (
                id SERIAL PRIMARY KEY,
                cat_id INTEGER NOT NULL REFERENCES cats(id) ON DELETE CASCADE,
                date TEXT NOT NULL,
                location TEXT,
                notes TEXT,
                image_data TEXT,
                image_type TEXT
            )
        ''')
        
        cur.execute('''
            CREATE TABLE IF NOT EXISTS cat_photos (
                id SERIAL PRIMARY KEY,
                cat_id INTEGER NOT NULL REFERENCES cats(id) ON DELETE CASCADE,
                image_data TEXT NOT NULL,
                image_type TEXT NOT NULL,
                caption TEXT,
                photo_date TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        db.commit()
    else:
        # SQLite syntax
        cur.execute('''
            CREATE TABLE IF NOT EXISTS cats (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE,
                description TEXT,
                image_data TEXT,
                image_type TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        cur.execute('''
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
        
        cur.execute('''
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


def execute_query(query, params=None, fetch_one=False, fetch_all=False, commit=False):
    """Execute a database query with proper handling for both PostgreSQL and SQLite"""
    db = get_db()
    cur = db.cursor()
    
    # Convert ? placeholders to %s for PostgreSQL
    if DB_TYPE == 'postgresql' and params:
        query = query.replace('?', '%s')
    
    try:
        if params:
            cur.execute(query, params)
        else:
            cur.execute(query)
        
        if commit:
            db.commit()
            # Get last inserted ID for PostgreSQL
            if DB_TYPE == 'postgresql' and 'INSERT' in query.upper():
                try:
                    cur.execute('SELECT lastval()')
                    return cur.fetchone()['lastval']
                except:
                    pass
            return cur.lastrowid if DB_TYPE == 'sqlite' else None
        
        if fetch_one:
            row = cur.fetchone()
            return dict(row) if row else None
        
        if fetch_all:
            rows = cur.fetchall()
            return [dict(row) for row in rows]
        
        return None
    except Exception as e:
        print(f"Database error: {e}")
        db.rollback()
        raise


@app.before_request
def before_request():
    init_db()


# ============== HELPER FUNCTIONS ==============

def get_utc_now():
    """Get current UTC time as ISO string"""
    return datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')


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
    """Convert various datetime formats to ISO format"""
    if not dt_string:
        return None
    
    if isinstance(dt_string, datetime):
        return dt_string.strftime('%Y-%m-%dT%H:%M:%SZ')
    
    dt_string = str(dt_string)
    
    if dt_string.endswith('Z'):
        return dt_string
    
    formats = [
        '%Y-%m-%dT%H:%M:%S',
        '%Y-%m-%d %H:%M:%S',
        '%Y-%m-%d %H:%M:%S.%f',
        '%Y-%m-%d %H:%M',
        '%Y-%m-%d',
    ]
    
    for fmt in formats:
        try:
            dt = datetime.strptime(dt_string.split('.')[0].split('+')[0], fmt)
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
    # Get gallery photos
    gallery_photos = execute_query('''
        SELECT id, 'gallery' as source, image_data, image_type, caption,
               photo_date, created_at, NULL as location, NULL as notes
        FROM cat_photos WHERE cat_id = ?
    ''', (cat_id,), fetch_all=True) or []
    
    # Get sighting photos
    sighting_photos = execute_query('''
        SELECT id, 'sighting' as source, image_data, image_type, notes as caption,
               date as photo_date, date as created_at, location, notes
        FROM sightings WHERE cat_id = ? AND image_data IS NOT NULL
    ''', (cat_id,), fetch_all=True) or []
    
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
    
    all_photos.sort(key=lambda x: x['iso_date'] or '', reverse=True)
    
    return all_photos


# ============== ROUTES ==============

@app.route('/')
def home():
    cats = execute_query('SELECT * FROM cats ORDER BY name', fetch_all=True) or []
    
    sightings = execute_query('''
        SELECT sightings.*, cats.name as cat_name, 
               cats.image_data as cat_image_data, 
               cats.image_type as cat_image_type
        FROM sightings 
        JOIN cats ON sightings.cat_id = cats.id
        ORDER BY sightings.date DESC
        LIMIT 50
    ''', fetch_all=True) or []
    
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
        execute_query(
            'INSERT INTO sightings (cat_id, date, location, notes, image_data, image_type) VALUES (?, ?, ?, ?, ?, ?)',
            (cat_id, get_utc_now(), location, notes, image_data, image_type),
            commit=True
        )
    
    return redirect(url_for('home'))


@app.route('/remove-sighting/<int:sighting_id>', methods=['POST'])
def remove_sighting(sighting_id):
    execute_query('DELETE FROM sightings WHERE id = ?', (sighting_id,), commit=True)
    return redirect(url_for('home'))


@app.route('/quick-add-cat', methods=['POST'])
def quick_add_cat():
    name = request.form.get('name', '').strip()
    
    if name:
        try:
            execute_query(
                'INSERT INTO cats (name, created_at) VALUES (?, ?)',
                (name, get_utc_now()),
                commit=True
            )
        except:
            pass  # Cat already exists
    
    return redirect(url_for('home'))


@app.route('/cats')
def cats_list():
    cats = execute_query('''
        SELECT cats.*, COUNT(sightings.id) as sighting_count
        FROM cats
        LEFT JOIN sightings ON cats.id = sightings.cat_id
        GROUP BY cats.id
        ORDER BY cats.name
    ''', fetch_all=True) or []
    
    cats_with_images = []
    for cat in cats:
        cat_dict = dict(cat)
        cat_dict['image_src'] = get_image_src(cat['image_data'], cat['image_type'])
        
        gallery_count = execute_query(
            'SELECT COUNT(*) as count FROM cat_photos WHERE cat_id = ?',
            (cat['id'],), fetch_one=True
        )
        
        sighting_photo_count = execute_query(
            'SELECT COUNT(*) as count FROM sightings WHERE cat_id = ? AND image_data IS NOT NULL',
            (cat['id'],), fetch_one=True
        )
        
        cat_dict['photo_count'] = (gallery_count['count'] if gallery_count else 0) + \
                                  (sighting_photo_count['count'] if sighting_photo_count else 0)
        
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
    
    try:
        execute_query(
            'INSERT INTO cats (name, description, image_data, image_type, created_at) VALUES (?, ?, ?, ?, ?)',
            (name, description, image_data, image_type, get_utc_now()),
            commit=True
        )
    except:
        pass
    
    return redirect(url_for('cats_list'))


@app.route('/cats/<int:cat_id>')
def view_cat(cat_id):
    cat = execute_query('SELECT * FROM cats WHERE id = ?', (cat_id,), fetch_one=True)
    
    if not cat:
        return redirect(url_for('cats_list'))
    
    cat_dict = dict(cat)
    cat_dict['image_src'] = get_image_src(cat['image_data'], cat['image_type'])
    
    sightings = execute_query('''
        SELECT * FROM sightings 
        WHERE cat_id = ? 
        ORDER BY date DESC 
        LIMIT 50
    ''', (cat_id,), fetch_all=True) or []
    
    sightings_with_images = []
    for s in sightings:
        s_dict = dict(s)
        s_dict['image_src'] = get_image_src(s['image_data'], s['image_type'])
        s_dict['iso_date'] = normalize_datetime(s['date'])
        sightings_with_images.append(s_dict)
    
    sighting_count = execute_query(
        'SELECT COUNT(*) as count FROM sightings WHERE cat_id = ?',
        (cat_id,), fetch_one=True
    )
    
    all_photos = get_all_cat_photos(cat_id)
    
    last_sighting = execute_query(
        'SELECT date FROM sightings WHERE cat_id = ? ORDER BY date DESC LIMIT 1',
        (cat_id,), fetch_one=True
    )
    last_seen_iso = normalize_datetime(last_sighting['date']) if last_sighting else None
    
    return render_template('cat_detail.html',
                           cat=cat_dict,
                           sightings=sightings_with_images,
                           sighting_count=sighting_count['count'] if sighting_count else 0,
                           photos=all_photos,
                           last_seen_iso=last_seen_iso)


@app.route('/cats/<int:cat_id>/edit', methods=['POST'])
def edit_cat(cat_id):
    name = request.form.get('name', '').strip()
    description = request.form.get('description', '').strip()
    
    if not name:
        return redirect(url_for('view_cat', cat_id=cat_id))
    
    if 'image' in request.files:
        file = request.files['image']
        if file and file.filename:
            image_data, image_type = file_to_base64(file)
            if image_data:
                execute_query(
                    'UPDATE cats SET name = ?, description = ?, image_data = ?, image_type = ? WHERE id = ?',
                    (name, description, image_data, image_type, cat_id),
                    commit=True
                )
                return redirect(url_for('view_cat', cat_id=cat_id))
    
    execute_query(
        'UPDATE cats SET name = ?, description = ? WHERE id = ?',
        (name, description, cat_id),
        commit=True
    )
    return redirect(url_for('view_cat', cat_id=cat_id))


@app.route('/cats/<int:cat_id>/remove-profile-photo', methods=['POST'])
def remove_profile_photo(cat_id):
    execute_query(
        'UPDATE cats SET image_data = NULL, image_type = NULL WHERE id = ?',
        (cat_id,),
        commit=True
    )
    return redirect(url_for('view_cat', cat_id=cat_id))


@app.route('/cats/<int:cat_id>/delete', methods=['POST'])
def delete_cat(cat_id):
    execute_query('DELETE FROM cat_photos WHERE cat_id = ?', (cat_id,), commit=True)
    execute_query('DELETE FROM sightings WHERE cat_id = ?', (cat_id,), commit=True)
    execute_query('DELETE FROM cats WHERE id = ?', (cat_id,), commit=True)
    return redirect(url_for('cats_list'))


# ============== GALLERY ROUTES ==============

@app.route('/cats/<int:cat_id>/photos/add', methods=['POST'])
def add_cat_photos(cat_id):
    cat = execute_query('SELECT * FROM cats WHERE id = ?', (cat_id,), fetch_one=True)
    if not cat:
        return redirect(url_for('cats_list'))
    
    caption = request.form.get('caption', '').strip()
    photo_date = request.form.get('photo_date', '').strip()
    photo_time = request.form.get('photo_time', '').strip()
    
    iso_date = combine_date_time(photo_date, photo_time) if photo_date else get_utc_now()
    
    if 'photos' in request.files:
        files = request.files.getlist('photos')
        
        for file in files:
            if file and file.filename:
                image_data, image_type = file_to_base64(file)
                if image_data:
                    execute_query('''
                        INSERT INTO cat_photos (cat_id, image_data, image_type, caption, photo_date, created_at)
                        VALUES (?, ?, ?, ?, ?, ?)
                    ''', (cat_id, image_data, image_type, caption, iso_date, get_utc_now()),
                    commit=True)
    
    return redirect(url_for('view_cat', cat_id=cat_id))


@app.route('/cats/<int:cat_id>/photos/<source>/<int:photo_id>/delete', methods=['POST'])
def delete_cat_photo(cat_id, source, photo_id):
    if source == 'gallery':
        execute_query('DELETE FROM cat_photos WHERE id = ? AND cat_id = ?', (photo_id, cat_id), commit=True)
    elif source == 'sighting':
        execute_query(
            'UPDATE sightings SET image_data = NULL, image_type = NULL WHERE id = ? AND cat_id = ?',
            (photo_id, cat_id),
            commit=True
        )
    
    return redirect(url_for('view_cat', cat_id=cat_id))


@app.route('/cats/<int:cat_id>/photos/<source>/<int:photo_id>/set-profile', methods=['POST'])
def set_profile_photo(cat_id, source, photo_id):
    if source == 'gallery':
        photo = execute_query(
            'SELECT * FROM cat_photos WHERE id = ? AND cat_id = ?',
            (photo_id, cat_id), fetch_one=True
        )
    elif source == 'sighting':
        photo = execute_query(
            'SELECT * FROM sightings WHERE id = ? AND cat_id = ?',
            (photo_id, cat_id), fetch_one=True
        )
    else:
        return redirect(url_for('view_cat', cat_id=cat_id))
    
    if photo and photo.get('image_data'):
        execute_query(
            'UPDATE cats SET image_data = ?, image_type = ? WHERE id = ?',
            (photo['image_data'], photo['image_type'], cat_id),
            commit=True
        )
    
    return redirect(url_for('view_cat', cat_id=cat_id))


@app.route('/history')
def history():
    sightings = execute_query('''
        SELECT sightings.*, cats.name as cat_name,
               cats.image_data as cat_image_data,
               cats.image_type as cat_image_type
        FROM sightings 
        JOIN cats ON sightings.cat_id = cats.id
        ORDER BY sightings.date DESC
        LIMIT 100
    ''', fetch_all=True) or []
    
    sightings_list = []
    for s in sightings:
        s_dict = dict(s)
        s_dict['cat_image_src'] = get_image_src(s['cat_image_data'], s['cat_image_type'])
        s_dict['sighting_image_src'] = get_image_src(s['image_data'], s['image_type'])
        s_dict['iso_date'] = normalize_datetime(s['date'])
        sightings_list.append(s_dict)
    
    total_count = execute_query('SELECT COUNT(*) as count FROM sightings', fetch_one=True)
    
    return render_template('history.html',
                           sightings=sightings_list,
                           total=total_count['count'] if total_count else 0)


# Health check endpoint for deployment platforms
@app.route('/health')
def health():
    return {'status': 'healthy', 'database': DB_TYPE}


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    debug = os.environ.get('FLASK_DEBUG', 'False').lower() == 'true'
    app.run(host='0.0.0.0', port=port, debug=debug)