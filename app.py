import os
import re
import secrets
import sqlite3
import time
from functools import wraps

from flask import (Flask, abort, flash, redirect, render_template, request,
                   session, url_for)
from werkzeug.security import check_password_hash, generate_password_hash

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, 'les_privat.db')

app = Flask(__name__)


# ==========================================
# KONFIGURASI & KEAMANAN
# ==========================================
def _load_secret_key():
    """Ambil SECRET_KEY dari environment; kalau tidak ada, buat sekali lalu simpan
    di file .secret_key supaya sesi login tidak hilang tiap server restart."""
    env_key = os.environ.get('SECRET_KEY')
    if env_key:
        return env_key
    key_file = os.path.join(BASE_DIR, '.secret_key')
    if os.path.exists(key_file):
        with open(key_file) as f:
            return f.read().strip()
    key = secrets.token_hex(32)
    with open(key_file, 'w') as f:
        f.write(key)
    return key


app.secret_key = _load_secret_key()
app.config.update(
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE='Lax',
    # Aktifkan lewat env SESSION_COOKIE_SECURE=1 saat sudah pakai HTTPS
    SESSION_COOKIE_SECURE=os.environ.get('SESSION_COOKIE_SECURE') == '1',
)

ADMIN_USERNAME = os.environ.get('ADMIN_USERNAME', 'admin')
_env_hash = os.environ.get('ADMIN_PASSWORD_HASH')
if _env_hash:
    ADMIN_PASSWORD_HASH = _env_hash
else:
    # Fallback agar app tetap jalan di lokal. WAJIB diganti sebelum online!
    ADMIN_PASSWORD_HASH = generate_password_hash('admin123')
    print('\n[PERINGATAN] ADMIN_PASSWORD_HASH belum di-set. Memakai password '
          'bawaan "admin123". Lihat README_KEAMANAN.md untuk menggantinya.\n')

# Pembatasan percobaan login (anti tebak password), disimpan di memori
MAX_GAGAL = 5
BLOKIR_DETIK = 300
_gagal_login = {}


def login_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if not session.get('logged_in'):
            return redirect(url_for('login'))
        return view(*args, **kwargs)
    return wrapped


@app.before_request
def cek_csrf():
    """Semua request POST wajib membawa token CSRF yang cocok dengan sesi."""
    if request.method == 'POST':
        token = session.get('_csrf')
        if not token or token != request.form.get('_csrf'):
            abort(400, 'Sesi formulir kedaluwarsa. Silakan muat ulang halaman dan coba lagi.')


@app.context_processor
def inject_csrf():
    if '_csrf' not in session:
        session['_csrf'] = secrets.token_hex(16)
    return {'csrf_token': session['_csrf']}


# ==========================================
# DATA BIMBEL (ubah di sini, otomatis berubah di seluruh website)
# ==========================================
BIMBEL = {
    'nama': 'Bimbel Ruang Ilmu',
    'wa_admin': '6282223533663',          # format 62..., tanpa + atau spasi
    'wa_tampil': '0822-2353-3663',
    'harga': 45000,                       # per pertemuan
    'durasi_menit': 90,
    'jenjang': 'SD (Kelas 1-6)',
    'lokasi': 'Kotagede, Yogyakarta',
    # Ubah ke True setelah punya testimoni ASLI dari orang tua (isi di index.html)
    'tampilkan_testimoni': False,
}


@app.context_processor
def inject_bimbel():
    return {'bimbel': BIMBEL}


@app.template_filter('rupiah')
def rupiah(n):
    return 'Rp' + f'{int(n):,}'.replace(',', '.')


# ==========================================
# DATABASE
# ==========================================
def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute('PRAGMA foreign_keys = ON')
    return conn


def normalisasi_wa(nomor):
    """Ubah berbagai format nomor ke 62xxxxxxxxxx. Return None kalau tidak valid.
    Contoh: '0812-3456-789', '+62 812 3456 789', '62812...', '812...' -> '62812...'"""
    if not nomor:
        return None
    digit = re.sub(r'\D', '', nomor)
    if digit.startswith('0'):
        digit = '62' + digit[1:]
    elif digit.startswith('8'):
        digit = '62' + digit
    if not digit.startswith('62') or not 10 <= len(digit) <= 15:
        return None
    return digit


