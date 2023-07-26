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
meraki - recombine_networks.py

small async tool that takes a nested dict with data including 2 or more networkIds to combine

example list with one or more dicts and required fields to pass into async_recombine_networks as networks:
[{'enrollment_string': None,
  'network_ids': ['N_1234',
                  'N_5678',
                  'N_4321'],
  'network_name_combined': 'MY-NEW-NETWORK-NAME',
  'organization_id': '123456'}]
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

async def _recombine_networks(aiomeraki, networks_to_combine):
    '''
    Async function that calls combineOrganizationNetworks for a given org and network
    '''

    try:
        if networks_to_combine['enrollment_string']:
            combined_networks = await aiomeraki.organizations.combineOrganizationNetworks(
                organizationId=networks_to_combine['organization_id'],
                name = networks_to_combine['network_name_combined'],
                networkIds = networks_to_combine['network_ids'],
                enrollmentString = networks_to_combine['enrollment_string']
            )
        else:
            combined_networks = await aiomeraki.organizations.combineOrganizationNetworks(
                organizationId=networks_to_combine['organization_id'],
                name = networks_to_combine['network_name_combined'],
                networkIds = networks_to_combine['network_ids'],
            )

    except meraki.exceptions.AsyncAPIError as e:
        print(
            f'Meraki AIO API Error (NetworkIDs "{ networks_to_combine["network_ids"] }", Combined Network Name "{ networks_to_combine["network_name_combined"] }"): \n { e }'
        )

        combined_networks = None

    except Exception as e:
        print(e)
        print(f'some other ERROR: {e}')
        combined_networks = None

    if combined_networks:
        combined_json = [{
            'recombined_network_name': networks_to_combine['network_name_combined'],
            'resulting_network': combined_networks['resultingNetwork'],
            'previous_networks': networks_to_combine['networks']
        }]

    else:
        combined_json = None
    
    return combined_json

async def _async_apicall(api_key, networks, debug_values, cert_path):
    
    # Instantiate a Meraki dashboard API session
    # NOTE: you have to use "async with" so that the session will be closed correctly at the end of the usage
    async with meraki.aio.AsyncDashboardAPI(
            api_key,
            base_url='https://api.meraki.com/api/v1',
            log_file_prefix=__file__[:-3],
            # log_path=log_path,
            maximum_concurrent_requests=10,
            maximum_retries=100,
            wait_on_rate_limit=True,
            output_log=debug_values['output_log'],
            print_console=debug_values['output_console'],
            certificate_path=cert_path,
            suppress_logging=debug_values['suppress_logging']) as aiomeraki:

        recombine_results = []

        network_tasks = [_recombine_networks(aiomeraki, network) for network in networks]
        for task in tqdm.tqdm(
                asyncio.as_completed(network_tasks),
                total=len(networks),
                colour='green',
        ):

            network_json = await task
            if network_json:
                recombine_results.extend(iter(network_json))

        return recombine_results

def async_recombine_networks(api_key, networks, debug_app=False, cert_path=None):
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
    return loop.run_until_complete(_async_apicall(api_key, networks, debug_values, cert_path))
