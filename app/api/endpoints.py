from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
from app.core.ingest import ingestor
from app.core.gitops import gitops
import duckdb
import os
from app.core.config import settings

router = APIRouter()

class IngestRequest(BaseModel):
    pass

class QueryRequest(BaseModel):
    sql: str

@router.post("/ingest")
async def ingest_data(payload: List[Dict[str, Any]] | Dict[str, Any], background_tasks: BackgroundTasks):
    """
    Ingests data into the Exocortex.
    """
    background_tasks.add_task(ingestor.process_batch, payload)
    return {"status": "accepted", "message": "Processing started"}

@router.post("/sync")
async def trigger_sync():
    """
    Manually triggers a git pull/push.
    """
    success = gitops.pull()
    if not success:
        raise HTTPException(status_code=500, detail="Sync failed")
    return {"status": "success", "message": "Git pull completed"}

@router.post("/query")
async def query_data(request: QueryRequest):
    """
    Executes a SQL query against the local data using DuckDB.
    """
    try:
        # We need to execute the query in the context of the vault path
        # or rewrite the query. 
        # DuckDB runs in CWD by default.
        # We temporarily change dir to vault_path (thread safety warning!)
        # Or better, we tell the user to assume paths are relative to vault, 
        # but since we can't easily change DuckDB's base dir per connection without CWD change,
        # we can wrap the execution.
        
        cwd = os.getcwd()
        try:
            os.chdir(settings.vault_path)
            con = duckdb.connect(database=':memory:')
            # Execute query and fetch as Polars DataFrame (no Pandas dependency)
            df = con.execute(request.sql).pl()
            result = df.to_dicts()
        finally:
            os.chdir(cwd)

        return {"status": "success", "data": result}
        
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
