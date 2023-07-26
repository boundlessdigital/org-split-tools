import meraki
import meraki.aio
import asyncio
import tqdm.asyncio
import os
from pprint import pprint

__author__ = 'Zach Brewer'
__email__ = 'zbrewer@cisco.com'
__version__ = '0.1.0'
__license__ = 'MIT'
'''
meraki - get_networks.py

NOTE: MODIFIED from original to include find and replace strings

small async tool that takes either an API key or orgs from getOrganizations Dashboard API call 
Returns a nested Python object with OrgName, OrgID, and other network data

Useful because Dashboard API does not include orgname in getOrgNetworks

Also useful to be able to return all given networks for all orgs (or a subset of orgs) and call them via python dict
'''


def _create_logdir(dir_name, package_dir):
    current_path = os.path.dirname(os.path.realpath(__file__))

    # are we in the package directory? if so create our log file in the parent dir
    if os.path.split(current_path)[1] == package_dir:
        parent_dir = os.path.abspath(os.path.join(current_path, os.pardir))
        parent_log_path = os.path.join(parent_dir, dir_name)
        path_exists = os.path.exists(parent_log_path)
        log_path = parent_log_path
    else:
        path_exists = os.path.exists(dir_name)
        log_path =  os.path.join(current_path, dir_name)

    if not path_exists:
        os.makedirs(log_path)
    
    return log_path

async def _get_orgnetworks(aiomeraki, org):
    '''
    Async function that calls getOrganizationNetworks for a given org
    '''

    try:
        networks = await aiomeraki.organizations.getOrganizationNetworks(
            organizationId=org['id'], total_pages=-1)

    except meraki.exceptions.AsyncAPIError as e:
        print(
            f'Meraki AIO API Error (OrgID "{ org["id"] }", OrgName "{ org["name"] }"): \n { e }'
        )
        networks = None
    except Exception as e:
        print(f'some other ERROR: {e}')
        networks = None

    if networks:
        org_networks = [{
            'organizationName': org['name'],
            'organizationId': org['id'],
            **network_dict, 
        } for network_dict in networks]
    
    else:
        org_networks = None
    
    return org_networks


async def _async_apicall(api_key, orgs, debug_values, cert_path):
    if debug_values['output_log']:
        log_path = _create_logdir(dir_name=debug_values['log_dir'], package_dir = 'masync')
    else:
        log_path = debug_values['log_dir']
    
    # Instantiate a Meraki dashboard API session
    # NOTE: you have to use "async with" so that the session will be closed correctly at the end of the usage
    async with meraki.aio.AsyncDashboardAPI(
            api_key,
            base_url='https://api.meraki.com/api/v1',
            log_file_prefix=__file__[:-3],
            log_path=log_path,
            maximum_concurrent_requests=10,
            maximum_retries=100,
            wait_on_rate_limit=True,
            output_log=debug_values['output_log'],
            print_console=debug_values['output_console'],
            suppress_logging=debug_values['suppress_logging'],
            certificate_path=cert_path) as aiomeraki:

        all_orgnetworks = []

        network_tasks = [_get_orgnetworks(aiomeraki, org) for org in orgs]
        for task in tqdm.tqdm(
                asyncio.as_completed(network_tasks),
                total=len(all_orgnetworks),
                colour='green',
        ):

            network_json = await task
            if network_json:
                all_orgnetworks.extend(iter(network_json))
        
        return all_orgnetworks

def asyncget_networks(api_key, orgs, debug_app=False, cert_path=None):
    if debug_app:
        debug_values = {
            'output_log': True,
            'output_console': True,
            'suppress_logging': False,
            'log_dir': 'logs'
        }
    else:
        debug_values = {
            'output_log': False,
            'output_console': False,
            'suppress_logging': True,
            'log_dir': None
        }

    #begin async loop
    loop = asyncio.get_event_loop()
    return loop.run_until_complete(_async_apicall(api_key, orgs, debug_values, cert_path))



