import requests as rq
import sys
import argparse

# deletes clinical data for UHN node from katsu only.
# Program auths and genomic data are not touched


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument('--url', type=str, required=True, help="Url of your candig instance")
    parser.add_argument('--exclude', type=str, required=False,
                        help="Comma-delimited list of programs to exclude from the deletion, all other programs at the "
                             "node will be deleted")
    parser.add_argument('--program-list', type=str, required=False,
                        help="Comma-delimited list of programs to delete")
    args = parser.parse_args()
    return args


def main():
    args = parse_args()
    if args.exclude and args.program_list:
        print("Cannot specify both program list and exclude. Please choose one and try again.")
        sys.exit()
    token = input("Enter site admin token for prod instance:")
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json; charset=utf-8"
    }
    response = rq.get(f"{args.url}/query/discovery/query",
                      headers=headers)
    if response.status_code != 200:
        print("Error retrieving program data, please check your token and try again")
        sys.exit()
    program_list = list(response.json()['patients_per_program'].keys())
    if args.exclude:
        exclude_programs = [item.strip() for item in args.exclude.split(',')]
        program_list = set(program_list) - set(exclude_programs)
    elif args.program_list:
        include_program_list = [item.strip() for item in args.program_list.split(',')]
        if not set(include_program_list).issubset(set(program_list)):
            print("Unrecognized programs in --program-list, please check the string and try again")
            print("Programs not found:")
            unrecognised_programs = set(include_program_list).difference(program_list)
            print(f"{'\n'.join(unrecognised_programs)}")
            sys.exit()
        else:
            program_list = include_program_list
    print(f"WARNING: this script will delete all clinical data in the following {len(program_list)} programs:")
    print(f"{'\n'.join(program_list)}")
    answer = input("Do you wish to continue? (Y/N)")
    if answer == "Y":
        for program in program_list:
            print(f"deleting {program}")
            deletion_url = f"{args.url}/katsu/v3/ingest/program/{program}/"
            response = rq.delete(deletion_url, headers=headers)
            if response.status_code != 204:
                print("Error deleting program, please check your token and try again")
                sys.exit()
            print(response)
    elif answer == "N":
        print("User decided not to continue, exiting..")
        sys.exit()
    else:
        print("Input not recognized, use Y for yes or N for no. Exiting...")
        sys.exit()


if __name__ == '__main__':
    main()
