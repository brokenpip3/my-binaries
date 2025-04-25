setup() {
    bats_load_library bats-support
    bats_load_library bats-assert
    SCRIPT_PATH="./util_uuid_machineid.sh"
    MOCK_MACHINE_ID="15d33826d9860558565d4d4a9b7dd2d3"
    MOCK_UUID="c1696bd5-ded2-874b-697a-d128a3d0bebd"
    function cat() {
        if [[ "$1" == "/etc/machine-id" ]]; then
            cat "${BATS_TEST_TMPDIR}/machine-id"
        else
            command cat "$@"
        fi
    }
}

@test "01 - generates valid UUID format from machine-id" {
    echo "$MOCK_MACHINE_ID" > "${BATS_TEST_TMPDIR}/machine-id"
    export -f cat

    run "$SCRIPT_PATH"
    assert_success
    assert_output --regexp '^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$'
    assert_output "$MOCK_UUID"
}

@test "02 - fails when /etc/machine-id is missing" {
    export -f cat

    run "$SCRIPT_PATH"
    assert_output --partial "No such file or directory"
}

@test "03 - generates always same UUID for same machine-id" {
    echo "$MOCK_MACHINE_ID" > "${BATS_TEST_TMPDIR}/machine-id"
    export -f cat

    run "$SCRIPT_PATH"
    first_run=$output
    run "$SCRIPT_PATH"
    second_run=$output
    run "$SCRIPT_PATH"
    assert_success
    assert_equal "$output" "$first_run"
    assert_equal "$first_run" "$second_run"
}

@test "04 - generates different UUIDs for different machine-ids" {
    echo "$MOCK_MACHINE_ID" > "${BATS_TEST_TMPDIR}/machine-id"
    export -f cat

    run "$SCRIPT_PATH"
    first_run=$output

    echo "219d4732c142d09dd98647749d64f3c3" > "${BATS_TEST_TMPDIR}/machine-id"
    run "$SCRIPT_PATH"

    [ "$output" != "$first_run" ]
    assert_success
}
