#!/usr/bin/env bash
#
# Home manager remote
#
# https://www.brokenpip3.com/posts/2024-27-06-nix-tiny-tools/#home-manager-remote
#
# shellcheck disable=SC2181,SC2029,SC1087

set +u

log() {
    local user host
    IFS='@' read -r user host <<< "$1"

    if [ -z "$NO_COLOR" ]; then
        echo -e "\033[36m[$(date '+%Y-%m-%d %H:%M:%S')]\033[0m \033[35m$host[$user]\033[0m: $2"
    else
        echo "[$(date '+%Y-%m-%d %H:%M:%S')] $user at $host: $2"
    fi
}

_create_temp() {
    local target="$1"
    local temp_dir_name
    temp_dir_name=$(head /dev/urandom | tr -dc A-Za-z0-9 | head -c 8)
    ssh "$target" "mkdir -p /tmp/$temp_dir_name"
    [ $? -ne 0 ] && { log "$target" "Failed to create temporary directory."; exit 1; }
    echo "$temp_dir_name"
}

_sshexec() {
    local target="$1"
    local command="$2"
    ssh "$target" "$command"
    [ $? -ne 0 ] && { log "$target" "Failed to execute command $command."; exit 1; }
}

copy_git_to_target() {
    local target="$1"
    local temp_dir="$2"
    log "$target" "Copying git repository..."
    git archive --format=tar HEAD | ssh "$target" "tar -xC /tmp/$temp_dir"
    [ $? -ne 0 ] && { log "$target" "Failed to copy git repository. Aborting."; exit 1; }
}

local_build_and_copy() {
    local target="$1"
    local temp_dir="$2"
    local flake_path="$3"
    local local_build_output
    log "$target" "Building locally..."
    local_build_output=$(nix build "$flake_path#homeConfigurations.$(_sshexec "$target" 'whoami')@$(_sshexec "$target" "echo \$HOSTNAME").activationPackage" --json | jq -r '.[].outputs.out')
    [ $? -ne 0 ] && { log "$target" "Local build failed. Aborting."; exit 1; }

    log "$target" "Copying the closure..."
    nix copy --verbose --to "ssh://$target" "$local_build_output"
    [ $? -ne 0 ] && { log "$target" "Failed to copy closure. Aborting."; exit 1; }
}

help() {
    echo "Usage: $0 <flake_path> [target] [--build-on-target]"
    exit 1
}

main() {
    [ "$#" -lt 1 ] && help

    local flake_path="$1"
    local target="$2"
    local build_on_target=false
    local temp_dir

    [[ "$3" = "--build-on-target" ]] && build_on_target=true
    [[ -z "$target" ]] && read -rp "Enter the target host: " target
    ssh -q "$target" true || { log "$target" "Unable to connect to the target."; exit 1; }

    temp_dir=$(_create_temp "$target")
    log "$target" "Temporary directory '/tmp/$temp_dir' created."

    copy_git_to_target "$target" "$temp_dir"

    if [ "$build_on_target" = true ]; then
        log "$target" "Building on target..."
        _sshexec "$target" "cd /tmp/$temp_dir && sh -c '\$HOME/.nix-profile/bin/home-manager build --flake .#\$(whoami)@\$(hostname || echo \$HOSTNAME)'"
    else
        local_build_and_copy "$target" "$temp_dir" "$flake_path"
    fi

    log "$target" "Switching to the new configuration..."
    _sshexec "$target" "cd /tmp/$temp_dir && sh -c '\$HOME/.nix-profile/bin/home-manager switch --flake .#\$(whoami)@\$(hostname || echo \$HOSTNAME)'"

    log "$target" "Cleaning up temporary files..."
    _sshexec "$target" "rm -rf /tmp/$temp_dir"

    log "$target" "Running home-manager expire-generations..."
    _sshexec "$target" "\$HOME/.nix-profile/bin/home-manager expire-generations 7d"

    log "$target" "Home-manager remote completed."
}

if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    main "$@"
fi
