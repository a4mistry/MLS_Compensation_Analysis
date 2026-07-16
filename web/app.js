/* MLS 2026 compensation narrative — chart + copy rendering */
const D = window.MLS_DATA;
const L = D.league;

/* soccer / pitch palette (light theme) */
const COL = { accent: '#0f8a3c', grassDk: '#0a6b2f', blue: '#1f7ac4', hot: '#e23b3b',
              gold: '#e0a800', ink: '#12241a', muted: '#566659', line: '#d5e3d1',
              panel: '#ffffff' };

const usd = (v, dp = 0) => '$' + Number(v).toLocaleString('en-US', { maximumFractionDigits: dp });
const usdShort = v => v >= 1e6 ? '$' + (v / 1e6).toFixed(v >= 1e7 ? 0 : 1) + 'M'
                    : '$' + Math.round(v / 1e3) + 'K';

const AXIS = {
  axisLine: { lineStyle: { color: COL.line } },
  axisLabel: { color: COL.muted },
  splitLine: { lineStyle: { color: 'rgba(18,36,26,.08)' } },
  nameTextStyle: { color: COL.muted },
};
const baseGrid = { left: 8, right: 24, top: 24, bottom: 8, containLabel: true };
const TT = {
  backgroundColor: '#ffffff', borderColor: COL.line, borderWidth: 1,
  textStyle: { color: COL.ink, fontFamily: 'Inter' },
  extraCssText: 'box-shadow:0 6px 22px rgba(10,60,30,.16);border-radius:8px;',
};

/* -------------------- hero + inline copy -------------------- */
document.getElementById('h-payroll').textContent = '$' + (L.totalPayroll / 1e6).toFixed(0) + 'M';
document.getElementById('h-players').textContent = L.players;
document.getElementById('h-gini').textContent = L.gini.toFixed(2);
document.getElementById('h-r2').textContent = (D.regression.r2 * 100).toFixed(0) + '%';
document.getElementById('t-median').textContent = usd(L.median);
document.getElementById('t-mean').textContent = usd(L.mean);
document.getElementById('t-min').textContent = usd(L.leagueMin);
document.getElementById('t-top10').textContent = (L.top10Share * 100).toFixed(0) + '%';
document.getElementById('t-max').textContent = usd(L.max);
document.getElementById('t-r2b').textContent = (D.regression.r2 * 100).toFixed(0) + '%';
document.getElementById('f-asof').textContent = L.asOf;

/* landscape stat cards */
const cards = [
  { n: '$' + (L.totalPayroll / 1e6).toFixed(0) + 'M', cls: 'accent', cap: 'Total league payroll (guaranteed comp)' },
  { n: usd(L.median), cls: 'blue', cap: 'Median player pay' },
  { n: usd(L.p90), cls: '', cap: '90th-percentile pay — the DP threshold' },
  { n: usdShort(L.max), cls: 'gold', cap: "Top earner's compensation" },
];
document.getElementById('landscape-stats').innerHTML = cards.map(c =>
  `<div class="stat"><div class="num ${c.cls}">${c.n}</div><div class="cap">${c.cap}</div></div>`).join('');

/* -------------------- 1. distribution histogram -------------------- */
(() => {
  const cats = D.hist.map(h => Math.round((h.lo + h.hi) / 2));
  echarts.init(document.getElementById('chart-dist')).setOption({
    grid: { ...baseGrid, left: 48, bottom: 48 }, tooltip: {
      ...TT, trigger: 'axis',
      formatter: p => { const h = D.hist[p[0].dataIndex];
        return `${usdShort(h.lo)} – ${usdShort(h.hi)}<br/><b>${h.n}</b> players`; },
    },
    xAxis: { type: 'category', data: cats, name: 'Guaranteed compensation', nameLocation: 'middle',
      nameGap: 32, ...AXIS,
      axisLabel: { color: COL.muted, formatter: v => usdShort(v), interval: 4 } },
    yAxis: { type: 'value', name: 'Players', nameLocation: 'middle', nameGap: 36, nameRotate: 90, ...AXIS },
    series: [{ type: 'bar', data: D.hist.map(h => h.n),
      itemStyle: {
        borderRadius: [3, 3, 0, 0],
        color: new echarts.graphic.LinearGradient(0, 0, 0, 1,
          [{ offset: 0, color: '#2faa5a' }, { offset: 1, color: COL.grassDk }]),
      } }],
  });
})();

