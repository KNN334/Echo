"""Download an authorized repository release through official API/CDN, with resumable ranges."""
import argparse
import hashlib
import json
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import re
import shutil
import subprocess
import time
import urllib.error
import urllib.parse
import urllib.request
import zipfile


def digest(path):
    h=hashlib.sha256()
    with path.open('rb') as f:
        for b in iter(lambda:f.read(1024*1024),b''):h.update(b)
    return h.hexdigest()


def main():
    p=argparse.ArgumentParser()
    p.add_argument('--repository',default='KNN334/Echo')
    p.add_argument('--tag',required=True)
    p.add_argument('--asset',required=True)
    p.add_argument('--output',required=True)
    p.add_argument('--sha256')
    p.add_argument('--workers',type=int,default=8)
    p.add_argument('--extract-to')
    a=p.parse_args()
    if not re.fullmatch(r'[\w.-]+/[\w.-]+',a.repository):raise ValueError('invalid repository')
    c=subprocess.run(['git','-c','credential.interactive=never','credential','fill'],
            input='protocol=https\nhost=github.com\n\n',text=True,capture_output=True,check=True)
    values=dict(x.split('=',1) for x in c.stdout.splitlines() if '=' in x)
    token=values.get('password')
    if not token:raise RuntimeError('No GitHub credential available')
    base='https://api.github.com/repos/'+a.repository
    headers={'Authorization':'Bearer '+token,'Accept':'application/vnd.github+json','User-Agent':'Echo-data-downloader'}
    with urllib.request.urlopen(urllib.request.Request(base+'/releases/tags/'+a.tag,headers=headers),timeout=60) as r:
        release=json.load(r)
    candidates=[x for x in release['assets'] if x['name']==a.asset]
    if len(candidates)!=1:raise RuntimeError('release asset not found')
    asset=candidates[0];size=asset['size']
    expected=a.sha256 or (asset.get('digest','') or '').removeprefix('sha256:') or None
    dest=Path(a.output);dest.parent.mkdir(parents=True,exist_ok=True)
    if not (dest.exists() and dest.stat().st_size==size and (not expected or digest(dest)==expected)):
        class NoRedirect(urllib.request.HTTPRedirectHandler):
            def redirect_request(self,*args,**kwargs):return None
        req=urllib.request.Request(base+f"/releases/assets/{asset['id']}?download={int(time.time())}",
             headers={**headers,'Accept':'application/octet-stream'})
        try:
            r=urllib.request.build_opener(NoRedirect).open(req,timeout=60)
            r.close();raise RuntimeError('asset API did not redirect to official download host')
        except urllib.error.HTTPError as e:
            if e.code not in (301,302,303,307,308):raise
            url=e.headers['Location']
        parsed=urllib.parse.urlparse(url)
        if parsed.scheme!='https' or not parsed.hostname.endswith('.githubusercontent.com'):
            raise RuntimeError('unexpected download host')
        parts=dest.parent/(dest.name+'.parts');parts.mkdir(exist_ok=True)
        chunk=8*1024*1024
        def fetch(i):
            start,end=i*chunk,min(size,(i+1)*chunk)-1
            target=parts/f'{i:05}.part'
            if target.exists() and target.stat().st_size==end-start+1:return target
            for attempt in range(5):
                try:
                    request=urllib.request.Request(url,headers={'Range':f'bytes={start}-{end}'})
                    with urllib.request.urlopen(request,timeout=120) as r:
                        if r.status!=206 or not r.headers.get('Content-Range','').startswith(f'bytes {start}-{end}/'):
                            raise RuntimeError('download range not honored')
                        with target.open('wb') as f:shutil.copyfileobj(r,f,1024*1024)
                    if target.stat().st_size!=end-start+1:raise RuntimeError('incomplete range')
                    print(f"{a.asset}: chunk {i+1}/{(size+chunk-1)//chunk}",flush=True)
                    return target
                except Exception:
                    if attempt==4:raise
                    time.sleep(2**attempt)
        with ThreadPoolExecutor(max_workers=a.workers) as pool:
            paths=list(pool.map(fetch,range((size+chunk-1)//chunk)))
        temporary=dest.with_suffix('.assembling')
        with temporary.open('wb') as f:
            for path in paths:
                with path.open('rb') as src:shutil.copyfileobj(src,f,1024*1024)
        if temporary.stat().st_size!=size or (expected and digest(temporary)!=expected):
            raise RuntimeError('release archive size/SHA256 verification failed')
        temporary.replace(dest)
    provenance={'repository':a.repository,'tag':a.tag,'asset_id':asset['id'],
                'bytes':size,'sha256':digest(dest),'declared_digest':asset.get('digest')}
    dest.with_suffix(dest.suffix+'.source.json').write_text(json.dumps(provenance,indent=2))
    if a.extract_to:
        root=Path(a.extract_to).resolve()
        with zipfile.ZipFile(dest) as z:
            for info in z.infolist():
                target=(root/info.filename).resolve()
                if not target.is_relative_to(root):raise RuntimeError('unsafe ZIP path')
                if info.is_dir():continue
                target.parent.mkdir(parents=True,exist_ok=True)
                with z.open(info) as src,target.open('wb') as f:shutil.copyfileobj(src,f)
    print(json.dumps(provenance,indent=2))


if __name__=='__main__':main()
