import React from 'react';
import { AbsoluteFill, useCurrentFrame, useVideoConfig, spring, interpolate } from 'remotion';
import { z } from 'zod';
import { CLAUDE, CLAUDE_FONT } from '../tokens/claude';
import { WORLD_A, WORLD_B } from './WorldSimData';

/**
 * WorldSim — figures for "Plan Ahead." (claude-liam, fellow reel by Rohan Jauhari)
 * Source: world-sim/ (github.com/rohanjauhari1312/world-sim), README.md and results/*.json.
 *
 * Every number on screen is measured:
 *   200 unseen worlds, 100 turns, mean score   never invests 1247 · greedy 1835 · 4 ahead 2409 ·
 *                                              10 ahead 2637 · 20 ahead 2705 · 40 ahead 2847
 *   seed 10003, one run each                   never invests 1027 · plans 40 ahead 5496
 *   Same 3 worlds, 20 turns (seeds 10000-10002) Gemma-2-9B-it 533 · greedy 854 · never invests 951 ·
 *                                              10 ahead 1158 · 20 ahead 1214
 * Terracotta moment per beat is named in each component's header.
 */

const SERIF = CLAUDE_FONT.serif;
const SANS = CLAUDE_FONT.ui;
const MONO = CLAUDE_FONT.mono;
const clamp = (v: number, a: number, b: number) => Math.min(b, Math.max(a, v));
const ease = { damping: 30, stiffness: 110, mass: 0.8 };
const grow = { damping: 26, stiffness: 80, mass: 1.0 };
const N = 16;

const Frame: React.FC<{ eyebrow: string; title: string; sparkLine?: string; children: React.ReactNode }> = ({
  eyebrow, title, sparkLine, children,
}) => {
  const frame = useCurrentFrame();
  const { fps, width, height } = useVideoConfig();
  const U = Math.min(width, height);
  const inAnim = spring({ frame, fps, config: ease });
  const sparkIn = spring({ frame: frame - 50, fps, config: ease });
  const PAD_X = width * 0.075;
  return (
    <AbsoluteFill style={{ background: CLAUDE.PAGE, overflow: 'hidden' }}>
      <div style={{
        position: 'absolute', left: PAD_X, top: height * 0.075, fontFamily: SANS, fontSize: U * 0.021,
        fontWeight: 700, letterSpacing: 3.2, textTransform: 'uppercase' as const, lineHeight: 1.5,
        color: CLAUDE.INK_SOFT, opacity: clamp(inAnim, 0, 1), maxWidth: width - PAD_X * 2,
      }}>{eyebrow}</div>
      <div style={{
        position: 'absolute', left: PAD_X, top: height * 0.115, fontFamily: SERIF, fontSize: U * 0.052,
        fontWeight: 600, color: CLAUDE.INK, letterSpacing: '-0.015em', lineHeight: 1.1,
        opacity: clamp(inAnim, 0, 1), transform: `translateY(${(1 - inAnim) * 12}px)`, maxWidth: width * 0.84,
      }}>{title}</div>
      {children}
      {sparkLine ? (
        <div style={{
          position: 'absolute', left: PAD_X, bottom: height * 0.062, display: 'flex', alignItems: 'baseline',
          gap: width * 0.011, opacity: clamp(sparkIn, 0, 1), transform: `translateY(${(1 - sparkIn) * 8}px)`,
        }}>
          <span style={{ fontFamily: SERIF, fontSize: U * 0.036, color: CLAUDE.SPARK }}>✳</span>
          <span style={{ fontFamily: SERIF, fontSize: U * 0.032, color: CLAUDE.INK }}>{sparkLine}</span>
        </div>
      ) : null}
    </AbsoluteFill>
  );
};

type WorldData = typeof WORLD_A | typeof WORLD_B;
type Build = readonly [number, number, string];
const GLYPH: Record<string, string> = { farm: 'F', lumberyard: 'L', mine: 'M', house: 'H', school: 'S', levee: 'V' };

