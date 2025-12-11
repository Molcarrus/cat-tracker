# app.py
import os
import sqlite3
import base64
from datetime import datetime
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
    
    # Cats table
    db.execute('''
        CREATE TABLE IF NOT EXISTS cats (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE,
            description TEXT,
            image_data TEXT,
            image_type TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Sightings table
    db.execute('''
        CREATE TABLE IF NOT EXISTS sightings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            cat_id INTEGER NOT NULL,
            date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            location TEXT,
            notes TEXT,
            image_data TEXT,
            image_type TEXT,
            FOREIGN KEY (cat_id) REFERENCES cats (id) ON DELETE CASCADE
        )
    ''')
    
    # Cat photos gallery table (for manually uploaded old photos)
    db.execute('''
        CREATE TABLE IF NOT EXISTS cat_photos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            cat_id INTEGER NOT NULL,
            image_data TEXT NOT NULL,
            image_type TEXT NOT NULL,
            caption TEXT,
            photo_date TEXT,
            photo_time TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (cat_id) REFERENCES cats (id) ON DELETE CASCADE
        )
    ''')
    
    db.commit()


@app.before_request
def before_request():
    init_db()


# ============== HELPER FUNCTIONS ==============

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


def parse_datetime(dt_string):
    """Parse datetime string to datetime object"""
    if not dt_string:
        return None
    
    # Try different formats
    formats = [
        '%Y-%m-%d %H:%M:%S',
        '%Y-%m-%d %H:%M',
        '%Y-%m-%d',
    ]
    
    for fmt in formats:
        try:
            return datetime.strptime(dt_string, fmt)
        except ValueError:
            continue
    
    return None


def format_date(dt_string):
    """Format date for display"""
    dt = parse_datetime(dt_string)
    if dt:
        return dt.strftime('%b %d, %Y')
    return dt_string or ''


def format_time(dt_string):
    """Format time for display"""
    dt = parse_datetime(dt_string)
    if dt:
        return dt.strftime('%I:%M %p')
    return ''


def format_datetime_full(dt_string):
    """Format full datetime for display"""
    dt = parse_datetime(dt_string)
    if dt:
        return dt.strftime('%b %d, %Y at %I:%M %p')
    return dt_string or ''


def get_sort_datetime(date_str, time_str=None, created_at=None):
    """Get a datetime object for sorting"""
    # Try combining date and time
    if date_str and time_str:
        combined = f"{date_str} {time_str}"
        dt = parse_datetime(combined)
        if dt:
            return dt
    
    # Try just the date
    if date_str:
        dt = parse_datetime(date_str)
        if dt:
            return dt
    
    # Fall back to created_at
    if created_at:
        dt = parse_datetime(created_at)
        if dt:
            return dt
    
    # Default to epoch
    return datetime(1970, 1, 1)


def get_all_cat_photos(cat_id):
    """
    Get all photos for a cat from both:
    - cat_photos table (manually uploaded old photos)
    - sightings table (photos taken during sightings)
    
    Returns them combined and sorted by date (newest first)
    """
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
            photo_time,
            created_at,
            NULL as location,
            NULL as notes
        FROM cat_photos 
        WHERE cat_id = ?
    ''', (cat_id,)).fetchall()
    
    # Get sighting photos (only those with images)
    sighting_photos = db.execute('''
        SELECT 
            id,
            'sighting' as source,
            image_data,
            image_type,
            notes as caption,
            date as photo_date,
            NULL as photo_time,
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
        photo['sort_datetime'] = get_sort_datetime(p['photo_date'], p['photo_time'], p['created_at'])
        photo['display_date'] = format_date(p['photo_date']) if p['photo_date'] else format_date(p['created_at'])
        photo['display_time'] = format_time(f"2000-01-01 {p['photo_time']}") if p['photo_time'] else ''
        photo['display_datetime'] = format_datetime_full(p['photo_date'] + ' ' + p['photo_time']) if p['photo_date'] and p['photo_time'] else format_date(p['photo_date']) if p['photo_date'] else format_date(p['created_at'])
        all_photos.append(photo)
    
    for p in sighting_photos:
        photo = dict(p)
        photo['image_src'] = get_image_src(p['image_data'], p['image_type'])
        photo['sort_datetime'] = get_sort_datetime(p['photo_date'], None, p['created_at'])
        photo['display_date'] = format_date(p['photo_date'])
        photo['display_time'] = format_time(p['photo_date'])
        photo['display_datetime'] = format_datetime_full(p['photo_date'])
        all_photos.append(photo)
    
    # Sort by datetime (newest first)
    all_photos.sort(key=lambda x: x['sort_datetime'], reverse=True)
    
    return all_photos


# ============== ROUTES ==============

@app.route('/')
def home():
    db = get_db()
    
    cats = db.execute('SELECT * FROM cats ORDER BY name').fetchall()
    
    today = datetime.now().strftime('%Y-%m-%d')
    sightings = db.execute('''
        SELECT sightings.*, cats.name as cat_name, 
               cats.image_data as cat_image_data, 
               cats.image_type as cat_image_type
        FROM sightings 
        JOIN cats ON sightings.cat_id = cats.id
        WHERE DATE(sightings.date) = ?
        ORDER BY sightings.date DESC
    ''', (today,)).fetchall()
    
    seen_cat_ids = [s['cat_id'] for s in sightings]
    
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
        s_dict['display_time'] = format_time(s['date'])
        sightings_with_images.append(s_dict)
    
    return render_template('home.html',
                           cats=cats_with_images,
                           sightings=sightings_with_images,
                           seen_cat_ids=seen_cat_ids,
                           today=datetime.now().strftime('%A, %B %d, %Y'))


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
            'INSERT INTO sightings (cat_id, location, notes, image_data, image_type) VALUES (?, ?, ?, ?, ?)',
            (cat_id, location, notes, image_data, image_type)
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
            db.execute('INSERT INTO cats (name) VALUES (?)', (name,))
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
        
        # Get total photo count (gallery + sighting photos)
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
            'INSERT INTO cats (name, description, image_data, image_type) VALUES (?, ?, ?, ?)',
            (name, description, image_data, image_type)
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
    
    # Get sightings (for timeline view)
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
        s_dict['display_date'] = format_date(s['date'])
        s_dict['display_time'] = format_time(s['date'])
        sightings_with_images.append(s_dict)
    
    sighting_count = db.execute(
        'SELECT COUNT(*) as count FROM sightings WHERE cat_id = ?',
        (cat_id,)
    ).fetchone()['count']
    
    # Get ALL photos (gallery + sighting photos combined)
    all_photos = get_all_cat_photos(cat_id)
    
    # Get last seen
    last_sighting = db.execute(
        'SELECT date FROM sightings WHERE cat_id = ? ORDER BY date DESC LIMIT 1',
        (cat_id,)
    ).fetchone()
    last_seen = format_datetime_full(last_sighting['date']) if last_sighting else 'Never'
    
    return render_template('cat_detail.html',
                           cat=cat_dict,
                           sightings=sightings_with_images,
                           sighting_count=sighting_count,
                           photos=all_photos,
                           last_seen=last_seen)


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
    """Remove the profile photo from a cat"""
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
    """Add one or multiple photos to cat's gallery"""
    db = get_db()
    
    # Check if cat exists
    cat = db.execute('SELECT * FROM cats WHERE id = ?', (cat_id,)).fetchone()
    if not cat:
        return redirect(url_for('cats_list'))
    
    caption = request.form.get('caption', '').strip()
    photo_date = request.form.get('photo_date', '').strip()
    photo_time = request.form.get('photo_time', '').strip()
    
    # Handle multiple file uploads
    if 'photos' in request.files:
        files = request.files.getlist('photos')
        
        for file in files:
            if file and file.filename:
                image_data, image_type = file_to_base64(file)
                if image_data:
                    db.execute('''
                        INSERT INTO cat_photos (cat_id, image_data, image_type, caption, photo_date, photo_time)
                        VALUES (?, ?, ?, ?, ?, ?)
                    ''', (cat_id, image_data, image_type, caption, photo_date or None, photo_time or None))
    
    db.commit()
    return redirect(url_for('view_cat', cat_id=cat_id))


@app.route('/cats/<int:cat_id>/photos/<source>/<int:photo_id>/delete', methods=['POST'])
def delete_cat_photo(cat_id, source, photo_id):
    """Delete a photo from gallery or sighting"""
    db = get_db()
    
    if source == 'gallery':
        db.execute('DELETE FROM cat_photos WHERE id = ? AND cat_id = ?', (photo_id, cat_id))
    elif source == 'sighting':
        # For sighting photos, just remove the image, keep the sighting record
        db.execute('UPDATE sightings SET image_data = NULL, image_type = NULL WHERE id = ? AND cat_id = ?', (photo_id, cat_id))
    
    db.commit()
    return redirect(url_for('view_cat', cat_id=cat_id))


@app.route('/cats/<int:cat_id>/photos/<source>/<int:photo_id>/set-profile', methods=['POST'])
def set_profile_photo(cat_id, source, photo_id):
    """Set a gallery or sighting photo as the cat's main profile photo"""
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


@app.route('/cats/<int:cat_id>/photos/<int:photo_id>/edit', methods=['POST'])
def edit_cat_photo(cat_id, photo_id):
    """Edit photo caption and date (gallery photos only)"""
    caption = request.form.get('caption', '').strip()
    photo_date = request.form.get('photo_date', '').strip()
    photo_time = request.form.get('photo_time', '').strip()
    
    db = get_db()
    db.execute('''
        UPDATE cat_photos 
        SET caption = ?, photo_date = ?, photo_time = ?
        WHERE id = ? AND cat_id = ?
    ''', (caption, photo_date or None, photo_time or None, photo_id, cat_id))
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
    
    grouped = {}
    for sighting in sightings:
        dt = parse_datetime(sighting['date'])
        if dt:
            date_str = dt.strftime('%A, %B %d, %Y')
        else:
            date_str = 'Unknown Date'
        
        if date_str not in grouped:
            grouped[date_str] = []
        
        s_dict = dict(sighting)
        s_dict['cat_image_src'] = get_image_src(sighting['cat_image_data'], sighting['cat_image_type'])
        s_dict['sighting_image_src'] = get_image_src(sighting['image_data'], sighting['image_type'])
        s_dict['display_time'] = format_time(sighting['date'])
        grouped[date_str].append(s_dict)
    
    total_count = db.execute('SELECT COUNT(*) as count FROM sightings').fetchone()['count']
    
    return render_template('history.html', grouped_sightings=grouped, total=total_count)


if __name__ == '__main__':
    app.run(debug=True, port=5000)