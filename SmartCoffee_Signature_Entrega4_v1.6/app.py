import csv, io, json, os, secrets, hashlib, hmac, threading, webbrowser, argparse, random
from datetime import date, datetime, timedelta
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
from pathlib import Path
from urllib.parse import urlparse, parse_qs
from collections import Counter

ROOT=Path(__file__).resolve().parent
DATA=ROOT/'data'; DATA.mkdir(exist_ok=True)
LOCK=threading.RLock(); SESSIONS={}; TEMP_SUGGESTIONS={}; LAST_GENERATION={}
DEFAULT_PORT=8765

def read(name,default):
    p=DATA/name
    if not p.exists(): return default
    with LOCK:
        try: return json.loads(p.read_text(encoding='utf-8'))
        except (ValueError,OSError): return default

def save(name,obj):
    with LOCK:
        p=DATA/name; tmp=p.with_suffix('.tmp')
        with open(tmp,'w',encoding='utf-8') as f:
            json.dump(obj,f,ensure_ascii=False,indent=2); f.flush(); os.fsync(f.fileno())
        os.replace(tmp,p)

def hash_password(pwd,salt=None):
    salt=salt or secrets.token_hex(16)
    return salt+'$'+hashlib.pbkdf2_hmac('sha256',pwd.encode(),bytes.fromhex(salt),260000).hex()

def check_password(pwd,stored):
    try: return hmac.compare_digest(hash_password(pwd,stored.split('$')[0]),stored)
    except Exception: return False

def days(exp): return (date.fromisoformat(exp)-date.today()).days

def state(lot):
    try:
        d=days(lot['expiry'])
        return 'Vencido' if d<0 else 'Crítico' if d<=2 else 'Próximo' if d<=5 else 'Vigente'
    except Exception: return 'Inválido'

def next_lot_code(inventory=None):
    """Preview the next permanent identifier; legacy codes are preserved."""
    if inventory is None: inventory=read('inventory.json',[])
    used=[int(str(x.get('lot',''))[4:]) for x in inventory
          if str(x.get('lot','')).upper().startswith('LOT-') and str(x.get('lot',''))[4:].isdigit()]
    counter=read('lot_sequence.json',{}).get('last',0)
    return f'LOT-{max([int(counter)]+used)+1:03d}'

def seed():
    if not (DATA/'inventory.json').exists():
        today=date.today()
        products=[('Pan de caja','Panadería',12,'pzas',1,8),('Leche entera','Lácteos',6,'litros',2,24),('Muffin','Panadería',8,'pzas',2,18),('Yogurt','Lácteos',4,'pzas',-1,14),('Café americano','Bebidas',35,'pzas',20,16),('Cappuccino','Bebidas',30,'pzas',15,25),('Croissant','Panadería',10,'pzas',4,20),('Té chai','Bebidas',25,'pzas',30,20),('Galleta de avena','Panadería',14,'pzas',7,12),('Sandwich integral','Alimentos',10,'pzas',3,32)]
        save('inventory.json',[{'id':i+1,'product':p,'category':c,'lot':f'LOT-{i+1:03d}','qty':q,'unit':u,'expiry':(today+timedelta(days=d)).isoformat(),'cost':cost} for i,(p,c,q,u,d,cost) in enumerate(products)])
    if not (DATA/'transactions.json').exists():
        # 100 tickets DEMO with consistent market basket associations.
        tickets=[]
        for i in range(100):
            basket=[]
            if i<24: basket=['Pan de caja','Café americano']
            elif i<30: basket=['Pan de caja','Té chai']
            elif i<50: basket=['Café americano','Galleta de avena']
            elif i<65: basket=['Muffin','Cappuccino']
            elif i<70: basket=['Muffin','Té chai']
            elif i<75: basket=['Cappuccino','Croissant']
            elif i<85: basket=['Sandwich integral','Café americano']
            else: basket=['Croissant','Té chai']
            tickets.append({'ticket_id':f'T-{i+1:04d}','date':date.today().isoformat(),'items':basket})
        save('transactions.json',tickets)
    if not (DATA/'promotions.json').exists(): save('promotions.json',[])
    if not (DATA/'losses.json').exists(): save('losses.json',[])
    if not (DATA/'users.json').exists():
        password=os.environ.get('SMARTCOFFEE_ADMIN_PASSWORD') or secrets.token_urlsafe(10)
        save('users.json',[{'id':1,'username':'admin','name':'Administrador','role':'admin','password_hash':hash_password(password),'active':True,'must_change':True}])
        print('\n'+'='*58+'\n CREDENCIALES INICIALES (GUARDAR EN LUGAR SEGURO)\n Usuario: admin\n Contraseña: '+password+'\n Cambiar contraseña desde Gestión de usuarios.\n'+'='*58+'\n',flush=True)