/** The terrain: land shaded by height, water hatched, river as a line, forest and ore marked. */
const TerrainMap: React.FC<{
  w: WorldData; x: number; y: number; size: number; reveal: number;
  tiles?: readonly Build[]; roads?: readonly (readonly number[])[]; tileProgress?: number; showTown?: boolean;
}> = ({ w, x, y, size, reveal, tiles = [], roads = [], tileProgress = 1, showTown = true }) => {
  const c = size / N;
  const rows = reveal * N;
  const cells: React.ReactNode[] = [];
  for (let j = 0; j < N; j++) {
    for (let i = 0; i < N; i++) {
      const k = j * N + i;
      const op = clamp(rows - j, 0, 1);
      if (op <= 0) continue;
      const h = w.h[k];
      const land = w.water[k] ? '#85806D' : w.river[k] ? '#85806D' : `rgb(${Math.round(204 - h * 52)},${Math.round(198 - h * 54)},${Math.round(176 - h * 58)})`;
      cells.push(
        <g key={k} opacity={op}>
          <rect x={x + i * c} y={y + j * c} width={c + 0.5} height={c + 0.5} fill={land} />
          {w.water[k] ? (
            <path d={`M${x + i * c + c * 0.15},${y + j * c + c * 0.35} h${c * 0.7} M${x + i * c + c * 0.15},${y + j * c + c * 0.65} h${c * 0.7}`}
              stroke={CLAUDE.INK} strokeWidth={c * 0.06} opacity={0.85} />
          ) : null}
          {w.river[k] ? (
            <rect x={x + i * c + c * 0.1} y={y + j * c + c * 0.1} width={c * 0.8} height={c * 0.8}
              fill={w.ford[k] ? 'none' : CLAUDE.INK} stroke={CLAUDE.INK} strokeWidth={c * 0.08}
              strokeDasharray={w.ford[k] ? `${c * 0.12} ${c * 0.1}` : undefined} opacity={0.9} />
          ) : null}
          {!w.water[k] && !w.river[k] && w.forest[k] > 0.5 ? (
            <rect x={x + i * c + c * 0.3} y={y + j * c + c * 0.3} width={c * 0.4} height={c * 0.4} fill={CLAUDE.INK_SOFT} opacity={0.9} />
          ) : null}
          {w.ore[k] > 5 ? <circle cx={x + i * c + c / 2} cy={y + j * c + c / 2} r={c * 0.2} fill={CLAUDE.INK} /> : null}
        </g>,
      );
    }
  }
  const nT = tiles.length * clamp(tileProgress, 0, 1);
  return (
    <svg style={{ position: 'absolute', left: 0, top: 0 }} width="100%" height="100%">
      {cells}
      <rect x={x} y={y} width={size} height={size} fill="none" stroke={CLAUDE.BORDER} strokeWidth={2} />
      {roads.map((r, n) => (n < roads.length * clamp(tileProgress, 0, 1) ? (
        <rect key={'r' + n} x={x + r[0] * c + c * 0.28} y={y + r[1] * c + c * 0.28} width={c * 0.44} height={c * 0.44}
          fill={CLAUDE.SPARK} />
      ) : null))}
      {tiles.map((t, n) => (n < nT ? (
        <g key={'b' + n}>
          <rect x={x + t[0] * c + c * 0.12} y={y + t[1] * c + c * 0.12} width={c * 0.76} height={c * 0.76} fill={CLAUDE.INK} />
          <text x={x + t[0] * c + c / 2} y={y + t[1] * c + c * 0.68} textAnchor="middle" fontFamily={MONO}
            fontSize={c * 0.5} fontWeight={700} fill={CLAUDE.PAGE}>{GLYPH[t[2]]}</text>
        </g>
      ) : null))}
      {showTown && reveal > 0.95 ? (
        <g>
          <circle cx={x + w.town[0] * c + c / 2} cy={y + w.town[1] * c + c / 2} r={c * 0.46} fill={CLAUDE.PAGE} stroke={CLAUDE.INK} strokeWidth={c * 0.08} />
          <text x={x + w.town[0] * c + c / 2} y={y + w.town[1] * c + c * 0.7} textAnchor="middle" fontFamily={SERIF}
            fontSize={c * 0.6} fontWeight={700} fill={CLAUDE.INK}>T</text>
        </g>
      ) : null}
    </svg>
  );
};

