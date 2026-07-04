#!/usr/bin/env python3
"""GSD Execute Plan — Pipeline Plan Execution with Core Verification.

This module executes the data pipeline plan with:
- gsd-core module verification (config, BigQuery client, dependencies)
- Structured error handling with retry logic
- Pipeline stage validation before execution
- Comprehensive logging via structlog

Usage:
    python gsd-execute-plan.py [--dry-run] [--stage {extract,transform,load,all}]

Or import as a module:
    from gsd_execute_plan import GSDExecutePlan, verify_gsd_core
"""
from __future__ import annotations

import argparse
import asyncio
import logging
import sys
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

# Configure structured logging
logging.basicConfig(
    level=logging.INFO,
    format="%(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class PipelineStage(str, Enum):
    """Pipeline execution stages in order."""
    EXTRACT = "extract"
    TRANSFORM = "transform"
    LOAD = "load"
    ALL = "all"


class VerificationStatus(str, Enum):
    """Status of a verification check."""
    PASSED = "passed"
    FAILED = "failed"
    SKIPPED = "skipped"
    WARNING = "warning"


# ---------------------------------------------------------------------------
# Data Classes
# ---------------------------------------------------------------------------

@dataclass
class VerificationResult:
    """Result of a single verification check."""
    name: str
    status: VerificationStatus
    message: str = ""
    details: Dict[str, Any] = field(default_factory=dict)
    duration_ms: float = 0.0

    @property
    def is_ok(self) -> bool:
        return self.status in (VerificationStatus.PASSED, VerificationStatus.SKIPPED)


@dataclass
class StageResult:
    """Result of a pipeline stage execution."""
    stage: PipelineStage
    success: bool
    records_in: int = 0
    records_out: int = 0
    duration_ms: float = 0.0
    error: Optional[str] = None
    warnings: List[str] = field(default_factory=list)


@dataclass
class PlanExecutionResult:
    """Overall result of a plan execution."""
    success: bool
    started_at: str = ""
    completed_at: str = ""
    duration_ms: float = 0.0
    verification_results: List[VerificationResult] = field(default_factory=list)
    stage_results: List[StageResult] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# GSD Core Verification
# ---------------------------------------------------------------------------

class GSDCoreVerifier:
    """Verify all gsd-core dependencies and configuration before execution."""

    def __init__(self) -> None:
        self.results: List[VerificationResult] = []

    def verify_all(self) -> List[VerificationResult]:
        """Run all verification checks in order."""
        verifications = [
            ("python_version", self._verify_python_version),
            ("config_module", self._verify_config_module),
            ("bigquery_client", self._verify_bigquery_client),
            ("required_packages", self._verify_required_packages),
            ("environment_variables", self._verify_environment_variables),
            ("gcp_credentials", self._verify_gcp_credentials),
        ]
        for name, fn in verifications:
            result = self._timed_verification(name, fn)
            self.results.append(result)
        return self.results

    def _timed_verification(
        self, name: str, fn: callable
    ) -> VerificationResult:
        """Execute a verification with timing."""
        start = time.perf_counter()
        try:
            return fn(name)
        except Exception as exc:  # noqa: BLE001
            duration_ms = (time.perf_counter() - start) * 1000
            return VerificationResult(
                name=name,
                status=VerificationStatus.FAILED,
                message=f"Verification raised exception: {exc}",
                duration_ms=duration_ms,
            )

    def _verify_python_version(self, name: str) -> VerificationResult:
        """Verify Python version is 3.11+."""
        import sys
        version = sys.version_info
        if version.major >= 3 and version.minor >= 11:
            return VerificationResult(
                name=name,
                status=VerificationStatus.PASSED,
                message=f"Python {version.major}.{version.minor}.{version.micro}",
            )
        return VerificationResult(
            name=name,
            status=VerificationStatus.FAILED,
            message=f"Python {version.major}.{version.minor} — requires 3.11+",
        )

    def _verify_config_module(self, name: str) -> VerificationResult:
        """Verify src.core.config loads successfully."""
        try:
            from src.core.config import settings, get_settings
            settings_check = get_settings()
            return VerificationResult(
                name=name,
                status=VerificationStatus.PASSED,
                message="src.core.config loaded successfully",
                details={
                    "project_name": settings_check.PROJECT_NAME,
                    "version": settings_check.VERSION,
                    "debug": settings_check.DEBUG,
                },
            )
        except ImportError as exc:
            return VerificationResult(
                name=name,
                status=VerificationStatus.FAILED,
                message=f"Failed to import src.core.config: {exc}",
            )
        except Exception as exc:
            return VerificationResult(
                name=name,
                status=VerificationStatus.WARNING,
                message=f"Config loaded with warnings: {exc}",
            )

    def _verify_bigquery_client(self, name: str) -> VerificationResult:
        """Verify BigQuery client can be instantiated."""
        try:
            from google.cloud import bigquery
            client = bigquery.Client()
            return VerificationResult(
                name=name,
                status=VerificationStatus.PASSED,
                message="BigQuery client initialized",
                details={"project": client.project},
            )
        except Exception as exc:
            return VerificationResult(
                name=name,
                status=VerificationStatus.WARNING,
                message=f"BigQuery client init failed (may be credentials issue): {exc}",
            )

    def _verify_required_packages(self, name: str) -> VerificationResult:
        """Verify all required packages are importable."""
        required = [
            "fastapi",
            "google.cloud.bigquery",
            "google.cloud.storage",
            "pydantic",
            "pydantic_settings",
            "httpx",
            "pandas",
        ]
        missing = []
        for pkg in required:
            try:
                __import__(pkg)
            except ImportError:
                missing.append(pkg)

        if not missing:
            return VerificationResult(
                name=name,
                status=VerificationStatus.PASSED,
                message=f"All {len(required)} required packages available",
            )
        return VerificationResult(
            name=name,
            status=VerificationStatus.FAILED,
            message=f"Missing packages: {', '.join(missing)}",
        )

    def _verify_environment_variables(self, name: str) -> VerificationResult:
        """Verify required environment variables are set."""
        try:
            from src.core.config import settings
            required = ["GCP_PROJECT_ID", "GCP_BIGQUERY_DATASET"]
            missing = [var for var in required if not getattr(settings, var, None)]
            if missing:
                return VerificationResult(
                    name=name,
                    status=VerificationStatus.WARNING,
                    message=f"Missing env vars: {', '.join(missing)}",
                )
            return VerificationResult(
                name=name,
                status=VerificationStatus.PASSED,
                message="All required environment variables set",
            )
        except Exception as exc:
            return VerificationResult(
                name=name,
                status=VerificationStatus.FAILED,
                message=f"Could not verify env vars: {exc}",
            )

    def _verify_gcp_credentials(self, name: str) -> VerificationResult:
        """Verify GCP credentials are configured."""
        try:
            import os
            creds_path = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS")
            if creds_path and os.path.exists(creds_path):
                return VerificationResult(
                    name=name,
                    status=VerificationStatus.PASSED,
                    message=f"Credentials file found at {creds_path}",
                )
            # Try Application Default Credentials
            import subprocess
            result = subprocess.run(
                ["gcloud", "auth", "list"],
                capture_output=True,
                text=True,
                timeout=10,
            )
            if result.returncode == 0:
                return VerificationResult(
                    name=name,
                    status=VerificationStatus.PASSED,
                    message="Application Default Credentials available",
                )
            return VerificationResult(
                name=name,
                status=VerificationStatus.WARNING,
                message="No GCP credentials found — BigQuery writes may fail",
            )
        except FileNotFoundError:
            return VerificationResult(
                name=name,
                status=VerificationStatus.SKIPPED,
                message="gcloud CLI not found — skipping credential check",
            )
        except Exception as exc:
            return VerificationResult(
                name=name,
                status=VerificationStatus.WARNING,
                message=f"Credential check failed: {exc}",
            )


# ---------------------------------------------------------------------------
# Pipeline Stage Executors
# ---------------------------------------------------------------------------

class ExtractStage:
    """Extract stage: process pending webhooks and API data."""

    def __init__(self) -> None:
        self._records: List[Dict[str, Any]] = []

    async def execute(self) -> StageResult:
        """Execute the extract stage."""
        stage = PipelineStage.EXTRACT
        start = time.perf_counter()
        try:
            from src.api.routes.ingestion import get_pending_records, clear_pending_records
            records = get_pending_records()
            self._records = records
            duration_ms = (time.perf_counter() - start) * 1000
            return StageResult(
                stage=stage,
                success=True,
                records_in=len(records),
                records_out=len(records),
                duration_ms=duration_ms,
            )
        except ImportError as exc:
            duration_ms = (time.perf_counter() - start) * 1000
            return StageResult(
                stage=stage,
                success=False,
                duration_ms=duration_ms,
                error=f"Import failed (may be running outside app context): {exc}",
            )
        except Exception as exc:
            duration_ms = (time.perf_counter() - start) * 1000
            return StageResult(
                stage=stage,
                success=False,
                duration_ms=duration_ms,
                error=str(exc),
            )

    @property
    def records(self) -> List[Dict[str, Any]]:
        return self._records


class TransformStage:
    """Transform stage: normalize, tag, and deduplicate records."""

    def __init__(self, records: List[Dict[str, Any]]) -> None:
        self._records = records
        self._transformed: List[Dict[str, Any]] = []

    async def execute(self) -> StageResult:
        """Execute the transform stage."""
        stage = PipelineStage.TRANSFORM
        start = time.perf_counter()
        try:
            from run_pipeline import ETLService
            from src.core.config import settings

            etl = ETLService(
                project_id=settings.GCP_PROJECT_ID,
                dataset=settings.GCP_BIGQUERY_DATASET,
                table=settings.GCP_BIGQUERY_TABLE,
            )
            self._transformed = etl.transform(self._records)
            duration_ms = (time.perf_counter() - start) * 1000
            return StageResult(
                stage=stage,
                success=True,
                records_in=len(self._records),
                records_out=len(self._transformed),
                duration_ms=duration_ms,
            )
        except ImportError as exc:
            duration_ms = (time.perf_counter() - start) * 1000
            return StageResult(
                stage=stage,
                success=False,
                duration_ms=duration_ms,
                error=f"Transform failed: {exc}",
            )
        except Exception as exc:
            duration_ms = (time.perf_counter() - start) * 1000
            return StageResult(
                stage=stage,
                success=False,
                duration_ms=duration_ms,
                error=str(exc),
            )

    @property
    def transformed_records(self) -> List[Dict[str, Any]]:
        return self._transformed


class LoadStage:
    """Load stage: write records to BigQuery."""

    def __init__(self, records: List[Dict[str, Any]]) -> None:
        self._records = records

    async def execute(self) -> StageResult:
        """Execute the load stage."""
        stage = PipelineStage.LOAD
        start = time.perf_counter()
        try:
            from google.cloud import bigquery
            from src.core.config import settings

            if not self._records:
                duration_ms = (time.perf_counter() - start) * 1000
                return StageResult(
                    stage=stage,
                    success=True,
                    records_in=0,
                    records_out=0,
                    duration_ms=duration_ms,
                    warnings=["No records to load"],
                )

            client = bigquery.Client(project=settings.GCP_PROJECT_ID)
            table_ref = (
                f"{settings.GCP_PROJECT_ID}."
                f"{settings.GCP_BIGQUERY_DATASET}."
                f"{settings.GCP_BIGQUERY_TABLE}"
            )
            errors = client.insert_rows_json(table_ref, self._records)
            if errors:
                duration_ms = (time.perf_counter() - start) * 1000
                return StageResult(
                    stage=stage,
                    success=False,
                    records_in=len(self._records),
                    duration_ms=duration_ms,
                    error=f"BigQuery insert errors: {errors}",
                )
            duration_ms = (time.perf_counter() - start) * 1000
            return StageResult(
                stage=stage,
                success=True,
                records_in=len(self._records),
                records_out=len(self._records),
                duration_ms=duration_ms,
            )
        except ImportError as exc:
            duration_ms = (time.perf_counter() - start) * 1000
            return StageResult(
                stage=stage,
                success=False,
                duration_ms=duration_ms,
                error=f"BigQuery not available: {exc}",
            )
        except Exception as exc:
            duration_ms = (time.perf_counter() - start) * 1000
            return StageResult(
                stage=stage,
                success=False,
                duration_ms=duration_ms,
                error=str(exc),
            )


# ---------------------------------------------------------------------------
# Main Executor
# ---------------------------------------------------------------------------

class GSDExecutePlan:
    """Execute pipeline plans with verification and error handling.

    Parameters
    ----------
    dry_run : bool
        If True, skip actual BigQuery writes and verify only.
    stage : PipelineStage
        Which stage(s) to execute (default: ALL).
    """

    def __init__(
        self,
        dry_run: bool = False,
        stage: PipelineStage = PipelineStage.ALL,
    ) -> None:
        self.dry_run = dry_run
        self.stage = stage
        self._verifier = GSDCoreVerifier()
        self._result: Optional[PlanExecutionResult] = None

    async def execute(self) -> PlanExecutionResult:
        """Execute the full plan with verification and error handling."""
        started_at = datetime.now(timezone.utc).isoformat()
        result = PlanExecutionResult(success=False, started_at=started_at)

        # Phase 1: Verification
        logger.info("gsd.execute_plan.phase", phase="verification", dry_run=self.dry_run)
        verifications = self._verifier.verify_all()
        result.verification_results = verifications

        for v in verifications:
            if v.status == VerificationStatus.FAILED:
                result.errors.append(f"Verification '{v.name}' failed: {v.message}")
                logger.error("gsd.verification.failed", name=v.name, message=v.message)
            elif v.status == VerificationStatus.WARNING:
                result.warnings.append(f"Verification '{v.name}' warning: {v.message}")
                logger.warning("gsd.verification.warning", name=v.name, message=v.message)
            else:
                logger.info(
                    "gsd.verification.passed",
                    name=v.name,
                    message=v.message,
                    duration_ms=round(v.duration_ms, 2),
                )

        # Check if critical verifications passed
        critical_failed = any(
            v.status == VerificationStatus.FAILED
            for v in verifications
            if v.name in ("python_version", "required_packages")
        )
        if critical_failed:
            result.errors.append("Critical verification failures — aborting execution")
            logger.error("gsd.execute_plan.aborted", reason="critical_verification_failures")
            result.completed_at = datetime.now(timezone.utc).isoformat()
            self._result = result
            return result

        # Phase 2: Stage Execution
        if self.stage in (PipelineStage.ALL, PipelineStage.EXTRACT):
            extract_stage = ExtractStage()
            extract_result = await self._safe_stage_execute(extract_stage, "extract")
            result.stage_results.append(extract_result)
            if not extract_result.success:
                result.errors.append(f"Extract stage failed: {extract_result.error}")
                result.completed_at = datetime.now(timezone.utc).isoformat()
                self._result = result
                return result

        if self.stage in (PipelineStage.ALL, PipelineStage.TRANSFORM):
            transform_stage = TransformStage(extract_stage.records)
            transform_result = await self._safe_stage_execute(transform_stage, "transform")
            result.stage_results.append(transform_result)
            if not transform_result.success:
                result.errors.append(f"Transform stage failed: {transform_result.error}")
                result.completed_at = datetime.now(timezone.utc).isoformat()
                self._result = result
                return result

        if self.stage in (PipelineStage.ALL, PipelineStage.LOAD):
            if self.dry_run:
                logger.info("gsd.load_stage.skipped", reason="dry_run")
                load_result = StageResult(
                    stage=PipelineStage.LOAD,
                    success=True,
                    records_in=len(transform_stage.transformed_records),
                    records_out=0,
                    warnings=["Skipped due to dry-run mode"],
                )
            else:
                load_stage = LoadStage(transform_stage.transformed_records)
                load_result = await self._safe_stage_execute(load_stage, "load")
            result.stage_results.append(load_result)
            if not load_result.success:
                result.errors.append(f"Load stage failed: {load_result.error}")
                result.completed_at = datetime.now(timezone.utc).isoformat()
                self._result = result
                return result

        # All stages completed
        result.success = True
        result.completed_at = datetime.now(timezone.utc).isoformat()
        total_duration = sum(s.duration_ms for s in result.stage_results)
        result.duration_ms = total_duration

        logger.info(
            "gsd.execute_plan.success",
            stages=len(result.stage_results),
            total_duration_ms=round(total_duration, 2),
        )
        self._result = result
        return result

    async def _safe_stage_execute(
        self,
        stage_executor: Any,
        stage_name: str,
    ) -> StageResult:
        """Execute a stage with error handling and retry logic."""
        max_retries = 3
        retry_delay = 2.0

        for attempt in range(1, max_retries + 1):
            try:
                result = await stage_executor.execute()
                if result.success:
                    logger.info(
                        f"gsd.stage.{stage_name}.complete",
                        records_in=result.records_in,
                        records_out=result.records_out,
                        duration_ms=round(result.duration_ms, 2),
                    )
                    return result
                if attempt < max_retries:
                    logger.warning(
                        f"gsd.stage.{stage_name}.retry",
                        attempt=attempt,
                        max_retries=max_retries,
                        error=result.error,
                    )
                    await asyncio.sleep(retry_delay * attempt)
                    continue
                logger.error(
                    f"gsd.stage.{stage_name}.failed",
                    attempts=attempt,
                    error=result.error,
                )
                return result
            except Exception as exc:
                if attempt < max_retries:
                    logger.warning(
                        f"gsd.stage.{stage_name}.retry_exception",
                        attempt=attempt,
                        max_retries=max_retries,
                        error=str(exc),
                    )
                    await asyncio.sleep(retry_delay * attempt)
                    continue
                logger.error(
                    f"gsd.stage.{stage_name}.exception",
                    attempts=attempt,
                    error=str(exc),
                )
                return StageResult(
                    stage=PipelineStage(stage_name),
                    success=False,
                    error=str(exc),
                )

        # Should not reach here
        return StageResult(
            stage=PipelineStage(stage_name),
            success=False,
            error="Max retries exceeded",
        )

    @property
    def result(self) -> Optional[PlanExecutionResult]:
        return self._result


# ---------------------------------------------------------------------------
# Standalone Verification Function
# ---------------------------------------------------------------------------

def verify_gsd_core() -> Tuple[bool, List[VerificationResult]]:
    """Run gsd-core verification checks.

    Returns
    -------
    Tuple of (all_passed, results)
    """
    verifier = GSDCoreVerifier()
    results = verifier.verify_all()
    all_passed = all(
        r.status in (VerificationStatus.PASSED, VerificationStatus.SKIPPED)
        for r in results
    )
    return all_passed, results


# ---------------------------------------------------------------------------
# CLI Entry Point
# ---------------------------------------------------------------------------

def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="gsd-execute-plan.py",
        description="GSD Execute Plan — Pipeline Plan Execution with Core Verification",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Verify only, skip BigQuery writes",
    )
    parser.add_argument(
        "--stage",
        type=str,
        choices=["extract", "transform", "load", "all"],
        default="all",
        help="Which pipeline stage to execute (default: all)",
    )
    parser.add_argument(
        "--verify-only",
        action="store_true",
        help="Run verification checks and exit",
    )
    return parser


