"""Jalankan: python buat_password.py
Lalu salin hash-nya ke environment variable ADMIN_PASSWORD_HASH."""
import getpass
from werkzeug.security import generate_password_hash

pw = getpass.getpass('Password admin baru: ')
if len(pw) < 8:
    raise SystemExit('Minimal 8 karakter.')
print('\nADMIN_PASSWORD_HASH=' + generate_password_hash(pw))