const Note: React.FC<{ left: number; top: number; width: number; a: number; head: string; body: string; accent?: boolean }> = ({
  left, top, width, a, head, body, accent,
}) => {
  const { width: W, height: H } = useVideoConfig();
  const U = Math.min(W, H);
  return (
    <div style={{ position: 'absolute', left, top, width, opacity: clamp(a, 0, 1), transform: `translateY(${(1 - clamp(a, 0, 1)) * 10}px)` }}>
      <div style={{ fontFamily: SANS, fontSize: U * 0.021, fontWeight: 700, letterSpacing: 2.4, textTransform: 'uppercase' as const,
        color: accent ? CLAUDE.SPARK : CLAUDE.INK_SOFT, marginBottom: U * 0.008 }}>{head}</div>
      <div style={{ fontFamily: SERIF, fontSize: U * 0.036, lineHeight: 1.25, color: CLAUDE.INK, whiteSpace: 'pre-line' as const }}>{body}</div>
    </div>
  );
};

/* ───────────────────── B01 / B02 — the land, and the path across it ───────────── */
/** Terracotta moment: phase "terrain" the town; phase "path" the cheapest route. */

export const worldTerrainSchema = z.object({
  phase: z.enum(['terrain', 'path']).default('terrain'),
  sparkLine: z.string().default('A new seed, a new land.'),
});
export type WorldTerrainProps = z.infer<typeof worldTerrainSchema>;

export const WorldTerrain: React.FC<WorldTerrainProps> = ({ phase, sparkLine }) => {
  const frame = useCurrentFrame();
  const { fps, width, height } = useVideoConfig();
  const U = Math.min(width, height);
  const PAD_X = width * 0.075;
  const SIZE = height * 0.6;
  const MX = PAD_X, MY = height * 0.235;
  const TX = MX + SIZE + width * 0.06;
  const TW = width - TX - PAD_X;
  const w = phase === 'terrain' ? WORLD_B : WORLD_A;
  const reveal = clamp(interpolate(frame, [8, 95], [0, 1]), 0, 1);
  const draw = clamp(interpolate(frame, [70, 190], [0, 1]), 0, 1);
  const aN = (d: number) => spring({ frame: frame - d, fps, config: ease });
  const A = WORLD_A;
  const c = SIZE / N;

  return (
    <Frame
      eyebrow={phase === 'terrain' ? 'WORLD SIM · EVERY TOWN GETS ITS OWN LAND' : 'WORLD SIM · WHERE YOU BUILD MATTERS'}
      title={phase === 'terrain' ? 'Hills, a river, ore. Never the same twice.' : 'The cheapest route is rarely the straight one'}
      sparkLine={sparkLine}
    >
      <TerrainMap w={w} x={MX} y={MY} size={SIZE} reveal={reveal} showTown />
      {phase === 'path' ? (
        <svg style={{ position: 'absolute', left: 0, top: 0 }} width="100%" height="100%">
          <line x1={MX + A.src[0] * c + c / 2} y1={MY + A.src[1] * c + c / 2} x2={MX + A.town[0] * c + c / 2}
            y2={MY + A.town[1] * c + c / 2} stroke={CLAUDE.INK_SOFT} strokeWidth={3} strokeDasharray="10 9"
            opacity={clamp(aN(70), 0, 1)} />
          <polyline fill="none" stroke={CLAUDE.SPARK} strokeWidth={c * 0.3} strokeLinejoin="round" strokeLinecap="round"
            points={A.path.map((p) => `${MX + p[0] * c + c / 2},${MY + p[1] * c + c / 2}`).join(' ')}
            pathLength={1} strokeDasharray={1} strokeDashoffset={1 - draw} />
          <rect x={MX + A.src[0] * c + c * 0.1} y={MY + A.src[1] * c + c * 0.1} width={c * 0.8} height={c * 0.8} fill={CLAUDE.INK} />
          <text x={MX + A.src[0] * c + c / 2} y={MY + A.src[1] * c + c * 0.7} textAnchor="middle" fontFamily={MONO}
            fontSize={c * 0.5} fontWeight={700} fill={CLAUDE.PAGE}>M</text>
        </svg>
      ) : null}
      {phase === 'terrain' ? (
        <>
          <Note left={TX} top={MY} width={TW} a={aN(30)} head="Built from one seed" body={'16 by 16 tiles.\nNoisy hills, one ridge.'} />
          <Note left={TX} top={MY + height * 0.15} width={TW} a={aN(60)} head="Water" body={'A river with a few fords,\nand lakes that block the way.'} />
          <Note left={TX} top={MY + height * 0.30} width={TW} a={aN(90)} head="Resources" body={'Forest, farmland, and ore\nonly where the hills are.'} />
          <Note left={TX} top={MY + height * 0.45} width={TW} a={aN(120)} accent head="The town" body={'One market. Everything has to\nreach it.'} />
        </>
      ) : (
        <>
          <Note left={TX} top={MY} width={TW} a={aN(40)} head="On paper" body={'Mine to town: 9 tiles\nin a straight line.'} />
          <Note left={TX} top={MY + height * 0.15} width={TW} a={aN(110)} head="In practice" body={`Slopes, forest and water push the real\nroute to ${A.path.length - 1} tiles, cost ${A.cost}.`} accent />
          <Note left={TX} top={MY + height * 0.32} width={TW} a={aN(170)} head="Roads and bridges" body={'Cost money now and cut the cost\nof every trip after.'} />
        </>
      )}
    </Frame>
  );
};

