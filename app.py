"""
Walmex Dashboard — CFBC
Análisis de ventas, embarques y merma por tienda y producto
"""
import json, base64, openpyxl, re
from collections import defaultdict
from pathlib import Path
import streamlit as st
import streamlit.components.v1 as components

st.set_page_config(page_title="Walmex · CFBC", layout="wide", initial_sidebar_state="collapsed")
st.markdown("<style>header,footer,[data-testid='stToolbar']{display:none!important}section[data-testid='stSidebar']{display:none!important}.main .block-container{padding:0!important;max-width:100%!important}</style>", unsafe_allow_html=True)

# ── DATA ─────────────────────────────────────────────────────────────────────

@st.cache_data(ttl=3600)
def cargar_datos(path: str) -> dict:
    wb = openpyxl.load_workbook(path, data_only=True)
    ws = wb['Data']

    def sv(v):
        try: return float(v) if v is not None else 0.0
        except: return 0.0

    records = []
    for row in ws.iter_rows(min_row=2, values_only=True):
        producto = str(row[3]).strip() if row[3] else None
        tienda   = str(row[15]).strip() if row[15] else None
        semana   = int(row[25]) if row[25] else None
        if not producto or not tienda or not semana:
            continue
        yr = semana // 100
        wk = semana % 100
        records.append({
            'producto':   producto,
            'tienda':     tienda,
            'semana':     semana,
            'year':       yr,
            'week':       wk,
            'ventas_u':   sv(row[18]),
            'ventas_$':   sv(row[17]),
            'embarque_u': sv(row[20]),
            'embarque_$': sv(row[23]),
            'inventario': sv(row[26]),
            'sem_inv':    sv(row[27]),
            'merma_u':    max(0.0, sv(row[20]) - sv(row[18])),
            'cnt_sab': sv(row[28]), 'cnt_dom': sv(row[29]),
            'cnt_lun': sv(row[30]), 'cnt_mar': sv(row[31]),
            'cnt_mie': sv(row[32]), 'cnt_jue': sv(row[33]),
            'cnt_vie': sv(row[34]),
        })

    semanas   = sorted(set(r['semana'] for r in records))
    tiendas   = sorted(set(r['tienda']  for r in records))
    productos = sorted(set(r['producto'] for r in records))

    # Aggregate: por_semana[sem][tienda|producto] = {...}
    por_tienda   = defaultdict(lambda: defaultdict(lambda: defaultdict(float)))
    por_producto = defaultdict(lambda: defaultdict(lambda: defaultdict(float)))
    global_sem   = defaultdict(lambda: defaultdict(float))
    METRICS = ['ventas_u','ventas_$','embarque_u','embarque_$','merma_u','inventario']

    for r in records:
        for m in METRICS:
            por_tienda[r['semana']][r['tienda']][m]     += r[m]
            por_producto[r['semana']][r['producto']][m] += r[m]
            global_sem[r['semana']][m]                  += r[m]

    # Weekly trend across semanas (total)
    tendencia = [{
        'semana': s,
        'year': s // 100,
        'week': s % 100,
        **{m: round(global_sem[s][m], 1) for m in METRICS}
    } for s in semanas]

    # Per tienda detail
    td = {}
    for s in semanas:
        td[s] = {}
        for t in tiendas:
            d = por_tienda[s][t]
            td[s][t] = {m: round(d[m], 1) for m in METRICS}

    # Per producto detail
    pd2 = {}
    for s in semanas:
        pd2[s] = {}
        for p in productos:
            d = por_producto[s][p]
            pd2[s][p] = {m: round(d[m], 1) for m in METRICS}

    return {
        'semanas':    semanas,
        'tiendas':    tiendas,
        'productos':  productos,
        'tendencia':  tendencia,
        'por_tienda': {str(k): v for k,v in td.items()},
        'por_prod':   {str(k): v for k,v in pd2.items()},
    }

# Load data
EXCEL_PATH = "Analisis_Walmart.xlsx"
if not Path(EXCEL_PATH).exists():
    EXCEL_PATH = "/mnt/user-data/uploads/Analisis_Walmart.xlsx"

DATA = cargar_datos(EXCEL_PATH)

# ── HTML ──────────────────────────────────────────────────────────────────────

