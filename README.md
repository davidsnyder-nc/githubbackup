# GitHub Backup Manager

A comprehensive Flask web application for automated GitHub repository backup and management. This tool provides a modern, intuitive web interface for scheduling and managing backups of your GitHub repositories with enterprise-grade features.

![GitHub Backup Manager Dashboard](https://via.placeholder.com/800x400/24292e/ffffff?text=GitHub+Backup+Manager+Dashboard)

## 🚀 Features

### Core Functionality
- **Automated Repository Backup**: Clone and archive repositories as ZIP files with timestamps
- **Scheduled Backups**: Flexible scheduling with daily, weekly, monthly, and custom cron expressions
- **Real-time Monitoring**: Live dashboard with backup status and progress tracking
- **Selective Backup**: Enable/disable backup for individual repositories
- **Bulk Operations**: Enable or disable backup for all repositories at once
- **Download Management**: Direct download of backup files through the web interface

### User Interface
- **GitHub-Inspired Design**: Clean, modern interface matching GitHub's visual style
- **Responsive Layout**: Mobile-friendly design that works on all devices
- **Real-time Updates**: Auto-refreshing dashboard with live job status
- **Intuitive Navigation**: Easy-to-use interface with clear visual feedback
- **12-Hour Time Format**: User-friendly time display with AM/PM format

### Advanced Features
- **Auto-Repository Sync**: Automatically discovers and adds new repositories
- **Token Validation**: Real-time GitHub token validation with helpful error messages
- **Backup Retention**: Configurable maximum number of backups to retain
- **Job History**: Complete backup job history with detailed status information
- **Error Handling**: Comprehensive error reporting and recovery
- **System Purge**: Complete system reset functionality with safety confirmations

### Security & Reliability
- **Secure Token Storage**: GitHub tokens stored securely in the database
- **Input Validation**: Comprehensive validation of all user inputs
- **Error Recovery**: Robust error handling with detailed logging
- **Database Integrity**: SQLAlchemy ORM with proper transaction management
- **Safe Operations**: No destructive browser confirmations, all feedback through the interface

## 📋 Requirements

- Python 3.8 or higher
- PostgreSQL database
- GitHub Personal Access Token
- Modern web browser

## 🛠️ Installation

### 1. Clone the Repository

```bash
git clone https://github.com/davidsnyder-nc/githubbackup.git
cd githubbackup
```

### 2. Set Up Python Environment

```bash
# Create virtual environment
python -m venv venv

# Activate virtual environment
# On Windows:
venv\Scripts\activate
# On macOS/Linux:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 3. Database Setup

Create a PostgreSQL database and set the connection string:

```bash
export DATABASE_URL="postgresql://username:password@localhost/githubbackup"
```

### 4. Environment Variables

Set the required environment variables:

```bash
export SESSION_SECRET="your-secret-key-here"
export DATABASE_URL="postgresql://username:password@localhost/githubbackup"
```

### 5. Initialize Database

The application will automatically create the necessary database tables on first run.

### 6. Run the Application

```bash
python main.py
```

Or use Gunicorn for production:

```bash
gunicorn --bind 0.0.0.0:5000 --reuse-port --reload main:app
```

The application will be available at `http://localhost:5000`

## ⚙️ Configuration

### GitHub Token Setup

1. Go to [GitHub Settings > Developer settings > Personal access tokens](https://github.com/settings/tokens)
2. Click "Generate new token (classic)"
3. Select the following scopes:
   - `repo` - Access repositories
   - `user` - Read user profile
4. Copy the generated token
5. Enter the token in the application's configuration page

### Backup Configuration

- **Backup Directory**: Local directory where ZIP files will be stored
- **Max Backups**: Maximum number of backup files to retain per repository
- **Auto-Sync**: Automatically discover and add new repositories
- **Schedule**: Configure automated backup timing

## 📅 Scheduling Options

### Built-in Presets
- **Daily**: Backup every day at specified time
- **Weekly**: Backup once per week on chosen day
- **Monthly**: Backup once per month on chosen date

### Custom Scheduling
Use standard cron expressions for advanced scheduling:
- `0 2 * * *` - Daily at 2:00 AM
- `0 14 * * 1-5` - Weekdays at 2:00 PM
- `0 */6 * * *` - Every 6 hours

## 🎯 Usage

### Initial Setup
1. Access the application at `http://localhost:5000`
2. Navigate to Configuration
3. Enter your GitHub Personal Access Token
4. Configure backup directory and retention settings
5. Set up backup schedule

### Managing Repositories
1. Go to the Repositories page
2. Enable/disable backup for individual repositories
3. Use bulk operations to manage all repositories at once
4. New repositories are automatically discovered and can be enabled

### Monitoring Backups
1. Check the Dashboard for overview and status
2. View detailed job history on the Status page
3. Download completed backup files
4. Monitor real-time progress during active backups

### System Management
1. Modify configuration settings as needed
2. Use the Danger Zone for complete system reset if required
3. Monitor application logs for troubleshooting

## 📁 Project Structure

```
githubbackup/
├── app.py              # Flask application setup
├── main.py             # Application entry point
├── models.py           # Database models
├── routes.py           # Web routes and handlers
├── github_service.py   # GitHub API integration
├── backup_service.py   # Backup logic and scheduling
├── static/             # CSS, JavaScript, and assets
│   ├── css/
│   └── js/
├── templates/          # Jinja2 HTML templates
├── backups/           # Default backup storage directory
└── instance/          # SQLite database (if not using PostgreSQL)
```

## 🔧 Dependencies

### Core Framework
- `Flask` - Web framework
- `Flask-SQLAlchemy` - Database ORM
- `Gunicorn` - WSGI HTTP Server

### Database & Scheduling
- `psycopg2-binary` - PostgreSQL adapter
- `APScheduler` - Advanced Python Scheduler

### External Services
- `requests` - HTTP library for GitHub API
- `email-validator` - Email validation

### Utilities
- `Werkzeug` - WSGI utilities
- `SQLAlchemy` - SQL toolkit

## 🔐 Security Considerations

- Store GitHub tokens securely and never commit them to version control
- Use environment variables for sensitive configuration
- Run the application behind a reverse proxy (nginx) in production
- Enable HTTPS for production deployments
- Regularly rotate GitHub personal access tokens
- Implement proper backup file access controls

## 🚀 Production Deployment

### Using Docker (Recommended)

```dockerfile
FROM python:3.11-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .
EXPOSE 5000

CMD ["gunicorn", "--bind", "0.0.0.0:5000", "main:app"]
```

### Using systemd

Create a systemd service file:

```ini
[Unit]
Description=GitHub Backup Manager
After=network.target

[Service]
User=www-data
WorkingDirectory=/path/to/githubbackup
Environment=DATABASE_URL=postgresql://...
Environment=SESSION_SECRET=...
ExecStart=/path/to/venv/bin/gunicorn --bind 0.0.0.0:5000 main:app
Restart=always

[Install]
WantedBy=multi-user.target
```

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📝 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🆘 Support

- **Issues**: Report bugs and request features via [GitHub Issues](https://github.com/davidsnyder-nc/githubbackup/issues)
- **Documentation**: Check this README and inline code documentation
- **Logs**: Application logs provide detailed information for troubleshooting

## 🔄 Version History

### v1.0.0 (Current)
- Initial release
- Core backup functionality
- Web-based configuration
- Automated scheduling
- GitHub API integration
- Modern responsive UI

---

**Built with ❤️ for developers who value their code**