/* ───────────────────────── B03 — the loop the agent runs ───────────────────────── */
/** Terracotta moment: the score at the end of 100 turns. */

export const worldLoopSchema = z.object({ sparkLine: z.string().default('See. Act. The world answers.') });
export type WorldLoopProps = z.infer<typeof worldLoopSchema>;

const LOOP = [
  { k: 'AGENT SEES', v: 'Stock, prices,\nhazards, and a\nmap of the land', mono: false },
  { k: 'AGENT DOES', v: 'tool: build\nbuilding: road\nx: 8   y: 6', mono: true },
  { k: 'WORLD ANSWERS', v: 'Prices follow\nits trades. Floods\nhit low ground.', mono: false },
];

export const WorldLoop: React.FC<WorldLoopProps> = ({ sparkLine }) => {
  const frame = useCurrentFrame();
  const { fps, width, height } = useVideoConfig();
  const U = Math.min(width, height);
  const PAD_X = width * 0.075;
  const GAP = width * 0.05;
  const BOX_W = (width - PAD_X * 2 - GAP * 2) / 3;
  const TOP = height * 0.26;
  const BOX_H = height * 0.31;
  const scoreIn = spring({ frame: frame - 70, fps, config: ease });
  return (
    <Frame eyebrow="THE GAME · ONE TURN, THEN 99 MORE" title="Observe, act, repeat for a hundred turns" sparkLine={sparkLine}>
      {LOOP.map((s, i) => {
        const a = spring({ frame: frame - 12 - i * 14, fps, config: ease });
        const left = PAD_X + i * (BOX_W + GAP);
        return (
          <React.Fragment key={s.k}>
            <div style={{
              position: 'absolute', left, top: TOP, width: BOX_W, height: BOX_H, background: CLAUDE.CARD,
              border: `2px solid ${CLAUDE.BORDER}`, borderRadius: 14, padding: U * 0.026, boxSizing: 'border-box' as const,
              opacity: clamp(a, 0, 1), transform: `translateY(${(1 - clamp(a, 0, 1)) * 14}px)`,
            }}>
              <div style={{ fontFamily: SANS, fontSize: U * 0.021, fontWeight: 700, letterSpacing: 2.4, color: CLAUDE.INK_SOFT, marginBottom: U * 0.016 }}>{s.k}</div>
              <div style={{ fontFamily: s.mono ? MONO : SERIF, fontSize: s.mono ? U * 0.04 : U * 0.046, lineHeight: 1.3, color: CLAUDE.INK, whiteSpace: 'pre-line' as const }}>{s.v}</div>
            </div>
            {i < 2 ? (
              <div style={{ position: 'absolute', left: left + BOX_W + GAP * 0.2, top: TOP + BOX_H / 2 - U * 0.03, width: GAP * 0.6,
                fontFamily: SERIF, fontSize: U * 0.06, color: CLAUDE.INK_SOFT, textAlign: 'center' as const, opacity: clamp(a, 0, 1) }}>→</div>
            ) : null}
          </React.Fragment>
        );
      })}
      <div style={{
        position: 'absolute', left: PAD_X, top: TOP + BOX_H + height * 0.06, right: PAD_X,
        borderTop: `2px solid ${CLAUDE.SPARK}`, paddingTop: U * 0.02, opacity: clamp(scoreIn, 0, 1),
        transform: `translateY(${(1 - clamp(scoreIn, 0, 1)) * 10}px)`,
      }}>
        <span style={{ fontFamily: SANS, fontSize: U * 0.021, fontWeight: 700, letterSpacing: 2.4, color: CLAUDE.SPARK }}>SCORE AT TURN 100  </span>
        <span style={{ fontFamily: SERIF, fontSize: U * 0.048, color: CLAUDE.INK }}>gold, minus debt, plus stock and people</span>
      </div>
    </Frame>
  );
};

