"""Hourly early-career US tech job scraper. ATS + first-party career portals."""
import os,re,time,random,json
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urljoin, urlparse, parse_qsl, urlencode, urlunparse
from concurrent.futures import ThreadPoolExecutor, as_completed
from threading import Lock
import pandas as pd
import requests
from bs4 import BeautifulSoup

HEADERS={'User-Agent':'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/131 Safari/537.36','Accept-Language':'en-US,en;q=0.9'}
ROLE_PATTERNS=[
 ('DATA_ENGINEERING',[r'\bdata engineer',r'analytics engineer',r'data platform engineer',r'data infrastructure',r'data reliability',r'data warehouse engineer',r'\betl\b',r'\belt\b']),
 ('CLOUD_PLATFORM_DEVOPS',[r'cloud engineer',r'cloud infrastructure',r'cloud platform',r'platform engineer',r'infrastructure engineer',r'devops',r'devsecops',r'site reliability',r'\bsre\b',r'production engineer',r'cloud operations',r'cloud reliability',r'kubernetes platform']),
 ('ANALYTICS_BI',[r'\bdata analyst',r'business intelligence',r'\bbi analyst',r'\bbi engineer',r'analytics analyst',r'product analyst',r'growth analyst',r'reporting analyst',r'\bbusiness analyst']),
 ('DATA_SCIENCE_AI',[r'\bdata scientist',r'machine learning engineer',r'\bml engineer',r'\bai engineer',r'\bmlops',r'\bllm',r'applied scientist']),
 ('SOFTWARE_ENGINEERING',[r'software engineer',r'software developer',r'backend engineer',r'backend developer',r'\bsde\b',r'\bswe\b']),
]
HARD_TITLE_EXCLUDE=[r'\bsenior\b',r'\bsr\.?\b',r'\bstaff\b',r'\bprincipal\b',r'\bdirector\b',r'\bmanager\b',r'\blead\b',r'\bhead of\b',r'\bvp\b',r'vice president',r'\bchief\b',r'distinguished',r'\bfellow\b',r'engineer iii',r'engineer iv',r'level 3',r'level 4',r'\bl3\b',r'\bl4\b']
INTERN_EXCLUDE=[r'\bintern\b',r'\binternship\b',r'\bco[- ]?op\b']
DOMAIN_EXCLUDE=[r'power systems engineer',r'fluid systems engineer',r'avionics systems engineer',r'hvac systems engineer',r'wireless systems engineer',r'quality systems engineer',r'hardware systems engineer',r'cyber systems engineer',r'it systems engineer',r'facilities infrastructure engineer',r'physical security systems engineer',r'finance systems engineer']
CLEARANCE_EXCLUDE=[r'ts/sci',r'top secret',r'secret clearance',r'clearance required',r'active clearance',r'polygraph']
EMPLOYMENT_EXCLUDE=[r'\bcontractor\b',r'\btemporary\b',r'\bseasonal\b']
YOE_REJECT=[
 r'(?:minimum|required|requires?|qualifications?|must have|you have|experience).{0,120}\b(?:4|5|6|7|8|9|10|11|12|13|14|15)\+?\s*(?:years?|yrs?)',
 r'\b(?:4|5|6|7|8|9|10|11|12|13|14|15)\+?\s*(?:years?|yrs?)\s+(?:of\s+)?(?:professional|industry|relevant|software|engineering|data|cloud|development)',
]
DISCOVERY_SOURCES=[
 ('SpeedyApply AI New Grad','https://raw.githubusercontent.com/speedyapply/2027-AI-College-Jobs/main/NEW_GRAD_USA.md'),
 ('SpeedyApply SWE New Grad','https://raw.githubusercontent.com/speedyapply/2027-SWE-College-Jobs/main/NEW_GRAD_USA.md'),
]

