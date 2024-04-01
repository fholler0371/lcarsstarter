import asyncio
import argparse
import sys
import pathlib
import tomllib
import shutil
import importlib.util
import os
import tempfile
import socket

APT_LOCK : asyncio.Lock = asyncio.Lock()
PIP_LOCK : asyncio.Lock = asyncio.Lock()


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
            
async def create_command_plugin(folder_def:dict, cmd: str, link: str) -> None:
    bin_file = pathlib.Path(folder_def.get('cmd_folder', '')) / f'lcars-{cmd}'
    p = await asyncio.subprocess.create_subprocess_shell(f'sudo rm {bin_file}', 
                                                             stderr=asyncio.subprocess.PIPE, 
                                                             stdout=asyncio.subprocess.PIPE)
    await p.wait()
    sh_file = pathlib.Path(folder_def.get('base', '')) / folder_def.get('run', '') / f"{cmd}.sh"
    with sh_file.open('w') as f:
        f.write('#!/usr/bin/bash\n\n')
        f.write(f'pushd {folder_def.get("base", "")} > /dev/null\n\n')
        f.write(f'{folder_def.get("venv", "")}/bin/python3 {link} "$@"\n')
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
    async with APT_LOCK:
        p = await asyncio.subprocess.create_subprocess_shell(f'sudo apt update && sudo apt install {" ".join(apt_def)}', 
                                                                    stderr=asyncio.subprocess.PIPE, 
                                                                    stdout=asyncio.subprocess.PIPE)
        await p.wait()
    
async def pip_install(folder_def: dict, moduls: list) -> None:
    pip_cmd = pathlib.Path(folder_def.get('base', '')) / pathlib.Path(folder_def.get('venv', '')) / 'bin/pip3'
    for modul in moduls:
        async with PIP_LOCK:
            p = await asyncio.subprocess.create_subprocess_shell(f'{pip_cmd} install {modul}', 
                                                                    stderr=asyncio.subprocess.PIPE, 
                                                                    stdout=asyncio.subprocess.PIPE)
            await p.wait()

async def create_folder(folder_def: dict, folders: list) -> None:
    for folder in folders:
        p = await asyncio.subprocess.create_subprocess_shell(f'mkdir -p {folder_def.get("base", "")}/{folder_def.get(folder, "")}', 
                                                                stderr=asyncio.subprocess.PIPE, 
                                                                stdout=asyncio.subprocess.PIPE)
        await p.wait()

async def set_language(lang: str) -> None:
    p = await asyncio.subprocess.create_subprocess_shell(f'sudo lcars-language -s {lang}', 
                                                                stderr=asyncio.subprocess.PIPE, 
                                                                stdout=asyncio.subprocess.PIPE)
    await p.wait()
    
async def install_systemd(systemd_def: dict) -> None:
    tmp = tempfile.NamedTemporaryFile(delete=False)
    try:
        tmp.write(systemd_def['content'].encode())
        tmp.close()
        if systemd_def.get('start', True):
            service = systemd_def["name"]
            p = await asyncio.subprocess.create_subprocess_shell(f'sudo systemctl disable {service} && sudo systemctl stop {service}', 
                                                                    stderr=asyncio.subprocess.PIPE, 
                                                                    stdout=asyncio.subprocess.PIPE)
            await p.wait()
        p = await asyncio.subprocess.create_subprocess_shell(f'sudo cp {tmp.name} /etc/systemd/system/{systemd_def["name"]}', 
                                                                stderr=asyncio.subprocess.PIPE, 
                                                                stdout=asyncio.subprocess.PIPE)
        await p.wait()
        p = await asyncio.subprocess.create_subprocess_shell(f'sudo chmod 444 /etc/systemd/system/{systemd_def["name"]}', 
                                                                stderr=asyncio.subprocess.PIPE, 
                                                                stdout=asyncio.subprocess.PIPE)
        await p.wait()
        if systemd_def.get('start', True):
            p = await asyncio.subprocess.create_subprocess_shell(f'sudo systemctl enable {service} && sudo systemctl start {service}', 
                                                                    stderr=asyncio.subprocess.PIPE, 
                                                                    stdout=asyncio.subprocess.PIPE)
            await p.wait()
        p = await asyncio.subprocess.create_subprocess_shell(f'sudo systemctl daemon-reload', 
                                                                    stderr=asyncio.subprocess.PIPE, 
                                                                    stdout=asyncio.subprocess.PIPE)
        await p.wait()
    finally:
        tmp.close()
        os.unlink(tmp.name)

