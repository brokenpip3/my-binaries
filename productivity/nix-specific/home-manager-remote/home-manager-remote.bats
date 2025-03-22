setup() {
    bats_load_library bats-support
    bats_load_library bats-assert
    SCRIPT_PATH="./home-manager-remote.sh"
}

@test "01 - running script without arguments shows help message" {
    run "$SCRIPT_PATH"
    assert_failure
    assert_output "Usage: ./home-manager-remote.sh <flake_path> [target] [--build-on-target]"
}

@test "02 - help function outputs correct usage information" {
    source "$SCRIPT_PATH"
    run help
    assert_failure
    assert_output --partial "<flake_path> [target] [--build-on-target]"
}

@test "03 - log function displays colored output when NO_COLOR is not set" {
    source "$SCRIPT_PATH"
    local old_no_color="$NO_COLOR"
    unset NO_COLOR
    run log "rancore@politicalrap" "message from a rap song"
    export NO_COLOR="$old_no_color"
    assert_output --partial "politicalrap[rancore]"
    assert_output --partial "message from a rap song"
    refute_output --regexp "\\033"
}

@test "04 - log function displays plain output when NO_COLOR is set" {
    source "$SCRIPT_PATH"
    export NO_COLOR=1
    run log "rancore@politicalrap" "Another message from a rap song"
    unset NO_COLOR
    refute_output --regexp "\\033"
    assert_output --partial "rancore at politicalrap"
    assert_output --partial "Another message from a rap song"
}

@test "05 - log function correctly splits user@host input" {
    source "$SCRIPT_PATH"
    export NO_COLOR=1
    run log "root@server" "Root message"
    assert_output --partial "root at server"
    run log "murubutu@192.168.1.1" "IP address host"
    assert_output --partial "murubutu at 192.168.1.1"
}
