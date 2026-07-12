# Databricks notebook source
# MAGIC %md
# MAGIC # Verify the AIR Blackbox audit chain — in the lakehouse
# MAGIC
# MAGIC The AIR gateway records every LLM call as a tamper-evident, HMAC-chained
# MAGIC record. `air-blackbox lake export` lands those records as a Parquet
# MAGIC dataset. This notebook proves the chain **where the data lives**: no
# MAGIC AIR install required, just the rows and the signing key.
# MAGIC
# MAGIC - **Chain walk** (sequential by construction): recomputes every record's
# MAGIC   HMAC from `record_json`, ordered by `chain_seq`. Tampering with any
# MAGIC   record breaks every record after it.
# MAGIC - **Column consistency** (fully distributed): Spark SQL confirms the
# MAGIC   flattened analytics columns agree with the verified `record_json`.
# MAGIC
# MAGIC The verifier below is the reference implementation from
# MAGIC `docs/spec/audit-chain-v1.md` Section 6.2, byte-compatible with the Go
# MAGIC gateway's writer and the Python SDK's `verify_records`.

# COMMAND ----------

dbutils.widgets.text("lake_path", "/Volumes/main/default/air_lake", "AIR lake dataset path")
dbutils.widgets.text("signing_key_secret", "air/signing-key", "Secret scope/key for TRUST_SIGNING_KEY")

LAKE_PATH = dbutils.widgets.get("lake_path")
# Never hardcode the key in a notebook; pull it from a secret scope.
scope, key_name = dbutils.widgets.get("signing_key_secret").split("/", 1)
SIGNING_KEY = dbutils.secrets.get(scope, key_name).encode()

# COMMAND ----------

df = spark.read.parquet(LAKE_PATH)
df.createOrReplaceTempView("air_records")
display(spark.sql("""
    SELECT model, provider, count(*) AS calls, sum(tokens_total) AS tokens,
           avg(duration_ms) AS avg_ms
    FROM air_records GROUP BY model, provider ORDER BY calls DESC
"""))

# COMMAND ----------

# MAGIC %md ## 1. Chain walk (spec §6.2, verbatim)

# COMMAND ----------

import hashlib, hmac, json

def verify_chain(records, signing_key):
    errors, prev_digest, checked = [], b"genesis", 0
    for i, record in enumerate(records):
        stored_hash = record.get("chain_hash")
        if not stored_hash:
            continue  # unchained record: outside the chain
        record_copy = {k: v for k, v in record.items() if k != "chain_hash"}
        record_bytes = json.dumps(record_copy, sort_keys=True).encode("utf-8")
        h = hmac.new(signing_key, prev_digest + record_bytes, hashlib.sha256)
        if stored_hash != h.hexdigest():
            errors.append(f"Record {i} ({record['run_id']}): chain_hash mismatch. "
                          f"TAMPERING DETECTED (modified, deleted, or reordered).")
            break
        prev_digest = h.digest()
        checked += 1
    return {"valid": not errors, "events_checked": checked, "errors": errors}

# The walk is inherently sequential (each hash depends on the previous
# digest), so collect the payload column in chain order. One chain per
# gateway replica: for multi-replica lakes, group by replica first.
rows = (df.select("chain_seq", "timestamp", "record_json")
          .orderBy("chain_seq", "timestamp")
          .collect())
records = [json.loads(r.record_json) for r in rows]

result = verify_chain(records, SIGNING_KEY)
print(result)
assert result["valid"], "AUDIT CHAIN BROKEN - do not trust these records"

# COMMAND ----------

# MAGIC %md ## 2. Column consistency (distributed)
# MAGIC The SQL columns must agree with the verified `record_json` payload,
# MAGIC so neither layer can be edited independently.

# COMMAND ----------

mismatches = spark.sql("""
    SELECT run_id, 'model' AS column, model AS column_value,
           get_json_object(record_json, '$.model') AS record_value
    FROM air_records
    WHERE model != get_json_object(record_json, '$.model')
    UNION ALL
    SELECT run_id, 'tokens_total', cast(tokens_total AS string),
           get_json_object(record_json, '$.tokens.total')
    FROM air_records
    WHERE tokens_total != cast(get_json_object(record_json, '$.tokens.total') AS bigint)
    UNION ALL
    SELECT run_id, 'chain_seq', cast(chain_seq AS string),
           get_json_object(record_json, '$.chain_seq')
    FROM air_records
    WHERE chain_seq != cast(get_json_object(record_json, '$.chain_seq') AS bigint)
    UNION ALL
    SELECT run_id, 'status', status, get_json_object(record_json, '$.status')
    FROM air_records
    WHERE status != get_json_object(record_json, '$.status')
""")
n = mismatches.count()
display(mismatches) if n else print("All analytics columns agree with the verified payload.")
assert n == 0, f"{n} column(s) disagree with the verified record_json"

# COMMAND ----------

# MAGIC %md
# MAGIC ✅ **Both checks passed**: the audit trail in this table is complete,
# MAGIC ordered, and untampered — provable by anyone with the rows and the key,
# MAGIC on any engine. The signing key itself never enters the lake.
