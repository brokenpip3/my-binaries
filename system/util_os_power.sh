#!/usr/bin/env bash

OPTIONS="exit i3\nsuspend\nreboot\npoweroff"

if [ -t 0 ]; then
    SELECTED=$(echo -e "$OPTIONS" | fzf --prompt="Power options: " --height=~10 --layout=reverse --border)
else
    SELECTED=$(echo -e "$OPTIONS" | rofi -dmenu -p "Power options: ")
fi

case "$SELECTED" in
    "exit i3")
        i3-msg exit
        ;;
    "suspend")
        systemctl suspend
        ;;
    "reboot")
        systemctl reboot
        ;;
    "poweroff")
        systemctl poweroff
        ;;
    *)
        exit 0
        ;;
esac
