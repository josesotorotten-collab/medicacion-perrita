from flask import Flask, request, jsonify
from datetime import datetime, timedelta
from apscheduler.schedulers.background import BackgroundScheduler
import sqlite3
import requests
import pytz
import atexit
import os

app = Flask(__name__)

DB_PATH = os.environ.get("DB_PATH", "medicaciones.db")
if os.path.dirname(DB_PATH):
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)

TIMEZONE = pytz.timezone("America/Argentina/Buenos_Aires")

MEDICATIONS = [
    {"id": "gota_dolor",      "name": "Gota Dolor",          "description": "Gota para el dolor",              "interval_hours": 12, "color": "#e07b54", "icon": "💊"},
    {"id": "tratamiento_crema","name": "Tratamiento + Crema", "description": "Gota Tratamiento y Crema (juntas)","interval_hours": 8,  "color": "#5b8dd9", "icon": "🩹"},
]

HTML = """<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="UTF-8"/>
<meta name="viewport" content="width=device-width,initial-scale=1"/>
<title>Medicación 🐾</title>
<style>
*{box-sizing:border-box;margin:0;padding:0}
:root{--ok:#3db87a;--warn:#f0a500;--danger:#e04e4e;--border:#e8e0d8;--bg:#fdf6f0;--surface:#fff;--muted:#888;--r:14px}
body{font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;background:var(--bg);min-height:100vh;padding-bottom:40px}
header{background:linear-gradient(135deg,#e07b54,#c9614a);color:#fff;text-align:center;padding:28px 20px 22px}
header h1{font-size:1.55rem;font-weight:700}
header p{margin-top:4px;font-size:.88rem;opacity:.85}
main{max-width:520px;margin:0 auto;padding:20px 16px 0}
.card{background:var(--surface);border-radius:var(--r);box-shadow:0 2px 16px rgba(0,0,0,.08);margin-bottom:16px;overflow:hidden}
.card-head{display:flex;align-items:center;gap:12px;padding:16px 18px 12px;border-bottom:1px solid var(--border)}
.card-icon{font-size:1.5rem}
.card-title h2{font-size:1rem;font-weight:700}
.card-title p{font-size:.78rem;color:var(--muted);margin-top:2px}
.card-body{padding:14px 18px}
.row{display:flex;align-items:center;justify-content:space-between;margin-bottom:12px}
.badge{display:inline-flex;align-items:center;padding:4px 11px;border-radius:99px;font-size:.78rem;font-weight:600}
.badge.ok{background:#e8f7ef;color:var(--ok)}.badge.warn{background:#fff4dc;color:var(--warn)}.badge.danger{background:#fdeaea;color:var(--danger)}.badge.none{background:#f0f0f0;color:var(--muted)}
.itag{font-size:.76rem;color:var(--muted);background:#f5f0eb;padding:3px 9px;border-radius:99px}
.times{display:grid;grid-template-columns:1fr 1fr;gap:8px;margin-bottom:12px}
.tblock{background:#faf7f4;border-radius:9px;padding:9px 11px}
.tblock .lbl{font-size:.7rem;color:var(--muted);text-transform:uppercase;letter-spacing:.4px;margin-bottom:3px}
.tblock .val{font-size:.92rem;font-weight:600}
.tblock .val.danger{color:var(--danger)}
.countdown{text-align:center;padding:9px;margin-bottom:14px;border-radius:9px;font-size:1.35rem;font-weight:700;letter-spacing:1px}
.countdown.ok{background:#e8f7ef;color:var(--ok)}.countdown.warn{background:#fff4dc;color:var(--warn)}.countdown.danger{background:#fdeaea;color:var(--danger)}.countdown.none{background:#f5f5f5;color:var(--muted);font-size:.95rem;font-weight:400}
.actions{display:flex;gap:8px}
.btn{border:none;border-radius:9px;padding:9px 14px;font-size:.86rem;font-weight:600;cursor:pointer;transition:opacity .15s,transform .1s}
.btn:active{transform:scale(.97)}.btn:hover{opacity:.88}
.btn-p{background:#e07b54;color:#fff;flex:1}.btn-g{background:#f5f0eb;color:var(--muted);font-size:.8rem}
.btn-o{background:transparent;border:1.5px solid #e07b54;color:#e07b54}
/* modal */
.overlay{position:fixed;inset:0;background:rgba(0,0,0,.4);display:flex;align-items:center;justify-content:center;z-index:100;padding:20px}
.modal{background:#fff;border-radius:var(--r);padding:22px;width:100%;max-width:360px;box-shadow:0 8px 40px rgba(0,0,0,.18)}
.modal h2{font-size:1rem;margin-bottom:14px}
.modal label{display:block;font-size:.78rem;color:var(--muted);margin-bottom:5px}
.modal input{width:100%;padding:9px 11px;border:1.5px solid var(--border);border-radius:9px;font-size:.93rem;margin-bottom:18px;outline:none}
.modal input:focus{border-color:#e07b54}
.mact{display:flex;gap:8px;justify-content:flex-end}
/* history */
.hlist{max-height:250px;overflow-y:auto;margin-bottom:14px}
.hitem{display:flex;align-items:center;justify-content:space-between;padding:8px 0;border-bottom:1px solid var(--border);font-size:.88rem}
.hitem:last-child{border:none}
.hdel{background:none;border:none;color:#ccc;font-size:.95rem;cursor:pointer;padding:2px 6px;border-radius:5px}
.hdel:hover{color:var(--danger)}
/* config */
#cfg-section{margin-top:24px}
.cfg-toggle{background:none;border:none;color:var(--muted);font-size:.86rem;cursor:pointer;display:flex;align-items:center;gap:6px;padding:4px 0}
.cfg-toggle:hover{color:#333}
.cfg-card{background:var(--surface);border-radius:var(--r);box-shadow:0 2px 16px rgba(0,0,0,.08);padding:18px;margin-top:10px}
.cfg-card h3{font-size:.95rem;margin-bottom:9px}
.cfg-card p{font-size:.82rem;color:var(--muted);margin-bottom:8px}
ol.steps{font-size:.82rem;padding-left:16px;line-height:1.9;margin-bottom:14px}
ol.steps code{background:#f0ebe5;padding:1px 5px;border-radius:4px;font-size:.8rem}
.cfg-fields{display:flex;flex-direction:column;gap:6px;margin-bottom:14px}
.cfg-fields label{font-size:.78rem;color:var(--muted)}
.cfg-fields input{padding:9px 11px;border:1.5px solid var(--border);border-radius:9px;font-size:.93rem;outline:none}
.cfg-fields input:focus{border-color:#e07b54}
.cfg-acts{display:flex;gap:8px;flex-wrap:wrap}
#cfg-status{margin-top:10px;font-size:.82rem;min-height:18px}
.hidden{display:none!important}
</style>
</head>
<body>
<header>
  <h1>🐾 Medicación de mi perrita</h1>
  <p>Recordatorios automáticos por WhatsApp</p>
</header>
<main>
  <div id="cards"></div>

  <div id="m-overlay" class="overlay hidden">
    <div class="modal">
      <h2 id="m-title">Registrar aplicación</h2>
      <label>Horario de aplicación</label>
      <input type="datetime-local" id="m-dt"/>
      <div class="mact">
        <button class="btn btn-g" onclick="closeModal()">Cancelar</button>
        <button class="btn btn-p" onclick="confirmApply()">Guardar</button>
      </div>
    </div>
  </div>

  <div id="h-overlay" class="overlay hidden">
    <div class="modal">
      <h2 id="h-title">Historial</h2>
      <div class="hlist" id="h-list"></div>
      <div class="mact">
        <button class="btn btn-g" onclick="closeHistory()">Cerrar</button>
      </div>
    </div>
  </div>

  <section id="cfg-section">
    <button class="cfg-toggle" onclick="toggleCfg()">⚙️ Configurar WhatsApp</button>
    <div id="cfg-form" class="hidden">
      <div class="cfg-card">
        <h3>📱 Recordatorios por WhatsApp</h3>
        <p>Usamos <strong>CallMeBot</strong> (gratuito). Pasos para activarlo:</p>
        <ol class="steps">
          <li>Guardá el número <strong>+34 644 63 51 09</strong> como contacto "CallMeBot".</li>
          <li>Enviále este mensaje exacto por WhatsApp:<br/><code>I allow callmebot to send me messages</code></li>
          <li>Te responde con tu API key en segundos.</li>
        </ol>
        <div class="cfg-fields">
          <label>Tu número (con código de país, sin +). Ej: 5491112345678</label>
          <input type="text" id="cfg-phone" placeholder="5491112345678"/>
          <label>API Key de CallMeBot</label>
          <input type="text" id="cfg-key" placeholder="123456"/>
        </div>
        <div class="cfg-acts">
          <button class="btn btn-p" onclick="saveCfg()">Guardar</button>
          <button class="btn btn-o" onclick="testWA()">Enviar mensaje de prueba</button>
        </div>
        <p id="cfg-status"></p>
      </div>
    </div>
  </section>
</main>
<script>
let data=[], pendingId=null, pendingHistId=null, ticker=null;

document.addEventListener("DOMContentLoaded",()=>{loadCfg();fetchStatus();setInterval(fetchStatus,30000);});

async function fetchStatus(){
  const r=await fetch("/api/status"); data=await r.json();
  renderCards(data); startTicker();
}

function renderCards(meds){
  const c=document.getElementById("cards"); c.innerHTML="";
  meds.forEach(m=>c.appendChild(buildCard(m)));
}

function buildCard(m){
  const d=document.createElement("div"); d.className="card"; d.id="card-"+m.id;
  const {cls,txt}=statusInfo(m);
  d.innerHTML=`
    <div class="card-head">
      <div class="card-icon">${m.icon}</div>
      <div class="card-title"><h2>${m.name}</h2><p>${m.description}</p></div>
    </div>
    <div class="card-body">
      <div class="row">
        <span class="badge ${cls}">${txt}</span>
        <span class="itag">cada ${m.interval_hours}hs</span>
      </div>
      <div class="times">
        <div class="tblock"><div class="lbl">Última vez</div><div class="val">${m.last_applied?fmtDT(m.last_applied):"Sin registros"}</div></div>
        <div class="tblock"><div class="lbl">Próxima vez</div><div class="val ${m.is_overdue?"danger":""}">${m.next_due?fmtDT(m.next_due):"—"}</div></div>
      </div>
      <div class="countdown ${cls}" id="cd-${m.id}">${cdText(m)}</div>
      <div class="actions">
        <button class="btn btn-p" onclick="applyNow('${m.id}')">✅ Apliqué ahora</button>
        <button class="btn btn-g" onclick="openCustom('${m.id}','${m.name}')">🕐</button>
        <button class="btn btn-g" onclick="openHist('${m.id}','${m.name}')">📋</button>
      </div>
    </div>`;
  return d;
}

function statusInfo(m){
  if(!m.last_applied) return {cls:"none",txt:"⬜ Sin registros"};
  if(m.is_overdue)    return {cls:"danger",txt:"🔴 Vencida"};
  if(m.remaining_seconds<3600) return {cls:"warn",txt:"🟡 Por vencer"};
  return {cls:"ok",txt:"🟢 Al día"};
}

function cdText(m){
  if(!m.last_applied) return "Registrá la primera aplicación";
  if(m.is_overdue) return "¡Vencida hace "+fmtDur(-m.remaining_seconds)+"!";
  return "Faltan "+fmtDur(m.remaining_seconds);
}

function startTicker(){
  if(ticker) clearInterval(ticker);
  ticker=setInterval(()=>{
    data.forEach(m=>{
      if(m.remaining_seconds===null) return;
      m.remaining_seconds-=1; m.is_overdue=m.remaining_seconds<0;
      const cd=document.getElementById("cd-"+m.id); if(!cd) return;
      const {cls}=statusInfo(m); cd.className="countdown "+cls; cd.textContent=cdText(m);
      const b=document.querySelector("#card-"+m.id+" .badge"); if(!b) return;
      const {cls:c2,txt:t2}=statusInfo(m); b.className="badge "+c2; b.textContent=t2;
    });
  },1000);
}

async function applyNow(id){ await doApply(id,null); }

function openCustom(id,name){
  pendingId=id;
  document.getElementById("m-title").textContent="Registrar: "+name;
  document.getElementById("m-dt").value=localISO(new Date());
  document.getElementById("m-overlay").classList.remove("hidden");
}
function closeModal(){ document.getElementById("m-overlay").classList.add("hidden"); pendingId=null; }
async function confirmApply(){
  const v=document.getElementById("m-dt").value; if(!v) return;
  await doApply(pendingId,v); closeModal();
}
async function doApply(id,at){
  const b={med_id:id}; if(at) b.applied_at=at;
  await fetch("/api/apply",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify(b)});
  await fetchStatus();
}

async function openHist(id,name){
  pendingHistId=id;
  document.getElementById("h-title").textContent="Historial: "+name;
  await loadHist(id);
  document.getElementById("h-overlay").classList.remove("hidden");
}
function closeHistory(){ document.getElementById("h-overlay").classList.add("hidden"); }
async function loadHist(id){
  const r=await fetch("/api/history/"+id); const rows=await r.json();
  const el=document.getElementById("h-list");
  if(!rows.length){el.innerHTML='<p style="color:#aaa;text-align:center;padding:16px">Sin registros</p>';return;}
  el.innerHTML=rows.map(r=>`<div class="hitem"><span>${fmtDT(r.applied_at)}</span><button class="hdel" onclick="delRec(${r.id})">✕</button></div>`).join("");
}
async function delRec(id){
  await fetch("/api/delete/"+id,{method:"DELETE"});
  await loadHist(pendingHistId); await fetchStatus();
}

async function loadCfg(){
  const r=await fetch("/api/config"); const c=await r.json();
  document.getElementById("cfg-phone").value=c.whatsapp_phone||"";
  if(c.has_apikey) document.getElementById("cfg-key").placeholder="•••••• (ya guardada)";
}
async function saveCfg(){
  const phone=document.getElementById("cfg-phone").value.trim();
  const key=document.getElementById("cfg-key").value.trim();
  const b={whatsapp_phone:phone}; if(key) b.callmebot_apikey=key;
  await fetch("/api/config",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify(b)});
  showCfgStatus("✅ Configuración guardada."); loadCfg();
}
async function testWA(){
  showCfgStatus("Enviando...");
  const r=await fetch("/api/test-whatsapp",{method:"POST"}); const d=await r.json();
  showCfgStatus(d.success?"✅ ¡Mensaje enviado! Revisá tu WhatsApp.":"❌ No se pudo enviar. Verificá el número y la API key.");
}
function showCfgStatus(m){ const e=document.getElementById("cfg-status"); e.textContent=m; setTimeout(()=>e.textContent="",5000); }
function toggleCfg(){ document.getElementById("cfg-form").classList.toggle("hidden"); }

function fmtDT(s){
  const d=new Date(s); if(isNaN(d)) return "—";
  return d.toLocaleString("es-AR",{day:"2-digit",month:"2-digit",hour:"2-digit",minute:"2-digit"});
}
function fmtDur(s){
  const t=Math.abs(Math.round(s)),h=Math.floor(t/3600),m=Math.floor((t%3600)/60),ss=t%60;
  if(h>0) return h+"h "+pad(m)+"m"; if(m>0) return m+"m "+pad(ss)+"s"; return ss+"s";
}
function pad(n){ return String(n).padStart(2,"0"); }
function localISO(d){ const o=d.getTimezoneOffset(); return new Date(d-o*60000).toISOString().slice(0,16); }
</script>
</body>
</html>"""


