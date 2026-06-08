"""Unit tests for the SQL transformation pipeline."""
from __future__ import annotations

import pytest

from src.bigquery.transformation import (
    AggregationType,
    ColumnAliasStep,
    DynamicFilterStep,
    FilterOperator,
    FilterStep,
    JoinStep,
    JoinType,
    OrderLimitStep,
    PivotStep,
    SortDirection,
    TransformPipeline,
    UnionStep,
    WindowStep,
    AggregateStep,
    make_daily_metric_pipeline,
)


class TestFilterStep:
    def test_eq_operator(self):
        step = FilterStep(column="status", operator=FilterOperator.EQ, value="active")
        assert "WHERE `status` = 'active'" in step.render({})

    def test_is_null(self):
        step = FilterStep(column="deleted_at", operator=FilterOperator.IS_NULL)
        assert "WHERE `deleted_at` IS NULL" in step.render({})

    def test_in_operator(self):
        step = FilterStep(column="user_id", operator=FilterOperator.IN, value=[1, 2, 3])
        assert "WHERE `user_id` IN (1, 2, 3)" in step.render({})

    def test_between_operator(self):
        step = FilterStep(column="amount", operator=FilterOperator.BETWEEN, condition=(0, 100))
        assert "BETWEEN 0 AND 100" in step.render({})

    def test_like_operator(self):
        step = FilterStep(column="email", operator=FilterOperator.LIKE, value="%@example.com")
        assert "LIKE '%@example.com'" in step.render({})

    def test_validate_between_missing_condition(self):
        step = FilterStep(column="x", operator=FilterOperator.BETWEEN, condition=None)
        errors = step.validate({})
        assert any("BETWEEN" in e for e in errors)

    def test_validate_in_missing_value(self):
        step = FilterStep(column="x", operator=FilterOperator.IN, value=None)
        errors = step.validate({})
        assert any("requires" in e for e in errors)


class TestAggregateStep:
    def test_basic_group_by(self):
        step = AggregateStep(
            group_by=["date"],
            aggregations=[("revenue", AggregationType.SUM, "total_revenue")],
        )
        sql = step.render({})
        assert "GROUP BY `date`" in sql
        assert "SUM(`revenue`)" in sql
        assert "`total_revenue`" in sql

    def test_count_distinct(self):
        step = AggregateStep(
            aggregations=[("user_id", AggregationType.COUNT_DISTINCT, "unique_users")],
        )
        sql = step.render({})
        assert "COUNT(DISTINCT `user_id`)" in sql

    def test_having_clause(self):
        step = AggregateStep(
            aggregations=[("revenue", AggregationType.SUM, "total_revenue")],
            having=("total_revenue", FilterOperator.GTE, 1000),
        )
        sql = step.render({})
        assert "HAVING `total_revenue` >= 1000" in sql

    def test_validate_empty_aggregations(self):
        step = AggregateStep(group_by=["date"], aggregations=[])
        errors = step.validate({})
        assert any("at least one aggregation" in e for e in errors)


class TestWindowStep:
    def test_basic_partition(self):
        step = WindowStep(
            partitions=["user_id"],
            functions=[("SUM(revenue)", "user_revenue")],
        )
        sql = step.render({})
        assert "PARTITION BY `user_id`" in sql
        assert "SUM(revenue)" in sql

    def test_order_by_in_window(self):
        step = WindowStep(
            partitions=["user_id"],
            orders=[("date", SortDirection.DESC)],
            functions=[("SUM(revenue)", "user_revenue")],
        )
        sql = step.render({})
        assert "ORDER BY `date` DESC" in sql

    def test_explicit_over(self):
        step = WindowStep(
            functions=[("SUM(revenue) OVER(PARTITION BY user_id)", "user_revenue")],
        )
        sql = step.render({})
        assert "SUM(revenue) OVER(PARTITION BY user_id)" in sql


class TestColumnAliasStep:
    def test_rename(self):
        step = ColumnAliasStep(renames=[("old_name", "new_name")])
        sql = step.render({})
        assert "`old_name` AS `new_name`" in sql

    def test_cast(self):
        step = ColumnAliasStep(casts=[("revenue", "FLOAT")])
        sql = step.render({})
        assert "CAST(`revenue` AS FLOAT)" in sql


