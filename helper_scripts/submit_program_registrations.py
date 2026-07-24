
import argparse
import pandas as pd
import requests as rq
import sys


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument('--input', type=str, required=True,
                        help="Csv file that has at least one column with the column header specified with the "
                             "--column-name argument")
    parser.add_argument('--column-name', type=str, default="program_id",
                        help="exact column name in the csv where the program id is specified. Default: 'program_id'")
    parser.add_argument('--url', type=str, required=True, help="Full URL of the CanDIG node")
    parser.add_argument('--token', type=str, required=True, help="site admin or site curator token")
    parser.add_argument('--curators', type=str, required=False,
                        help="comma delimited list of curators to add to each program")
    parser.add_argument('--team-members', type=str, required=False,
                        help="comma delimited list of team members to add to each program")
    args = parser.parse_args()
    return args


def add_program_authorization(program: str, token: str, url:str, curators: list = [], team_members: list = []):
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json; charset=utf-8",
    }

    # create a program and its authorizations:
    test_program = {
        "program_id": program,
        "program_curators": curators,
        "team_members": team_members
    }

    response = rq.post(f"{url}/ingest/program", headers=headers, json=test_program)
    print(response.text)


def main(args):
    candig_url = args.url
    programs_df = pd.read_csv(args.input)
    programs = set(programs_df[args.column_name])
    print(f"Found the following programs in the input file to ingest:")
    print("\n".join(programs))
    headers = {
        "Authorization": f"Bearer {args.token}",
        "Content-Type": "application/json; charset=utf-8",
    }
    response = rq.get(f"{candig_url}/ingest/program", headers=headers)
    if response.status_code == 200:
        registered_programs = set(response.json())
        programs_to_ingest = programs - registered_programs
        if len(programs_to_ingest) > 0:
            print("Proceeding to register missing programs:")
            print("\n".join(programs_to_ingest))
        else:
            print("All programs in input file already registered, exiting.")
            sys.exit()
    else:
        print(f"Did not get a success response from ingest/program endpoint: {response.status_code}, exiting.")
        sys.exit()
    if args.curators:
        curators = args.curators.split(',')
    else:
        curators = []
    if args.team_members:
        team_members = args.team_members.split(',')
    else:
        team_members = []
    for program in programs_to_ingest:
        add_program_authorization(program, args.token, candig_url, team_members=team_members, curators=curators)


if __name__ == '__main__':
    main(parse_args())
