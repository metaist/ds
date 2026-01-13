# What 2,400 GitHub Repos Taught Me About Task Runners

*A census of the most popular repositories reveals surprising patterns in how developers automate their workflows.*

## The Question

When building [ds](https://github.com/metaist/ds), a task runner that reads from existing config files, I wanted to know: **what features do developers actually use?** Rather than guessing, I decided to look at real data.

## The Method

I wrote a Python script that:
1. Fetched the top 200 most-starred repos for each of 12 languages (Python, JavaScript, TypeScript, Rust, PHP, Go, Ruby, Java, C, C++, C#, Swift)
2. Detected which task runner config files existed in each repo
3. Analyzed those files for specific features using regex patterns

Total: **2,400 repositories** analyzed.

## Task Runner Popularity

The first surprise: only **64%** of top repos have a recognizable task runner config.

| Runner | Repos | Share |
|--------|-------|-------|
| npm (package.json) | 542 | 22.6% |
| make | 409 | 17.0% |
| cargo | 197 | 8.2% |
| composer | 191 | 8.0% |
| rake | 181 | 7.5% |
| pyproject.toml | 163 | 6.8% |
| maven | 89 | 3.7% |
| gradle | 82 | 3.4% |
| just | 25 | 1.0% |
| task (Taskfile.yml) | 8 | 0.3% |

**npm scripts dominate**, but Make is a strong second - proving the 50-year-old tool isn't going anywhere. The "modern" alternatives like `just` and `task` are still niche, at least among popular open-source projects.

## Feature Usage

Here's what people actually do with their task runners:

| Feature | Usage | What It Means |
|---------|-------|---------------|
| **Composite tasks** | 54.6% | Tasks that call other tasks |
| **Help/descriptions** | 27.3% | Documentation for tasks |
| **Environment variables** | 26.7% | Setting vars for commands |
| **Hooks** | 23.9% | Pre/post task automation |
| **Workspaces** | 19.7% | Monorepo support |
| **Working directory** | 18.0% | Running from different dirs |
| **Parallel execution** | 14.6% | Running tasks concurrently |
| **Argument passing** | 13.5% | Forwarding args to commands |
| **Env files** | 5.3% | Loading .env files |
| **Keep going** | 1.0% | Continue on failure |

### The Takeaways

1. **Composite tasks are table stakes.** Over half of task configs chain tasks together. If your task runner doesn't support this, you're fighting the current.

2. **Hooks are more popular than expected.** Nearly 1 in 4 repos use pre/post hooks. npm's automatic `pretest`/`posttest` pattern has clearly influenced expectations.

3. **Parallel execution is niche.** Only 14.6% of repos use it. Most build tasks are inherently sequential, or projects just haven't bothered optimizing.

4. **Almost nobody uses keep_going.** At 1%, error suppression is rare. Developers want builds to fail fast.

5. **Env files are underused.** Only 5.3% explicitly load `.env` files through their task runner. Most probably rely on shell dotfile loading or IDE integration.

## Deep Dive: Feature Patterns by Runner

### Make is the kitchen sink
Make users use *everything*: 88% composite, 79% env vars, 65% cwd changes, 45% argument passing. It's the most feature-dense runner.

### npm relies on conventions
68% of npm users leverage hooks (`pretest`, `postbuild`, etc.). It's the highest hook usage of any runner. Convention over configuration works.

### Just prioritizes ergonomics
Just users heavily use argument passing (80%) and env vars (48%). It's designed for interactive use, and the data confirms people use it that way.

### pyproject.toml is composition-focused
83% composite tasks, but low usage of other features. Python projects define tasks mainly to chain together commands like `ruff check && pytest`.

## What This Means for ds

The census validated ds's design decisions:
- ✅ **Composite tasks**: Supported
- ✅ **Help text**: Supported
- ✅ **Environment variables**: Supported
- ✅ **Hooks**: Supported via `--pre`/`--post` flags
- ✅ **Workspaces**: Supported
- ✅ **Parallel**: Supported (experimental)
- ✅ **Argument passing**: Supported (`$@`, `$1`, `{args}`, `{args:default}`)
- ✅ **Env files**: Supported via `--env-file`

Future consideration:
- 📋 **Named arguments** (e.g., `ds build --target=release` → `$target`) - would pair well with Justfile format support

## Try It Yourself

The census script is available at [`research/task_runner_census/census.py`](./census.py). It's a self-contained `uv` script - just run:

```bash
export GITHUB_TOKEN=your_token
./census.py --limit 100  # start small
```

The script is resumable (saves state to JSON) and rate-limit aware.

## Conclusion

Task runner usage is surprisingly conservative. Despite dozens of modern alternatives, npm scripts and Make handle nearly 40% of the top repos. Features like composite tasks and hooks are widely used; parallel execution and error suppression are not.

If you're building a task runner (or choosing one), focus on the basics: make it easy to chain tasks, document them, and set environment variables. The fancy stuff can wait.

---

*Data collected January 2026. Full results available in `research/task_runner_census/data/`.*

---

*Written by Claude Opus 4.5 during research with [@metaist](https://github.com/metaist).*
