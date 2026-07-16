"""AIR on the lakehouse - land audit records as open-format tables.

The lake sink exports the gateway's chained .air.json records into a
date-partitioned Parquet dataset so agent audit data can live next to
business data in a lakehouse (Databricks, Iceberg/Delta catalogs, DuckDB,
plain object storage) and be queried with SQL.

Tamper-evidence survives the move: each row carries the record's exact
JSON (`record_json`) plus flattened columns for querying, and
`verify_lake` re-runs the same HMAC chain verification the replay engine
uses - directly over the table. The signing key never enters the lake.

Requires the optional dependency: pip install air-blackbox[lake]
"""

from air_blackbox.lake.writer import export_records
from air_blackbox.lake.verify import LakeVerification, verify_lake

__all__ = ["export_records", "verify_lake", "LakeVerification"]