def apriori(transactions, min_support=.15, min_conf=.70, min_lift=1.4):
    baskets=[set(t.get('items',[])) for t in transactions if t.get('items')]
    n=len(baskets)
    if not n: return []
    singles=Counter(item for basket in baskets for item in basket)
    pairs=Counter(tuple(sorted((a,b))) for basket in baskets for a in basket for b in basket if a<b)
    rules=[]
    for (a,b),count in pairs.items():
        for antecedent,consequent in [(a,b),(b,a)]:
            support=count/n; conf=count/singles[antecedent]; lift=conf/(singles[consequent]/n)
            if support>=min_support and conf>=min_conf and lift>=min_lift:
                rules.append({'a':antecedent,'b':consequent,'support':round(support,4),'confidence':round(conf,4),'lift':round(lift,3),'count':count})
    return sorted(rules,key=lambda r:(-r['lift'],-r['confidence'],-r['support']))

def viable(prom,inventory):
    if prom.get('status')!='approved': return False
    try:
        if date.fromisoformat(prom['expires'])<date.today(): return False
    except Exception: return False
    for product in prom['products']:
        if not any(l['product']==product and float(l['qty'])>0 and days(l['expiry'])>=0 for l in inventory): return False
    return True

def recommendation_analysis():
    """Prioritize expiring stock; never invent rules or quantities."""
    inv=read('inventory.json',[])
    transactions=read('transactions.json',[])
    rules=apriori(transactions)
    valid=[l for l in inv if float(l.get('qty',0))>0 and state(l) in ('Crítico','Próximo','Vigente')]
    at_risk=[l for l in valid if state(l) in ('Crítico','Próximo')]
    products_in_tickets={x for t in transactions for x in t.get('items',[])}
    products_in_rules={r['a'] for r in rules}|{r['b'] for r in rules}
    diagnostics={'tickets':len(transactions),'rules':len(rules),'critical_lots':sum(state(l)=='Crítico' for l in at_risk),
        'near_lots':sum(state(l)=='Próximo' for l in at_risk),'at_risk_products':len({l['product'] for l in at_risk}),
        'missing_history':sorted({l['product'] for l in at_risk}-products_in_tickets),
        'no_strong_rule':sorted(({l['product'] for l in at_risk}&products_in_tickets)-products_in_rules),
        'no_valid_partner':[],'limit':None}
    by_product={}
    for l in valid: by_product.setdefault(l['product'],[]).append(l)
    candidates={}
    for r in rules:
        for risk,partner in ((r['a'],r['b']),(r['b'],r['a'])):
            risk_lots=[l for l in by_product.get(risk,[]) if state(l) in ('Crítico','Próximo')]
            partner_lots=by_product.get(partner,[])
            if not risk_lots or not partner_lots or risk==partner: continue
            urgency=min(days(l['expiry']) for l in risk_lots)
            usable_risk=[l for l in risk_lots if days(l['expiry'])==urgency]
            capacity=min(sum(float(l['qty']) for l in usable_risk),sum(float(l['qty']) for l in partner_lots))
            if capacity<=0: continue
            cost=sum(min(float(l['cost']) for l in by_product[x]) for x in (risk,partner))
            key=(risk,partner)
            candidate={'id':f'{risk}|{partner}','name':f'Selección Gourmet: {risk} + {partner}',
                'products':[risk,partner],'price':round(cost*1.6,2),'max_units':capacity,
                'expires':min(l['expiry'] for l in usable_risk),
                'description':f'Especial antimerma: disfruta {risk} acompañado de {partner}.',
                'metrics':r,'method':'Apriori','priority':'Crítico' if urgency<=2 else 'Próximo','days_left':urgency}
            previous=candidates.get(key)
            if previous is None or (candidate['metrics']['confidence'],candidate['metrics']['lift'])>(previous['metrics']['confidence'],previous['metrics']['lift']):
                candidates[key]=candidate
    out=sorted(candidates.values(),key=lambda x:(x['days_left'],-x['metrics']['confidence'],-x['metrics']['lift'],-x['metrics']['support'],x['name']))
    # Modelo comparativo Top-N de la Entrega 3: propuestas heurísticas claramente
    # identificadas, sin presentar métricas estadísticas inexistentes.
    frequency=Counter(item for t in transactions for item in set(t.get('items',[])))
    for risk in sorted({l['product'] for l in at_risk}, key=lambda name:(min(days(l['expiry']) for l in at_risk if l['product']==name),name)):
        risk_lots=[l for l in by_product[risk] if state(l) in ('Crítico','Próximo')]
        urgency=min(days(l['expiry']) for l in risk_lots)
        usable=[l for l in risk_lots if days(l['expiry'])==urgency]
        for partner in sorted((x for x in by_product if x!=risk),key=lambda x:(-frequency[x],x)):
            key=(risk,partner)
            if key in candidates: continue
            partner_lots=by_product[partner]
            capacity=min(sum(float(l['qty']) for l in usable),sum(float(l['qty']) for l in partner_lots))
            if capacity<=0: continue
            cost=sum(min(float(l['cost']) for l in by_product[x]) for x in key)
            candidates[key]={'id':f'{risk}|{partner}','name':f'Rescate Gourmet: {risk} + {partner}',
                'products':[risk,partner],'price':round(cost*1.6,2),'max_units':capacity,
                'expires':min(l['expiry'] for l in usable),
                'description':f'Propuesta antimerma Top-N: {risk} con {partner}. Asociación no validada por Apriori.',
                'metrics':None,'method':'Top-N (heurístico)','priority':'Crítico' if urgency<=2 else 'Próximo','days_left':urgency,
                'popularity':frequency[partner]}
    out=sorted(candidates.values(),key=lambda x:(x['days_left'],x.get('metrics') is None,-(x['metrics']['confidence'] if x.get('metrics') else 0),-x.get('popularity',0),x['name']))
    diagnostics['apriori_viable']=sum(x.get('metrics') is not None for x in out)
    diagnostics['heuristic_viable']=sum(x.get('metrics') is None for x in out)
    diagnostics['no_valid_partner']=sorted({l['product'] for l in at_risk}-{x['products'][0] for x in out}-set(diagnostics['missing_history'])-set(diagnostics['no_strong_rule']))
    diagnostics['viable_total']=len(out)
    return out,diagnostics

