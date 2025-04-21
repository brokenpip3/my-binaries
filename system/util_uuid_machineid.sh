##!/usr/bin/env bash

MACHINE_ID=$(cat /etc/machine-id)
UUID=$(echo -n "$MACHINE_ID" | sha1sum | awk '{print $1}' | head -c 32 \
    | sed 's/\(.\{8\}\)\(.\{4\}\)\(.\{4\}\)\(.\{4\}\)\(.\{12\}\)/\1-\2-\3-\4-\5/')
    # Thanks openai for the sed command
echo "$UUID"
