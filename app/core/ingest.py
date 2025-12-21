import os
import json
import time
from datetime import datetime
import polars as pl
import pyarrow as pa
import lancedb
from loguru import logger
from app.core.config import settings
from app.core.gitops import gitops

class DataIngestor:
    def __init__(self):
        self.vault_path = settings.vault_path
        # Ensure directories exist
        self.data_dir = os.path.join(self.vault_path, "data", "sensors")
        
    def process_batch(self, payload: dict | list[dict]) -> bool:
        """
        Ingests data, converts to Arrow/Polars, saves to LanceDB/Parquet, 
        and triggers GitOps sync.
        """
        start_time = time.time()
        
        # Normalize input to list of dicts
        if isinstance(payload, dict):
            data = [payload]
        else:
            data = payload
            
        if not data:
            logger.warning("Empty data batch received.")
            return False

        try:
            # 1. Zero Copy Ingest
            df = pl.DataFrame(data)
            
            # Add timestamp if not present
            if "timestamp" not in df.columns:
                df = df.with_columns(pl.lit(datetime.now()).alias("timestamp"))
                
            # Convert to Arrow Table (implicit check if needed)
            # arrow_table = df.to_arrow()
            
            # 2. Persist
            timestamp_str = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
            filename = f"sensors_{timestamp_str}.parquet"
            
            # Ensure output directory exists (it might be inside the repo)
            os.makedirs(self.data_dir, exist_ok=True)
            
            file_path = os.path.join(self.data_dir, filename)
            rel_path = os.path.join("data", "sensors", filename)
            
            # Write Parquet
            df.write_parquet(file_path)
            
            logger.info(f"Persisted batch to {file_path} in {time.time() - start_time:.4f}s")
            
            # 3. Trigger GitOps (Sync)
            try:
                gitops.sync_data(rel_path)
            except Exception as e:
                logger.error(f"GitOps sync failed: {e}")
            
            return True
            
        except Exception as e:
            logger.exception(f"Error processing batch: {e}")
            return False

ingestor = DataIngestor()
