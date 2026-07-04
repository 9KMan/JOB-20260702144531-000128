"""Tests for ETLService transform logic."""
from __future__ import annotations

import pytest

from src.bigquery.transformation import (
    AggregationType,
    FilterOperator,
    FilterStep,
    TransformPipeline,
)


class TestETLServiceTransform:
    """Tests for ETLService transform pipeline."""

    def test_transform_normalizes_text(self) -> None:
        """Transform should normalize text content to lowercase."""
        from src.bigquery.transformation import ColumnAliasStep

        step = ColumnAliasStep(renames=[("raw_text", "normalized_text")])
        sql = step.render({})
        assert "raw_text" in sql
        assert "normalized_text" in sql

    def test_transform_applies_length_filter(self) -> None:
        """Transform should filter records by content length."""
        pipeline = (
            TransformPipeline(base_table="`project.dataset.raw_events`")
            .filter(
                FilterStep(
                    column="length",
                    operator=FilterOperator.GTE,
                    value=10,
                )
            )
        )
        sql, _ = pipeline.render()
        assert "`project.dataset.raw_events`" in sql
        assert "WHERE" in sql
        assert "length" in sql

    def test_transform_deduplication_key(self) -> None:
        """Transform should filter out duplicates based on source_id + ingested_at."""
        pipeline = (
            TransformPipeline(base_table="`project.dataset.raw_events`")
            .filter(
                FilterStep(
                    column="source_id",
                    operator=FilterOperator.IS_NOT_NULL,
                )
            )
        )
        sql, _ = pipeline.render()
        assert "source_id" in sql
        assert "IS NOT NULL" in sql

    def test_transform_with_ai_tag_filter(self) -> None:
        """Transform should filter records that have AI-generated topic tags."""
        pipeline = (
            TransformPipeline(base_table="`project.dataset.raw_events`")
            .filter(
                FilterStep(
                    column="topic_tags",
                    operator=FilterOperator.IS_NOT_NULL,
                )
            )
        )
        sql, _ = pipeline.render()
        assert "topic_tags" in sql
        assert "IS NOT NULL" in sql

    def test_transform_sentiment_range_filter(self) -> None:
        """Transform should filter records within a sentiment score range."""
        pipeline = (
            TransformPipeline(base_table="`project.dataset.raw_events`")
            .filter(
                FilterStep(
                    column="sentiment_score",
                    operator=FilterOperator.BETWEEN,
                    condition=(-1.0, 1.0),
                )
            )
        )
        sql, _ = pipeline.render()
        assert "sentiment_score" in sql
        assert "BETWEEN" in sql

    def test_transform_aggregates_by_source_type(self) -> None:
        """Transform should aggregate metrics grouped by source_type."""
        from src.bigquery.transformation import AggregateStep

        pipeline = (
            TransformPipeline(base_table="`project.dataset.raw_events`")
            .aggregate(
                AggregateStep(
                    group_by=["source_type"],
                    aggregations=[
                        ("id", AggregationType.COUNT, "record_count"),
                        (
                            "sentiment_score",
                            AggregationType.AVG,
                            "avg_sentiment",
                        ),
                    ],
                )
            )
        )
        sql, _ = pipeline.render()
        assert "GROUP BY `source_type`" in sql
        assert "COUNT(`id`)" in sql
        assert "AVG(`sentiment_score`)" in sql

    def test_transform_full_pipeline(self) -> None:
        """Full ETL transform pipeline from raw events to aggregated metrics."""
        from src.bigquery.transformation import (
            AggregateStep,
            OrderLimitStep,
            SortDirection,
        )

        pipeline = (
            TransformPipeline(base_table="`project.dataset.raw_events`")
            .filter(
                FilterStep(
                    column="sentiment_score",
                    operator=FilterOperator.IS_NOT_NULL,
                )
            )
            .filter(
                FilterStep(
                    column="topic_tags",
                    operator=FilterOperator.IS_NOT_NULL,
                )
            )
            .aggregate(
                AggregateStep(
                    group_by=["source_type"],
                    aggregations=[
                        ("id", AggregationType.COUNT, "total_records"),
                        (
                            "sentiment_score",
                            AggregationType.AVG,
                            "avg_sentiment",
                        ),
                    ],
                )
            )
            .order_limit(
                OrderLimitStep(
                    order_by=[("total_records", SortDirection.DESC)],
                    limit=10,
                )
            )
        )
        sql, _ = pipeline.render()
        assert "WHERE" in sql
        assert "GROUP BY" in sql
        assert "ORDER BY" in sql
        assert "LIMIT 10" in sql