NON_US=[r'\bcanada\b',r'\bcanadian\b',r'\bunited kingdom\b',r'\buk\b',r'\bnetherlands\b',r'\bindia\b',r'\bgermany\b',r'\bfrance\b',r'\bireland\b',r'\bspain\b',r'\bpoland\b',r'\baustralia\b',r'\bsingapore\b']
US_STATE_ABBRS=set('AL AK AZ AR CA CO CT DE FL GA HI ID IL IN IA KS KY LA ME MD MA MI MN MS MO MT NE NV NH NJ NM NY NC ND OH OK OR PA RI SC SD TN TX UT VT VA WA WV WI WY DC'.split())
MASS_KEYS=['new grad','new graduate','university graduate','college graduate','early career','recent graduate','graduate program','development program','technology development program','rotational program','campus hire','2027 graduate','2026 graduate','associate engineer','associate data']
errors=[]; results=[]; health=[]; old_links=set(); state_lock=Lock()

def clean(s): return re.sub(r'\s+',' ',str(s or '')).strip()
def canonical(url):
    try:
        p=urlparse(url); q=[(k,v) for k,v in parse_qsl(p.query) if not k.lower().startswith('utm_') and k.lower() not in {'gh_src','source','sourceid'}]
        return urlunparse((p.scheme,p.netloc,p.path.rstrip('/'),'',urlencode(q),'')).rstrip('/')
    except: return url

def role_family(title):
    t=title.lower()
    for fam,pats in ROLE_PATTERNS:
        if any(re.search(p,t) for p in pats): return fam
    return None

def title_ok(title):
    t=clean(title).lower()
    if not role_family(t): return False
    if any(re.search(p,t) for p in HARD_TITLE_EXCLUDE+INTERN_EXCLUDE+DOMAIN_EXCLUDE): return False
    return True

def location_ok(loc):
    s=clean(loc); l=s.lower()
    if not s or s.lower() in {'n/a','remote'}: return True
    # Explicit foreign location wins over the word "remote".
    if any(re.search(p,l) for p in NON_US):
        return False
    if 'united states' in l or 'usa' in l or 'u.s.' in l or 'us remote' in l or 'remote - usa' in l: return True
    if re.search(r'\bremote\b',l) and not any(re.search(p,l) for p in NON_US): return True
    if re.search(r',\s*([A-Z]{2})(?:\b|,)',s):
        return re.search(r',\s*([A-Z]{2})(?:\b|,)',s).group(1) in US_STATE_ABBRS
    return any(x in l for x in ['san francisco','seattle','new york','austin','boston','chicago','denver','atlanta','phoenix','dallas','houston','mountain view','palo alto','sunnyvale','cupertino','redmond','bellevue','arlington','virginia','california','texas','washington dc'])

def stale(posted, days=120):
    s=clean(posted)
    if not s or s.lower() in {'n/a','posted today','today'}: return False
    try:
        dt=pd.to_datetime(s,utc=True,errors='coerce')
        if pd.isna(dt): return False
        return (pd.Timestamp.now(tz='UTC')-dt).days > days
    except: return False

def add_job(company,title,location,link,posted='N/A',description='',source=''):
    title,location,link=clean(title),clean(location),clean(link)
    if not title_ok(title) or not location_ok(location) or not link: return False
    txt=(title+' '+clean(description)).lower()
    if any(re.search(p,txt) for p in CLEARANCE_EXCLUDE): return False
    if any(re.search(p,title.lower()) for p in EMPLOYMENT_EXCLUDE): return False
    if any(re.search(p,txt,re.I|re.S) for p in YOE_REJECT): return False
    if stale(posted,120): return False
    link=canonical(link)
    with state_lock:
        if link in old_links: return False
        old_links.add(link)
        results.append({'company':company,'location':location or 'N/A','title':title,'link':link,'posted':posted or 'N/A','role_family':role_family(title),'source':source})
    return True

