import asyncio
import argparse
import sys
import pathlib
import tomllib
import shutil


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
                
async def create_update_command(folder_def: dict) -> None:
    run_folder = pathlib.Path(folder_def.get('base', '')) / folder_def.get('run', '')
    p = await asyncio.subprocess.create_subprocess_shell(f'mkdir -p {str(run_folder)}', 
                                                         stderr=asyncio.subprocess.PIPE, 
                                                         stdout=asyncio.subprocess.PIPE)
    await p.wait()
    with (run_folder / 'lcars-update.sh').open('w') as f:
        f.write('#!/usr/bin/bash\n\n')
        f.write(f'pushd {folder_def.get("base", "")} > /dev/null\n\n')
        f.write(f'{folder_def.get("venv", "")}/bin/python3 {folder_def.get("git", "")}/lcarsstarter/commands/update.py -p\n')
        f.write(f'{folder_def.get("venv", "")}/bin/python3 {folder_def.get("git", "")}/lcarsstarter/commands/update.py\n\n')
        f.write('popd > /dev/null\n')
    p = await asyncio.subprocess.create_subprocess_shell(f'chmod 755 {str(run_folder / "lcars-update.sh")}', 
                                                         stderr=asyncio.subprocess.PIPE, 
                                                         stdout=asyncio.subprocess.PIPE)
    await p.wait()
    bin_file = pathlib.Path(folder_def.get('cmd_folder', '')) / 'lcars-update'
    p = await asyncio.subprocess.create_subprocess_shell(f'sudo rm {bin_file}', 
                                                         stderr=asyncio.subprocess.PIPE, 
                                                         stdout=asyncio.subprocess.PIPE)
    await p.wait()
    p = await asyncio.subprocess.create_subprocess_shell(f'sudo ln -s {str(run_folder)}/lcars-update.sh {bin_file}', 
                                                         stderr=asyncio.subprocess.PIPE, 
                                                         stdout=asyncio.subprocess.PIPE)
    await p.wait()
    
async def create_commands(folder_def:dict, command_dev: dict) -> None:
    for cmd, activ in command_dev.items():
        bin_file = pathlib.Path(folder_def.get('cmd_folder', '')) / f'lcars-{cmd}'
        p = await asyncio.subprocess.create_subprocess_shell(f'sudo rm {bin_file}', 
                                                             stderr=asyncio.subprocess.PIPE, 
                                                             stdout=asyncio.subprocess.PIPE)
        await p.wait()
        if activ:
            sh_file = pathlib.Path(folder_def.get('base', '')) / folder_def.get('run', '') / f"{cmd}.sh"
            with sh_file.open('w') as f:
                f.write('#!/usr/bin/bash\n\n')
                f.write(f'pushd {folder_def.get("base", "")} > /dev/null\n\n')
                f.write(f'{folder_def.get("venv", "")}/bin/python3 {folder_def.get("git", "")}/lcarsstarter/commands/{cmd}.py "$@"\n')
                f.write('popd > /dev/null\n')
            p = await asyncio.subprocess.create_subprocess_shell(f'chmod 755 {sh_file}', 
                                                                stderr=asyncio.subprocess.PIPE, 
                                                                stdout=asyncio.subprocess.PIPE)
            await p.wait()
            p = await asyncio.subprocess.create_subprocess_shell(f'sudo ln -s {sh_file} {bin_file}', 
                                                         stderr=asyncio.subprocess.PIPE, 
                                                         stdout=asyncio.subprocess.PIPE)
            await p.wait()
            
async def apt(apt_def: list) -> None:
    p = await asyncio.subprocess.create_subprocess_shell(f'sudo apt update && sudo apt install {" ".join(apt_def)}', 
                                                                stderr=asyncio.subprocess.PIPE, 
                                                                stdout=asyncio.subprocess.PIPE)
    await p.wait()
 
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
        await apt(cfg.get('apt', {}).get('install', []))
        await create_update_command(cfg.get('folder', {}))
        await create_commands(cfg.get('folder', {}), cfg.get('commands', {}))

if __name__ == "__main__":
    asyncio.run(main())