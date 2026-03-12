"""
Walmex Dashboard — CFBC
Reporte ejecutivo estilo Walmart
"""
import json, base64, openpyxl
from collections import defaultdict
from pathlib import Path
import streamlit as st
import streamlit.components.v1 as components

st.set_page_config(page_title="Walmex · CFBC", layout="wide", initial_sidebar_state="collapsed")
st.markdown("""<style>
/* Eliminar TODO el padding/margin de Streamlit */
header, footer, [data-testid='stToolbar'], [data-testid='stDecoration'],
[data-testid='stStatusWidget'] { display:none !important; visibility:hidden !important; height:0 !important; }
section[data-testid='stSidebar'] { display:none !important; }
.main .block-container {
    padding-top: 0 !important;
    padding-bottom: 0 !important;
    padding-left: 0 !important;
    padding-right: 0 !important;
    max-width: 100% !important;
    margin: 0 !important;
}
.main { padding: 0 !important; overflow: hidden !important; }
.stApp { margin: 0 !important; }
[data-testid='stAppViewContainer'] { padding: 0 !important; margin: 0 !important; }
[data-testid='stVerticalBlock'] { gap: 0 !important; padding: 0 !important; }
div[data-testid='stHtml'] { padding: 0 !important; margin: 0 !important; line-height: 0 !important; }
iframe { display: block !important; margin: 0 !important; border: none !important; }
/* Ocultar badge Made with Streamlit */
footer { display: none !important; }
[data-testid="stBottom"] { display: none !important; }
.viewerBadge_container__r5tak { display: none !important; }
.styles_viewerBadge__CvC9N { display: none !important; }
a[href="https://streamlit.io"] { display: none !important; }
</style>""", unsafe_allow_html=True)

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
        if not producto or not tienda or not semana: continue
        records.append({
            'producto': producto, 'tienda': tienda, 'semana': semana,
            'ventas_u': sv(row[18]),
            'embarque_u': sv(row[20]),
            'merma_u': max(0.0, sv(row[20]) - sv(row[18])),
        })

    semanas   = sorted(set(r['semana'] for r in records))
    tiendas   = sorted(set(r['tienda']  for r in records))
    productos = sorted(set(r['producto'] for r in records))

    by_stp = defaultdict(lambda: defaultdict(lambda: defaultdict(lambda: defaultdict(float))))
    for r in records:
        by_stp[r['semana']][r['tienda']][r['producto']]['ventas_u']   += r['ventas_u']
        by_stp[r['semana']][r['tienda']][r['producto']]['embarque_u'] += r['embarque_u']
        by_stp[r['semana']][r['tienda']][r['producto']]['merma_u']    += r['merma_u']

    result = {}
    for t in tiendas:
        result[t] = {}
        for s in semanas:
            idx    = semanas.index(s)
            last12 = semanas[max(0, idx-11):idx+1]
            last3  = semanas[max(0, idx-2):idx+1]
            prod_data = {}
            for p in productos:
                v12   = sum(by_stp[sem][t][p]['ventas_u']   for sem in last12)
                v3    = sum(by_stp[sem][t][p]['ventas_u']   for sem in last3)
                emb   = by_stp[s][t][p]['embarque_u']
                m3    = sum(by_stp[sem][t][p]['merma_u']    for sem in last3)
                avg   = v12 / len(last12) if last12 else 0
                prod_data[p] = {
                    'v12': round(v12), 'v3': round(v3),
                    'emb': round(emb), 'm3': round(m3),
                    'avg': round(avg, 1), 'proj': round(avg),
                    'pct_merma': round(m3/emb*100) if emb > 0 else 0,
                }
            result[t][s] = prod_data

    return {
        'semanas':   semanas,
        'tiendas':   tiendas,
        'productos': productos,
        'data': {t: {str(s): v for s, v in sv2.items()} for t, sv2 in result.items()},
    }

EXCEL_PATH = "Analisis_Walmart.xlsx"
if not Path(EXCEL_PATH).exists():
    EXCEL_PATH = "/mnt/user-data/uploads/Analisis_Walmart.xlsx"

