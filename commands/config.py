import asyncio
import argparse
import pathlib
import tomllib

from pprint import pprint


async def main() -> None:
    parser = argparse.ArgumentParser(prog='lcars-config',
                                     description='Editor für Konfiguration')
    parser.add_argument('-s', action='store_true', dest='show_source', help='Zeigt die default Konfiguration an.')
    parser.add_argument('-b', action='store_true', dest='show_backup', help='Zeigt die letzte Konfiguration an.')
    args = parser.parse_args()
    cfg = {}
    with (pathlib.Path('/'.join(__file__.split('/')[:-4])) / 'config/config.toml').open('rb') as f:
        cfg = tomllib.load(f)
    if args.show_backup:
        config_file: pathlib.Path = pathlib.Path(cfg.get('folder', {}).get('config', '')) / 'config.toml.bak'
    elif args.show_source:
        config_file: pathlib.Path = pathlib.Path(cfg.get('folder', {}).get('base', '')) / \
                                    pathlib.Path(cfg.get('folder', {}).get('git', '')) / 'lcarsstarter/config/config.toml'
    else:
        config_file: pathlib.Path = pathlib.Path(cfg.get('folder', {}).get('config', '')) / 'config.toml'
    if not config_file.exists():
        print(f"Datei {config_file} nicht gefunden")
        return
    p = await asyncio.subprocess.create_subprocess_shell(f'{cfg.get("helper_programms", {}).get("editor", "")} {config_file}')
    await p.wait()

if __name__ == "__main__":
    asyncio.run(main())