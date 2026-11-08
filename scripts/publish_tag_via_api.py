"""Fallback: merge an already uploaded version tag using GitHub's official API.

Uses Git Credential Manager in memory; never writes or prints credentials.
Run only for a repository you have explicitly authorized to update.
"""
import argparse
import json
import subprocess
import urllib.request


def main():
    p=argparse.ArgumentParser()
    p.add_argument('--repository',required=True)
    p.add_argument('--tag',required=True)
    a=p.parse_args()
    if len(a.repository.split('/'))!=2 or any(x in a.repository for x in ('..','?','#','\\')):
        raise ValueError('invalid repository')
    cred=subprocess.run(['git','-c','credential.interactive=never','credential','fill'],
                        input='protocol=https\nhost=github.com\n\n',text=True,capture_output=True,check=True)
    values=dict(line.split('=',1) for line in cred.stdout.splitlines() if '=' in line)
    token=values.get('password')
    if not token:raise RuntimeError('No GitHub credential available')
    def api(path,data=None):
        req=urllib.request.Request('https://api.github.com/repos/'+a.repository+path,
             data=json.dumps(data).encode() if data is not None else None,
             headers={'Authorization':'Bearer '+token,'Accept':'application/vnd.github+json',
                      'X-GitHub-Api-Version':'2022-11-28','Content-Type':'application/json','User-Agent':'Echo-project-publisher'})
        with urllib.request.urlopen(req,timeout=60) as r:
            content=r.read()
            return json.loads(content) if content else {}
    before=api('/git/ref/heads/main')['object']['sha']
    result=api('/merges',{'base':'main','head':a.tag,'commit_message':f'Merge {a.tag}: CAMUS preprocessing and EchoNet baseline'})
    after=api('/git/ref/heads/main')['object']['sha']
    print(json.dumps({'repository':a.repository,'before':before,'after':after,'merge_sha':result.get('sha')}))


if __name__=='__main__':main()
