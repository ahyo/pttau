from passlib.context import CryptContext


password_context = CryptContext(
    schemes=["pbkdf2_sha256", "bcrypt"],
    default="pbkdf2_sha256",
    deprecated="auto",
)


def verify_password(plain: str, hashed: str) -> bool:
    try:
        return password_context.verify(plain, hashed)
    except Exception:
        return False


def hash_password(password: str) -> str:
    return password_context.hash(password)


def get_session_admin(request):
    return request.session.get("admin")