def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_db()
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS applications (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            med_id TEXT NOT NULL,
            applied_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS config (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL
        );
    """)
    conn.commit()
    conn.close()


def get_last_application(med_id):
    conn = get_db()
    row = conn.execute(
        "SELECT applied_at FROM applications WHERE med_id=? ORDER BY applied_at DESC LIMIT 1",
        (med_id,),
    ).fetchone()
    conn.close()
    if row:
        dt = datetime.fromisoformat(row["applied_at"])
        if dt.tzinfo is None:
            dt = TIMEZONE.localize(dt)
        return dt
    return None


def get_config():
    conn = get_db()
    rows = conn.execute("SELECT key, value FROM config").fetchall()
    conn.close()
    return {r["key"]: r["value"] for r in rows}


def send_whatsapp(message):
    cfg = get_config()
    phone = cfg.get("whatsapp_phone")
    apikey = cfg.get("callmebot_apikey")
    if not phone or not apikey:
        return False
    try:
        url = (
            f"https://api.callmebot.com/whatsapp.php"
            f"?phone={phone}&text={requests.utils.quote(message)}&apikey={apikey}"
        )
        r = requests.get(url, timeout=10)
        return r.status_code == 200
    except Exception:
        return False


def check_reminders():
    now = datetime.now(TIMEZONE)
    for med in MEDICATIONS:
        last = get_last_application(med["id"])
        if last is None:
            continue
        next_due = last + timedelta(hours=med["interval_hours"])
        diff = (now - next_due).total_seconds()
        if 0 <= diff <= 60:
            msg = (
                f"🐾 ¡Hora de la medicación!\n"
                f"{med['icon']} {med['name']} — cada {med['interval_hours']}hs\n"
                f"Última aplicación: {last.strftime('%H:%M')}"
            )
            send_whatsapp(msg)


init_db()
scheduler = BackgroundScheduler(timezone=TIMEZONE)
scheduler.add_job(check_reminders, "interval", minutes=1)
scheduler.start()
atexit.register(lambda: scheduler.shutdown())


@app.route("/")
def index():
    return HTML


@app.route("/api/status")
def api_status():
    now = datetime.now(TIMEZONE)
    result = []
    for med in MEDICATIONS:
        last = get_last_application(med["id"])
        if last:
            next_due = last + timedelta(hours=med["interval_hours"])
            remaining = (next_due - now).total_seconds()
            entry = {**med, "last_applied": last.isoformat(), "next_due": next_due.isoformat(),
                     "remaining_seconds": int(remaining), "is_overdue": remaining < 0}
        else:
            entry = {**med, "last_applied": None, "next_due": None,
                     "remaining_seconds": None, "is_overdue": False}
        result.append(entry)
    return jsonify(result)


@app.route("/api/apply", methods=["POST"])
def api_apply():
    data = request.get_json()
    med_id = data.get("med_id")
    applied_at_str = data.get("applied_at")
    if not med_id:
        return jsonify({"error": "med_id requerido"}), 400
    if applied_at_str:
        applied_at = datetime.fromisoformat(applied_at_str)
        if applied_at.tzinfo is None:
            applied_at = TIMEZONE.localize(applied_at)
    else:
        applied_at = datetime.now(TIMEZONE)
    conn = get_db()
    conn.execute("INSERT INTO applications (med_id, applied_at) VALUES (?, ?)",
                 (med_id, applied_at.isoformat()))
    conn.commit()
    conn.close()
    return jsonify({"success": True, "applied_at": applied_at.isoformat()})


@app.route("/api/history/<med_id>")
def api_history(med_id):
    conn = get_db()
    rows = conn.execute(
        "SELECT id, applied_at FROM applications WHERE med_id=? ORDER BY applied_at DESC LIMIT 30",
        (med_id,),
    ).fetchall()
    conn.close()
    return jsonify([{"id": r["id"], "applied_at": r["applied_at"]} for r in rows])


@app.route("/api/delete/<int:record_id>", methods=["DELETE"])
def api_delete(record_id):
    conn = get_db()
    conn.execute("DELETE FROM applications WHERE id=?", (record_id,))
    conn.commit()
    conn.close()
    return jsonify({"success": True})


@app.route("/api/config", methods=["GET", "POST"])
def api_config():
    if request.method == "POST":
        data = request.get_json()
        conn = get_db()
        for key, value in data.items():
            conn.execute("INSERT OR REPLACE INTO config (key, value) VALUES (?, ?)", (key, value))
        conn.commit()
        conn.close()
        return jsonify({"success": True})
    cfg = get_config()
    return jsonify({"whatsapp_phone": cfg.get("whatsapp_phone", ""), "has_apikey": bool(cfg.get("callmebot_apikey"))})


@app.route("/api/test-whatsapp", methods=["POST"])
def api_test_whatsapp():
    ok = send_whatsapp("🐾 ¡Hola! Los recordatorios de medicación de tu perrita están activos.")
    return jsonify({"success": ok})


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
