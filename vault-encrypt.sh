#!/bin/bash

# Configuration
VAULT_FILES=$(find inventories -name "vault.yml")
ENV_FILE=".env.vault"

# Load ANSIBLE_VAULT_PASSWORD from .env.vault
if [ -f "$ENV_FILE" ]; then
    export $(grep -v '^#' "$ENV_FILE" | grep "ANSIBLE_VAULT_PASSWORD" | xargs)
fi

if [ -z "$ANSIBLE_VAULT_PASSWORD" ]; then
    echo "ERROR: ANSIBLE_VAULT_PASSWORD is not set in $ENV_FILE"
    exit 1
fi

# Create a temporary password file for ansible-vault
PASS_FILE=$(mktemp)
echo "$ANSIBLE_VAULT_PASSWORD" > "$PASS_FILE"

for FILE in $VAULT_FILES; do
    TEMP_FILE="${FILE}.temp"
    
    if [ -f "$TEMP_FILE" ]; then
        # Case 1: .temp exists. Overwrite vault.yml and encrypt.
        echo "Updating $FILE from $TEMP_FILE..."
        cp "$TEMP_FILE" "$FILE"
        ansible-vault encrypt "$FILE" --vault-password-file "$PASS_FILE" > /dev/null
        if [ $? -eq 0 ]; then
            echo "  - Successfully encrypted $FILE"
        else
            echo "  - FAILED to encrypt $FILE"
        fi
    else
        # Case 2: .temp does NOT exist.
        if grep -q "\$ANSIBLE_VAULT" "$FILE"; then
            # If already encrypted, decrypt to .temp
            echo "Extracting $FILE to $TEMP_FILE..."
            ansible-vault decrypt "$FILE" --vault-password-file "$PASS_FILE" --output "$TEMP_FILE" > /dev/null
            if [ $? -eq 0 ]; then
                echo "  - Created $TEMP_FILE for editing."
            else
                echo "  - FAILED to decrypt $FILE"
            fi
        else
            # If plain text, create .temp and encrypt
            echo "Backing up and encrypting plain-text $FILE..."
            cp "$FILE" "$TEMP_FILE"
            ansible-vault encrypt "$FILE" --vault-password-file "$PASS_FILE" > /dev/null
            echo "  - Backup created: $TEMP_FILE"
            echo "  - Encrypted original: $FILE"
        fi
    fi
done

# Cleanup
rm "$PASS_FILE"
echo "Done."
