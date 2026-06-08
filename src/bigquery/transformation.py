"""SQL transformation pipeline — composable, type-safe SQL transform steps.

Each step in the pipeline implements the ``TransformStep`` protocol and can be
combined into a ``TransformPipeline`` that generates a final SQL query ready to
be executed against BigQuery.

Supported step types
-------------------
- ``PivotStep`` — pivot rows to columns
- ``AggregateStep``   — GROUP BY with built-in aggregation functions
- ``FilterStep``      — WHERE / HAVING clauses
- ``WindowStep``      — OVER (PARTITION BY … ORDER BY …)
- ``UnionStep``       — stack multiple tables
- ``JoinStep``        — LEFT / INNER / FULL JOIN between two tables
- ``ColumnAliasStep`` — rename / recast columns
- ``OrderLimitStep``  — ORDER BY + LIMIT / OFFSET
- ``DynamicFilterStep`` — interpolate runtime parameters

Usage
-----
 pipeline = (
        TransformPipeline()
        .filter(FilterStep(column="date", operator=">=", value="2024-01-01"))
        .aggregate(AggregateStep(aggregations=[("revenue", "SUM", "total_revenue")]))
        .order_limit(OrderLimitStep(order_by=[("date", "DESC")], limit=100))
    )
    sql, params = pipeline.render()
"""
from __future__ import annotations

import re
import string
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Sequence, Tuple, Union

logger: Any = None  # deferred import to avoid circular references


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


class AggregationType(str, Enum):
    SUM = "SUM"
    AVG = "AVG"
    COUNT = "COUNT"
    COUNT_DISTINCT = "COUNT_DISTINCT"
    MIN = "MIN"
    MAX = "MAX"
    STDDEV = "STDDEV"
    MEDIAN = "MEDIAN"
    APPROX_QUANTILES = "APPROX_QUANTILES"


class JoinType(str, Enum):
    INNER = "INNER"
    LEFT = "LEFT"
    RIGHT = "RIGHT"
    FULL = "FULL"


class SortDirection(str, Enum):
    ASC = "ASC"
    DESC = "DESC"


class FilterOperator(str, Enum):
    EQ = "="
    NE = "!="
    GT = ">"
    GTE = ">="
    LT = "<"
    LTE = "<="
    LIKE = "LIKE"
    NOT_LIKE = "NOT LIKE"
    IN = "IN"
    NOT_IN = "NOT IN"
    IS_NULL = "IS NULL"
    IS_NOT_NULL = "IS NOT NULL"
    BETWEEN = "BETWEEN"


# ---------------------------------------------------------------------------
# SQL sanitisation
# ---------------------------------------------------------------------------

_SAFE_IDENTIFIER_RE = re.compile(r"^[a-zA-Z_][a-zA-Z0-9_]*$")
_SAFE_IDENTIFIER_MAX = 256


def _sanitise_identifier(value: str) -> str:
    """Return value quoted as a BigQuery safe identifier, or raise."""
    if not value or len(value) > _SAFE_IDENTIFIER_MAX:
        raise ValueError(f"Invalid identifier: {value!r}")
    if not _SAFE_IDENTIFIER_RE.match(value):
        raise ValueError(f"Identifier contains illegal characters: {value!r}")
    return f"`{value}`"


def _format_literal(value: Any) -> str:
    """Format a Python value as a BigQuery SQL literal."""
    if value is None:
        return "NULL"
    if isinstance(value, bool):
        return "TRUE" if value else "FALSE"
    if isinstance(value, (int, float)):
        return str(value)
    if isinstance(value, datetime):
        return f"CAST('{value.isoformat()}' AS TIMESTAMP)"
    if isinstance(value, str):
        return "'" + value.replace("'", "''") + "'"
    if isinstance(value, (list, tuple)):
        items = ", ".join(_format_literal(v) for v in value)
        return f"({items})"
    return "'" + str(value).replace("'", "''") + "'"


# ---------------------------------------------------------------------------
# TransformStep protocol
# ---------------------------------------------------------------------------


class TransformStep(ABC):
    """Abstract base for all transformation steps."""

    @abstractmethod
    def render(self, ctx: Dict[str, Any]) -> str:
        """Return the SQL fragment for this step."""
        ...

    def validate(self, ctx: Dict[str, Any]) -> List[str]:
        """Return a list of validation error messages (empty = valid)."""
        return []


