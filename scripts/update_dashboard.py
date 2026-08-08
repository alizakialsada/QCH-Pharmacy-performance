#!/usr/bin/env python3
import os, re, json, argparse
from pathlib import Path
from collections import defaultdict
from datetime import datetime
import pandas as pd
import requests

ROOT=Path(__file__).resolve().parents[1]
DATA_PATH=ROOT/'data/platform-data.json'
JS_PATH=ROOT/'data/platform-data.js'
CONFIG=json.loads((ROOT/'config.json').read_text(encoding='utf-8'))

def norm(s):
    return re.sub(r'\s+',' ',str(s or '').strip()).upper()

def month_key(v):
    x=pd.to_datetime(v,errors='coerce',dayfirst=True)
    return None if pd.isna(x) else x.strftime('%Y-%m')

def safe_num(v):
    try:return float(v)
    except:return 0.0

def duration_minutes(v):
    if pd.isna(v): return None
    if isinstance(v,pd.Timedelta): return v.total_seconds()/60
    if hasattr(v,'hour') and hasattr(v,'minute'):
        return v.hour*60+v.minute+getattr(v,'second',0)/60
    if isinstance(v,(int,float)):
        # Excel duration is usually fraction of a day. Values > 1 are assumed minutes.
        return float(v)*1440 if 0 <= float(v) < 1 else float(v)
    s=str(v).strip()
    m=re.match(r'^(?:(\d+)\s+days?\s+)?(\d{1,2}):(\d{2})(?::(\d{2}(?:\.\d+)?))?$',s)
    if m:
        d,h,mi,se=m.groups();return (int(d or 0)*24+int(h))*60+int(mi)+float(se or 0)/60
    try:return float(s)
    except:return None

def read_xlsx(path):
    return pd.read_excel(path,engine='openpyxl')

def staff_rosters(data):
    out={'QCH':set(),'PMFH':set()}
    for h in out:
        for m in data['months']:
            for e in data['dispensing'][h][m].get('employees',[]):out[h].add(norm(e.get('name') or e.get('key')))
    return out

def process_dispensing(df,hospital,data):
    cols={norm(c):c for c in df.columns}
    need=['ORDER DATE','PATIENT ID','DISPENSE','ORDER ID','DISP BY','STORE DISP']
    for n in need:
        if n not in cols: raise ValueError(f'Dispensing missing column: {n}')
    d=df.copy();d['_month']=d[cols['ORDER DATE']].map(month_key);d=d[d['_month'].notna()]
    d['_emp']=d[cols['DISP BY']].map(norm);d['_store']=d[cols['STORE DISP']].astype(str).str.strip()
    d['_order']=d[cols['ORDER ID']].astype(str);d['_patient']=d[cols['PATIENT ID']].astype(str)
    d['_disp']=d[cols['DISPENSE']].astype(str).str.upper().str.contains('DISPENSED') & ~d[cols['DISPENSE']].astype(str).str.upper().str.contains('NOT')
    for mon,g in d.groupby('_month'):
        employees=[]
        # unique order status by employee
        for emp,eg in g[g['_emp']!=''].groupby('_emp'):
            order_rows=eg.drop_duplicates('_order')
            stores=[]
            for st,sg in eg.groupby('_store'):
                stores.append({'store':str(st),'orders':int(sg['_order'].nunique()),'patients':int(sg['_patient'].nunique())})
            orders=int(order_rows['_order'].nunique());disp=int(order_rows[order_rows['_disp']]['_order'].nunique())
            name=str(eg[cols['DISP BY']].dropna().astype(str).iloc[0]).strip()
            stores.sort(key=lambda x:x['orders'],reverse=True)
            for x in stores:x['share']=round(100*x['orders']/orders,1) if orders else 0
            employees.append({'key':emp,'name':name,'patients':int(eg['_patient'].nunique()),'orders':orders,'dispensed':disp,'not_dispensed':max(0,orders-disp),'completion':round(100*disp/orders,1) if orders else 0,'stores':stores,'store_count':len(stores)})
        total_orders=int(g['_order'].nunique());disp_orders=int(g.drop_duplicates('_order').query('_disp == True')['_order'].nunique())
        mx=max([e['orders'] for e in employees],default=1)
        for e in employees:
            e['workload_index']=round(100*e['orders']/mx,1);e['performance_index']=round(.6*e['completion']+.4*e['workload_index'],1)
        employees.sort(key=lambda e:(-e['performance_index'],-e['orders']))
        data['dispensing'][hospital][mon]={'summary':{'patients':int(g['_patient'].nunique()),'orders':total_orders,'dispensed':disp_orders,'not_dispensed':max(0,total_orders-disp_orders),'completion':round(100*disp_orders/total_orders,1) if total_orders else 0},'employees':employees}
        if mon not in data['months']:data['months'].append(mon)

