"""模型任务高级命令行接口；数据准备由根目录 prepare.py 调度数据集适配器。"""
import argparse
import json


def main():
    """解析命令行参数并分派到训练或评估流程。"""
    p=argparse.ArgumentParser(description='CAMUS / EchoNet reproducible segmentation and function baseline')
    sub=p.add_subparsers(dest='command',required=True)
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
    if cmd=='train':
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
