import click

import orgsplit_tools.subcommands.device_count as device_count
import orgsplit_tools.subcommands.precheck as precheck
import orgsplit_tools.subcommands.rename as rename
import orgsplit_tools.subcommands.recombine as recombine

# override general help to match other options, use group callback to this dict
ctx_settings = dict(help_option_names=['-h', '--help'])

__author__ = 'Zach Brewer'
__email__ = 'zbrewer@cisco.com'
__version__ = '0.1.0'
__license__ = 'MIT'

# begin click group and cli options for mtk parent
@click.group(context_settings=ctx_settings)
@click.option('-d', '--debug', is_flag=True, help='Flag for debug')
@click.option('-c', 'certpath', help='Optional path to api.meraki.com cert for rare error')
@click.pass_context
def entry_point(ctx, debug, certpath):
    '''orgsplit.py 
    CLI suite of tools for pre and post Meraki Organization split
    
    Help for specific CMDs: orgsplit.py [CMD] --help
    '''

    if ctx.obj is None:
        ctx.obj = {}

    ctx.obj['debug'] = debug
    ctx.obj['cert_path'] = certpath


'''
Command specific entry points go here

FORMAT: package.function
The module must have been imported first!
'''
entry_point.add_command(device_count.device_count)
entry_point.add_command(precheck.precheck)
entry_point.add_command(recombine.recombine)
entry_point.add_command(rename.rename)

if __name__ == "__main__":
    entry_point()

