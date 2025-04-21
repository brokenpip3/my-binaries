command -v gpg &> /dev/null || { echo "gpg is not installed"; exit 1; }

[ $# -ne 1 ] && { echo "usage: $0 <file_to_encrypt>"; exit 1; }

file_to_encrypt="$1"

[ ! -f "$file_to_encrypt" ] && { echo "file not found: $file_to_encrypt"; exit 1; }

display_keys() {
    local key_type=$1
    local -n key_array=$2
    local counter=1

    while IFS= read -r line; do
        key_id=$(echo "$line" | cut -d' ' -f1)
        email=$(echo "$line" | cut -d' ' -f2)
        echo "$counter) $key_id $email"
        key_array[$counter]=$key_id
        ((counter++))
    done < <(gpg --list-"$key_type" --keyid-format LONG | awk '
    /^(pub|sec)/ {
        key_id = $2;
        sub(".*/", "", key_id);
    }
    /^uid/ {
        if (match($0, /<[^>]+>/)) {
            email = substr($0, RSTART+1, RLENGTH-2);
            print key_id, email;
        }
    }')
}

get_selection() {
    local prompt=$1
    local -n options=$2
    local selection

    while true; do
        read -p "$prompt" selection
        if [[ "$selection" =~ ^[0-9]+$ ]] && [ "$selection" -ge 1 ] && [ "$selection" -le ${#options[@]} ]; then
            echo "${options[$selection]}"
            break
        else
            echo "mmm are you sure? enter a valid number between 1 and ${#options[@]}."
        fi
    done
}

echo "available secret keys for encryption:"
declare -A secret_keys
display_keys "secret-keys" secret_keys

secret_key=$(get_selection "enter the number of the secret key for encryption: " secret_keys)

echo "available public keys for recipients:"
declare -A public_keys
display_keys "keys" public_keys

recipient_key=$(get_selection "enter the number of the recipients key: " public_keys)

gpg --output "${file_to_encrypt}.gpg" --encrypt --recipient "$recipient_key" --trust-model always --default-key "$secret_key" "$file_to_encrypt" && \
echo "file encrypted successfully: ${file_to_encrypt}.gpg" || \
echo "failed to encrypt the file."
