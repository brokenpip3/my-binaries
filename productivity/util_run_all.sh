#!/usr/bin/env bash

get_util_stuff() {
    compgen -c | grep "^util_"
    [[ -f ~/.bashrc ]] && grep "^alias util_" ~/.bashrc | sed 's/^alias \([^=]*\)=.*/\1/'
}

selected=$(get_util_stuff | sort -u | fzf --height=40% --reverse --prompt="util> ")
[[ -z "$selected" ]] && exit

read -r -e -p "> " args
bash -i -c "$selected $args"