def init_db():
    conn = get_db_connection()
    conn.execute('CREATE TABLE IF NOT EXISTS Siswa (id_siswa INTEGER PRIMARY KEY AUTOINCREMENT, nama_siswa TEXT, nama_ortu TEXT, nomor_wa TEXT, asal_sekolah TEXT, kelas TEXT, alamat TEXT, target_belajar TEXT)')
    conn.execute('CREATE TABLE IF NOT EXISTS Jadwal (id_jadwal INTEGER PRIMARY KEY AUTOINCREMENT, id_siswa INTEGER, tanggal_les TEXT, jam_mulai TEXT, jam_selesai TEXT, status TEXT, status_pembayaran TEXT, FOREIGN KEY (id_siswa) REFERENCES Siswa (id_siswa))')
    conn.execute('CREATE TABLE IF NOT EXISTS Laporan_Belajar (id_laporan INTEGER PRIMARY KEY AUTOINCREMENT, id_jadwal INTEGER, materi TEXT, status_tujuan TEXT, catatan_bimbingan TEXT, FOREIGN KEY (id_jadwal) REFERENCES Jadwal (id_jadwal))')

    # Migrasi satu kali: seragamkan nomor WA lama (mis. 0812... -> 62812...)
    for row in conn.execute('SELECT id_siswa, nomor_wa FROM Siswa').fetchall():
        baru = normalisasi_wa(row['nomor_wa'])
        if baru and baru != row['nomor_wa']:
            conn.execute('UPDATE Siswa SET nomor_wa = ? WHERE id_siswa = ?', (baru, row['id_siswa']))
    conn.commit()
    conn.close()


init_db()


# ==========================================
# 1. RUTE PUBLIK
# ==========================================
@app.route('/', methods=('GET', 'POST'))
def landing_page():
    if request.method == 'POST':
        data = {k: request.form.get(k, '').strip() for k in
                ('nama_siswa', 'nama_ortu', 'nomor_wa', 'asal_sekolah', 'kelas', 'alamat', 'target_belajar')}

        nomor_wa = normalisasi_wa(data['nomor_wa'])
        if not nomor_wa:
            return render_template('index.html', form=data,
                                   error='Nomor WhatsApp tidak valid. Contoh: 0812 3456 7890')
        if not all(data[k] for k in ('nama_siswa', 'nama_ortu', 'asal_sekolah', 'kelas', 'alamat')):
            return render_template('index.html', form=data, error='Mohon lengkapi semua kolom yang wajib diisi.')

        conn = get_db_connection()
        conn.execute('''
            INSERT INTO Siswa (nama_siswa, nama_ortu, nomor_wa, asal_sekolah, kelas, alamat, target_belajar)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (data['nama_siswa'], data['nama_ortu'], nomor_wa, data['asal_sekolah'],
              data['kelas'], data['alamat'], data['target_belajar']))
        conn.commit()
        conn.close()
        return render_template('sukses.html', nama_siswa=data['nama_siswa'])

    return render_template('index.html', form={}, error=None)


@app.route('/portal', methods=('GET', 'POST'))
def portal():
    siswa = None
    laporan = None
    error = None
    if request.method == 'POST':
        nomor_wa = normalisasi_wa(request.form.get('nomor_wa', ''))
        if not nomor_wa:
            error = 'Format nomor WhatsApp tidak valid.'
        else:
            conn = get_db_connection()
            siswa = conn.execute('SELECT * FROM Siswa WHERE nomor_wa = ?', (nomor_wa,)).fetchone()
            if siswa:
                laporan = conn.execute(
                    'SELECT Laporan_Belajar.*, Jadwal.tanggal_les FROM Laporan_Belajar '
                    'JOIN Jadwal ON Laporan_Belajar.id_jadwal = Jadwal.id_jadwal '
                    'WHERE Jadwal.id_siswa = ? ORDER BY Jadwal.tanggal_les DESC', (siswa['id_siswa'],)).fetchall()
            else:
                error = 'Nomor tersebut belum terdaftar. Pastikan memakai nomor yang sama saat mendaftar.'
            conn.close()
    return render_template('portal.html', siswa=siswa, laporan=laporan, error=error)


# ==========================================
# 2. AUTENTIKASI ADMIN
# ==========================================
@app.route('/login', methods=['GET', 'POST'])
def login():
    error = None
    ip = request.remote_addr or 'unknown'
    if request.method == 'POST':
        gagal, sampai = _gagal_login.get(ip, (0, 0))
        if gagal >= MAX_GAGAL and time.time() >= sampai:
            gagal = 0                    # masa blokir sudah lewat
        if gagal >= MAX_GAGAL:
            sisa = int((sampai - time.time()) // 60) + 1
            return render_template('login.html', error=f'Terlalu banyak percobaan. Coba lagi dalam {sisa} menit.')

        username_ok = secrets.compare_digest(request.form.get('username', ''), ADMIN_USERNAME)
        password_ok = check_password_hash(ADMIN_PASSWORD_HASH, request.form.get('password', ''))
        if username_ok and password_ok:
            _gagal_login.pop(ip, None)
            csrf = session.get('_csrf')
            session.clear()              # cegah session fixation
            session['_csrf'] = csrf or secrets.token_hex(16)
            session['logged_in'] = True
            return redirect(url_for('admin_dashboard'))

        _gagal_login[ip] = (gagal + 1, time.time() + BLOKIR_DETIK)
        error = 'Username atau password salah.'
    return render_template('login.html', error=error)


@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('landing_page'))


# ==========================================
# 3. RUTE ADMIN (semua wajib login)
# ==========================================
@app.route('/admin')
@login_required
def admin_dashboard():
    conn = get_db_connection()
    siswa = conn.execute('SELECT * FROM Siswa').fetchall()
    jadwal = conn.execute('SELECT Jadwal.*, Siswa.nama_siswa, Siswa.nomor_wa FROM Jadwal JOIN Siswa ON Jadwal.id_siswa = Siswa.id_siswa ORDER BY Jadwal.tanggal_les ASC').fetchall()
    conn.close()
    return render_template('admin.html', siswa=siswa, jadwal=jadwal)


@app.route('/tambah_siswa', methods=('GET', 'POST'))
@login_required
def tambah_siswa():
    if request.method == 'POST':
        data = {k: request.form.get(k, '').strip() for k in
                ('nama_siswa', 'nama_ortu', 'nomor_wa', 'asal_sekolah', 'kelas', 'alamat', 'target_belajar')}
        nomor_wa = normalisasi_wa(data['nomor_wa'])
        if not nomor_wa:
            return render_template('tambah_siswa.html', form=data, error='Nomor WhatsApp tidak valid. Contoh: 0812 3456 7890')
        conn = get_db_connection()
        conn.execute('''
            INSERT INTO Siswa (nama_siswa, nama_ortu, nomor_wa, asal_sekolah, kelas, alamat, target_belajar)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (data['nama_siswa'], data['nama_ortu'], nomor_wa, data['asal_sekolah'],
              data['kelas'], data['alamat'], data['target_belajar']))
        conn.commit()
        conn.close()
        return redirect(url_for('admin_dashboard'))
    return render_template('tambah_siswa.html', form={}, error=None)


