"""Shell completion scripts for ds."""

from __future__ import annotations

__all__ = ["get_completion_script"]

BASH_COMPLETION = r"""
_ds_completions() {
    local cur prev opts tasks
    COMPREPLY=()
    cur="${COMP_WORDS[COMP_CWORD]}"
    prev="${COMP_WORDS[COMP_CWORD-1]}"

    # Options that take arguments
    case "${prev}" in
        --cwd|--file|-f|--env-file)
            COMPREPLY=($(compgen -f -- "${cur}"))
            return 0
            ;;
        --env|-e)
            return 0
            ;;
        --workspace|-w)
            return 0
            ;;
        --output-format)
            COMPREPLY=($(compgen -W "text json" -- "${cur}"))
            return 0
            ;;
        --completion)
            COMPREPLY=($(compgen -W "bash zsh fish" -- "${cur}"))
            return 0
            ;;
    esac

    # Options
    if [[ "${cur}" == -* ]]; then
        opts="--help --version --debug --dry-run --self-update --no-config --no-project --list --tree --cwd --file --env-file --env --workspace --pre --post --parallel --output-format --completion"
        COMPREPLY=($(compgen -W "${opts}" -- "${cur}"))
        return 0
    fi

    # Task names (dynamically from config)
    tasks=$(ds --list --output-format json 2>/dev/null | grep -o '"[^"]*":' | tr -d '":' | grep -v '^path$\|^tasks$' | head -100)
    if [[ -n "${tasks}" ]]; then
        COMPREPLY=($(compgen -W "${tasks}" -- "${cur}"))
    fi
}

complete -F _ds_completions ds
"""

ZSH_COMPLETION = r"""
#compdef ds

_ds() {
    local -a opts tasks

    opts=(
        '--help[Show help message and exit]'
        '--version[Show program version and exit]'
        '--debug[Show debug messages]'
        '--dry-run[Show which tasks would be run]'
        '--self-update[Update ds (Cosmopolitan build only)]'
        '--no-config[Do not load configuration file]'
        '--no-project[Do not search for project dependencies]'
        '-l[List available tasks]'
        '--list[List available tasks]'
        '-t[Show task dependency tree]'
        '--tree[Show task dependency tree]'
        '--cwd[Set working directory]:directory:_files -/'
        '-f[File with task definitions]:file:_files'
        '--file[File with task definitions]:file:_files'
        '--env-file[File with environment variables]:file:_files'
        '-e[Set environment variable]:var:'
        '--env[Set environment variable]:var:'
        '-w[Workspace pattern]:pattern:'
        '--workspace[Workspace pattern]:pattern:'
        '--pre[Run pre- tasks]'
        '--post[Run post- tasks]'
        '--parallel[Run top-level tasks in parallel]'
        '--output-format[Output format]:format:(text json)'
        '--completion[Output completion script]:shell:(bash zsh fish)'
    )

    _arguments -s $opts

    # Get task names dynamically
    local -a task_list
    task_list=(${(f)"$(ds --list --output-format json 2>/dev/null | grep -o '"[^"]*":' | tr -d '":' | grep -v '^path$\|^tasks$' | head -100)"})
    if [[ -n "${task_list}" ]]; then
        _describe 'task' task_list
    fi
}

_ds "$@"
"""

FISH_COMPLETION = r"""
# Disable file completion by default
complete -c ds -f

# Options
complete -c ds -s h -l help -d 'Show help message and exit'
complete -c ds -l version -d 'Show program version and exit'
complete -c ds -l debug -d 'Show debug messages'
complete -c ds -l dry-run -d 'Show which tasks would be run'
complete -c ds -l self-update -d 'Update ds (Cosmopolitan build only)'
complete -c ds -l no-config -d 'Do not load configuration file'
complete -c ds -l no-project -d 'Do not search for project dependencies'
complete -c ds -s l -l list -d 'List available tasks'
complete -c ds -s t -l tree -d 'Show task dependency tree'
complete -c ds -l cwd -d 'Set working directory' -r -a '(__fish_complete_directories)'
complete -c ds -s f -l file -d 'File with task definitions' -r -F
complete -c ds -l env-file -d 'File with environment variables' -r -F
complete -c ds -s e -l env -d 'Set environment variable' -r
complete -c ds -s w -l workspace -d 'Workspace pattern' -r
complete -c ds -l pre -d 'Run pre- tasks'
complete -c ds -l post -d 'Run post- tasks'
complete -c ds -l parallel -d 'Run top-level tasks in parallel'
complete -c ds -l output-format -d 'Output format' -r -a 'text json'
complete -c ds -l completion -d 'Output completion script' -r -a 'bash zsh fish'

# Task names (dynamically from config)
complete -c ds -a '(ds --list --output-format json 2>/dev/null | string match -r \'"[^"]*":\' | string replace -a \'"\' \'\' | string replace \':\' \'\' | string match -v path | string match -v tasks | head -100)'
"""


def get_completion_script(shell: str) -> str:
    """Return the completion script for the given shell."""
    scripts = {
        "bash": BASH_COMPLETION.strip(),
        "zsh": ZSH_COMPLETION.strip(),
        "fish": FISH_COMPLETION.strip(),
    }
    return scripts.get(shell, "")