/* -------------------- 2. top earners -------------------- */
(() => {
  const top = D.topEarners.slice(0, 15).slice().reverse();
  echarts.init(document.getElementById('chart-top')).setOption({
    grid: { ...baseGrid, left: 24, right: 70, bottom: 40 }, tooltip: {
      ...TT, trigger: 'item',
      formatter: p => { const t = top[p.dataIndex];
        return `<b>${t.name}</b><br/>${t.club} · ${t.position}<br/>${usd(t.comp)}`; },
    },
    xAxis: { type: 'value', name: 'Guaranteed compensation', nameLocation: 'middle', nameGap: 28,
      ...AXIS, axisLabel: { color: COL.muted, formatter: usdShort } },
    yAxis: { type: 'category', data: top.map(t => t.name), ...AXIS,
      axisLabel: { color: COL.ink, fontSize: 12 } },
    series: [{
      type: 'bar', data: top.map(t => t.comp),
      label: { show: true, position: 'right', color: COL.muted, formatter: p => usdShort(p.value) },
      itemStyle: {
        borderRadius: [0, 4, 4, 0],
        color: new echarts.graphic.LinearGradient(0, 0, 1, 0,
          [{ offset: 0, color: COL.grassDk }, { offset: 1, color: COL.gold }]),
      },
    }],
  });
})();

/* -------------------- 3. positions -------------------- */
(() => {
  const pos = D.positions.slice().reverse();
  echarts.init(document.getElementById('chart-pos')).setOption({
    grid: { ...baseGrid, left: 24, right: 80, bottom: 40 }, tooltip: {
      ...TT, trigger: 'item',
      formatter: p => { const x = pos[p.dataIndex];
        return `<b>${x.position}</b><br/>Median ${usd(x.median)}<br/>${x.n} players`; },
    },
    xAxis: { type: 'value', name: 'Median guaranteed compensation', nameLocation: 'middle', nameGap: 28,
      ...AXIS, axisLabel: { color: COL.muted, formatter: usdShort } },
    yAxis: { type: 'category', data: pos.map(x => x.position), ...AXIS,
      axisLabel: { color: COL.ink, fontSize: 12 } },
    series: [{
      type: 'bar', data: pos.map(x => x.median),
      label: { show: true, position: 'right', color: COL.muted,
        formatter: p => usdShort(p.value) + '  ·  n=' + pos[p.dataIndex].n },
      itemStyle: { borderRadius: [0, 4, 4, 0], color: COL.accent },
    }],
  });
})();

/* -------------------- 4. payroll vs PPG scatter -------------------- */
(() => {
  const R = D.regression;
  const line = [];
  for (let i = 0; i <= 40; i++) {
    const x = R.xmin * Math.pow(R.xmax / R.xmin, i / 40);
    line.push([x / 1e6, R.intercept + R.slope * Math.log10(x)]);
  }
  const mk = conf => D.clubs.filter(c => c.conf === conf).map(c => ({
    value: [c.payroll / 1e6, c.ppg], club: c,
  }));
  echarts.init(document.getElementById('chart-scatter')).setOption({
    grid: { ...baseGrid, top: 40, right: 30, left: 56, bottom: 44 },
    legend: { data: ['East', 'West'], textStyle: { color: COL.muted }, top: 0, right: 0 },
    tooltip: {
      ...TT, trigger: 'item',
      formatter: p => { if (!p.data.club) return '';
        const c = p.data.club;
        const over = c.residual >= 0;
        return `<b>${c.club}</b> <span style="color:${COL.muted}">(${c.conf})</span><br/>`
          + `Payroll: ${usd(c.payroll)}<br/>`
          + `Record: ${c.w}-${c.l}-${c.d} · ${c.pts} pts (${c.ppg.toFixed(2)} PPG)<br/>`
          + `Cost/point: ${usd(c.costPerPoint)}<br/>`
          + `<span style="color:${over ? COL.accent : COL.hot}">`
          + `${over ? '▲ over' : '▼ under'}-performing spend by ${Math.abs(c.residual).toFixed(2)} PPG</span>`; },
    },
    xAxis: { type: 'log', name: 'Total payroll', nameLocation: 'middle', nameGap: 34, ...AXIS,
      axisLabel: { color: COL.muted, formatter: v => '$' + v + 'M' } },
    yAxis: { type: 'value', name: 'Points per game', nameLocation: 'middle', nameGap: 40,
      nameRotate: 90, ...AXIS },
    series: [
      { name: 'trend', type: 'line', data: line, showSymbol: false, silent: true,
        lineStyle: { color: COL.hot, type: 'dashed', width: 2 }, z: 1,
        tooltip: { show: false } },
      { name: 'East', type: 'scatter', data: mk('East'), symbolSize: 15, z: 3,
        itemStyle: { color: COL.accent, borderColor: '#ffffff', borderWidth: 1.5, opacity: .95 },
        emphasis: { scale: 1.5 },
        label: { show: true, position: 'right', color: COL.muted, fontSize: 10,
          formatter: p => p.data.club.club } },
      { name: 'West', type: 'scatter', data: mk('West'), symbolSize: 15, z: 3,
        itemStyle: { color: COL.blue, borderColor: '#ffffff', borderWidth: 1.5, opacity: .95 },
        emphasis: { scale: 1.5 },
        label: { show: true, position: 'right', color: COL.muted, fontSize: 10,
          formatter: p => p.data.club.club } },
    ],
  });
})();

