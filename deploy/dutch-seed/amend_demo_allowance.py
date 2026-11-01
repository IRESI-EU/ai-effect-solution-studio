"""One-call demo amendment. Default preview never writes; --apply needs authorization."""
import argparse
import json
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'apps/api'))
from app.services.design_ai_demo_allowance import amend_demo_call

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ['ledger','expected-ledger-sha256','amendment-id','operator','reason','authorization-ref','task-checkpoint']:
        parser.add_argument('--'+name,required=True)
    parser.add_argument('--expected-limit',type=int,required=True)
    parser.add_argument('--new-limit',type=int,required=True)
    parser.add_argument('--runtime-container')
    parser.add_argument('--apply',action='store_true')
    args=vars(parser.parse_args());args['path']=args.pop('ledger');args['task_limit_file']=args.pop('task_checkpoint');args['dry_run']=not args.pop('apply')
    print(json.dumps(amend_demo_call(**args),indent=2))