def req(method,url,**kw):
    h=dict(HEADERS); h.update(kw.pop('headers',{})); return requests.request(method,url,headers=h,timeout=15,**kw)

def scrape_greenhouse(url,company):
    m=re.search(r'(?:boards|job-boards)\.greenhouse\.io/([^/?\s]+)',url)
    if not m: raise ValueError('Bad Greenhouse URL')
    r=req('GET',f'https://boards-api.greenhouse.io/v1/boards/{m.group(1)}/jobs?content=true'); r.raise_for_status(); n=0
    for j in r.json().get('jobs',[]):
        n+=add_job(company,j.get('title'),(j.get('location') or {}).get('name'),j.get('absolute_url'),j.get('first_published') or j.get('updated_at'),BeautifulSoup(j.get('content') or '','html.parser').get_text(' '),'greenhouse')
    return n

def scrape_lever(url,company):
    m=re.search(r'lever\.co/([^/?\s]+)',url)
    if not m: raise ValueError('Bad Lever URL')
    r=req('GET',f'https://api.lever.co/v0/postings/{m.group(1)}?mode=json'); r.raise_for_status(); n=0
    for j in r.json():
        posted=datetime.fromtimestamp((j.get('createdAt') or 0)/1000,tz=timezone.utc).isoformat() if j.get('createdAt') else 'N/A'
        desc=' '.join([j.get('descriptionPlain') or '',j.get('additionalPlain') or ''])
        n+=add_job(company,j.get('text'),(j.get('categories') or {}).get('location'),j.get('hostedUrl'),posted,desc,'lever')
    return n

def scrape_ashby(url,company):
    m=re.search(r'ashbyhq\.com/([\w\-]+)',url)
    if not m: raise ValueError('Bad Ashby URL')
    r=req('GET',f'https://api.ashbyhq.com/posting-api/job-board/{m.group(1)}'); r.raise_for_status(); n=0
    for j in r.json().get('jobs',[]):
        desc=BeautifulSoup(j.get('descriptionHtml') or j.get('description') or '','html.parser').get_text(' ')
        n+=add_job(company,j.get('title'),j.get('location'),j.get('jobUrl'),j.get('publishedAt'),desc,'ashby')
    return n

def scrape_workday(url,company):
    m=re.search(r'https://([\w\-]+)\.(wd\d+)\.myworkdayjobs\.com/(?:[\w\-]+/)?([\w\-]+)',url)
    if not m: raise ValueError('Bad Workday URL')
    sub,wd,site=m.groups(); api=f'https://{sub}.{wd}.myworkdayjobs.com/wday/cxs/{sub}/{site}/jobs'; n=0
    for offset in range(0,100,20):
        time.sleep(random.uniform(.15,.4)); r=req('POST',api,json={'appliedFacets':{},'limit':20,'offset':offset,'searchText':''},headers={'Content-Type':'application/json','Accept':'application/json'})
        if r.status_code!=200: raise RuntimeError(f'Workday {r.status_code} at {api}')
        data=r.json(); posts=data.get('jobPostings',[])
        if not posts: break
        for j in posts:
            title=j.get('title'); loc=j.get('locationsText'); path=j.get('externalPath','')
            if not title_ok(title) or not location_ok(loc):
                continue
            link=f'https://{sub}.{wd}.myworkdayjobs.com/en-US/{site}{path}'
            desc=''; posted=j.get('postedOn') or 'N/A'
            # Fetch the public Workday job-detail JSON only for title/location candidates.
            # This lets the 0-3 YOE filter inspect actual requirements instead of title alone.
            try:
                dr=req('GET',f'https://{sub}.{wd}.myworkdayjobs.com/wday/cxs/{sub}/{site}{path}',headers={'Accept':'application/json'})
                if dr.status_code==200:
                    info=(dr.json() or {}).get('jobPostingInfo',{})
                    desc=BeautifulSoup(info.get('jobDescription') or '','html.parser').get_text(' ')
                    posted=info.get('startDate') or posted
            except Exception:
                pass
            n+=add_job(company,title,loc,link,posted,desc,'workday')
        if offset+20>=data.get('total',0): break
    return n

