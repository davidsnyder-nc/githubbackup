from flask import render_template, request, redirect, url_for, flash, jsonify, send_file
from app import app, db, scheduler
from models import BackupConfig, Repository, BackupJob, AppSettings
from github_service import GitHubService
from backup_service import BackupService
from datetime import datetime
import os
import logging

logger = logging.getLogger(__name__)

@app.route('/')
def index():
    """Main dashboard showing backup status and recent jobs"""
    config = BackupConfig.query.first()
    recent_jobs = BackupJob.query.order_by(BackupJob.started_at.desc()).limit(10).all()
    total_repos = Repository.query.filter_by(enabled=True).count()
    
    # Get scheduler status
    scheduler_running = scheduler.running
    next_job = None
    if scheduler_running:
        jobs = scheduler.get_jobs()
        if jobs:
            next_job = min(job.next_run_time for job in jobs if job.next_run_time)
    
    return render_template('index.html', 
                         config=config,
                         recent_jobs=recent_jobs,
                         total_repos=total_repos,
                         scheduler_running=scheduler_running,
                         next_job=next_job)

@app.route('/config', methods=['GET', 'POST'])
def config():
    """Configuration page for GitHub token and backup settings"""
    if request.method == 'POST':
        github_token = request.form.get('github_token')
        backup_path = request.form.get('backup_path', './backups')
        max_backups = int(request.form.get('max_backups', 5))
        schedule_enabled = 'schedule_enabled' in request.form
        auto_sync_enabled = 'auto_sync_enabled' in request.form
        schedule_cron = request.form.get('schedule_cron', '0 2 * * *')
        
        # Validate GitHub token
        if github_token:
            github_service = GitHubService(github_token)
            if not github_service.test_connection():
                flash('Invalid GitHub token. Please check your token and try again.', 'error')
                return render_template('config.html')
        
        # Create or update config
        config = BackupConfig.query.first()
        if not config:
            config = BackupConfig()
            db.session.add(config)
        
        config.github_token = github_token
        config.backup_path = backup_path
        config.max_backups = max_backups
        config.schedule_enabled = schedule_enabled
        config.auto_sync_enabled = auto_sync_enabled
        # Use the final_cron value if provided (from the new UI), otherwise use schedule_cron
        final_cron = request.form.get('final_cron', schedule_cron)
        config.schedule_cron = final_cron
        config.updated_at = datetime.utcnow()
        
        try:
            db.session.commit()
            
            # Create backup directory if it doesn't exist
            os.makedirs(backup_path, exist_ok=True)
            
            # Auto-sync repositories when token is configured
            if github_token:
                try:
                    github_service = GitHubService(github_token)
                    repos = github_service.get_user_repositories()
                    synced_count = 0
                    
                    for repo_data in repos:
                        existing_repo = Repository.query.filter_by(full_name=repo_data['full_name']).first()
                        if not existing_repo:
                            new_repo = Repository()
                            new_repo.name = repo_data['name']
                            new_repo.full_name = repo_data['full_name']
                            new_repo.clone_url = repo_data['clone_url']
                            new_repo.enabled = True
                            db.session.add(new_repo)
                            synced_count += 1
                    
                    if synced_count > 0:
                        db.session.commit()
                        flash(f'Configuration saved and {synced_count} repositories synced!', 'success')
                    else:
                        flash('Configuration saved successfully!', 'success')
                        
                except Exception as e:
                    logger.warning(f"Could not auto-sync repositories: {str(e)}")
                    flash('Configuration saved, but could not sync repositories automatically.', 'warning')
            
            # Update scheduler
            backup_service = BackupService()
            if schedule_enabled:
                backup_service.schedule_backup(final_cron)
            else:
                backup_service.unschedule_backup()
                
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error saving configuration: {str(e)}")
            flash(f'Error saving configuration: {str(e)}', 'error')
    
    config = BackupConfig.query.first()
    return render_template('config.html', config=config)

@app.route('/repositories')
def repositories():
    """List and manage repositories"""
    config = BackupConfig.query.first()
    if not config or not config.github_token:
        flash('Please configure GitHub token first.', 'warning')
        return redirect(url_for('config'))
    
    repositories = Repository.query.all()
    return render_template('repositories.html', repositories=repositories)

@app.route('/sync-repositories', methods=['POST'])
def sync_repositories():
    """Sync repositories from GitHub"""
    config = BackupConfig.query.first()
    if not config or not config.github_token:
        flash('Please configure GitHub token first.', 'error')
        return redirect(url_for('config'))
    
    try:
        github_service = GitHubService(config.github_token)
        repos = github_service.get_user_repositories()
        
        synced_count = 0
        for repo_data in repos:
            existing_repo = Repository.query.filter_by(full_name=repo_data['full_name']).first()
            if not existing_repo:
                new_repo = Repository()
                new_repo.name = repo_data['name']
                new_repo.full_name = repo_data['full_name']
                new_repo.clone_url = repo_data['clone_url']
                db.session.add(new_repo)
                synced_count += 1
        
        db.session.commit()
        flash(f'Successfully synced {synced_count} new repositories.', 'success')
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error syncing repositories: {str(e)}")
        flash(f'Error syncing repositories: {str(e)}', 'error')
    
    return redirect(url_for('repositories'))

