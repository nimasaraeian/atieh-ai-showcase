"""
API routes for data import operations.
"""
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import text
import logging
import traceback

from database import get_db
from app.importers.history_importer import import_history_excel
from app.security.rbac import require_roles

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/import",
    tags=["import"],
    dependencies=[Depends(require_roles("operator", "clinic_manager"))],
)


class ImportFileRequest(BaseModel):
    path: str
    year: Optional[int] = None
    sheet: Any = 0  # Can be int or string


@router.get("/ping")
async def ping():
    """Health check for import API."""
    return {"status": "ok", "message": "Import API is running"}


class ImportHistoryRequest(BaseModel):
    files: List[ImportFileRequest]


class ImportRunResponse(BaseModel):
    import_run_id: int
    status: str
    stats: Optional[Dict[str, Any]] = None
    error: Optional[str] = None


class ImportRunDetail(BaseModel):
    id: int
    run_type: str
    status: str
    started_at: str
    completed_at: Optional[str]
    stats_json: Optional[str]
    error_message: Optional[str]


class ImportErrorRow(BaseModel):
    id: int
    row_number: int
    file_name: str
    parse_error: str
    row_json: str


@router.post("/history", response_model=ImportRunResponse)
async def import_history_files(
    request: ImportHistoryRequest,
    db: Session = Depends(get_db)
):
    """
    Import historical Excel files with Jalali date conversion.
    
    Example:
    ```json
    {
      "files": [
        {
          "path": "data/inputs/history/1404/نوبت_دهی_بیمارانی_که_حضور_پیدا_میکنند_1404.xlsx",
          "year": 1404,
          "sheet": 0
        }
      ]
    }
    ```
    """
    # Create import_runs record
    started_at = datetime.now().isoformat()
    
    try:
        result = db.execute(
            text("""
            INSERT INTO import_runs (run_type, status, started_at, created_by)
            VALUES (:run_type, :status, :started_at, :created_by)
            """),
            {"run_type": "history", "status": "running", "started_at": started_at, "created_by": "api"}
        )
        db.commit()
        import_run_id = result.lastrowid
        
        logger.info(f"Started import run {import_run_id} for {len(request.files)} files")
        
        # Process each file
        all_stats = {
            'files_processed': 0,
            'files_success': 0,
            'files_failed': 0,
            'total_rows': 0,
            'total_success': 0,
            'total_errors': 0,
            'patients_created': 0,
            'appointments_created': 0,
        }
        
        errors = []
        
        for file_req in request.files:
            try:
                logger.info(f"Processing file: {file_req.path}")
                
                stats = import_history_excel(
                    file_path=file_req.path,
                    import_run_id=import_run_id,
                    sheet_name=file_req.sheet,
                    db=db
                )
                
                # Aggregate stats
                all_stats['files_processed'] += 1
                all_stats['files_success'] += 1
                all_stats['total_rows'] += stats.get('total_rows', 0)
                all_stats['total_success'] += stats.get('success', 0)
                all_stats['total_errors'] += stats.get('errors', 0)
                all_stats['patients_created'] += stats.get('patients_created', 0)
                all_stats['appointments_created'] += stats.get('appointments_created', 0)
                
                logger.info(f"File processed successfully: {file_req.path}")
                
            except Exception as e:
                all_stats['files_failed'] += 1
                error_msg = f"File {file_req.path}: {str(e)}"
                errors.append(error_msg)
                logger.error(f"File import failed: {error_msg}\n{traceback.format_exc()}")
        
        # Update import_runs record
        completed_at = datetime.now().isoformat()
        final_status = 'success' if all_stats['files_failed'] == 0 else 'partial'
        
        if all_stats['files_success'] == 0:
            final_status = 'failed'
        
        error_message = "\n".join(errors) if errors else None
        
        db.execute(
            text("""
            UPDATE import_runs 
            SET status = :status, completed_at = :completed_at, stats_json = :stats_json, error_message = :error_message
            WHERE id = :id
            """),
            {"status": final_status, "completed_at": completed_at, "stats_json": str(all_stats), "error_message": error_message, "id": import_run_id}
        )
        db.commit()
        
        logger.info(f"Import run {import_run_id} completed with status: {final_status}")
        
        return ImportRunResponse(
            import_run_id=import_run_id,
            status=final_status,
            stats=all_stats,
            error=error_message
        )
        
    except Exception as e:
        error_msg = str(e)
        logger.error(f"Import run failed: {error_msg}\n{traceback.format_exc()}")
        
        # Try to update status
        try:
            db.execute(
                text("""
                UPDATE import_runs 
                SET status = :status, completed_at = :completed_at, error_message = :error_message
                WHERE id = :id
                """),
                {"status": "failed", "completed_at": datetime.now().isoformat(), "error_message": error_msg[:1000], "id": import_run_id}
            )
            db.commit()
        except:
            pass
        
        raise HTTPException(status_code=500, detail=f"Import failed: {error_msg}")