def scrape_smartrecruiters(url,company):
    m=re.search(r'smartrecruiters\.com/([^/?#]+)',url,re.I)
    if not m: raise ValueError('Bad SmartRecruiters URL')
    slug=m.group(1); n=0; offset=0
    while offset<200:
        r=req('GET',f'https://api.smartrecruiters.com/v1/companies/{slug}/postings',params={'limit':100,'offset':offset}); r.raise_for_status()
        data=r.json(); rows=data.get('content',[])
        if not rows: break
        for j in rows:
            loc=j.get('location') or {}; location=', '.join(filter(None,[loc.get('city'),loc.get('region'),loc.get('country')]))
            jid=j.get('id'); link=f'https://jobs.smartrecruiters.com/{slug}/{jid}' if jid else url
            n+=add_job(company,j.get('name'),location,link,j.get('releasedDate'),'','smartrecruiters')
        offset+=len(rows)
        if offset>=data.get('totalFound',0): break
    return n

def parse_jsonld_jobs(html,base,company,source):
    soup=BeautifulSoup(html,'html.parser'); n=0
    for sc in soup.find_all('script',type='application/ld+json'):
        try: objs=json.loads(sc.string or '{}'); objs=objs if isinstance(objs,list) else [objs]
        except: continue
        stack=list(objs)
        while stack:
            o=stack.pop()
            if isinstance(o,dict):
                if o.get('@type')=='JobPosting':
                    loc=o.get('jobLocation',{}); loc=loc[0] if isinstance(loc,list) and loc else loc
                    addr=(loc or {}).get('address',{}) if isinstance(loc,dict) else {}
                    location=', '.join(filter(None,[addr.get('addressLocality'),addr.get('addressRegion'),addr.get('addressCountry')]))
                    n+=add_job(company,o.get('title'),location,o.get('url') or base,o.get('datePosted'),BeautifulSoup(o.get('description') or '','html.parser').get_text(' '),source)
                stack.extend(v for v in o.values() if isinstance(v,(dict,list)))
            elif isinstance(o,list): stack.extend(o)
    return n

def scrape_google(url,company):
    n=0
    for page in range(1,5):
        r=req('GET',f'https://www.google.com/about/careers/applications/jobs/results/?page={page}'); r.raise_for_status(); soup=BeautifulSoup(r.text,'html.parser')
        found=0
        for a in soup.find_all('a',href=re.compile(r'/about/careers/applications/jobs/results/\d+')):
            href=urljoin('https://www.google.com',a.get('href')); title=clean(a.get('aria-label',''))
            title=re.sub(r'^Learn more about\s+','',title,flags=re.I) or clean(a.get_text(' '))
            box=a.find_parent(['li','div']); text=clean(box.get_text(' ')) if box else ''
            n+=add_job(company,title,text,href,'N/A','', 'google_first_party'); found+=1
        if not found: break
    return n

def scrape_apple(url,company):
    n=0
    for page in range(1,8):
        r=req('GET',f'https://jobs.apple.com/en-us/search?location=united-states-USA&page={page}'); r.raise_for_status(); soup=BeautifulSoup(r.text,'html.parser'); found=0
        for a in soup.find_all('a',href=re.compile(r'/en-us/details/')):
            title=clean(a.get_text(' ')); href=urljoin('https://jobs.apple.com',a.get('href')); box=a.find_parent(['li','tr','div']); text=clean(box.get_text(' ')) if box else ''
            # Apple search result text contains date/location; title/link are authoritative.
            n+=add_job(company,title,text,href,'N/A','', 'apple_first_party'); found+=1
        # Current Apple markup may expose details through links around h3 headings.
        if not found:
            for h in soup.find_all(['h2','h3']):
                a=h.find('a',href=True) or h.find_parent('a',href=True)
                if a and '/details/' in a.get('href',''):
                    n+=add_job(company,clean(h.get_text(' ')),clean(h.parent.get_text(' ')),urljoin('https://jobs.apple.com',a['href']),'N/A','','apple_first_party'); found+=1
        if not found: break
    return n

