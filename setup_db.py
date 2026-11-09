"""Membuat database kosong. Skema sama persis dengan yang dipakai app.py.
(Sebenarnya app.py sudah membuat tabel otomatis saat dijalankan.)"""
import sqlite3

conn = sqlite3.connect('les_privat.db')
c = conn.cursor()

c.execute('''CREATE TABLE IF NOT EXISTS Siswa (
    id_siswa INTEGER PRIMARY KEY AUTOINCREMENT,
    nama_siswa TEXT NOT NULL,
    nama_ortu TEXT NOT NULL,
    nomor_wa TEXT NOT NULL,
    asal_sekolah TEXT NOT NULL,
    kelas TEXT NOT NULL,
    alamat TEXT NOT NULL,
    target_belajar TEXT
)''')

c.execute('''CREATE TABLE IF NOT EXISTS Jadwal (
    id_jadwal INTEGER PRIMARY KEY AUTOINCREMENT,
    id_siswa INTEGER,
    tanggal_les TEXT NOT NULL,
    jam_mulai TEXT NOT NULL,
    jam_selesai TEXT NOT NULL,
    status TEXT NOT NULL,
    status_pembayaran TEXT NOT NULL,
    FOREIGN KEY (id_siswa) REFERENCES Siswa (id_siswa)
)''')

c.execute('''CREATE TABLE IF NOT EXISTS Laporan_Belajar (
    id_laporan INTEGER PRIMARY KEY AUTOINCREMENT,
    id_jadwal INTEGER,
    materi TEXT NOT NULL,
    status_tujuan TEXT NOT NULL,
    catatan_bimbingan TEXT,
    FOREIGN KEY (id_jadwal) REFERENCES Jadwal (id_jadwal)
)''')

conn.commit()
conn.close()
print("Selesai! Database 'les_privat.db' siap digunakan.")
