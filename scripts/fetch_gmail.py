#!/usr/bin/env python3
"""Optional Gmail attachment fetcher.
Requires GMAIL_CLIENT_ID, GMAIL_CLIENT_SECRET, GMAIL_REFRESH_TOKEN.
Downloads new .xlsx attachments into incoming/. Search query is controlled by GMAIL_QUERY.
"""
import os,base64,requests
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]; IN=ROOT/'incoming';IN.mkdir(exist_ok=True)
CID=os.getenv('GMAIL_CLIENT_ID');SEC=os.getenv('GMAIL_CLIENT_SECRET');REF=os.getenv('GMAIL_REFRESH_TOKEN')
if not all([CID,SEC,REF]):
    print('Gmail secrets not configured; skipping email fetch.');raise SystemExit(0)
tok=requests.post('https://oauth2.googleapis.com/token',data={'client_id':CID,'client_secret':SEC,'refresh_token':REF,'grant_type':'refresh_token'},timeout=30).json()['access_token']
H={'Authorization':'Bearer '+tok};q=os.getenv('GMAIL_QUERY','has:attachment filename:xlsx newer_than:10d')
r=requests.get('https://gmail.googleapis.com/gmail/v1/users/me/messages',headers=H,params={'q':q,'maxResults':100},timeout=30).json()
for item in r.get('messages',[]):
    msg=requests.get(f"https://gmail.googleapis.com/gmail/v1/users/me/messages/{item['id']}",headers=H,params={'format':'full'},timeout=30).json()
    stack=list(msg.get('payload',{}).get('parts',[]) or [])
    while stack:
        part=stack.pop();stack.extend(part.get('parts',[]) or [])
        fn=part.get('filename','')
        aid=part.get('body',{}).get('attachmentId')
        if fn.lower().endswith('.xlsx') and aid:
            a=requests.get(f"https://gmail.googleapis.com/gmail/v1/users/me/messages/{item['id']}/attachments/{aid}",headers=H,timeout=30).json()
            b=base64.urlsafe_b64decode(a['data']+'===');dest=IN/fn
            if not dest.exists():dest.write_bytes(b);print('Downloaded',fn)