/* -------------------- 5. efficiency lists + residual bar -------------------- */
(() => {
  const byCost = D.clubs.slice().sort((a, b) => a.costPerPoint - b.costPerPoint);
  const best = byCost.slice(0, 6), worst = byCost.slice(-6).reverse();
  const row = (c, cls) => `<div class="r"><span class="team">${c.club}
      <span class="tag">${c.pts} pts · ${usdShort(c.payroll)}</span></span>
      <span class="val ${cls}">${usd(c.costPerPoint)}<span class="tag">/pt</span></span></div>`;
  document.getElementById('best-list').innerHTML = best.map(c => row(c, 'good')).join('');
  document.getElementById('worst-list').innerHTML = worst.map(c => row(c, 'bad')).join('');

  const atl = D.clubs.find(c => c.club === 'Atlanta United');
  document.getElementById('pull-atl').innerHTML =
    `Atlanta United is the league's cautionary tale: a top-five payroll of
     <span style="color:var(--gold)">${usdShort(atl.payroll)}</span> buying
     <span style="color:var(--hot)">just ${atl.pts} points</span> — the most expensive futility in MLS.`;

  const res = D.clubs.slice().sort((a, b) => a.residual - b.residual);
  echarts.init(document.getElementById('chart-residual')).setOption({
    grid: { ...baseGrid, left: 24, right: 30, bottom: 44 },
    tooltip: { ...TT, trigger: 'item',
      formatter: p => { const c = res[p.dataIndex];
        return `<b>${c.club}</b><br/>Actual ${c.ppg.toFixed(2)} vs predicted ${c.ppgPred.toFixed(2)} PPG<br/>`
          + `<span style="color:${c.residual >= 0 ? COL.accent : COL.hot}">`
          + `${c.residual >= 0 ? '+' : ''}${c.residual.toFixed(2)} vs spend</span>`; } },
    xAxis: { type: 'value', name: 'PPG vs what payroll predicts', nameLocation: 'middle', nameGap: 34, ...AXIS },
    yAxis: { type: 'category', data: res.map(c => c.club), ...AXIS,
      axisLabel: { color: COL.ink, fontSize: 11 } },
    series: [{
      type: 'bar', data: res.map(c => ({
        value: +c.residual.toFixed(3),
        itemStyle: { color: c.residual >= 0 ? COL.accent : COL.hot, borderRadius: 3 },
      })),
    }],
  });
})();