def scrape_amazon(url,company):
    n=0
    # Search first-party site directly; sort recent and restrict US.
    for q in ['data engineer','cloud engineer','platform engineer','devops engineer','data analyst','data scientist','software engineer']:
        r=req('GET','https://www.amazon.jobs/en/search',params={'base_query':q,'country':'USA','sort':'recent','result_limit':10,'offset':0}); r.raise_for_status(); soup=BeautifulSoup(r.text,'html.parser')
        for a in soup.find_all('a',href=re.compile(r'/en/jobs/')):
            title=clean(a.get_text(' ')); box=a.find_parent(['div','li']); text=clean(box.get_text(' ')) if box else ''
            n+=add_job(company,title,text,urljoin('https://www.amazon.jobs',a.get('href')),'N/A',text,'amazon_first_party')
    return n

def scrape_official(url,company):
    cl=company.lower()
    if cl=='google': return scrape_google(url,company)
    if cl=='apple': return scrape_apple(url,company)
    if cl in {'amazon','amazon / aws'}: return scrape_amazon(url,company)
    # Meta/Microsoft/other first-party portals: try server-rendered JSON-LD/HTML. If blocked, health reports it explicitly.
    r=req('GET',url); r.raise_for_status(); n=parse_jsonld_jobs(r.text,url,company,'official_jsonld')
    if n: return n
    soup=BeautifulSoup(r.text,'html.parser')
    for a in soup.find_all('a',href=True):
        href=urljoin(url,a['href']); title=clean(a.get_text(' '))
        if title_ok(title) and any(x in href.lower() for x in ['/job','jobs/','job_details','position']):
            box=a.find_parent(['li','div']); n+=add_job(company,title,clean(box.get_text(' ')) if box else 'N/A',href,'N/A','','official_html')
    if not n: raise RuntimeError('official portal returned no parseable job records (browser/API adapter needed)')
    return n

def scrape_discovery_markdown(name,url):
    r=req('GET',url); r.raise_for_status(); n=0
    for line in r.text.splitlines():
        if not line.startswith('|') or '---' in line: continue
        cols=[c.strip() for c in line.strip('|').split('|')]
        if len(cols)<4 or cols[0].lower() in {'company','**company**'}: continue
        company=re.sub(r'[*_`]+','',cols[0]).strip()
        title=re.sub(r'[*_`]+','',cols[1]).strip()
        location=re.sub(r'[*_`]+','',cols[2]).strip()
        urls=re.findall(r'https?://[^)\s|]+',line)
        if not urls: continue
        # Prefer employer posting over repository/image links.
        link=next((u for u in urls if 'github.com' not in u and 'img.shields.io' not in u),urls[0])
        age=cols[-1] if cols else 'N/A'
        n+=add_job(company,title,location,link,age,'',f'discovery:{name}')
    return n

def scrape_company(row):
    company=clean(row.get('company')); platform=clean(row.get('platform')).lower(); url=clean(row.get('careers_url')); before=len(results)
    dispatch={'greenhouse':scrape_greenhouse,'lever':scrape_lever,'ashby':scrape_ashby,'workday':scrape_workday,'smartrecruiters':scrape_smartrecruiters,'official':scrape_official,'amazon':scrape_amazon}
    if platform=='official':
        if 'myworkdayjobs.com' in url: fn=scrape_workday
        elif 'smartrecruiters.com' in url: fn=scrape_smartrecruiters
        else: fn=dispatch.get(platform)
    else: fn=dispatch.get(platform)
    try:
        if not fn: raise RuntimeError(f'Unsupported platform: {platform}')
        count=fn(url,company); health.append({'company':company,'platform':platform,'status':'WORKING','new_matches':int(count or 0),'detail':''})
    except Exception as e:
        msg=clean(e); errors.append(f'[ERROR] {company}: {msg[:300]}'); health.append({'company':company,'platform':platform,'status':'FAILED','new_matches':0,'detail':msg[:300]})

