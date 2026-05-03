"""
GitHub Repository Parser
Fetches repository context from GitHub REST API
"""
import httpx
import re
from typing import Optional
from config import Config
import structlog

logger = structlog.get_logger()


class GitHubParserError(Exception):
    """Custom exception for GitHub parsing errors"""
    pass


def parse_github_url(url: str) -> tuple[str, str]:
    """
    Parse GitHub URL to extract owner and repo name
    
    Handles formats:
    - https://github.com/owner/repo
    - https://github.com/owner/repo.git
    - https://github.com/owner/repo/tree/main
    - github.com/owner/repo
    
    Args:
        url: GitHub repository URL
        
    Returns:
        Tuple of (owner, repo_name)
        
    Raises:
        GitHubParserError: If URL is invalid
    """
    url = url.strip().rstrip('/').replace('.git', '')
    
    # Add https if missing
    if not url.startswith('http'):
        url = f'https://{url}'
    
    # Match github.com/owner/repo pattern
    pattern = r'github\.com[/:]([^/]+)/([^/]+)'
    match = re.search(pattern, url)
    
    if not match:
        raise GitHubParserError(
            "Invalid GitHub URL format. Expected: https://github.com/owner/repo"
        )
    
    owner, repo = match.groups()
    
    # Remove any trailing path segments
    repo = repo.split('/')[0]
    
    logger.info("parsed_github_url", owner=owner, repo=repo)
    return owner, repo


async def fetch_repo_metadata(owner: str, repo: str) -> dict:
    """
    Fetch repository metadata from GitHub API
    
    Args:
        owner: Repository owner
        repo: Repository name
        
    Returns:
        Dictionary with repo metadata
        
    Raises:
        GitHubParserError: On API errors
    """
    url = f"https://api.github.com/repos/{owner}/{repo}"
    headers = Config.get_github_headers()
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            response = await client.get(url, headers=headers)
            
            if response.status_code == 404:
                raise GitHubParserError("Repository not found. It may not exist or may be private.")
            elif response.status_code == 403:
                raise GitHubParserError("This repository is private or GitHub rate limit exceeded.")
            elif response.status_code != 200:
                raise GitHubParserError(f"GitHub API error: {response.status_code}")
            
            data = response.json()
            
            metadata = {
                "name": data.get("name"),
                "full_name": data.get("full_name"),
                "description": data.get("description") or "No description provided",
                "language": data.get("language") or "Unknown",
                "stars": data.get("stargazers_count", 0),
                "forks": data.get("forks_count", 0),
                "open_issues": data.get("open_issues_count", 0),
                "default_branch": data.get("default_branch", "main"),
                "topics": data.get("topics", []),
                "created_at": data.get("created_at"),
                "updated_at": data.get("updated_at"),
                "homepage": data.get("homepage"),
                "license": data.get("license", {}).get("name") if data.get("license") else None,
                "size": data.get("size", 0)
            }
            
            logger.info("fetched_repo_metadata", repo=metadata["full_name"], stars=metadata["stars"])
            return metadata
            
        except httpx.RequestError as e:
            raise GitHubParserError(f"Network error while fetching repository: {str(e)}")


async def fetch_file_tree(owner: str, repo: str, branch: str = "main") -> list[dict]:
    """
    Fetch complete file tree from repository
    
    Args:
        owner: Repository owner
        repo: Repository name
        branch: Branch name (default: main)
        
    Returns:
        List of file objects with path, type, and size
        
    Raises:
        GitHubParserError: On API errors
    """
    url = f"https://api.github.com/repos/{owner}/{repo}/git/trees/{branch}?recursive=1"
    headers = Config.get_github_headers()
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            response = await client.get(url, headers=headers)
            
            if response.status_code == 404:
                # Try 'master' branch if 'main' doesn't exist
                if branch == "main":
                    logger.info("main_branch_not_found", trying="master")
                    return await fetch_file_tree(owner, repo, "master")
                raise GitHubParserError("Repository branch not found")
            elif response.status_code == 403:
                raise GitHubParserError("GitHub rate limit exceeded. Please try again later.")
            elif response.status_code != 200:
                raise GitHubParserError(f"Failed to fetch file tree: {response.status_code}")
            
            data = response.json()
            tree = data.get("tree", [])
            
            # Filter out unwanted directories and files
            excluded_patterns = [
                'node_modules', '.git', 'dist', 'build', '__pycache__',
                '.next', '.cache', 'coverage', '.venv', 'venv',
                'vendor', 'target', 'out', '.idea', '.vscode'
            ]
            
            files = []
            for item in tree:
                if item.get("type") == "blob":  # Only files, not directories
                    path = item.get("path", "")
                    
                    # Skip excluded directories
                    if any(excluded in path for excluded in excluded_patterns):
                        continue
                    
                    files.append({
                        "path": path,
                        "size": item.get("size", 0),
                        "sha": item.get("sha")
                    })
            
            logger.info("fetched_file_tree", total_files=len(files))
            return files
            
        except httpx.RequestError as e:
            raise GitHubParserError(f"Network error while fetching file tree: {str(e)}")