/* -------------------- 6. roster construction -------------------- */
(() => {
  const R = D.roster;
  const BUCKET = { Attack: COL.hot, Midfield: COL.gold, Defense: COL.blue, Goalkeeper: COL.accent };
  const pct = v => (v * 100).toFixed(0) + '%';

  // inline copy
  const set = (id, v) => { const el = document.getElementById(id); if (el) el.textContent = v; };
  set('t-ginir', `r = ${R.giniR >= 0 ? '+' : ''}${R.giniR.toFixed(2)}`);
  set('t-ginipartial', `r = ${R.giniPartialR >= 0 ? '+' : ''}${R.giniPartialR.toFixed(2)}`);
  set('t-atkcount', R.topBucketCounts.Attack);
  set('t-gkppg', R.ppgByTopBucket.Goalkeeper ? R.ppgByTopBucket.Goalkeeper.toFixed(2) : '—');
  set('s-atk', `${R.topBucketCounts.Attack}/30`);
  set('s-atkppg', R.ppgByTopBucket.Attack ? R.ppgByTopBucket.Attack.toFixed(2) : '—');
  set('s-gk', `${R.topBucketCounts.Goalkeeper}/30`);
  set('s-gkppg2', R.ppgByTopBucket.Goalkeeper ? R.ppgByTopBucket.Goalkeeper.toFixed(2) : '—');

  // 6a. Gini vs PPG scatter (quadrant, bubble = payroll)
  const gmax = Math.max(...R.giniByClub.map(d => d.payroll));
  const mk = conf => R.giniByClub.filter(d => d.conf === conf).map(d => ({
    value: [d.gini, d.ppg], club: d,
    symbolSize: 12 + (d.payroll / gmax) * 34,
  }));
  const med = arr => { const a = [...arr].sort((x, y) => x - y), n = a.length;
    return n % 2 ? a[(n - 1) / 2] : (a[n / 2 - 1] + a[n / 2]) / 2; };
  const gMed = med(R.giniByClub.map(d => d.gini));
  const pMed = med(R.giniByClub.map(d => d.ppg));
  echarts.init(document.getElementById('chart-gini')).setOption({
    grid: { ...baseGrid, top: 40, right: 30, left: 56, bottom: 44 },
    legend: { data: ['East', 'West'], textStyle: { color: COL.muted }, top: 0, right: 0 },
    tooltip: { ...TT, trigger: 'item', formatter: p => { const c = p.data.club; if (!c) return '';
      return `<b>${c.club}</b><br/>Gini ${c.gini.toFixed(2)} · ${c.ppg.toFixed(2)} PPG<br/>`
        + `Payroll ${usd(c.payroll)}`; } },
    xAxis: { type: 'value', name: 'Pay inequality (Gini)', nameLocation: 'middle', nameGap: 32, ...AXIS,
      min: 0.35, max: 0.8 },
    yAxis: { type: 'value', name: 'Points per game', nameLocation: 'middle', nameGap: 40,
      nameRotate: 90, ...AXIS },
    series: [
      { type: 'scatter', name: 'East', data: mk('East'),
        itemStyle: { color: COL.accent, borderColor: '#fff', borderWidth: 1.4, opacity: .9 },
        markLine: { silent: true, symbol: 'none', lineStyle: { color: '#bbb', type: 'dashed' },
          data: [{ xAxis: gMed }, { yAxis: pMed }], label: { show: false } } },
      { type: 'scatter', name: 'West', data: mk('West'),
        itemStyle: { color: COL.blue, borderColor: '#fff', borderWidth: 1.4, opacity: .9 } },
    ],
  });

  // 6b. minimum-wage tier: league vs bottom quartile
  const cats = R.posOrder;
  echarts.init(document.getElementById('chart-minwage')).setOption({
    grid: { ...baseGrid, top: 40, left: 58, bottom: 40 },
    legend: { data: ['Whole league', 'Bottom pay quartile'], textStyle: { color: COL.muted }, top: 0 },
    tooltip: { ...TT, trigger: 'axis', axisPointer: { type: 'shadow' },
      formatter: ps => ps[0].axisValue + '<br/>' + ps.map(p => `${p.seriesName}: ${p.value}%`).join('<br/>') },
    xAxis: { type: 'category', data: cats, name: 'Position', nameLocation: 'middle', nameGap: 30,
      ...AXIS, axisLabel: { color: COL.ink } },
    yAxis: { type: 'value', name: 'Share of players', nameLocation: 'middle', nameGap: 46, nameRotate: 90,
      ...AXIS, axisLabel: { color: COL.muted, formatter: '{value}%' } },
    series: [
      { name: 'Whole league', type: 'bar', data: cats.map(b => +(R.leagueMix[b] * 100).toFixed(0)),
        itemStyle: { color: '#c9d6cc', borderRadius: [3, 3, 0, 0] } },
      { name: 'Bottom pay quartile', type: 'bar',
        data: cats.map(b => ({ value: +(R.bottomQuartileMix[b] * 100).toFixed(0),
          itemStyle: { color: BUCKET[b], borderRadius: [3, 3, 0, 0] } })) },
    ],
  });

  // 6c. Atlanta spotlight: position payroll share vs league
  const atl = R.shareByClub[R.spotlight];
  echarts.init(document.getElementById('chart-atlanta')).setOption({
    grid: { ...baseGrid, top: 40, left: 58, bottom: 40 },
    legend: { data: ['League avg', R.spotlight], textStyle: { color: COL.muted }, top: 0 },
    tooltip: { ...TT, trigger: 'axis', axisPointer: { type: 'shadow' },
      formatter: ps => ps[0].axisValue + '<br/>' + ps.map(p => `${p.seriesName}: ${p.value}%`).join('<br/>') },
    xAxis: { type: 'category', data: cats, name: 'Position', nameLocation: 'middle', nameGap: 30,
      ...AXIS, axisLabel: { color: COL.ink } },
    yAxis: { type: 'value', name: 'Share of payroll', nameLocation: 'middle', nameGap: 46, nameRotate: 90,
      ...AXIS, axisLabel: { color: COL.muted, formatter: '{value}%' } },
    series: [
      { name: 'League avg', type: 'bar', data: cats.map(b => +(R.leagueShare[b] * 100).toFixed(0)),
        itemStyle: { color: '#c9d6cc', borderRadius: [3, 3, 0, 0] } },
      { name: R.spotlight, type: 'bar',
        data: cats.map(b => ({ value: +(atl[b] * 100).toFixed(0),
          itemStyle: { color: BUCKET[b], borderRadius: [3, 3, 0, 0] } })) },
    ],
  });
})();

