"""Validate local BPMN references, flow structure, DI, and cross-file calls.

Run from the package directory: python validacion/validar_bpmn.py
Optional: --schema /path/to/OMG/BPMN20.xsd (requires lxml).
"""
from pathlib import Path
import xml.etree.ElementTree as E
from collections import Counter, defaultdict, deque
import argparse, json

NS={'b':'http://www.omg.org/spec/BPMN/20100524/MODEL','bd':'http://www.omg.org/spec/BPMN/20100524/DI','dc':'http://www.omg.org/spec/DD/20100524/DC','di':'http://www.omg.org/spec/DD/20100524/DI'}
KINDS={'startEvent','endEvent','intermediateCatchEvent','intermediateThrowEvent','boundaryEvent','task','userTask','manualTask','serviceTask','sendTask','receiveTask','businessRuleTask','scriptTask','subProcess','callActivity','exclusiveGateway','parallelGateway','inclusiveGateway','eventBasedGateway','complexGateway'}
def local(tag):return tag.rsplit('}',1)[-1]
def reachable(starts,adj):
 seen=set(starts);q=deque(starts)
 while q:
  for n in adj.get(q.popleft(),[]):
   if n not in seen:seen.add(n);q.append(n)
 return seen

def validate(root,schema=None):
 files=sorted((root/'bpmn').glob('*.bpmn'));trees={f:E.parse(f) for f in files}
 processes={p.get('id') for t in trees.values() for p in t.findall('.//b:process',NS)}
 results=[]
 for f,t in trees.items():
  errors=[];notes=[];ids=[x.get('id') for x in t.iter() if x.get('id')];by={x.get('id'):x for x in t.iter() if x.get('id')}
  duplicates=[k for k,v in Counter(ids).items() if v>1]
  if duplicates:errors.append('IDs repetidos: '+str(duplicates))
  for x in t.iter():
   for attr in ['sourceRef','targetRef','attachedToRef','processRef','bpmnElement','default']:
    if x.get(attr) and x.get(attr) not in by:errors.append(f'Referencia inexistente: {x.get("id")} {attr}={x.get(attr)}')
   if local(x.tag)=='callActivity' and x.get('calledElement','').split(':')[-1] not in processes:errors.append('Proceso llamado inexistente: '+x.get('calledElement',''))
  shapes={s.get('bpmnElement'):s for s in t.findall('.//bd:BPMNShape',NS)}
  edges={s.get('bpmnElement') for s in t.findall('.//bd:BPMNEdge',NS)}
  for sh in shapes.values():
   b=sh.find('dc:Bounds',NS)
   if b is None or any(float(b.get(v,'0'))<=0 for v in ['width','height']):errors.append('Bounds inválidos: '+sh.get('id'))
  for p in t.findall('.//b:process',NS):
   topnodes=[x for x in p if local(x.tag) in KINDS];refs=[x.text for x in p.findall('./b:laneSet/b:lane/b:flowNodeRef',NS)]
   for x in topnodes:
    if refs.count(x.get('id'))!=1:errors.append('Carril ausente o repetido: '+x.get('id'))
    if x.get('id') not in shapes:errors.append('DI de nodo ausente: '+x.get('id'))
   for scope in [p]+p.findall('.//b:subProcess',NS):
    nodes={x.get('id'):x for x in scope if local(x.tag) in KINDS};flows=[x for x in scope if local(x.tag)=='sequenceFlow'];inc=defaultdict(list);out=defaultdict(list);adj=defaultdict(list);rev=defaultdict(list)
    for flow in flows:
     s=flow.get('sourceRef');g=flow.get('targetRef');fid=flow.get('id')
     if s not in nodes or g not in nodes:errors.append('Flujo fuera de su ámbito: '+fid)
     inc[g].append(fid);out[s].append(fid);adj[s].append(g);rev[g].append(s)
     if scope is p and fid not in edges:errors.append('DI de flujo ausente: '+fid)
    starts=[];ends=[]
    for id,n in nodes.items():
     kind=local(n.tag)
     if sorted(x.text for x in n.findall('b:incoming',NS))!=sorted(inc[id]):errors.append('Incoming incoherente: '+id)
     if sorted(x.text for x in n.findall('b:outgoing',NS))!=sorted(out[id]):errors.append('Outgoing incoherente: '+id)
     if kind=='startEvent':
      starts.append(id)
      if inc[id]:errors.append('Inicio con incoming: '+id)
     elif kind=='endEvent':
      ends.append(id)
      if out[id]:errors.append('Fin con outgoing: '+id)
     elif kind=='boundaryEvent':
      parent=n.get('attachedToRef');adj[parent].append(id);rev[id].append(parent)
      if inc[id]:errors.append('Evento de borde con incoming: '+id)
     elif not inc[id] or not out[id]:errors.append('Nodo sin continuidad: '+id)
     if kind=='exclusiveGateway' and len(out[id])>1:
      for flow in flows:
       if flow.get('sourceRef')==id and flow.get('id')!=n.get('default') and flow.find('b:conditionExpression',NS) is None:
        # The supplied legacy models use branch labels without executable expressions.
        if f.name.startswith(('00','07')):notes.append('Condición solo etiquetada en referencia previa: '+flow.get('id'))
        else:errors.append('Condición o default ausente: '+flow.get('id'))
    for id in set(nodes)-reachable(starts,adj):errors.append('Nodo inalcanzable: '+id)
    for id in set(nodes)-reachable(ends,rev):errors.append('Nodo sin ruta a fin: '+id)
  xsd=None
  if schema:
   from lxml import etree
   validator=etree.XMLSchema(etree.parse(str(schema)));xsd=validator.validate(etree.parse(str(f)))
   if not xsd:errors.extend(str(x) for x in validator.error_log)
  # Verify generated sequence connectors avoid the interior of unrelated node shapes.
  crosses=[]
  if not f.name.startswith(('00','07')):
   rectangles={}
   for id,sh in shapes.items():
    if id in by and local(by[id].tag) in KINDS and local(by[id].tag)!='boundaryEvent':
     v=sh.find('dc:Bounds',NS);rectangles[id]=tuple(float(v.get(k)) for k in ['x','y','width','height'])
   for ed in t.findall('.//bd:BPMNEdge',NS):
    flow=by[ed.get('bpmnElement')]
    if local(flow.tag)!='sequenceFlow':continue
    pts=[(float(w.get('x')),float(w.get('y'))) for w in ed.findall('di:waypoint',NS)]
    exclude={flow.get('sourceRef'),flow.get('targetRef')};src=by[flow.get('sourceRef')]
    if src.get('attachedToRef'):exclude.add(src.get('attachedToRef'))
    for a,b in zip(pts,pts[1:]):
     for id,(x,y,w,h) in rectangles.items():
      if id in exclude:continue
      hit=(abs(a[0]-b[0])<.1 and x+1<a[0]<x+w-1 and max(min(a[1],b[1]),y+1)<min(max(a[1],b[1]),y+h-1)) or (abs(a[1]-b[1])<.1 and y+1<a[1]<y+h-1 and max(min(a[0],b[0]),x+1)<min(max(a[0],b[0]),x+w-1))
      if hit:crosses.append([flow.get('id'),id])
   if crosses:errors.append('Conectores que atraviesan nodos ajenos: '+str(crosses))
  results.append({'file':f.name,'xsd_valid':xsd,'structural_errors':errors,'legacy_notes':sorted(set(notes)),'sequence_shape_crossings':crosses,'passed':not errors})
 return {'date':'2026-10-14','scope':'XML, referencias, ámbitos, carriles, DI, condiciones, rutas y geometría de conectores nuevos','files':results,'passed':all(x['passed'] for x in results)}

if __name__=='__main__':
 parser=argparse.ArgumentParser();parser.add_argument('--schema');a=parser.parse_args();root=Path(__file__).resolve().parents[1]
 result=validate(root,Path(a.schema) if a.schema else None)
 (root/'validacion/estructura-bpmn.json').write_text(json.dumps(result,ensure_ascii=False,indent=2))
 for x in result['files']:print(x['file'], 'PASS' if x['passed'] else 'FAIL',x['structural_errors'])
 raise SystemExit(0 if result['passed'] else 1)
