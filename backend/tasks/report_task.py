"""
tasks/report_task.py
"""
import asyncio
from datetime import datetime
from celery.utils.log import get_task_logger
from tasks.celery_app import celery_app
from agents.data_fetcher import get_commodity_data, get_macro_snapshot, get_equity_data
from agents.llm_analyst import analyse_commodity, analyse_equity
from report_builder.docx_builder import build_commodity_report, build_equity_report

logger = get_task_logger(__name__)


def run_async(coro):
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


def _update_report_status(report_id: str, status: str, file_url: str = None, error: str = None):
    from supabase import create_client
    from core.config import get_settings
    settings = get_settings()
    sb = create_client(settings.supabase_url, settings.supabase_service_key)
    data = {"status": status}
    if file_url:
        data["file_url"] = file_url
        data["completed_at"] = datetime.utcnow().isoformat()
    if error:
        data["error_message"] = error[:500]  # cap length
    sb.table("reports").update(data).eq("id", report_id).execute()


def _upload_to_supabase(report_bytes: bytes, filename: str) -> str:
    from supabase import create_client
    from core.config import get_settings
    settings = get_settings()
    sb = create_client(settings.supabase_url, settings.supabase_service_key)
    path = f"generated/{filename}"
    sb.storage.from_("reports").upload(
        path,
        report_bytes,
        {"content-type": "application/vnd.openxmlformats-officedocument.wordprocessingml.document"},
    )
    return sb.storage.from_("reports").get_public_url(path)


@celery_app.task(
    bind=True,
    max_retries=3,
    default_retry_delay=30,
    name="tasks.report_task.generate_report",
)
def generate_report(self, report_id, asset_type, asset_symbol, analysis_type, user_id):
    logger.info(f"[{report_id}] Starting: {asset_symbol} ({asset_type})")

    try:
        _update_report_status(report_id, "processing")

        macro_data = run_async(get_macro_snapshot())

        if asset_type == "commodity":
            market_data = run_async(get_commodity_data(asset_symbol))
            if market_data.get("error"):
                raise ValueError(f"Data fetch failed: {market_data['error']}")

            analysis = run_async(analyse_commodity(asset_symbol, market_data, macro_data, analysis_type))
            if analysis.get("error"):
                raise ValueError(f"Analysis failed: {analysis['error']}")

            report_bytes = build_commodity_report(
                asset_symbol, market_data, analysis["text"], macro_data
            )

        elif asset_type == "equity":
            market_data = run_async(get_equity_data(asset_symbol))
            if market_data.get("error"):
                raise ValueError(f"Data fetch failed: {market_data['error']}")

            analysis = run_async(analyse_equity(asset_symbol, market_data, macro_data))
            if analysis.get("error"):
                raise ValueError(f"Analysis failed: {analysis['error']}")

            report_bytes = build_equity_report(
                asset_symbol, market_data, analysis["text"], macro_data
            )

        else:
            raise ValueError(f"Unknown asset_type: {asset_type}")

        ts = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        filename = f"{asset_symbol}_{report_id[:8]}_{ts}.docx"
        file_url = _upload_to_supabase(report_bytes, filename)

        _update_report_status(report_id, "completed", file_url=file_url)
        logger.info(f"[{report_id}] Completed: {file_url}")
        return {"status": "completed", "file_url": file_url}

    except Exception as exc:
        logger.error(f"[{report_id}] Failed: {exc}")
        _update_report_status(report_id, "failed", error=str(exc))
        if self.request.retries < self.max_retries:
            raise self.retry(exc=exc, countdown=30)
        return {"status": "failed", "error": str(exc)}