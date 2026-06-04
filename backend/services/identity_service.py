import ulid


def generate_public_id() -> str:
    return str(ulid.new())


def normalize_email(email: str) -> str:
    return email.strip().lower()