DATA = cargar_datos(EXCEL_PATH)

HTML = r"""<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<style>
*{box-sizing:border-box;margin:0;padding:0}
body{background:#fff;font-family:Arial,sans-serif;font-size:12px;color:#111}

/* ── HEADER ── */
.hdr{display:flex;align-items:center;justify-content:space-between;padding:6px 16px 4px;border-bottom:1px solid #ccc}
.wm-logo{display:flex;align-items:center;gap:4px}
.wm-text{font-size:1.2rem;font-weight:700;color:#0071ce;letter-spacing:-0.5px}
.wm-spark{color:#ffc220;font-size:1.3rem;line-height:1}
.hdr-right{text-align:right;font-size:.72rem;color:#333;line-height:1.6}
.hdr-tienda{padding:3px 16px 4px;font-size:.78rem;color:#333;border-bottom:1px solid #ddd}
.hdr-tienda strong{font-size:.8rem}

/* ── CONTROLS ── */
.ctrl{display:flex;align-items:center;gap:8px;padding:5px 16px;background:#f5f7fa;border-bottom:1px solid #ddd;flex-wrap:wrap}
.ctrl label{font-size:.7rem;color:#555;font-weight:600}
select{border:1px solid #bbb;border-radius:4px;padding:3px 7px;font-size:.72rem;cursor:pointer;background:#fff}
.chip-wrap{display:flex;flex-wrap:wrap;gap:4px;flex:1}
.chip{padding:2px 9px;border-radius:12px;font-size:.67rem;cursor:pointer;border:1px solid #bbb;color:#333;background:#fff;transition:.15s}
.chip:hover{border-color:#0071ce;color:#0071ce}
.chip.on{background:#0071ce;color:#fff;border-color:#0071ce}

/* ── 4 TABLE GRID ── */
.grid{display:grid;grid-template-columns:1fr 1fr;padding:8px 16px;gap:8px}

.box{border:1px solid #bbb;border-radius:4px;overflow:hidden}
.box-hdr{background:#f0f0f0;border-bottom:1px solid #bbb;padding:4px 10px;text-align:center;font-size:.74rem;font-weight:700;color:#111}

table.t{width:100%;border-collapse:collapse}
table.t th{padding:3px 10px;font-size:.67rem;font-weight:700;color:#333;border-bottom:1px solid #ccc;text-align:right;white-space:nowrap;background:#fafafa}
table.t th:first-child{text-align:left}
table.t td{padding:2px 10px;font-size:.72rem;border-bottom:none;text-align:right;color:#222;white-space:nowrap}
table.t td:first-child{text-align:left;color:#111}
table.t tr.total td{font-weight:700;border-top:1px solid #ddd;background:#f5f5f5}
table.t tr:hover:not(.total) td{background:#f0f7ff}
.red{color:#c00;font-weight:600}
.bold{font-weight:700}

/* ── LOADER ── */
#loader{position:fixed;inset:0;background:#fff;display:flex;align-items:center;justify-content:center;z-index:99;flex-direction:column;gap:10px}
.ld-txt{font-size:.85rem;color:#0071ce;font-weight:600}
.ld-bar{width:160px;height:3px;background:#dde;border-radius:2px;overflow:hidden}
.ld-fill{height:100%;background:#0071ce;animation:ld .9s ease-in-out infinite}
@keyframes ld{0%{transform:translateX(-100%)}100%{transform:translateX(200%)}}
</style>
</head>
<body>

<div id="loader"><div class="ld-txt">Cargando...</div><div class="ld-bar"><div class="ld-fill"></div></div></div>

<div id="app" style="display:none">

  <!-- HEADER -->
  <div class="hdr">
    <div class="wm-logo">
      <div class="wm-text">Walmart</div>
      <div class="wm-spark">&#10022;</div>
    </div>
    <div class="hdr-right">
      <div id="hdrFecha">—</div>
      <div>Semana&nbsp;&nbsp;<strong id="hdrSem">—</strong></div>
    </div>
  </div>
  <div class="hdr-tienda">Nombre de Tienda&nbsp;&nbsp;<strong id="hdrTienda">—</strong></div>

  <!-- CONTROLS -->
  <div class="ctrl">
    <label>Semana:</label>
    <select id="semSel" onchange="onSem(this.value)"></select>
    <label>Tienda:</label>
    <div class="chip-wrap" id="chips"></div>
  </div>

  <!-- 4 TABLES -->
  <div class="grid">

    <div class="box">
      <div class="box-hdr">Ventas Históricas</div>
      <table class="t"><thead><tr><th>Producto</th><th>12 Semanas</th><th>3 Semanas</th></tr></thead>
      <tbody id="tHist"></tbody></table>
    </div>

    <div class="box">
      <div class="box-hdr">Índice de Merma por Artículo Últimas 3 Semanas</div>
      <table class="t"><thead><tr><th>Producto</th><th>Embarque</th><th>3 Semanas</th></tr></thead>
      <tbody id="tMerma"></tbody></table>
    </div>

    <div class="box">
      <div class="box-hdr">Venta Promedio Semanal</div>
      <table class="t"><thead><tr><th>Producto</th><th>Promedio</th></tr></thead>
      <tbody id="tAvg"></tbody></table>
    </div>

    <div class="box">
      <div class="box-hdr" id="projTitle">Proyección Semana Siguiente</div>
      <table class="t"><thead><tr><th>Producto</th><th>Proyección</th></tr></thead>
      <tbody id="tProj"></tbody></table>
    </div>

  </div>
</div>

<script>
var DATA = JSON.parse(atob('__DATA_JSON__'));
var state = { semana: null, tienda: null };

var DIAS = ['domingo','lunes','martes','miércoles','jueves','viernes','sábado'];
var MESES = ['enero','febrero','marzo','abril','mayo','junio','julio','agosto','septiembre','octubre','noviembre','diciembre'];

function fmt(v){ return Math.round(v||0).toLocaleString('es-MX'); }

function init(){
  window.onerror = function(m,s,l){
    document.body.innerHTML='<p style="padding:20px;color:red">Error: '+m+' (línea '+l+')</p>';
  };

  // Semanas
  var sel = document.getElementById('semSel');
  DATA.semanas.forEach(function(s){
    var opt = document.createElement('option');
    opt.value = s;
    var yr = Math.floor(s/100), wk = s%100;
    opt.textContent = yr+' · Semana '+String(wk).padStart(2,'0');
    sel.appendChild(opt);
  });
  state.semana = DATA.semanas[DATA.semanas.length-1];
  sel.value = state.semana;
  state.tienda = DATA.tiendas[0];

  buildChips();
  updateHeader();
  render();

  document.getElementById('loader').style.display = 'none';
  document.getElementById('app').style.display = 'block';
}

function buildChips(){
  document.getElementById('chips').innerHTML = DATA.tiendas.map(function(t){
    var n = t.replace('SC ','');
    return '<button class="chip'+(t===state.tienda?' on':'')+'" onclick="selTienda(\''+t+'\')">'+n+'</button>';
  }).join('');
}

function selTienda(t){ state.tienda=t; buildChips(); updateHeader(); render(); }

function onSem(v){ state.semana=parseInt(v); updateHeader(); render(); }

function updateHeader(){
  var now = new Date();
  var dia = DIAS[now.getDay()];
  var fecha = dia.charAt(0).toUpperCase()+dia.slice(1)+', '+now.getDate()+' de '+MESES[now.getMonth()]+' de '+now.getFullYear();
  document.getElementById('hdrFecha').textContent = fecha;
  document.getElementById('hdrSem').textContent = state.semana%100;
  document.getElementById('hdrTienda').textContent = state.tienda;
  var nxtWk = (state.semana%100)+1;
  document.getElementById('projTitle').textContent = 'Proyección Semana '+nxtWk;
}

function getD(){
  var key = String(state.semana);
  return (DATA.data[state.tienda]&&DATA.data[state.tienda][key]) || {};
}

function render(){
  var d = getD();
  var prods = DATA.productos;

  var totV12=0, totV3=0, totEmb=0, totM3=0, totAvg=0, totProj=0;

  var histRows='', mermaRows='', avgRows='', projRows='';

  prods.forEach(function(p){
    var v = d[p]||{v12:0,v3:0,emb:0,m3:0,avg:0,proj:0,pct_merma:0};
    var name = p.replace('BQT ','');
    totV12+=v.v12; totV3+=v.v3; totEmb+=v.emb; totM3+=v.m3; totAvg+=v.avg; totProj+=v.proj;

    histRows += '<tr><td>'+name+'</td><td>'+fmt(v.v12)+'</td><td>'+fmt(v.v3)+'</td></tr>';

    var mCls = v.m3>0?'red':'';
    mermaRows += '<tr><td>'+name+'</td><td>'+fmt(v.emb)+'</td>'+
      '<td class="'+mCls+'">'+fmt(v.m3)+'</td></tr>';

    avgRows += '<tr><td>'+name+'</td><td>'+Math.round(v.avg)+'</td></tr>';
    projRows += '<tr><td>'+name+'</td><td class="bold">'+fmt(v.proj)+'</td></tr>';
  });

  var pctTot = totEmb>0?Math.round(totM3/totEmb*100)+'%':'0%';

  histRows  += '<tr class="total"><td>Total</td><td>'+fmt(totV12)+'</td><td>'+fmt(totV3)+'</td></tr>';
  mermaRows += '<tr class="total"><td>Total</td><td>'+fmt(totEmb)+'</td><td class="red">'+fmt(totM3)+'</td></tr>';
  avgRows   += '<tr class="total"><td>Total</td><td>'+Math.round(totAvg)+'</td></tr>';
  projRows  += '<tr class="total"><td>Total</td><td>'+fmt(totProj)+'</td></tr>';

  document.getElementById('tHist').innerHTML  = histRows;
  document.getElementById('tMerma').innerHTML = mermaRows;
  document.getElementById('tAvg').innerHTML   = avgRows;
  document.getElementById('tProj').innerHTML  = projRows;
}

window.addEventListener('load', init);

// Eliminar padding del frame padre de Streamlit
(function fixParent(){
  try {
    var p = window.parent.document;
    var style = p.createElement('style');
    style.textContent = [
      '.main .block-container{padding:0!important;margin:0!important}',
      '.main{padding:0!important}',
      '[data-testid="stAppViewContainer"]{padding:0!important}',
      '[data-testid="stVerticalBlock"]{gap:0!important}',
      'header,[data-testid="stToolbar"],[data-testid="stDecoration"]{display:none!important}',
      'iframe{margin:0!important}',
      'section[data-testid="stMain"]{padding:0!important}',
      '.stMainBlockContainer{padding:0!important}',
      '[data-testid="manage-app-button"]{display:none!important}',
      '.stDeployButton{display:none!important}',
      '#MainMenu{display:none!important}',
      'button[kind="header"]{display:none!important}',
      '[data-testid="manage-app-button"]{display:none!important}',
      '.viewerBadge_container__r5tak{display:none!important}',
      '.styles_viewerBadge__CvC9N{display:none!important}',
      'a[href="https://streamlit.io"]{display:none!important}',
      '#stDecoration{display:none!important}',
      'footer{display:none!important}',
      '[data-testid="stBottom"]{display:none!important}',
    ].join('');
    p.head.appendChild(style);
  } catch(e){}
  // Resize iframe to full viewport
  try {
    var frames = window.parent.document.querySelectorAll('iframe');
    frames.forEach(function(f){
      f.style.height = window.parent.innerHeight + 'px';
      f.style.width  = '100%';
    });
  } catch(e){}
})();
</script>
</body>
</html>"""

def build_html():
    data_json = base64.b64encode(
        json.dumps(DATA, ensure_ascii=True, default=str).encode('utf-8')
    ).decode('ascii')
    return HTML.replace('__DATA_JSON__', data_json)

components.html(build_html(), height=980, scrolling=False)