# ---------------------------------------------------------------------------
# Step implementations
# ---------------------------------------------------------------------------


@dataclass
class FilterStep(TransformStep):
    """Generate a WHERE clause.

    Parameters
    ----------
    column:
        Column name to filter on.
    operator:
        One of the ``FilterOperator`` values.
    value:
        Comparison value (not used for IS_NULL / IS_NOT_NULL).
    condition:
        For ``BETWEEN`` operator, a two-element sequence.
    """

    column: str
    operator: FilterOperator = FilterOperator.EQ
    value: Any = None
    condition: Optional[Sequence[Any]] = None

    def render(self, ctx: Dict[str, Any]) -> str:
        op = self.operator
        col = _sanitise_identifier(self.column)

        if op in (FilterOperator.IS_NULL, FilterOperator.IS_NOT_NULL):
            null_check = "IS NULL" if op == FilterOperator.IS_NULL else "IS NOT NULL"
            return f"WHERE {col} {null_check}"

        if op == FilterOperator.BETWEEN:
            lo, hi = self.condition if self.condition else (None, None)
            return f"WHERE {col} BETWEEN {_format_literal(lo)} AND {_format_literal(hi)}"

        if op in (FilterOperator.IN, FilterOperator.NOT_IN):
            in_token = "IN" if op == FilterOperator.IN else "NOT IN"
            vals = self.value if isinstance(self.value, (list, tuple)) else [self.value]
            return f"WHERE {col} {in_token} {_format_literal(vals)}"

        if op in (FilterOperator.LIKE, FilterOperator.NOT_LIKE):
            like_token = "LIKE" if op == FilterOperator.LIKE else "NOT LIKE"
            return f"WHERE {col} {like_token} {_format_literal(self.value)}"

        return f"WHERE {col} {op.value} {_format_literal(self.value)}"

    def validate(self, ctx: Dict[str, Any]) -> List[str]:
        errors = []
        if self.operator == FilterOperator.BETWEEN:
            if not self.condition or len(self.condition) != 2:
                errors.append("BETWEEN requires a two-element condition sequence")
        if self.operator in (
            FilterOperator.IN,
            FilterOperator.NOT_IN,
 FilterOperator.LIKE,
            FilterOperator.NOT_LIKE,
        ) and self.value is None:
            errors.append(f"Operator {self.operator} requires a non-None value")
        return errors


@dataclass
class AggregateStep(TransformStep):
    """Generate a GROUP BY clause with aggregation expressions.

    Parameters
    ----------
    group_by:
        List of column names to group by.
    aggregations:
        List of ``(source_col, agg_func, alias)`` tuples.
        ``agg_func`` is a ``AggregationType`` value or a raw SQL aggregation string.
    having:
        Optional HAVING clause expressed as a ``(agg_alias, operator, value)`` tuple.
    """

    group_by: List[str] = field(default_factory=list)
    aggregations: List[Tuple[str, Union[AggregationType, str], str]] = field(default_factory=list)
    having: Optional[Tuple[str, FilterOperator, Any]] = None

    def render(self, ctx: Dict[str, Any]) -> str:
        parts: List[str] = []

        select_parts: List[str] = []
        for col in self.group_by:
            select_parts.append(_sanitise_identifier(col))

        for src, agg, alias in self.aggregations:
            safe_alias = _sanitise_identifier(alias)
            if isinstance(agg, AggregationType):
                if agg == AggregationType.COUNT_DISTINCT:
                    select_parts.append(
                        f"COUNT(DISTINCT {_sanitise_identifier(src)}) AS {safe_alias}"
                    )
                elif agg == AggregationType.APPROX_QUANTILES:
                    select_parts.append(
                        f"APPROX_QUANTILES({_sanitise_identifier(src)}, 100)[OFFSET(50)] AS {safe_alias}"
                    )
                else:
                    select_parts.append(
                        f"{agg.value}({_sanitise_identifier(src)}) AS {safe_alias}"
                    )
            else:
                # Raw SQL aggregation string
                select_parts.append(f"{agg}({_sanitise_identifier(src)}) AS {safe_alias}")

        parts.append("SELECT " + ", ".join(select_parts))

        if self.group_by:
            cols = ", ".join(_sanitise_identifier(c) for c in self.group_by)
            parts.append(f"GROUP BY {cols}")

        if self.having:
            alias, op, val = self.having
            parts.append(f"HAVING {_sanitise_identifier(alias)} {op.value} {_format_literal(val)}")

        return "\n".join(parts)

    def validate(self, ctx: Dict[str, Any]) -> List[str]:
        errors = []
        if not self.aggregations:
            errors.append("AggregateStep requires at least one aggregation")
        for src, agg, alias in self.aggregations:
            if not alias:
                errors.append("Every aggregation must have a non-empty alias")
        return errors


