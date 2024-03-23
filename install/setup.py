import asyncio
import atexit
import toml
import sys
import os
import pathlib
import argparse


def load_config() -> dict:
    try:
        with open('../config/config.toml', 'r') as f:
            return toml.load(f)
    except:
        print('Konnte Konfiguration nicht lesen')
        sys.exit(-1)
        
async def create_base_folder(base_folder:str) -> None:
    p = await asyncio.subprocess.create_subprocess_shell(f'sudo mkdir -p {base_folder}', 
                                                         stderr=asyncio.subprocess.PIPE, 
                                                         stdout=asyncio.subprocess.PIPE)
    if (ret_code := await p.wait()) != 0:
        print('Ordner konnten nicht erstellt werden')
        print(ret_code)
        sys.exit(-1)
    p = await asyncio.subprocess.create_subprocess_shell(f'sudo chown {os.getuid()}:{os.getgid()} {base_folder}', 
                                                         stderr=asyncio.subprocess.PIPE, 
                                                         stdout=asyncio.subprocess.PIPE)
    if (ret_code := await p.wait()) != 0:
        print('Besitzer für Ordner konnte nicht angepasst werden')
        print(ret_code)
        sys.exit(-1)

async def create_venv(base_folder:str, folder_def:dict) -> None:
    p = await asyncio.subprocess.create_subprocess_shell(f'python3 -m venv {base_folder}/{folder_def.get("venv", "")}', 
                                                         stderr=asyncio.subprocess.PIPE, 
                                                         stdout=asyncio.subprocess.PIPE)
    await p.wait()
    
async def clone_git(base_folder:str, folder_def: dict, git_def: dict) -> None:
    git_folder = f'{base_folder}/{folder_def.get("git", "")}'
    p = await asyncio.subprocess.create_subprocess_shell(f'mkdir -p {git_folder}', 
                                                         stderr=asyncio.subprocess.PIPE, 
                                                         stdout=asyncio.subprocess.PIPE)
    if (ret_code := await p.wait()) != 0:
        print('Git-Ordner konnten nicht erstellt werden')
        print(ret_code)
        sys.exit(-1)
    project_folder = pathlib.Path(git_folder) / git_def.get('folder', '')
    if project_folder.exists():
        p = await asyncio.subprocess.create_subprocess_shell(f'cd {str(project_folder)} && git pull', 
                                                         stderr=asyncio.subprocess.PIPE, 
                                                         stdout=asyncio.subprocess.PIPE)
    else:
        print(f'cd {git_folder} && git clone {git_def.get("remote", "")}')
        p = await asyncio.subprocess.create_subprocess_shell(f'cd {git_folder} && git clone {git_def.get("remote", "")}', 
                                                         stderr=asyncio.subprocess.PIPE, 
                                                         stdout=asyncio.subprocess.PIPE)
    await p.wait()
    
async def copy_config(base_folder:str, folder_def: dict):
    folder_section = False
    config_folder = pathlib.Path(base_folder) / folder_def.get('config', '')
    p = await asyncio.subprocess.create_subprocess_shell(f'mkdir -p {str(config_folder)}', 
                                                         stderr=asyncio.subprocess.PIPE, 
                                                         stdout=asyncio.subprocess.PIPE)
    await p.wait()
    with open('../config/config.toml', 'r') as f_in:
        with open(config_folder / 'config.toml', 'w') as f_out:
            while line := f_in.readline():
                if line[:-1] == '[folder]':
                    folder_section = True 
                elif line.startswith('['):
                    folder_section = False
                #change Basefolder
                if folder_section and line[:-1].replace(' ', '').startswith('base='):
                    line = f'base = "{base_folder}"\n'
                f_out.write(line)
            
async def create_update_command(base_folder: str, folder_def: dict) -> None:
    run_folder = pathlib.Path(base_folder) / folder_def.get('run', '')
    p = await asyncio.subprocess.create_subprocess_shell(f'mkdir -p {str(run_folder)}', 
                                                         stderr=asyncio.subprocess.PIPE, 
                                                         stdout=asyncio.subprocess.PIPE)
    await p.wait()
    with (run_folder / 'lcars-update.sh').open('w') as f:
        f.write('#!/usr/bin/bash\n\n')
        f.write(f'pushd {base_folder} > /dev/null\n\n')
        f.write(f'{folder_def.get("venv", "")}/bin/python3 {folder_def.get("git", "")}/lcarsstarter/commands/update.py -p\n')
        f.write(f'{folder_def.get("venv", "")}/bin/python3 {folder_def.get("git", "")}/lcarsstarter/commands/update.py\n\n')
        f.write('popd > /dev/null\n')
    p = await asyncio.subprocess.create_subprocess_shell(f'chmod 755 {str(run_folder / "lcars-update.sh")}', 
                                                         stderr=asyncio.subprocess.PIPE, 
                                                         stdout=asyncio.subprocess.PIPE)
    await p.wait()
    bin_file = pathlib.Path(folder_def.get('cmd_folder', '')) / 'lcars-update'
    p = await asyncio.subprocess.create_subprocess_shell(f'rm {bin_file}', 
                                                         stderr=asyncio.subprocess.PIPE, 
                                                         stdout=asyncio.subprocess.PIPE)
    await p.wait()
    p = await asyncio.subprocess.create_subprocess_shell(f'sudo ln -s {str(run_folder)}/lcars-update.sh {bin_file}', 
                                                         stderr=asyncio.subprocess.PIPE, 
                                                         stdout=asyncio.subprocess.PIPE)
    await p.wait()
    
async def run_update() -> None:
    p = await asyncio.subprocess.create_subprocess_shell('lcars-update')
    await p.wait()

async def main() -> None:
    parser = argparse.ArgumentParser(prog='setup',
                                     description='Installieren vom lscarsstarter')
    parser.add_argument('-f', '--folder', help='Ordner in dem das Programm installiert wird', type=str, default=None)
    args = parser.parse_args()
    cfg = load_config()
    base_folder = args.folder if args.folder is not None else cfg.get('folder', {}).get("base", "")
    await create_base_folder(base_folder)
    async with asyncio.TaskGroup() as tg:
        tg.create_task(create_venv(base_folder, cfg.get('folder', {})))
        tg.create_task(clone_git(base_folder, cfg.get('folder', {}), cfg.get('git', {})))
    async with asyncio.TaskGroup() as tg:
        tg.create_task(copy_config(base_folder, cfg.get('folder', {})))
        tg.create_task(create_update_command(base_folder, cfg.get('folder', {})))
    await run_update()
    
@atexit.register
def something_went_wrong() -> None:
    print('Fehler ist aufgetreten')
    
if __name__ == '__main__':
    asyncio.run(main())
    atexit.unregister(something_went_wrong)
