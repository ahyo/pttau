from passlib.hash import bcrypt

def verify_password(plain: str, hashed: str) -> bool:
    try:
        return bcrypt.verify(plain, hashed)
    except Exception:
        return False

def get_session_admin(request):
    return request.session.get("admin")
