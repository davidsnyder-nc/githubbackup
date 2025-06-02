from app import db
from datetime import datetime
from sqlalchemy import Text

class BackupConfig(db.Model):
    """Configuration settings for GitHub backup"""
    id = db.Column(db.Integer, primary_key=True)
    github_token = db.Column(db.String(256), nullable=False)
    backup_path = db.Column(db.String(512), default='./backups')
    max_backups = db.Column(db.Integer, default=5)
    schedule_enabled = db.Column(db.Boolean, default=False)
    schedule_cron = db.Column(db.String(64), default='0 2 * * *')  # Daily at 2 AM
    auto_sync_enabled = db.Column(db.Boolean, default=True)  # Auto-sync new repositories
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class Repository(db.Model):
    """GitHub repositories to backup"""
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(256), nullable=False)
    full_name = db.Column(db.String(512), nullable=False)
    clone_url = db.Column(db.String(512), nullable=False)
    enabled = db.Column(db.Boolean, default=True)
    last_backup = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class BackupJob(db.Model):
    """Backup job history and status"""
    id = db.Column(db.Integer, primary_key=True)
    repository_id = db.Column(db.Integer, db.ForeignKey('repository.id'), nullable=True)
    status = db.Column(db.String(32), default='pending')  # pending, running, completed, failed
    started_at = db.Column(db.DateTime, default=datetime.utcnow)
    completed_at = db.Column(db.DateTime)
    error_message = db.Column(Text)
    backup_file_path = db.Column(db.String(512))
    file_size = db.Column(db.BigInteger)
    
    repository = db.relationship('Repository', backref='backup_jobs')

class AppSettings(db.Model):
    """General application settings"""
    id = db.Column(db.Integer, primary_key=True)
    key = db.Column(db.String(128), unique=True, nullable=False)
    value = db.Column(Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