@app.route('/bulk-toggle-repositories', methods=['POST'])
def bulk_toggle_repositories():
    """Bulk enable/disable repositories"""
    try:
        data = request.get_json()
        action = data.get('action')
        
        if action == 'enable_all':
            repositories = Repository.query.all()
            for repo in repositories:
                repo.enabled = True
            db.session.commit()
            return jsonify({'success': True, 'message': 'All repositories enabled for backup'})
            
        elif action == 'disable_all':
            repositories = Repository.query.all()
            for repo in repositories:
                repo.enabled = False
            db.session.commit()
            return jsonify({'success': True, 'message': 'All repositories disabled for backup'})
            
        else:
            return jsonify({'success': False, 'message': 'Invalid action'})
            
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error in bulk toggle: {str(e)}")
        return jsonify({'success': False, 'message': str(e)})

@app.route('/toggle-repository/<int:repo_id>', methods=['POST'])
def toggle_repository(repo_id):
    """Enable/disable repository for backup"""
    repository = Repository.query.get_or_404(repo_id)
    repository.enabled = not repository.enabled
    
    try:
        db.session.commit()
        status = "enabled" if repository.enabled else "disabled"
        flash(f'Repository {repository.name} {status} for backup.', 'success')
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error toggling repository: {str(e)}")
        flash(f'Error updating repository: {str(e)}', 'error')
    
    return redirect(url_for('repositories'))

@app.route('/backup-now', methods=['POST'])
def backup_now():
    """Trigger immediate backup of all enabled repositories"""
    try:
        backup_service = BackupService()
        backup_service.backup_all_repositories()
        flash('Backup started successfully! Check the status page for progress.', 'success')
    except Exception as e:
        logger.error(f"Error starting backup: {str(e)}")
        flash(f'Error starting backup: {str(e)}', 'error')
    
    return redirect(url_for('status'))

@app.route('/status')
def status():
    """Backup status and job history"""
    jobs = BackupJob.query.order_by(BackupJob.started_at.desc()).limit(50).all()
    running_jobs = BackupJob.query.filter_by(status='running').all()
    
    return render_template('status.html', jobs=jobs, running_jobs=running_jobs)

@app.route('/download-backup/<int:job_id>')
def download_backup(job_id):
    """Download a backup file"""
    job = BackupJob.query.get_or_404(job_id)
    
    if not job.backup_file_path or not os.path.exists(job.backup_file_path):
        flash('Backup file not found.', 'error')
        return redirect(url_for('status'))
    
    try:
        return send_file(
            job.backup_file_path,
            as_attachment=True,
            download_name=os.path.basename(job.backup_file_path)
        )
    except Exception as e:
        logger.error(f"Error downloading backup: {str(e)}")
        flash('Error downloading backup file.', 'error')
        return redirect(url_for('status'))

@app.route('/delete-job/<int:job_id>', methods=['POST'])
def delete_job(job_id):
    """Delete a backup job record"""
    job = BackupJob.query.get_or_404(job_id)
    
    try:
        # Delete backup file if it exists
        if job.backup_file_path and os.path.exists(job.backup_file_path):
            os.remove(job.backup_file_path)
        
        db.session.delete(job)
        db.session.commit()
        flash('Backup job deleted successfully.', 'success')
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error deleting job: {str(e)}")
        flash(f'Error deleting job: {str(e)}', 'error')
    
    return redirect(url_for('status'))

@app.route('/purge-system', methods=['POST'])
def purge_system():
    """Purge all system data and settings"""
    try:
        # Stop scheduler
        if scheduler.running:
            scheduler.shutdown(wait=False)
        
        # Get backup path before deleting config
        config = BackupConfig.query.first()
        backup_path = config.backup_path if config else './backups'
        
        # Delete all database records
        BackupJob.query.delete()
        Repository.query.delete()
        BackupConfig.query.delete()
        AppSettings.query.delete()
        db.session.commit()
        
        # Delete all backup files
        if os.path.exists(backup_path):
            import shutil
            shutil.rmtree(backup_path)
            logger.info(f"Deleted backup directory: {backup_path}")
        
        # Recreate backup directory
        os.makedirs(backup_path, exist_ok=True)
        
        flash('All system data has been permanently purged. The system has been reset to initial state.', 'success')
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error purging system: {str(e)}")
        flash(f'Error purging system: {str(e)}', 'error')
    
    return redirect(url_for('config'))

@app.errorhandler(404)
def not_found(error):
    return render_template('404.html'), 404

@app.errorhandler(500)
def internal_error(error):
    db.session.rollback()
    return render_template('500.html'), 500