async def fetch_file_content(owner: str, repo: str, path: str, branch: str = "main") -> Optional[str]:
    """
    Fetch content of a specific file
    
    Args:
        owner: Repository owner
        repo: Repository name
        path: File path in repository
        branch: Branch name
        
    Returns:
        File content as string, or None if file is too large or binary
    """
    url = f"https://api.github.com/repos/{owner}/{repo}/contents/{path}?ref={branch}"
    headers = Config.get_github_headers()
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            response = await client.get(url, headers=headers)
            
            if response.status_code != 200:
                return None
            
            # Get raw content
            raw_url = response.json().get("download_url")
            if not raw_url:
                return None
            
            raw_response = await client.get(raw_url)
            if raw_response.status_code != 200:
                return None
            
            content = raw_response.text
            
            # Limit file size
            max_size = Config.MAX_FILE_SIZE_KB * 1024
            if len(content) > max_size:
                logger.debug("file_too_large", path=path, size=len(content))
                return content[:max_size] + "\n... (truncated)"
            
            return content
            
        except Exception as e:
            logger.debug("failed_to_fetch_file", path=path, error=str(e))
            return None


def identify_key_files(files: list[dict]) -> list[str]:
    """
    Identify key files that should be analyzed
    
    Args:
        files: List of file objects
        
    Returns:
        List of file paths to analyze (limited by MAX_FILES_TO_READ)
    """
    key_patterns = [
        # Documentation (highest priority)
        (r'^README\.md$', 100),
        (r'^README\.txt$', 95),
        (r'^CONTRIBUTING\.md$', 90),
        (r'^CHANGELOG\.md$', 85),
        
        # Configuration files
        (r'^package\.json$', 95),
        (r'^requirements\.txt$', 95),
        (r'^pyproject\.toml$', 95),
        (r'^Cargo\.toml$', 95),
        (r'^go\.mod$', 95),
        (r'^pom\.xml$', 95),
        (r'^composer\.json$', 95),
        (r'^Gemfile$', 95),
        (r'^\.env\.example$', 90),
        (r'^\.env\.sample$', 90),
        (r'^config\.(js|ts|json|yaml|yml)$', 85),
        (r'^tsconfig\.json$', 80),
        (r'^webpack\.config\.js$', 80),
        (r'^vite\.config\.(js|ts)$', 80),
        
        # Docker
        (r'^Dockerfile$', 85),
        (r'^docker-compose\.yml$', 85),
        
        # Main entry points
        (r'^(src/)?main\.(py|js|ts|go|rs)$', 90),
        (r'^(src/)?index\.(js|ts)$', 90),
        (r'^(src/)?app\.(py|js|ts)$', 90),
        (r'^(src/)?server\.(py|js|ts)$', 90),
        (r'^manage\.py$', 85),
        
        # Common structure files
        (r'^src/App\.(jsx?|tsx?)$', 85),
        (r'^src/routes\.(jsx?|tsx?|py)$', 80),
        (r'^src/api/.*\.(py|js|ts)$', 75),
    ]
    
    scored_files = []
    file_paths = [f["path"] for f in files]
    
    for path in file_paths:
        score = 0
        for pattern, pattern_score in key_patterns:
            if re.search(pattern, path, re.IGNORECASE):
                score = max(score, pattern_score)
        
        if score > 0:
            scored_files.append((path, score))
    
    # Sort by score (highest first) and limit
    scored_files.sort(key=lambda x: x[1], reverse=True)
    key_files = [path for path, _ in scored_files[:Config.MAX_FILES_TO_READ]]
    
    logger.info("identified_key_files", count=len(key_files))
    return key_files


async def build_repo_context(github_url: str) -> dict:
    """
    Main function to fetch complete repository context
    
    Args:
        github_url: GitHub repository URL
        
    Returns:
        Dictionary with complete repository context
        
    Raises:
        GitHubParserError: If any step fails
    """
    try:
        logger.info("building_repo_context", url=github_url)
        
        # Parse URL
        owner, repo = parse_github_url(github_url)
        
        # Fetch metadata
        metadata = await fetch_repo_metadata(owner, repo)
        branch = metadata["default_branch"]
        
        # Fetch file tree
        files = await fetch_file_tree(owner, repo, branch)
        
        # Identify key files
        key_file_paths = identify_key_files(files)
        
        # Fetch content of key files
        key_files_content = {}
        for path in key_file_paths:
            content = await fetch_file_content(owner, repo, path, branch)
            if content:
                key_files_content[path] = content
        
        # Build directory structure summary
        directories = set()
        for file in files:
            parts = file["path"].split("/")
            for i in range(1, len(parts)):
                directories.add("/".join(parts[:i]))
        
        context = {
            "url": github_url,
            "owner": owner,
            "repo": repo,
            "metadata": metadata,
            "file_count": len(files),
            "directory_structure": sorted(list(directories))[:50],  # Limit for context
            "all_files": [f["path"] for f in files][:200],  # Limit for context
            "key_files": key_files_content,
            "file_tree": files[:100]  # Limit for context
        }
        
        logger.info("repo_context_built", 
                   files=len(files), 
                   key_files=len(key_files_content),
                   directories=len(directories))
        
        return context
        
    except GitHubParserError:
        raise
    except Exception as e:
        logger.error("unexpected_error", error=str(e))
        raise GitHubParserError(f"Unexpected error: {str(e)}")

# Made with Bob
