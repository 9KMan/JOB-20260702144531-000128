"""Tests for BigQuery transformation length-categorization logic."""
from __future__ import annotations

import pytest

from src.bigquery.transformation import (
    AggregationType,
    FilterOperator,
    FilterStep,
    TransformPipeline,
)


class TestLengthCategorization:
    """Tests for the length-based categorization transform."""

    def test_short_text_below_threshold(self) -> None:
        """Text shorter than 100 chars should not be categorized as long."""
        step = FilterStep(
            column="content_length",
            operator=FilterOperator.LT,
            value=100,
        )
        sql = step.render({})
        assert "content_length" in sql
        assert "<" in sql

    def test_medium_text_range(self) -> None:
        """Text between 100 and 1000 chars is medium length."""
        step = FilterStep(
            column="content_length",
            operator=FilterOperator.BETWEEN,
            condition=(100, 1000),
        )
        sql = step.render({})
        assert "BETWEEN" in sql
        assert "100" in sql
        assert "1000" in sql

    def test_long_text_above_threshold(self) -> None:
        """Text longer than 1000 chars should be categorized as long."""
        step = FilterStep(
            column="content_length",
            operator=FilterOperator.GT,
            value=1000,
        )
        sql = step.render({})
        assert "content_length" in sql
        assert ">" in sql

    def test_length_pipeline_with_aggregate(self) -> None:
        """Pipeline categorizing by length and aggregating should render correctly."""
        pipeline = (
            TransformPipeline()
            .filter(
                FilterStep(
                    column="content_length",
                    operator=FilterOperator.GTE,
                    value=100,
                )
            )
        )
        sql, _ = pipeline.render()
        assert "WHERE" in sql
        assert "content_length" in sql

    def test_length_categorization_three_tier(self) -> None:
        """Three-tier length categorization: short/medium/long."""
        short_pipeline = TransformPipeline(
            base_table="`project.dataset.events`"
        ).filter(
            FilterStep(column="content_length", operator=FilterOperator.LT, value=100)
        )
        medium_pipeline = TransformPipeline(
            base_table="`project.dataset.events`"
        ).filter(
            FilterStep(
                column="content_length",
                operator=FilterOperator.BETWEEN,
                condition=(100, 1000),
            )
        )
        long_pipeline = TransformPipeline(
            base_table="`project.dataset.events`"
        ).filter(
            FilterStep(column="content_length", operator=FilterOperator.GT, value=1000)
        )

        short_sql, _ = short_pipeline.render()
        medium_sql, _ = medium_pipeline.render()
        long_sql, _ = long_pipeline.render()

        assert "`content_length` < 100" in short_sql
        assert "BETWEEN 100 AND 1000" in medium_sql
        assert "`content_length` > 1000" in long_sql

    def test_transform_pipeline_categorize_and_count(self) -> None:
        """Aggregate counting records per length category."""
        from src.bigquery.transformation import AggregateStep

        pipeline = (
            TransformPipeline(base_table="`project.dataset.events`")
            .filter(
                FilterStep(
                    column="content_length",
                    operator=FilterOperator.GTE,
                    value=100,
                )
            )
            .aggregate(
                AggregateStep(
                    group_by=["content_length_category"],
                    aggregations=[
                        ("content_length", AggregationType.COUNT, "record_count")
                    ],
                )
            )
        )
        sql, _ = pipeline.render()
        assert "GROUP BY" in sql
        assert "COUNT" in sql
        assert "content_length_category" in sql