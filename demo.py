import json
import os
import sys
import webbrowser

from worldsim.agents import Cruise, Lookahead
from worldsim.env import WorldEnv
from worldsim.terrain import N

HTML = """<!doctype html><meta charset=utf-8><title>World Sim</title>
<style>body{background:#111;color:#ddd;font:13px monospace;margin:20px}
.row{display:flex;gap:30px;flex-wrap:wrap}canvas{image-rendering:pixelated;width:512px;border:2px solid #444}
pre{margin:6px 0;height:110px}h3{margin:0 0 6px}button,input{margin:8px 6px 0 0}</style>
<h3>World Sim - seed SEED, same terrain, two agents</h3>
<div class=row><div><h3>Cruise (never invests)</h3><canvas id=c0 width=256 height=256></canvas><pre id=s0></pre></div>
<div><h3>Lookahead 40 (plans ahead)</h3><canvas id=c1 width=256 height=256></canvas><pre id=s1></pre></div></div>
<div>houses red, farms yellow, lumber green, mines grey, school blue, levee cyan, roads tan, town white</div>
<button id=pp>pause</button><input id=sl type=range min=0 max=100 value=0 style=width:400px><span id=tt></span>
<script>
const D=DATA,M=MAP,N=16,S=16;
const COL={farm:'#e6c828',lumberyard:'#1e7a2d',mine:'#7a7a86',house:'#d2503c',school:'#4a5ae0',levee:'#38c8e8'};
let t=+location.hash.slice(1)||0,play=!location.hash;
function base(c){for(let y=0;y<N;y++)for(let x=0;x<N;x++){const i=y*N+x,h=M.h[i];let col;
if(M.water[i])col='#2a5d9a';else if(M.river[i])col=M.ford[i]?'#6fa8dc':'#3c7fc0';
else{const g=Math.round(110+h*90),r=Math.round(70+h*110),b=Math.round(60+h*70);col='rgb('+r+','+g+','+b+')'}
c.fillStyle=col;c.fillRect(x*S,y*S,S,S);
if(!M.water[i]&&!M.river[i]){if(M.forest[i]>0.5){c.fillStyle='rgba(20,70,30,.55)';c.fillRect(x*S+3,y*S+3,10,10)}
if(M.ore[i]>5){c.fillStyle='rgba(30,30,30,.6)';c.fillRect(x*S+6,y*S+6,4,4)}}}}
function draw(i,s){const c=document.getElementById('c'+i).getContext('2d');base(c);
for(const r of s.roads){c.fillStyle='#e8d9a0';c.fillRect(r[0]*S+5,r[1]*S+5,6,6)}
for(const b of s.tiles){c.fillStyle=COL[b[2]];c.fillRect(b[0]*S+2,b[1]*S+2,12,12)}
c.fillStyle='#fff';c.fillRect(M.town[0]*S+2,M.town[1]*S+2,12,12);
document.getElementById('s'+i).textContent='turn '+s.t+'\\npop '+s.pop+'  happy '+s.happy+'\\ngold '+s.gold+'  debt '+s.debt+'\\nfood '+s.food+' wood '+s.wood+' ore '+s.ore+'  roads '+s.roads.length+'\\nscore '+s.score+(s.out!='running'?'  ['+s.out+']':'')+'\\n'+(s.ev||'');}
function show(){for(let i=0;i<2;i++)draw(i,D[i][Math.min(t,D[i].length-1)]);document.getElementById('sl').value=t;document.getElementById('tt').textContent='turn '+t}
setInterval(()=>{if(play&&t<100){t++;show()}},150);
document.getElementById('pp').onclick=e=>{play=!play;e.target.textContent=play?'pause':'play'};
document.getElementById('sl').oninput=e=>{t=+e.target.value;show()};show();
</script>"""


def snap(env):
    w = env.w
    return dict(t=w.t, pop=round(w.pop), happy=round(w.happy, 2), gold=round(w.gold), debt=round(w.debt),
                food=round(w.stock["food"]), wood=round(w.stock["wood"]), ore=round(w.stock["ore"]),
                score=round(env.score()), out=w.outcome, tiles=[[t[0], t[1], k] for t, k in w.tiles.items()],
                roads=[list(r) for r in w.roads], ev=", ".join(e.split(" (")[0].split(":")[0] for e in env.last_events))


def terrain_json(T):
    ts = [(x, y) for y in range(N) for x in range(N)]
    return dict(h=[round(T.h[t], 3) for t in ts], water=[int(t in T.water) for t in ts],
                river=[int(t in T.river) for t in ts], ford=[int(t in T.ford) for t in ts],
                forest=[round(T.forest[t], 2) for t in ts], ore=[round(T.ore0[t]) for t in ts], town=list(T.town))


def episode(seed, agent):
    env = WorldEnv(seed)
    frames = [snap(env)]
    while not env.done:
        agent.act(env)
        env.call("end_turn")
        frames.append(snap(env))
    return frames, env.w.T


if __name__ == "__main__":
    seed = int(sys.argv[1]) if len(sys.argv) > 1 else 10000
    (f0, T), (f1, _) = episode(seed, Cruise()), episode(seed, Lookahead(40))
    html = HTML.replace("DATA", json.dumps([f0, f1])).replace("MAP", json.dumps(terrain_json(T))).replace("SEED", str(seed))
    with open("results/demo.html", "w") as f:
        f.write(html)
    if "--no-open" not in sys.argv:
        webbrowser.open("file://" + os.path.abspath("results/demo.html"))
