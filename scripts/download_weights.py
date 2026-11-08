"""Range download the official EchoNet release, with size checks and provenance."""
import argparse
from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
from pathlib import Path
import shutil
import time
import urllib.request

URL = 'https://github.com/douyang/EchoNetDynamic/releases/download/v1.0.0/deeplabv3_resnet50_random.pt'
SIZE = 317401511  # official GitHub release asset 16393969


def main():
    p=argparse.ArgumentParser()
    p.add_argument('--output', default='checkpoints/echonet_official.pt')
    p.add_argument('--workers', type=int, default=16)
    a=p.parse_args()
    dest=Path(a.output)
    dest.parent.mkdir(parents=True,exist_ok=True)
    parts=dest.parent/'echonet_download_parts'
    parts.mkdir(exist_ok=True)
    # Resolve GitHub redirect once; all chunks then use the official release asset host.
    direct_url=URL
    for endpoint in ('https://api.github.com/repos/douyang/EchoNetDynamic/releases/assets/16393969?download=1',URL):
        try:
            req=urllib.request.Request(endpoint,headers={'Accept':'application/octet-stream','Range':'bytes=0-0','User-Agent':'Echo-research'})
            with urllib.request.urlopen(req,timeout=60) as r:
                resolved=r.geturl()
                if 'release-assets.githubusercontent.com' in resolved or 'objects.githubusercontent.com' in resolved:
                    direct_url=resolved
                    break
        except Exception:
            pass
    chunk=8*1024*1024
    def download(i):
        start,end=i*chunk,min(SIZE,(i+1)*chunk)-1
        target=parts/f'{i:04}.part'
        if target.exists() and target.stat().st_size==end-start+1:
            return target
        for attempt in range(5):
            try:
                req=urllib.request.Request(direct_url,headers={'Range':f'bytes={start}-{end}','User-Agent':'CAMUS-research-baseline'})
                with urllib.request.urlopen(req,timeout=90) as r:
                    if r.status != 206 or not r.headers.get('Content-Range','').startswith(f'bytes {start}-{end}/'):
                        raise RuntimeError('server did not honor byte range')
                    with target.open('wb') as f:
                        shutil.copyfileobj(r,f,1024*1024)
                if target.stat().st_size != end-start+1:
                    raise RuntimeError('partial chunk')
                print(f'weights chunk {i+1}/{(SIZE+chunk-1)//chunk}',flush=True)
                return target
            except Exception:
                if attempt==4:raise
                time.sleep(2**attempt)
    with ThreadPoolExecutor(max_workers=a.workers) as pool:
        paths=list(pool.map(download,range((SIZE+chunk-1)//chunk)))
    temp=dest.with_suffix('.assembling')
    h=hashlib.sha256()
    with temp.open('wb') as f:
        for path in paths:
            with path.open('rb') as src:
                for b in iter(lambda:src.read(1024*1024),b''):
                    f.write(b);h.update(b)
    if temp.stat().st_size != SIZE:raise RuntimeError('size mismatch')
    temp.replace(dest)
    (dest.parent/'echonet_official_source.json').write_text(json.dumps({'url':URL,'bytes':SIZE,'sha256':h.hexdigest(),'release_asset_id':16393969},indent=2))


if __name__=='__main__':main()
