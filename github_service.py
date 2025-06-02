import requests
import logging
from typing import List, Dict, Optional

logger = logging.getLogger(__name__)

class GitHubService:
    def __init__(self, token: str):
        self.token = token
        self.base_url = "https://api.github.com"
        self.headers = {
            "Authorization": f"token {token}",
            "Accept": "application/vnd.github.v3+json",
            "User-Agent": "GitHub-Backup-App/1.0"
        }
    
    def test_connection(self) -> bool:
        """Test if the GitHub token is valid"""
        try:
            response = requests.get(
                f"{self.base_url}/user",
                headers=self.headers,
                timeout=10
            )
            return response.status_code == 200
        except Exception as e:
            logger.error(f"GitHub connection test failed: {str(e)}")
            return False
    
    def get_user_info(self) -> Optional[Dict]:
        """Get authenticated user information"""
        try:
            response = requests.get(
                f"{self.base_url}/user",
                headers=self.headers,
                timeout=10
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Error getting user info: {str(e)}")
            return None
    
    def get_user_repositories(self) -> List[Dict]:
        """Get all repositories for the authenticated user"""
        repositories = []
        page = 1
        per_page = 100
        
        try:
            while True:
                response = requests.get(
                    f"{self.base_url}/user/repos",
                    headers=self.headers,
                    params={
                        "page": page,
                        "per_page": per_page,
                        "sort": "updated",
                        "direction": "desc"
                    },
                    timeout=30
                )
                response.raise_for_status()
                
                repos = response.json()
                if not repos:
                    break
                
                for repo in repos:
                    repositories.append({
                        "name": repo["name"],
                        "full_name": repo["full_name"],
                        "clone_url": repo["clone_url"],
                        "private": repo["private"],
                        "description": repo.get("description", ""),
                        "updated_at": repo["updated_at"],
                        "size": repo["size"],
                        "language": repo.get("language"),
                        "default_branch": repo["default_branch"]
                    })
                
                # Check if we've got all repositories
                if len(repos) < per_page:
                    break
                
                page += 1
            
            logger.info(f"Retrieved {len(repositories)} repositories from GitHub")
            return repositories
        
        except requests.exceptions.RequestException as e:
            logger.error(f"Error fetching repositories: {str(e)}")
            raise Exception(f"Failed to fetch repositories from GitHub: {str(e)}")
        except Exception as e:
            logger.error(f"Unexpected error fetching repositories: {str(e)}")
            raise Exception(f"Unexpected error: {str(e)}")
    
    def get_repository_details(self, full_name: str) -> Optional[Dict]:
        """Get detailed information about a specific repository"""
        try:
            response = requests.get(
                f"{self.base_url}/repos/{full_name}",
                headers=self.headers,
                timeout=10
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Error getting repository details for {full_name}: {str(e)}")
            return None
    
    def get_repository_branches(self, full_name: str) -> List[Dict]:
        """Get all branches for a repository"""
        try:
            response = requests.get(
                f"{self.base_url}/repos/{full_name}/branches",
                headers=self.headers,
                timeout=10
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Error getting branches for {full_name}: {str(e)}")
            return []
    
    def get_rate_limit(self) -> Optional[Dict]:
        """Get current rate limit status"""
        try:
            response = requests.get(
                f"{self.base_url}/rate_limit",
                headers=self.headers,
                timeout=10
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Error getting rate limit: {str(e)}")
            return None
