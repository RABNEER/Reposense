import asyncio
import httpx
import time
import logging
from typing import Optional, Dict, List
from datetime import datetime

logger = logging.getLogger(__name__)

class GitHubParserError(Exception):
    """Custom exception for GitHub parsing errors"""
    pass

def parse_github_url(url: str) -> tuple[str, str]:
    if not url:
        raise ValueError("URL cannot be empty")

    cleaned = url.strip()

    # Add https if missing
    if not cleaned.startswith('http'):
        cleaned = 'https://' + cleaned

    # Remove .git suffix
    cleaned = cleaned.rstrip('/')
    if cleaned.endswith('.git'):
        cleaned = cleaned[:-4]

    # Strip tree/blob paths
    for pattern in ['/tree/', '/blob/', '/commit/', '/releases/']:
        if pattern in cleaned:
            cleaned = cleaned.split(pattern)[0]

    # Extract github.com part
    if 'github.com' not in cleaned:
        raise ValueError("Not a GitHub URL")

    parts = cleaned.split('github.com/')
    if len(parts) < 2:
        raise ValueError("Invalid GitHub URL format")

    path = parts[1].strip('/')
    segments = path.split('/')

    if len(segments) < 2:
        raise ValueError(
            "URL must include owner and repo: "
            "github.com/owner/repo"
        )

    owner = segments[0]
    repo = segments[1]

    if not owner or not repo:
        raise ValueError("Owner and repo name cannot be empty")

    return owner, repo

def fetch_repo_metadata(owner: str, repo: str, token: Optional[str] = None) -> Dict:
    """
    Fetch repository metadata from GitHub API.
    
    Returns: dict with repo metadata
    Raises: GitHubParserError on failure
    """
    url = f"https://api.github.com/repos/{owner}/{repo}"
    headers = {"Accept": "application/vnd.github.v3+json"}
    
    if token:
        headers["Authorization"] = f"token {token}"
    
    try:
        response = httpx.get(url, headers=headers, timeout=10.0, follow_redirects=True)
        
        if response.status_code == 404:
            raise GitHubParserError(f"Repository {owner}/{repo} not found")
        elif response.status_code == 403:
            if 'rate limit' in response.text.lower():
                raise GitHubParserError("GitHub API rate limit exceeded. Please add a GITHUB_TOKEN.")
            raise GitHubParserError(f"Repository {owner}/{repo} is private or access denied")
        elif response.status_code == 401:
            raise GitHubParserError("Invalid GitHub token")
        elif response.status_code != 200:
            raise GitHubParserError(f"GitHub API error: {response.status_code}")
        
        data = response.json()
        
        return {
            "name": data.get("name", ""),
            "full_name": data.get("full_name", ""),
            "description": data.get("description", ""),
            "language": data.get("language", "Unknown"),
            "stars": data.get("stargazers_count", 0),
            "forks": data.get("forks_count", 0),
            "license": data.get("license", {}).get("name", "None") if data.get("license") else "None",
            "topics": data.get("topics", []),
            "default_branch": data.get("default_branch", "main"),
            "size": data.get("size", 0),
            "created_at": data.get("created_at", ""),
            "updated_at": data.get("updated_at", ""),
            "open_issues": data.get("open_issues_count", 0),
            "watchers": data.get("watchers_count", 0)
        }
        
    except httpx.TimeoutException:
        raise GitHubParserError("GitHub API request timed out")
    except httpx.RequestError as e:
        raise GitHubParserError(f"Network error connecting to GitHub: {str(e)}")
    except Exception as e:
        if isinstance(e, GitHubParserError):
            raise
        raise GitHubParserError(f"Error fetching repository metadata: {str(e)}")

