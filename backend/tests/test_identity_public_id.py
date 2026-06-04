from services.identity_service import generate_public_id, normalize_email


def test_generate_public_id_returns_26_character_ulid():
    public_id = generate_public_id()

    assert len(public_id) == 26
    assert public_id == public_id.upper()


def test_normalize_email_trims_and_lowercases():
    assert normalize_email("  Trader@Example.COM ") == "trader@example.com"
