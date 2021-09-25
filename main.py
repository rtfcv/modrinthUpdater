import os.path
import sys
import io

import json
from urllib import request

config = None
config_dir = ''
config_file = ''


def load_paths():
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
    global config

    load_paths()

    # try to load config
    try:
        with open(config_file, mode='r') as file:
            config = json.load(file)
    except FileNotFoundError:
        config = {}


def save_config():
    global config
    global config_dir
    global config_file
    if not os.path.exists(config_dir):
        os.makedirs(config_dir, exist_ok=True)

    with open(config_file, mode='w') as file:
        json.dump(config, file, indent=2)


def initialize():
    global config
    global config_dir
    global config_file
    load_config()

    try:
        do_exit = config['exit_right_away']
    except BaseException:
        do_exit = False

    if (config == {}) or do_exit:
        config['exit_right_away'] = True
        config['current_game_ver'] = '1.17.1'
        config['dest_dir'] = 'your_install_destination'
        config['mods'] = {}
        config['mods']['P7dR8mSH'] = {}
        config['mods']['replace_this_with_project_ids'] = {}
        # # mod_id = 'AZomiSrC'
        # # mod_id = 'AANobbMI'
        # mod_id = 'YL57xq9U'
        save_config()
        print('config was empty or disabled')
        print(f'edit {config_file} to use')
        print('delete key "exit_right_away" or set it to False')
        sys.exit(1)
    save_config()


def main():
    global config
    global config_dir
    global config_file

    initialize()

    for mod_id in config['mods'].keys():
        if mod_id == 'exit_right_away':
            continue

        current_game_version = config['current_game_ver']
        dest_dir = config['dest_dir']

        versions = []
        with request.urlopen('https://api.modrinth.com/api/v1/mod/'
                             + mod_id + '/version') as req:
            versions = json.loads(req.read())

        v = 0
        url = ''
        fname = ''
        version_number = ''
        for v in range(len(versions)):
            if current_game_version in versions[v]['game_versions']:
                version_number = versions[v]['version_number']
                url = versions[v]['files'][0]['url']
                fname = versions[v]['files'][0]['filename']
                break

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
            print(f'{fname} is up to date: {version_number}')
            continue

        # download if otherwise
        with request.urlopen(url) as req,\
                io.open(os.path.join(dest_dir, fname), 'wb') as file:
            file.write(req.read())

        # remove old file if any
        if os.path.exists(os.path.join(dest_dir, oldfile))\
                and oldfile != fname:
            os.remove(os.path.join(dest_dir, oldfile))

        load_config()
        # You really should make sure that the config was
        # not edited in the meantime but whatever
        config['mods'][mod_id]['current_version'] = version_number
        config['mods'][mod_id]['fname'] = fname
        save_config()



main()
