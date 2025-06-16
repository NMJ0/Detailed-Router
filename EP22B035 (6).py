# -*- coding: utf-8 -*-
"""
Created on Wed May 21 10:48:44 2025

@author: noelm
"""
def detailed_route(input_def,input_lef,input_guide,ouptut_def):
  import requests
  import LEFDEFParser
  from LEFDEFParser import Rect
  import math
  import heapq as hq
  import time



  with open(input_guide, 'r') as f:
    lines = f.read().splitlines()
  #response =input_guide
  #lines = response.text.splitlines()
  global_route={}
  n=len(lines)
  m=0
  while True:
    if m>=n-1:
      break
    name=lines[m]
    global_route[name]=[]
    m+=1
    while True:
      if lines[m]==')':
        m+=1
        break
      if lines[m]=='(':
        m+=1
      x1,y1,x2,y2,layer=map(str,lines[m].split())
      global_route[name].append([layer,[int(x1),int(y1),int(x2),int(y2)]])
      m+=1
  skipCells = {"sky130_fd_sc_hd__decap_3", "sky130_fd_sc_hd__decap_4", "sky130_fd_sc_hd__decap_6", "sky130_fd_sc_hd__decap_8",\
              "sky130_fd_sc_hd__decap_12", "sky130_fd_sc_hd__fill_1", "sky130_fd_sc_hd__fill_2", "sky130_fd_sc_hd__fill_4",
              "sky130_fd_sc_hd__fill_8", "sky130_fd_sc_hd__lpflow_decapkapwr_3", "sky130_fd_sc_hd__lpflow_decapkapwr_4",\
              "sky130_fd_sc_hd__lpflow_decapkapwr_6", "sky130_fd_sc_hd__lpflow_decapkapwr_8", "sky130_fd_sc_hd__lpflow_decapkapwr_12", \
              "sky130_fd_sc_hd__lpflow_lsbuf_lh_hl_isowell_tap_1", "sky130_fd_sc_hd__lpflow_lsbuf_lh_hl_isowell_tap_2", \
              "sky130_fd_sc_hd__lpflow_lsbuf_lh_hl_isowell_tap_4", "sky130_fd_sc_hd__lpflow_lsbuf_lh_isowell_tap_1", \
              "sky130_fd_sc_hd__lpflow_lsbuf_lh_isowell_tap_2", "sky130_fd_sc_hd__lpflow_lsbuf_lh_isowell_tap_4", "sky130_fd_sc_hd__tap_1", \
              "sky130_fd_sc_hd__tap_2", "sky130_fd_sc_hd__tapvgnd2_1", "sky130_fd_sc_hd__tapvgnd_1", \
              "sky130_fd_sc_hd__tapvpwrvgnd_1", "sky130_ef_sc_hd__decap_12"}

  layerColors = { 'li1': 'red', 'met1': 'blue', 'met2': 'green', 'met3': 'orange', 'met4': 'magenta', 'met5': 'cyan' }


  # skip power/ground/clock nets
  skipNets = {'clk', 'VPWR', 'VGND'}
  l = LEFDEFParser.LEFReader()
  leffile=input_lef
  l.readLEF(leffile)
  d = LEFDEFParser.DEFReader()
  deffile=input_def
  d.readDEF(deffile)
  macros={}
  for i in l.macros():
    macros[i.name()]=i
  cells={}
  for i in d.components():
    cells[i]=i.macro()
  nets={}
  for i in d.nets():
    nets[i.name()]=i.pins()
  layerWidth = {}
  layerSpacing = {}
  for layer in l.layers():
      layerWidth[layer.name()] = layer.width()
      layerSpacing[layer.name()] = layer.pitch() - layer.width()
  tracks=d.tracks()
  tracks_ = {
      'li1':  [tracks['li1'][0].x,  tracks['li1'][0].num,  tracks['li1'][0].step],
      'met1': [tracks['met1'][1].x, tracks['met1'][1].num, tracks['met1'][1].step],
      'met2': [tracks['met2'][0].x, tracks['met2'][0].num, tracks['met2'][0].step],
      'met3': [tracks['met3'][1].x, tracks['met3'][1].num, tracks['met3'][1].step],
      'met4': [tracks['met4'][0].x, tracks['met4'][0].num, tracks['met4'][0].step],
      'met5': [tracks['met5'][1].x, tracks['met5'][1].num, tracks['met5'][1].step],
  }
  def bloat(r, s):
    return Rect(r.ll.x - s, r.ll.y - s, r.ur.x + s, r.ur.y + s)
  class Inst:
    def __init__(self, comp, macro):
      self._comp = comp
      self._macro = macro
      origin = comp.location()
      self._bbox = Rect(origin.x, origin.y, origin.x + macro.xdim(), origin.y + macro.ydim())
      self._pins = dict()
      self._obsts = dict()
      for p in macro.pins():
        shapes = dict()
        for port in p.ports():
          for layer, rects in port.items():
            if layer not in layerColors: continue
            if layer not in shapes: shapes[layer] = list()
            for v in rects:
              r = Rect(v.ll.x, v.ll.y, v.ur.x, v.ur.y)
              r.transform(comp.orient(), origin, macro.xdim(), macro.ydim())
              shapes[layer].append(r)
        self._pins[p.name()] = shapes

      for layer, rects in macro.obstructions().items():
        if layer not in layerColors: continue
        if layer not in self._obsts: self._obsts[layer] = list()
        for v in rects:
          r = Rect(v.ll.x, v.ll.y, v.ur.x, v.ur.y)
          s=layerSpacing[layer]
          
          r.transform(comp.orient(), origin, macro.xdim(), macro.ydim())
          r=bloat(r,1*s//2)
          self._obsts[layer].append(r)
  cell_pin={}
  obstructions={'li1':set(),'met1':set(),'met2':set(),'met3':set(),'met4':set(),'met5':set()}
  for r in cells.keys():
    inst=Inst(r,macros[cells[r]])
    for j in inst._obsts.keys():
      obstructions[j].update(inst._obsts[j])
    for i in inst._pins.keys():
      for k in inst._pins[i].keys():
        
        obstructions[k].update(inst._pins[i][k])
        pass
      if len(inst._pins[i])==0:
        continue
      cell_pin[(inst._comp.name(),i)]=inst._pins[i]
  #print(cell_pin)
  #print(obstructions)
  b_pins={}
  for i in d.pins():
    b_pins['PIN',i.name()]=i.ports()[0]

  for i in b_pins:
    cell_pin[i]=b_pins[i]
    for j in b_pins[i].keys():
      obstructions[j].update(b_pins[i][j])
      pass
  #print(cell_pin)
  #print(obstructions)
  nets_2={}
  for i in nets.keys():
    if i in skipNets:
      continue
    nets_2[i]=[]
    for j in nets[i]:
      nets_2[i].append(cell_pin[j])
  #print(nets_2)
  def inter_section(r1,r2,adjLayer):
    layer1=r1[0]
    layer2=r2[0]
    if layer2 not in adjLayer[layer1]:
      return None
    x1 = max(r1[1][0], r2[1][0])
    y1 = max(r1[1][1], r2[1][1])
    x2 = min(r1[1][2], r2[1][2])
    y2 = min(r1[1][3], r2[1][3])
    if x1 <= x2 and y1 <= y2:
      return [layer1, layer2, (x1, y1, x2, y2)]
    else :
      return None

  from collections import defaultdict

  def convert_graph(graph):
      result = {}
      order = ['li1', 'met1', 'met2', 'met3', 'met4', 'met5']
      
      for layer in order:
          layer_entries = [(x, y) for (lname, (x, y)) in graph if lname == layer]
          
          if not layer_entries:
              continue
          
          use_x_as_key = (order.index(layer) % 2 == 0)  # even index: use x as key, odd index: use y as key
          layer_dict = defaultdict(set)
          
          for x, y in layer_entries:
              key, value = (x, y) if use_x_as_key else (y, x)
              layer_dict[key].add(value)
          
          # Optionally remove duplicates and sort
          result[layer] = {k: sorted(set(v)) for k, v in layer_dict.items()}
      
      return result
  from itertools import product

  def cross_xy(layer, x_list, y_list):
      return [(layer, (x, y)) for x, y in product(x_list, y_list)]
  def net_to_graph(net,global_solution,obstructions):
    layerOrient = { 'li1': 'VERTICAL', 'met1': 'HORIZONTAL', 'met2': 'VERTICAL', 'met3': 'HORIZONTAL', 'met4': 'VERTICAL', 'met5': 'HORIZONTAL' }
    adjLayer = {
    'li1':  ['met1'],
    'met1': ['li1',  'met2'],
    'met2': ['met1', 'met3'],
    'met3': ['met2', 'met4'],
    'met4': ['met3', 'met5'],
    'met5': ['met4']
    }
    graph=[]
    edges=[]
    weights={}
    
    for i in global_solution:
      layer,x1,y1,x2,y2=i[0],i[1][0],i[1][1],i[1][2],i[1][3]
      a=tracks_[layer][-1]
      
      if layerOrient[layer]=='VERTICAL':
        n=tracks_[layer][2]
        x1-=tracks_[layer][0]
        x2-=tracks_[layer][0]
        start = ((x1 + n - 1) // n) * n
        lx=[i+tracks_[layer][0] for i in range(start, x2 + 1, n)]
        ly=[]

        for j in adjLayer[layer]:
          n=tracks_[j][2]
          y1-=tracks_[j][0]
          y2-=tracks_[j][0]
          start = ((y1 + n - 1) // n) * n

          ly=[i+tracks_[j][0] for i in range(start, y2 + 1, n)]
          graph.extend(cross_xy(layer, lx, ly))
          
          

      else:
        n=tracks_[layer][2]
        y1-=tracks_[layer][0]
        y2-=tracks_[layer][0]
        start = ((y1 + n - 1) // n) * n
        ly=[i+tracks_[layer][0] for i in range(start, y2 + 1, n)]
        lx=[]
        for j in adjLayer[layer]:
          n=tracks_[j][2]
          x1-=tracks_[j][0]
          x2-=tracks_[j][0]
          start = ((x1 + n - 1) // n) * n
          lx=[i+tracks_[j][0] for i in range(start, x2 + 1, n)]
          graph.extend(cross_xy(layer, lx, ly))
          
    
    graph_new = []
    seen = set()
    for i in graph:
      if i not in seen:
          graph_new.append(i)
          seen.add(i)

    
    graph=graph_new
    
    graph_dict=convert_graph(graph)
    
    for q in range(len(graph)):
      layer=graph[q][0]
      if layerOrient[layer]=='VERTICAL':
        x1=graph[q][1][0]
        y1=graph[q][1][1]
        for y2 in graph_dict[layer][x1]:
          if y2==y1:
            continue
          if abs(y1-y2)<=1.5*tracks_[layer][-1]:
                edges.append(((layer,(x1,y1)),(layer,(x1,y2))))
      else:
        x1=graph[q][1][0]
        y1=graph[q][1][1]
        for x2 in graph_dict[layer][y1]:
          if x2==x1:
            continue
          if abs(x1-x2)<=1.5*tracks_[layer][-1]:
                edges.append(((layer,(x1,y1)),(layer,(x2,y1))))
          
      

      
    
    for i in edges:

      weights[i]=1
    #print(weights)


    for i in range(len(global_solution)):
      for j in range(i+1,len(global_solution)):
        intersection=inter_section(global_solution[i],global_solution[j],adjLayer)
        if intersection!=None:
          layer1=intersection[0]
          layer2=intersection[1]
          x1=intersection[2][0]
          y1=intersection[2][1]
          x2=intersection[2][2]
          y2=intersection[2][3]
          g1= graph_dict[layer1]
          #g2= graph_dict[layer2]
          if layerOrient[layer1]=='VERTICAL':
            for x in g1.keys():
              if x1<=x<=x2:

                for y in g1[x]:
                  if  y1<=y<=y2:
                    edges.append(((layer1,(x,y)),(layer2,(x,y))))
                    weights[((layer1,(x,y)),(layer2,(x,y)))]=3
          else:
            for y in g1.keys():
              if y1<=y<=y2:

                for x in g1[y]:
                  if x1<=x<=x2 :
                    edges.append(((layer1,(x,y)),(layer2,(x,y))))
                    weights[((layer1,(x,y)),(layer2,(x,y)))]=3
          
    
    obs=set()
    for i in obstructions.keys():
      layer=i
      if layer in graph_dict.keys():
        g1_=graph_dict[layer]
      else:
        continue
      
      for j in obstructions[i]:
        x1=j.ll.x
        y1=j.ll.y
        x2=j.ur.x
        y2=j.ur.y
        
        if layerOrient[layer]=='VERTICAL':
          for x in g1_.keys():
            if x1<=x<=x2:

              for y in g1_[x]:
                if  y1<=y<=y2:
                  obs.add((layer,(x,y)))
        else:
          for y in g1_.keys():
            if y1<=y<=y2:

              for x in g1_[y]:
                if x1<=x<=x2 :
                  obs.add((layer,(x,y)))
        


    s_t=[]
    for i in net:
      p=[]
      for j in i.keys():
        layer=j
        for k in i[j]:
          x1=k.ll.x
          y1=k.ll.y
          x2=k.ur.x
          y2=k.ur.y
          g3=graph_dict[layer]
          if layerOrient[layer]=='VERTICAL':
            for x in g3.keys():
              if x1<=x<=x2:

                for y in g3[x]:
                  if  y1<=y<=y2:
                    p.append((layer,(x,y)))
                    node=(layer,(x,y))
                    if node in obs:
                      obs.remove(node)
          else:
            for y in g3.keys():
              if y1<=y<=y2:

                for x in g3[y]:
                  if x1<=x<=x2 :
                    p.append((layer,(x,y)))
                    node=(layer,(x,y))
                    if node in obs:
                      obs.remove(node)
          

        for h in range(len(p)):
          for k in range(h+1,len(p)):

            edges.append((p[h],p[k]))
            weights[(p[h],p[k])]=0
      if len(p)==0:
        continue
      s_t.append(p[0])

    edges=weights.keys()
    
    nodes = set()
    for u, v in edges:
      nodes.add(u)
      nodes.add(v)
    graph = list(nodes)
    
    
    adj = {v: [] for v in graph}
    for (u, v) in edges:
      adj[u].append(v)
      adj[v].append(u)
    

    return graph,weights,obs,s_t,adj

  class Vertex:
    def __init__(self, node, cost=math.inf, parent=None, nbrs=None):
      self._node=node
      self._xy = node[1]

      self._g=0
      self._h=0
      self._cost = self._g+self._h
      self._parent = parent
      self._nbrs = nbrs
    def __lt__(self, r):
      return self._cost < r._cost
    def __eq__(self, r):
      return self._node == r._node
    def __repr__(self):
      return f'(xy:{self._node}, cost:{self._cost})'
  class priority_queue:
    def __init__(self, vertices = []):
      self._vertices = vertices[:]
      self._q = vertices[:]
      hq.heapify(self._q)
    def push(self, v):
      hq.heappush(self._q, v)
    def pop(self):
      return(hq.heappop(self._q))
    def update(self, v, cost):
      try: i = self._q.index(v)
      except ValueError: i = None
      if i is not None:
        self._q[i]._cost = cost
        hq.heapify(self._q)
    def updateIndex(self, i, cost):
      assert i < len(self._q)
      self._vertices[i]._cost = cost
      hq.heapify(self._q)
    def empty(self):
      return len(self._q) == 0
    def __contains__(self, v):
      return v in self._q
    def __repr__(self):
      return str(self._q)
  def dist(u, v):
    return abs(u._xy[0] - v._xy[0]) + abs(u._xy[1] - v._xy[1])
  def astar(V, s, t,obs,weights):
    for v in V:
      
      v._g,v._h, v._parent,v._cost = math.inf,dist(v,t), None,math.inf
    for v in obs:
      v=V[v]
      v._g,v._h, v._parent,v._cost = math.inf,10*dist(v,t), None,math.inf


    s._g = 0
    s._h= dist(s,t)
    s._cost= s._g + s._h

    Q = priority_queue(V)
    while not Q.empty():
      u = Q.pop()
      #print(u)
      if u == t: break
      for v in u._nbrs:
        v=V[v]
        
        if u == v: # Check if neighbor is the current node

          w = 0      
        else:
          try :
            
            w=weights[(u._node,v._node)]
          except :
            
            w=weights[(v._node,u._node)]
        if v._g > u._g + w:
          v._g = u._g + w
          v._parent = u
          if v in Q:
            Q.update(v, v._g + v._h)
          else:
            Q.push(v)
    path = [t]
    while path[-1]._parent is not None:
      path.append(path[-1]._parent)
    return path

  net_name={}
  for i in d.nets():
    net_name[i.name()]=i
  time_g=0
  time_a=0
  for i in nets_2.keys():
    layerOrient = { 'li1': 'VERTICAL', 'met1': 'HORIZONTAL', 'met2': 'VERTICAL', 'met3': 'HORIZONTAL', 'met4': 'VERTICAL', 'met5': 'HORIZONTAL' }
    net=nets_2[i]
    name=i
    global_solution=global_route[i]
    m=time.time()
    graph,weights,obs,s_t,adj=net_to_graph(net,global_solution,obstructions)
    time_g+=time.time()-m
    indx={}

    vertices=[Vertex(j) for j in graph]
    index={}
    for j in range(len(vertices)):
      index[vertices[j]._node]=j
    for j in vertices:
      j._nbrs=set()
      for k in adj[j._node]:
        j._nbrs.add(index[k])
    obst=set()
    for j in obs:
      obst.add(index[j])
    obs=obst
    source=vertices[index[s_t[0]]]
    #print(s_t)
    new_obs=[]
    for j in range(1,len(s_t)):
      target=vertices[index[s_t[j]]]
      m=time.time()
      path=astar(vertices,source,target,obs,weights)
      time_a+=time.time()-m
      current_net=net_name[name]
      for k in range(len(path)-1):
        layer=path[k]._node[0]
        x=path[k]._xy[0]
        y=path[k]._xy[1]
        layer_=path[k+1]._node[0]
        x_=path[k+1]._xy[0]
        y_=path[k+1]._xy[1]
        if layer !=layer_:
            w=layerWidth[layer]
            r=Rect(x-w//2,y-w//2,x+w//2,y+w//2)
            s=layerSpacing[layer]
            r=bloat(r,s//2)
            obstructions[layer].add(r)
          
            current_net.addRect(layer,x-w//2,y-w//2,x+w//2,y+w//2)
            w=layerWidth[layer_]
            r=Rect(x_-w//2,y_-w//2,x_+w//2,y_+w//2)
            s=layerSpacing[layer_]
            r=bloat(r,s//2)
            obstructions[layer_].add(r)
            current_net.addRect(layer_,x_-w//2,y_-w//2,x_+w//2,y_+w//2)
            
        if layer==layer_:
          width=layerWidth[layer]
          if layerOrient[layer]=='VERTICAL':
            y1=min(y,y_)
            y2=max(y,y_)
            if x==x_:
              r=Rect(x-width//2,y1,x_+width//2,y2)
              s=layerSpacing[layer]
              r=bloat(r,1*s//2)
              obstructions[layer].add(r)
              new_obs.append(r)

              current_net.addRect(layer,x-width//2,y1,x_+width//2,y2)
          else:
            x1=min(x,x_)
            x2=max(x,x_)
            if y==y_:
              r=Rect(x1,y-width//2,x2,y_+width//2)
              s=layerSpacing[layer]
              r=bloat(r,1*s//2)
              obstructions[layer].add(r)
              new_obs.append(r)
              current_net.addRect(layer,x1,y-width//2,x2,y_+width//2)
          
      #obstructions.extend(new_obs)


      print(name)
      print(path)
  d.writeDEF(ouptut_def)