def fresh_for_signal(posted):
    s=clean(posted).lower()
    if not s or s=='n/a': return False
    if 'today' in s or 'yesterday' in s: return True
    m=re.search(r'(\d+)\s+days?\s+ago',s)
    if m: return int(m.group(1))<=14
    try:
        dt=pd.to_datetime(posted,utc=True,errors='coerce')
        return False if pd.isna(dt) else (pd.Timestamp.now(tz='UTC')-dt).days<=14
    except: return False

def mass_hiring_signals(jobs):
    by={}
    for j in jobs: by.setdefault(j['company'],[]).append(j)
    out=[]
    for c,js in by.items():
        cohort=[j for j in js if any(k in j['title'].lower() for k in MASS_KEYS)]
        recent=[j for j in js if fresh_for_signal(j.get('posted'))]
        # Burst requires fresh evidence, preventing a newly-added source full of old jobs
        # from looking like a real hiring surge. Cohort titles remain independently useful.
        burst=len(recent)>=5
        if burst or len(cohort)>=2:
            out.append({'company':c,'new_jobs_this_hour':len(js),'fresh_jobs':len(recent),'cohort_jobs':len(cohort),'signal':'COHORT + BURST' if cohort and burst else ('COHORT' if cohort else 'HIRING BURST'),'roles':', '.join(sorted(set(j['role_family'] for j in js if j['role_family']))),'detected_at':datetime.now().strftime('%Y-%m-%d %H:%M:%S')})
    return out

def write_mass(signals):
    if not signals:return
    p=Path('mass_hiring_signals.csv'); pd.DataFrame(signals).to_csv(p,mode='a',index=False,header=not p.exists())
    md=Path('MASS-HIRING-WATCH.md'); old=md.read_text() if md.exists() else '# 🚨 Mass / Cohort Hiring Watch\n'
    block=f"\n## {datetime.now().strftime('%Y-%m-%d %H:%M')}\n\n| Company | Signal | New jobs | Fresh <=14d | Cohort | Roles |\n|---|---|---:|---:|---:|---|\n"
    for x in signals:block+=f"| **{x['company']}** | 🚨 {x['signal']} | {x['new_jobs_this_hour']} | {x.get('fresh_jobs',0)} | {x['cohort_jobs']} | {x['roles']} |\n"
    md.write_text(old+block)

def daily_name(): return f"{datetime.now().day}-{datetime.now().strftime('%B')}-Jobs-List.md"
def update_md(jobs):
    if not jobs: print('No new jobs found this batch.'); return
    f=Path(daily_name()); now=datetime.now().strftime('%Y-%m-%d %H:%M:%S'); counts={}
    for j in jobs:counts[j['company']]=counts.get(j['company'],0)+1
    summary=f"\n📊 **{len(jobs)} new jobs this batch:**\n"+''.join(f"- {c}: {n} job{'s' if n!=1 else ''}\n" for c,n in sorted(counts.items()))
    table='| Company | Location | Role | Family | Apply | Posted |\n|---|---|---|---|---|---|\n'
    for j in jobs:table+=f"| **{j['company']}** | {j['location']} | {j['title']} | {j['role_family']} | [Apply]({j['link']}) | {j['posted']} |\n"
    header=f"# 📢 Job Listings — {datetime.now().strftime('%B %d, %Y')}\n\n> Hourly · US only · full-time · 0–3 YOE target · newest batch first.\n"
    existing=f.read_text() if f.exists() else ''
    if existing.startswith('# '): existing='\n'.join(existing.split('\n')[3:])
    f.write_text(header+f"\n### 🕐 Batch at {now}\n{summary}\n{table}\n---\n"+existing)
    Path('README.md').write_text(f.read_text())