def fetch_file_tree(owner: str, repo: str, branch: str, token: Optional[str] = None) -> List[Dict]:
    """
    Fetch repository file tree from GitHub API.
    
    Returns: list of file objects with path, size, type
    Raises: GitHubParserError on failure
    """
    url = f"https://api.github.com/repos/{owner}/{repo}/git/trees/{branch}?recursive=1"
    headers = {"Accept": "application/vnd.github.v3+json"}
    
    if token:
        headers["Authorization"] = f"token {token}"
    
    exclude_patterns = [
        'node_modules', '.git', 'dist', 'build', '__pycache__',
        '.next', '.cache', 'coverage', '.nyc_output', 'vendor',
        'target', 'out', '.gradle', '.idea', '.vscode',
        'venv', 'env', '.env', '.pytest_cache'
    ]
    
    exclude_extensions = ['.min.js', '.min.css', '.lock', '.sum', '.log']
    
    include_extensions = [
        '.js', '.ts', '.jsx', '.tsx', '.py', '.go', '.rs', '.java', '.rb', '.php',
        '.c', '.cpp', '.h', '.hpp', '.cs', '.swift', '.kt', '.scala',
        '.md', '.json', '.yaml', '.yml', '.toml', '.xml',
        '.sh', '.bash', '.sql', '.graphql'
    ]
    
    include_files = [
        'Dockerfile', 'docker-compose.yml', '.gitignore', '.dockerignore',
        'Makefile', 'CMakeLists.txt', '.env.example', '.env.sample'
    ]
    
    try:
        response = httpx.get(url, headers=headers, timeout=10.0, follow_redirects=True)
        
        if response.status_code == 404:
            raise GitHubParserError(f"Branch '{branch}' not found in repository")
        elif response.status_code != 200:
            raise GitHubParserError(f"GitHub API error fetching file tree: {response.status_code}")
        
        data = response.json()
        tree = data.get("tree", [])
        
        filtered_files = []
        for item in tree:
            if item.get("type") != "blob":
                continue
            
            path = item.get("path", "")
            
            if any(pattern in path for pattern in exclude_patterns):
                continue
            
            if any(path.endswith(ext) for ext in exclude_extensions):
                continue
            
            filename = path.split('/')[-1]
            if filename in include_files:
                filtered_files.append({
                    "path": path,
                    "size": item.get("size", 0),
                    "type": "blob"
                })
                continue
            
            if any(path.endswith(ext) for ext in include_extensions):
                filtered_files.append({
                    "path": path,
                    "size": item.get("size", 0),
                    "type": "blob"
                })
        
        filtered_files = filtered_files[:500]
        
        logger.info(f"Filtered {len(filtered_files)} files from {len(tree)} total")
        return filtered_files
        
    except httpx.TimeoutException:
        raise GitHubParserError("GitHub API request timed out")
    except httpx.RequestError as e:
        raise GitHubParserError(f"Network error: {str(e)}")
    except Exception as e:
        if isinstance(e, GitHubParserError):
            raise
        raise GitHubParserError(f"Error fetching file tree: {str(e)}")

def select_priority_files(file_tree: list) -> list:
    """Select up to 40 high-priority files to fetch from the repository."""
    priority_1 = [
        'README.md', 'README.rst', 'README', 'README.txt',
        'package.json', 'package-lock.json',
        'requirements.txt', 'pyproject.toml', 'setup.py', 'Pipfile',
        'go.mod', 'go.sum',
        'Cargo.toml', 'Cargo.lock',
        'pom.xml', 'build.gradle', 'build.gradle.kts',
        '.env.example', '.env.sample',
        'Dockerfile', 'docker-compose.yml'
    ]
    
    priority_2 = [
        'index.js', 'index.ts', 'main.js', 'main.ts', 'app.js', 'app.ts',
        'server.js', 'server.ts', 'api.js', 'api.ts',
        'main.py', 'app.py', 'server.py', 'api.py', '__init__.py',
        'main.go', 'cmd/main.go',
        'main.rs', 'src/main.rs', 'lib.rs', 'src/lib.rs',
        'Main.java', 'Application.java'
    ]
    
    priority_3 = [
        'vite.config.js', 'vite.config.ts',
        'webpack.config.js', 'rollup.config.js',
        'tsconfig.json', 'jsconfig.json',
        '.eslintrc', '.eslintrc.js', '.eslintrc.json',
        'tailwind.config.js', 'postcss.config.js',
        'jest.config.js', 'vitest.config.js'
    ]
    
    priority_4 = [
        'models.py', 'schemas.py', 'types.ts', 'interfaces.ts',
        'schema.graphql', 'schema.sql'
    ]
    
    files_to_fetch = []
    file_paths = {f["path"] for f in file_tree}
    
    for filename in priority_1:
        if filename in file_paths:
            files_to_fetch.append(filename)
        for path in file_paths:
            if path.endswith('/' + filename):
                files_to_fetch.append(path)
                break
    
    entry_found = False
    for filename in priority_2:
        if entry_found:
            break
        if filename in file_paths:
            files_to_fetch.append(filename)
            entry_found = True
        for path in file_paths:
            if path.endswith('/' + filename):
                files_to_fetch.append(path)
                entry_found = True
                break
    
    for filename in priority_3:
        if filename in file_paths:
            files_to_fetch.append(filename)
        for path in file_paths:
            if path.endswith('/' + filename):
                files_to_fetch.append(path)
                break
    
    for filename in priority_4:
        if filename in file_paths:
            files_to_fetch.append(filename)
        for path in file_paths:
            if path.endswith('/' + filename):
                files_to_fetch.append(path)
                break
    
    files_to_fetch = list(dict.fromkeys(files_to_fetch))[:40]
    return files_to_fetch


