import argparse
import os.path
import sys
import io
import json
from urllib import request
from urllib.error import HTTPError
from copy import deepcopy

args = []
config = None
config_dir = ''
config_file = ''


def load_paths():
    ''' Configure path variables for this app
    '''
    global config_dir
    global config_file

    config_dirname = 'modrinthUpdater'
    config_fname = 'data.json'

    __platform__ = sys.platform
    if __platform__ == 'win32':
        HOME = os.environ.get('HOMEPATH')
        config_dir = os.path.join(HOME, r'AppData\Roaming', config_dirname)
        config_file = os.path.join(config_dir, config_fname)

    elif __platform__ == 'linux':
        HOME = os.environ.get('HOME')
        config_dir = os.path.join(HOME, '.config', config_dirname)
        config_file = os.path.join(config_dir, config_fname)

    else:
        print(f'Platform {__platform__} not supported')


def load_config():
    ''' Load from Config file onto global object: config
    '''
    global config

    load_paths()

    # try to load config
    try:
        with open(config_file, mode='r') as file:
            config = json.load(file)
    except FileNotFoundError:
        config = {}
        create_config()
        print('config file did not exist')
        print(f'edit {config_file} and configure "dest_dir" to use')
        sys.exit(1)


def save_config():
    ''' Write data present on global object: config, back to config file
    '''
    global config
    global config_dir
    global config_file
    if not os.path.exists(config_dir):
        os.makedirs(config_dir, exist_ok=True)

    with open(config_file, mode='w') as file:
        json.dump(config, file, indent=2)


def create_config():
    ''' Create Brand-new config. this is destructive.
    '''
    global config

    config['current_game_ver'] = '1.17.1'
    config['dest_dir'] = 'your_install_destination'
    config['mods'] = {}
    config['mods']['P7dR8mSH'] = {}
    save_config()


def initialize():
    ''' Check existance of config file
    should also check format to some extent
    '''
    global config
    global config_dir
    global config_file
    load_config()

    if (config == {}):
        create_config()
        print('config was empty')
        print(f'edit {config_file} and configure "dest_dir" to use')
        sys.exit(1)

    try:
        if not os.path.exists(config['dest_dir']):
            print(f'your dest_dir: {config["dest_dir"]}'
                  + ' does not seem to exist.')
            print(f'edit {config_file} and configure "dest_dir" to use')
            sys.exit(1)
    except BaseException as e:
        print(f'Error: {e}')
        print(f'Something was wrong with your config: {config_file}')
        sys.exit(1)
    save_config()


def update(args):
    global config
    global config_dir
    global config_file

    initialize()
    current_game_version = config['current_game_ver']
    dest_dir = config['dest_dir']

    print('Updating Mods...')
    for mod_id in config['mods'].keys():
        versions = []
        with request.urlopen('https://api.modrinth.com/api/v1/mod/'
                             + mod_id + '/version') as req:
            versions = json.loads(req.read())

        v = 0
        url = ''
        fname = ''
        version_number = ''
        version_matches = False
        for v in range(len(versions)):
            if current_game_version in versions[v]['game_versions']:
                version_number = versions[v]['version_number']
                url = versions[v]['files'][0]['url']
                fname = versions[v]['files'][0]['filename']
                version_matches = True
                break
        if not version_matches:
            print(f'{mod_id} does not match the game '
                  + f'version: {current_game_version}')
            continue

        # print(fname, version_number, url)

        try:
            oldfile = config['mods'][mod_id]['fname']
        except BaseException:
            # reset the config.mods.$mod_id should the content be unexpected
            config['mods'][mod_id] = {}
            oldfile = 'hoge'  # some placeholder

        # check if the latest is installed
        if (fname == oldfile)\
                and os.path.exists(os.path.join(dest_dir, fname)):
            print(f'{mod_id}: {fname} is up to date: {version_number}')
            continue

        # download if otherwise
        with request.urlopen(url) as req,\
                io.open(os.path.join(dest_dir, fname), 'wb') as file:
            print(f'downloading {fname}...')
            file.write(req.read())
            print(f'installing {fname}...')

        # remove old file if any
        if os.path.exists(os.path.join(dest_dir, oldfile))\
                and oldfile != fname:
            print(f'removing {oldfile}...')
            os.remove(os.path.join(dest_dir, oldfile))

        load_config()
        # You really should make sure that the config was
        # not edited in the meantime but whatever
        config['mods'][mod_id]['current_version'] = version_number
        config['mods'][mod_id]['fname'] = fname
        save_config()


def list(args):
    global config
    global config_dir
    global config_file

    initialize()
    for mod_id in config['mods'].keys():
        modinfo = []
        with request.urlopen('https://api.modrinth.com/api/v1/mod/'
                             + mod_id) as req:
            modinfo = json.loads(req.read())

        try:
            installed_ver = config['mods'][mod_id]['current_version']
            fname = config['mods'][mod_id]['fname']
        except KeyError:
            installed_ver = 'Not installed?'
            fname = 'Does not seem to be installed'

        # print(json.dumps(modinfo, indent=2))
        modname = modinfo['title']
        desc = modinfo['description']

        print(f'{mod_id}\t{modname}\t{installed_ver}')
        if args.verbose:
            print(f'\t{fname}')
            print(f'\t{desc}')
            print('')


def install(args):
    modlist = args.mods

    global config
    global config_dir
    global config_file

    changed = False

    initialize()

    current_game_version = config['current_game_ver']

    for mod_id in modlist:
        print(f'Checking Status for mod {mod_id}')

        # prevent duplicate
        if mod_id in config['mods'].keys():
            try:
                fpath = os.path.join(
                    config['mods'],
                    config['mods'][mod_id]['fname']
                )
            except BaseException:
                fpath = ''
            if os.path.exists(fpath):
                print(f'{mod_id}already in the list')
            else:
                changed = True
            # either way
            continue

        versions = []
        try:
            with request.urlopen('https://api.modrinth.com/api/v1/mod/'
                                 + mod_id + '/version') as req:
                versions = json.loads(req.read())
        except HTTPError as e:
            if e.code == 404:
                print(f'{mod_id} could not be found')
                print('double check the ID')
            else:
                print(f'There was error retrieving information of {mod_id}.')
                print(f'{e} happened: thats all we know')
            continue
        except BaseException as e:
            print(f'{e} happened')
            continue

        # check compatibility
        version_matches = False
        for v in range(len(versions)):
            if current_game_version in versions[v]['game_versions']:
                version_matches = True
                break

        if version_matches:
            load_config()
            print(f'adding {mod_id} to installation queue...')
            config['mods'][mod_id] = {}
            save_config()
            changed = True
        else:
            print(f'{mod_id} does not match the game '
                  + f'version: {current_game_version}')

    if changed:
        update(None)


def parse():
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(help='subcommands')

    # parser for install subcommand
    parser_install = subparsers.add_parser('install', help='install mods')
    parser_install.add_argument(
        'mods', nargs='*', type=str, help='Project IDs from modrinth'
    )
    parser_install.set_defaults(subcommand_func=install)

    # parser for update subcommand
    parser_update = subparsers.add_parser('update', help='update mods')
    parser_update.set_defaults(subcommand_func=update)

    # parser for list subcommand
    parser_list = subparsers.add_parser('list', help='list installed mods')
    parser_list.set_defaults(subcommand_func=list)
    parser_list.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='Print additional informations.'
    )

    args = parser.parse_args()

    if hasattr(args, 'subcommand_func'):
        args.subcommand_func(args)
    else:
        parser.print_help()
        initialize()


if __name__ == '__main__':
    parse()