async def _main() -> int:
    parser = _build_parser()
    args = parser.parse_args()

    # Configure logging level based on dry-run
    if args.dry_run:
        logger.setLevel(logging.INFO)

    if args.verify_only:
        all_passed, results = verify_gsd_core()
        for r in results:
            status_symbol = {
                VerificationStatus.PASSED: "✓",
                VerificationStatus.FAILED: "✗",
                VerificationStatus.SKIPPED: "○",
                VerificationStatus.WARNING: "⚠",
            }[r.status]
            print(f"{status_symbol} [{r.name}] {r.message} ({r.duration_ms:.1f}ms)")
        return 0 if all_passed else 1

    executor = GSDExecutePlan(
        dry_run=args.dry_run,
        stage=PipelineStage(args.stage),
    )
    result = await executor.execute()

    # Print summary
    print("\n" + "=" * 60)
    print("GSD EXECUTE PLAN SUMMARY")
    print("=" * 60)
    print(f"Status:        {'SUCCESS' if result.success else 'FAILED'}")
    print(f"Started:       {result.started_at}")
    print(f"Completed:     {result.completed_at}")
    print(f"Duration:      {result.duration_ms:.1f}ms")
    print(f"\nVerifications: {len(result.verification_results)}")
    for v in result.verification_results:
        status_map = {
            VerificationStatus.PASSED: "PASS",
            VerificationStatus.FAILED: "FAIL",
            VerificationStatus.SKIPPED: "SKIP",
            VerificationStatus.WARNING: "WARN",
        }
        print(f"  [{status_map[v.status]}] {v.name}: {v.message}")

    print(f"\nStages: {len(result.stage_results)}")
    for s in result.stage_results:
        status_str = "OK" if s.success else "FAIL"
        print(
            f"  [{status_str}] {s.stage.value}: "
            f"{s.records_in}→{s.records_out} records "
            f"({s.duration_ms:.1f}ms)"
        )
        if s.error:
            print(f"         ERROR: {s.error}")
        if s.warnings:
            for w in s.warnings:
                print(f"         WARN: {w}")

    if result.errors:
        print(f"\nErrors ({len(result.errors)}):")
        for e in result.errors:
            print(f"  • {e}")

    if result.warnings:
        print(f"\nWarnings ({len(result.warnings)}):")
        for w in result.warnings:
            print(f"  • {w}")

    print("=" * 60)
    return 0 if result.success else 1


if __name__ == "__main__":
    sys.exit(asyncio.run(_main()))
