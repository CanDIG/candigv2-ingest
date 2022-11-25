import argparse
import os
from dotenv import dotenv_values

def main():
    parser = argparse.ArgumentParser(description="Script to automate creating env.sh")
    parser.add_argument("candigv2", help="Location of CanDIGv2 repo")
    args = parser.parse_args()
    
    candigv2 = args.candigv2
    candigv2_env = dotenv_values(f"{candigv2}/.env")

    vars = {}
    vars["CANDIG_URL"] = candigv2_env["TYK_LOGIN_TARGET_URL"]
    vars["CANDIG_CLIENT_ID"] = candigv2_env["KEYCLOAK_CLIENT_ID"]
    vars["KEYCLOAK_PUBLIC_URL"] = candigv2_env["KEYCLOAK_PUBLIC_URL"]
    vars["VAULT_URL"] = vars["CANDIG_URL"] + "/vault"
    vars["OPA_URL"] = vars["CANDIG_URL"] + "/policy"
    vars["OPA_SITE_ADMIN_KEY"] = candigv2_env["OPA_SITE_ADMIN_KEY"]

    # vars that come from files:
    with open(f"{candigv2}/tmp/secrets/keycloak-client-{vars['CANDIG_CLIENT_ID']}-secret") as f:
        vars["CANDIG_CLIENT_SECRET"] = f.read().splitlines().pop()
    with open(f"{candigv2}/tmp/secrets/keycloak-test-user2") as f:
        vars["CANDIG_SITE_ADMIN_USER"] = f.read().splitlines().pop()
    with open(f"{candigv2}/tmp/secrets/keycloak-test-user2-password") as f:
        vars["CANDIG_SITE_ADMIN_PASSWORD"] = f.read().splitlines().pop()
    with open(f"{candigv2}/tmp/secrets/vault-s3-token") as f:
        vars["VAULT_S3_TOKEN"] = f.read().splitlines().pop()
    with open(f"{candigv2}/tmp/secrets/opa-root-token") as f:
        vars["OPA_SECRET"] = f.read().splitlines().pop()

    with open("env.sh", "w") as f:
        for key in vars.keys():
            f.write(f"export {key}={vars[key]}\n")

if __name__ == "__main__":
    main()
# set -xuo pipefail
# 
# CANDIGV2=$1
# more $CANDIGV2/tmp/secrets/keycloak-client-local_candig-secret 
# more $CANDIGV2/tmp/secrets/minio-secret-key 
# more $CANDIGV2/tmp/secrets/keycloak-test-user-password 
# more $CANDIGV2/tmp/secrets/keycloak-test-user2-password 
# more $CANDIGV2/tmp/secrets/vault-s3-token 
# more $CANDIGV2/tmp/secrets/keycloak-admin-password 
# more $CANDIGV2/tmp/secrets/opa-root-token 
# docker exec candigv2_vault-runner_1 tail -n 1 /vault/config/keys.txt