def process_stat(df,hospital,data):
    cols={norm(c):c for c in df.columns}
    for n in ['ORDER_DATETIME','DURATION OF DISPENSING','STORE_NAME','DISPENSED_BY']:
        if n not in cols: raise ValueError(f'STAT missing column: {n}')
    d=df.copy();d['_month']=d[cols['ORDER_DATETIME']].map(month_key);d=d[d['_month'].notna()]
    d['_emp']=d[cols['DISPENSED_BY']].map(norm);d['_store']=d[cols['STORE_NAME']].astype(str).str.strip();d['_min']=d[cols['DURATION OF DISPENSING']].map(duration_minutes)
    d=d[d['_min'].notna() & (d['_min']>=0)]
    for mon,g in d.groupby('_month'):
        employees=[]
        for emp,eg in g[g['_emp']!=''].groupby('_emp'):
            stores=[]
            for st,sg in eg.groupby('_store'):
                stores.append({'store':str(st),'orders':int(len(sg)),'share':0})
            orders=len(eg)
            for x in stores:x['share']=round(100*x['orders']/orders,1) if orders else 0
            name=str(eg[cols['DISPENSED_BY']].dropna().astype(str).iloc[0]).strip()
            employees.append({'key':emp,'name':name,'orders':int(orders),'within':int((eg['_min']<=30).sum()),'over':int((eg['_min']>30).sum()),'compliance':round(100*(eg['_min']<=30).mean(),1),'avg':round(float(eg['_min'].mean()),1),'median':round(float(eg['_min'].median()),1),'stores':sorted(stores,key=lambda x:x['orders'],reverse=True)})
        data['stat'][hospital][mon]={'summary':{'orders':int(len(g)),'within':int((g['_min']<=30).sum()),'over':int((g['_min']>30).sum()),'compliance':round(100*(g['_min']<=30).mean(),1)},'employees':employees}
        if mon not in data['months']:data['months'].append(mon)

def classify_hold_emp(name,rosters):
    n=norm(name);q=n in rosters['QCH'];p=n in rosters['PMFH']
    if q and not p:return 'QCH'
    if p and not q:return 'PMFH'
    # if an employee exists in both source hospitals, leave as PMFH only if explicitly prefixed; otherwise unresolved
    return None

def process_hold(df,data):
    cols={norm(c):c for c in df.columns}
    for n in ['HOLD DATE','HOLD BY','HOLDREASON']:
        if n not in cols: raise ValueError(f'Hold missing column: {n}')
    rosters=staff_rosters(data);d=df.copy();d['_month']=d[cols['HOLD DATE']].map(month_key);d['_emp']=d[cols['HOLD BY']].map(norm);d['_hospital']=d[cols['HOLD BY']].map(lambda x: classify_hold_emp(x,rosters));d=d[d['_month'].notna() & d['_hospital'].notna()]
    for (h,mon),g in d.groupby(['_hospital','_month']):
        em=[]
        for emp,eg in g.groupby('_emp'):
            name=str(eg[cols['HOLD BY']].dropna().astype(str).iloc[0]).strip();em.append({'key':emp,'name':name,'holds':int(len(eg))})
        reasons=[{'reason':str(k),'count':int(v)} for k,v in g[cols['HOLDREASON']].fillna('Unspecified').value_counts().items()]
        data['hold'][h][mon]={'holds':int(len(g)),'employees':sorted(em,key=lambda x:x['holds'],reverse=True),'reasons':reasons}
        if mon not in data['months']:data['months'].append(mon)

def classify_wasfaty(row,cols):
    phy=norm(row[cols['PHYSICIAN NAME']]);typ=norm(row.get(cols.get('MEDICATION TYPE',''),''))
    if phy in set(CONFIG['qch_physicians']): return 'QCH'
    if phy==CONFIG['mazen_physician']:
        return 'QCH' if 'CHRON' in typ else 'PMFH'
    return 'PMFH'

def inventory_lookup():
    f=ROOT/CONFIG['inventory']['local_file'];url=os.getenv(CONFIG['inventory']['remote_url_env'],'').strip()
    if url:
        try:
            r=requests.get(url,timeout=30);r.raise_for_status();f.write_bytes(r.content)
        except Exception as e: print('Inventory download skipped:',e)
    if not f.exists() or f.stat().st_size<20:return {},{}
    inv=pd.read_csv(f);mapping={}
    mf=ROOT/CONFIG['inventory']['medication_map']
    if mf.exists():
        mm=pd.read_csv(mf)
        for _,r in mm.iterrows():mapping[norm(r.get('wasfaty_medication'))]=str(r.get('nupco_code','')).strip()
    bycode={str(r.get('nupco_code','')).strip():r for _,r in inv.iterrows()}
    return mapping,bycode

