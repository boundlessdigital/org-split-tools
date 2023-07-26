import time
import json
import itertools

import click
import meraki
from prettytable import PrettyTable

from orgsplit_tools.merakilib import get_networks
from orgsplit_tools.merakilib import recombine_networks

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
    
    def get_org_networks(self, org_id):
        return self.api_session.organizations.getOrganizationNetworks(organizationId=org_id, total_pages='all')

def clean_orgs(all_orgs, org_name):

    user_org = org_name.lower().strip()
    
    cleaned_orgs = []
    for org in all_orgs:
        if org['name'].lower() == user_org:
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
def recombine_group(ctx):
     pass

@recombine_group.command(name='recombine')
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
            metavar='[ORGNAME]', 
            required=True,  
            help='Perform the action on a single organization. Organization name must follow --orgname option'
            )
@click.pass_context
def recombine(ctx, apikey, orgname):
    """
    Recombines networks that were previously split by product type (post org-split)
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


    user_orgs = clean_orgs(all_orgs=all_orgs, org_name=orgname)
    user_orgid = user_orgs[0]['id']
    all_networks = session.get_org_networks(org_id=user_orgid)

    network_name_suffixes = [' - appliance', ' - switch', ' - wireless', ' - cellular gateway', ' - camera', ' - environmental', ' - phone']

    split_networks = []
    unique_names = set()

    to_combine_networks = []

    for network in all_networks:
        # filter out any potential combined networks
        if 'combined' not in network['productTypes']:
            split_networks.append(network)

    for network, suffix in itertools.product(split_networks, network_name_suffixes):
        if suffix in network['name']:
            new_name = network['name'].replace(suffix, '')
            if new_name not in unique_names:
                to_combine_networks.append({new_name: []})
                unique_names.add(new_name)

    for network, network_name in itertools.product(split_networks, to_combine_networks):
        for k in network_name.items():
            potential_name = k[0]
            if potential_name in network['name']:
                network_name[potential_name].append(network)

    to_rename_table = PrettyTable(['Combined Network', 'Previous Networks'])
    if to_combine_networks:
        for each_network in to_combine_networks:
            for new_name, network_details in each_network.items():
                previous_networks = []
                for network in network_details:
                    previous_networks.append(network['name'])

                combined_network_name = new_name
                to_rename_table.add_row([combined_network_name, previous_networks])

        print('\n')
        print(to_rename_table)
        print('\n')
        timestr = time.strftime("%Y%m%d-%H%M%S")
        to_combine_filename = f'{orgname}_to_combine_{timestr}.json'

        click.secho(f'Writing JSON for networks to combine to backup filename "{ to_combine_filename }."\n', fg='yellow', bold=True)

        with open (to_combine_filename, 'w') as outfile:
            outfile.write(json.dumps(to_combine_networks, indent=4))
        
        click.secho(f'Confirm new network names in the table above or review the file { to_combine_filename } before continuing.', fg='yellow', bold=True)

        click.secho(f'This step cannot be undone without another network split operation!\n',  fg='yellow', bold=True)

        if click.confirm(f'Continue?'):
            # updated_networks = recombine_networks.async_update_networks(api_key=apikey, networks=to_rename_networks, cert_path=cert_path)

            updated_networks = recombine_networks.async_recombine_networks(api_key=apikey, networks=to_combine_networks, debug_app=debug, cert_path=cert_path)
        else:
            exit(0)

    else:
        click.secho(f'\nNo networks matched! (network names in the given orgs did not contain one of the following suffixes: "{network_name_suffixes}" \n', fg='yellow', bold=True)
        exit(0)

    async_to_combine = []
    if to_combine_networks:
        # rebuild our data for our async merakilib (somewhat redundant step, will re-write later)
        for network in to_combine_networks:
            for k,v in network.items():
                new_dict = {
                            'network_name_combined': k, 
                            'network_ids': [v['id'] for v in v],
                            'networks': v,
                            'enrollment_string': v[0]['enrollmentString'],
                            'organization_id': v[0]['organizationId']
                            }
                async_to_combine.append(new_dict)

        click.secho(f'Combining networks for org "{ orgname }"\n', fg='green')

        recombined_networks = recombine_networks.async_recombine_networks(
                                                                        api_key=apikey,
                                                                        networks=async_to_combine,
                                                                        debug_app=debug,
                                                                        cert_path=cert_path
                                                                        )

        backup_filename = f'{orgname}_combined_{timestr}.json'
        with open (backup_filename, 'w') as outfile:
            outfile.write(json.dumps(recombined_networks, indent=4))

        click.secho(f'\nRecombine complete, backup filename results are in file "{ backup_filename }."\n', fg='green', bold=True)
