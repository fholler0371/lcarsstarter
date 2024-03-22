import asyncio
import atexit
import toml
import sys
import os

from pprint import pprint


def load_config() -> dict:
    try:
        with open('../config/config.toml', 'r') as f:
            return toml.load(f)
    except:
        print('Konnte Konfiguration nicht lesen')
        sys.exit(-1)
        
async def create_base_folder(folder_def: dict) -> None:
    p = await asyncio.subprocess.create_subprocess_shell(f'sudo mkdir -p {folder_def.get("base", "")}', 
                                                         stderr=asyncio.subprocess.PIPE, 
                                                         stdout=asyncio.subprocess.PIPE)
    if (ret_code := await p.wait()) != 0:
        print('Ordner konnten nicht erstellt werden')
        print(ret_code)
        sys.exit(-1)
    p = await asyncio.subprocess.create_subprocess_shell(f'sudo chown {os.getuid()}:{os.getgid()} {folder_def.get("base", "")}', 
                                                         stderr=asyncio.subprocess.PIPE, 
                                                         stdout=asyncio.subprocess.PIPE)
    if (ret_code := await p.wait()) != 0:
        print('Besitzer für Ordner konnte nicht angepasst werden')
        print(ret_code)
        sys.exit(-1)

async def create_venv(folder_def:dict) -> None:
    p = await asyncio.subprocess.create_subprocess_shell(f'python3 -m venv {folder_def.get("base", "")}/{folder_def.get("venv", "")}', 
                                                         stderr=asyncio.subprocess.PIPE, 
                                                         stdout=asyncio.subprocess.PIPE)
    await p.wait()
    pprint(folder_def)

async def main() -> None:
    cfg = load_config()
    await create_base_folder(cfg.get('folder', {}))
    async with asyncio.TaskGroup() as tg:
        tg.create_task(create_venv(cfg.get('folder', {})))
    #pprint(cfg)
    
@atexit.register
def something_went_wrong() -> None:
    print('Fehler ist aufgetreten')
    
if __name__ == '__main__':
    asyncio.run(main())
    atexit.unregister(something_went_wrong)