/* ==================== deeper analyses (7-9) ==================== */
const BUCKET_COL = { Attack: COL.hot, Midfield: COL.gold, Defense: COL.blue, Goalkeeper: COL.accent };
const putText = (id, v) => { const el = document.getElementById(id); if (el) el.textContent = v; };
// No auto "significant" label: with ~15 correlations on the same 30 clubs,
// none survives a multiple-comparisons correction (see footer caveat).
const corrTxt = (r, p) => `r = ${r >= 0 ? '+' : ''}${r.toFixed(2)}` +
  (p != null ? ` (p = ${p})` : '');
const mkGrid = e => ({ left: 56, right: 24, top: 40, bottom: 46, containLabel: true, ...e });
function linfit(xs, ys) {
  const n = xs.length, mx = xs.reduce((a, b) => a + b) / n, my = ys.reduce((a, b) => a + b) / n;
  let num = 0, den = 0;
  for (let i = 0; i < n; i++) { num += (xs[i] - mx) * (ys[i] - my); den += (xs[i] - mx) ** 2; }
  const m = num / den; return { m, b: my - m * mx };
}
function scatterChart(elId, pts, xLabel, yLabel, xf, labelTopN) {
  const xs = pts.map(p => p.x), ys = pts.map(p => p.y);
  const fit = linfit(xs, ys), xmin = Math.min(...xs), xmax = Math.max(...xs);
  let labelSet = null;
  if (labelTopN && labelTopN < pts.length) {   // label only the N biggest outliers (any direction)
    const mean = a => a.reduce((s, v) => s + v, 0) / a.length;
    const std = (a, m) => Math.sqrt(a.reduce((s, v) => s + (v - m) ** 2, 0) / a.length) || 1;
    const mx = mean(xs), my = mean(ys), sx = std(xs, mx), sy = std(ys, my);
    labelSet = new Set(pts.map((p, i) => ({ i, d: Math.hypot((p.x - mx) / sx, (p.y - my) / sy) }))
      .sort((a, b) => b.d - a.d).slice(0, labelTopN).map(o => o.i));
  }
  echarts.init(document.getElementById(elId)).setOption({
    grid: mkGrid({}), tooltip: { ...TT, trigger: 'item', formatter: p => p.data.tip || '' },
    xAxis: { type: 'value', name: xLabel, nameLocation: 'middle', nameGap: 32, ...AXIS,
      axisLabel: { color: COL.muted, formatter: xf || '{value}' } },
    yAxis: { type: 'value', name: yLabel, nameLocation: 'middle', nameGap: 40, nameRotate: 90, ...AXIS },
    series: [
      { type: 'line', silent: true, showSymbol: false, z: 1, tooltip: { show: false },
        lineStyle: { color: COL.hot, type: 'dashed', width: 2 },
        data: [[xmin, fit.m * xmin + fit.b], [xmax, fit.m * xmax + fit.b]] },
      { type: 'scatter', z: 3, symbolSize: 14,
        itemStyle: { color: COL.blue, borderColor: '#fff', borderWidth: 1.3, opacity: .9 },
        label: { show: true, position: 'right', color: COL.muted, fontSize: 9,
          formatter: p => (labelSet && !labelSet.has(p.dataIndex)) ? '' : p.data.label },
        data: pts.map(p => ({ value: [p.x, p.y], label: p.label, tip: p.tip })) },
    ],
  });
}

