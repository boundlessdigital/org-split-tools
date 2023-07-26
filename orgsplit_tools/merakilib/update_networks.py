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
meraki - update_networks.py

small async tool that takes a nested dict with data to update a network with the data in that nested dict
NOTE:  this is modified from my original to only rename networks!!!
old_name, new_name, and network id are required!

example list with one or more dicts and required fields to pass into async_update_networks as networks:
[{'enrollmentString': None,
  'id': 'L_12345',
  'isBoundToConfigTemplate': False,
  'name': 'TEST-Blah-5678',
  'network_id': 'L_12345',
  'network_name': 'TEST-Test-5678',
  'new_name': 'TEST-Blah-5678',
  'notes': None,
  'old_name': 'TEST-Test-5678',
  'organizationId': '1234',
  'organization_name': 'TMP',
  'productTypes': ['appliance',
                   'camera',
                   'cellularGateway',
                   'sensor',
                   'switch',
                   'wireless'],
  'tags': [],
  'timeZone': 'America/Los_Angeles',
  'url': 'https://n51.meraki.com/url'}]'''

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

async def _update_networks(aiomeraki, network_to_update):
    '''
    Async function that calls updateNetwork for a given network
    '''

    try:
        updated_network = await aiomeraki.networks.updateNetwork(
            networkId=network_to_update['network_id'],
            name=network_to_update['new_name']
        )

    except meraki.exceptions.AsyncAPIError as e:
        print(
            f'Meraki AIO API Error (NetworkIDs "{ network_to_update["network_ids"] }", Combined Network Name "{ network_to_update["network_name_combined"] }"): \n { e }'
        )

        updated_network = None

    except Exception as e:
        print(e)
        print(f'some other ERROR: {e}')
        updated_network = None

    return [{**network_to_update, **updated_network}] if updated_network else None

async def _async_apicall(api_key, networks, debug_values, cert_path):
    # if debug_values['output_log']:
    #     log_path = _create_logdir(dir_name=debug_values['log_dir'], package_dir = 'masync')
    # else:
    #     log_path = debug_values['log_dir']

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
            suppress_logging=debug_values['suppress_logging'],
            certificate_path=cert_path) as aiomeraki:

        update_results = []

        network_tasks = [_update_networks(aiomeraki, network) for network in networks]
        for task in tqdm.tqdm(
                asyncio.as_completed(network_tasks),
                total=len(networks),
                colour='green',
        ):

            network_json = await task
            if network_json:
                update_results.extend(iter(network_json))

        return update_results

def async_update_networks(api_key, networks, debug_app=False, cert_path=None):
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



