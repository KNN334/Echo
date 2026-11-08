import argparse
import json
from .common import read_json


def main():
    p=argparse.ArgumentParser(description='CAMUS / EchoNet reproducible segmentation and function baseline')
    sub=p.add_subparsers(dest='command',required=True)
    prep=sub.add_parser('prepare')
    prep.add_argument('--root',default='data/raw/CAMUS')
    prep.add_argument('--output',default='data/processed/camus')
    prep.add_argument('--config',default='configs/camus.json')
    prep.add_argument('--splits',default='data/manifests/splits.json')
    prep.add_argument('--limit',type=int)
    train=sub.add_parser('train')
    train.add_argument('--processed',default='data/processed/camus')
    train.add_argument('--output',default='checkpoints/camus_baseline')
    train.add_argument('--epochs',type=int,default=30)
    train.add_argument('--batch',type=int,default=8)
    train.add_argument('--lr',type=float,default=1e-4)
    train.add_argument('--weights')
    train.add_argument('--device',default='cuda')
    train.add_argument('--seed',type=int,default=2026)
    train.add_argument('--max-cases',type=int)
    ev=sub.add_parser('evaluate')
    ev.add_argument('--processed',default='data/processed/camus')
    ev.add_argument('--weights',required=True)
    ev.add_argument('--output',default='runs/baseline')
    ev.add_argument('--split',choices=['train','val','test'],default='test')
    ev.add_argument('--normalization')
    ev.add_argument('--device',default='cuda')
    ev.add_argument('--limit',type=int)
    ev.add_argument('--temporal',action='store_true')
    ev.add_argument('--gate',action='store_true')
    ev.add_argument('--references')
    ev.add_argument('--manual-landmarks')
    args=vars(p.parse_args())
    cmd=args.pop('command')
    if cmd=='prepare':
        from .dataset import prepare_camus
        config=read_json(args.pop('config'))
        args['split_path']=args.pop('splits')
        result=prepare_camus(config=config,**args)
    elif cmd=='train':
        from .model import train
        result=train(**args)
    else:
        from .pipeline import evaluate
        result=evaluate(**args)
    print(json.dumps(result,ensure_ascii=False,indent=2,allow_nan=False))
    if isinstance(result,dict) and (result.get('failures') or result.get('cases_failed',0)):
        raise SystemExit(2)


if __name__=='__main__':
    main()