/* 7. marketability gap */
(() => {
  const G = D.gap;
  putText('g-mkt', usd(G.marketingTotal));
  putText('g-mktpct', (G.marketingPct * 100).toFixed(0) + '%');
  putText('g-mktr', corrTxt(G.marketingPpgR, G.marketingPpgP));
  document.getElementById('gap-stats').innerHTML = [
    { n: '$' + (G.marketingTotal / 1e6).toFixed(0) + 'M', c: 'gold', cap: 'Total marketing/bonus money' },
    { n: (G.marketingPct * 100).toFixed(0) + '%', c: 'accent', cap: 'of guaranteed pay is marketing money' },
    { n: Math.round(G.nWithGap / G.nPlayers * 100) + '%', c: 'blue', cap: 'of players earn above base salary' },
    { n: '$' + (G.byPosition.find(p => p.bucket === 'Attack').marketing / 1e6).toFixed(0) + 'M', c: '',
      cap: 'of it goes to attackers' },
  ].map(c => `<div class="stat"><div class="num ${c.c}">${c.n}</div><div class="cap">${c.cap}</div></div>`).join('');

  const top = G.topGap.slice(0, 15).slice().reverse();
  echarts.init(document.getElementById('ch-gap')).setOption({
    grid: mkGrid({ left: 4, right: 60 }),
    legend: { data: ['Base salary', 'Marketing premium'], top: 0, textStyle: { color: COL.muted } },
    tooltip: { ...TT, trigger: 'axis', axisPointer: { type: 'shadow' }, formatter: ps => {
      const t = top[ps[0].dataIndex];
      return `<b>${t.name}</b> · ${t.club}<br/>Base ${usdShort(t.base)} → Guar ${usdShort(t.guar)}`
        + `<br/>Marketing premium ${usdShort(t.gap)}`; } },
    xAxis: { type: 'value', name: 'Guaranteed compensation', nameLocation: 'middle', nameGap: 30, ...AXIS,
      axisLabel: { color: COL.muted, formatter: usdShort } },
    yAxis: { type: 'category', data: top.map(t => t.name), ...AXIS, axisLabel: { color: COL.ink, fontSize: 11 } },
    series: [
      { name: 'Base salary', type: 'bar', stack: 'p', data: top.map(t => t.base), itemStyle: { color: COL.grassDk } },
      { name: 'Marketing premium', type: 'bar', stack: 'p', data: top.map(t => t.gap), itemStyle: { color: COL.gold } },
    ],
  });

  const bp = G.byPosition;
  echarts.init(document.getElementById('ch-gappos')).setOption({
    grid: mkGrid({ bottom: 40 }),
    tooltip: { ...TT, trigger: 'item', formatter: p => { const d = bp[p.dataIndex];
      return `<b>${d.bucket}</b><br/>${usd(d.marketing)} marketing money<br/>`
        + `${(d.shareWithGap * 100).toFixed(0)}% of players have a premium`; } },
    xAxis: { type: 'category', data: bp.map(d => d.bucket), name: 'Position', nameLocation: 'middle',
      nameGap: 30, ...AXIS, axisLabel: { color: COL.ink } },
    yAxis: { type: 'value', name: 'Marketing money', nameLocation: 'middle', nameGap: 46, nameRotate: 90,
      ...AXIS, axisLabel: { color: COL.muted, formatter: v => '$' + (v / 1e6).toFixed(0) + 'M' } },
    series: [{ type: 'bar', data: bp.map(d => ({ value: d.marketing,
      itemStyle: { color: BUCKET_COL[d.bucket], borderRadius: [3, 3, 0, 0] } })) }],
  });
})();

