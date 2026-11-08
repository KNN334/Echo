"""Push exact local commit objects via GitHub official Git Data API when Git transport fails.

Preserves local hashes, parent history and file contents. Ref update is fast-forward only.
Credentials are read from the installed Git credential helper into memory, never logged.
"""
import argparse
import base64
import json
import re
import subprocess
import urllib.error
import urllib.request


def git(*args,raw=False):
    value=subprocess.check_output(['git',*args])
    return value if raw else value.decode('utf-8').strip()


def main():
    p=argparse.ArgumentParser()
    p.add_argument('--repository',required=True)
    a=p.parse_args()
    if not re.fullmatch(r'[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+',a.repository):
        raise ValueError('invalid repository')
    credential=subprocess.run(['git','-c','credential.interactive=never','credential','fill'],
                  input='protocol=https\nhost=github.com\n\n',text=True,capture_output=True,check=True)
    values=dict(x.split('=',1) for x in credential.stdout.splitlines() if '=' in x)
    token=values.get('password')
    if not token:raise RuntimeError('No GitHub credential available')
    def api(path,data=None,method=None):
        req=urllib.request.Request('https://api.github.com/repos/'+a.repository+path,
                data=json.dumps(data).encode() if data is not None else None,method=method,
                headers={'Authorization':'Bearer '+token,'Accept':'application/vnd.github+json',
                         'Content-Type':'application/json','X-GitHub-Api-Version':'2022-11-28','User-Agent':'Echo-project-publisher'})
        try:
            with urllib.request.urlopen(req,timeout=90) as r:return json.load(r)
        except urllib.error.HTTPError as e:
            raise RuntimeError(f'GitHub API status {e.code}: '+e.read().decode()[:800]) from None
    before=api('/git/ref/heads/main')['object']['sha']
    expected=git('rev-parse','origin/main')
    if before!=expected:raise RuntimeError('Remote main changed; fetch and merge before publishing')
    commits=git('rev-list','--reverse','origin/main..HEAD').splitlines()
    for commit in commits:
        parent_line=git('rev-list','--parents','-n','1',commit).split()
        parents=parent_line[1:]
        if not parents:raise RuntimeError('root commit publishing is not supported')
        parent=parents[0]
        paths=git('diff','--name-only','-z',parent,commit,raw=True).decode().rstrip('\x00').split('\x00')
        entries=[]
        for path in paths:
            if not path:continue
            ls=git('ls-tree',commit,'--',path)
            if not ls:
                entries.append({'path':path,'mode':'100644','type':'blob','sha':None});continue
            mode=ls.split()[0]
            content=git('show',commit+':'+path,raw=True)
            # A pointer whose payload is not on LFS storage must never be published by this fallback.
            if content.startswith(b'version https://git-lfs.github.com/spec/v1'):
                raise RuntimeError('Publish LFS payloads through git lfs before updating refs')
            try:
                text=content.decode('utf-8')
                if '\x00' in text:raise UnicodeDecodeError('utf-8',b'\x00',0,1,'binary')
                entries.append({'path':path,'mode':mode,'type':'blob','content':text})
            except UnicodeDecodeError:
                blob=api('/git/blobs',{'content':base64.b64encode(content).decode(),'encoding':'base64'})
                entries.append({'path':path,'mode':mode,'type':'blob','sha':blob['sha']})
        expected_tree=git('rev-parse',commit+'^{tree}')
        if entries:
            tree=api('/git/trees',{'base_tree':git('rev-parse',parent+'^{tree}'),'tree':entries})['sha']
            if tree!=expected_tree:raise RuntimeError('Remote tree hash does not match local tree')
        else:tree=expected_tree
        fields=git('show','-s','--format=%an%x00%ae%x00%aI%x00%cn%x00%ce%x00%cI',commit).split('\x00')
        raw_commit=git('cat-file','commit',commit,raw=True)
        message=raw_commit.split(b'\n\n',1)[1].decode()
        result=api('/git/commits',{'message':message,'tree':tree,'parents':parents,
                    'author':{'name':fields[0],'email':fields[1],'date':fields[2]},
                    'committer':{'name':fields[3],'email':fields[4],'date':fields[5]}})
        if result['sha']!=commit:raise RuntimeError('Remote commit hash mismatch: '+result['sha']+' versus '+commit)
        print('Uploaded commit '+commit,flush=True)
    head=git('rev-parse','HEAD')
    api('/git/refs/heads/main',{'sha':head,'force':False},method='PATCH')
    after=api('/git/ref/heads/main')['object']['sha']
    if after!=head:raise RuntimeError('Remote verification failed')
    print(json.dumps({'repository':a.repository,'remote_main':after,'verified':True}))


if __name__=='__main__':main()
