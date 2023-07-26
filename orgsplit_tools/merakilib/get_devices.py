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
meraki - get_devices.py

small async tool that returns all devices for given org
'''


def create_logdir(dir_name):
    path_exists = os.path.exists(dir_name)
    if not path_exists:
        os.makedirs(dir_name)


async def get_devices(aiomeraki, org):
    '''
    Async function that calls getOrganizationDevices for a given org
    '''
    try:

        print(f'Getting devices for org {org["name"]}')
        devices = await aiomeraki.organizations.getOrganizationDevices(
            organizationId=org['id'],
            total_pages='all'
            )

    except meraki.exceptions.AsyncAPIError as e:
        print(
            f'Meraki AIO API Error (OrganizationID "{ org["id"] }", OrgName "{ org["name"] }"): \n { e }'
        )
        devices = None

    except Exception as e:
        print(f'some other ERROR: {e}')
        devices = None

    if devices:
        org_devices = [{
            'organizationName': org['name'],
            'organizationId': org['id'],
            **device_dict, 
        } for device_dict in devices]

        return org_devices

    else:
        print(
            f'The following organization has no devices: (OrganizationID "{ org["id"] }", OrgName "{ org["name"] }")\n '
        )
        return None


async def async_apicall(api_key, orgs, debug_values, cert_path):
    if debug_values['output_log']:
        create_logdir(dir_name=debug_values['log_dir'])

    # Instantiate a Meraki dashboard API session
    # NOTE: you have to use "async with" so that the session will be closed correctly at the end of the usage
    async with meraki.aio.AsyncDashboardAPI(
            api_key,
            base_url='https://api.meraki.com/api/v1',
            log_file_prefix=__file__[:-3],
            log_path=debug_values['log_dir'],
            maximum_concurrent_requests=10,
            maximum_retries=100,
            wait_on_rate_limit=True,
            output_log=debug_values['output_log'],
            print_console=debug_values['output_console'],
            suppress_logging=debug_values['suppress_logging'],
            certificate_path=cert_path) as aiomeraki:

        all_devices = []
        device_tasks = [get_devices(aiomeraki, org) for org in orgs]
        for task in tqdm.tqdm(
                asyncio.as_completed(device_tasks),
                total=len(all_devices),
                colour='green',
        ):

            device_json = await task

            if device_json:
                all_devices.extend(iter(device_json))

        return all_devices


def asyncget_devices(api_key, orgs, debug_app=False, cert_path=None):
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
    return loop.run_until_complete(async_apicall(api_key, orgs, debug_values, cert_path))