@dataclass
class WindowStep(TransformStep):
    """Generate an OVER clause for window functions.

    Parameters
    ----------
    partitions:
        List of columns to PARTITION BY.
    orders:
        List of ``(column, direction)`` tuples for ORDER BY inside the window.
    functions:
        List of ``(func_expr, alias)`` tuples.
        ``func_expr`` is a raw SQL expression including OVER (e.g. ``SUM(x) OVER (...)``)
        or just the window-aggregate portion (e.g. ``SUM(x)``) which will be completed.
    frame:
        Window frame specifier, e.g. ``ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW``.
    """

    partitions: List[str] = field(default_factory=list)
    orders: List[Tuple[str, SortDirection]] = field(default_factory=list)
    functions: List[Tuple[str, str]] = field(default_factory=list)
    frame: Optional[str] = None

    def render(self, ctx: Dict[str, Any]) -> str:
        window_spec = ""
        if self.partitions:
            cols = ", ".join(_sanitise_identifier(c) for c in self.partitions)
            window_spec += f"PARTITION BY {cols}"
        if self.orders:
            order_parts = []
            for col, direction in self.orders:
                order_parts.append(
                    f"{_sanitise_identifier(col)} {direction.value}"
                )
            window_spec += (" " if window_spec else "") + "ORDER BY " + ", ".join(order_parts)
        if self.frame:
            window_spec += f" {self.frame}"

        over_clauses: List[str] = []
        for func_expr, alias in self.functions:
            safe_alias = _sanitise_identifier(alias)
            # If the expression already contains OVER, use it as-is.
            if "OVER" in func_expr.upper():
                over_clauses.append(f"{func_expr} AS {safe_alias}")
            else:
                over_clauses.append(f"{func_expr} OVER({window_spec}) AS {safe_alias}")

        return "SELECT " + ", ".join(over_clauses)

    def validate(self, ctx: Dict[str, Any]) -> List[str]:
        errors = []
        if not self.functions:
            errors.append("WindowStep requires at least one window function")
        return errors


@dataclass
class ColumnAliasStep(TransformStep):
    """Rename or recast columns in the SELECT clause."""

    renames: List[Tuple[str, str]] = field(default_factory=list)  # (old, new)
    casts: List[Tuple[str, str]] = field(default_factory=list)  # (col, bq_type)

    def render(self, ctx: Dict[str, Any]) -> str:
        selects: List[str] = []
        for old, new in self.renames:
            selects.append(f"{_sanitise_identifier(old)} AS {_sanitise_identifier(new)}")
        for col, bq_type in self.casts:
            selects.append(f"CAST({_sanitise_identifier(col)} AS {bq_type}) AS {_sanitise_identifier(col)}")
        return "SELECT " + ", ".join(selects) if selects else ""


@dataclass
class OrderLimitStep(TransformStep):
    """ORDER BY + LIMIT / OFFSET."""

    order_by: List[Tuple[str, SortDirection]] = field(default_factory=list)
    limit: Optional[int] = None
    offset: Optional[int] = None

    def render(self, ctx: Dict[str, Any]) -> str:
        parts: List[str] = []
        if self.order_by:
            order_parts = [
                f"{_sanitise_identifier(col)} {direction.value}"
                for col, direction in self.order_by
            ]
            parts.append("ORDER BY " + ", ".join(order_parts))
        if self.limit is not None:
            parts.append(f"LIMIT {self.limit}")
        if self.offset is not None:
            parts.append(f"OFFSET {self.offset}")
        return "\n".join(parts)


