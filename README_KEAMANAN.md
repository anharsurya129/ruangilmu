# Mengganti Password Admin (WAJIB sebelum website online)

1. Jalankan `python buat_password.py`, masukkan password baru.
2. Salin baris `ADMIN_PASSWORD_HASH=...` yang muncul.
3. Set sebagai environment variable sebelum menjalankan app.

Windows (CMD):
    set ADMIN_PASSWORD_HASH=pbkdf2:sha256:...
    set ADMIN_USERNAME=namaanda
    python app.py

Mac/Linux:
    export ADMIN_PASSWORD_HASH='pbkdf2:sha256:...'
    python app.py

Opsional:
- SECRET_KEY : kalau kosong, dibuat otomatis di file `.secret_key` (jangan dibagikan).
- SESSION_COOKIE_SECURE=1 : aktifkan saat sudah memakai HTTPS.
- FLASK_DEBUG=1 : HANYA untuk development di komputer sendiri.