/* ───────────────────────── bar figures: depth ladder, Gemma ─────────────────────── */

const Bars: React.FC<{
  rows: { label: string; value: number; accent?: boolean }[]; max: number; eyebrow: string; title: string; sparkLine: string;
}> = ({ rows, max, eyebrow, title, sparkLine }) => {
  const frame = useCurrentFrame();
  const { fps, width, height } = useVideoConfig();
  const U = Math.min(width, height);
  const PAD_X = width * 0.075;
  const TOP = height * 0.265;
  const ROW_H = height * 0.108;
  const LABEL_W = width * 0.3;
  const TRACK_L = PAD_X + LABEL_W;
  const TRACK_W = width - TRACK_L - PAD_X - width * 0.085;
  return (
    <Frame eyebrow={eyebrow} title={title} sparkLine={sparkLine}>
      {rows.map((b, i) => {
        const a = spring({ frame: frame - 14 - i * 11, fps, config: grow });
        const top = TOP + i * ROW_H;
        return (
          <React.Fragment key={b.label}>
            <div style={{ position: 'absolute', left: PAD_X, top: top + ROW_H * 0.26, width: LABEL_W - width * 0.018, textAlign: 'right' as const,
              fontFamily: SERIF, fontSize: U * 0.033, color: b.accent ? CLAUDE.INK : CLAUDE.INK_SOFT, opacity: clamp(a, 0, 1), lineHeight: 1.2,
              fontWeight: b.accent ? 600 : 400 }}>{b.label}</div>
            <div style={{ position: 'absolute', left: TRACK_L, top: top + ROW_H * 0.06, width: TRACK_W, height: ROW_H * 0.84, background: CLAUDE.PILL, borderRadius: 8 }} />
            <div style={{ position: 'absolute', left: TRACK_L, top: top + ROW_H * 0.06, width: TRACK_W * (b.value / max) * clamp(a, 0, 1),
              height: ROW_H * 0.84, background: b.accent ? CLAUDE.INK : CLAUDE.INK_SOFT, borderRadius: 8 }} />
            {b.accent ? (
              <div style={{ position: 'absolute', left: TRACK_L, top: top + ROW_H * 0.06 + ROW_H * 0.88, width: TRACK_W * (b.value / max) * clamp(a, 0, 1),
                height: U * 0.007, background: CLAUDE.SPARK }} />
            ) : null}
            <div style={{ position: 'absolute', left: TRACK_L + TRACK_W + width * 0.016, top: top + ROW_H * 0.2, fontFamily: SERIF, fontSize: U * 0.046,
              fontWeight: 600, color: CLAUDE.INK, opacity: clamp(a, 0, 1) }}>
              {Math.round(b.value * clamp(a, 0, 1)).toLocaleString('en-US')}
            </div>
          </React.Fragment>
        );
      })}
    </Frame>
  );
};