/* 8. does spending buy goals */
(() => {
  const GO = D.goals;
  putText('g-atkr', corrTxt(GO.attackGfR, GO.attackGfP));
  putText('g-atkr2', corrTxt(GO.attackGfR, GO.attackGfP));
  putText('g-defr', corrTxt(GO.defGaR, GO.defGaP));
  scatterChart('ch-atk',
    GO.clubs.map(c => ({ x: c.attackPay / 1e6, y: c.gf, label: c.club,
      tip: `<b>${c.club}</b><br/>Attack pay ${usd(c.attackPay)}<br/>${c.gf} goals scored` })),
    'Attack payroll ($M)', 'Goals scored', v => '$' + v + 'M', 7);
  scatterChart('ch-def',
    GO.clubs.map(c => ({ x: c.defPay / 1e6, y: c.ga, label: c.club,
      tip: `<b>${c.club}</b><br/>Defence+GK pay ${usd(c.defPay)}<br/>${c.ga} goals conceded` })),
    'Defence + GK payroll ($M)', 'Goals conceded', v => '$' + v + 'M', 7);

  const gv = GO.clubs.slice().sort((a, b) => a.goalsPer10mAtk - b.goalsPer10mAtk);
  const mid = gv[Math.floor(gv.length / 2)].goalsPer10mAtk;
  putText('g-bestval', gv[gv.length - 1].club);
  putText('g-worstval', gv[0].club);
  echarts.init(document.getElementById('ch-goalval')).setOption({
    grid: mkGrid({ left: 4, right: 60, bottom: 40 }),
    tooltip: { ...TT, trigger: 'item', formatter: p => { const c = gv[p.dataIndex];
      return `<b>${c.club}</b><br/>${c.goalsPer10mAtk.toFixed(1)} goals per $10M attack<br/>`
        + `${c.gf} goals on ${usd(c.attackPay)}`; } },
    xAxis: { type: 'value', name: 'Goals per $10M of attack pay', nameLocation: 'middle', nameGap: 30, ...AXIS },
    yAxis: { type: 'category', data: gv.map(c => c.club), ...AXIS, axisLabel: { color: COL.ink, fontSize: 11 } },
    series: [{ type: 'bar', data: gv.map(c => ({ value: +c.goalsPer10mAtk.toFixed(1),
      itemStyle: { color: c.goalsPer10mAtk >= mid ? COL.accent : COL.hot, borderRadius: [0, 3, 3, 0] } })),
      label: { show: true, position: 'right', color: COL.muted, formatter: '{c}' } }],
  });
})();

/* 9. stars vs the middle class */
(() => {
  const M = D.middle;
  putText('g-midr', corrTxt(M.restMedianPpgR, M.restMedianPpgP));
  scatterChart('ch-mid',
    M.clubs.map(c => ({ x: c.restMedian / 1e3, y: c.ppg, label: c.club,
      tip: `<b>${c.club}</b><br/>Middle-class median ${usdShort(c.restMedian)}<br/>${c.ppg.toFixed(2)} PPG` })),
    'Rest-of-roster median pay ($K)', 'Points per game', v => '$' + v + 'K');

  const C = M.corr, metricColor = { ppg: COL.accent, gf: COL.hot, ga: COL.blue };
  echarts.init(document.getElementById('ch-midbar')).setOption({
    grid: mkGrid({ left: 8, top: 42, bottom: 40 }),
    legend: { data: C.metrics.map(m => m.label), top: 0, textStyle: { color: COL.muted } },
    tooltip: { ...TT, trigger: 'axis', axisPointer: { type: 'shadow' },
      formatter: ps => ps[0].axisValue + '<br/>' +
        ps.map(p => `${p.seriesName}: r = ${p.value >= 0 ? '+' : ''}${p.value}`).join('<br/>') },
    xAxis: { type: 'category', data: C.tiers, name: 'Pay tier', nameLocation: 'middle',
      nameGap: 30, ...AXIS, axisLabel: { color: COL.ink } },
    yAxis: { type: 'value', name: 'Correlation (r)', nameLocation: 'middle', nameGap: 40, nameRotate: 90, ...AXIS },
    series: C.metrics.map(m => ({ name: m.label, type: 'bar', data: m.values.map(v => +v.toFixed(2)),
      itemStyle: { color: metricColor[m.key], borderRadius: [2, 2, 0, 0] },
      label: { show: true, position: 'top', color: COL.muted, fontSize: 9,
        formatter: p => (p.value >= 0 ? '+' : '') + p.value } })),
  });
})();