def detect_languages(metadata: dict, file_tree: list) -> set:
    """Detect languages from repository metadata and file extensions."""
    languages_detected = set()
    if metadata["language"]:
        languages_detected.add(metadata["language"])

    for filepath in file_tree:
        path = filepath["path"]
        if path.endswith('.py'):
            languages_detected.add('Python')
        elif path.endswith(('.js', '.jsx')):
            languages_detected.add('JavaScript')
        elif path.endswith(('.ts', '.tsx')):
            languages_detected.add('TypeScript')
        elif path.endswith('.go'):
            languages_detected.add('Go')
        elif path.endswith('.rs'):
            languages_detected.add('Rust')
        elif path.endswith('.java'):
            languages_detected.add('Java')
        elif path.endswith('.rb'):
            languages_detected.add('Ruby')
        elif path.endswith('.php'):
            languages_detected.add('PHP')

    return languages_detected


async def fetch_key_files_async(
    owner: str,
    repo: str,
    file_tree: list,
    token: Optional[str] = None
) -> dict:
    """
    Fetch content of key files from repository concurrently.

    Returns: dict mapping filepath to content
    """
    priority_files = select_priority_files(file_tree)
    
    headers = {"Accept": "application/vnd.github.v3.raw"}
    if token:
        headers["Authorization"] = f"token {token}"

    async def fetch_single(client, filepath, file_info):
        try:
            if file_info and file_info.get("size", 0) > 150 * 1024:
                return filepath, f"[File too large: {file_info['size']} bytes]"

            url = f"https://api.github.com/repos/{owner}/{repo}/contents/{filepath}"
            response = await client.get(url, headers=headers, timeout=5.0)

            if response.status_code == 200:
                content = response.text
                logger.info(f"Fetched: {filepath} ({len(content)} chars)")
                return filepath, content
            else:
                return filepath, None

        except Exception as e:
            logger.warning(f"Error fetching {filepath}: {str(e)}")
            return filepath, None

    file_path_map = {f["path"]: f for f in file_tree}

    async with httpx.AsyncClient(timeout=10.0, follow_redirects=True) as client:
        tasks = [
            fetch_single(
                client,
                filepath,
                file_path_map.get(filepath)
            )
            for filepath in priority_files
        ]

        results = await asyncio.gather(*tasks, return_exceptions=True)

    key_files = {}
    for result in results:
        if isinstance(result, tuple):
            filepath, content = result
            if content:
                key_files[filepath] = content

    logger.info(f"Successfully fetched {len(key_files)} key files concurrently")
    return key_files


async def build_repo_context(github_url: str, token: Optional[str] = None) -> Dict:
    """
    Build complete repository context by fetching all necessary data.
    
    Returns: complete context dict
    Raises: GitHubParserError on any failure
    """
    start_time = time.time()
    
    try:
        owner, repo_name = parse_github_url(github_url)
        logger.info(f"Parsing repository: {owner}/{repo_name}")
        
        metadata = fetch_repo_metadata(owner, repo_name, token)
        logger.info(f"Fetched metadata for {metadata['full_name']}")
        
        branch = metadata["default_branch"]
        file_tree = fetch_file_tree(owner, repo_name, branch, token)
        logger.info(f"Fetched file tree: {len(file_tree)} files")
        
        key_files = await fetch_key_files_async(owner, repo_name, file_tree, token)
        logger.info(f"Fetched {len(key_files)} key files")
        
        languages_detected = detect_languages(metadata, file_tree)
        
        has_tests = any('test' in f["path"].lower() or 'spec' in f["path"].lower() for f in file_tree)
        has_docker = any('dockerfile' in f["path"].lower() or 'docker-compose' in f["path"].lower() for f in file_tree)
        has_ci = any('.github/workflows' in f["path"].lower() or '.gitlab-ci' in f["path"].lower() or 'jenkinsfile' in f["path"].lower() for f in file_tree)
        
        elapsed = time.time() - start_time
        logger.info(f"Repository context built in {elapsed:.2f}s")
        
        return {
            "url": github_url,
            "owner": owner,
            "repo_name": repo_name,
            "metadata": metadata,
            "file_tree": file_tree,
            "key_files": key_files,
            "total_files": len(file_tree),
            "languages_detected": sorted(list(languages_detected)),
            "has_tests": has_tests,
            "has_docker": has_docker,
            "has_ci": has_ci,
            "fetched_at": datetime.utcnow().isoformat() + "Z"
        }
        
    except ValueError as e:
        raise GitHubParserError(str(e))
    except Exception as e:
        if isinstance(e, GitHubParserError):
            raise
        raise GitHubParserError(f"Failed to build repository context: {str(e)}")

# Made with Bob
