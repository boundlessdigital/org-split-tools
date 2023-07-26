import itertools

import click
import meraki

from orgsplit_tools.merakilib import get_appliance
from orgsplit_tools.merakilib import get_networks


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
    
    def get_lic_overview(self, org_id):
        return self.api_session.organizations.getOrganizationLicensesOverview(organizationId=org_id)

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
            fg='yellow', bold=True)
        click.secho(
        'NOTE: Organization names that contain spaces must be wrapped in quotes (e.g. "Org Name")\n',
        fg='yellow', bold=True
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
def precheck_group(ctx):
     pass

@precheck_group.command(name='precheck')
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
            help='Perform the action on a single organization'
            )

@click.pass_context
def precheck(ctx, apikey, orgname):
    """
    Identify settings that may need to be changed prior to an org-split
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


    user_org = clean_orgs(all_orgs=all_orgs, org_name=orgname)
    user_orgid = user_org[0]['id']

    license_check_status = None
    license_check_message = None
    client_tracking_message = None
    client_tracking_status = None
    template_tracking_message = None
    template_tracking_status = None

    readiness_report = []

    click.secho('::PRECHECK MODE::\n', fg='green', bold=True)
    click.secho('This mode will check for issues that may prevent a successful org split.\n', fg='green')
    click.secho('No changes will be made to the Dashboard Organization in this mode.\n', fg='green')

    if click.confirm('Continue?'):
        # ToDo : tracking type, MT only networks, templates, 
        click.secho('Gathering license information...\n', fg='green', bold=True)

        try:
            license_overview = session.get_lic_overview(org_id=user_orgid)

        except meraki.exceptions.APIError as e:
            print(f'Meraki API ERROR: {e}\n')
            exit(0)

        except Exception as e:
            print(f'Non Meraki-SDK ERROR: {e}')
            exit(0)

        # first precheck - client tracking
        click.secho(f'Getting network info for org {orgname} ...\n', fg='green')
        all_networks = get_networks.asyncget_networks(api_key=apikey, orgs=user_org, cert_path=cert_path)
        click.secho(f'Checking network appliance tracking type for each network in org {orgname} ...\n', fg='green')
        all_appliance_settings = get_appliance.asyncget_networks(api_key=apikey, networks=all_networks)

        if click.confirm('\nAll data gathered print Org Split Readiness Report?.\n'):
            click.secho('.:LICENSE STATUS:.\n', fg='green', bold=True)

        # second precheck = license
            if 'status' in license_overview:
                if license_overview['status'] == 'License Expired' or 'License Required':
                    click.secho('WARNING: License EXPIRED on this org, it is not reccomended to proceed with org split.\n', fg='yellow', bold=True)
                elif license_overview['status'] == 'License Expired' or 'License Required':
                    click.secho('WARNING: License REQUIRED for this org, it is not reccomended to proceed with org split.\n', fg='yellow', bold=True)
                elif license_overview['status'] == 'OK':
                    click.secho('LICSENSE PRECHECK PASSED!\n', fg='green')
            else:
                click.secho('No License overview status found - check license status in dashboard and coordinate with Meraki support before proceeding with org split.\n', fg='yellow', bold=True)

            click.secho('.:CLIENT TRACKING STATUS:.\n', fg='green', bold=True)
            tracksby_unique_client = [appliance_setting for appliance_setting in all_appliance_settings if appliance_setting['clientTrackingMethod'] == 'Unique client identifier']

            if tracksby_unique_client:
                click.secho('The following networks are tracking by unique client identifier.  They must be changed to track by MAC address before an org split\n', fg='yellow', bold=True)
                click.secho('This setting can be changed in Security & SD-WAN --> Addressing and VLANs\n', fg='yellow', bold=True)

                for appliance in tracksby_unique_client:
                    click.secho(f'Network Name: {appliance["networkName"]} Network ID: {appliance["networkId"]}\n', fg='yellow', bold=True)
            else:
                click.secho('CLIENT TRACKING PRECHECK PASSED!\n', fg='green')

                click.secho('No networks in this organization are tracking by Unique Client ID. No client tracking changes are needed prior to org split.\n', fg='green')
            
            # 3rd precheck - network templates
            click.secho('.:NETWORK TEMPLATE STATUS:.\n', fg='green', bold=True)
            template_bound = [network for network in all_networks if network['isBoundToConfigTemplate']]
            if template_bound:
                click.secho('The following networks are bound to configuration templates.\n', fg='yellow', bold=True)
                click.secho('configuration templates must be unbound before an org split. Please work with support as removing configuration templates can change settings.\n', fg='yellow', bold=True)
                click.secho('You may also want to use the TemplateBreaker tool written by Nico Darrow: https://github.com/wifiguru10/templateBreaker \n', fg='yellow', bold=True)
                for network in template_bound:
                    click.secho(f'Network Name: {network["name"]} Network ID: {network["id"]}\n', fg='yellow', bold=True)
            else:
                click.secho('NETWORK PRECHECK PASSED!\n', fg='green')

                click.secho('No template bound networks found in this org. No changes to network templates are necessary prior to Org Split.\n', fg='green')

        exit(0)
    exit(0)

if __name__ == "__main__":
    precheck()


