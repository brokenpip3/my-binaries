#!/usr/bin/env bats

setup() {
    bats_load_library bats-support
    bats_load_library bats-assert
    SCRIPT_PATH="./util_privacy_gpg_encrypt.sh"
}

@test "01 - fails no arguments" {
    run "$SCRIPT_PATH"

    assert_failure
    assert_output --partial "usage: $SCRIPT_PATH <file_to_encrypt>"
}

@test "02 - fails file does not exist" {
    run "$SCRIPT_PATH" "/no/i/do/no/exist.txt"

    assert_failure
    assert_output --partial "file not found: /no/i/do/no/exist.txt"
}