/* ==================== data-bound narrative numbers ==================== */
(() => {
  const pctf = v => Math.round(v * 100) + '%';
  const ordinal = n => { const s = ['th', 'st', 'nd', 'rd'], v = n % 100;
    return n + (s[(v - 20) % 10] || s[v] || s[0]); };

  // --- Atlanta cautionary-tale paragraph (C1 + M4: all from data) ---
  const R = D.roster, share = R.shareByClub[R.spotlight], lg = R.leagueShare;
  const byPay = D.clubs.slice().sort((a, b) => b.payroll - a.payroll);
  const atl = D.clubs.find(c => c.club === R.spotlight);
  const rank = byPay.findIndex(c => c.club === R.spotlight) + 1;
  const atlTop3 = (D.middle.clubs.find(c => c.club === R.spotlight) || {}).top3Share;
  const byPts = D.clubs.slice().sort((a, b) => b.pts - a.pts);
  const ptsRank = byPts.findIndex(c => c.club === R.spotlight) + 1;
  const standing = ptsRank > D.clubs.length - 3 ? 'bottom-three'
                 : ptsRank > D.clubs.length - 6 ? 'bottom-five' : 'struggling';
  putText('atl-rank', ordinal(rank));
  putText('atl-pay', '$' + (atl.payroll / 1e6).toFixed(1) + 'M');
  putText('atl-atk', pctf(share.Attack));
  putText('atl-lgatk', pctf(lg.Attack));
  putText('atl-atkdiff', Math.round((share.Attack - lg.Attack) * 100) + ' points');
  putText('atl-top3', pctf(atlTop3));
  putText('atl-gk', pctf(share.Goalkeeper));
  putText('atl-lggk', pctf(lg.Goalkeeper));
  putText('atl-ppg', atl.ppg == null ? '—' : atl.ppg.toFixed(2));
  putText('atl-standing', standing);
  putText('t-gkcount', R.topBucketCounts.Goalkeeper);

  // --- cost-per-point spread (M5) ---
  putText('t-cppspread', D.league.costPerPointSpreadX);

  // --- footer season-progress (M4: from standings meta) ---
  const m = D.meta || {};
  putText('fp-gprange', (m.standingsMinGp === m.standingsMaxGp)
    ? m.standingsMaxGp : `${m.standingsMinGp}–${m.standingsMaxGp}`);
  putText('fp-gametotal', m.gamesTotal);
  putText('fp-asof', m.standingsAsOf || '—');
  const prog = (m.standingsMaxGp || 0) / (m.gamesTotal || 34);
  putText('fp-stage', prog < 0.4 ? 'early season' : prog < 0.72 ? 'roughly mid-season' : 'late season');
})();

/* -------------------- scroll polish -------------------- */
const bar = document.getElementById('progress');
const onScroll = () => {
  const h = document.documentElement;
  bar.style.width = (h.scrollTop / (h.scrollHeight - h.clientHeight) * 100) + '%';
};
document.addEventListener('scroll', onScroll, { passive: true });

const io = new IntersectionObserver(es => es.forEach(e => {
  if (e.isIntersecting) { e.target.classList.add('in'); io.unobserve(e.target); }
}), { threshold: 0.12 });
document.querySelectorAll('.reveal').forEach(el => io.observe(el));

/* keep charts crisp on resize */
window.addEventListener('resize', () => {
  document.querySelectorAll('.chart').forEach(el => {
    const inst = echarts.getInstanceByDom(el); if (inst) inst.resize();
  });
});