def process_wasfaty(df,data):
    cols={norm(c):c for c in df.columns}
    for n in ['PRESCRIPTION DATE AND TIME','PATIENTNUMBER','ENCOUNTERNUMBER','PHYSICIAN NAME','MEDICATION NAME']:
        if n not in cols: raise ValueError(f'Wasfaty missing column: {n}')
    d=df.copy();d['_month']=d[cols['PRESCRIPTION DATE AND TIME']].map(month_key);d=d[d['_month'].notna()];d['_hospital']=d.apply(lambda r: classify_wasfaty(r,cols),axis=1)
    mp,inv=inventory_lookup()
    for (h,mon),g in d.groupby(['_hospital','_month']):
        physicians=[{'name':str(k),'count':int(v)} for k,v in g[cols['PHYSICIAN NAME']].fillna('Unknown').value_counts().head(30).items()]
        medications=[{'name':str(k),'count':int(v)} for k,v in g[cols['MEDICATION NAME']].fillna('Unknown').value_counts().head(50).items()]
        despite=due=matched=unmatched=0
        for med in g[cols['MEDICATION NAME']].astype(str):
            code=mp.get(norm(med))
            if not code or code not in inv:unmatched+=1;continue
            matched+=1;r=inv[code];avail=safe_num(r.get('lc_qty'))+safe_num(r.get('mosool_qty'))>0
            if avail:despite+=1
            else:due+=1
        data['wasfaty'][h][mon]={'items':int(len(g)),'prescriptions':int(g[cols['ENCOUNTERNUMBER']].astype(str).nunique()),'patients':int(g[cols['PATIENTNUMBER']].astype(str).nunique()),'mom':0,'per1000':0,'physicians':physicians,'medications':medications,'despite_availability':despite if matched else None,'due_to_unavailability':due if matched else None,'inventory_matched_items':matched if matched else None,'inventory_unmatched_items':unmatched if matched else None}
        if mon not in data['months']:data['months'].append(mon)

def detect(path):
    n=path.name.lower()
    if 'wasfaty' in n:return ('wasfaty',None)
    if 'hold' in n:return ('hold',None)
    if 'stat' in n:return ('stat','QCH' if 'qch' in n or 'qatif' in n else 'PMFH' if 'pmfh' in n or 'prince' in n else None)
    if 'qch' in n or 'qatif' in n:return ('dispensing','QCH')
    if 'pmfh' in n or 'prince' in n:return ('dispensing','PMFH')
    return (None,None)

def main():
    data=json.loads(DATA_PATH.read_text(encoding='utf-8'))
    files=sorted((ROOT/'incoming').glob('*.xlsx'))
    for p in files:
        kind,h=detect(p);print('Processing',p.name,'=>',kind,h)
        if not kind:continue
        df=read_xlsx(p)
        if kind=='dispensing' and h:process_dispensing(df,h,data)
        elif kind=='stat' and h:process_stat(df,h,data)
        elif kind=='hold':process_hold(df,data)
        elif kind=='wasfaty':process_wasfaty(df,data)
    data['months']=sorted(set(data['months']))
    # ensure empty structures for all months
    for h in ['QCH','PMFH']:
        for mon in data['months']:
            data['dispensing'][h].setdefault(mon,{'summary':{'patients':0,'orders':0,'dispensed':0,'not_dispensed':0,'completion':0},'employees':[]})
            data['stat'][h].setdefault(mon,{'summary':{'orders':0,'within':0,'over':0,'compliance':0},'employees':[]})
            data['hold'][h].setdefault(mon,{'holds':0,'employees':[],'reasons':[]})
            data['wasfaty'][h].setdefault(mon,{'items':0,'prescriptions':0,'patients':0,'mom':0,'per1000':0,'physicians':[],'medications':[],'despite_availability':None,'due_to_unavailability':None,'inventory_matched_items':None,'inventory_unmatched_items':None})
    data.setdefault('meta',{})['last_refresh']=datetime.now().astimezone().isoformat(timespec='minutes')
    DATA_PATH.write_text(json.dumps(data,ensure_ascii=False,separators=(',',':')),encoding='utf-8')
    JS_PATH.write_text('window.PLATFORM_DATA='+json.dumps(data,ensure_ascii=False,separators=(',',':'))+';\n',encoding='utf-8')
    print('Updated',JS_PATH)
if __name__=='__main__':main()
