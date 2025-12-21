import os
import subprocess
from loguru import logger
from app.core.config import settings

class GitOpsManager:
    def __init__(self):
        self.repo_path = settings.vault_path
        self.repo_url = settings.git_repo_url

    def _run_command(self, cmd: list[str], cwd: str = None) -> bool:
        """Runs a shell command and returns True if successful."""
        try:
            # Mask secrets in logs
            masked_cmd = []
            for arg in cmd:
                if any(secret in arg for secret in [settings.minio_secret_key, settings.minio_access_key] if secret):
                     masked_cmd.append("***")
                else:
                     masked_cmd.append(arg)
            
            logger.debug(f"Running command: {' '.join(masked_cmd)} in {cwd or 'default cwd'}")
            result = subprocess.run(
                cmd, 
                cwd=cwd, 
                capture_output=True, 
                text=True, 
                check=True
            )
            logger.info(f"Command succeeded: {result.stdout.strip()}")
            return True
        except subprocess.CalledProcessError as e:
            logger.error(f"Command failed: {e.stderr.strip()}")
            return False

    def bootstrap(self):
        """
        Initializes the data vault.
        Checks if /data/vault exists and is a git repo.
        If not, clones from git_repo_url.
        If yes, pulls latest changes.
        Then configures DVC remote.
        """
        if not self.repo_url:
            logger.warning("No git_repo_url configured. Skipping GitOps bootstrap.")
            return

        # Check if repo exists
        git_dir = os.path.join(self.repo_path, ".git")
        if os.path.exists(git_dir):
            logger.info("Existing git repository found. Pulling latest changes...")
            self.pull()
        else:
            logger.info(f"No git repository found at {self.repo_path}. Cloning...")
            # Ensure parent dir exists
            os.makedirs(settings.data_path, exist_ok=True)
            # Remove the target dir if it exists but isn't a git repo (to avoid clone errors)
            if os.path.exists(self.repo_path):
                 logger.warning(f"Directory {self.repo_path} exists but is not a git repo. Removing it.")
                 # Use shutil for recursive delete if needed, but subprocess rm -rf is often safer/easier in container
                 subprocess.run(["rm", "-rf", self.repo_path], check=True)
            
            success = self._run_command(["git", "clone", self.repo_url, self.repo_path])
            if not success:
                logger.error("Failed to clone repository.")
                return

        # Configure Git Identity (for automated commits)
        self._configure_git_identity()

        # Configure DVC
        self._configure_dvc()

    def _configure_git_identity(self):
        """Configures git user/email for the repo if not set."""
        # We set it locally for the repo
        self._run_command(["git", "config", "user.name", "Exocortex Bot"], cwd=self.repo_path)
        self._run_command(["git", "config", "user.email", "bot@exocortex.local"], cwd=self.repo_path)

    def pull(self):
        """Pulls changes from git."""
        return self._run_command(["git", "pull", "--ff-only"], cwd=self.repo_path)

    def _configure_dvc(self):
        """Configures DVC remote based on settings."""
        if not (settings.minio_endpoint and settings.minio_access_key and settings.minio_secret_key):
             logger.warning("MinIO credentials incomplete. Skipping DVC configuration.")
             return

        logger.info("Configuring DVC remote...")
        
        remote_name = "storage"
        
        try:
            # Set endpoint
            self._run_command(["dvc", "remote", "modify", "--local", remote_name, "endpointurl", settings.minio_endpoint], cwd=self.repo_path)
            self._run_command(["dvc", "remote", "modify", "--local", remote_name, "access_key_id", settings.minio_access_key], cwd=self.repo_path)
            self._run_command(["dvc", "remote", "modify", "--local", remote_name, "secret_access_key", settings.minio_secret_key], cwd=self.repo_path)
            # Ensure it works with MinIO (s3 compatible)
            self._run_command(["dvc", "remote", "modify", "--local", remote_name, "use_ssl", "false"], cwd=self.repo_path) # Assuming internal MinIO often no SSL, or check http/https in endpoint
            
            logger.info("DVC remote credentials configured.")
        except Exception as e:
            logger.error(f"Error configuring DVC: {e}")

    def sync_data(self, filepath: str):
        """
        Adds a file to DVC, pushes to MinIO, and commits the .dvc file to Git.
        filepath is relative to vault_path.
        """
        full_path = os.path.join(self.repo_path, filepath)
        if not os.path.exists(full_path):
            logger.error(f"File {full_path} does not exist.")
            return False

        logger.info(f"Syncing {filepath}...")
        
        # 1. DVC Add
        if not self._run_command(["dvc", "add", filepath], cwd=self.repo_path):
            return False
            
        # 2. DVC Push
        if not self._run_command(["dvc", "push", filepath], cwd=self.repo_path):
            logger.error("DVC Push failed. Continuing... (Fail-Fast logged)")
            pass 

        # 3. Git Commit
        dvc_file = filepath + ".dvc"
        self._run_command(["git", "add", dvc_file, ".gitignore"], cwd=self.repo_path)
        
        commit_msg = f"chore(data): update {filepath}"
        self._run_command(["git", "commit", "-m", commit_msg], cwd=self.repo_path)
        
        # 4. Git Push
        if not self._run_command(["git", "push"], cwd=self.repo_path):
             logger.error("Git Push failed.")
             
        return True

gitops = GitOpsManager()
