import asyncio
import argparse
import sys
import pathlib
import tomllib
import shutil

from pprint import pprint

async def pull_git(folder_def: dict, git_def: dict) -> None:
    git_folder = f'{folder_def.get("base", "")}/{folder_def.get("git", "")}'
    project_folder = pathlib.Path(git_folder) / git_def.get('folder', '')
    p = await asyncio.subprocess.create_subprocess_shell(f'cd {str(project_folder)} && git pull', 
                                                         stderr=asyncio.subprocess.PIPE, 
                                                         stdout=asyncio.subprocess.PIPE)
    await p.wait()
    
async def update_config(folder_def: dict) -> None:
    config_file: pathlib.Path = pathlib.Path(folder_def.get('base', '')) / folder_def.get('config', '') / 'config.toml'
    if config_file.exists():
        choise = input("""
    Kofigurationsdatei existiert bereits.
    Soll diese ersetzt werden [ja/Nein]  """)
        if choise.upper()[:1] == 'J':
            shutil.copy(config_file, str(config_file) + '.bak')
        else:
            return
    folder_section = False
    source = pathlib.Path(folder_def.get('base', '')) / folder_def.get('git', '') / 'lcarsstarter/config/config.toml'
    with open(source, 'r') as f_in:
        with open(config_file, 'w') as f_out:
            while line := f_in.readline():
                if line[:-1] == '[folder]':
                    folder_section = True 
                elif line.startswith('['):
                    folder_section = False
                #change Basefolder
                if folder_section and line[:-1].replace(' ', '').startswith('base='):
                    line = f'base = "{folder_def.get("base", "")}"\n'
                f_out.write(line)
 
async def main():
    parser = argparse.ArgumentParser(prog='lcars-update',
                                     description='Aktualiesiert lcars')
    parser.add_argument('-p', action='store_true', dest='pre_run')
    args = parser.parse_args()
    cfg = {}
    with (pathlib.Path('/'.join(__file__.split('/')[:-4])) / 'config/config.toml').open('rb') as f:
        cfg = tomllib.load(f)
    if args.pre_run:
        if cfg.get('git', {}).get('pull', True):
            await pull_git(cfg.get('folder', {}), cfg.get('git', {}))
            await update_config(cfg.get('folder', {}))
    else:
        pass
    print(args)
    pprint(sys.path)
    print('call update')

if __name__ == "__main__":
    asyncio.run(main())