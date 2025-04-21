[ -z "$1" ] && { echo "$0 command"; exit 1;}
xdotool type "$1" && xdotool key Return
