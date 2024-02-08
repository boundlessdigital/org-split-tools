import json
import time

import click
import meraki
from prettytable import PrettyTable

from orgsplit_tools.merakilib import get_networks, update_networks


class CallDashboard(object):
    def __init__(self, apikey, debug, cert_path=None):
        """
        call to dashboard API and makes session available to other methods in this class
        """
        if debug:
            self.api_session = meraki.DashboardAPI(
            api_key=apikey,
            base_url="https://api.meraki.com/api/v1/",
            output_log=True,
            print_console=True,
            suppress_logging=False,
            certificate_path=cert_path
            )
        else:
            self.api_session = meraki.DashboardAPI(
            api_key=apikey,
            base_url="https://api.meraki.com/api/v1/",
            output_log=False,
            print_console=False,
            suppress_logging=True,
            certificate_path=cert_path

            )

    def get_allorgs(self):
        return self.api_session.organizations.getOrganizations()

def clean_orgs(all_orgs, org_name):

    user_org = org_name.lower().strip()
    
    cleaned_orgs = []
    for org in all_orgs:
        if org['name'].lower().strip() == user_org:
            cleaned_orgs.append(org)

    if cleaned_orgs:
        return cleaned_orgs

    else:
        click.secho(f'[WARNING] Could not find given Organiztion Name: "{org_name}."\n',
            fg='yellow')
        click.secho(
        'NOTE: Organization names that contain spaces must be wrapped in quotes (e.g. "Org Name")\n',
        fg='yellow'
        )

        if click.confirm('Print all org names that this apikey has access to?'):
            for org in all_orgs:
                click.secho(f'{org["name"]}',
                fg='green',
                )
            exit(0)

        else:
            exit(0)


@click.group()
@click.pass_context
def rename_group(ctx):
     pass

@rename_group.command(name='rename', context_settings={"ignore_unknown_options": True})
@click.option(
    '-k',
    '--apikey', 
    prompt=True, 
    hide_input=True,
    required=True,  
    metavar='[APIKEY]',
    help='API key with access to one or more organizations.'
    )
@click.option(
            '-o', 
            '--orgname',
            metavar='[ORGNAME] or [All]', 
            required=True,  
            help='Perform the action on a single organization or use "all" for all orgnames. Organization name or ALL must follow --orgname option'
            )
@click.option(
            '-f', 
            '--filter',
            metavar='[FILTER STRING]', 
            required=False,  
            help='A filter to perform on any organization names that begin with the given string (Case sensitive).'
            )
@click.argument('find_string', nargs=1)
@click.argument('replace_string', nargs=1)
@click.pass_context
def rename(ctx, apikey, orgname, filter, find_string, replace_string):
    """
    Replaces part or all of a network name in one or more organizations
    """

    if ctx.obj is not None:
        debug = ctx.obj['debug']
        cert_path = ctx.obj['cert_path']

    click.secho('Getting org info...\n', fg='green', bold=True)

    try:
        session = CallDashboard(apikey=apikey, debug=debug, cert_path=cert_path)
        all_orgs = session.get_allorgs()

    except meraki.exceptions.APIError as e:
        print(f'Meraki API ERROR: {e}\n')
        exit(0)

    except Exception as e:
        print(f'Non Meraki-SDK ERROR: {e}')
        exit(0)

    if orgname != 'all':
        if filter:
            click.secho(f'[WARNING] --filter (-f) option is ignored when used with a single organization.\n',
            fg='yellow',
            bold=True)


        user_orgs = clean_orgs(all_orgs=all_orgs, org_name=orgname)
    
    else:
        
        if filter:
            filtered_orgs = [org for org in all_orgs if org['name'].startswith(filter)]
            user_orgs = filtered_orgs


    # @ToDo : fix early reference error when all is used with no filter
    org_names = []

    for name in user_orgs:
        org_names.append(name['name'])

    click.secho(f'Getting networks for the following orgs {org_names} \n', fg='green', bold=True)
    all_org_networks = get_networks.asyncget_networks(api_key=apikey, 
                                                      orgs=user_orgs,
                                                      debug_app=debug,
                                                      cert_path=cert_path)

    to_rename_networks = []

    for network in all_org_networks:
        if find_string in network['name']:
           new_name = network['name'].replace(find_string, replace_string)
           new_dict = {
            'organizationName': network['organizationName'],
            'organizationId': network['organizationId'],
            'network_id': network['id'],
            'name': network['name'],
            'productTypes': network['productTypes'],
            'timeZone': network['timeZone'],
            'tags': network['tags'],
            'enrollmentString': network['enrollmentString'],
            'url': network['url'],
            'notes': network['notes'],
            'isBoundToConfigTemplate': network['isBoundToConfigTemplate'],
            'new_name': new_name,
            'old_name': network['name']
            }
           
           to_rename_networks.append(new_dict)
        else:
            click.secho(f'String {find_string} not found in network "{network["name"]}"', fg='green', bold=True)
    
    to_rename_table = PrettyTable(['Old Name', 'New Name'])
    if to_rename_networks:
        for network in to_rename_networks:
            old_name = network['old_name']
            new_name = network['new_name']
            to_rename_table.add_row([old_name, new_name])

        print('\n')
        print(to_rename_table)
        print('\n')
    else:
        click.secho(f'\nNo networks matched! (network names in the given orgs did not contain the string "{find_string}") \n', fg='yellow', bold=True)
        exit(0)

    if click.confirm('Confirm new network names in the table above before continuing.  This step cannot be undone without another rename.  Continue?'):
        updated_networks = update_networks.async_update_networks(api_key=apikey, networks=to_rename_networks, cert_path=cert_path)
    else:
        exit(0)

    if update_networks:
        timestr = time.strftime("%Y%m%d-%H%M%S")
        json_filename = f'{orgname}_rename_{timestr}.json'

        click.secho(f'\nNetwork rename process was successfull - output JSON for the operation written to filename "{ json_filename }."\n', fg='green', bold=True)

        with open (json_filename, 'w') as outfile:
            outfile.write(json.dumps(updated_networks, indent=4))
    else:
        click.secho(f'\nSomething went wrong - check the screen for errors. You may need to re-run with the debug (-d) flag set \n', fg='yellow', bold=True)

if __name__ == "__main__":
    rename()

