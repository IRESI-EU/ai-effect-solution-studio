"""Install active fixture I/O exports via normal publisher routes; never activate.

For an already-onboarded isolated workspace. Retains the earlier qualification
and active parameter-only exports and refuses duplicate archive installation.
"""
import argparse
import hashlib
import json
from pathlib import Path
import stat
from onboard import readonly_export,session,login,call


def install(directory):
    p=json.loads((directory/'profile.private.json').read_text())
    if p['kind']!='offline-assistant-danish-v1':raise RuntimeError('Wrong workspace')
    accounts=json.loads((directory/'credentials.private.json').read_text())
    records=json.loads((directory/'fixtures.private.json').read_text())
    client=session();login(client,p['api_url'],accounts['provider'])
    hashes={}
    for kind,record in zip(('generator','renderer-a','renderer-b'),records):
        contract=record.get('contract',record['io_contract'])
        value=call(client,'GET',p['api_url'],'/operation-contracts/'+contract['id']+'/runtime-capability')
        if kind=='generator':hashes[kind]=readonly_export(directory,value,'active-io')
        else:
            target=directory/'contracts'/(kind+'.json')
            raw=(json.dumps(value,indent=2)+'\n').encode()
            with target.open('xb') as stream:stream.write(raw)
            target.chmod(stat.S_IREAD);hashes[kind]=hashlib.sha256(raw).hexdigest()
    (directory/'io-exports.private.json').write_text(json.dumps(hashes,indent=2))
    print(json.dumps({'normal_owned_active_exports_installed_read_only':hashes,'contracts_activated':0}))


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--directory',type=Path,required=True)
    install(parser.parse_args().directory.resolve())