def recommendations():
    return recommendation_analysis()[0]

def selected_limit():
    settings=read('generation_settings.json',{})
    return settings.get('quantity',15)

def refresh_suggestions(quantity=None, user_id=None):
    """Generación temporal: cada clic sustituye propuestas, sin escribirlas en disco."""
    if quantity is None: quantity=selected_limit()
    if quantity != 'all' and (type(quantity) is not int or not 1<=quantity<=1000):
        raise ValueError('Selecciona una cantidad entre 1 y 1000, o todos los disponibles.')
    suggestions,diagnostics=recommendation_analysis()
    diagnostics['requested']=quantity
    uid=user_id or 0
    # Evitar duplicados con las promociones ya aprobadas.
    approved_keys={p.get('source_id') for p in read('promotions.json',[]) if p.get('status')=='approved'}
    pool=[s for s in suggestions if s['id'] not in approved_keys]
    previous=LAST_GENERATION.get(uid,set())
    # Mezcla por grupos de urgencia, alternando productos de riesgo cuando es posible.
    buckets={}
    for candidate in pool:
        buckets.setdefault(candidate['days_left'],[]).append(candidate)
    ordered=[]
    for urgency in sorted(buckets):
        group=buckets[urgency]
        by_risk={}
        for c in group: by_risk.setdefault(c['products'][0],[]).append(c)
        for vals in by_risk.values():
            random.shuffle(vals)
            vals.sort(key=lambda c:(c['id'] in previous,c.get('metrics') is None))
        names=list(by_risk)
        random.shuffle(names)
        while names:
            remaining=[]
            for name in names:
                if by_risk[name]: ordered.append(by_risk[name].pop(0))
                if by_risk[name]: remaining.append(name)
            names=remaining
    # Si hay alternativas suficientes, no repetir combos de la generación anterior.
    fresh=[c for c in ordered if c['id'] not in previous]
    repeated=[c for c in ordered if c['id'] in previous]
    ordered=fresh+repeated
    chosen=ordered if quantity=='all' else ordered[:quantity]
    TEMP_SUGGESTIONS[uid]=[dict(c,id=secrets.token_hex(6),source_id=c['id'],status='pending',created=datetime.now().isoformat(timespec='seconds')) for c in chosen]
    LAST_GENERATION[uid]={c['source_id'] for c in TEMP_SUGGESTIONS[uid]}
    return {'count':len(chosen),'created':len(chosen),'refreshed':0,'withdrawn':0,'items':TEMP_SUGGESTIONS[uid], 'diagnostics':diagnostics,'total_viable':len(pool)}