class TestOrderLimitStep:
    def test_order_and_limit(self):
        step = OrderLimitStep(
            order_by=[("date", SortDirection.DESC)],
            limit=100,
            offset=10,
        )
        sql = step.render({})
        assert "ORDER BY `date` DESC" in sql
        assert "LIMIT 100" in sql
        assert "OFFSET 10" in sql


class TestUnionStep:
    def test_union_all(self):
        step = UnionStep(sources=["table_a", "table_b"], distinct=False)
        sql = step.render({})
        assert "UNION ALL" in sql
        assert "table_a" in sql
        assert "table_b" in sql

    def test_union_distinct(self):
        step = UnionStep(sources=["a", "b"], distinct=True)
        sql = step.render({})
        assert "UNION DISTINCT" in sql


class TestJoinStep:
    def test_left_join(self):
        step = JoinStep(
            join_type=JoinType.LEFT,
            right_table="users",
            join_condition="orders.user_id = users.id",
        )
        sql = step.render({})
        assert "LEFT JOIN users" in sql
        assert "ON orders.user_id = users.id" in sql


class TestPivotStep:
    def test_basic_pivot(self):
        step = PivotStep(
            index_cols=["region"],
            pivot_col="status",
            pivot_values=["active", "churned"],
            value_col="revenue",
            agg_func=AggregationType.SUM,
        )
        sql = step.render({})
        assert "GROUP BY `region`" in sql
        assert "SUM(IF(`status` = 'active'" in sql


class TestDynamicFilterStep:
    def test_dynamic_eq(self):
        step = DynamicFilterStep(param_name="start_date", column="date", operator=FilterOperator.GTE)
        sql = step.render({})
        assert "@start_date" in sql
        assert "COALESCE" in sql


class TestTransformPipeline:
    def test_empty_pipeline(self):
        p = TransformPipeline()
        sql, params = p.render()
        assert sql == ""

    def test_filter_chain(self):
        p = (
            TransformPipeline()
            .filter(FilterStep(column="date", operator=FilterOperator.GTE, value="2024-01-01"))
            .filter(FilterStep(column="status", operator=FilterOperator.EQ, value="active"))
        )
        sql, params = p.render()
        assert "WHERE" in sql

    def test_aggregate_pipeline(self):
        p = (
            TransformPipeline()
            .aggregate(
                AggregateStep(
                    group_by=["date"],
                    aggregations=[("revenue", AggregationType.SUM, "total_revenue")],
                )
            )
            .order_limit(OrderLimitStep(order_by=[("date", SortDirection.DESC)], limit=100))
        )
        sql, params = p.render()
        assert "GROUP BY" in sql
        assert "ORDER BY" in sql
        assert "LIMIT 100" in sql

    def test_pipeline_with_base_table(self):
        p = TransformPipeline(base_table="`project.dataset.events`")
        p = p.filter(FilterStep(column="date", operator=FilterOperator.GTE, value="2024-01-01"))
        sql, params = p.render()
        assert "`project.dataset.events`" in sql
        assert "WHERE" in sql

    def test_render_subquery(self):
        p = TransformPipeline().filter(FilterStep(column="x", operator=FilterOperator.GT, value=0))
        sql, params = p.render_subquery("filtered")
        assert "AS `filtered`" in sql

    def test_step_types(self):
        p = (
            TransformPipeline()
            .filter(FilterStep(column="x", operator=FilterOperator.EQ, value=1))
            .aggregate(AggregateStep(aggregations=[("x", AggregationType.SUM, "s")]))
        )
        assert p.step_types() == ["FilterStep", "AggregateStep"]

    def test_len(self):
        p = TransformPipeline().filter(FilterStep(column="x", operator=FilterOperator.EQ, value=1))
        assert len(p) == 1

    def test_validate_propagates(self):
        p = TransformPipeline().aggregate(AggregateStep(group_by=[], aggregations=[]))
        with pytest.raises(ValueError, match="validation failed"):
            p.render()


class TestMakeDailyMetricPipeline:
    def test_make_daily_metric(self):
        p = make_daily_metric_pipeline(
            source_table="events",
            date_col="date",
            metric_col="revenue",
            agg_func=AggregationType.SUM,
        )
        sql, _ = p.render()
        assert "GROUP BY `date`" in sql
        assert "SUM(`revenue`)" in sql
        assert "ORDER BY `date` DESC" in sql
