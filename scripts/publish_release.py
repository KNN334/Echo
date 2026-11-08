"""Publish requested research artifacts to GitHub Release and verify server SHA256."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess
import urllib.error
import urllib.parse
import urllib.request


def sha(path):
    h=hashlib.sha256()
    with path.open('rb') as f:
        for b in iter(lambda:f.read(1024*1024),b''):h.update(b)
    return h.hexdigest()


def main():
    p=argparse.ArgumentParser()
    p.add_argument('--repository',default='KNN334/Echo')
    p.add_argument('--tag',required=True)
    p.add_argument('--title',required=True)
    p.add_argument('--notes',required=True)
    p.add_argument('--file',action='append',default=[])
    a=p.parse_args()
    if not re.fullmatch(r'[\w.-]+/[\w.-]+',a.repository):raise ValueError('invalid repository')
    c=subprocess.run(['git','-c','credential.interactive=never','credential','fill'],input='protocol=https\nhost=github.com\n\n',text=True,capture_output=True,check=True)
    values=dict(x.split('=',1) for x in c.stdout.splitlines() if '=' in x)
    token=values.get('password')
    if not token:raise RuntimeError('No GitHub credential available')
    headers={'Authorization':'Bearer '+token,'Accept':'application/vnd.github+json','User-Agent':'Echo-release-publisher'}
    def api(path,data=None):
        req=urllib.request.Request('https://api.github.com/repos/'+a.repository+path,
                data=json.dumps(data).encode() if data is not None else None,
                headers={**headers,'Content-Type':'application/json'})
        with urllib.request.urlopen(req,timeout=60) as r:return json.load(r)
    try:release=api('/releases/tags/'+a.tag)
    except urllib.error.HTTPError as e:
        if e.code!=404:raise
        commit=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip()
        release=api('/releases',{'tag_name':a.tag,'target_commitish':commit,'name':a.title,
                    'body':Path(a.notes).read_text(encoding='utf-8'),'draft':False,'prerelease':True})
    upload=release['upload_url'].split('{')[0]
    if urllib.parse.urlparse(upload).hostname!='uploads.github.com':raise RuntimeError('unexpected upload host')
    verified=[]
    for name in a.file:
        path=Path(name);digest=sha(path)
        found=[x for x in release['assets'] if x['name']==path.name]
        if found:
            asset=found[0]
            if asset.get('digest')!='sha256:'+digest:raise RuntimeError('existing release file has different content: '+path.name)
        else:
            with path.open('rb') as f:
                req=urllib.request.Request(upload+'?name='+urllib.parse.quote(path.name),data=f,method='POST',
                     headers={**headers,'Content-Type':'application/octet-stream','Content-Length':str(path.stat().st_size)})
                with urllib.request.urlopen(req,timeout=600) as r:asset=json.load(r)
        if asset['size']!=path.stat().st_size or (asset.get('digest') and asset['digest']!='sha256:'+digest):
            raise RuntimeError('uploaded file verification failed: '+path.name)
        verified.append({'file':path.name,'sha256':digest,'bytes':asset['size'],'url':asset['browser_download_url']})
        print('Verified uploaded artifact '+path.name,flush=True)
    print(json.dumps({'release':release['html_url'],'assets':verified},indent=2))


if __name__=='__main__':main()