class Handler(BaseHTTPRequestHandler):
    server_version='SmartCoffee/1.0'
    def log_message(self,fmt,*args): print('[HTTP]',fmt%args)
    def reply(self,code,obj):
        payload=json.dumps(obj,ensure_ascii=False).encode()
        self.send_response(code); self.send_header('Content-Type','application/json; charset=utf-8'); self.send_header('Cache-Control','no-store'); self.send_header('X-Content-Type-Options','nosniff'); self.send_header('Content-Length',str(len(payload))); self.end_headers(); self.wfile.write(payload)
    def current(self):
        cookie=self.headers.get('Cookie','')
        token=next((x.strip().split('=',1)[1] for x in cookie.split(';') if x.strip().startswith('sc_session=')),None)
        user_id=SESSIONS.get(token)
        return next((u for u in read('users.json',[]) if u['id']==user_id and u['active']),None)
    def require(self,admin=False):
        u=self.current()
        if not u: self.reply(401,{'error':'Inicia sesión para continuar.'}); return None
        if admin and u['role']!='admin': self.reply(403,{'error':'Acceso exclusivo para administradores.'}); return None
        return u
    def body(self):
        n=int(self.headers.get('Content-Length','0'))
        if n>2_000_000: raise ValueError('Archivo demasiado grande (máx. 2 MB).')
        return json.loads(self.rfile.read(n) or b'{}')
    def do_GET(self):
        path=urlparse(self.path).path
        if path in ('/','/index.html'):
            p=ROOT/'static'/'index.html'; data=p.read_bytes(); mime='text/html; charset=utf-8'
        elif path in ('/style.css','/app.js'):
            p=ROOT/'static'/path.lstrip('/'); data=p.read_bytes(); mime='text/css' if path.endswith('.css') else 'text/javascript'
        elif path=='/api/public':
            inv=read('inventory.json',[])
            return self.reply(200,{'promotions':[p for p in read('promotions.json',[]) if viable(p,inv)]})
        elif path=='/api/me':
            u=self.current(); return self.reply(200,{'user':self.clean_user(u) if u else None})
        elif path.startswith('/api/'):
            u=self.require()
            if not u: return
            if path=='/api/overview':
                inv=read('inventory.json',[]); promos=read('promotions.json',[])
                counts={s:sum(1 for l in inv if state(l)==s) for s in ('Vencido','Crítico','Próximo','Vigente')}
                return self.reply(200,{'counts':counts,'lots':len(inv),'pending':sum(p['status']=='pending' for p in promos),'approved':sum(viable(p,inv) for p in promos),'alerts':[l for l in inv if state(l) in ('Vencido','Crítico')]})
            if path=='/api/next-lot':
                if u['role']!='admin': return self.reply(403,{'error':'Sin permiso.'})
                return self.reply(200,{'lot':next_lot_code()})
            if path=='/api/inventory':
                inv=read('inventory.json',[])
                if u['role']!='admin': inv=[{k:v for k,v in l.items() if k!='cost'} for l in inv]
                return self.reply(200,{'items':[dict(l,status=state(l),days=days(l['expiry'])) for l in inv]})
            if path=='/api/transactions': return self.reply(200,{'items':read('transactions.json',[]),'rules':apriori(read('transactions.json',[]))})
            if path=='/api/recommendations':
                suggestions,diagnostics=recommendation_analysis()
                return self.reply(200,{'items':TEMP_SUGGESTIONS.get(u['id'],[]),'diagnostics':diagnostics})
            if path=='/api/promotions': return self.reply(200,{'items':TEMP_SUGGESTIONS.get(u['id'],[])+[p for p in read('promotions.json',[]) if p.get('status')=='approved']})
            if path=='/api/users':
                if u['role']!='admin': return self.reply(403,{'error':'Sin permiso.'})
                return self.reply(200,{'items':[self.clean_user(x) for x in read('users.json',[])]})
            if path=='/api/report':
                inv=read('inventory.json',[]); promos=read('promotions.json',[]); losses=read('losses.json',[])
                return self.reply(200,{'expired':sum(float(l['qty'])*float(l['cost']) for l in inv if state(l)=='Vencido') if u['role']=='admin' else None,'expired_lots':sum(state(l)=='Vencido' for l in inv),'approved':sum(p['status']=='approved' for p in promos),'rejected':sum(p['status']=='rejected' for p in promos),'losses':losses})
            if path=='/api/export':
                rows=read('inventory.json',[]); f=io.StringIO(); w=csv.writer(f); w.writerow(['producto','lote','cantidad','unidad','caducidad','estado']); [w.writerow([r['product'],r['lot'],r['qty'],r['unit'],r['expiry'],state(r)]) for r in rows]
                data=f.getvalue().encode('utf-8-sig'); self.send_response(200); self.send_header('Content-Type','text/csv; charset=utf-8'); self.send_header('Content-Disposition','attachment; filename="inventario_smartcoffee.csv"'); self.end_headers(); self.wfile.write(data); return
            return self.reply(404,{'error':'Ruta no encontrada.'})
        else: return self.reply(404,{'error':'No encontrado.'})
        self.send_response(200); self.send_header('Content-Type',mime); self.send_header('Content-Length',str(len(data))); self.send_header('Cache-Control','no-store'); self.end_headers(); self.wfile.write(data)
    @staticmethod
    def clean_user(u): return {k:v for k,v in u.items() if k!='password_hash'} if u else None
    def do_POST(self):
        path=urlparse(self.path).path
        try: b=self.body()
        except (ValueError,json.JSONDecodeError) as e: return self.reply(400,{'error':str(e)})
        if path=='/api/login':
            u=next((u for u in read('users.json',[]) if u['username'].lower()==str(b.get('username','')).lower() and u['active']),None)
            if not u or not check_password(str(b.get('password','')),u['password_hash']): return self.reply(401,{'error':'Usuario o contraseña incorrectos.'})
            token=secrets.token_urlsafe(32); SESSIONS[token]=u['id']
            payload=json.dumps({'user':self.clean_user(u)},ensure_ascii=False).encode()
            self.send_response(200); self.send_header('Content-Type','application/json'); self.send_header('Set-Cookie',f'sc_session={token}; HttpOnly; SameSite=Strict; Path=/'); self.send_header('Content-Length',str(len(payload))); self.end_headers(); self.wfile.write(payload); return
        if path=='/api/logout':
            cookie=self.headers.get('Cookie',''); token=next((x.strip().split('=',1)[1] for x in cookie.split(';') if x.strip().startswith('sc_session=')),None)
            SESSIONS.pop(token,None); self.send_response(200); self.send_header('Set-Cookie','sc_session=; Max-Age=0; HttpOnly; SameSite=Strict; Path=/'); self.end_headers(); return
        u=self.require()
        if not u: return
        try:
            if path=='/api/password':
                if not check_password(str(b.get('old','')),u['password_hash']): raise ValueError('La contraseña actual no coincide.')
                if len(str(b.get('new','')))<10: raise ValueError('La nueva contraseña requiere al menos 10 caracteres.')
                users=read('users.json',[])
                for x in users:
                    if x['id']==u['id']: x['password_hash']=hash_password(b['new']); x['must_change']=False
                save('users.json',users); return self.reply(200,{'ok':True})
            if path=='/api/users':
                if not self.require(admin=True): return
                username=str(b.get('username','')).strip(); pwd=str(b.get('password',''))
                if not username or len(pwd)<10: raise ValueError('Usuario obligatorio y contraseña de al menos 10 caracteres.')
                users=read('users.json',[])
                if any(x['username'].lower()==username.lower() for x in users): raise ValueError('Ese usuario ya existe.')
                role=b.get('role','operator')
                if role not in ('admin','operator'): raise ValueError('Rol no válido.')
                users.append({'id':max([x['id'] for x in users],default=0)+1,'username':username,'name':str(b.get('name','')).strip() or username,'role':role,'password_hash':hash_password(pwd),'active':True,'must_change':True})
                save('users.json',users); return self.reply(200,{'ok':True})
            if path=='/api/user-toggle':
                if not self.require(admin=True): return
                users=read('users.json',[]); target=next((x for x in users if x['id']==int(b['id'])),None)
                if not target or target['id']==u['id']: raise ValueError('No puedes desactivar tu propia cuenta.')
                target['active']=not target['active']; save('users.json',users); return self.reply(200,{'ok':True})
            if path=='/api/user-reset':
                if not self.require(admin=True): return
                users=read('users.json',[]); target=next((x for x in users if x['id']==int(b['id'])),None)
                if not target or len(str(b.get('password','')))<10: raise ValueError('Cuenta o contraseña inválida (mínimo 10 caracteres).')
                target['password_hash']=hash_password(b['password']); target['must_change']=True; save('users.json',users); return self.reply(200,{'ok':True})
            if path=='/api/inventory':
                if not self.require(admin=True): return
                product=str(b.get('product','')).strip(); qty=float(b.get('qty',-1)); cost=float(b.get('cost',-1)); expiry=str(b.get('expiry','')); date.fromisoformat(expiry)
                if not product or qty<0 or cost<0 or not b.get('unit'): raise ValueError('Completa los campos con cantidades y costos válidos.')
                with LOCK:
                    inv=read('inventory.json',[])
                    existing=next((x for x in inv if x['id']==int(b.get('id',0))),None)
                    # El servidor determina el código: no se acepta un lote inventado desde el navegador.
                    lot=existing['lot'] if existing else next_lot_code(inv)
                    new={'product':product,'category':str(b.get('category','Otros')),'lot':lot,'qty':qty,'unit':str(b['unit']),'expiry':expiry,'cost':cost}
                    if existing: existing.update(new)
                    else:
                        inv.append(dict(id=max([x['id'] for x in inv],default=0)+1,**new))
                    save('inventory.json',inv)
                    if not existing: save('lot_sequence.json',{'last':int(lot.split('-')[1])})
                TEMP_SUGGESTIONS.clear(); LAST_GENERATION.clear(); return self.reply(200,{'ok':True,'recommendations':0})
            if path=='/api/transactions':
                if not self.require(admin=True): return
                rows=b.get('items',[])
                if not isinstance(rows,list) or len(rows)>5000: raise ValueError('Se aceptan hasta 5000 tickets.')
                for t in rows:
                    if not isinstance(t.get('items'),list) or len(t['items'])<1: raise ValueError('Cada ticket requiere al menos un producto.')
                save('transactions.json',rows); TEMP_SUGGESTIONS.clear(); LAST_GENERATION.clear(); return self.reply(200,{'ok':True,'count':len(rows),'recommendations':0})
            if path=='/api/generate':
                if not self.require(admin=True): return
                quantity=b.get('quantity',selected_limit())
                if quantity!='all' and (type(quantity) is not int or not 1<=quantity<=1000):
                    raise ValueError('Selecciona una cantidad entre 1 y 1000, o todos los disponibles.')
                save('generation_settings.json',{'quantity':quantity})
                return self.reply(200,refresh_suggestions(quantity,u['id']))
            if path=='/api/promotion-action':
                if not self.require(admin=True): return
                promos=read('promotions.json',[])
                temporary=TEMP_SUGGESTIONS.get(u['id'],[])
                p=next((p for p in temporary if p['id']==b.get('id')),None)
                is_temporary=p is not None
                if p is None: p=next((p for p in promos if p['id']==b.get('id') and p.get('status')=='approved'),None)
                if not p: raise ValueError('La sugerencia ya no está disponible. Genera otras recomendaciones.')
                action=b.get('action')
                if action=='edit':
                    name=str(b.get('name','')).strip(); desc=str(b.get('description','')).strip(); price=float(b.get('price',0))
                    if not name or price<=0: raise ValueError('Nombre y precio válido obligatorios.')
                    p.update(name=name,description=desc,price=price,status='pending',manually_edited=True)
                    if not is_temporary:
                        promos=[x for x in promos if x['id']!=p['id']]
                        temporary.append(p)
                elif action=='approve':
                    if not all(any(l['product']==x and float(l['qty'])>0 and days(l['expiry'])>=0 for l in read('inventory.json',[])) for x in p['products']): raise ValueError('No hay inventario vigente para este combo.')
                    if date.fromisoformat(p['expires'])<date.today(): raise ValueError('Promoción vencida.')
                    p['status']='approved'
                    if is_temporary:
                        promos.append(dict(p))
                        temporary.remove(p)
                elif action=='reject':
                    if is_temporary: temporary.remove(p)
                    else: raise ValueError('Solo puedes rechazar propuestas temporales.')
                else: raise ValueError('Acción no válida.')
                p['updated']=datetime.now().isoformat(timespec='seconds')
                save('promotions.json',promos)
                return self.reply(200,{'ok':True})
            if path=='/api/loss':
                if not self.require(admin=True): return
                amount=float(b.get('amount',0)); qty=float(b.get('qty',0))
                if amount<0 or qty<=0: raise ValueError('Cantidad y costo inválidos.')
                losses=read('losses.json',[]); losses.append({'date':date.today().isoformat(),'product':str(b.get('product','')).strip(),'qty':qty,'amount':amount}); save('losses.json',losses); return self.reply(200,{'ok':True})
            return self.reply(404,{'error':'Ruta no encontrada.'})
        except (ValueError,KeyError,TypeError,OverflowError) as e: return self.reply(400,{'error':str(e)})

if __name__=='__main__':
    parser=argparse.ArgumentParser(); parser.add_argument('--port',type=int,default=DEFAULT_PORT); parser.add_argument('--no-browser',action='store_true'); args=parser.parse_args()
    seed(); url=f'http://127.0.0.1:{args.port}'
    print(f'Smart Coffee Menú iniciado: {url}\nPara detener: Ctrl+C',flush=True)
    if not args.no_browser: threading.Timer(1,lambda:webbrowser.open(url)).start()
    ThreadingHTTPServer(('127.0.0.1',args.port),Handler).serve_forever()
