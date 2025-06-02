import os
import zipfile
import shutil
import tempfile
import subprocess
from datetime import datetime
import logging
from app import app, db, scheduler
from models import BackupConfig, Repository, BackupJob
from github_service import GitHubService

logger = logging.getLogger(__name__)

class BackupService:
    def __init__(self):
        self.config = None
        self.github_service = None
        self._load_config()
    
    def _load_config(self):
        """Load current backup configuration"""
        with app.app_context():
            self.config = BackupConfig.query.first()
            if self.config and self.config.github_token:
                self.github_service = GitHubService(self.config.github_token)
    
    def schedule_backup(self, cron_expression):
        """Schedule automatic backups using cron expression"""
        try:
            # Remove existing backup jobs
            self.unschedule_backup()
            
            # Parse cron expression (minute hour day month day_of_week)
            cron_parts = cron_expression.split()
            if len(cron_parts) != 5:
                raise ValueError("Invalid cron expression. Expected format: minute hour day month day_of_week")
            
            minute, hour, day, month, day_of_week = cron_parts
            
            # Add new scheduled job
            scheduler.add_job(
                func=self.backup_all_repositories,
                trigger='cron',
                minute=minute,
                hour=hour,
                day=day,
                month=month,
                day_of_week=day_of_week,
                id='github_backup_job',
                replace_existing=True
            )
            
            logger.info(f"Backup scheduled with cron expression: {cron_expression}")
            
        except Exception as e:
            logger.error(f"Error scheduling backup: {str(e)}")
            raise
    
    def unschedule_backup(self):
        """Remove scheduled backup job"""
        try:
            scheduler.remove_job('github_backup_job')
            logger.info("Backup schedule removed")
        except Exception:
            # Job doesn't exist, which is fine
            pass
    
    def backup_all_repositories(self):
        """Backup all enabled repositories"""
        if not self.config:
            logger.error("No backup configuration found")
            return
        
        with app.app_context():
            # Auto-sync repositories if enabled
            if getattr(self.config, 'auto_sync_enabled', True):
                logger.info("Auto-sync enabled, checking for new repositories...")
                try:
                    self._sync_repositories()
                except Exception as e:
                    logger.error(f"Error during auto-sync: {str(e)}")
            
            enabled_repos = Repository.query.filter_by(enabled=True).all()
            
            if not enabled_repos:
                logger.info("No enabled repositories found for backup")
                return
            
            logger.info(f"Starting backup of {len(enabled_repos)} repositories")
            
            for repo in enabled_repos:
                try:
                    self.backup_repository(repo)
                except Exception as e:
                    logger.error(f"Error backing up repository {repo.full_name}: {str(e)}")
            
            # Clean up old backups
            self.cleanup_old_backups()
    
    def backup_repository(self, repository):
        """Backup a single repository"""
        with app.app_context():
            # Create backup job record
            job = BackupJob(
                repository_id=repository.id,
                status='running',
                started_at=datetime.utcnow()
            )
            db.session.add(job)
            db.session.commit()
            
            try:
                # Create backup directory if it doesn't exist
                os.makedirs(self.config.backup_path, exist_ok=True)
                
                # Create temporary directory for cloning
                with tempfile.TemporaryDirectory() as temp_dir:
                    repo_dir = os.path.join(temp_dir, repository.name)
                    
                    # Clone repository
                    clone_url = repository.clone_url
                    if self.config.github_token:
                        # Add token to clone URL for private repos
                        clone_url = clone_url.replace('https://', f'https://{self.config.github_token}@')
                    
                    logger.info(f"Cloning repository: {repository.full_name}")
                    subprocess.run([
                        'git', 'clone', '--depth', '1', clone_url, repo_dir
                    ], check=True, capture_output=True, text=True)
                    
                    # Create zip file
                    timestamp = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
                    zip_filename = f"{repository.name}_{timestamp}.zip"
                    zip_path = os.path.join(self.config.backup_path, zip_filename)
                    
                    logger.info(f"Creating backup archive: {zip_filename}")
                    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                        for root, dirs, files in os.walk(repo_dir):
                            # Skip .git directory to reduce size
                            if '.git' in dirs:
                                dirs.remove('.git')
                            
                            for file in files:
                                file_path = os.path.join(root, file)
                                arcname = os.path.relpath(file_path, repo_dir)
                                zipf.write(file_path, arcname)
                    
                    # Get file size
                    file_size = os.path.getsize(zip_path)
                    
                    # Update job record
                    job.status = 'completed'
                    job.completed_at = datetime.utcnow()
                    job.backup_file_path = zip_path
                    job.file_size = file_size
                    
                    # Update repository last backup time
                    repository.last_backup = datetime.utcnow()
                    
                    db.session.commit()
                    
                    logger.info(f"Successfully backed up {repository.full_name} ({self._format_file_size(file_size)})")
            
            except subprocess.CalledProcessError as e:
                error_msg = f"Git clone failed: {e.stderr if e.stderr else str(e)}"
                logger.error(error_msg)
                job.status = 'failed'
                job.completed_at = datetime.utcnow()
                job.error_message = error_msg
                db.session.commit()
                raise Exception(error_msg)
            
            except Exception as e:
                error_msg = str(e)
                logger.error(f"Backup failed for {repository.full_name}: {error_msg}")
                job.status = 'failed'
                job.completed_at = datetime.utcnow()
                job.error_message = error_msg
                db.session.commit()
                raise
    
    def cleanup_old_backups(self):
        """Remove old backup files based on max_backups setting"""
        if not self.config or self.config.max_backups <= 0:
            return
        
        with app.app_context():
            # Get all repositories
            repositories = Repository.query.all()
            
            for repo in repositories:
                # Get backup jobs for this repository, ordered by date
                jobs = BackupJob.query.filter_by(
                    repository_id=repo.id,
                    status='completed'
                ).order_by(BackupJob.completed_at.desc()).all()
                
                # Remove excess backups
                if len(jobs) > self.config.max_backups:
                    jobs_to_remove = jobs[self.config.max_backups:]
                    
                    for job in jobs_to_remove:
                        try:
                            # Delete backup file
                            if job.backup_file_path and os.path.exists(job.backup_file_path):
                                os.remove(job.backup_file_path)
                                logger.info(f"Deleted old backup: {job.backup_file_path}")
                            
                            # Delete job record
                            db.session.delete(job)
                        
                        except Exception as e:
                            logger.error(f"Error deleting old backup {job.backup_file_path}: {str(e)}")
                    
                    db.session.commit()
    
    def _sync_repositories(self):
        """Sync repositories from GitHub (used for auto-sync)"""
        if not self.github_service:
            logger.warning("No GitHub service available for auto-sync")
            return
        
        try:
            repos = self.github_service.get_user_repositories()
            synced_count = 0
            
            for repo_data in repos:
                existing_repo = Repository.query.filter_by(full_name=repo_data['full_name']).first()
                if not existing_repo:
                    new_repo = Repository()
                    new_repo.name = repo_data['name']
                    new_repo.full_name = repo_data['full_name']
                    new_repo.clone_url = repo_data['clone_url']
                    new_repo.enabled = True  # Auto-enable new repositories
                    db.session.add(new_repo)
                    synced_count += 1
            
            if synced_count > 0:
                db.session.commit()
                logger.info(f"Auto-sync: Added {synced_count} new repositories")
            else:
                logger.info("Auto-sync: No new repositories found")
                
        except Exception as e:
            logger.error(f"Error during repository auto-sync: {str(e)}")
            raise
    
    def _format_file_size(self, size_bytes):
        """Format file size in human readable format"""
        if size_bytes == 0:
            return "0B"
        
        size_names = ["B", "KB", "MB", "GB", "TB"]
        i = 0
        while size_bytes >= 1024.0 and i < len(size_names) - 1:
            size_bytes /= 1024.0
            i += 1
        
        return f"{size_bytes:.1f} {size_names[i]}"
