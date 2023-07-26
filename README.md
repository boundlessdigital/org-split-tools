Meraki Org Split Tools
-----------------  

Meraki Org Split Tools (orgsplit.py) - a suite of CLI applications for use before/after/during a Meraki Dashboard Organization split.

There are four operations supported today in each of the following commands:

* **device-count** - Device counts for one or more organizations
* **precheck** - Does various checks and provides an org-split readiness report for a given org
* **recombine** - A command to re-combine networks on a child org post organization split
* **rename** - A command that supports finding and replacing given strings in network names.  Commonly used to rename the networks to match a new naming convention in a child org (post org-split)

Various flags and options reviewed by using the help flag following any command, e.g.
```
orgsplit.py -h
```

which outputs the following:

```
Usage: orgsplit.py [OPTIONS] COMMAND [ARGS]...

  orgsplit.py  CLI suite of tools for pre and post Meraki Organization split

  Help for specific CMDs: orgsplit.py [CMD] --help

Options:
  -d, --debug  Flag for debug
  -c TEXT      Optional path to api.meraki.com cert for rare error
  -h, --help   Show this message and exit.

Commands:
  device-count  Device counts for one or more organizations
  precheck      Identify settings that may need to be changed prior to an...
  recombine     Recombines networks that were previously split by product...
  rename        Replaces part or all of a network name in one or more...
```

You can also use the -h command for a given subcommand:
```
python orgsplit.py device-count -h
```

output:
```
Usage: orgsplit.py device-count [OPTIONS]

  Device counts for one or more organizations

Options:
  -k, --apikey [APIKEY]           API key with access to one or more
                                  organizations.  [required]
  -o, --orgname [ORGNAME] or [All]
                                  Perform the action on a single organization
                                  or use "all" for all orgnames. Organization
                                  name or ALL must follow --orgname option
                                  [required]
  -f, --filter [FILTER STRING]    A filter to perform on any organization
                                  names that begin with the given string (Case
                                  sensitive).
  -h, --help                      Show this message and exit.
```

# Installation

orgsplit tools can be installed as a package from this git repository.  Note that orgsplit tools requires **Python 3.8 or higher**

Installing to a Python Virtual Environment is highly reccomended but not required.



## Changelog

[Changelog](CHANGELOG.txt)

## License

[License](LICENSE)