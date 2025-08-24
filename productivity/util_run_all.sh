#!/usr/bin/env bash

get_util_stuff() {
    compgen -c | grep "^util_"
    if [[ -f ~/.bashrc ]]; then
        grep "^alias util_" ~/.bashrc | sed 's/^alias \([^=]*\)=.*/\1/'
    fi
}

selected=$(get_util_stuff | sort -u | fzf --height=40% --reverse --prompt="util> ")

[[ -n "$selected" ]] && bash -i -c "$selected"
