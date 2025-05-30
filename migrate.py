import authx.auth
import auth


def main():
    role_types, status_code = auth.list_role_types()
    if status_code == 200:
        for role_type in role_types:
            result, status_code = auth.get_role_type(role_type)
            if status_code == 200:
                auth.set_role_type(role_type, result[role_type])

    programs, status_code = auth.list_programs()
    if status_code == 200:
        for program_id in programs:
            program, status_code = auth.get_program(program_id)
            if status_code == 200:
                auth.add_program(program)


if __name__ == "__main__":
    main()
