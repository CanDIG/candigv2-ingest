import auth
import sys
import os
import authx.auth
import requests


### Re-sets previously existing site roles and program roles:
### they may have been saved with mixed-case names before DIG-1974
### so will be re-saved by the updated set_role_type and add_program
### to be all lower-case.

### DIG-2097: Go through all programs and users to update their
### dac_authorizations.

VAULT_URL = os.getenv("VAULT_URL")
SERVICE_NAME = os.getenv("SERVICE_NAME")


def main():
    role_types, status_code = auth.list_role_types()
    if status_code == 200:
        for role_type in role_types:
            result, status_code = auth.get_role_type(role_type)
            if status_code == 200:
                auth.set_role_type(role_type, result[role_type])

    programs, status_code = auth.list_programs()
    print(programs)
    if status_code != 200:
        print(f"Couldn't list programs: {programs} {status_code}")
        sys.exit(1)

    # start a dictionary of programs that we can then add dacs to
    programs_dict = {}
    for program_id in programs:
        program, status_code = auth.get_program(program_id)
        if status_code == 200:
            programs_dict[program_id] = program
            programs_dict[program_id]["dac_authorizations"] = {}

    # need to call Vault to get the list of users
    headers = {
        "X-Vault-Token": authx.auth.get_vault_token_for_service()
    }
    url = f"{VAULT_URL}/v1/opa/users"
    response = requests.request("LIST", url, headers=headers)
    if response.status_code != 200:
        print(f"Couldn't list users: {response.text} {response.status_code}")
        sys.exit(1)

    errors = []
    result = response.json()["data"]["keys"]
    for user_id in result:
        user_dict, status_code = auth.get_user(user_id)
        if status_code != 200:
            errors.append(f"Couldn't get user {user_id}: {user_dict} {status_code}")

        if "dac_authorizations" in user_dict:
            for program_id in user_dict["dac_authorizations"]:
                # add the user's dac authz to the program
                programs_dict[program_id]["dac_authorizations"][user_id] = user_dict["dac_authorizations"][program_id]

        # write the user back
        response, status_code = auth.write_user(user_dict)
        if status_code != 200:
            errors.append(f"Couldn't write user {user_id}: {response} {status_code}")
        # print(response)

    for program_id in programs_dict:
        response, status_code = auth.add_program(programs_dict[program_id])
        if status_code != 200:
            errors.append(f"Couldn't write program {program_id}: {response} {status_code}")
        # print(response)

    if len(errors) > 0:
        print(errors)
        sys.exit(1)

if __name__ == "__main__":
    main()
