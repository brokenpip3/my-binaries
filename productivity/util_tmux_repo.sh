#!/usr/bin/env bash
repo_bases=(~/repo ~/dotfiles ~/var)
fzf_cmd='fzf --tmux --height 100% --prompt=repo: '

repo_list=$(find "${repo_bases[@]}" -mindepth 1 -maxdepth 1 -type d -printf "%P\n" | awk -F/ '{print $NF}' | sort -u | $fzf_cmd)
[ -z "$repo_list" ] && exit 1

full_path=$(find "${repo_bases[@]}" -mindepth 1 -maxdepth 1 -type d | grep "/$repo_list$" | head -n1)
repo_base=$(dirname "$full_path")
session_name=$(basename "$repo_base")

set +u
if [ -n "$TMUX" ]; then
    tmux new-window -c "$full_path" -n "$repo_list"
    tmux select-window -t "$(tmux display-message -p '#S'):$repo_list"
else
    if tmux has-session -t "$session_name" 2>/dev/null; then
        tmux new-window -c "$full_path" -n "$repo_list" -t "$session_name"
        tmux attach-session -t "$session_name"
    else
        tmux new-session -s "$session_name" -c "$full_path" -n "$repo_list"
        tmux attach-session -t "$session_name"
    fi
fi