async def install_plugin(cfg: dict, plugin_data: dict) -> None:
    folder = plugin_data.get('remote', '').split('/')[-1].split('.')[0]
    folder_def = cfg.get('folder', {})
    git_folder = pathlib.Path(folder_def.get('base', '')) / folder_def.get('git', '')
    if plugin_data.get('pull', True):
        if (git_folder / folder).exists():
            p = await asyncio.subprocess.create_subprocess_shell(f'cd {str(git_folder / folder)} && git pull', 
                                                                stderr=asyncio.subprocess.PIPE, 
                                                                stdout=asyncio.subprocess.PIPE)
        else:
            p = await asyncio.subprocess.create_subprocess_shell(f'cd {str(git_folder)} && git clone {plugin_data.get("remote", "")}', 
                                                                stderr=asyncio.subprocess.PIPE, 
                                                                stdout=asyncio.subprocess.PIPE)
        _, err = await p.communicate()
        if err.decode() != '':
            print(err.decode())
    if not (git_folder / folder).exists():
        return
    if plugin_data.get('install', True):
        spec=importlib.util.spec_from_file_location(folder, (git_folder / folder / 'install/install.py'))
        foo = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(foo)
        todo = await foo.install(cfg)
        if 'requirements' in todo:
            await pip_install(cfg.get('folder', ''), todo['requirements'])
        if 'systemd' in todo:
            for job in todo['systemd']:
                await install_systemd(job)
        if 'run' in todo:
            for cmd, link in todo['run'].items():
                await create_command_plugin(cfg.get('folder', ''), cmd, link)
    
async def install_plugins(cfg:dict) -> None:
    async with asyncio.TaskGroup() as tg:
        for idx, plugin_data in enumerate(cfg.get('plugins', [])):
            tg.create_task(install_plugin(cfg, plugin_data))
            
async def link_config(lcars_base: str, config_file: str)->None:
    if lcars_base is None:
        return
    p = await asyncio.subprocess.create_subprocess_shell(f'sudo mkdir -p {lcars_base}/config/hosts/{socket.getfqdn()}', 
                                                                stderr=asyncio.subprocess.PIPE, 
                                                                stdout=asyncio.subprocess.PIPE)
    await p.wait()
    p = await asyncio.subprocess.create_subprocess_shell(f'sudo chown {os.getuid()}:{os.getgid()} -R {lcars_base}', 
                                                                stderr=asyncio.subprocess.PIPE, 
                                                                stdout=asyncio.subprocess.PIPE)
    await p.wait()
    p = await asyncio.subprocess.create_subprocess_shell(f'ln -s {config_file} {lcars_base}/config/hosts/{socket.getfqdn()}/starter_config.toml', 
                                                                stderr=asyncio.subprocess.PIPE, 
                                                                stdout=asyncio.subprocess.PIPE)
    await p.wait()
 
async def main()->None:
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
        await apt(cfg.get('setup', {}).get('apt', []))
        await create_folder(cfg.get('folder', {}), cfg.get('setup', {}).get('folder', []))
        await create_update_command(cfg.get('folder', {}))
        await create_commands(cfg.get('folder', {}), cfg.get('commands', {}))
        await set_language(cfg.get('language', ''))
        await install_plugins(cfg)
        await link_config(cfg.get('setup', {}).get('lcars_base_folder'),
                          pathlib.Path('/'.join(__file__.split('/')[:-4])) / 'config/config.toml')

if __name__ == "__main__":
    asyncio.run(main())