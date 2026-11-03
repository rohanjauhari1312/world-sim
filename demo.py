import json
import sys
import webbrowser

from worldsim.agents import Cruise, Lookahead
from worldsim.env import WorldEnv

HTML = """<!doctype html><meta charset=utf-8><title>World Sim</title>
<style>body{background:#111;color:#ddd;font:13px monospace;margin:20px}
.row{display:flex;gap:30px;flex-wrap:wrap}canvas{image-rendering:pixelated;width:480px;border:2px solid #444}
pre{margin:6px 0;height:150px}h3{margin:0 0 6px}button,input{margin:8px 6px 0 0}</style>
<h3>World Sim - seed SEED, same world, two agents</h3>
<div class=row><div><h3>Cruise (no investing)</h3><canvas id=c0 width=192 height=160></canvas><pre id=s0></pre></div>
<div><h3>Lookahead 40 (plans ahead)</h3><canvas id=c1 width=192 height=160></canvas><pre id=s1></pre></div></div>
<button id=pp>pause</button><input id=sl type=range min=0 max=100 value=0 style=width:400px><span id=tt></span>
<script>
const D=DATA,COL={farm:'#c8b43c',lumberyard:'#287832',mine:'#6e6e78',house:'#be5a46',school:'#465ac8',levee:'#3ca0c8'};
let t=+location.hash.slice(1)||0,play=!location.hash;
function draw(i,s){const c=document.getElementById('c'+i).getContext('2d');
c.fillStyle='rgb('+(150+60*s.fert|0)+',200,120)';c.fillRect(0,0,192,160);let n=0;
for(const k in s.b)for(let j=0;j<s.b[k];j++){if(n<24*18){c.fillStyle=COL[k];c.fillRect((n%24)*8+1,(n/24|0)*8+1,6,6);n++}}
c.fillStyle='#f0dcc8';for(let j=0;j<Math.min(s.pop/2|0,24);j++)c.fillRect(j*8+1,145,6,6);
c.fillStyle='#ffd700';for(let j=0;j<Math.min(s.gold/100|0,24);j++)c.fillRect(j*8+1,153,6,6);
document.getElementById('s'+i).textContent='turn '+s.t+'\\npop '+s.pop+'  happy '+s.happy+'\\ngold '+s.gold+'  debt '+s.debt+'\\nfood '+s.food+' wood '+s.wood+' ore '+s.ore+'\\nscore '+s.score+(s.out!='running'?'  ['+s.out+']':'')+'\\n'+(s.ev||'');}
function show(){for(let i=0;i<2;i++)draw(i,D[i][Math.min(t,D[i].length-1)]);document.getElementById('sl').value=t;document.getElementById('tt').textContent='turn '+t}
setInterval(()=>{if(play&&t<100){t++;show()}},150);
document.getElementById('pp').onclick=e=>{play=!play;e.target.textContent=play?'pause':'play'};
document.getElementById('sl').oninput=e=>{t=+e.target.value;show()};show();
</script>"""


def snap(env):
    w = env.w
    return dict(t=w.t, pop=round(w.pop), happy=round(w.happy, 2), gold=round(w.gold), debt=round(w.debt),
                food=round(w.stock["food"]), wood=round(w.stock["wood"]), ore=round(w.stock["ore"]),
                score=round(env.score()), b=dict(w.b), fert=w.fert, out=w.outcome,
                ev=", ".join(e.split(":")[0] for e in env.last_events))


def episode(seed, agent):
    env = WorldEnv(seed)
    frames = [snap(env)]
    while not env.done:
        agent.act(env)
        env.call("end_turn")
        frames.append(snap(env))
    return frames


if __name__ == "__main__":
    seed = int(sys.argv[1]) if len(sys.argv) > 1 else 10000
    data = [episode(seed, Cruise()), episode(seed, Lookahead(40))]
    with open("results/demo.html", "w") as f:
        f.write(HTML.replace("DATA", json.dumps(data)).replace("SEED", str(seed)))
    webbrowser.open("file://" + __import__("os").path.abspath("results/demo.html"))
