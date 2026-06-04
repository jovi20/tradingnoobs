from datetime import timezone

from models import DashboardCache, PositionMetric
from services.identity_service import generate_public_id


class DerivedReadModelService:
    def __init__(self, db_session):
        self.db = db_session

    def store_dashboard_cache(self, *, user_id: int, cache_key: str, payload: dict, as_of, freshness: str) -> DashboardCache:
        cache = self.db.query(DashboardCache).filter_by(user_id=user_id, cache_key=cache_key).one_or_none()
        if not cache:
            cache = DashboardCache(
                public_id=generate_public_id(),
                user_id=user_id,
                cache_key=cache_key,
                payload=payload,
                as_of=as_of,
                freshness=freshness,
                source="DERIVED",
            )
            self.db.add(cache)
        else:
            cache.payload = payload
            cache.as_of = as_of
            cache.freshness = freshness
            cache.source = "DERIVED"
        self.db.flush()
        return cache

    def get_dashboard_cache(self, *, user_id: int, cache_key: str) -> dict | None:
        cache = self.db.query(DashboardCache).filter_by(user_id=user_id, cache_key=cache_key).one_or_none()
        if not cache:
            return None
        return self._wrap_payload(payload=cache.payload, as_of=cache.as_of, freshness=cache.freshness, source=cache.source)

    def store_position_metric(
        self,
        *,
        position_public_id: str,
        metric_key: str,
        payload: dict,
        as_of,
        freshness: str,
    ) -> PositionMetric:
        metric = (
            self.db.query(PositionMetric)
            .filter_by(position_public_id=position_public_id, metric_key=metric_key)
            .one_or_none()
        )
        if not metric:
            metric = PositionMetric(
                public_id=generate_public_id(),
                position_public_id=position_public_id,
                metric_key=metric_key,
                payload=payload,
                as_of=as_of,
                freshness=freshness,
                source="DERIVED",
            )
            self.db.add(metric)
        else:
            metric.payload = payload
            metric.as_of = as_of
            metric.freshness = freshness
            metric.source = "DERIVED"
        self.db.flush()
        return metric

    def get_position_metric(self, *, position_public_id: str, metric_key: str) -> dict | None:
        metric = (
            self.db.query(PositionMetric)
            .filter_by(position_public_id=position_public_id, metric_key=metric_key)
            .one_or_none()
        )
        if not metric:
            return None
        return self._wrap_payload(payload=metric.payload, as_of=metric.as_of, freshness=metric.freshness, source=metric.source)

    @classmethod
    def _wrap_payload(cls, *, payload: dict, as_of, freshness: str, source: str) -> dict:
        return {
            "payload": payload,
            "meta": {
                "as_of": cls._isoformat(as_of),
                "freshness": freshness,
                "source": source,
                "maturity": "DERIVED",
                "value_status": "FINAL",
                "generated_by": "derived_read_model_service",
                "source_refs": [],
            },
        }

    @staticmethod
    def _isoformat(value) -> str:
        if value.tzinfo is None:
            value = value.replace(tzinfo=timezone.utc)
        return value.isoformat()
