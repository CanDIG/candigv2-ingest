CANDIGV2=$1
more $CANDIGV2/tmp/secrets/keycloak-client-local_candig-secret 
more $CANDIGV2/tmp/secrets/minio-secret-key 
more $CANDIGV2/tmp/secrets/keycloak-test-user-password 
more $CANDIGV2/tmp/secrets/keycloak-test-user2-password 
more $CANDIGV2/tmp/secrets/vault-s3-token 
more $CANDIGV2/tmp/secrets/keycloak-admin-password 
docker exec candigv2_vault-runner_1 tail -n 1 /vault/config/keys.txt