@dataclass
class UnionStep(TransformStep):
    """Stack multiple tables with UNION ALL / UNION DISTINCT."""

    sources: List[str] = field(default_factory=list)  # table references or sub-queries
    distinct: bool = False

    def render(self, ctx: Dict[str, Any]) -> str:
        if not self.sources:
            return ""
        union_token = "UNION DISTINCT" if self.distinct else "UNION ALL"
        return ("\n" + union_token + "\n").join(self.sources)


@dataclass
class JoinStep(TransformStep):
    """Generate a JOIN clause between two tables."""

    join_type: JoinType = JoinType.LEFT
    right_table: str = ""
    join_condition: str = ""  # raw ON clause, e.g. "a.id = b.ref_id"

    def render(self, ctx: Dict[str, Any]) -> str:
        return (
            f"{self.join_type.value} JOIN {self.right_table}\n"
            f"ON {self.join_condition}"
        )


@dataclass
class PivotStep(TransformStep):
    """Generate a pivot query using conditional aggregation.

    Parameters
    ----------
    index_cols:
        Columns to keep as row identifiers (GROUP BY).
    pivot_col:
        Column whose distinct values become column headers.
    value_col:
        Column to aggregate.
    agg_func:
        Aggregation to apply (default SUM).
    sparse:
        If True, output only non-null columns.
    """

    index_cols: List[str] = field(default_factory=list)
    pivot_col: str = ""
    pivot_values: List[Any] = field(default_factory=list)
    value_col: str = ""
    agg_func: AggregationType = AggregationType.SUM
    sparse: bool = True

    def render(self, ctx: Dict[str, Any]) -> str:
        selects: List[str] = []
        for col in self.index_cols:
            selects.append(_sanitise_identifier(col))

        for val in self.pivot_values:
            safe_val = str(val).replace("'", "''")
            col_alias = f"pivot_{safe_val}"
            selects.append(
                f"{self.agg_func.value}(IF({_sanitise_identifier(self.pivot_col)} = "
                f"{_format_literal(val)}, {_sanitise_identifier(self.value_col)}, NULL)) "
                f"AS {_sanitise_identifier(col_alias)}"
            )

        parts = ["SELECT " + ", ".join(selects)]
        if self.index_cols:
            cols = ", ".join(_sanitise_identifier(c) for c in self.index_cols)
            parts.append(f"GROUP BY {cols}")

        return "\n".join(parts)


@dataclass
class DynamicFilterStep(TransformStep):
    """Interpolate runtime parameters into the WHERE clause.

    Parameters
    ----------
    param_name:
        Name of the runtime parameter (without ``@`` prefix).
    column:
        Column to filter on.
    operator:
        Filter operator.
    default_value:
        Fallback value when the parameter is not set.
    """

    param_name: str
    column: str
    operator: FilterOperator = FilterOperator.EQ
    default_value: Any = None

    def render(self, ctx: Dict[str, Any]) -> str:
        col = _sanitise_identifier(self.column)
        param = f"@{self.param_name}"
        if self.operator == FilterOperator.IS_NULL:
            return f"WHERE {col} IS NULL"
        if self.operator == FilterOperator.IS_NOT_NULL:
            return f"WHERE {col} IS NOT NULL"
        return f"WHERE {col} {self.operator.value} COALESCE({param}, {_format_literal(self.default_value)})"


# ---------------------------------------------------------------------------
# TransformPipeline
# ---------------------------------------------------------------------------


