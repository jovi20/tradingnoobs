import unittest


from app_bootstrap import bootstrap_schema_if_enabled, resolve_auto_create_schema_enabled


class DummyMetadata:
    def __init__(self):
        self.called_with = None

    def create_all(self, bind=None):
        self.called_with = bind


class SchemaBootstrapTests(unittest.TestCase):
    def test_resolve_auto_create_schema_defaults_off_in_production(self):
        self.assertFalse(resolve_auto_create_schema_enabled("production", None))

    def test_resolve_auto_create_schema_defaults_on_in_development(self):
        self.assertTrue(resolve_auto_create_schema_enabled("development", None))

    def test_resolve_auto_create_schema_honors_explicit_override(self):
        self.assertTrue(resolve_auto_create_schema_enabled("production", True))
        self.assertFalse(resolve_auto_create_schema_enabled("development", False))

    def test_bootstrap_schema_calls_create_all_when_enabled(self):
        metadata = DummyMetadata()
        engine = object()

        bootstrap_schema_if_enabled(metadata=metadata, engine=engine, enabled=True)

        self.assertIs(metadata.called_with, engine)

    def test_bootstrap_schema_skips_create_all_when_disabled(self):
        metadata = DummyMetadata()
        engine = object()

        bootstrap_schema_if_enabled(metadata=metadata, engine=engine, enabled=False)

        self.assertIsNone(metadata.called_with)


if __name__ == "__main__":
    unittest.main()
