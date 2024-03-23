import asyncio
import os
import argparse
from typing import List

import time


LANGUAGES_FILE = '/etc/locale.gen'

def name_converter(name:str) -> str:
    if name.endswith('.utf8'):
        return f'{name[:-4]}UTF-8'
    return name
    
async def get_current_language() -> str:
    return os.getenv('LANG')

async def update_language(language:str) -> None:
    p = await asyncio.create_subprocess_shell(f'localectl set-locale LANG={language}', stderr=asyncio.subprocess.PIPE,
                                                            stdout=asyncio.subprocess.PIPE)
    await p.wait()

async def generate_languages() -> None:
    p = await asyncio.create_subprocess_shell('locale-gen', stderr=asyncio.subprocess.PIPE,
                                                            stdout=asyncio.subprocess.PIPE)
    await p.wait()

async def install_language(language:str) -> bool:
    if os.getuid() != 0:
        print('\nmuss als Root-Nutzer ausgeführt werden.')
        return False
    with open(LANGUAGES_FILE) as f:
        entries = f.read().split('\n')
    if len(entries) == 0:
        print('\nkeine Liste gefunden')
        return False
    language_up = language.upper()
    for idx, lang in enumerate(entries):
        if lang.upper().startswith(f'# {language_up}'):
            entries[idx] = lang[2:]
            break
    else:
        return False
    with open(LANGUAGES_FILE, 'w') as f:
        f.write('\n'.join(entries))       
    return True

async def remove_language(language:str) -> bool:
    if os.getuid() != 0:
        print('\nmuss als Root-Nutzer ausgeführt werden.')
        return False
    with open(LANGUAGES_FILE) as f:
        entries = f.read().split('\n')
    if len(entries) == 0:
        print('\nkeine Liste gefunden')
        return False
    language_up = language.upper()
    for idx, lang in enumerate(entries):
        if lang.upper().startswith(language_up):
            entries[idx] = f'# {lang[2:]}'
            break
    else:
        return False
    with open(LANGUAGES_FILE, 'w') as f:
        f.write('\n'.join(entries))       
    return True

async def get_languages() -> bool|List[str]:
    p = await asyncio.create_subprocess_shell('locale -a | grep _', stderr=asyncio.subprocess.PIPE,
                                                                    stdout=asyncio.subprocess.PIPE)
    stdout, stderr = await p.communicate()
    stderr = stderr.decode()
    if stderr != '':
        print('\nEs ist ein Fehler aufgetreten.')
        print(stderr)
        return False
    else:
        return stdout.decode().split('\n')[:-1]

async def show_languages() -> None:
    print('Diese Sprachen sind installiert:')
    if result := await get_languages():
        print('\n'.join(result))
        
async def set_languages(language: str) -> None:
    if not(languages := await get_languages()):
        return False
    language_installed = False
    if language not in languages:
        language_installed = await install_language(name_converter(language))
    if language_installed:
        await generate_languages()

async def remove_languages(language: str) -> None:
    if not(languages := await get_languages()):
        return False
    language_removed = False
    if language in languages:
        language_removed = await remove_language(name_converter(language))
    if language_removed:
        await generate_languages()

async def main() -> None:
    parser = argparse.ArgumentParser(
        prog = 'lcars-language',
        description = 'Dieser Progamm setzt die Systemsprache auf einem RaspberryPi. Ohne Parameter werden die installierten Sprachen aufgelistet.')
    parser.add_argument('--set', '-s' , help='setzt die Systemsprache', dest='language', default=None)
    parser.add_argument('--remove', '-r' , help='entfernt installierte Sprache', dest='language_to_remove', default=None)
    args = parser.parse_args()
    if args.language_to_remove is not None:
        await remove_languages(args.language_to_remove)
    if args.language is not None:
        await set_languages(args.language)
        await update_language(name_converter(args.language))
        if name_converter(args.language) != await get_current_language():
            print('\033[91mBitte, neu anmelden oder Reboot!\033[0m')
    if args.language is None and args.language_to_remove is None:
        await show_languages()
    
if __name__ == "__main__":
    asyncio.run(main())