class TransformPipeline:
    """Composable SQL transformation pipeline.

    Supports fluent chaining::

        pipeline = TransformPipeline().filter(...).aggregate(...)
    """

    def __init__(self, base_table: Optional[str] = None) -> None:
        self._base_table = base_table or ""
        self._steps: List[TransformStep] = []
        self._params: Dict[str, Any] = {}

    # ------------------------------------------------------------------
    # Fluent builder
    # ------------------------------------------------------------------

    def filter(self, step: FilterStep) -> "TransformPipeline":
        self._steps.append(step)
        return self

    def aggregate(self, step: AggregateStep) -> "TransformPipeline":
        self._steps.append(step)
        return self

    def window(self, step: WindowStep) -> "TransformPipeline":
        self._steps.append(step)
        return self

    def column_alias(self, step: ColumnAliasStep) -> "TransformPipeline":
        self._steps.append(step)
        return self

    def order_limit(self, step: OrderLimitStep) -> "TransformPipeline":
        self._steps.append(step)
        return self

    def union(self, step: UnionStep) -> "TransformPipeline":
        self._steps.append(step)
        return self

    def join(self, step: JoinStep) -> "TransformPipeline":
        self._steps.append(step)
        return self

    def pivot(self, step: PivotStep) -> "TransformPipeline":
        self._steps.append(step)
        return self

    def dynamic_filter(self, step: DynamicFilterStep) -> "TransformPipeline":
        self._steps.append(step)
        return self

    def set_param(self, key: str, value: Any) -> "TransformPipeline":
        self._params[key] = value
        return self

    # ------------------------------------------------------------------
    # Rendering
    # ------------------------------------------------------------------

    def render(self) -> Tuple[str, Dict[str, Any]]:
        """Render the pipeline into a SQL string and a parameter dict.

        Returns
        -------
        Tuple[str, Dict[str, Any]]
            SQL query string and BigQuery query parameters dict.
        """
        ctx: Dict[str, Any] = {"params": self._params}
        fragments: List[str] = []

        for step in self._steps:
            errors = step.validate(ctx)
            if errors:
                raise ValueError(f"{type(step).__name__} validation failed: {errors}")
            fragment = step.render(ctx)
            if fragment:
                fragments.append(fragment)

        if self._base_table:
            sql = f"SELECT * FROM {self._base_table}"
            if fragments:
                sql += "\n" + "\n".join(fragments)
        else:
            sql = "\n".join(fragments)

        return sql, self._params

    def render_subquery(self, alias: str = "t") -> Tuple[str, Dict[str, Any]]:
        """Render the pipeline as a subquery with the given alias."""
        inner_sql, params = self.render()
        return f"({inner_sql}) AS {_sanitise_identifier(alias)}", params

    # ------------------------------------------------------------------
    # Introspection
    # ------------------------------------------------------------------

    @property
    def steps(self) -> List[TransformStep]:
        return list(self._steps)

    def step_types(self) -> List[str]:
        return [type(s).__name__ for s in self._steps]

    def __len__(self) -> int:
        return len(self._steps)

    def __repr__(self) -> str:
        return (
            f"TransformPipeline(base_table={self._base_table!r}, "
            f"steps={self.step_types()})"
        )


# ---------------------------------------------------------------------------
# Registry for named pipelines
# ---------------------------------------------------------------------------

TRANSFORM_REGISTRY: Dict[str, TransformPipeline] = {}


def register_pipeline(name: str, pipeline: TransformPipeline) -> None:
    """Register a named pipeline for later retrieval."""
    TRANSFORM_REGISTRY[name] = pipeline


def get_pipeline(name: str) -> Optional[TransformPipeline]:
    return TRANSFORM_REGISTRY.get(name)


# ---------------------------------------------------------------------------
# Pre-built pipelines
# ---------------------------------------------------------------------------


def make_daily_metric_pipeline(
    source_table: str,
    date_col: str,
    metric_col: str,
    agg_func: AggregationType = AggregationType.SUM,
) -> TransformPipeline:
    """Standard daily rollup pipeline.

    Generates::

        SELECT<date_col> AS date, <agg_func>(<metric_col>) AS metric
        FROM <source_table>
        GROUP BY <date_col>
        ORDER BY <date_col> DESC
    """
    return (
        TransformPipeline(base_table=source_table)
        .aggregate(
            AggregateStep(
                group_by=[date_col],
                aggregations=[(metric_col, agg_func, "metric")],
            )
        )
        .order_limit(OrderLimitStep(order_by=[(date_col, SortDirection.DESC)]))
    )


def make_funnel_pipeline(
    source_table: str,
    steps: List[Tuple[str, str]],
    conversion_col: str,
) -> TransformPipeline:
    """Multi-step funnel analysis pipeline.

    Parameters
    ----------
    steps:
        List of ``(step_name, filter_expression)`` tuples in order.
    conversion_col:
        Column that indicates a conversion (e.g. a boolean flag).
    """
    pipeline = TransformPipeline(base_table=source_table)
    for step_name, filter_expr in steps:
        pipeline = pipeline.filter(
            FilterStep(column=step_name, operator=FilterOperator.EQ, value=filter_expr)
        )
    pipeline = pipeline.aggregate(
        AggregateStep(
            aggregations=[(conversion_col, AggregationType.COUNT_DISTINCT, "conversions")],
        )
    )
    return pipeline