/** B04. Terracotta moment: the 40-turn bar. */
export const worldLadderSchema = z.object({ sparkLine: z.string().default('Looking further pays.') });
export type WorldLadderProps = z.infer<typeof worldLadderSchema>;
export const WorldLadder: React.FC<WorldLadderProps> = ({ sparkLine }) => (
  <Bars
    eyebrow="200 UNSEEN WORLDS · 100 TURNS · MEAN SCORE"
    title="The further ahead it plans, the more it makes"
    sparkLine={sparkLine}
    max={3000}
    rows={[
      { label: 'never invests', value: 1247 },
      { label: 'looks 1 turn ahead', value: 1835 },
      { label: 'looks 4 turns ahead', value: 2409 },
      { label: 'looks 10 turns ahead', value: 2637 },
      { label: 'looks 20 turns ahead', value: 2705 },
      { label: 'looks 40 turns ahead', value: 2847, accent: true },
    ]}
  />
);

/** B06. Terracotta moment: the Gemma bar. */
export const worldGemmaSchema = z.object({ sparkLine: z.string().default('Sensible plans, bad bookkeeping.') });
export type WorldGemmaProps = z.infer<typeof worldGemmaSchema>;
export const WorldGemma: React.FC<WorldGemmaProps> = ({ sparkLine }) => (
  <Bars
    eyebrow="SAME 3 WORLDS · 20 TURNS · MEAN SCORE"
    title="A 9B model scores below every scripted agent"
    sparkLine={sparkLine}
    max={1400}
    rows={[
      { label: 'Gemma-2-9B', value: 533, accent: true },
      { label: 'looks 1 turn ahead', value: 854 },
      { label: 'never invests', value: 951 },
      { label: 'looks 10 turns ahead', value: 1158 },
      { label: 'looks 20 turns ahead', value: 1214 },
    ]}
  />
);

/* ───────────────────────── B05 — same land, two outcomes ───────────────────────── */
/** Terracotta moment: the planner's roads. */

export const worldCompareSchema = z.object({ sparkLine: z.string().default('Same land. Same luck.') });
export type WorldCompareProps = z.infer<typeof worldCompareSchema>;

export const WorldCompare: React.FC<WorldCompareProps> = ({ sparkLine }) => {
  const frame = useCurrentFrame();
  const { fps, width, height } = useVideoConfig();
  const U = Math.min(width, height);
  const PAD_X = width * 0.075;
  const SIZE = height * 0.5;
  const GAPX = width * 0.09;
  const LX = (width - SIZE * 2 - GAPX) / 2;
  const MY = height * 0.27;
  const reveal = clamp(interpolate(frame, [6, 40], [0, 1]), 0, 1);
  const prog = clamp(interpolate(frame, [50, 150], [0, 1]), 0, 1);
  const sc = spring({ frame: frame - 150, fps, config: ease });
  const sides = [
    { d: WORLD_B.cruise, label: 'Never invests', x: LX, accent: false },
    { d: WORLD_B.planner, label: 'Plans 40 turns ahead', x: LX + SIZE + GAPX, accent: true },
  ];
  return (
    <Frame eyebrow="SEED 10003 · SAME LAND, SAME EVENTS · TURN 100" title="Same town, two ways to run it" sparkLine={sparkLine}>
      {sides.map((s) => (
        <React.Fragment key={s.label}>
          <TerrainMap w={WORLD_B} x={s.x} y={MY} size={SIZE} reveal={reveal} tiles={s.d.tiles as unknown as Build[]}
            roads={s.d.roads as unknown as number[][]} tileProgress={prog} />
          <div style={{ position: 'absolute', left: s.x, top: MY + SIZE + height * 0.02, width: SIZE, display: 'flex', justifyContent: 'space-between', alignItems: 'baseline' }}>
            <span style={{ fontFamily: SERIF, fontSize: U * 0.032, color: s.accent ? CLAUDE.INK : CLAUDE.INK_SOFT, fontWeight: s.accent ? 600 : 400 }}>{s.label}</span>
            <span style={{ fontFamily: SERIF, fontSize: U * 0.05, fontWeight: 600, color: CLAUDE.INK, opacity: clamp(sc, 0, 1) }}>
              {Math.round(s.d.score * clamp(sc, 0, 1)).toLocaleString('en-US')}
            </span>
          </div>
        </React.Fragment>
      ))}
    </Frame>
  );
};
