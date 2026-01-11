#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.12"
# dependencies = [
#     "requests>=2.32.5",
# ]
# ///
"""Task Runner Census - Analyze task runner usage in popular GitHub repos.

This script uses the GitHub API to:
1. Find top repos by stars for each language
2. Detect which task runner config files they use
3. Analyze features used in those configs
4. Generate reports on findings

Usage:
    ./census.py [--resume] [--limit N]

Requires:
    - GITHUB_TOKEN environment variable (for API access)
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path
from typing import Any

import requests

# === Configuration ===

LANGUAGES = [
    "Python",
    "JavaScript",
    "TypeScript",
    "Rust",
    "PHP",
    "Go",
    "Ruby",
    "Java",
    "C",
    "C++",
    "C#",
    "Swift",
]

# Task runner config files to detect
RUNNER_FILES: dict[str, list[str]] = {
    "make": ["Makefile", "GNUmakefile", "makefile"],
    "npm": ["package.json"],
    "pyproject": ["pyproject.toml"],
    "cargo": ["Cargo.toml"],
    "composer": ["composer.json"],
    "ds": ["ds.toml"],
    "uv": ["uv.toml"],
    "just": ["Justfile", "justfile", ".justfile"],
    "task": ["Taskfile.yml", "Taskfile.yaml"],
    "deno": ["deno.json", "deno.jsonc"],
    "rake": ["Rakefile"],
    "gradle": ["build.gradle", "build.gradle.kts"],
    "maven": ["pom.xml"],
}

# Features to detect (with regex patterns per runner type)
FEATURES: dict[str, dict[str, Any]] = {
    "composite": {
        "description": "Tasks that call other tasks",
        "patterns": {
            "make": r"^\w+:.*\$\(MAKE\)|^\w+:\s+\w+",  # target: dep or $(MAKE)
            "npm": r'"(pre|post)\w+":|"run\s+\w+"|npm\s+run|yarn\s+run',
            "pyproject": r'"\w+".*,|chain\s*=|depends\s*=|composite\s*=',
            "just": r"^\w+:.*\n\s+just\s+\w+|^@?\w+\s+\w+:",  # just calls or deps
        },
    },
    "env_vars": {
        "description": "Tasks that set environment variables",
        "patterns": {
            "make": r"^\s*export\s+\w+=|^\w+\s*[:?]?=",
            "npm": r'"env":\s*\{|cross-env\s+\w+=|env\s+\w+=',
            "pyproject": r"\[.*env\]|env\s*=\s*\{",
            "just": r"^export\s+\w+|^\s*\w+\s*:=",
        },
    },
    "cwd": {
        "description": "Tasks that change working directory",
        "patterns": {
            "make": r"\bcd\s+\S+\s*[;&]|--directory|-C\s+\S+",
            "npm": r'"cwd":|--prefix\s+\S+',
            "pyproject": r"cwd\s*=|working_dir\s*=",
            "just": r"cd\s+\S+\s*[;&]",
        },
    },
    "parallel": {
        "description": "Tasks that run concurrently",
        "patterns": {
            "make": r"-j\s*\d*|--jobs|\.PARALLEL",
            "npm": r"concurrently|npm-run-all|run-p\s|parallel\s",
            "pyproject": r"parallel\s*=\s*true",
            "just": r"&$|parallel",
        },
    },
    "keep_going": {
        "description": "Error suppression / continue on failure",
        "patterns": {
            "make": r"^-\w+:|--keep-going|-k\b|\.IGNORE",
            "npm": r'"\|\|?\s*true"|; true|--ignore-scripts',
            "pyproject": r'keep_going\s*=\s*true|"\+\w+"',
            "just": r"^\s*-\w+:|--keep-going",
        },
    },
    "help": {
        "description": "Task descriptions/documentation",
        "patterns": {
            "make": r"^##\s*\w+|\.PHONY.*help|@echo.*help",
            "npm": r'"description":',
            "pyproject": r'help\s*=\s*"',
            "just": r"^#\s*\w+.*:|@echo|# help",
        },
    },
    "args": {
        "description": "Argument interpolation",
        "patterns": {
            "make": r"\$[@<^?*]|\$\(\d+\)",
            "npm": r'"\$\w+"|"\$@"|--\s*\$|"\{\d+\}"',
            "pyproject": r"\$\d+|\$@|\{0\}|\{args\}",
            "just": r"\$\d+|\$@|\{\{",
        },
    },
    "env_file": {
        "description": "Environment file loading",
        "patterns": {
            "make": r"include\s+.*\.env|-include\s+.*\.env",
            "npm": r"dotenv|env-cmd|\.env",
            "pyproject": r"env_file\s*=|env-file\s*=|dotenv",
            "just": r"set dotenv|dotenv-load",
        },
    },
    "hooks": {
        "description": "Pre/post task hooks",
        "patterns": {
            "make": r"^pre_\w+:|^post_\w+:",
            "npm": r'"pre\w+":|"post\w+":',
            "pyproject": r'"pre_?\w+":|"post_?\w+":',
            "just": r"^pre_\w+:|^post_\w+:",
        },
    },
    "workspaces": {
        "description": "Monorepo/workspace support",
        "patterns": {
            "make": r"--directory|-C\s+packages/",
            "npm": r'"workspaces":|lerna|nx\s|turbo',
            "pyproject": r"workspace\s*=|members\s*=",
            "cargo": r"\[workspace\]",
        },
    },
}

REPOS_PER_LANGUAGE = 200
DATA_DIR = Path(__file__).parent / "data"
STATE_FILE = DATA_DIR / "state.json"


@dataclass
class RepoInfo:
    """Information about a repository."""

    full_name: str
    stars: int
    language: str
    url: str
    runners_detected: list[str] = field(default_factory=list)
    features_detected: dict[str, list[str]] = field(default_factory=dict)
    analyzed: bool = False
    error: str | None = None


@dataclass
class CensusState:
    """Persistent state for resumable execution."""

    started_at: str = ""
    last_updated: str = ""
    repos_fetched: dict[str, list[str]] = field(
        default_factory=dict
    )  # lang -> repo names
    repos_analyzed: list[str] = field(default_factory=list)
    results: dict[str, dict] = field(default_factory=dict)  # repo name -> RepoInfo dict

    def save(self) -> None:
        """Save state to file."""
        self.last_updated = datetime.now().isoformat()
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        STATE_FILE.write_text(json.dumps(asdict(self), indent=2))

    @classmethod
    def load(cls) -> "CensusState":
        """Load state from file or create new."""
        if STATE_FILE.exists():
            data = json.loads(STATE_FILE.read_text())
            return cls(**data)
        state = cls(started_at=datetime.now().isoformat())
        return state


class GitHubAPI:
    """GitHub API client with rate limiting."""

    BASE_URL = "https://api.github.com"

    def __init__(self, token: str | None = None):
        self.token = token or os.environ.get("GITHUB_TOKEN")
        if not self.token:
            print("Warning: No GITHUB_TOKEN set. Rate limits will be very restrictive.")
        self.session = requests.Session()
        if self.token:
            self.session.headers["Authorization"] = f"token {self.token}"
        self.session.headers["Accept"] = "application/vnd.github.v3+json"
        self.rate_limit_remaining = 5000
        self.rate_limit_reset = 0

    def _handle_rate_limit(self, response: requests.Response) -> None:
        """Update rate limit info and wait if needed."""
        self.rate_limit_remaining = int(
            response.headers.get("X-RateLimit-Remaining", 5000)
        )
        self.rate_limit_reset = int(response.headers.get("X-RateLimit-Reset", 0))

        if self.rate_limit_remaining < 10:
            wait_time = max(0, self.rate_limit_reset - time.time()) + 1
            print(
                f"Rate limit low ({self.rate_limit_remaining}), waiting {wait_time:.0f}s..."
            )
            time.sleep(wait_time)

    def get(self, endpoint: str, params: dict | None = None) -> dict | list | None:
        """Make a GET request to the GitHub API."""
        url = f"{self.BASE_URL}/{endpoint.lstrip('/')}"
        try:
            response = self.session.get(url, params=params)
            self._handle_rate_limit(response)

            if response.status_code == 403 and "rate limit" in response.text.lower():
                wait_time = max(0, self.rate_limit_reset - time.time()) + 1
                print(f"Rate limited, waiting {wait_time:.0f}s...")
                time.sleep(wait_time)
                return self.get(endpoint, params)

            if response.status_code == 200:
                return response.json()
            else:
                print(f"API error {response.status_code}: {response.text[:200]}")
                return None
        except requests.RequestException as e:
            print(f"Request error: {e}")
            return None

    def get_file_content(self, repo: str, path: str) -> str | None:
        """Get the content of a file from a repo."""
        result = self.get(f"repos/{repo}/contents/{path}")
        if result and isinstance(result, dict) and "content" in result:
            import base64

            return base64.b64decode(result["content"]).decode("utf-8", errors="replace")
        return None

    def search_repos(
        self, language: str, per_page: int = 100, page: int = 1
    ) -> list[dict]:
        """Search for top repos by language."""
        result = self.get(
            "search/repositories",
            params={
                "q": f"language:{language} stars:>1000",
                "sort": "stars",
                "order": "desc",
                "per_page": per_page,
                "page": page,
            },
        )
        if result and isinstance(result, dict):
            return result.get("items", [])
        return []

    def check_file_exists(self, repo: str, path: str) -> bool:
        """Check if a file exists in a repo (lighter than getting content)."""
        url = f"{self.BASE_URL}/repos/{repo}/contents/{path}"
        try:
            response = self.session.head(url)
            self._handle_rate_limit(response)
            return response.status_code == 200
        except requests.RequestException:
            return False


def fetch_repos(api: GitHubAPI, state: CensusState, limit: int | None = None) -> None:
    """Fetch top repos for each language."""
    for language in LANGUAGES:
        if (
            language in state.repos_fetched
            and len(state.repos_fetched[language]) >= REPOS_PER_LANGUAGE
        ):
            print(
                f"[{language}] Already fetched {len(state.repos_fetched[language])} repos"
            )
            continue

        print(f"[{language}] Fetching top repos...")
        repos = []
        pages_needed = (REPOS_PER_LANGUAGE + 99) // 100

        for page in range(1, pages_needed + 1):
            items = api.search_repos(language, per_page=100, page=page)
            if not items:
                break
            repos.extend(items)
            print(f"  Page {page}: got {len(items)} repos (total: {len(repos)})")
            if len(repos) >= REPOS_PER_LANGUAGE:
                break
            time.sleep(2)  # Be nice to the API

        state.repos_fetched[language] = [
            r["full_name"] for r in repos[:REPOS_PER_LANGUAGE]
        ]

        # Store basic repo info
        for repo in repos[:REPOS_PER_LANGUAGE]:
            if repo["full_name"] not in state.results:
                state.results[repo["full_name"]] = asdict(
                    RepoInfo(
                        full_name=repo["full_name"],
                        stars=repo["stargazers_count"],
                        language=language,
                        url=repo["html_url"],
                    )
                )

        state.save()
        print(f"[{language}] Saved {len(state.repos_fetched[language])} repos")

        if limit and sum(len(v) for v in state.repos_fetched.values()) >= limit:
            print(f"Reached limit of {limit} repos")
            break


def detect_runners(
    api: GitHubAPI, state: CensusState, limit: int | None = None
) -> None:
    """Detect which task runner files exist in each repo."""
    all_repos = [r for repos in state.repos_fetched.values() for r in repos]
    analyzed_count = 0

    for repo_name in all_repos:
        if repo_name in state.repos_analyzed:
            continue

        print(f"[{repo_name}] Detecting runners...")
        repo_info = state.results.get(repo_name, {})
        runners_found = []

        for runner, files in RUNNER_FILES.items():
            for filename in files:
                if api.check_file_exists(repo_name, filename):
                    runners_found.append(runner)
                    print(f"  Found: {filename} ({runner})")
                    break  # Only need to find one file per runner
                time.sleep(0.1)  # Small delay between file checks

        repo_info["runners_detected"] = runners_found
        state.results[repo_name] = repo_info
        state.repos_analyzed.append(repo_name)
        analyzed_count += 1

        if analyzed_count % 10 == 0:
            state.save()
            print(f"  Progress: {analyzed_count} repos analyzed")

        if limit and analyzed_count >= limit:
            break

    state.save()


def analyze_features(
    api: GitHubAPI, state: CensusState, limit: int | None = None
) -> None:
    """Analyze features used in detected task runner files."""
    analyzed_count = 0

    for repo_name, repo_info in state.results.items():
        if repo_info.get("analyzed"):
            continue

        runners = repo_info.get("runners_detected", [])
        if not runners:
            repo_info["analyzed"] = True
            continue

        print(f"[{repo_name}] Analyzing features...")
        features_detected: dict[str, list[str]] = {}

        for runner in runners:
            # Get the actual file content
            files = RUNNER_FILES.get(runner, [])
            content = None
            for filename in files:
                content = api.get_file_content(repo_name, filename)
                if content:
                    break
                time.sleep(0.5)

            if not content:
                continue

            # Check each feature
            for feature_name, feature_info in FEATURES.items():
                patterns = feature_info.get("patterns", {})
                pattern = patterns.get(runner)
                if pattern and re.search(
                    pattern, content, re.MULTILINE | re.IGNORECASE
                ):
                    if feature_name not in features_detected:
                        features_detected[feature_name] = []
                    features_detected[feature_name].append(runner)

        repo_info["features_detected"] = features_detected
        repo_info["analyzed"] = True
        state.results[repo_name] = repo_info
        analyzed_count += 1

        if analyzed_count % 5 == 0:
            state.save()
            print(f"  Progress: {analyzed_count} repos fully analyzed")

        if limit and analyzed_count >= limit:
            break

    state.save()


def generate_report(state: CensusState) -> None:
    """Generate summary report from collected data."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    # Save raw results as JSON
    results_file = DATA_DIR / "results.json"
    results_file.write_text(json.dumps(state.results, indent=2))
    print(f"Saved results to {results_file}")

    # Calculate statistics
    total_repos = len(state.results)
    repos_with_runners = sum(
        1 for r in state.results.values() if r.get("runners_detected")
    )

    runner_counts: dict[str, int] = {}
    feature_counts: dict[str, int] = {}
    runner_feature_counts: dict[str, dict[str, int]] = {}

    for repo_info in state.results.values():
        for runner in repo_info.get("runners_detected", []):
            runner_counts[runner] = runner_counts.get(runner, 0) + 1

        for feature, runners in repo_info.get("features_detected", {}).items():
            feature_counts[feature] = feature_counts.get(feature, 0) + 1
            for runner in runners:
                if runner not in runner_feature_counts:
                    runner_feature_counts[runner] = {}
                runner_feature_counts[runner][feature] = (
                    runner_feature_counts[runner].get(feature, 0) + 1
                )

    # Generate CSV summary
    csv_lines = ["runner,count,percentage"]
    for runner, count in sorted(runner_counts.items(), key=lambda x: -x[1]):
        pct = (count / total_repos * 100) if total_repos else 0
        csv_lines.append(f"{runner},{count},{pct:.1f}")

    csv_file = DATA_DIR / "summary.csv"
    csv_file.write_text("\n".join(csv_lines))
    print(f"Saved summary to {csv_file}")

    # Generate markdown report
    report_lines = [
        "# Task Runner Census Report",
        "",
        f"Generated: {datetime.now().isoformat()}",
        "",
        "## Overview",
        "",
        f"- **Total repos analyzed**: {total_repos}",
        f"- **Repos with task runners**: {repos_with_runners} ({repos_with_runners / total_repos * 100:.1f}%)"
        if total_repos
        else "",
        "",
        "## Task Runner Popularity",
        "",
        "| Runner | Count | % of Repos |",
        "|--------|-------|------------|",
    ]

    for runner, count in sorted(runner_counts.items(), key=lambda x: -x[1]):
        pct = (count / total_repos * 100) if total_repos else 0
        report_lines.append(f"| {runner} | {count} | {pct:.1f}% |")

    report_lines.extend(
        [
            "",
            "## Feature Usage",
            "",
            "| Feature | Count | % of Repos with Runners |",
            "|---------|-------|-------------------------|",
        ]
    )

    for feature, count in sorted(feature_counts.items(), key=lambda x: -x[1]):
        pct = (count / repos_with_runners * 100) if repos_with_runners else 0
        desc = FEATURES.get(feature, {}).get("description", "")
        report_lines.append(f"| {feature} | {count} | {pct:.1f}% |")

    report_lines.extend(
        [
            "",
            "## Features by Runner",
            "",
        ]
    )

    for runner, features in sorted(runner_feature_counts.items()):
        runner_total = runner_counts.get(runner, 1)
        report_lines.append(f"### {runner}")
        report_lines.append("")
        report_lines.append("| Feature | Count | % |")
        report_lines.append("|---------|-------|---|")
        for feature, count in sorted(features.items(), key=lambda x: -x[1]):
            pct = (count / runner_total * 100) if runner_total else 0
            report_lines.append(f"| {feature} | {count} | {pct:.1f}% |")
        report_lines.append("")

    report_file = DATA_DIR / "REPORT.md"
    report_file.write_text("\n".join(report_lines))
    print(f"Saved report to {report_file}")


