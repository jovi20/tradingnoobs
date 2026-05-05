import os
import tempfile
import unittest
from datetime import datetime, timezone

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from database import Base
from models import FeatureFlag
from services.platform_config_service import get_feature_flag_enabled


class PlatformConfigServiceTests(unittest.TestCase):
    def setUp(self):
        fd, self.db_path = tempfile.mkstemp(suffix=".db")
        os.close(fd)
        self.engine = create_engine(
            f"sqlite:///{self.db_path}",
            connect_args={"check_same_thread": False},
        )
        self.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)
        Base.metadata.create_all(bind=self.engine)
        self.db = self.SessionLocal()

    def tearDown(self):
        self.db.close()
        self.engine.dispose()
        if os.path.exists(self.db_path):
            os.remove(self.db_path)

    def test_feature_flag_enabled_returns_false_for_absent_disabled_and_expired_flags(self):
        self.assertFalse(get_feature_flag_enabled(self.db, "missing_flag"))

        self.db.add(FeatureFlag(key="disabled_flag", enabled=False))
        self.db.add(
            FeatureFlag(
                key="expired_flag",
                enabled=True,
                expires_at=datetime(2000, 1, 1, tzinfo=timezone.utc),
            )
        )
        self.db.commit()

        self.assertFalse(get_feature_flag_enabled(self.db, "disabled_flag"))
        self.assertFalse(get_feature_flag_enabled(self.db, "expired_flag"))

    def test_feature_flag_enabled_returns_true_for_unexpired_enabled_flag(self):
        self.db.add(
            FeatureFlag(
                key="active_flag",
                enabled=True,
                expires_at=datetime(2999, 1, 1, tzinfo=timezone.utc),
            )
        )
        self.db.commit()

        self.assertTrue(get_feature_flag_enabled(self.db, "active_flag"))

    def test_feature_flag_enabled_respects_actor_targets_when_present(self):
        self.db.add(
            FeatureFlag(
                key="targeted_flag",
                enabled=True,
                actor_targets=["user-public-id"],
            )
        )
        self.db.commit()

        self.assertTrue(get_feature_flag_enabled(self.db, "targeted_flag", actor_key="user-public-id"))
        self.assertFalse(get_feature_flag_enabled(self.db, "targeted_flag", actor_key="other-user"))
        self.assertFalse(get_feature_flag_enabled(self.db, "targeted_flag"))


if __name__ == "__main__":
    unittest.main()