HTML = """<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<link href="https://fonts.googleapis.com/css2?family=Barlow+Condensed:wght@400;600;700;800&family=JetBrains+Mono:wght@400;600&display=swap" rel="stylesheet">
<script src="https://cdnjs.cloudflare.com/ajax/libs/Chart.js/4.4.1/chart.umd.min.js"></script>
<style>
:root{
  --bg:#05080f;--surface:#0b1120;--surface2:#111827;--border:#1a2840;
  --blue:#0071ce;--blue2:#00a3ff;--accent:#f5c518;--red:#ff4d4d;--green:#00d084;
  --text:#e8eef8;--muted:#5a7a9a;--dim:#2a3a50;
}
*{box-sizing:border-box;margin:0;padding:0}
body{background:var(--bg);color:var(--text);font-family:'Barlow Condensed',sans-serif;min-height:100vh;overflow-x:hidden}

/* HEADER */
.header{background:linear-gradient(135deg,#001a3a 0%,#003080 50%,#001a3a 100%);padding:14px 28px;display:flex;align-items:center;gap:16px;border-bottom:2px solid var(--blue)}
.walmart-logo{font-size:1.6rem;font-weight:800;letter-spacing:-1px;color:#fff}
.walmart-logo span{color:var(--accent)}
.header-sub{font-size:.7rem;font-family:'JetBrains Mono',monospace;color:rgba(255,255,255,.5);letter-spacing:2px;text-transform:uppercase}
.header-sem{margin-left:auto;font-family:'JetBrains Mono',monospace;font-size:.75rem;color:var(--accent);background:rgba(245,197,24,.1);border:1px solid rgba(245,197,24,.3);padding:4px 12px;border-radius:6px}

/* CONTROLS */
.ctrl-bar{display:flex;align-items:center;gap:12px;padding:10px 28px;background:var(--surface);border-bottom:1px solid var(--border);flex-wrap:wrap}
.view-tabs{display:flex;gap:0;background:var(--bg);border:1px solid var(--border);border-radius:8px;overflow:hidden}
.view-tab{padding:7px 18px;font-size:.8rem;font-weight:700;cursor:pointer;border:none;color:var(--muted);background:transparent;transition:all .2s;font-family:'Barlow Condensed',sans-serif;letter-spacing:.5px;text-transform:uppercase}
.view-tab:hover{color:var(--text)}
.view-tab.active{background:var(--blue);color:#fff}
.sem-select{background:var(--surface2);border:1px solid var(--border);border-radius:8px;color:var(--text);font-family:'JetBrains Mono',monospace;font-size:.75rem;padding:7px 12px;cursor:pointer;outline:none}
.sem-select:focus{border-color:var(--blue)}
.ctrl-label{font-size:.65rem;text-transform:uppercase;letter-spacing:1.5px;color:var(--muted);font-family:'JetBrains Mono',monospace}
.metric-toggle{display:flex;background:var(--bg);border:1px solid var(--border);border-radius:8px;overflow:hidden}
.metric-btn{padding:6px 14px;font-size:.75rem;font-weight:700;cursor:pointer;border:none;color:var(--muted);background:transparent;font-family:'Barlow Condensed',sans-serif;transition:all .2s;text-transform:uppercase}
.metric-btn.active{background:var(--accent);color:#000}

/* MAIN */
.main{padding:20px 28px;display:flex;flex-direction:column;gap:20px}

/* KPI STRIP */
.kpi-strip{display:grid;grid-template-columns:repeat(4,1fr);gap:12px}
.kpi{background:var(--surface);border:1px solid var(--border);border-radius:12px;padding:16px 20px;position:relative;overflow:hidden}
.kpi::before{content:'';position:absolute;top:0;left:0;right:0;height:3px}
.kpi.blue::before{background:var(--blue)}
.kpi.yellow::before{background:var(--accent)}
.kpi.green::before{background:var(--green)}
.kpi.red::before{background:var(--red)}
.kpi-label{font-size:.65rem;text-transform:uppercase;letter-spacing:1.5px;color:var(--muted);font-family:'JetBrains Mono',monospace;margin-bottom:6px}
.kpi-val{font-size:1.9rem;font-weight:800;line-height:1}
.kpi-sub{font-size:.68rem;font-family:'JetBrains Mono',monospace;color:var(--muted);margin-top:4px}

/* CARDS */
.card{background:var(--surface);border:1px solid var(--border);border-radius:12px;padding:20px}
.card-hdr{display:flex;align-items:center;justify-content:space-between;margin-bottom:16px}
.card-title{font-size:.9rem;font-weight:700;text-transform:uppercase;letter-spacing:.5px;color:var(--text)}
.card-note{font-size:.65rem;font-family:'JetBrains Mono',monospace;color:var(--muted)}
.row2{display:grid;grid-template-columns:1fr 1fr;gap:20px}
.chart-wrap{position:relative;height:280px}
.chart-wrap.tall{height:360px}

/* TABLE */
.tbl-wrap{overflow-x:auto}
table.dtbl{width:100%;border-collapse:collapse;font-size:.78rem}
table.dtbl th{padding:8px 12px;text-align:left;font-family:'JetBrains Mono',monospace;font-size:.65rem;text-transform:uppercase;letter-spacing:1px;color:var(--muted);border-bottom:2px solid var(--border);white-space:nowrap}
table.dtbl td{padding:8px 12px;border-bottom:1px solid var(--dim);white-space:nowrap}
table.dtbl tr:hover td{background:rgba(0,113,206,.06)}
.tbl-name{font-weight:700;color:var(--text)}
.chg-pos{color:var(--green)}
.chg-neg{color:var(--red)}
.badge-merma{background:rgba(255,77,77,.12);border:1px solid rgba(255,77,77,.3);color:var(--red);border-radius:4px;padding:2px 6px;font-size:.65rem;font-family:'JetBrains Mono',monospace}
.badge-ok{background:rgba(0,208,132,.1);border:1px solid rgba(0,208,132,.25);color:var(--green);border-radius:4px;padding:2px 6px;font-size:.65rem;font-family:'JetBrains Mono',monospace}

/* MERMA BARS */
.merma-bar-wrap{display:flex;flex-direction:column;gap:8px}
.merma-row{display:flex;align-items:center;gap:10px}
.merma-label{font-size:.72rem;font-family:'JetBrains Mono',monospace;color:var(--text);min-width:200px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.merma-track{flex:1;height:10px;background:var(--dim);border-radius:5px;overflow:hidden}
.merma-fill{height:100%;border-radius:5px;background:linear-gradient(90deg,var(--accent),var(--red));transition:width .5s}
.merma-val{font-size:.7rem;font-family:'JetBrains Mono',monospace;color:var(--red);min-width:50px;text-align:right}

/* LOADER */
#loader{position:fixed;inset:0;background:var(--bg);display:flex;flex-direction:column;align-items:center;justify-content:center;z-index:999;gap:16px}
.loader-logo{font-size:2rem;font-weight:800;color:#fff;letter-spacing:-1px}
.loader-logo span{color:var(--accent)}
.loader-bar{width:200px;height:3px;background:var(--dim);border-radius:3px;overflow:hidden}
.loader-fill{height:100%;background:var(--blue);animation:load 1.2s ease-in-out infinite}
@keyframes load{0%{transform:translateX(-100%)}100%{transform:translateX(200%)}}
.err{position:fixed;inset:0;background:var(--bg);display:flex;align-items:center;justify-content:center;color:var(--red);font-family:'JetBrains Mono',monospace;font-size:.8rem;padding:40px;text-align:center}
</style>
</head>
<body>
<div id="loader">
  <div class="loader-logo">WAL<span>★</span>MEX</div>
  <div class="loader-bar"><div class="loader-fill"></div></div>
</div>

<div id="app" style="display:none">
  <div class="header">
    <div>
      <div class="walmart-logo">WAL<span>★</span>MEX</div>
      <div class="header-sub">Centro Floricultor de Baja California</div>
    </div>
    <div class="header-sem" id="headerSem">—</div>
  </div>

  <div class="ctrl-bar">
    <div class="view-tabs">
      <button class="view-tab active" id="vtTienda"   onclick="setView('tienda')">Por Tienda</button>
      <button class="view-tab"        id="vtProducto" onclick="setView('producto')">Por Producto</button>
      <button class="view-tab"        id="vtTendencia" onclick="setView('tendencia')">Tendencia</button>
      <button class="view-tab"        id="vtMerma"    onclick="setView('merma')">Merma</button>
    </div>
    <span class="ctrl-label">Semana</span>
    <select class="sem-select" id="semSelect" onchange="onSemChange(this.value)"></select>
    <div class="metric-toggle" id="metricToggle">
      <button class="metric-btn active" id="mU" onclick="setMetric('u')">Unidades</button>
      <button class="metric-btn"        id="m$" onclick="setMetric('$')">$ Venta</button>
    </div>
  </div>

  <!-- VIEW: TIENDA -->
  <div id="viewTienda" class="main">
    <div class="kpi-strip" id="kpiTienda"></div>
    <div class="row2">
      <div class="card">
        <div class="card-hdr"><span class="card-title">Ventas vs Embarque por Tienda</span><span class="card-note" id="barNote">Unidades</span></div>
        <div class="chart-wrap tall"><canvas id="chartTiendaBar"></canvas></div>
      </div>
      <div class="card">
        <div class="card-hdr"><span class="card-title">% de Participación</span><span class="card-note">Ventas semana</span></div>
        <div class="chart-wrap tall"><canvas id="chartTiendaDough"></canvas></div>
      </div>
    </div>
    <div class="card">
      <div class="card-hdr"><span class="card-title">Detalle por Tienda</span><span class="card-note" id="tblTiendaNote">—</span></div>
      <div class="tbl-wrap">
        <table class="dtbl">
          <thead><tr>
            <th>Tienda</th><th>Ventas U</th><th>Embarque U</th><th>% Vta/Emb</th><th>Merma U</th><th>Inv.</th><th>Venta $</th><th>Estado</th>
          </tr></thead>
          <tbody id="tblTiendaBody"></tbody>
        </table>
      </div>
    </div>
  </div>

  <!-- VIEW: PRODUCTO -->
  <div id="viewProducto" class="main" style="display:none">
    <div class="kpi-strip" id="kpiProd"></div>
    <div class="row2">
      <div class="card">
        <div class="card-hdr"><span class="card-title">Ventas vs Embarque por Producto</span><span class="card-note" id="barProdNote">Unidades</span></div>
        <div class="chart-wrap tall"><canvas id="chartProdBar"></canvas></div>
      </div>
      <div class="card">
        <div class="card-hdr"><span class="card-title">Participación de Ventas</span><span class="card-note">% del total</span></div>
        <div class="chart-wrap tall"><canvas id="chartProdDough"></canvas></div>
      </div>
    </div>
    <div class="card">
      <div class="card-hdr"><span class="card-title">Detalle por Producto</span></div>
      <div class="tbl-wrap">
        <table class="dtbl">
          <thead><tr>
            <th>Producto</th><th>Ventas U</th><th>Embarque U</th><th>% Vta/Emb</th><th>Merma U</th><th>Venta $</th><th>Estado</th>
          </tr></thead>
          <tbody id="tblProdBody"></tbody>
        </table>
      </div>
    </div>
  </div>

  <!-- VIEW: TENDENCIA -->
  <div id="viewTendencia" class="main" style="display:none">
    <div class="card">
      <div class="card-hdr"><span class="card-title">Tendencia Semanal — Embarque vs Ventas</span><span class="card-note">Todas las semanas</span></div>
      <div class="chart-wrap tall"><canvas id="chartTend"></canvas></div>
    </div>
    <div class="row2">
      <div class="card">
        <div class="card-hdr"><span class="card-title">Merma Acumulada por Semana</span><span class="card-note">Unidades</span></div>
        <div class="chart-wrap"><canvas id="chartTendMerma"></canvas></div>
      </div>
      <div class="card">
        <div class="card-hdr"><span class="card-title">% Eficiencia (Ventas/Embarque)</span><span class="card-note">por semana</span></div>
        <div class="chart-wrap"><canvas id="chartTendEfic"></canvas></div>
      </div>
    </div>
  </div>

  <!-- VIEW: MERMA -->
  <div id="viewMerma" class="main" style="display:none">
    <div class="kpi-strip" id="kpiMerma"></div>
    <div class="row2">
      <div class="card">
        <div class="card-hdr"><span class="card-title">Merma por Tienda</span><span class="card-note">Unidades no vendidas</span></div>
        <div id="mermaBarsTienda" class="merma-bar-wrap" style="padding:8px 0"></div>
      </div>
      <div class="card">
        <div class="card-hdr"><span class="card-title">Merma por Producto</span><span class="card-note">Unidades no vendidas</span></div>
        <div id="mermaBarsProd" class="merma-bar-wrap" style="padding:8px 0"></div>
      </div>
    </div>
    <div class="card">
      <div class="card-hdr"><span class="card-title">Tendencia de Merma Semanal</span><span class="card-note">Histórico</span></div>
      <div class="chart-wrap"><canvas id="chartMermaHist"></canvas></div>
    </div>
  </div>
</div>

<script>
// ── DATA ─────────────────────────────────────────────────────────────────────
var _raw = atob('__DATA_JSON__');
var DATA = JSON.parse(_raw);

var state = { view:'tienda', semana: null, metric:'u' };
var charts = {};

function fmt(v){ return Math.round(v).toLocaleString('es-MX'); }
function fmtD(v){ return '$'+Math.round(v).toLocaleString('es-MX'); }
function pct(a,b){ return b>0?((a/b)*100).toFixed(1)+'%':'—'; }

// Palette
var TIENDA_COLORS = [
  '#0071ce','#00a3ff','#f5c518','#00d084','#ff4d4d',
  '#a78bfa','#fb923c','#34d399','#f472b6','#60a5fa',
  '#fbbf24','#4ade80','#f87171','#c084fc','#38bdf8','#e879f9'
];
var PROD_COLORS = [
  '#0071ce','#00a3ff','#f5c518','#00d084','#ff4d4d',
  '#a78bfa','#fb923c','#34d399','#f472b6','#60a5fa',
  '#fbbf24','#4ade80','#38bdf8'
];

function destroyChart(id){ if(charts[id]){ charts[id].destroy(); delete charts[id]; } }

// ── INIT ──────────────────────────────────────────────────────────────────────
function init(){
  window.onerror = function(msg,src,l,c,e){
    document.body.innerHTML='<div class="err">Error JS: '+msg+' (linea '+l+')</div>';
  };

  // Build semana selector
  var el = document.getElementById('semSelect');
  DATA.semanas.forEach(function(s){
    var yr = Math.floor(s/100), wk = s%100;
    var opt = document.createElement('option');
    opt.value = s;
    opt.textContent = yr+' · W'+String(wk).padStart(2,'0');
    el.appendChild(opt);
  });
  // Default to latest semana
  state.semana = DATA.semanas[DATA.semanas.length-1];
  el.value = state.semana;

  updateHeader();
  renderView();
  document.getElementById('loader').style.display='none';
  document.getElementById('app').style.display='block';
}

function updateHeader(){
  var s=state.semana, yr=Math.floor(s/100), wk=s%100;
  document.getElementById('headerSem').textContent = yr+' · Semana '+wk;
}

function setView(v){
  state.view=v;
  ['tienda','producto','tendencia','merma'].forEach(function(n){
    document.getElementById('viewTienda'.replace('tienda',n.charAt(0).toUpperCase()+n.slice(1))||'view'+n.charAt(0).toUpperCase()+n.slice(1)).style.display = v===n?'':'none';
    document.getElementById('vt'+n.charAt(0).toUpperCase()+n.slice(1)).classList.toggle('active', v===n);
  });
  // Fix IDs
  document.getElementById('viewTienda').style.display    = v==='tienda'?'':'none';
  document.getElementById('viewProducto').style.display  = v==='producto'?'':'none';
  document.getElementById('viewTendencia').style.display = v==='tendencia'?'':'none';
  document.getElementById('viewMerma').style.display     = v==='merma'?'':'none';
  ['vtTienda','vtProducto','vtTendencia','vtMerma'].forEach(function(id){
    document.getElementById(id).classList.remove('active');
  });
  document.getElementById('vt'+v.charAt(0).toUpperCase()+v.slice(1)).classList.add('active');
  renderView();
}

function onSemChange(val){
  state.semana = parseInt(val);
  updateHeader();
  renderView();
}

function setMetric(m){
  state.metric = m;
  document.getElementById('mU').classList.toggle('active', m==='u');
  document.getElementById('m$').classList.toggle('active', m==='$');
  renderView();
}

function renderView(){
  if(state.view==='tienda')    renderTienda();
  else if(state.view==='producto')  renderProducto();
  else if(state.view==='tendencia') renderTendencia();
  else if(state.view==='merma')     renderMerma();
}

// ── HELPERS ───────────────────────────────────────────────────────────────────
function getTiendaData(sem){
  var key = String(sem);
  var d = DATA.por_tienda[key] || {};
  return DATA.tiendas.map(function(t){ return {tienda:t, ...(d[t]||{ventas_u:0,'ventas_$':0,embarque_u:0,'embarque_$':0,merma_u:0,inventario:0})}; });
}
function getProdData(sem){
  var key = String(sem);
  var d = DATA.por_prod[key] || {};
  return DATA.productos.map(function(p){ return {producto:p, ...(d[p]||{ventas_u:0,'ventas_$':0,embarque_u:0,'embarque_$':0,merma_u:0,inventario:0})}; });
}

// ── TIENDA ────────────────────────────────────────────────────────────────────
function renderTienda(){
  var rows = getTiendaData(state.semana);
  var totalV = rows.reduce(function(a,r){return a+r.ventas_u;},0);
  var totalE = rows.reduce(function(a,r){return a+r.embarque_u;},0);
  var totalM = rows.reduce(function(a,r){return a+r.merma_u;},0);
  var total$ = rows.reduce(function(a,r){return a+r['ventas_$'];},0);
  var efic   = totalE>0?((totalV/totalE)*100).toFixed(1):0;

  document.getElementById('kpiTienda').innerHTML = [
    {label:'Ventas Totales',val:fmt(totalV)+' u',sub:fmtD(total$),cls:'blue'},
    {label:'Embarque Total',val:fmt(totalE)+' u',sub:'unidades enviadas',cls:'yellow'},
    {label:'Merma Total',val:fmt(totalM)+' u',sub:pct(totalM,totalE)+' del embarque',cls:'red'},
    {label:'Eficiencia',val:efic+'%',sub:'Ventas / Embarque',cls:'green'},
  ].map(function(k){
    return '<div class="kpi '+k.cls+'"><div class="kpi-label">'+k.label+'</div>'+
           '<div class="kpi-val">'+k.val+'</div><div class="kpi-sub">'+k.sub+'</div></div>';
  }).join('');

  var labels = rows.map(function(r){return r.tienda.replace('SC ','');});
  var ventasD = rows.map(function(r){return state.metric==='u'?r.ventas_u:r['ventas_$'];});
  var embD    = rows.map(function(r){return state.metric==='u'?r.embarque_u:r['embarque_$'];});

  document.getElementById('barNote').textContent = state.metric==='u'?'Unidades':'$ Venta';

  destroyChart('tiendaBar');
  charts.tiendaBar = new Chart(document.getElementById('chartTiendaBar').getContext('2d'),{
    type:'bar',
    data:{
      labels:labels,
      datasets:[
        {label:'Ventas',data:ventasD,backgroundColor:'rgba(0,113,206,.8)',borderRadius:4,borderSkipped:false},
        {label:'Embarque',data:embD,backgroundColor:'rgba(245,197,24,.5)',borderRadius:4,borderSkipped:false},
      ]
    },
    options:{responsive:true,maintainAspectRatio:false,plugins:{legend:{labels:{color:'#5a7a9a',font:{family:'JetBrains Mono',size:11}}}},
      scales:{x:{ticks:{color:'#5a7a9a',font:{size:9}},grid:{color:'#1a2840'}},y:{ticks:{color:'#5a7a9a',font:{size:10}},grid:{color:'#1a2840'}}}}
  });

  var ventasTot = rows.reduce(function(a,r){return a+r.ventas_u;},0)||1;
  destroyChart('tiendaDough');
  charts.tiendaDough = new Chart(document.getElementById('chartTiendaDough').getContext('2d'),{
    type:'doughnut',
    data:{
      labels:labels,
      datasets:[{data:rows.map(function(r){return r.ventas_u;}),backgroundColor:TIENDA_COLORS,borderWidth:0,hoverOffset:8}]
    },
    options:{responsive:true,maintainAspectRatio:false,cutout:'65%',
      plugins:{legend:{position:'right',labels:{color:'#5a7a9a',font:{size:9},boxWidth:10}}}}
  });

  // Table
  var sorted = rows.slice().sort(function(a,b){return b.ventas_u-a.ventas_u;});
  document.getElementById('tblTiendaBody').innerHTML = sorted.map(function(r,i){
    var efic = r.embarque_u>0?((r.ventas_u/r.embarque_u)*100).toFixed(1):null;
    var mermaOk = r.merma_u===0||r.embarque_u===0;
    return '<tr>'+
      '<td class="tbl-name">'+r.tienda.replace('SC ','')+'</td>'+
      '<td style="color:#0071ce;font-weight:700">'+fmt(r.ventas_u)+'</td>'+
      '<td style="color:#f5c518">'+fmt(r.embarque_u)+'</td>'+
      '<td>'+(efic!==null?'<span class="'+(parseFloat(efic)>=80?'chg-pos':'chg-neg')+'">'+efic+'%</span>':'—')+'</td>'+
      '<td><span class="'+(mermaOk?'badge-ok':'badge-merma')+'">'+fmt(r.merma_u)+'</span></td>'+
      '<td style="color:#5a7a9a">'+fmt(r.inventario)+'</td>'+
      '<td style="color:#5a7a9a">'+fmtD(r['ventas_$'])+'</td>'+
      '<td>'+(mermaOk?'<span class="badge-ok">OK</span>':'<span class="badge-merma">⚠ Merma</span>')+'</td>'+
      '</tr>';
  }).join('');

  document.getElementById('tblTiendaNote').textContent = 'W'+String(state.semana%100).padStart(2,'0')+' · '+Math.floor(state.semana/100);
}

// ── PRODUCTO ──────────────────────────────────────────────────────────────────
function renderProducto(){
  var rows = getProdData(state.semana);
  var totalV = rows.reduce(function(a,r){return a+r.ventas_u;},0);
  var totalE = rows.reduce(function(a,r){return a+r.embarque_u;},0);
  var totalM = rows.reduce(function(a,r){return a+r.merma_u;},0);
  var total$ = rows.reduce(function(a,r){return a+r['ventas_$'];},0);

  document.getElementById('kpiProd').innerHTML = [
    {label:'Productos Activos',val:rows.filter(function(r){return r.ventas_u>0;}).length+' / '+rows.length,sub:'con ventas esta semana',cls:'blue'},
    {label:'Ventas Totales',val:fmt(totalV)+' u',sub:fmtD(total$),cls:'yellow'},
    {label:'Merma Total',val:fmt(totalM)+' u',sub:pct(totalM,totalE)+' del embarque',cls:'red'},
    {label:'Embarque Total',val:fmt(totalE)+' u',sub:'enviado a tiendas',cls:'green'},
  ].map(function(k){
    return '<div class="kpi '+k.cls+'"><div class="kpi-label">'+k.label+'</div>'+
           '<div class="kpi-val">'+k.val+'</div><div class="kpi-sub">'+k.sub+'</div></div>';
  }).join('');

  var labels = rows.map(function(r){return r.producto.replace('BQT ','');});
  var ventasD = rows.map(function(r){return state.metric==='u'?r.ventas_u:r['ventas_$'];});
  var embD    = rows.map(function(r){return state.metric==='u'?r.embarque_u:r['embarque_$'];});

  destroyChart('prodBar');
  charts.prodBar = new Chart(document.getElementById('chartProdBar').getContext('2d'),{
    type:'bar',
    data:{labels:labels,datasets:[
      {label:'Ventas',data:ventasD,backgroundColor:'rgba(0,113,206,.8)',borderRadius:4,borderSkipped:false},
      {label:'Embarque',data:embD,backgroundColor:'rgba(245,197,24,.5)',borderRadius:4,borderSkipped:false},
    ]},
    options:{responsive:true,maintainAspectRatio:false,
      plugins:{legend:{labels:{color:'#5a7a9a',font:{family:'JetBrains Mono',size:11}}}},
      scales:{x:{ticks:{color:'#5a7a9a',font:{size:9}},grid:{color:'#1a2840'}},y:{ticks:{color:'#5a7a9a'},grid:{color:'#1a2840'}}}}
  });

  destroyChart('prodDough');
  charts.prodDough = new Chart(document.getElementById('chartProdDough').getContext('2d'),{
    type:'doughnut',
    data:{labels:labels,datasets:[{data:rows.map(function(r){return r.ventas_u;}),backgroundColor:PROD_COLORS,borderWidth:0,hoverOffset:8}]},
    options:{responsive:true,maintainAspectRatio:false,cutout:'65%',
      plugins:{legend:{position:'right',labels:{color:'#5a7a9a',font:{size:9},boxWidth:10}}}}
  });

  var sorted = rows.slice().sort(function(a,b){return b.ventas_u-a.ventas_u;});
  document.getElementById('tblProdBody').innerHTML = sorted.map(function(r){
    var efic = r.embarque_u>0?((r.ventas_u/r.embarque_u)*100).toFixed(1):null;
    var mermaOk = r.merma_u===0||r.embarque_u===0;
    return '<tr>'+
      '<td class="tbl-name">'+r.producto.replace('BQT ','')+'</td>'+
      '<td style="color:#0071ce;font-weight:700">'+fmt(r.ventas_u)+'</td>'+
      '<td style="color:#f5c518">'+fmt(r.embarque_u)+'</td>'+
      '<td>'+(efic!==null?'<span class="'+(parseFloat(efic)>=80?'chg-pos':'chg-neg')+'">'+efic+'%</span>':'—')+'</td>'+
      '<td><span class="'+(mermaOk?'badge-ok':'badge-merma')+'">'+fmt(r.merma_u)+'</span></td>'+
      '<td style="color:#5a7a9a">'+fmtD(r['ventas_$'])+'</td>'+
      '<td>'+(mermaOk?'<span class="badge-ok">OK</span>':'<span class="badge-merma">⚠ Merma</span>')+'</td>'+
      '</tr>';
  }).join('');
}

// ── TENDENCIA ─────────────────────────────────────────────────────────────────
function renderTendencia(){
  var td = DATA.tendencia;
  var labels = td.map(function(r){return Math.floor(r.semana/100)+'W'+String(r.semana%100).padStart(2,'0');});
  var ventas  = td.map(function(r){return state.metric==='u'?r.ventas_u:r['ventas_$'];});
  var embarque= td.map(function(r){return state.metric==='u'?r.embarque_u:r['embarque_$'];});
  var merma   = td.map(function(r){return r.merma_u;});
  var efic    = td.map(function(r){return r.embarque_u>0?parseFloat(((r.ventas_u/r.embarque_u)*100).toFixed(1)):0;});

  destroyChart('tend');
  charts.tend = new Chart(document.getElementById('chartTend').getContext('2d'),{
    type:'line',
    data:{labels:labels,datasets:[
      {label:'Ventas',data:ventas,borderColor:'#0071ce',backgroundColor:'rgba(0,113,206,.15)',fill:true,tension:.4,borderWidth:2.5,pointRadius:4,pointBackgroundColor:'#0071ce'},
      {label:'Embarque',data:embarque,borderColor:'#f5c518',backgroundColor:'rgba(245,197,24,.1)',fill:true,tension:.4,borderWidth:2,borderDash:[6,3],pointRadius:3,pointBackgroundColor:'#f5c518'},
    ]},
    options:{responsive:true,maintainAspectRatio:false,
      plugins:{legend:{labels:{color:'#5a7a9a',font:{family:'JetBrains Mono',size:11}}}},
      scales:{x:{ticks:{color:'#5a7a9a',font:{size:10}},grid:{color:'#1a2840'}},y:{ticks:{color:'#5a7a9a'},grid:{color:'#1a2840'}}}}
  });

  destroyChart('tendMerma');
  charts.tendMerma = new Chart(document.getElementById('chartTendMerma').getContext('2d'),{
    type:'bar',
    data:{labels:labels,datasets:[{label:'Merma (u)',data:merma,backgroundColor:'rgba(255,77,77,.7)',borderRadius:4,borderSkipped:false}]},
    options:{responsive:true,maintainAspectRatio:false,plugins:{legend:{display:false}},
      scales:{x:{ticks:{color:'#5a7a9a',font:{size:9}},grid:{color:'#1a2840'}},y:{ticks:{color:'#5a7a9a'},grid:{color:'#1a2840'}}}}
  });

  destroyChart('tendEfic');
  charts.tendEfic = new Chart(document.getElementById('chartTendEfic').getContext('2d'),{
    type:'line',
    data:{labels:labels,datasets:[{label:'% Eficiencia',data:efic,borderColor:'#00d084',backgroundColor:'rgba(0,208,132,.1)',fill:true,tension:.4,borderWidth:2,pointRadius:4,pointBackgroundColor:'#00d084'}]},
    options:{responsive:true,maintainAspectRatio:false,plugins:{legend:{display:false}},
      scales:{x:{ticks:{color:'#5a7a9a',font:{size:9}},grid:{color:'#1a2840'}},
        y:{min:0,max:100,ticks:{color:'#5a7a9a',callback:function(v){return v+'%'}},grid:{color:'#1a2840'}}}}
  });
}

// ── MERMA ─────────────────────────────────────────────────────────────────────
function renderMerma(){
  var tRows = getTiendaData(state.semana);
  var pRows = getProdData(state.semana);
  var totalM = tRows.reduce(function(a,r){return a+r.merma_u;},0);
  var totalE = tRows.reduce(function(a,r){return a+r.embarque_u;},0);
  var totalV = tRows.reduce(function(a,r){return a+r.ventas_u;},0);
  var pctM   = totalE>0?((totalM/totalE)*100).toFixed(1):0;
  var topT   = tRows.slice().sort(function(a,b){return b.merma_u-a.merma_u;})[0];

  document.getElementById('kpiMerma').innerHTML = [
    {label:'Merma Total',val:fmt(totalM)+' u',sub:pctM+'% del embarque',cls:'red'},
    {label:'Embarque Total',val:fmt(totalE)+' u',sub:'unidades enviadas',cls:'yellow'},
    {label:'Ventas Totales',val:fmt(totalV)+' u',sub:'unidades vendidas',cls:'blue'},
    {label:'Mayor Merma',val:topT?(topT.tienda.replace('SC ','')+' '+fmt(topT.merma_u)+'u'):'—',sub:'tienda con mayor merma',cls:'red'},
  ].map(function(k){
    return '<div class="kpi '+k.cls+'"><div class="kpi-label">'+k.label+'</div>'+
           '<div class="kpi-val" style="font-size:1.4rem">'+k.val+'</div><div class="kpi-sub">'+k.sub+'</div></div>';
  }).join('');

  // Merma bars tienda
  var maxMT = Math.max.apply(null, tRows.map(function(r){return r.merma_u;})) || 1;
  var sortedT = tRows.slice().sort(function(a,b){return b.merma_u-a.merma_u;});
  document.getElementById('mermaBarsTienda').innerHTML = sortedT.map(function(r){
    var w = (r.merma_u/maxMT*100).toFixed(1);
    return '<div class="merma-row">'+
      '<div class="merma-label">'+r.tienda.replace('SC ','')+'</div>'+
      '<div class="merma-track"><div class="merma-fill" style="width:'+w+'%"></div></div>'+
      '<div class="merma-val">'+fmt(r.merma_u)+'</div></div>';
  }).join('');

  // Merma bars producto
  var maxMP = Math.max.apply(null, pRows.map(function(r){return r.merma_u;})) || 1;
  var sortedP = pRows.slice().sort(function(a,b){return b.merma_u-a.merma_u;});
  document.getElementById('mermaBarsProd').innerHTML = sortedP.map(function(r){
    var w = (r.merma_u/maxMP*100).toFixed(1);
    return '<div class="merma-row">'+
      '<div class="merma-label">'+r.producto.replace('BQT ','')+'</div>'+
      '<div class="merma-track"><div class="merma-fill" style="width:'+w+'%"></div></div>'+
      '<div class="merma-val">'+fmt(r.merma_u)+'</div></div>';
  }).join('');

  // Merma history chart
  var td = DATA.tendencia;
  var labels = td.map(function(r){return 'W'+String(r.semana%100).padStart(2,'0');});
  var mermas  = td.map(function(r){return r.merma_u;});

  destroyChart('mermaHist');
  charts.mermaHist = new Chart(document.getElementById('chartMermaHist').getContext('2d'),{
    type:'bar',
    data:{labels:labels,datasets:[{label:'Merma (u)',data:mermas,backgroundColor:mermas.map(function(v,i){return i===mermas.length-1?'rgba(255,77,77,.9)':'rgba(255,77,77,.4)';}),borderRadius:4,borderSkipped:false}]},
    options:{responsive:true,maintainAspectRatio:false,
      plugins:{legend:{display:false}},
      scales:{x:{ticks:{color:'#5a7a9a',font:{size:10}},grid:{color:'#1a2840'}},y:{ticks:{color:'#5a7a9a'},grid:{color:'#1a2840'}}}}
  });
}

window.addEventListener('load', init);
</script>
</body>
</html>
"""

def build_html():
    data_json = base64.b64encode(
        json.dumps(DATA, ensure_ascii=True, default=str).encode('utf-8')
    ).decode('ascii')
    return HTML.replace('__DATA_JSON__', data_json)

components.html(build_html(), height=900, scrolling=True)