def main() -> None:
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Task Runner Census")
    parser.add_argument("--resume", action="store_true", help="Resume from saved state")
    parser.add_argument("--limit", type=int, help="Limit number of repos to process")
    parser.add_argument(
        "--phase",
        choices=["fetch", "detect", "analyze", "report", "all"],
        default="all",
        help="Which phase to run",
    )
    args = parser.parse_args()

    # Load or create state
    if args.resume and STATE_FILE.exists():
        print("Resuming from saved state...")
        state = CensusState.load()
        print(f"  Started: {state.started_at}")
        print(f"  Repos fetched: {sum(len(v) for v in state.repos_fetched.values())}")
        print(f"  Repos analyzed: {len(state.repos_analyzed)}")
    else:
        print("Starting fresh...")
        state = CensusState(started_at=datetime.now().isoformat())

    api = GitHubAPI()

    if args.phase in ["fetch", "all"]:
        print("\n=== Phase 1: Fetching repos ===")
        fetch_repos(api, state, args.limit)

    if args.phase in ["detect", "all"]:
        print("\n=== Phase 2: Detecting runners ===")
        detect_runners(api, state, args.limit)

    if args.phase in ["analyze", "all"]:
        print("\n=== Phase 3: Analyzing features ===")
        analyze_features(api, state, args.limit)

    if args.phase in ["report", "all"]:
        print("\n=== Phase 4: Generating report ===")
        generate_report(state)

    print("\nDone!")


if __name__ == "__main__":
    main()