@app.route('/bayar_lunas/<int:id_jadwal>', methods=['POST'])
@login_required
def bayar_lunas(id_jadwal):
    conn = get_db_connection()
    conn.execute('UPDATE Jadwal SET status_pembayaran = "Lunas" WHERE id_jadwal = ?', (id_jadwal,))
    conn.commit()
    conn.close()
    return redirect(url_for('admin_dashboard'))


@app.route('/booking', methods=('GET', 'POST'))
@login_required
def booking():
    conn = get_db_connection()
    siswa = conn.execute('SELECT id_siswa, nama_siswa FROM Siswa').fetchall()
    if request.method == 'POST':
        jam_mulai = request.form.get('jam_mulai', '')
        jam_selesai = request.form.get('jam_selesai', '')
        if jam_selesai <= jam_mulai:
            conn.close()
            return render_template('booking.html', siswa=siswa, error='Jam selesai harus lebih besar dari jam mulai.')
        conn.execute('INSERT INTO Jadwal (id_siswa, tanggal_les, jam_mulai, jam_selesai, status, status_pembayaran) VALUES (?, ?, ?, ?, "Booking", "Belum Lunas")',
                     (request.form['id_siswa'], request.form['tanggal_les'], jam_mulai, jam_selesai))
        conn.commit()
        conn.close()
        return redirect(url_for('admin_dashboard'))
    conn.close()
    return render_template('booking.html', siswa=siswa, error=None)


@app.route('/buat_laporan/<int:id_jadwal>', methods=('GET', 'POST'))
@login_required
def buat_laporan(id_jadwal):
    conn = get_db_connection()
    jadwal = conn.execute('SELECT Jadwal.*, Siswa.nama_siswa FROM Jadwal JOIN Siswa ON Jadwal.id_siswa = Siswa.id_siswa WHERE Jadwal.id_jadwal = ?', (id_jadwal,)).fetchone()
    if jadwal is None:
        conn.close()
        abort(404)
    if request.method == 'POST':
        conn.execute('INSERT INTO Laporan_Belajar (id_jadwal, materi, status_tujuan, catatan_bimbingan) VALUES (?, ?, ?, ?)',
                     (id_jadwal, request.form['materi'], request.form['status_tujuan'], request.form.get('catatan_bimbingan', '')))
        conn.execute('UPDATE Jadwal SET status = "Selesai" WHERE id_jadwal = ?', (id_jadwal,))
        conn.commit()
        conn.close()
        return redirect(url_for('admin_dashboard'))
    conn.close()
    return render_template('buat_laporan.html', jadwal=jadwal)


@app.route('/hapus_jadwal/<int:id_jadwal>', methods=['POST'])
@login_required
def hapus_jadwal(id_jadwal):
    conn = get_db_connection()
    # Hapus laporan terkait agar tidak ada data yatim
    conn.execute('DELETE FROM Laporan_Belajar WHERE id_jadwal = ?', (id_jadwal,))
    conn.execute('DELETE FROM Jadwal WHERE id_jadwal = ?', (id_jadwal,))
    conn.commit()
    conn.close()
    return redirect(url_for('admin_dashboard'))


if __name__ == '__main__':
    app.run(debug=os.environ.get('FLASK_DEBUG') == '1')
