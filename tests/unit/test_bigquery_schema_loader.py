"""Unit tests for the BigQuery schema loader."""
from __future__ import annotations

import json
from datetime import datetime, timezone

import pytest

from src.bigquery.schema_loader import (
    BQField,
    TableSchema,
    load_dataset_schema,
    resolve_table_ref,
    schema_from_db_row,
)


class TestBQField:
    def test_from_bq_api_basic(self):
        raw = {"name": "user_id", "type": "STRING", "mode": "REQUIRED"}
        f = BQField.from_bq_api(raw)
        assert f.name == "user_id"
        assert f.field_type == "STRING"
        assert f.mode == "REQUIRED"
        assert f.description == ""
        assert f.policy_tags == []

    def test_from_bq_api_with_policy_tags(self):
        raw = {
            "name": "ssn",
            "type": "STRING",
            "mode": "REQUIRED",
            "description": "Social security number",
            "policyTags": {"names": ["pii"]},
            "maxLength": 9,
        }
        f = BQField.from_bq_api(raw)
        assert f.name == "ssn"
        assert f.field_type == "STRING"
        assert f.description == "Social security number"
        assert f.policy_tags == ["pii"]
        assert f.max_length == 9

    def test_to_dict_roundtrip(self):
        raw = {"name": "created_at", "type": "TIMESTAMP", "mode": "NULLABLE"}
        f = BQField.from_bq_api(raw)
        assert f.to_dict() == {
            "name": "created_at",
            "type": "TIMESTAMP",
            "mode": "NULLABLE",
            "description": "",
            "policy_tags": [],
            "max_length": None,
        }


class TestTableSchema:
    def test_table_ref(self):
        s = TableSchema(project="my-project", dataset="analytics", table="events")
        assert s.table_ref == "my-project.analytics.events"

    def test_schema_hash_stable(self):
        s1 = TableSchema(
            project="p", dataset="d", table="t",
            fields=[BQField(name="x", field_type="INTEGER")],
        )
        s2 = TableSchema(
            project="p", dataset="d", table="t",
            fields=[BQField(name="x", field_type="INTEGER")],
        )
        assert s1.schema_hash == s2.schema_hash

    def test_schema_hash_changes_on_field(self):
        s1 = TableSchema(
            project="p", dataset="d", table="t",
            fields=[BQField(name="x", field_type="INTEGER")],
        )
        s2 = TableSchema(
            project="p", dataset="d", table="t",
            fields=[BQField(name="x", field_type="FLOAT")],
        )
        assert s1.schema_hash != s2.schema_hash

    def test_has_field(self):
        s = TableSchema(
            project="p", dataset="d", table="t",
            fields=[BQField(name="user_id", field_type="STRING")],
        )
        assert s.has_field("user_id") is True
        assert s.has_field("missing") is False

    def test_is_temporal(self):
        s = TableSchema(
            project="p", dataset="d", table="t",
            fields=[BQField(name="ts", field_type="TIMESTAMP")],
        )
        assert s.is_temporal() is True

    def test_is_not_temporal(self):
        s = TableSchema(
            project="p", dataset="d", table="t",
            fields=[BQField(name="x", field_type="INTEGER")],
        )
        assert s.is_temporal() is False

    def test_to_dict_roundtrip(self):
        s = TableSchema(
            project="p", dataset="d", table="t",
            fields=[BQField(name="x", field_type="INTEGER")],
            description="test table",
            labels={"env": "prod"},
            partition_enabled=True,
            clustering_enabled=True,
            clustering_fields=["user_id"],
        )
        d = s.to_dict()
        assert d["project"] == "p"
        assert d["partition_enabled"] is True
        assert d["clustering_enabled"] is True
        assert d["clustering_fields"] == ["user_id"]

    def test_to_json(self):
        s = TableSchema(project="p", dataset="d", table="t")
        loaded = json.loads(s.to_json())
        assert loaded["project"] == "p"


class TestResolveTableRef:
    def test_resolve_with_explicit_project(self):
        ref = resolve_table_ref("explicit-project", "dataset", "table")
        assert ref == "explicit-project.dataset.table"

    def test_resolve_without_project_uses_default(self, monkeypatch):
        monkeypatch.setattr("src.bigquery.schema_loader.settings.GCP_PROJECT_ID", "default-proj")
        ref = resolve_table_ref(None, "dataset", "table")
        assert ref == "default-proj.dataset.table"


class TestSchemaFromDbRow:
    def test_roundtrip(self):
        raw = {
            "project": "my-project",
            "dataset": "my-dataset",
            "table": "my-table",
            "fields": [
                {"name": "user_id", "type": "STRING", "mode": "REQUIRED"},
                {"name": "revenue", "type": "FLOAT", "mode": "NULLABLE"},
            ],
            "description": "Revenue table",
            "partition_enabled": True,
            "clustering_fields": ["user_id"],
        }
        s = schema_from_db_row(raw)
        assert s.project == "my-project"
        assert len(s.fields) == 2
        assert s.partition_enabled is True
        assert s.clustering_fields == ["user_id"]


@pytest.mark.asyncio
class TestLoadDatasetSchema:
    async def test_load_fallback_when_not_live(self, monkeypatch):
        """When BigQuery is not live, load_dataset_schema returns an empty schema."""
        from src.bigquery import schema_loader

        class FakeBQ:
            is_live = False

            async def get_dataset_schema(self, dataset, table):
                return {"fields": [], "live": False}

        monkeypatch.setattr(schema_loader, "get_bigquery_client", lambda: FakeBQ())

        s = await load_dataset_schema("p", "d", "t")
        assert s.project == "p"
        assert s.fields == []
        assert s.partition_enabled is False