@router.get("/runs", response_model=List[ImportRunDetail])
async def get_import_runs(
    limit: int = 20,
    db: Session = Depends(get_db)
):
    """
    Get list of recent import runs.
    """
    rows = db.execute(
        text("""
        SELECT id, run_type, status, started_at, completed_at, stats_json, error_message
        FROM import_runs
        ORDER BY started_at DESC
        LIMIT :limit
        """),
        {"limit": limit}
    ).fetchall()
    
    return [
        ImportRunDetail(
            id=row[0],
            run_type=row[1],
            status=row[2],
            started_at=row[3],
            completed_at=row[4],
            stats_json=row[5],
            error_message=row[6]
        )
        for row in rows
    ]


@router.get("/runs/{run_id}", response_model=ImportRunDetail)
async def get_import_run_detail(
    run_id: int,
    db: Session = Depends(get_db)
):
    """
    Get details of a specific import run.
    """
    row = db.execute(
        text("""
        SELECT id, run_type, status, started_at, completed_at, stats_json, error_message
        FROM import_runs
        WHERE id = :run_id
        """),
        {"run_id": run_id}
    ).fetchone()
    
    if not row:
        raise HTTPException(status_code=404, detail="Import run not found")
    
    return ImportRunDetail(
        id=row[0],
        run_type=row[1],
        status=row[2],
        started_at=row[3],
        completed_at=row[4],
        stats_json=row[5],
        error_message=row[6]
    )


@router.get("/runs/{run_id}/errors", response_model=List[ImportErrorRow])
async def get_import_run_errors(
    run_id: int,
    limit: int = 200,
    db: Session = Depends(get_db)
):
    """
    Get error rows for a specific import run.
    """
    rows = db.execute(
        text("""
        SELECT id, row_number, file_name, parse_error, row_json
        FROM stg_appointments
        WHERE import_run_id = :run_id AND parse_status = 'error'
        ORDER BY row_number
        LIMIT :limit
        """),
        {"run_id": run_id, "limit": limit}
    ).fetchall()
    
    return [
        ImportErrorRow(
            id=row[0],
            row_number=row[1],
            file_name=row[2],
            parse_error=row[3] or "",
            row_json=row[4]
        )
        for row in rows
    ]


@router.get("/stats")
async def get_import_stats(db: Session = Depends(get_db)):
    """
    Get overall import statistics.
    """
    stats = {}
    
    # Count total runs
    result = db.execute(text("SELECT COUNT(*) FROM import_runs")).fetchone()
    stats['total_runs'] = result[0] if result else 0
    
    # Count by status
    result = db.execute(
        text("""
        SELECT status, COUNT(*) 
        FROM import_runs 
        GROUP BY status
        """)
    ).fetchall()
    stats['runs_by_status'] = {row[0]: row[1] for row in result}
    
    # Count staging rows
    result = db.execute(text("SELECT COUNT(*) FROM stg_appointments")).fetchone()
    stats['total_staging_rows'] = result[0] if result else 0
    
    # Count errors
    result = db.execute(
        text("SELECT COUNT(*) FROM stg_appointments WHERE parse_status = 'error'")
    ).fetchone()
    stats['total_errors'] = result[0] if result else 0
    
    return stats
