"""
Password hashing utilities using passlib + bcrypt.

Design decision: bcrypt_sha256 is used instead of plain bcrypt because it
pre-hashes the password with SHA-256, avoiding bcrypt's 72-byte input limit.
The "deprecated=auto" flag automatically rehashes passwords stored with
older (weaker) schemes on next verification.
"""
from passlib.context import CryptContext

# CryptContext manages the hashing scheme lifecycle — it can transparently
# upgrade old hashes to the current scheme during verify_password().
pwd_context = CryptContext(
    schemes=["bcrypt_sha256"],
    deprecated="auto"
)


def hash_password(password: str) -> str:
    """Hash a plaintext password for storage.

    Args:
        password: The user's plaintext password.

    Returns:
        A bcrypt_sha256 hash string safe to store in the database.
    """
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a plaintext password against a stored hash.

    Args:
        plain_password: The password the user just typed.
        hashed_password: The hash stored in the database.

    Returns:
        True if the password matches, False otherwise.
    """
    return pwd_context.verify(plain_password, hashed_password)
