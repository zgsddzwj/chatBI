from dataclasses import asdict

from app.entities.column_metric import ColumnMetric
from app.models_meta import ColumnMetricMySQL


class ColumnMetricMapper:
    @staticmethod
    def to_entity(column_metric_mysql: ColumnMetricMySQL) -> ColumnMetric:
        return ColumnMetric(
            column_id=column_metric_mysql.column_id,
            metric_id=column_metric_mysql.metric_id,
        )

    @staticmethod
    def to_model(column_metric: ColumnMetric) -> ColumnMetricMySQL:
        return ColumnMetricMySQL(**asdict(column_metric))