def telegram(jobs):
    tok=os.getenv('TELEGRAM_BOT_TOKEN',''); cid=os.getenv('TELEGRAM_CHAT_ID','')
    if not jobs or not tok or not cid:return
    sig=mass_hiring_signals(jobs); msg=f"🚀 *{len(jobs)} NEW MATCHING JOBS — {datetime.now().strftime('%b %d %H:%M')}*\n"
    if sig:
        msg+=f"🚨 *{len(sig)} HIRING SIGNAL(S)*\n"+''.join(f"• {x['company']}: {x['signal']} — {x['new_jobs_this_hour']}\n" for x in sig[:4])+'\n'
    for j in jobs[:15]:msg+=f"\n🏢 *{j['company']}*\n💼 {j['title']}\n📍 {j['location']}\n🔗 [Apply]({j['link']})\n"
    requests.post(f'https://api.telegram.org/bot{tok}/sendMessage',json={'chat_id':cid,'text':msg,'parse_mode':'Markdown','disable_web_page_preview':True},timeout=10)

if __name__=='__main__':
    p=Path('seen_links.csv')
    if p.exists():
        try: old_links=set(canonical(x) for x in pd.read_csv(p)['link'].dropna().astype(str))
        except: old_links=set()
    df=pd.read_csv('companies.csv'); print(f'Scraping {len(df)} companies...')
    with ThreadPoolExecutor(max_workers=8) as ex:
        fs=[ex.submit(scrape_company,row) for _,row in df.iterrows()]
        for f in as_completed(fs):
            try:f.result()
            except:pass
    # Supplemental discovery feeds: discover new-grad jobs, but alerts still use direct employer URLs.
    discovery_health=[]
    for dname,durl in DISCOVERY_SOURCES:
        try:
            c=scrape_discovery_markdown(dname,durl); discovery_health.append({'company':dname,'platform':'discovery','status':'WORKING','new_matches':c,'detail':''})
        except Exception as e:
            discovery_health.append({'company':dname,'platform':'discovery','status':'FAILED','new_matches':0,'detail':clean(e)[:300]})
    health.extend(discovery_health)
    # Deterministic order and de-dupe.
    uniq={j['link']:j for j in results}; final=sorted(uniq.values(),key=lambda j:(j['company'],j['title'],j['location']))
    print(f'Found {len(final)} new matching jobs')
    update_md(final)
    if final: pd.DataFrame({'link':[j['link'] for j in final]}).to_csv(p,mode='a',index=False,header=not p.exists())
    sig=mass_hiring_signals(final); write_mass(sig); telegram(final)
    pd.DataFrame(health).sort_values(['status','company']).to_csv('source_health.csv',index=False)
    direct_health=[x for x in health if x.get('platform')!='discovery']; working=sum(x['status']=='WORKING' for x in direct_health); failed=len(direct_health)-working
    print('\n========== SOURCE HEALTH ==========')
    print(f'Total companies:      {len(df)}')
    print(f'Working/queried:      {working}')
    print(f'Failed/unsupported:   {failed}')
    print(f'Discovery feeds:      {sum(x["status"]=="WORKING" for x in health if x.get("platform")=="discovery")}/{len(DISCOVERY_SOURCES)} working')
    for name in ['Google','Meta','Amazon','Apple','Microsoft']:
        rows=[x for x in health if x['company'].lower()==name.lower()]
        if rows: print(f"{name:20} {rows[0]['status']:8} {rows[0]['platform']} {rows[0]['detail'][:80]}")
    print('===================================')
    if errors:
        print('\n--- ERRORS (first 30) ---')
        print('\n'.join(errors[:30]))
