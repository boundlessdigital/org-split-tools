import itertools

import click
import meraki

# from merakilib import get_networks
from orgsplit_tools.merakilib import get_devices


class CallDashboard(object):
    def __init__(self, apikey, debug):
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
            )
        else:
            self.api_session = meraki.DashboardAPI(
            api_key=apikey,
            base_url="https://api.meraki.com/api/v1/",
            output_log=False,
            print_console=False,
            suppress_logging=True,
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
def device_count_group(ctx):
     pass

@device_count_group.command(name='device-count')
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

@click.pass_context
def device_count(ctx, apikey, orgname, filter):
    """
    Device counts for one or more organizations
    """

    if ctx.obj is not None:
        debug = ctx.obj['debug']
        cert_path = ctx.obj['cert_path']

    click.secho('Getting org info...\n', fg='green')

    try:
        session = CallDashboard(apikey=apikey, debug=debug)
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
            fg='yellow')


        user_orgs = clean_orgs(all_orgs=all_orgs, org_name=orgname)
    
    else:
        
        if filter:
            filtered_orgs = [org for org in all_orgs if org['name'].startswith(filter)]
            user_orgs = filtered_orgs

    async_org_devices = get_devices.asyncget_devices(api_key=apikey, orgs=user_orgs, cert_path=cert_path)

    all_org_devices = [{user_org['name']: 
                        [{'cellularGateway':[0],
                    'switch':[0],
                    'appliance':[0],
                    'wireless':[0],
                    'sensor':[0],
                    'camera':[0],
                    'total':[0]}]}for user_org in user_orgs]

    for device, org_name, in itertools.product(async_org_devices, all_org_devices):    
        for k in org_name.items():
            org_name_dictkey = k[0]
            if org_name_dictkey in device['organizationName']:
                product_type = device['productType']
                org_name[org_name_dictkey][0][product_type][0] += 1
                org_name[org_name_dictkey][0]['total'][0] += 1

    all_devices = 0
    cellular_gateway = 0
    switch = 0
    appliance = 0
    wireless = 0
    sensor = 0
    camera = 0

    print('\n')

    for each_org in all_org_devices:
        for org_name, quantities in each_org.items():
            print(f'quantities for org {org_name}:')
            for all_quantities in quantities:
                for device, quantity in all_quantities.items():
                    print(f'{device}: {quantity[0]}')
                    if device == 'total':
                        all_devices += quantity[0]
                    elif device == 'cellularGateway':
                        cellular_gateway += quantity[0]
                    elif device == 'switch':
                        switch += quantity[0]
                    elif device == 'appliance':
                        appliance += quantity[0]
                    elif device == 'wireless':
                        wireless += quantity[0]
                    elif device == 'sensor':
                        sensor += quantity[0]
                    elif device == 'camera':
                        camera += quantity[0]
                    else:
                        click.secho(f'[WARNING] Unknown device type: "{device}."\n',
                            fg='yellow')

        print('\n')

    print('Total devices in all orgs:')
    print(f'cellularGateways: {cellular_gateway}')
    print(f'switches: {switch}')
    print(f'appliances: {appliance}')
    print(f'wireless: {wireless}')
    print(f'sensors: {sensor}')
    print(f'camera: {camera}')
    print(f'total: {all_devices}')

if __name__ == "__main__":
    device_count()

