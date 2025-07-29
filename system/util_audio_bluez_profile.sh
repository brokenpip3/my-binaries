#!/usr/bin/env bash

set +u

blueid=$(pw-dump | jq -r '.[] | select(.type=="PipeWire:Interface:Device" and .info.props["device.api"]=="bluez5") | .id')

[ -z "$blueid" ] && { echo "no bluetooth device found"; exit 1; }

set_profile() {
    local profile_index="$1"
    local profile_name="$2"
    pw-cli s "$blueid" Profile "{ index: $profile_index, save: false }" &>/dev/null
    notify-send "Bluetooth headset switched to profile $profile_name"
}

if [[ "$1" == "music" ]]; then
    target="a2dp-sink-sbc_xq"
    profile_index=$(pw-dump | jq -r --arg target "$target" '
        .[] | select(.id == '"$blueid"') | .info.params.EnumProfile[]? |
        select(.name == $target) | .index')

    set_profile "$profile_index" "$target"
    exit 0
elif [[ "$1" == "call" ]]; then
    target="headset-head-unit"
    profile_index=$(pw-dump | jq -r --arg target "$target" '
        .[] | select(.id == '"$blueid"') | .info.params.EnumProfile[]? |
        select(.name == $target) | .index')

    set_profile "$profile_index" "$target"
    exit 0
fi

profiles=$(pw-dump | jq -c --argjson card "$blueid" '
    .[] | select(.id == $card) | .info.params.EnumProfile[]? | select(.available == "yes")')
selected_profile=$(echo "$profiles" | jq -r '.name' | fzf --height=10 --border --prompt="select audio profile: ")
[ -z "$selected_profile" ] && { echo "no profile selected"; exit 1; }
profile_index=$(echo "$profiles" | jq -r --arg name "$selected_profile" 'select(.name == $name) | .index')

set_profile "$profile_index" "$selected_profile"
