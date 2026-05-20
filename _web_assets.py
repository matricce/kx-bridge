# AUTOGENERIERT von tools/bundle_web_assets.py – NICHT von Hand editieren.
# Quelle: bridge/web/index.html
INDEX_HTML = r"""<!DOCTYPE html>
<html lang="de" data-theme="dark">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>KX-Bridge</title>
<style>
:root{
  --bg:#1a1a1f;--card:#24242c;--raised:#2e2e3a;--border:#3a3a4a;
  --txt:#f0f0f5;--txt2:#8888aa;--accent:#00c8ff;--accent2:#ff6b35;
  --ok:#4cde80;--err:#ff4d6d;--warn:#ffb020;
  --font:-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;
  --mono:"JetBrains Mono","Fira Code",monospace;
}
[data-theme=light]{
  --bg:#f0f0f5;--card:#fff;--raised:#e8e8f0;--border:#d0d0e0;
  --txt:#1a1a2e;--txt2:#666680;
}
*{box-sizing:border-box;margin:0;padding:0}
body{background:var(--bg);color:var(--txt);font-family:var(--font);font-size:14px;min-height:100vh;display:flex;flex-direction:column}
a{color:var(--accent);text-decoration:none}

/* ── HEADER ── */
header{background:var(--card);border-bottom:1px solid var(--border);
  display:flex;align-items:center;gap:12px;padding:0 20px;height:52px;
  position:sticky;top:0;z-index:100}
.logo{font-size:18px;font-weight:700;color:var(--accent);letter-spacing:-.02em}
.hname{font-size:13px;color:var(--txt2)}
.hbadge{display:flex;align-items:center;gap:6px;font-size:12px;font-weight:600;
  padding:4px 10px;border-radius:20px;background:var(--raised);color:var(--txt2);
  text-transform:uppercase;letter-spacing:.04em}
.hbadge.printing{background:#0d2d1a;color:var(--ok)}
.hbadge.complete{background:#0d1f38;color:#60b0ff}
.hbadge.error{background:#2d0d0d;color:var(--err)}
.hbadge .dot{width:7px;height:7px;border-radius:50%;background:currentColor}
.hbadge.printing .dot{animation:pulse 1.4s infinite}
@keyframes pulse{0%,100%{opacity:1}50%{opacity:.25}}
.theme-btn{background:none;border:1px solid var(--border);color:var(--txt2);
  border-radius:8px;padding:6px 10px;cursor:pointer;font-size:13px;transition:.15s}
.theme-btn:hover{border-color:var(--accent);color:var(--accent)}
.conn-btn{border-radius:8px;padding:6px 12px;cursor:pointer;font-size:13px;
  font-weight:600;border:none;transition:.15s}
.conn-btn.disconnected{background:var(--accent);color:#fff}
.conn-btn.disconnected:hover{opacity:.85}
.conn-btn.connected{background:transparent;border:1px solid var(--border);color:var(--txt2)}
.conn-btn.connected:hover{border-color:#e05;color:#e05}

/* ── LAYOUT ── */
.layout{display:flex;flex:1;min-height:0}
nav.sidebar{width:200px;background:var(--card);border-right:1px solid var(--border);
  display:flex;flex-direction:column;padding:12px 8px;gap:2px;flex-shrink:0}
.nav-btn{background:none;border:none;color:var(--txt2);text-align:left;
  padding:9px 12px;border-radius:8px;cursor:pointer;font-size:13px;
  display:flex;align-items:center;gap:10px;transition:.12s;width:100%}
.nav-btn:hover{background:var(--raised);color:var(--txt)}
.nav-btn.active{background:var(--raised);color:var(--accent)}
.nav-icon{font-size:16px;width:20px;text-align:center}
main{flex:1;overflow-y:auto;padding:20px}
.grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(320px,1fr));gap:16px}

/* ── CARD ── */
.card{background:var(--card);border:1px solid var(--border);border-radius:12px;
  padding:18px;transition:box-shadow .15s,transform .15s}
.card:hover{box-shadow:0 4px 20px rgba(0,0,0,.3);transform:translateY(-1px)}
.card-title{font-size:11px;text-transform:uppercase;letter-spacing:.1em;color:var(--txt2);
  margin-bottom:14px;display:flex;align-items:center;gap:8px}
.card-title span{font-size:14px}

/* ── HERO ── */
.hero{grid-column:1/-1;display:grid;grid-template-columns:1fr 320px;gap:16px}
@media(max-width:900px){.hero{grid-template-columns:1fr}}
.cam-wrap{background:#0a0a0e;border-radius:10px;overflow:hidden;
  min-height:180px;max-height:320px;display:flex;align-items:center;justify-content:center;position:relative}
.cam-wrap img,.cam-wrap video{width:100%;max-height:320px;height:auto;display:block;object-fit:contain}
.cam-placeholder{color:var(--txt2);font-size:13px;text-align:center;padding:20px}
@keyframes spin{to{transform:rotate(360deg)}}
.cam-spinner{width:40px;height:40px;border:3px solid rgba(255,255,255,.15);
  border-top-color:var(--accent);border-radius:50%;animation:spin .8s linear infinite;display:none}
.cam-overlay{position:absolute;bottom:0;left:0;right:0;
  background:linear-gradient(transparent,rgba(0,0,0,.75));padding:14px}
.cam-toggle{position:absolute;top:10px;right:10px;background:rgba(0,0,0,.5);
  border:1px solid rgba(255,255,255,.2);color:#fff;border-radius:8px;
  padding:6px 10px;cursor:pointer;font-size:12px;backdrop-filter:blur(4px)}
.cam-toggle:hover{background:rgba(0,0,0,.7)}

/* ── PROGRESS ── */
.hero-info{display:flex;flex-direction:column;gap:12px}
.pct-big{font-size:52px;font-weight:700;line-height:1;color:var(--txt)}
.pct-big small{font-size:20px;font-weight:400;color:var(--txt2)}
.progress-bar{height:8px;background:var(--raised);border-radius:4px;overflow:hidden;margin:4px 0}
.progress-fill{height:100%;background:linear-gradient(90deg,var(--accent),#0080cc);
  border-radius:4px;transition:width .6s ease}
.meta-row{display:flex;justify-content:space-between;font-size:12px;color:var(--txt2)}
.layer-badge{background:var(--raised);border-radius:6px;padding:4px 8px;
  font-family:var(--mono);font-size:12px;color:var(--txt)}
.fname{font-size:12px;color:var(--txt2);white-space:nowrap;overflow:hidden;text-overflow:ellipsis;
  background:var(--raised);border-radius:6px;padding:6px 8px}

/* ── PRINT CONTROLS ── */
.ctrl-btns{display:flex;gap:8px;flex-wrap:wrap}
.btn{border:none;border-radius:8px;padding:10px 16px;font-size:13px;font-weight:600;
  cursor:pointer;transition:opacity .15s,transform .1s;white-space:nowrap}
.btn:hover{opacity:.85;transform:translateY(-1px)}
.btn:active{transform:translateY(0)}
.btn-start{background:var(--ok);color:#0d2010}
.btn-pause{background:var(--raised);color:var(--txt);border:1px solid var(--border)}
.btn-resume{background:#0d2d1a;color:var(--ok);border:1px solid var(--ok)}
.btn-skip{background:var(--raised);color:var(--warn);border:1px solid var(--warn)}
.btn-cancel{background:#2d0d0d;color:var(--err);border:1px solid var(--err)}
.btn-accent{background:var(--accent);color:#001a24}
.btn-sm{padding:7px 12px;font-size:12px}
.spd-btn{flex:1;border:1.5px solid var(--border);background:var(--raised);color:var(--txt);
  border-radius:10px;padding:14px 8px;font-size:13px;font-weight:600;cursor:pointer;
  transition:all .15s;display:flex;flex-direction:column;align-items:center;gap:4px}
.spd-btn:hover{border-color:var(--accent);color:var(--accent)}
.spd-btn.spd-active{border-color:var(--accent);background:rgba(0,200,255,.12);color:var(--accent)}
.spd-btn .spd-icon{font-size:22px}
.spd-bar{height:4px;border-radius:2px;background:var(--border);margin-top:10px;overflow:hidden}
.spd-bar-fill{height:100%;border-radius:2px;background:linear-gradient(90deg,var(--accent2),var(--accent));transition:width .3s}

/* ── TIME CARDS ── */
.time-grid{display:grid;grid-template-columns:1fr 1fr 1fr;gap:8px;margin-top:8px}
.time-block{background:var(--raised);border-radius:10px;padding:10px 12px}
.time-label{font-size:10px;text-transform:uppercase;letter-spacing:.08em;color:var(--txt2);margin-bottom:4px}
.time-val{font-size:20px;font-weight:700;font-family:var(--mono);color:var(--txt)}
/* ── TEMPS ── */
.temp-pair{display:grid;grid-template-columns:1fr 1fr;gap:12px}
.temp-card-inner{display:grid;grid-template-columns:1fr 1fr;gap:12px}
.temp-block{background:var(--raised);border-radius:10px;padding:14px;position:relative}
.temp-label{font-size:11px;text-transform:uppercase;letter-spacing:.08em;color:var(--txt2);margin-bottom:6px}
.temp-row{display:flex;align-items:baseline;gap:6px}
.temp-val{font-size:30px;font-weight:700;font-family:var(--mono)}
.temp-unit{font-size:14px;color:var(--txt2)}
.temp-target{font-size:11px;color:var(--txt2);margin-top:2px}
.temp-arc{position:absolute;top:12px;right:12px}
.temp-edit{display:flex;gap:6px;margin-top:10px}
.temp-input{background:var(--bg);border:1px solid var(--border);color:var(--txt);
  border-radius:6px;padding:5px 8px;font-size:13px;font-family:var(--mono);width:70px}
.temp-input:focus{outline:none;border-color:var(--accent)}
.chart-wrap{margin-top:12px}
canvas.tchart{width:100%;height:60px;display:block;border-radius:6px;background:var(--raised)}

/* ── MOTION ── */
.joypad{display:grid;grid-template-columns:repeat(3,52px);
  grid-template-rows:repeat(3,52px);gap:6px;justify-content:center;margin:8px auto}
.joy{background:var(--raised);border:1px solid var(--border);color:var(--txt);
  border-radius:10px;font-size:18px;cursor:pointer;transition:.12s;
  display:flex;align-items:center;justify-content:center}
.joy:hover{background:var(--accent);color:#001a24;border-color:var(--accent)}
.joy:active{transform:scale(.93)}
.joy.home{font-size:14px;background:var(--bg)}
.step-btns{display:flex;gap:6px;justify-content:center;flex-wrap:wrap;margin-top:10px}
.step-btn{background:var(--raised);border:1px solid var(--border);color:var(--txt2);
  border-radius:6px;padding:5px 10px;font-size:12px;cursor:pointer;transition:.12s}
.step-btn.active,.step-btn:hover{background:var(--accent);color:#001a24;border-color:var(--accent)}
.home-btns{display:flex;gap:6px;flex-wrap:wrap;margin-top:10px;justify-content:center}

/* ── AMS ── */
.ams-slots{display:flex;flex-direction:column;gap:12px}
.ams-box-group{}
.ams-box-label{font-size:11px;font-weight:700;color:var(--txt2);text-transform:uppercase;letter-spacing:.06em;margin-bottom:6px;padding-left:2px}
.ams-box-slots{display:grid;grid-template-columns:repeat(4,1fr);gap:8px}
.ams-slot{background:var(--raised);border-radius:10px;padding:10px;text-align:center;
  border:2px solid transparent;transition:.2s;position:relative}
.ams-slot.active{border-color:var(--slot-color,var(--accent));
  box-shadow:0 0 12px rgba(var(--slot-rgb,0,200,255),.3)}
.ams-slot.loaded{border-color:var(--ok)!important;
  box-shadow:0 0 0 2px rgba(64,220,120,.35),0 0 14px rgba(64,220,120,.35)}
.ams-slot.loading{border-color:var(--ok)!important;animation:amsPulseGreen 1s ease-in-out infinite}
.ams-slot.unloading{border-color:var(--err)!important;animation:amsPulseRed 1s ease-in-out infinite}
@keyframes amsPulseGreen{0%{box-shadow:0 0 0 0 rgba(64,220,120,.55)}50%{box-shadow:0 0 0 4px rgba(64,220,120,.25),0 0 18px rgba(64,220,120,.45)}100%{box-shadow:0 0 0 0 rgba(64,220,120,.55)}}
@keyframes amsPulseRed{0%{box-shadow:0 0 0 0 rgba(230,80,80,.55)}50%{box-shadow:0 0 0 4px rgba(230,80,80,.25),0 0 18px rgba(230,80,80,.45)}100%{box-shadow:0 0 0 0 rgba(230,80,80,.55)}}
.ams-slot-bridge{display:flex;flex-direction:column;align-items:center;justify-content:center;gap:6px;
  border:1px dashed var(--border);background:linear-gradient(180deg,rgba(255,255,255,.03),rgba(255,255,255,.01));
  color:var(--txt2);min-height:106px}
.ams-slot-bridge .bridge-chip{width:58px;height:58px;border:1px solid rgba(255,255,255,.14);border-radius:50%;
  display:flex;align-items:center;justify-content:center;background:rgba(255,255,255,.04);color:var(--txt2);
  font-size:13px;font-weight:700;letter-spacing:.04em}
.slot-circle{width:36px;height:36px;border-radius:50%;margin:0 auto 6px;border:2px solid rgba(255,255,255,.15)}
.slot-label{font-size:11px;color:var(--txt2);font-family:var(--mono)}
.slot-material{font-size:12px;font-weight:600;margin-bottom:2px}

/* ── LIGHT + FAN ── */
.toggle-row{display:flex;align-items:center;justify-content:space-between;margin-bottom:14px}
.toggle-label{font-size:13px;font-weight:600}
.toggle{position:relative;width:44px;height:24px;cursor:pointer}
.toggle input{opacity:0;width:0;height:0;position:absolute}
.toggle-track{width:44px;height:24px;background:var(--raised);border-radius:12px;
  border:1px solid var(--border);transition:.25s;display:block}
.toggle input:checked+.toggle-track{background:var(--accent)}
.toggle-thumb{position:absolute;top:3px;left:3px;width:18px;height:18px;
  background:#fff;border-radius:50%;transition:.25s;pointer-events:none}
.toggle input:checked~.toggle-thumb{transform:translateX(20px)}
.slider-row{display:flex;align-items:center;gap:10px;margin-top:8px}
.slider-label{font-size:12px;color:var(--txt2);width:80px}
.slider{flex:1;-webkit-appearance:none;height:4px;border-radius:2px;
  background:var(--raised);outline:none;cursor:pointer}
.slider::-webkit-slider-thumb{-webkit-appearance:none;width:16px;height:16px;
  border-radius:50%;background:var(--accent);cursor:pointer;transition:.1s}
.slider::-webkit-slider-thumb:hover{transform:scale(1.2)}
.slider-val{font-family:var(--mono);font-size:12px;color:var(--txt);width:30px;text-align:right}

/* ── CONSOLE ── */
.console{background:#0a0a0e;border-radius:8px;padding:10px;font-family:var(--mono);
  font-size:11px;color:#8888aa;overflow-y:auto;line-height:1.6}
.console .ts{color:#444;margin-right:6px}
.console .msg-info{color:#8888aa}
.console .msg-ok{color:var(--ok)}
.console .msg-err{color:var(--err)}
.console .msg-warn{color:var(--warn)}

/* ── PANELS ── */
.panel{display:none}
.panel.active{display:block}

/* ── MODAL ── */
.modal-overlay{display:none;position:fixed;inset:0;background:rgba(0,0,0,.6);
  z-index:200;align-items:center;justify-content:center;padding:16px}
.modal-overlay.open{display:flex}
.modal-box{background:var(--card);border:1px solid var(--border);border-radius:14px;
  width:100%;max-width:480px;max-height:90vh;overflow-y:auto;padding:24px;
  display:flex;flex-direction:column;gap:18px}
.modal-header{display:flex;align-items:center;justify-content:space-between}
.modal-title{font-size:15px;font-weight:700;color:var(--txt)}
.modal-close{background:none;border:none;color:var(--txt2);font-size:20px;
  cursor:pointer;padding:4px 8px;border-radius:6px}
.modal-close:hover{background:var(--raised);color:var(--txt)}
.modal-section{font-size:10px;text-transform:uppercase;letter-spacing:.1em;
  color:var(--txt2);margin-bottom:6px;margin-top:4px}
.modal-field{display:flex;flex-direction:column;gap:4px;margin-bottom:10px}
.modal-field label{font-size:12px;color:var(--txt2)}
.modal-field input{background:var(--raised);border:1px solid var(--border);
  border-radius:7px;color:var(--txt);padding:7px 10px;font-size:13px;width:100%}
.modal-field input:focus{outline:none;border-color:var(--accent)}
.poll-btns{display:flex;gap:8px}
.poll-btn{flex:1;padding:7px;background:var(--raised);border:1px solid var(--border);
  border-radius:7px;color:var(--txt2);cursor:pointer;font-size:13px;transition:all .15s}
.poll-btn.active{background:var(--accent);border-color:var(--accent);color:#000;font-weight:600}
.update-row{display:flex;align-items:center;gap:10px;flex-wrap:wrap}
.update-status{font-size:12px;color:var(--txt2);flex:1;min-width:0}
.modal-save{width:100%;padding:10px;background:var(--accent);border:none;
  border-radius:8px;color:#000;font-weight:700;font-size:14px;cursor:pointer;margin-top:4px}
.modal-save:hover{opacity:.88}

/* ── BOTTOM NAV (mobile) ── */
nav.bottom-nav{display:none;position:fixed;bottom:0;left:0;right:0;
  background:var(--card);border-top:1px solid var(--border);
  justify-content:space-around;padding:8px 0 max(8px,env(safe-area-inset-bottom))}
.bnav-btn{background:none;border:none;color:var(--txt2);display:flex;
  flex-direction:column;align-items:center;gap:3px;cursor:pointer;font-size:10px;padding:4px 8px}
.bnav-btn.active{color:var(--accent)}
.bnav-icon{font-size:20px}

/* ── Tablet (769–1100px): schmale Sidebar ── */
@media(min-width:769px) and (max-width:1100px){
  nav.sidebar{width:52px;padding:12px 4px}
  .nav-btn .nav-text{display:none}
  .nav-btn{justify-content:center;padding:10px}
  .nav-icon{width:auto}
  .grid{grid-template-columns:repeat(2,1fr)}
  .hero{grid-template-columns:1fr}
}

/* ── Mobile (≤768px): Bottom-Nav, 1-Spalte ── */
@media(max-width:768px){
  nav.sidebar{display:none}
  nav.bottom-nav{display:flex}
  main{padding:10px;padding-bottom:72px}

  /* Header kompakt */
  header{padding:0 12px;gap:8px}
  .hname{display:none}

  /* 1-Spalten-Grid, full-width spans funktionieren weiterhin */
  .grid{grid-template-columns:1fr;gap:12px}

  /* Hero: Kamera über Info */
  .hero{grid-template-columns:1fr}
  .cam-wrap{max-height:220px}

  /* Temp-Pair und Temp-Card übereinander */
  .temp-pair{grid-template-columns:1fr}
  .temp-card-inner{grid-template-columns:1fr}

  /* AMS: 2 Spalten auf kleinen Screens */
  .ams-box-slots{grid-template-columns:repeat(2,1fr)}

  /* Joypad etwas kleiner */
  .joypad{grid-template-columns:repeat(3,44px);grid-template-rows:repeat(3,44px);gap:5px}
  .joy{font-size:16px}

  /* Buttons größere Touch-Targets */
  .btn{padding:10px 14px;font-size:13px}
  .btn-sm{padding:8px 12px}
  .step-btn{padding:8px 12px;font-size:13px}

  /* Modal vollbreite auf kleinen Screens */
  .modal-box{padding:16px;border-radius:10px}
  .poll-btns{gap:6px}
}
</style>
</head>
<body>

<div id="conn-error-banner" style="display:none;background:#c0392b;color:#fff;padding:10px 18px;font-size:14px;text-align:center;position:sticky;top:0;z-index:999;"></div>
<div id="file-ready-banner" style="display:none;background:#1a6e3c;color:#fff;padding:10px 18px;font-size:14px;text-align:center;position:sticky;top:0;z-index:998;display:none;align-items:center;justify-content:center;gap:12px;flex-wrap:wrap">
  <span>📄 <span id="file-ready-name"></span></span>
  <button id="file-ready-btn" onclick="startReadyFile()"
    style="padding:5px 16px;background:#fff;color:#1a6e3c;border:none;border-radius:6px;font-weight:700;cursor:pointer;font-size:13px"></button>
  <button id="file-slots-btn" onclick="startReadyFileWithSlots()"
    style="padding:5px 16px;background:rgba(255,255,255,0.15);color:#fff;border:1px solid rgba(255,255,255,0.5);border-radius:6px;font-weight:700;cursor:pointer;font-size:13px"></button>
  <button id="file-cancel-btn" onclick="cancelReadyFile()"
    style="padding:5px 16px;background:rgba(255,255,255,0.15);color:#fff;border:1px solid rgba(255,255,255,0.5);border-radius:6px;font-weight:700;cursor:pointer;font-size:13px"></button>
</div>

<header>
  <div class="logo">⬡ KX-Bridge</div>
  <div style="flex:1"></div>
  <div id="printer-dropdown-wrap" style="display:none;position:relative">
    <button id="printer-dropdown-btn" onclick="togglePrinterDropdown()" style="background:var(--raised);border:1px solid var(--border);border-radius:6px;padding:4px 10px;color:var(--txt);cursor:pointer;font-size:13px;display:flex;align-items:center;gap:6px">
      <span id="h-pname">Anycubic Kobra X</span><span style="opacity:.5">▾</span>
    </button>
    <div id="printer-dropdown-menu" style="display:none;position:absolute;top:calc(100% + 4px);right:0;background:var(--card);border:1px solid var(--border);border-radius:8px;min-width:200px;z-index:200;box-shadow:0 4px 16px #0006;overflow:hidden">
    </div>
  </div>
  <div id="h-pname-single" class="hname">Anycubic Kobra X</div>
  <span id="h-version" style="font-size:11px;opacity:.5;margin-left:6px"></span>
  <div class="hbadge" id="h-badge"><span class="dot"></span><span id="h-state">Standby</span></div>
  <button class="theme-btn" onclick="toggleTheme()">☀ / ☾</button>
  <button class="theme-btn" onclick="toggleLang()" id="lang-btn">EN</button>
  <button class="theme-btn" onclick="openSettings()" id="settings-btn" title="Einstellungen">⚙</button>
  <button class="conn-btn disconnected" id="conn-btn" onclick="toggleConnection()">⚡ Verbinden</button>
</header>

<!-- ═══ SETTINGS MODAL ═══ -->
<div class="modal-overlay" id="settings-modal" onclick="if(event.target===this)closeSettings()">
  <div class="modal-box">
    <div class="modal-header">
      <span class="modal-title" id="modal-title-settings">Einstellungen</span>
      <button class="modal-close" onclick="closeSettings()">✕</button>
    </div>

    <div>
      <div class="modal-field" style="margin-bottom:12px">
        <label id="lbl-printer-name" style="font-weight:600">Drucker-Name</label>
        <input type="text" id="s-printer-name" placeholder="z.B. Kobra X Links">
      </div>
      <div class="modal-section" id="modal-sec-connection">Verbindung</div>
      <div class="modal-field">
        <label id="lbl-printer-ip">Drucker-IP</label>
        <input type="text" id="s-printer-ip" placeholder="192.168.x.x">
        <small id="lbl-ip-hint" style="color:#f80;display:none"></small>
      </div>
      <div class="modal-field">
        <label id="lbl-mqtt-port">MQTT-Port</label>
        <input type="number" id="s-mqtt-port" placeholder="9883">
      </div>
      <div class="modal-field">
        <label id="lbl-username">MQTT-Benutzername</label>
        <input type="text" id="s-username" placeholder="userXXXXXXXX" autocomplete="new-password">
      </div>
      <div class="modal-field">
        <label id="lbl-password">MQTT-Passwort</label>
        <input type="password" id="s-password" autocomplete="new-password">
      </div>
      <div class="modal-field">
        <label id="lbl-device-id">Device-ID</label>
        <input type="text" id="s-device-id" placeholder="32 Hex-Zeichen">
      </div>
      <div class="modal-field">
        <label id="lbl-mode-id">Mode-ID</label>
        <input type="text" id="s-mode-id" placeholder="20030">
      </div>
    </div>

    <div>
      <div class="modal-section" id="modal-sec-print">Druckeinstellungen</div>
      <div class="modal-field">
        <label id="lbl-default-slot">Standard-Slot (Einfarbdruck)</label>
        <select id="s-default-slot">
          <option value="auto" id="opt-slot-auto">Auto (alle belegten Slots)</option>
          <option value="0" id="opt-slot-0">Slot 1</option>
          <option value="1" id="opt-slot-1">Slot 2</option>
          <option value="2" id="opt-slot-2">Slot 3</option>
          <option value="3" id="opt-slot-3">Slot 4</option>
        </select>
      </div>
      <div class="modal-field" style="flex-direction:row;align-items:center;gap:10px">
        <input type="checkbox" id="s-auto-leveling" style="width:auto;margin:0">
        <label id="lbl-auto-leveling" style="margin:0;cursor:pointer" for="s-auto-leveling">Auto-Leveling vor Druck</label>
      </div>
    </div>

    <div>
      <div class="modal-section" id="modal-sec-poll">Poll-Intervall</div>
      <div class="poll-btns">
        <button class="poll-btn" onclick="setPoll(1000)" id="poll-1">1s</button>
        <button class="poll-btn active" onclick="setPoll(2000)" id="poll-2">2s</button>
        <button class="poll-btn" onclick="setPoll(5000)" id="poll-5">5s</button>
      </div>
    </div>

    <div>
      <div class="modal-section" id="modal-sec-version">Version</div>
      <div class="update-row">
        <span id="s-version-label" style="font-size:13px;color:var(--txt)">–</span>
        <button class="btn btn-sm" style="background:var(--raised);color:var(--txt)" onclick="checkUpdate()" id="btn-update-check">🔄 <span id="lbl-update-check">Auf Updates prüfen</span></button>
      </div>
      <div class="update-status" id="update-status" style="margin-top:6px"></div>
      <button class="btn btn-sm btn-accent" id="btn-update-apply" style="display:none;margin-top:8px" onclick="applyUpdate()">
        <span id="lbl-update-apply">Jetzt installieren</span>
      </button>
      <div id="update-changelog" style="display:none;margin-top:10px;background:var(--raised);border-radius:6px;padding:10px;font-size:11px;font-family:var(--mono);color:var(--txt2);white-space:pre-wrap;max-height:180px;overflow-y:auto;line-height:1.6"></div>
    </div>

    <button class="modal-save" onclick="saveSettings()" id="btn-save-settings">Speichern &amp; Neustart</button>
  </div>
</div>

<!-- ═══ AMS SLOT EDIT DIALOG ═══ -->
<div class="modal-overlay" id="slot-edit-modal" onclick="if(event.target===this)closeSlotEdit()">
  <div class="modal-box" style="max-width:340px">
    <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:16px">
      <span class="modal-title" id="slot-edit-title"></span>
      <button onclick="closeSlotEdit()" style="background:none;border:none;color:var(--txt2);font-size:20px;cursor:pointer;line-height:1">✕</button>
    </div>
    <div style="display:flex;align-items:center;gap:16px;margin-bottom:20px">
      <div id="slot-edit-preview" style="width:56px;height:56px;border-radius:50%;border:3px solid rgba(255,255,255,.2);flex-shrink:0"></div>
      <div style="flex:1">
        <div style="font-size:11px;color:var(--txt2);margin-bottom:4px" id="lbl-slot-color"></div>
        <input type="color" id="slot-edit-color"
          oninput="document.getElementById('slot-edit-preview').style.background=this.value"
          style="width:100%;height:36px;border:1px solid var(--border);border-radius:6px;background:var(--raised);cursor:pointer;padding:2px">
      </div>
    </div>
    <div style="margin-bottom:20px">
      <div style="font-size:11px;color:var(--txt2);margin-bottom:6px" id="lbl-slot-material"></div>
      <div style="display:flex;flex-wrap:wrap;gap:6px" id="slot-mat-btns">
      </div>
      <input type="text" id="slot-edit-mat"
        oninput="highlightMatBtn(this.value)"
        style="margin-top:8px;width:100%;padding:6px 10px;background:var(--raised);border:1px solid var(--border);border-radius:6px;color:var(--txt);font-size:13px;box-sizing:border-box">
    </div>
    <button class="btn" id="btn-slot-edit-feed" style="width:100%;margin-bottom:8px" onclick="slotEditFeed()"></button>
    <button class="modal-save" id="btn-slot-edit-save" onclick="saveSlotEdit()"></button>
  </div>
</div>

<div class="layout">
  <nav class="sidebar">
    <button class="nav-btn active" onclick="showPanel('dashboard')" id="nb-dashboard">
      <span class="nav-icon">⊞</span><span class="nav-text">Dashboard</span></button>
    <button class="nav-btn" onclick="showPanel('printers');loadPrinterTab()" id="nb-printers">
      <span class="nav-icon">🖨</span><span class="nav-text">Drucker</span></button>
    <button class="nav-btn" onclick="showPanel('store');loadStore()" id="nb-store">
      <span class="nav-icon">🗂</span><span class="nav-text">Browser</span></button>
    <button class="nav-btn" onclick="showPanel('console');clearLogBadge()" id="nb-console">
      <span class="nav-icon">≡</span><span class="nav-text">Konsole</span><span id="log-badge" style="display:none;margin-left:4px;background:var(--err);color:#fff;border-radius:10px;font-size:10px;padding:1px 5px;font-weight:700"></span></button>
  </nav>

  <main>
    <!-- ═══ DASHBOARD ═══ -->
    <div class="panel active" id="panel-dashboard">
      <div class="grid">
        <!-- Kamera -->
        <div class="card" style="grid-column:1/-1">
          <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:10px">
            <div class="card-title" style="margin-bottom:0"><span>📷</span> <span id="d-card-cam">Kamera</span></div>
            <div style="display:flex;align-items:center;gap:10px">
              <span id="d-lbl-light" style="font-size:12px;color:var(--txt2)">💡 Licht</span>
              <label class="toggle">
                <input type="checkbox" id="d-light-toggle" onchange="setLight()">
                <span class="toggle-track"></span>
                <span class="toggle-thumb"></span>
              </label>
            </div>
          </div>
          <div class="cam-wrap" id="cam-wrap">
            <div class="cam-placeholder" id="cam-placeholder"><span id="cam-placeholder-txt">📷 Kamera nicht gestartet</span></div>
            <div class="cam-spinner" id="cam-spinner"></div>
            <img id="cam-img" style="display:none;width:100%;height:auto" alt="Kamera">
            <div class="cam-overlay" id="cam-overlay" style="display:none">
              <div style="font-size:12px;color:#fff" id="cam-fname"></div>
            </div>
            <button class="cam-toggle" onclick="toggleCam()" id="cam-toggle-btn">▶ Kamera</button>
          </div>
        </div>

        <!-- Fortschritt -->
        <div class="card" style="grid-column:1/-1">
          <div class="card-title"><span>◉</span> <span id="d-card-progress">Fortschritt</span></div>
          <img id="d-thumbnail" src="" alt="" style="display:none;width:100%;max-height:160px;object-fit:contain;border-radius:8px;background:#111;margin-bottom:10px">
          <div class="pct-big"><span id="d-pct">0</span><small>%</small></div>
          <div style="display:flex;align-items:center;gap:10px;margin:8px 0">
            <div class="progress-bar" style="flex:1;margin:0"><div class="progress-fill" id="d-pbar" style="width:0%"></div></div>
            <div class="time-block" style="padding:6px 10px;min-width:72px;text-align:center;flex-shrink:0">
              <div class="time-label" id="d-lbl-layers"></div>
              <div class="time-val" style="font-size:16px" id="d-layers">–</div>
            </div>
          </div>
          <div class="time-grid">
            <div class="time-block">
              <div class="time-label" id="d-lbl-elapsed"></div>
              <div class="time-val" id="d-elapsed">–</div>
            </div>
            <div class="time-block" id="d-slicer-row" style="display:none">
              <div class="time-label" id="d-slicer-label"></div>
              <div class="time-val" id="d-slicer-time">–</div>
            </div>
            <div class="time-block" style="color:var(--acc)">
              <div class="time-label" id="d-lbl-remain"></div>
              <div class="time-val" id="d-remain" style="color:var(--acc)">–</div>
            </div>
          </div>
          <div class="fname" id="d-fname" title="" style="margin-top:6px">–</div>
          <div class="ctrl-btns" id="d-ctrl-btns" style="margin-top:12px">
            <button class="btn btn-pause btn-sm" id="d-btn-pause" onclick="printAction('pause')">⏸ Pause</button>
            <button class="btn btn-resume btn-sm" id="d-btn-resume" onclick="printAction('resume')">▶ Weiter</button>
            <button class="btn btn-skip btn-sm" id="d-btn-skip" onclick="openSkipDialog()" style="display:none">✂ <span id="d-btn-skip-label">Objekte</span></button>
            <button class="btn btn-cancel btn-sm" id="d-btn-cancel" onclick="confirmCancel()">✕ Stopp</button>
          </div>
        </div>

        <!-- Temperatursteuerung + Verlauf -->
        <div class="card" style="grid-column:1/-1">
          <div class="card-title"><span>⊙</span> <span id="d-card-temps">Temperaturen</span></div>
          <div class="temp-card-inner">
            <div class="temp-block">
              <div class="temp-label">Nozzle</div>
              <div class="temp-row">
                <div class="temp-val" id="d-nt">–</div>
                <div class="temp-unit">°C</div>
              </div>
              <div class="temp-target">→ <span id="d-nt-t">0</span>°C</div>
              <div class="progress-bar" style="margin:8px 0 0">
                <div class="progress-fill" id="d-ntbar" style="width:0%;background:linear-gradient(90deg,var(--accent2),#ffb020)"></div>
              </div>
              <div class="temp-edit" style="margin-top:10px">
                <input type="number" class="temp-input" id="p-nozzle-inp" placeholder="Ziel" min="0" max="300" style="flex:1">
                <button class="btn btn-sm btn-accent" onclick="setNozzle()"><span class="lbl-set">Set</span></button>
                <button class="btn btn-sm" style="background:var(--raised);color:var(--txt)" onclick="document.getElementById('p-nozzle-inp').value=0;setNozzle()"><span class="lbl-off">Aus</span></button>
              </div>
            </div>
            <div class="temp-block">
              <div class="temp-label" id="d-lbl-bed">Bett</div>
              <div class="temp-row">
                <div class="temp-val" id="d-bt">–</div>
                <div class="temp-unit">°C</div>
              </div>
              <div class="temp-target">→ <span id="d-bt-t">0</span>°C</div>
              <div class="progress-bar" style="margin:8px 0 0">
                <div class="progress-fill" id="d-btbar" style="width:0%;background:linear-gradient(90deg,#ff6b35,var(--warn))"></div>
              </div>
              <div class="temp-edit" style="margin-top:10px">
                <input type="number" class="temp-input" id="p-bed-inp" placeholder="Ziel" min="0" max="120" style="flex:1">
                <button class="btn btn-sm btn-accent" onclick="setBed()"><span class="lbl-set">Set</span></button>
                <button class="btn btn-sm" style="background:var(--raised);color:var(--txt)" onclick="document.getElementById('p-bed-inp').value=0;setBed()"><span class="lbl-off">Aus</span></button>
              </div>
            </div>
          </div>
          <div style="margin-top:14px">
            <div style="font-size:10px;color:var(--txt2);margin-bottom:4px" id="d-chart-label">Verlauf (letzte 60 Messungen)</div>
            <canvas id="d-chart" width="800" height="120" style="width:100%;height:120px;background:var(--raised);border-radius:8px"></canvas>
          </div>
        </div>

        <!-- Achsensteuerung -->
        <div class="card">
          <div class="card-title"><span>✛</span> <span id="ptitle-motion-xy">XY-Achsen</span></div>
          <div class="joypad">
            <div></div>
            <button class="joy" onclick="move(1,1,getStep())" title="Y+">▲</button>
            <div></div>
            <button class="joy" onclick="move(0,-1,getStep())" title="X−">◀</button>
            <button class="joy home" onclick="homeAll()" title="Home All">⌂</button>
            <button class="joy" onclick="move(0,1,getStep())" title="X+">▶</button>
            <div></div>
            <button class="joy" onclick="move(1,-1,getStep())" title="Y−">▼</button>
            <div></div>
          </div>
          <div class="step-btns">
            <button class="step-btn" onclick="setStep(this,0.1)">0.1</button>
            <button class="step-btn active" onclick="setStep(this,1)">1</button>
            <button class="step-btn" onclick="setStep(this,5)">5</button>
            <button class="step-btn" onclick="setStep(this,10)">10 mm</button>
          </div>
          <div class="home-btns">
            <button class="btn btn-sm" style="background:var(--raised);color:var(--txt)" onclick="homeZ()"><span class="lbl-home-z">Home Z</span></button>
            <button class="btn btn-sm" style="background:var(--raised);color:var(--txt)" onclick="homeXY()"><span class="lbl-home-xy">Home XY</span></button>
            <button class="btn btn-sm btn-accent" onclick="homeAll()"><span class="lbl-home-all">Home All</span></button>
            <button class="btn btn-sm" style="background:var(--raised);color:var(--txt)" onclick="disableMotors()"><span class="lbl-disable-motors">Motors Off</span></button>
          </div>
        </div>
        <div class="card">
          <div class="card-title"><span>↕</span> <span id="ptitle-motion-z">Z-Achse</span></div>
          <div class="joypad" style="grid-template-columns:52px;grid-template-rows:repeat(2,52px)">
            <button class="joy" onclick="move(2,1,getStep())" title="Z+">▲</button>
            <button class="joy" onclick="move(2,-1,getStep())" title="Z−">▼</button>
          </div>
          <div style="text-align:center;margin-top:8px;font-size:12px;color:var(--txt2)"><span class="lbl-step">Schrittweite:</span> <span id="step-display">1</span> mm</div>
        </div>

        <!-- Print Speed -->
        <div class="card">
          <div class="card-title"><span>🏎</span> <span id="d-card-speed">Druckgeschwindigkeit</span></div>
          <div style="display:flex;gap:8px;margin-top:4px">
            <button class="spd-btn" id="d-spd-1" onclick="setSpeed(1)">
              <span class="spd-icon">🐢</span>
              <span id="d-spd-lbl-1">Leise</span>
            </button>
            <button class="spd-btn spd-active" id="d-spd-2" onclick="setSpeed(2)">
              <span class="spd-icon">⚡</span>
              <span id="d-spd-lbl-2">Normal</span>
            </button>
            <button class="spd-btn" id="d-spd-3" onclick="setSpeed(3)">
              <span class="spd-icon">🚀</span>
              <span id="d-spd-lbl-3">Sport</span>
            </button>
          </div>
          <div class="spd-bar" style="margin-top:12px">
            <div class="spd-bar-fill" id="d-spd-bar" style="width:50%"></div>
          </div>
        </div>

        <!-- Lüfter -->
        <div class="card">
          <div class="card-title"><span>🌀</span> <span id="d-card-lightfan">Lüfter</span></div>
          <div class="slider-row">
            <input type="range" class="slider" min="0" max="100" value="0" id="d-fan" oninput="document.getElementById('d-fan-val').textContent=this.value" onchange="setFan()">
            <span class="slider-val" id="d-fan-val">0</span>
          </div>
          <div style="margin-top:12px;display:flex;gap:8px;flex-wrap:wrap">
            <button class="btn btn-sm" style="background:var(--raised);color:var(--txt)" onclick="quickFan(0)">Aus</button>
            <button class="btn btn-sm" style="background:var(--raised);color:var(--txt)" onclick="quickFan(25)">25%</button>
            <button class="btn btn-sm" style="background:var(--raised);color:var(--txt)" onclick="quickFan(50)">50%</button>
            <button class="btn btn-sm" style="background:var(--raised);color:var(--txt)" onclick="quickFan(75)">75%</button>
            <button class="btn btn-sm btn-accent" onclick="quickFan(100)">100%</button>
          </div>
        </div>

        <div id="d-ace-dry-wrap" style="display:none">
          <div id="d-ace-dry-grid" style="display:contents"></div>
        </div>

        <!-- AMS -->
        <div class="card" style="grid-column:1/-1" id="d-ams-card">
          <div class="card-title"><span>◫</span> <span id="d-card-ams">Filament</span></div>
          <div class="ams-slots" id="ams-slots">
            <div style="grid-column:1/-1;text-align:center;color:var(--txt2);padding:20px" id="ams-no-data">Keine AMS-Daten empfangen</div>
          </div>
        </div>
      </div>
    </div>

    <!-- ═══ CONSOLE ═══ -->
    <!-- ═══ DRUCKER ═══ -->
    <div class="panel" id="panel-printers">
      <div class="card">
        <div class="card-title" style="display:flex;justify-content:space-between;align-items:center;margin-bottom:12px">
          <span id="printers-panel-title">🖨 Drucker</span>
          <div style="display:flex;gap:8px">
            <button onclick="openAddPrinterDialog()" style="font-size:12px;padding:4px 12px;background:var(--accent);border:none;border-radius:6px;color:#fff;cursor:pointer;font-weight:600">+ <span id="add-printer-btn-label">Drucker hinzufügen</span></button>
            <button onclick="loadPrinterTab()" style="font-size:12px;padding:4px 12px;background:var(--raised);border:1px solid var(--border);border-radius:6px;color:var(--txt2);cursor:pointer">↻</button>
          </div>
        </div>
        <div id="printers-grid" style="display:grid;grid-template-columns:repeat(auto-fill,minmax(260px,1fr));gap:14px"></div>
      </div>
    </div>

    <!-- ═══ GCODE STORE ═══ -->
    <div class="panel" id="panel-store">
      <div class="card">
        <div class="card-title" style="display:flex;justify-content:space-between;align-items:center;margin-bottom:10px">
          <span id="store-panel-title">🗂 Datei-Browser</span>
          <button id="store-refresh-btn" onclick="loadStore()" style="font-size:12px;padding:4px 12px;background:var(--raised);border:1px solid var(--border);border-radius:6px;color:var(--txt2);cursor:pointer">↻ Aktualisieren</button>
        </div>
        <div style="display:flex;gap:8px;margin-bottom:12px;flex-wrap:wrap">
          <input id="store-search" type="text" placeholder="🔍 Suche…" oninput="renderStore()"
            style="flex:1;min-width:140px;padding:6px 10px;background:var(--raised);border:1px solid var(--border);border-radius:6px;color:var(--txt);font-size:13px">
          <select id="store-filter" onchange="renderStore()"
            style="padding:6px 8px;background:var(--raised);border:1px solid var(--border);border-radius:6px;color:var(--txt);font-size:13px">
            <option value="all" id="sf-all">Alle</option>
            <option value="completed" id="sf-ok">✓ Erfolgreich</option>
            <option value="failed" id="sf-err">✗ Fehler</option>
            <option value="never" id="sf-new">Neu</option>
          </select>
          <select id="store-sort" onchange="renderStore()"
            style="padding:6px 8px;background:var(--raised);border:1px solid var(--border);border-radius:6px;color:var(--txt);font-size:13px">
            <option value="date_desc" id="ss-date">↓ Datum</option>
            <option value="name_asc" id="ss-name">A–Z Name</option>
            <option value="duration_asc" id="ss-dur">⏱ Druckzeit</option>
          </select>
        </div>
        <div id="store-empty" style="display:none;color:var(--txt2);text-align:center;padding:40px 0;font-size:14px">
        </div>
        <div id="store-grid" style="display:grid;grid-template-columns:repeat(auto-fill,minmax(200px,1fr));gap:14px"></div>
      </div>
    </div>

    <div class="panel" id="panel-console">
      <div class="card">
        <div class="card-title" style="display:flex;justify-content:space-between;align-items:center">
          <span><span>≡</span> <span id="ptitle-console">Ereignis-Log</span></span>
          <a id="btn-log-dl" href="/api/log/download" download="kx-bridge.log"
             style="font-size:12px;padding:4px 10px;background:var(--raised);border-radius:6px;color:var(--txt2);text-decoration:none">⬇ Download</a>
        </div>
        <div style="display:flex;gap:6px;margin-bottom:6px;flex-wrap:wrap;align-items:center">
          <input id="log-filter" type="text" placeholder="Filter…"
            oninput="renderLog()"
            style="flex:1;min-width:120px;padding:5px 10px;background:var(--raised);border:1px solid var(--border);border-radius:6px;color:var(--txt);font-size:12px;font-family:var(--mono)">
          <button id="btn-autoscroll" onclick="toggleAutoScroll()"
            style="font-size:12px;padding:5px 10px;border-radius:6px;border:1px solid var(--border);background:var(--accent);color:#fff;cursor:pointer;white-space:nowrap">⬇ Auto</button>
          <button onclick="consoleLogs=[];renderLog()"
            style="font-size:12px;padding:5px 10px;border-radius:6px;border:1px solid var(--border);background:var(--raised);color:var(--txt2);cursor:pointer">✕ Clear</button>
        </div>
        <div style="display:flex;gap:5px;margin-bottom:8px;flex-wrap:wrap">
          <span style="font-size:11px;color:var(--txt2);align-self:center;margin-right:2px">Dir:</span>
          <button class="log-dir-btn active" id="logdir-all"  onclick="setLogDir('all')"  style="font-size:11px;padding:3px 9px;border-radius:5px;border:1px solid var(--border);cursor:pointer"></button>
          <button class="log-dir-btn"        id="logdir-rx"   onclick="setLogDir('rx')"   style="font-size:11px;padding:3px 9px;border-radius:5px;border:1px solid var(--border);cursor:pointer">RX</button>
          <button class="log-dir-btn"        id="logdir-tx"   onclick="setLogDir('tx')"   style="font-size:11px;padding:3px 9px;border-radius:5px;border:1px solid var(--border);cursor:pointer">TX</button>
          <span style="font-size:11px;color:var(--txt2);align-self:center;margin-left:6px;margin-right:2px">Topic:</span>
          <button class="log-topic-btn" data-topic="multiColorBox" onclick="setLogTopic('multiColorBox')" style="font-size:11px;padding:3px 9px;border-radius:5px;border:1px solid var(--border);cursor:pointer">AMS</button>
          <button class="log-topic-btn" data-topic="print"         onclick="setLogTopic('print')"         style="font-size:11px;padding:3px 9px;border-radius:5px;border:1px solid var(--border);cursor:pointer">print</button>
          <button class="log-topic-btn" data-topic="info"          onclick="setLogTopic('info')"          style="font-size:11px;padding:3px 9px;border-radius:5px;border:1px solid var(--border);cursor:pointer">info</button>
          <button class="log-topic-btn" data-topic="status"        onclick="setLogTopic('status')"        style="font-size:11px;padding:3px 9px;border-radius:5px;border:1px solid var(--border);cursor:pointer">status</button>
        </div>
        <div class="console" id="console-log" style="height:calc(100vh - 260px);min-height:160px" onscroll="onLogScroll()"></div>
      </div>
    </div>
  </main>
</div>

<nav class="bottom-nav">
  <button class="bnav-btn active" onclick="showPanel('dashboard')" id="bnb-dashboard"><span class="bnav-icon">⊞</span>Dashboard</button>
  <button class="bnav-btn" onclick="showPanel('printers');loadPrinterTab()" id="bnb-printers"><span class="bnav-icon">🖨</span>Drucker</button>
  <button class="bnav-btn" onclick="showPanel('store');loadStore()" id="bnb-store"><span class="bnav-icon">🗂</span>Browser</button>
  <button class="bnav-btn" onclick="showPanel('console');clearLogBadge()" id="bnb-console"><span class="bnav-icon">≡</span>Log<span id="log-badge-bot" style="display:none;margin-left:3px;background:var(--err);color:#fff;border-radius:10px;font-size:10px;padding:1px 4px;font-weight:700"></span></button>
</nav>

<script>
// ── State ──
var S={nozzle_temp:0,nozzle_target:0,bed_temp:0,bed_target:0,
  print_state:'standby',filename:'',progress:0,print_duration:0,remain_time:0,
  curr_layer:0,total_layers:0,printer_name:'Kobra X',firmware_version:'–',
  camera_url:'',fan_speed:0,print_speed_mode:2,light_on:false,light_brightness:80,
  ams_slots:[],filament_mode:'toolhead',ace_units:[],ace_dry_presets:null,ace_drying:{status:0,target_temp:0,duration:0,remain_time:0,humidity:null,current_temp:null,units:[]}};
var tempHistory={n:[],b:[]};
var camOn=false;
var currentStep=1;
var currentPanel='dashboard';
var aceAutoRefillPrefs=(function(){
  try{return JSON.parse(localStorage.getItem('aceAutoRefillPrefs')||'{}')||{};}catch(_){return {};}
})();
var aceDryProfiles=(function(){
  try{return JSON.parse(localStorage.getItem('aceDryProfiles')||'{}')||{};}catch(_){return {};}
})();
var _aceDryDialogAceId=-1;
var _aceDryDialogPresetKey='';
var _aceDryDialogPresetOriginals={};
var ACE_DRY_PRESET_DEFAULTS={
  pla:{temp:45,duration_sec:4*3600},
  pla_plus:{temp:45,duration_sec:4*3600},
  petg:{temp:50,duration_sec:4*3600},
  tpu:{temp:55,duration_sec:4*3600},
  abs_asa:{temp:45,duration_sec:8*3600},
  pa_pc:{temp:55,duration_sec:12*3600}
};
var ACE_DRY_PRESETS={
  pla:{temp:45,duration_sec:4*3600},
  pla_plus:{temp:45,duration_sec:4*3600},
  petg:{temp:50,duration_sec:4*3600},
  tpu:{temp:55,duration_sec:4*3600},
  abs_asa:{temp:45,duration_sec:8*3600},
  pa_pc:{temp:55,duration_sec:12*3600},
  custom_1:{name:'Custom 1',temp:45,duration_sec:4*3600},
  custom_2:{name:'Custom 2',temp:45,duration_sec:4*3600},
  custom_3:{name:'Custom 3',temp:45,duration_sec:4*3600}
};

function _aceAutoRefillGet(aceId){return !!aceAutoRefillPrefs[String(aceId)];}
function _aceAutoRefillSet(aceId,on){
  aceAutoRefillPrefs[String(aceId)]=!!on;
  localStorage.setItem('aceAutoRefillPrefs',JSON.stringify(aceAutoRefillPrefs));
}
function _aceDryProfileGet(aceId){
  var p=aceDryProfiles[String(aceId)]||{};
  var temp=parseInt(p.temp,10);
  var dur=parseInt(p.duration_sec,10);
  if(!Number.isFinite(temp))temp=45;
  if(!Number.isFinite(dur))dur=4*3600;
  temp=Math.max(30,Math.min(80,temp));
  dur=Math.max(10*60,Math.min(24*3600,dur));
  return {temp:temp,duration_sec:dur,preset:p.preset||''};
}
function _aceDryProfileSet(aceId,temp,durationSec,preset){
  aceDryProfiles[String(aceId)]={
    temp:Math.max(30,Math.min(80,parseInt(temp,10)||45)),
    duration_sec:Math.max(10*60,Math.min(24*3600,parseInt(durationSec,10)||4*3600)),
    preset:preset||''
  };
  localStorage.setItem('aceDryProfiles',JSON.stringify(aceDryProfiles));
}
function _aceDryDurationMinFromSec(sec){
  var minutes=Math.round((parseInt(sec,10)||0)/60);
  return Math.max(10,Math.min(1440,minutes));
}
function _syncAceDryPresetsFromServer(raw){
  if(!raw||typeof raw!=='object')return;
  Object.keys(ACE_DRY_PRESETS).forEach(function(k){
    var p=raw[k];
    if(!p||typeof p!=='object')return;
    var t=parseInt(p.temp,10);
    var d=parseInt(p.duration_sec,10);
    if(Number.isFinite(t))ACE_DRY_PRESETS[k].temp=Math.max(30,Math.min(80,t));
    if(Number.isFinite(d))ACE_DRY_PRESETS[k].duration_sec=Math.max(10*60,Math.min(24*3600,d));
    if(/^custom_[123]$/.test(k)&&typeof p.name==='string'){
      var n=p.name.trim();
      ACE_DRY_PRESETS[k].name=n||('Custom '+k.slice(-1));
    }
  });
}

// ── Theme ──
function toggleTheme(){
  var h=document.documentElement;
  h.setAttribute('data-theme',h.getAttribute('data-theme')==='dark'?'light':'dark');
  localStorage.setItem('theme',h.getAttribute('data-theme'));
}
(function(){var t=localStorage.getItem('theme');if(t)document.documentElement.setAttribute('data-theme',t)})();

// ── i18n ──
var LANG_DE={
  header_status_standby:'Bereit',header_status_printing:'Druckt',header_status_complete:'Fertig',header_status_error:'Fehler',
  kobra_free:'Bereit',kobra_busy:'Beschäftigt',kobra_printing:'Druckt',kobra_preheating:'Aufheizen',kobra_auto_leveling:'Nivellierung',kobra_checking:'Prüfung',kobra_updated:'Aktualisierung',kobra_init:'Initialisierung',kobra_pausing:'Pausiert...',kobra_paused:'Pausiert',kobra_resuming:'Fortsetzen...',kobra_resumed:'Fortgesetzt',kobra_stopping:'Stoppt...',kobra_stoped:'Gestoppt',kobra_finished:'Abgeschlossen',kobra_failed:'Fehler',kobra_canceled:'Abgebrochen',kobra_offline:'Offline',
  nav_dashboard:'Dashboard',nav_print:'Druck',nav_temps:'Temperaturen',nav_motion:'Achsen',nav_ams:'AMS',nav_extras:'Licht / Lüfter',nav_console:'Konsole',
  card_progress:'Fortschritt',card_temps:'Temperaturen',card_light_fan:'Lüfter',card_speed:'Druckgeschwindigkeit',card_cam:'Kamera',lbl_elapsed:'Verstrichen:',lbl_remaining:'Restzeit:',lbl_slicer_time:'Slicer-Schätzung:',lbl_layers:'Layer',
  speed_silent:'🐢 Leise',speed_normal:'⚡ Normal',speed_sport:'🚀 Sport',
  lbl_light:'💡 Licht',lbl_feed:'Einziehen',lbl_unload:'Ausziehen',
  card_ace_dry:'ACE Trocknung',ace_dry_dryer:'Trockner',ace_dry_status_off:'Status: Aus',ace_dry_status_on:'Status: Aktiv',ace_dry_status_remaining:'Rest',ace_dry_humidity:'Luftfeuchte',ace_dry_current_temp:'Temperatur',ace_dry_chart:'Verlauf (Temp/Feuchte)',ace_dry_temp:'Temperatur (°C)',ace_dry_duration:'Dauer (Min)',ace_dry_start:'▶ Start',ace_dry_stop:'■ Stop',ace_dry_auto_refill:'Auto Refill',ace_dry_enable:'Enable Drying',ace_dry_temp_line:'Trocknungstemperatur',ace_dry_time_line:'Trocknungszeit',ace_dry_ui_pending:'(nur UI, Backend folgt)',ace_dry_dialog_title:'Dryer Temp/Time Settings',ace_dry_dialog_temp:'Temperature (30-80°C)',ace_dry_dialog_time:'Rem. Time (h:m:s)',ace_dry_dialog_confirm:'Confirm',ace_dry_dialog_cancel:'Cancel',ace_dry_dialog_save_restart:'Speichern & Neustart',ace_dry_dialog_custom_name:'Custom Name',
  cam_placeholder:'📷 Kamera nicht gestartet',btn_cam_start:'▶ Kamera',btn_cam_stop:'◼ Kamera',
  btn_pause:'⏸ Pause',btn_resume:'▶ Weiter',btn_cancel:'✕ Stopp',
  label_nozzle:'Nozzle',label_bed:'Bett',label_fan:'🌀 Lüfter',label_light:'💡 Licht',label_on_off:'Ein / Aus',label_speed:'Geschwindigkeit',
  panel_print_title:'Drucksteuerung',panel_print_btn_pause:'⏸ Pause',panel_print_btn_resume:'▶ Fortsetzen',panel_print_btn_cancel:'✕ Abbrechen',panel_print_temps_live:'Temperaturen (Live)',
  label_set:'Setzen',label_off:'Aus',
  panel_temps_nozzle:'Nozzle',panel_temps_bed:'Heizbett',panel_temps_chart:'Verlauf (letzte 60 Messungen)',label_target_c:'Ziel:',
  panel_motion_xy:'XY-Achsen',panel_motion_z:'Z-Achse',label_step:'Schrittweite:',btn_home_z:'Home Z',btn_home_xy:'Home XY',btn_home_all:'Home All',btn_disable_motors:'Motoren aus',
  panel_ams_title:'Filament',card_ams:'Filament',ams_no_data:'Keine AMS-Daten empfangen',label_slot:'Slot',ams_empty:'Leer',
  panel_extras_light:'Licht',panel_extras_fan:'Lüfter',panel_extras_camera:'Kamera',btn_cam_start2:'▶ Start',btn_cam_stop2:'◼ Stop',
  panel_console_title:'Ereignis-Log',
  log_light_on:'Licht an',log_light_off:'Licht aus',log_fan:'Lüfter →',log_nozzle:'Nozzle →',log_bed:'Bett →',log_axis:'Achse',log_home:'Home',log_home_all:'Home All',log_cam_start:'Kamera gestartet:',log_cam_stop:'Kamera gestoppt',log_poll_error:'Poll-Fehler:',log_error:'Fehler:',
  confirm_cancel:'Druck wirklich abbrechen?',
  settings_title:'Einstellungen',settings_connection:'Verbindung',settings_print:'Druckeinstellungen',settings_poll:'Poll-Intervall',settings_version:'Version',
  settings_save:'Speichern & Neustart',settings_printer_name:'Drucker-Name',settings_printer_ip:'Drucker-IP',settings_mqtt_port:'MQTT-Port',
  settings_username:'MQTT-Benutzername',settings_password:'MQTT-Passwort',settings_device_id:'Device-ID',settings_mode_id:'Mode-ID',hint_ip_no_port:'Nur IP-Adresse, kein Port (z.B. 192.168.1.102)',
  settings_default_slot:'Standard-Slot (Einfarbdruck)',settings_slot_auto:'Auto (alle belegten Slots)',settings_auto_leveling:'Auto-Leveling vor Druck',
  update_check:'Auf Updates prüfen',update_checking:'Prüfe...',update_available:'verfügbar',update_none:'Bereits aktuell',
  update_apply:'Jetzt installieren',update_applying:'Lade herunter...',update_restarting:'Starte neu...',update_error:'Fehler',
  btn_connect:'⚡ Verbinden',btn_disconnect:'✕ Trennen',
  lbl_conn_error:'Verbindungsfehler:',
  slot_edit_title:'Slot bearbeiten',slot_edit_color:'Farbe',slot_edit_material:'Material',
  slot_edit_load:'⬇ Einziehen',slot_edit_unload:'⬆ Ausziehen',
  slot_edit_save:'💾 Speichern',slot_edit_custom:'z.B. PLA, PETG, ABS…',
  slot_edit_ok:'AMS Slot',
  log_dir_all:'Alle',
  file_ready_btn:'▶ Druck starten',
  file_slots_btn:'🎨 Slots wählen',
  file_cancel_btn:'✕ Abbrechen',
  nav_printers:'Drucker',
  skip_title:'✂ Objekte überspringen',skip_hint:'Objekte abwählen, die nicht weiter gedruckt werden sollen:',
  skip_btn_label:'Objekte',skip_no_objects:'Keine Objekte in diesem Druck.',
  skip_already:'übersprungen',skip_select_at_least_one:'Bitte mindestens ein Objekt wählen.',
  skip_sending:'Sende …',skip_success:'Objekte werden übersprungen.',
  fd_objects_hint:'Objekte überspringen (optional):',
  add_printer:'Drucker hinzufügen',apd_lbl_ip:'Drucker-IP',apd_lbl_name:'Name (optional)',
  apd_fetching:'Hole Daten vom Drucker…',apd_success:'Drucker hinzugefügt, Bridge startet neu…',apd_err_ip:'Bitte IP-Adresse eingeben',
  printers_remove:'Drucker entfernen',printers_remove_confirm:'Drucker "{name}" entfernen? Die Bridge startet neu.',
  printers_active:'● aktiv',
  printers_switch:'Wechseln →',
  printers_current:'Aktueller Drucker',
  printers_loading:'Lade…',
  printers_none:'Keine Drucker konfiguriert.',
  printers_empty_hint:'Noch kein Drucker eingerichtet.',
  nav_browser:'Browser',
  panel_browser_title:'Datei-Browser',
  store_empty:'Noch keine Dateien hochgeladen.',
  store_refresh:'↻ Aktualisieren',
  store_print:'▶ Drucken',
  store_delete_confirm:'Datei löschen?',
  store_print_confirm:'Datei drucken?',
  store_no_results:'Keine Dateien gefunden.',
  store_never:'noch nicht gedruckt',
  sf_all:'Alle',sf_ok:'✓ Erfolgreich',sf_err:'✗ Fehler',sf_new:'Neu',
  ss_date:'↓ Datum',ss_name:'A–Z Name',ss_dur:'⏱ Druckzeit'
};
var LANG_EN={
  header_status_standby:'Ready',header_status_printing:'Printing',header_status_complete:'Complete',header_status_error:'Error',
  kobra_free:'Ready',kobra_busy:'Busy',kobra_printing:'Printing',kobra_preheating:'Preheating',kobra_auto_leveling:'Auto Leveling',kobra_checking:'Checking',kobra_updated:'Updating',kobra_init:'Initializing',kobra_pausing:'Pausing...',kobra_paused:'Paused',kobra_resuming:'Resuming...',kobra_resumed:'Resumed',kobra_stopping:'Stopping...',kobra_stoped:'Stopped',kobra_finished:'Finished',kobra_failed:'Error',kobra_canceled:'Cancelled',kobra_offline:'Offline',
  nav_dashboard:'Dashboard',nav_print:'Print',nav_temps:'Temperatures',nav_motion:'Motion',nav_ams:'AMS',nav_extras:'Light / Fan',nav_console:'Console',
  card_progress:'Progress',card_temps:'Temperatures',card_light_fan:'Fan',card_speed:'Print Speed',card_cam:'Camera',lbl_elapsed:'Elapsed:',lbl_remaining:'Remaining:',lbl_slicer_time:'Slicer estimate:',lbl_layers:'Layer',
  speed_silent:'🐢 Silent',speed_normal:'⚡ Normal',speed_sport:'🚀 Sport',
  lbl_light:'💡 Light',lbl_feed:'Load',lbl_unload:'Unload',
  card_ace_dry:'ACE Drying',ace_dry_dryer:'Dryer',ace_dry_status_off:'Status: Off',ace_dry_status_on:'Status: Active',ace_dry_status_remaining:'Remaining',ace_dry_humidity:'Humidity',ace_dry_current_temp:'Temperature',ace_dry_chart:'History (Temp/Humidity)',ace_dry_temp:'Temperature (°C)',ace_dry_duration:'Duration (min)',ace_dry_start:'▶ Start',ace_dry_stop:'■ Stop',ace_dry_auto_refill:'Auto Refill',ace_dry_enable:'Enable Drying',ace_dry_temp_line:'Drying Temperature',ace_dry_time_line:'Drying Time',ace_dry_ui_pending:'(UI only, backend next)',ace_dry_dialog_title:'Dryer Temp/Time Settings',ace_dry_dialog_temp:'Temperature (30-80°C)',ace_dry_dialog_time:'Rem. Time (h:m:s)',ace_dry_dialog_confirm:'Confirm',ace_dry_dialog_cancel:'Cancel',ace_dry_dialog_save_restart:'Save & Restart',ace_dry_dialog_custom_name:'Custom Name',
  cam_placeholder:'📷 Camera not started',btn_cam_start:'▶ Camera',btn_cam_stop:'◼ Camera',
  btn_pause:'⏸ Pause',btn_resume:'▶ Resume',btn_cancel:'✕ Stop',
  label_nozzle:'Nozzle',label_bed:'Bed',label_fan:'🌀 Fan',label_light:'💡 Light',label_on_off:'On / Off',label_speed:'Speed',
  panel_print_title:'Print Control',panel_print_btn_pause:'⏸ Pause',panel_print_btn_resume:'▶ Resume',panel_print_btn_cancel:'✕ Cancel',panel_print_temps_live:'Temperatures (Live)',
  label_set:'Set',label_off:'Off',
  panel_temps_nozzle:'Nozzle',panel_temps_bed:'Heated Bed',panel_temps_chart:'History (last 60 readings)',label_target_c:'Target:',
  panel_motion_xy:'XY Axes',panel_motion_z:'Z Axis',label_step:'Step size:',btn_home_z:'Home Z',btn_home_xy:'Home XY',btn_home_all:'Home All',btn_disable_motors:'Motors Off',
  panel_ams_title:'Filament',card_ams:'Filament',ams_no_data:'No AMS data received',label_slot:'Slot',ams_empty:'Empty',
  panel_extras_light:'Light',panel_extras_fan:'Fan',panel_extras_camera:'Camera',btn_cam_start2:'▶ Start',btn_cam_stop2:'◼ Stop',
  panel_console_title:'Event Log',
  log_light_on:'Light on',log_light_off:'Light off',log_fan:'Fan →',log_nozzle:'Nozzle →',log_bed:'Bed →',log_axis:'Axis',log_home:'Home',log_home_all:'Home All',log_cam_start:'Camera started:',log_cam_stop:'Camera stopped',log_poll_error:'Poll error:',log_error:'Error:',
  confirm_cancel:'Really cancel the print?',
  settings_title:'Settings',settings_connection:'Connection',settings_print:'Print Settings',settings_poll:'Poll Interval',settings_version:'Version',
  settings_save:'Save & Restart',settings_printer_name:'Printer Name',settings_printer_ip:'Printer IP',settings_mqtt_port:'MQTT Port',
  settings_username:'MQTT Username',settings_password:'MQTT Password',settings_device_id:'Device ID',settings_mode_id:'Mode ID',hint_ip_no_port:'IP address only, no port (e.g. 192.168.1.102)',
  settings_default_slot:'Default Slot (single color)',settings_slot_auto:'Auto (all loaded slots)',settings_auto_leveling:'Auto-Leveling before print',
  update_check:'Check for Updates',update_checking:'Checking...',update_available:'available',update_none:'Already up to date',
  update_apply:'Install Now',update_applying:'Downloading...',update_restarting:'Restarting...',update_error:'Error',
  btn_connect:'⚡ Connect',btn_disconnect:'✕ Disconnect',
  lbl_conn_error:'Connection error:',
  slot_edit_title:'Edit Slot',slot_edit_color:'Color',slot_edit_material:'Material',
  slot_edit_load:'⬇ Load',slot_edit_unload:'⬆ Unload',
  slot_edit_save:'💾 Save',slot_edit_custom:'e.g. PLA, PETG, ABS…',
  slot_edit_ok:'AMS Slot',
  log_dir_all:'All',
  file_ready_btn:'▶ Start Print',
  file_slots_btn:'🎨 Select Slots',
  file_cancel_btn:'✕ Cancel',
  nav_printers:'Printers',
  skip_title:'✂ Skip objects',skip_hint:'Uncheck objects you no longer want to print:',
  skip_btn_label:'Objects',skip_no_objects:'No objects in this print.',
  skip_already:'skipped',skip_select_at_least_one:'Please pick at least one object.',
  skip_sending:'Sending …',skip_success:'Objects will be skipped.',
  fd_objects_hint:'Skip objects (optional):',
  add_printer:'Add printer',apd_lbl_ip:'Printer IP',apd_lbl_name:'Name (optional)',
  apd_fetching:'Fetching data from printer…',apd_success:'Printer added, bridge restarting…',apd_err_ip:'Please enter an IP address',
  printers_remove:'Remove printer',printers_remove_confirm:'Remove printer "{name}"? The bridge will restart.',
  printers_active:'● active',
  printers_switch:'Switch →',
  printers_current:'Current printer',
  printers_loading:'Loading…',
  printers_none:'No printers configured.',
  printers_empty_hint:'No printer set up yet.',
  nav_browser:'Browser',
  panel_browser_title:'File Browser',
  store_empty:'No files uploaded yet.',
  store_refresh:'↻ Refresh',
  store_print:'▶ Print',
  store_delete_confirm:'Delete file?',
  store_print_confirm:'Print file?',
  store_no_results:'No files found.',
  store_never:'never printed',
  sf_all:'All',sf_ok:'✓ Completed',sf_err:'✗ Failed',sf_new:'New',
  ss_date:'↓ Date',ss_name:'A–Z Name',ss_dur:'⏱ Print time'
};
// Multi-Printer: BASE_URL aus Pathname (/printer2 → andere Bridge-Instanz)
var _printers=[];
var _activePrinter=null;
(function(){
  var path=window.location.pathname.replace(/\/+$/,'');
  var m=path.match(/^\/printer(\d+)$/);
  var idx=m?parseInt(m[1]):1;
  window._printerIndex=idx;
})();
function _apiUrl(path){
  if(_activePrinter&&_activePrinter.bridge_url){
    return _activePrinter.bridge_url.replace(/\/+$/,'')+path;
  }
  return path;
}
function initPrinters(){
  fetch('/kx/printers').then(function(r){return r.json()}).then(function(d){  // immer lokale Instanz für Drucker-Liste
    _printers=d.result||[];
    var idx=window._printerIndex||1;
    _activePrinter=_printers.find(function(p){return String(p.id)===String(idx)})||_printers[0]||null;
    renderPrinterDropdown();
  }).catch(function(){});
}
function renderPrinterDropdown(){
  var wrap=document.getElementById('printer-dropdown-wrap');
  var single=document.getElementById('h-pname-single');
  var name=_printers.length===0?'–':(_activePrinter?(_activePrinter.name||'Kobra X'):'Kobra X');
  var pname=document.getElementById('h-pname');
  if(pname)pname.textContent=name;
  if(single)single.textContent=name;
  if(_printers.length>1){
    if(wrap)wrap.style.display='';
    if(single)single.style.display='none';
    var menu=document.getElementById('printer-dropdown-menu');
    if(menu){
      menu.innerHTML=_printers.map(function(p){
        var active=_activePrinter&&String(p.id)===String(_activePrinter.id);
        var num=p.id;
        return '<a href="/printer'+num+'" style="display:block;padding:10px 14px;color:'+(active?'var(--accent)':'var(--txt)')+';text-decoration:none;font-size:13px;border-bottom:1px solid var(--border)" '+(active?'style="font-weight:600"':'')+'>'+
          (active?'▶ ':'')+p.name+'</a>';
      }).join('');
    }
  } else {
    if(wrap)wrap.style.display='none';
    if(single)single.style.display='';
  }
}
function togglePrinterDropdown(){
  var menu=document.getElementById('printer-dropdown-menu');
  if(menu)menu.style.display=menu.style.display==='none'?'block':'none';
}
document.addEventListener('click',function(e){
  var wrap=document.getElementById('printer-dropdown-wrap');
  if(wrap&&!wrap.contains(e.target)){
    var menu=document.getElementById('printer-dropdown-menu');
    if(menu)menu.style.display='none';
  }
});

var currentLang='de';
var T=LANG_DE;
function toggleLang(){
  currentLang=currentLang==='de'?'en':'de';
  T=currentLang==='de'?LANG_DE:LANG_EN;
  localStorage.setItem('lang',currentLang);
  document.getElementById('lang-btn').textContent=currentLang==='de'?'EN':'DE';
  document.documentElement.setAttribute('lang',currentLang);
  applyLang();
}
function applyLang(){
  ensureAceDryCards();
  // Nav
  var nb=document.getElementById('nb-dashboard');if(nb)nb.querySelector('.nav-text').textContent=T.nav_dashboard;
  nb=document.getElementById('nb-console');if(nb)nb.querySelector('.nav-text').textContent=T.nav_console;
  nb=document.getElementById('nb-printers');if(nb)nb.querySelector('.nav-text').textContent=T.nav_printers;
  nb=document.getElementById('nb-store');if(nb)nb.querySelector('.nav-text').textContent=T.nav_browser;
  // Bottom nav
  var bnb=document.getElementById('bnb-dashboard');if(bnb)bnb.lastChild.textContent=T.nav_dashboard;
  bnb=document.getElementById('bnb-console');if(bnb)bnb.lastChild.textContent=T.nav_console;
  bnb=document.getElementById('bnb-printers');if(bnb)bnb.lastChild.textContent=T.nav_printers;
  bnb=document.getElementById('bnb-store');if(bnb)bnb.lastChild.textContent=T.nav_browser;
  // Browser panel
  setText('printers-panel-title','🖨 '+T.nav_printers);
  setText('add-printer-btn-label',T.add_printer);
  setText('apd-title',T.add_printer);
  setText('skip-title',T.skip_title);
  setText('skip-hint',T.skip_hint);
  setText('d-btn-skip-label',T.skip_btn_label);
  setText('fd-objects-hint',T.fd_objects_hint);
  setText('apd-lbl-ip',T.apd_lbl_ip);
  setText('apd-lbl-name',T.apd_lbl_name);
  setText('store-panel-title','🗂 '+T.panel_browser_title);
  var srb=document.getElementById('store-refresh-btn');if(srb)srb.textContent=T.store_refresh;
  setText('store-empty',T.store_empty);
  setText('sf-all',T.sf_all);setText('sf-ok',T.sf_ok);setText('sf-err',T.sf_err);setText('sf-new',T.sf_new);
  setText('ss-date',T.ss_date);setText('ss-name',T.ss_name);setText('ss-dur',T.ss_dur);
  // Dashboard card titles
  setText('d-card-progress',T.card_progress);
  setText('d-card-temps',T.card_temps);
  setText('d-card-lightfan',T.card_light_fan);
  setText('d-card-speed',T.card_speed);
  setText('d-card-cam',T.card_cam);
  setText('d-card-ams',T.panel_ams_title);
  setText('d-lbl-elapsed',T.lbl_elapsed);
  setText('d-lbl-remain',T.lbl_remaining);
  setText('d-slicer-label',T.lbl_slicer_time);
  setText('d-lbl-layers',T.lbl_layers);
  setText('d-lbl-light',T.lbl_light);
  setText('d-lbl-bed',T.label_bed);
  // Dashboard buttons
  setText('d-btn-pause',T.btn_pause);
  setText('d-btn-resume',T.btn_resume);
  setText('d-btn-cancel',T.btn_cancel);
  setText('cam-toggle-btn',camOn?T.btn_cam_stop:T.btn_cam_start);
  setText('cam-placeholder-txt',T.cam_placeholder);
  // Temp labels
  document.querySelectorAll('.lbl-set').forEach(e=>e.textContent=T.label_set);
  document.querySelectorAll('.lbl-off').forEach(e=>e.textContent=T.label_off);
  setText('d-chart-label',T.panel_temps_chart);
  // Axis labels
  setText('ptitle-motion-xy',T.panel_motion_xy);
  setText('ptitle-motion-z',T.panel_motion_z);
  document.querySelectorAll('.lbl-home-z').forEach(e=>e.textContent=T.btn_home_z);
  document.querySelectorAll('.lbl-home-xy').forEach(e=>e.textContent=T.btn_home_xy);
  document.querySelectorAll('.lbl-home-all').forEach(e=>e.textContent=T.btn_home_all);
  document.querySelectorAll('.lbl-disable-motors').forEach(e=>e.textContent=T.btn_disable_motors);
  document.querySelectorAll('.lbl-step').forEach(e=>e.textContent=T.label_step);
  document.querySelectorAll('.temp-input').forEach(e=>e.setAttribute('placeholder',T.label_target_c.replace(':','')));
  // Console
  setText('ptitle-console',T.panel_console_title);
  // Settings modal
  setText('modal-title-settings',T.settings_title);
  setText('modal-sec-connection',T.settings_connection);
  setText('modal-sec-print',T.settings_print);
  setText('modal-sec-poll',T.settings_poll);
  setText('modal-sec-version',T.settings_version);
  setText('btn-save-settings',T.settings_save);
  setText('lbl-printer-name',T.settings_printer_name);
  setText('lbl-printer-ip',T.settings_printer_ip);
  setText('lbl-mqtt-port',T.settings_mqtt_port);
  setText('lbl-username',T.settings_username);
  setText('lbl-password',T.settings_password);
  setText('lbl-device-id',T.settings_device_id);
  setText('lbl-mode-id',T.settings_mode_id);
  setText('lbl-default-slot',T.settings_default_slot);
  setText('opt-slot-auto',T.settings_slot_auto);
  setText('lbl-auto-leveling',T.settings_auto_leveling);

  setText('lbl-update-check',T.update_check);
  setText('lbl-update-apply',T.update_apply);
  // Speed buttons
  setText('d-spd-lbl-1',T.speed_silent.replace(/^\S+\s/,''));
  setText('d-spd-lbl-2',T.speed_normal.replace(/^\S+\s/,''));
  setText('d-spd-lbl-3',T.speed_sport.replace(/^\S+\s/,''));
  // AMS feed/unload
  document.querySelectorAll('.lbl-feed').forEach(e=>e.textContent=T.lbl_feed);
  document.querySelectorAll('.lbl-unload').forEach(e=>e.textContent=T.lbl_unload);
  for(var i=0;i<4;i++){
    setText('d-card-ace-dry-'+i,'ACE '+(i+1)+' - '+(T.ace_dry_dryer||'Dryer'));
    setText('d-ace-auto-refill-label-'+i,T.ace_dry_auto_refill||'Auto Refill');
    setText('d-ace-drying-enable-label-'+i,T.ace_dry_enable||'Enable Drying');
    setText('d-ace-dry-humidity-label-'+i,(T.ace_dry_humidity||'Humidity')+':');
    setText('d-ace-dry-current-temp-label-'+i,(T.ace_dry_current_temp||'Current Temp')+':');
    setText('d-ace-dry-target-label-'+i,(T.ace_dry_temp_line||'Drying Temperature')+':');
    setText('d-ace-dry-time-label-'+i,(T.ace_dry_time_line||'Drying Time')+':');
    setText('d-ace-dry-chart-label-'+i,T.ace_dry_chart||'History (Temp/Humidity)');
    var adTemp=document.getElementById('ace-dry-temp-'+i);if(adTemp)adTemp.setAttribute('placeholder',T.ace_dry_temp);
    var adDur=document.getElementById('ace-dry-duration-'+i);if(adDur)adDur.setAttribute('placeholder',T.ace_dry_duration);
  }
  setText('ace-dry-dialog-title',T.ace_dry_dialog_title||'Dryer Temp/Time Settings');
  setText('ace-dry-dialog-temp-label',T.ace_dry_dialog_temp||'Temperature (30-80°C)');
  setText('ace-dry-dialog-time-label',T.ace_dry_dialog_time||'Rem. Time (h:m:s)');
  setText('ace-dry-dialog-custom-name-label',T.ace_dry_dialog_custom_name||'Custom Name');
  setText('ace-dry-dialog-cancel',T.ace_dry_dialog_cancel||'Cancel');
  setText('ace-dry-dialog-confirm',T.ace_dry_dialog_confirm||'Confirm');
  setText('ace-dry-dialog-reset-default',T.ace_dry_dialog_reset_default||'Reset to Default');
  setText('ace-dry-dialog-save-preset',T.ace_dry_dialog_save_restart||'Save & Restart');
  aceDryDialogSyncCustomButtonNames();
  // conn-btn text (nur wenn nicht im Übergangszustand)
  updateConnBtn();
  // Slot-Edit-Dialog
  setText('lbl-slot-color',T.slot_edit_color);
  setText('lbl-slot-material',T.slot_edit_material);
  setText('btn-slot-edit-save',T.slot_edit_save);
  updateSlotEditFeedButton();
  var mi=document.getElementById('slot-edit-mat');if(mi)mi.setAttribute('placeholder',T.slot_edit_custom);
  setText('logdir-all',T.log_dir_all);
  setText('file-ready-btn',T.file_ready_btn);
  setText('file-slots-btn',T.file_slots_btn);
  setText('file-cancel-btn',T.file_cancel_btn);
  setText('file-cancel-btn',T.file_cancel_btn);
}
function setText(id,txt){var el=document.getElementById(id);if(el)el.textContent=txt;}

function ensureAceDryCards(){
  var grid=document.getElementById('d-ace-dry-grid');
  if(!grid||grid.getAttribute('data-init')==='1')return;
  var html='';
  for(var i=0;i<4;i++){
    html+='<div class="card" id="d-ace-dry-card-'+i+'" style="display:none">'
      +'<div class="card-title"><span>♨</span> <span id="d-card-ace-dry-'+i+'">ACE '+(i+1)+' - Dryer</span></div>'
      +'<div style="display:flex;justify-content:space-between;gap:10px;font-size:14px;color:var(--txt2);margin-bottom:10px">'
        +'<span><span id="d-ace-dry-current-temp-label-'+i+'">Temperature:</span> <span id="d-ace-dry-current-temp-'+i+'" style="font-size:30px;font-weight:700;color:#ff8c2f;line-height:1">-</span></span>'
        +'<span><span id="d-ace-dry-humidity-label-'+i+'">Humidity:</span> <span id="d-ace-dry-humidity-'+i+'" style="font-size:30px;font-weight:700;color:#3aa8ff;line-height:1">-</span></span>'
      +'</div>'
      +'<div style="height:1px;background:var(--border);margin-bottom:10px"></div>'
      +'<div style="display:flex;justify-content:space-between;gap:10px;font-size:14px;color:var(--txt2);margin-bottom:10px">'
        +'<span><span id="d-ace-dry-target-label-'+i+'">Drying Temperature:</span> <span id="d-ace-dry-target-'+i+'" style="font-size:30px;font-weight:700;color:#ff8c2f;line-height:1">-</span></span>'
        +'<span><span id="d-ace-dry-time-label-'+i+'">Drying Time:</span> <span id="d-ace-dry-time-'+i+'" style="font-size:30px;font-weight:700;color:#fff;line-height:1">-</span></span>'
      +'</div>'
      +'<div style="margin-bottom:10px">'
        +'<button onclick="openAceDryDialog('+i+')" title="Edit Dryer Temp/Time Settings" style="width:100%;padding:8px 10px;border-radius:8px;border:1px solid var(--accent);background:var(--accent);color:#000;cursor:pointer;font-size:13px;font-weight:600;line-height:1.2">Set Temp/Time</button>'
      +'</div>'
      +'<div style="height:1px;background:var(--border);margin-bottom:10px"></div>'
      +'<div class="toggle-row" style="margin-bottom:10px">'
        +'<span class="toggle-label" id="d-ace-auto-refill-label-'+i+'">Auto Refill</span>'
        +'<label class="toggle">'
          +'<input type="checkbox" id="ace-auto-refill-toggle-'+i+'" onchange="aceAutoRefillToggle('+i+')">'
          +'<span class="toggle-track"></span>'
          +'<span class="toggle-thumb"></span>'
        +'</label>'
      +'</div>'
      +'<div class="toggle-row" style="margin-bottom:8px">'
        +'<span class="toggle-label" id="d-ace-drying-enable-label-'+i+'">Enable Drying</span>'
        +'<label class="toggle">'
          +'<input type="checkbox" id="ace-dry-enable-toggle-'+i+'" onchange="aceDryToggle('+i+',this.checked)">'
          +'<span class="toggle-track"></span>'
          +'<span class="toggle-thumb"></span>'
        +'</label>'
      +'</div>'
      +'</div>';
  }
  grid.innerHTML=html;
  grid.setAttribute('data-init','1');
}
(function(){
  var l=localStorage.getItem('lang')||'de';
  currentLang=l;T=l==='de'?LANG_DE:LANG_EN;
  document.getElementById('lang-btn').textContent=l==='de'?'EN':'DE';
  document.documentElement.setAttribute('lang',l);
  // defer until DOM ready
  window.addEventListener('DOMContentLoaded',function(){
    applyLang();
    // Kein Drucker konfiguriert? → direkt in den Drucker-Tab (zeigt "+ Drucker hinzufügen")
    fetch('/kx/printers').then(function(r){return r.json()}).then(function(d){
      if(!d.result||!d.result.length){showPanel('printers');loadPrinterTab();}
    }).catch(function(){});
  });
})();

// ── Panel nav ──
function showPanel(id){
  document.querySelectorAll('.panel').forEach(p=>p.classList.remove('active'));
  document.getElementById('panel-'+id).classList.add('active');
  document.querySelectorAll('.nav-btn,.bnav-btn').forEach(b=>b.classList.remove('active'));
  var nb=document.getElementById('nb-'+id);if(nb)nb.classList.add('active');
  var bnb=document.getElementById('bnb-'+id);if(bnb)bnb.classList.add('active');
  currentPanel=id;
}

// ── Console log ──
var consoleLogs=[];
var logAutoScroll=true;
var logBadgeCount=0;
var logDirFilter='all';   // 'all'|'rx'|'tx'
var logTopicFilter='';    // '' = no topic filter

function clog(msg,cls){
  cls=cls||'msg-info';
  var ts=new Date().toLocaleTimeString('de',{hour:'2-digit',minute:'2-digit',second:'2-digit'});
  _appendLog({ts:ts,lvl:'',name:'ui',msg:msg},cls);
}
function _lvlCls(lvl){
  if(lvl==='ERROR'||lvl==='CRITICAL')return'msg-err';
  if(lvl==='WARNING')return'msg-warn';
  if(lvl==='DEBUG')return'msg-info';
  return'msg-ok';
}
function _appendLog(entry,forceCls){
  var cls=forceCls||_lvlCls(entry.lvl);
  var label=entry.name?'['+entry.name+'] ':'';
  consoleLogs.push({ts:entry.ts,msg:label+entry.msg,cls:cls});
  if(consoleLogs.length>500)consoleLogs.shift();
  // Badge wenn Tab nicht aktiv und Fehler/Warnungen
  if(currentPanel!=='console'&&(cls==='msg-err'||cls==='msg-warn')){
    logBadgeCount++;
    var bc=logBadgeCount>99?'99+':logBadgeCount;
    ['log-badge','log-badge-bot'].forEach(function(id){var b=document.getElementById(id);if(b){b.style.display='inline';b.textContent=bc;}});
  }
  renderLog();
}
function setLogDir(dir){
  logDirFilter=dir;
  document.querySelectorAll('.log-dir-btn').forEach(function(b){
    b.style.background=b.id==='logdir-'+dir?'var(--accent)':'var(--raised)';
    b.style.color=b.id==='logdir-'+dir?'#fff':'var(--txt2)';
  });
  renderLog();
}
function setLogTopic(topic){
  var inp=document.getElementById('log-filter');
  var active=inp.value===topic;
  inp.value=active?'':topic;
  document.querySelectorAll('.log-topic-btn').forEach(function(b){
    var on=!active&&b.getAttribute('data-topic')===topic;
    b.style.background=on?'var(--accent)':'var(--raised)';
    b.style.color=on?'#fff':'var(--txt2)';
  });
  renderLog();
}
function renderLog(){
  var el=document.getElementById('console-log');
  if(!el)return;
  var filter=(document.getElementById('log-filter')||{}).value||'';
  var fl=filter.toLowerCase();
  var rows=consoleLogs.filter(function(l){
    var m=l.msg;
    if(logDirFilter==='rx'&&!/ RX[ (]/.test(m))return false;
    if(logDirFilter==='tx'&&!/ TX[ (]/.test(m))return false;
    if(fl&&!m.toLowerCase().includes(fl))return false;
    return true;
  });
  var savedScroll=logAutoScroll?null:el.scrollTop;
  el.innerHTML=rows.map(l=>`<div><span class="ts">${l.ts}</span><span class="${l.cls}">${escHtml(l.msg)}</span></div>`).join('');
  if(logAutoScroll)el.scrollTop=el.scrollHeight;
  else if(savedScroll!==null)el.scrollTop=savedScroll;
}
function onLogScroll(){
  var el=document.getElementById('console-log');
  if(!el)return;
  var atBottom=el.scrollHeight-el.scrollTop-el.clientHeight<30;
  if(!atBottom&&logAutoScroll){setAutoScroll(false);}
}
function toggleAutoScroll(){
  setAutoScroll(!logAutoScroll);
  if(logAutoScroll){var el=document.getElementById('console-log');if(el)el.scrollTop=el.scrollHeight;}
}
function setAutoScroll(on){
  logAutoScroll=on;
  var btn=document.getElementById('btn-autoscroll');
  if(btn){btn.style.background=on?'var(--accent)':'var(--raised)';btn.style.color=on?'#fff':'var(--txt2)';}
}
function clearLogBadge(){
  logBadgeCount=0;
  ['log-badge','log-badge-bot'].forEach(function(id){var b=document.getElementById(id);if(b)b.style.display='none';});
}
function escHtml(s){return s.replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');}
// SSE server-log stream
(function(){
  function connect(){
    var es=new EventSource('/api/log/stream');
    es.onmessage=function(e){try{_appendLog(JSON.parse(e.data));}catch(_){}};
    es.onerror=function(){es.close();setTimeout(connect,3000);};
  }
  window.addEventListener('DOMContentLoaded',connect);
})();

// ── Helpers ──
function fmtTime(s){if(!s||s<0)return'–';var m=Math.floor(s/60),h=Math.floor(m/60);m%=60;return h>0?h+'h '+m+'m':m+'m'}
function fmtHmsFromSec(total){
  total=Math.max(0,parseInt(total||0,10));
  var h=Math.floor(total/3600);
  var mm=Math.floor((total%3600)/60);
  var ss=total%60;
  return h+':'+String(mm).padStart(2,'0')+':'+String(ss).padStart(2,'0');
}
function post(url,body){return fetch(_apiUrl(url),{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)})}
function clamp(v,lo,hi){return Math.min(hi,Math.max(lo,v))}

// ── Apply state to DOM ──
function applyState(){
  var s=S;
  _syncAceDryPresetsFromServer(s.ace_dry_presets);
  // connection error banner – nur wenn überhaupt ein Drucker konfiguriert ist
  var banner=document.getElementById('conn-error-banner');
  if(banner){if(s.connection_error&&_printers.length>0){banner.textContent='⚠ '+(T.lbl_conn_error||'Connection error:')+' '+s.connection_error;banner.style.display='block';}else{banner.style.display='none';}}
  var frb=document.getElementById('file-ready-banner');
  if(frb){
    if(s.file_ready&&s.print_state==='standby'){
      document.getElementById('file-ready-name').textContent=s.file_ready;
      frb.style.display='flex';
    }else{frb.style.display='none';}
  }
  // skip-button (mid-print) – nur sichtbar wenn aktuell gedruckt wird
  var skipBtn=document.getElementById('d-btn-skip');
  if(skipBtn){
    var printing=(s.print_state==='printing'||s.print_state==='paused');
    skipBtn.style.display=printing?'':'none';
  }

  // header
  var b=document.getElementById('h-badge');
  b.className='hbadge '+s.print_state;
  document.getElementById('h-state').textContent=T['kobra_'+s.kobra_state]||s.kobra_state||T.header_status_standby;
  var _pn=_printers.length===0?'–':((_activePrinter&&_activePrinter.name)||s.printer_name);
  var _el=document.getElementById('h-pname');if(_el)_el.textContent=_pn;
  var _el2=document.getElementById('h-pname-single');if(_el2)_el2.textContent=_pn;
  var hv=document.getElementById('h-version');if(hv&&s.version)hv.textContent='v'+s.version;


  // temps
  var nt=document.getElementById('d-nt');if(nt)nt.textContent=s.nozzle_temp.toFixed(1);
  var ntt=document.getElementById('d-nt-t');if(ntt)ntt.textContent=s.nozzle_target.toFixed(0);
  var bt=document.getElementById('d-bt');if(bt)bt.textContent=s.bed_temp.toFixed(1);
  var btt=document.getElementById('d-bt-t');if(btt)btt.textContent=s.bed_target.toFixed(0);

  // temp bars (dashboard)
  var nb=document.getElementById('d-ntbar');if(nb)nb.style.width=clamp(s.nozzle_temp/300*100,0,100)+'%';
  var bb=document.getElementById('d-btbar');if(bb)bb.style.width=clamp(s.bed_temp/120*100,0,100)+'%';

  // progress
  var pct=Math.round(s.progress*100);
  var dpct=document.getElementById('d-pct');if(dpct)dpct.textContent=pct;
  var dpbar=document.getElementById('d-pbar');if(dpbar)dpbar.style.width=pct+'%';

  var layers=s.curr_layer&&s.total_layers?'L '+s.curr_layer+' / '+s.total_layers:'–';
  var dlayers=document.getElementById('d-layers');if(dlayers)dlayers.textContent=layers;

  var delapsed=document.getElementById('d-elapsed');if(delapsed)delapsed.textContent=fmtTime(s.print_duration);
  var dremain=document.getElementById('d-remain');if(dremain)dremain.textContent=s.remain_time>0?fmtTime(s.remain_time):'–';
  var dslrow=document.getElementById('d-slicer-row');
  var dsltime=document.getElementById('d-slicer-time');
  if(dslrow&&dsltime){
    if(s.slicer_time>0){dslrow.style.display='';dsltime.textContent=fmtTime(s.slicer_time);}
    else{dslrow.style.display='none';}
  }

  var fn=s.filename||'–';
  var dfname=document.getElementById('d-fname');if(dfname){dfname.textContent=fn;dfname.title=fn};
  var pfname=document.getElementById('p-fname');if(pfname){pfname.textContent=fn;pfname.title=fn};
  var cfo=document.getElementById('cam-fname');if(cfo)cfo.textContent=fn!=='–'?fn:'';

  // thumbnail
  var thumb=document.getElementById('d-thumbnail');
  if(thumb){
    if(s.thumbnail){
      thumb.src='data:image/png;base64,'+s.thumbnail;
      thumb.style.display='block';
    } else {
      thumb.style.display='none';
      thumb.src='';
    }
  }

  // light/fan sync
  document.getElementById('d-light-toggle').checked=s.light_on;
  var dfan=document.getElementById('d-fan');if(dfan)dfan.value=s.fan_speed;
  var dfanval=document.getElementById('d-fan-val');if(dfanval)dfanval.textContent=s.fan_speed;

  // speed mode buttons
  var spdWidths={1:25,2:55,3:90};
  [1,2,3].forEach(function(m){
    var b=document.getElementById('d-spd-'+m);
    if(b) b.classList.toggle('spd-active', s.print_speed_mode===m);
  });
  var spdBar=document.getElementById('d-spd-bar');
  if(spdBar) spdBar.style.width=(spdWidths[s.print_speed_mode]||55)+'%';

  var amsTitle=document.getElementById('d-card-ams');
  if(amsTitle){
    var baseTitle=T.card_ams||'Filament';
    var modeMap={toolhead:'Toolhead',ace_direct:'ACE Direct',ace_hub:'ACE Hub'};
    var modeTxt=modeMap[s.filament_mode]||'';
    amsTitle.textContent=modeTxt?(baseTitle+' - '+modeTxt):baseTitle;
  }

  ensureAceDryCards();
  var dry=s.ace_drying||{status:0,target_temp:0,duration:0,remain_time:0,humidity:null,current_temp:null,units:[]};
  var units=(dry.units||[]);
  var unitMap={};
  units.forEach(function(u){var id=Number(u.id);if(id>=0&&id<=3)unitMap[id]=u;});
  var aceMode=s.filament_mode==='ace_direct'||s.filament_mode==='ace_hub';
  var detected=(s.ace_units||[]).filter(function(id){return id>=0&&id<=3;});
  if(!detected.length){
    Object.keys(unitMap).forEach(function(k){detected.push(Number(k));});
  }
  if(!detected.length){
    (s.ams_slots||[]).forEach(function(sl){var id=Number(sl.box_id);if(id>=0&&id<=3&&detected.indexOf(id)<0)detected.push(id);});
  }
  detected.sort(function(a,b){return a-b;});
  var aceWrap=document.getElementById('d-ace-dry-wrap');
  if(aceWrap)aceWrap.style.display=(aceMode&&detected.length)?'contents':'none';
  for(var i=0;i<4;i++){
    var card=document.getElementById('d-ace-dry-card-'+i);
    if(!card)continue;
    var show=aceMode&&detected.indexOf(i)>=0;
    card.style.display=show?'':'none';
    if(!show)continue;
    var ud=unitMap[i]||dry;
    var refillToggle=document.getElementById('ace-auto-refill-toggle-'+i);
    var autoFeedMap=s.ace_auto_feed||{};
    if(refillToggle&&!_aceAutoFeedPending[i]){
      var afVal=autoFeedMap.hasOwnProperty(String(i))?Number(autoFeedMap[String(i)]):(_aceAutoRefillGet(i)?1:0);
      refillToggle.checked=afVal===1;
    }
    var dryToggle=document.getElementById('ace-dry-enable-toggle-'+i);
    if(dryToggle)dryToggle.checked=Number(ud.status||0)>0;
    var hh=document.getElementById('d-ace-dry-humidity-'+i);
    if(hh){
      var hv=(ud.humidity===null||ud.humidity===undefined||ud.humidity==='')?null:Number(ud.humidity);
      hh.textContent=(hv===null||Number.isNaN(hv))?'-':(Math.round(hv)+'%');
    }
    var ht=document.getElementById('d-ace-dry-current-temp-'+i);
    if(ht){
      var ct=(ud.current_temp===null||ud.current_temp===undefined||ud.current_temp==='')?null:Number(ud.current_temp);
      ht.textContent=(ct===null||Number.isNaN(ct))?'-':(ct.toFixed(1)+'°C');
    }
    var prof=_aceDryProfileGet(i);
    var useSec=(Number(ud.status||0)>0&&Number(ud.remain_time)>0)
      ?Number(ud.remain_time||0)*60
      :prof.duration_sec;
    var showTemp=(Number(ud.status||0)>0&&Number(ud.target_temp)>0)?Number(ud.target_temp):prof.temp;
    var dryTempEl=document.getElementById('d-ace-dry-target-'+i);
    if(dryTempEl)dryTempEl.textContent=showTemp+'°C';
    var dryTimeEl=document.getElementById('d-ace-dry-time-'+i);
    if(dryTimeEl)dryTimeEl.textContent=fmtHmsFromSec(useSec);
  }

  // AMS
  if(s.ams_slots&&s.ams_slots.length){
    window._amsSlots=s.ams_slots;
    // Group by box_id (-1=Toolhead, 0=ACE 1, 1=ACE 2, ...)
    var boxMap={};
    s.ams_slots.forEach(function(slot,i){
      var bid=slot.box_id!=null?slot.box_id:-1;
      if(!boxMap[bid])boxMap[bid]=[];
      boxMap[bid].push({slot:slot,arrIdx:i});
    });
    var boxIds=Object.keys(boxMap).map(Number).sort(function(a,b){return a-b});
    var acePresent=boxIds.some(function(b){return b>=0;});
    var html='';
    boxIds.forEach(function(bid){
      var entries=boxMap[bid];
      var label=bid===-1
        ?(acePresent?'Toolhead (Slots 1–3)':'Toolhead')
        :('ACE '+(bid+1));
      html+='<div class="ams-box-group">'
        +'<div class="ams-box-label">'+label+'</div>'
        +'<div class="ams-box-slots">';
      entries.forEach(function(e){
        var slot=e.slot;var i=e.arrIdx;
        var empty=slot.status!==5;
        var rgb=empty?[80,80,80]:(Array.isArray(slot.color)?slot.color:[128,128,128]);
        var col='rgb('+rgb[0]+','+rgb[1]+','+rgb[2]+')';
        var globalIdx=slot.global_index!=null?slot.global_index:i;
        var active=slot.status===1||slot.active;
        var loaded=(s.ams_loaded_slot!=null&&s.ams_loaded_slot>=0&&globalIdx===s.ams_loaded_slot);
        var activity=(slot.activity||'');
        var pct=empty?T.ams_empty:(slot.consumables_percent!=null?slot.consumables_percent+'%':'–');
        var slotLabel='Slot '+(globalIdx+1);
        html+='<div class="ams-slot'+(active?' active':'')+(loaded?' loaded':'')+(activity?' '+activity:'')+(empty?' empty':'')
          +'" style="--slot-color:'+col+';opacity:'+(empty?0.4:1)+';cursor:pointer" onclick="openSlotEdit('+i+')">'
          +'<div class="slot-circle" style="background:'+col+'"></div>'
          +'<div class="slot-material">'+(empty?'–':(slot.type||slot.material_type||'–'))+'</div>'
          +'<div class="slot-label">'+slotLabel+'</div>'
          +'<div class="slot-label" style="font-size:10px;color:var(--txt2)">'+pct+'</div>'
          +'<div style="font-size:9px;color:var(--txt2);margin-top:2px">✏</div>'
          +'</div>';
      });
      if(bid===-1&&acePresent){
        html+='<div class="ams-slot ams-slot-bridge" aria-label="Slot 4 connected to ACE">'
          +'<div class="bridge-chip">ACE</div>'
          +'</div>';
      }
      html+='</div></div>';
    });
    document.getElementById('ams-slots').innerHTML=html;
  }

  // camera overlay
  var co=document.getElementById('cam-overlay');
  if(co)co.style.display=(s.print_state==='printing'&&camOn)?'block':'none';

  // auto-start camera during print
  if(s.print_state==='printing'&&!camOn&&s.camera_url){
    camStart();
  }

  updateConnBtn();
}

function updateConnBtn(){
  var btn=document.getElementById('conn-btn');
  if(!btn)return;
  var offline=S.kobra_state==='offline';
  if(offline){
    btn.className='conn-btn disconnected';
    btn.textContent=T.btn_connect||'⚡ Verbinden';
  } else {
    btn.className='conn-btn connected';
    btn.textContent=T.btn_disconnect||'✕ Trennen';
  }
}

function toggleConnection(){
  var btn=document.getElementById('conn-btn');
  var offline=S.kobra_state==='offline';
  btn.disabled=true;
  btn.textContent='…';
  var url=offline?'/api/connect':'/api/disconnect';
  post(url,{}).then(function(r){return r.json()}).then(function(r){
    btn.disabled=false;
    if(r.error)addLog('Error: '+r.error);
  }).catch(function(){btn.disabled=false;});
}

// ── Temp history + chart ──
function updateHistory(){
  tempHistory.n.push(S.nozzle_temp);
  tempHistory.b.push(S.bed_temp);
  if(tempHistory.n.length>60)tempHistory.n.shift();
  if(tempHistory.b.length>60)tempHistory.b.shift();
  drawChart('d-chart',tempHistory,[{data:tempHistory.n,color:'#00c8ff',max:300},{data:tempHistory.b,color:'#ff6b35',max:120}]);
}
function drawChart(id,_,series){
  var canvas=document.getElementById(id);if(!canvas)return;
  var ctx=canvas.getContext('2d');
  var W=canvas.offsetWidth*window.devicePixelRatio||canvas.width;
  var H=canvas.offsetHeight*window.devicePixelRatio||canvas.height;
  canvas.width=W;canvas.height=H;
  ctx.clearRect(0,0,W,H);
  series.forEach(function(s){
    var data=s.data;if(!data.length)return;
    var max=s.max;
    ctx.beginPath();ctx.strokeStyle=s.color;ctx.lineWidth=2;ctx.lineJoin='round';
    data.forEach(function(v,i){
      var x=i/(Math.max(data.length-1,1))*(W-4)+2;
      var y=H-4-(v/max)*(H-8);
      if(i===0)ctx.moveTo(x,y);else ctx.lineTo(x,y);
    });
    ctx.stroke();
  });
}

// ── Settings Modal ──
var _updateTag='';
var _updateUrl='';
function openSettings(){
  // Titel mit aktivem Drucker-Namen aktualisieren
  var pname=_activePrinter&&_activePrinter.name?_activePrinter.name:null;
  var title=document.getElementById('modal-title-settings');
  if(title)title.textContent=T.settings_title+(pname?' – '+pname:'');
  fetch(_apiUrl('/api/settings')).then(function(r){return r.json()}).then(function(d){
    document.getElementById('s-printer-name').value=d.printer_name||'';
    document.getElementById('s-printer-ip').value=d.printer_ip||'';
    document.getElementById('s-mqtt-port').value=d.mqtt_port||9883;
    document.getElementById('s-username').value=d.username||'';
    document.getElementById('s-password').value=d.password||'';
    document.getElementById('s-device-id').value=d.device_id||'';
    document.getElementById('s-mode-id').value=d.mode_id||'';
    document.getElementById('s-default-slot').value=d.default_ams_slot||'auto';
    document.getElementById('s-auto-leveling').checked=(d.auto_leveling===undefined?true:!!d.auto_leveling);
  });
  var v=localStorage.getItem('pollInterval')||'2000';
  document.querySelectorAll('.poll-btn').forEach(function(b){b.classList.remove('active')});
  var pb=document.getElementById('poll-'+Math.round(parseInt(v)/1000));
  if(pb)pb.classList.add('active');
  document.getElementById('s-version-label').textContent='v'+('__VERSION__'||'?');
  document.getElementById('update-status').textContent='';
  document.getElementById('btn-update-apply').style.display='none';
  var cl=document.getElementById('update-changelog');if(cl)cl.style.display='none';
  _updateTag='';_updateUrl='';
  document.getElementById('settings-modal').classList.add('open');
}
function closeSettings(){
  document.getElementById('settings-modal').classList.remove('open');
}

// ── AMS Slot Edit ──
var _slotEditIndex=-1;
var _slotEditLoaded=false;
var _MAT_PRESETS=['PLA','PETG','ABS','ASA','TPU','PA','PC','HIPS'];
function updateSlotEditFeedButton(){
  var btn=document.getElementById('btn-slot-edit-feed');
  if(!btn)return;
  if(_slotEditIndex<0){
    btn.style.display='none';
    return;
  }
  btn.style.display='';
  btn.textContent=_slotEditLoaded?(T.slot_edit_unload||'⬆ Unload'):(T.slot_edit_load||'⬇ Load');
}
function openSlotEdit(i){
  var slot=(window._amsSlots||[])[i]||{};
  var globalIdx=slot.global_index!=null?slot.global_index:(slot.index!=null?slot.index:i);
  _slotEditIndex=globalIdx;
  _slotEditLoaded=(S.ams_loaded_slot!=null&&S.ams_loaded_slot===globalIdx);
  document.getElementById('slot-edit-title').textContent=T.slot_edit_title+' '+(globalIdx+1);
  var rgb=Array.isArray(slot.color)?slot.color:[128,128,128];
  var hex='#'+rgb.map(function(v){return('0'+Math.min(255,v).toString(16)).slice(-2)}).join('');
  var ci=document.getElementById('slot-edit-color');
  ci.value=hex;
  document.getElementById('slot-edit-preview').style.background=hex;
  var mat=(slot.type||'PLA').toUpperCase();
  document.getElementById('slot-edit-mat').value=mat;
  var btns=document.getElementById('slot-mat-btns');
  btns.innerHTML=_MAT_PRESETS.map(function(m){
    return '<button class="mat-preset-btn" data-mat="'+m+'" onclick="selectMatPreset(\''+m+'\')" '
      +'style="padding:4px 10px;border-radius:6px;border:1px solid var(--border);cursor:pointer;font-size:12px;'
      +(m===mat?'background:var(--accent);color:#fff':'background:var(--raised);color:var(--txt2)')+'">'+m+'</button>';
  }).join('');
  updateSlotEditFeedButton();
  document.getElementById('slot-edit-modal').classList.add('open');
}
function closeSlotEdit(){
  _slotEditIndex=-1;
  document.getElementById('slot-edit-modal').classList.remove('open');
}
function slotEditFeed(){
  if(_slotEditIndex<0)return;
  var type=_slotEditLoaded?2:1;
  amsFeed(type,_slotEditIndex)
    .then(function(){
      _slotEditLoaded=!_slotEditLoaded;
      updateSlotEditFeedButton();
      poll();
    })
    .catch(function(){});
}
function startReadyFile(){
  var btn=document.getElementById('file-ready-btn');
  if(btn){btn.disabled=true;btn.textContent='…';}
  post('/printer/print/start',{filename:S.file_ready})
    .then(function(r){return r.json();})
    .then(function(r){
      document.getElementById('file-ready-banner').style.display='none';
      if(btn){btn.disabled=false;setText('file-ready-btn',T.file_ready_btn);}
    })
    .catch(function(e){
      clog((T.log_error||'Error:')+' '+e,'msg-err');
      if(btn){btn.disabled=false;setText('file-ready-btn',T.file_ready_btn);}
    });
}
function cancelReadyFile(){
  post('/api/file_ready/clear',{})
    .then(function(){document.getElementById('file-ready-banner').style.display='none';});
}
function selectMatPreset(m){
  document.getElementById('slot-edit-mat').value=m;
  highlightMatBtn(m);
}
function highlightMatBtn(val){
  document.querySelectorAll('.mat-preset-btn').forEach(function(b){
    var on=b.getAttribute('data-mat')===val.toUpperCase();
    b.style.background=on?'var(--accent)':'var(--raised)';
    b.style.color=on?'#fff':'var(--txt2)';
  });
}
function hexToRgb(hex){
  var r=parseInt(hex.slice(1,3),16),g=parseInt(hex.slice(3,5),16),b=parseInt(hex.slice(5,7),16);
  return[r,g,b];
}
function saveSlotEdit(){
  var hex=document.getElementById('slot-edit-color').value;
  var mat=document.getElementById('slot-edit-mat').value.trim().toUpperCase()||'PLA';
  var color=hexToRgb(hex);
  post('/api/ams/set_slot',{index:_slotEditIndex,type:mat,color:color})
    .then(function(r){return r.json();})
    .then(function(r){
      closeSlotEdit();
      clog((T.slot_edit_ok||'AMS Slot')+' '+(_slotEditIndex+1)+': '+mat+' '+hex,'msg-ok');
    })
    .catch(function(e){clog('Fehler: '+e,'msg-err');});
}
document.addEventListener('DOMContentLoaded',function(){
  document.getElementById('s-printer-ip').addEventListener('input',function(){
    var hint=document.getElementById('lbl-ip-hint');
    if(this.value.includes(':')){hint.textContent=T.hint_ip_no_port;hint.style.display='block';}
    else{hint.style.display='none';}
  });
});
function setPoll(ms){
  document.querySelectorAll('.poll-btn').forEach(function(b){b.classList.remove('active')});
  var id='poll-'+Math.round(ms/1000);
  var pb=document.getElementById(id);if(pb)pb.classList.add('active');
  localStorage.setItem('pollInterval',ms);
  clearInterval(pollTimer);
  pollTimer=setInterval(poll,ms);
}
function saveSettings(){
  var btn=document.getElementById('btn-save-settings');
  btn.disabled=true;btn.textContent='…';
  post('/api/settings',{
    printer_name:     document.getElementById('s-printer-name').value,
    printer_ip:       document.getElementById('s-printer-ip').value,
    mqtt_port:        parseInt(document.getElementById('s-mqtt-port').value)||9883,
    username:         document.getElementById('s-username').value,
    password:         document.getElementById('s-password').value,
    device_id:        document.getElementById('s-device-id').value,
    mode_id:          document.getElementById('s-mode-id').value,
    default_ams_slot: document.getElementById('s-default-slot').value,
    auto_leveling:    document.getElementById('s-auto-leveling').checked?1:0,
  }).then(function(){
    btn.textContent=T.update_restarting;
    setTimeout(function(){
      btn.disabled=false;
      setText('btn-save-settings',T.settings_save);
      closeSettings();
      poll();
    },4000);
  }).catch(function(e){
    btn.disabled=false;setText('btn-save-settings',T.settings_save);
    clog('Settings-Fehler: '+e,'msg-err');
  });
}
function checkUpdate(){
  var sb=document.getElementById('update-status');
  sb.textContent=T.update_checking;
  document.getElementById('btn-update-apply').style.display='none';
  _updateTag='';_updateUrl='';
  fetch(_apiUrl('/api/update/check')).then(function(r){return r.json()}).then(function(d){
    if(d.error){sb.textContent=T.update_error+': '+d.error;return;}
    var cl=document.getElementById('update-changelog');
    if(d.changelog&&d.changelog.trim()){cl.textContent=d.changelog;cl.style.display='block';}
    else{cl.style.display='none';}
    if(d.update_available){
      sb.textContent='v'+d.latest+' '+T.update_available;
      sb.style.color='var(--ok)';
      _updateTag=d.tag;_updateUrl=d.download_url;
      document.getElementById('btn-update-apply').style.display='inline-block';
    } else {
      sb.textContent=T.update_none;
      sb.style.color='var(--txt2)';
    }
  }).catch(function(e){sb.textContent=T.update_error+': '+e;});
}
function applyUpdate(){
  if(!_updateUrl)return;
  var sb=document.getElementById('update-status');
  var btn=document.getElementById('btn-update-apply');
  btn.disabled=true;sb.textContent=T.update_applying;
  post('/api/update/apply',{download_url:_updateUrl,tag:_updateTag}).then(function(){
    sb.textContent=T.update_restarting;
    closeSettings();
    setTimeout(function(){poll();},5000);
  }).catch(function(e){
    btn.disabled=false;sb.textContent=T.update_error+': '+e;
  });
}

// ── Poll ──
async function poll(){
  try{
    var r=await fetch(_apiUrl('/api/state'));
    if(!r.ok)return;
    var d=await r.json();
    Object.assign(S,d);
    applyState();
    updateHistory();
  }catch(e){clog(T.log_poll_error+' '+e,'msg-err')}
}
var pollTimer;
(function(){
  var ms=parseInt(localStorage.getItem('pollInterval')||'2000');
  initPrinters();
  poll();pollTimer=setInterval(poll,ms);
})();

// ── Print actions ──
function printAction(a){
  post('/printer/print/'+a,{}).then(function(){clog('Druck: '+a,'msg-ok');poll()})
    .catch(function(e){clog('Fehler: '+e,'msg-err')});
}
function confirmCancel(){if(confirm('Druck wirklich abbrechen?'))printAction('cancel')}

// ── Axis motion ──
// axis codes: 0=X, 1=Y, 2=Z
// move_type 1=relative, distance positive/negative
function getStep(){return currentStep}
function setStep(btn,v){
  currentStep=v;
  document.querySelectorAll('.step-btn').forEach(b=>b.classList.remove('active'));
  btn.classList.add('active');
  document.getElementById('step-display').textContent=v;
}
function move(axis,dir,dist){
  // axis: 0=X,1=Y,2=Z → printer axis codes: 1=X,2=Y,3=Z
  var axisMap={0:1,1:2,2:3};
  post('/api/axis',{axis:axisMap[axis],move_type:1,distance:dir*dist})
    .then(function(){clog('Achse '+(axis===0?'X':axis===1?'Y':'Z')+' '+(dir>0?'+':'')+dir*dist+'mm','msg-ok')})
    .catch(function(e){clog('Achse-Fehler: '+e,'msg-err')});
}
function homeAll(){
  post('/api/axis',{axis:5,move_type:2,distance:0})
    .then(function(){clog('Home All','msg-ok')})
    .catch(function(e){clog('Home-Fehler: '+e,'msg-err')});
}
function homeXY(){
  post('/api/axis',{axis:4,move_type:2,distance:0})
    .then(function(){clog('Home XY','msg-ok')})
    .catch(function(e){clog('Home-Fehler: '+e,'msg-err')});
}
function homeZ(){
  post('/api/axis',{axis:3,move_type:2,distance:0})
    .then(function(){clog('Home Z','msg-ok')})
    .catch(function(e){clog('Home-Fehler: '+e,'msg-err')});
}
function disableMotors(){
  post('/api/axis',{action:'turnOff'})
    .then(function(){clog('Motors Off','msg-ok')})
    .catch(function(e){clog('Motors-Fehler: '+e,'msg-err')});
}

// ── Temperature ──
function setNozzle(){
  var v=parseFloat(document.getElementById('p-nozzle-inp').value||0);
  post('/api/temperature',{nozzle:v,bed:S.bed_target})
    .then(function(){clog('Nozzle → '+v+'°C','msg-ok')})
    .catch(function(e){clog('Temp-Fehler: '+e,'msg-err')});
}
function setBed(){
  var v=parseFloat(document.getElementById('p-bed-inp').value||0);
  post('/api/temperature',{nozzle:S.nozzle_target,bed:v})
    .then(function(){clog(T.label_bed+' → '+v+'°C','msg-ok')})
    .catch(function(e){clog('Temp-Fehler: '+e,'msg-err')});
}

// ── Light ──
function setLight(){
  var on=document.getElementById('d-light-toggle').checked;
  post('/api/light',{on:on,brightness:80})
    .then(function(){clog('Licht '+(on?'an, '+br+'%':'aus'),'msg-ok')})
    .catch(function(e){clog('Licht-Fehler: '+e,'msg-err')});
}

// ── Print Speed ──
function setSpeed(mode){
  S.print_speed_mode=mode;
  [1,2,3].forEach(function(m){
    var b=document.getElementById('d-spd-'+m);
    if(b) b.classList.toggle('spd-active',m===mode);
  });
  post('/api/speed',{mode:mode})
    .catch(function(e){clog('Speed-Fehler: '+e,'msg-err')});
}

// ── Fan ──
function setFan(){
  var v=parseInt(document.getElementById('d-fan').value);
  document.getElementById('d-fan-val').textContent=v;
  post('/api/fan',{speed:v})
    .then(function(){clog('Lüfter → '+v+'%','msg-ok')})
    .catch(function(e){clog('Lüfter-Fehler: '+e,'msg-err')});
}
function quickFan(v){
  document.getElementById('d-fan').value=v;
  document.getElementById('d-fan-val').textContent=v;
  post('/api/fan',{speed:v})
    .then(function(){clog('Lüfter → '+v+'%','msg-ok')})
    .catch(function(e){clog('Lüfter-Fehler: '+e,'msg-err')});
}

// ── AMS ──
function amsFeed(type,slotIndex){
  var globalIdx;
  if(typeof slotIndex==='number'&&slotIndex>=0){
    globalIdx=slotIndex;
  }else{
    var i=parseInt(document.getElementById('ams-slot-sel').value);
    var slot=(window._amsSlots||[])[i]||{};
    globalIdx=slot.global_index!=null?slot.global_index:i;
  }
  return post('/api/ams/feed',{slot_index:globalIdx,type:type})
    .then(function(){clog((type===1?T.lbl_feed:T.lbl_unload)+' Slot '+(globalIdx+1),'msg-ok')})
    .catch(function(e){clog('AMS-Fehler: '+e,'msg-err');throw e;});
}

// ── Camera ──
function camStart(){
  var img=document.getElementById('cam-img');
  var ph=document.getElementById('cam-placeholder');
  var sp=document.getElementById('cam-spinner');
  ph.style.display='none';
  img.style.display='none';
  sp.style.display='block';
  post('/api/camera/start',{}).then(function(){
    img.onerror=function(){
      sp.style.display='none';
      img.style.display='none';
      ph.style.display='flex';
      camOn=false;
      document.getElementById('cam-toggle-btn').textContent=T.btn_cam_start||'▶ Kamera';
      clog((T.log_error||'Fehler:')+' Stream nicht verfügbar','msg-err');
    };
    img.src='/api/camera/stream?t='+Date.now();
    camOn=true;
    document.getElementById('cam-toggle-btn').textContent=T.btn_cam_stop||'◼ Kamera';
    clog((T.log_cam_start||'Kamera gestartet'),'msg-ok');
    // MJPEG liefert kein onload – Spinner nach kurzem Timeout ausblenden
    setTimeout(function(){
      sp.style.display='none';
      img.style.display='block';
    },1200);
  }).catch(function(e){
    sp.style.display='none';
    ph.style.display='flex';
    clog((T.log_error||'Fehler:')+' '+e,'msg-err');
  });
}

function camStop(){
  var img=document.getElementById('cam-img');
  post('/api/camera/stop',{}).catch(function(){});
  img.src='';
  img.style.display='none';
  document.getElementById('cam-placeholder').style.display='flex';
  camOn=false;
  document.getElementById('cam-toggle-btn').textContent=T.btn_cam_start||'▶ Kamera';
  clog((T.log_cam_stop||'Kamera gestoppt'),'msg-ok');
}

function aceDryStart(aceId){
  aceId=(typeof aceId==='number'&&aceId>=0)?aceId:0;
  var prof=_aceDryProfileGet(aceId);
  var t=parseInt(prof.temp,10);
  var d=_aceDryDurationMinFromSec(prof.duration_sec);
  t=Math.max(30,Math.min(80,t));
  d=Math.max(10,Math.min(1440,d));
  return post('/api/ace/dry',{action:'start',target_temp:t,duration:d,ace_id:aceId})
    .then(function(r){return r.json();})
    .then(function(r){
      if(r.error){throw new Error(r.error);}
      clog('ACE '+(aceId+1)+' - '+(T.ace_dry_dryer||'Dryer')+': '+(T.ace_dry_start||'start')+' ('+t+'°C, '+d+' min)','msg-ok');
      poll();
    })
    .catch(function(e){clog('ACE-Fehler: '+e,'msg-err');});
}

var _aceAutoFeedPending={};
function aceAutoRefillToggle(aceId){
  aceId=(typeof aceId==='number'&&aceId>=0)?aceId:0;
  var on=!!((document.getElementById('ace-auto-refill-toggle-'+aceId)||{}).checked);
  _aceAutoFeedPending[aceId]=true;
  fetch('/api/ace/auto_feed',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({ace_id:aceId,on:on?1:0})})
    .then(function(r){return r.json();})
    .then(function(d){
      delete _aceAutoFeedPending[aceId];
      if(d.error){clog('Auto Refill error: '+d.error,'msg-err');var t=document.getElementById('ace-auto-refill-toggle-'+aceId);if(t)t.checked=!on;return;}
      clog('ACE '+(aceId+1)+' - '+(T.ace_dry_auto_refill||'Auto Refill')+': '+(on?'ON':'OFF'),'msg-ok');
    })
    .catch(function(e){delete _aceAutoFeedPending[aceId];clog('Auto Refill error: '+e,'msg-err');var t=document.getElementById('ace-auto-refill-toggle-'+aceId);if(t)t.checked=!on;});
}

function openAceDryDialog(aceId){
  aceId=(typeof aceId==='number'&&aceId>=0)?aceId:0;
  _aceDryDialogAceId=aceId;
  _syncAceDryPresetsFromServer(S.ace_dry_presets);
  _aceDryDialogPresetOriginals=JSON.parse(JSON.stringify(ACE_DRY_PRESETS));
  aceDryDialogSyncCustomButtonNames();
  var hasStored=Object.prototype.hasOwnProperty.call(aceDryProfiles,String(aceId));
  var prof=_aceDryProfileGet(aceId);
  if(hasStored&&prof.preset&&ACE_DRY_PRESETS[prof.preset]){
    aceDryDialogPreset(prof.preset);
  }else if(hasStored){
    var sec=prof.duration_sec;
    document.getElementById('ace-dry-dialog-temp').value=prof.temp;
    document.getElementById('ace-dry-dialog-h').value=Math.floor(sec/3600);
    document.getElementById('ace-dry-dialog-m').value=Math.floor((sec%3600)/60);
    document.getElementById('ace-dry-dialog-s').value=sec%60;
    aceDryDialogHighlightPreset('');
  }else{
    aceDryDialogPreset('pla');
  }
  aceDryDialogUpdateSaveButton();
  aceDryDialogUpdateResetButton();
  var sb=document.getElementById('ace-dry-dialog-save-preset');
  if(sb){sb.disabled=false;sb.textContent=T.ace_dry_dialog_save_restart||'Save & Restart';}
  document.getElementById('ace-dry-dialog').classList.add('open');
}

function closeAceDryDialog(){
  _aceDryDialogAceId=-1;
  _aceDryDialogPresetOriginals={};
  var sb=document.getElementById('ace-dry-dialog-save-preset');
  if(sb)sb.style.display='none';
  var rb=document.getElementById('ace-dry-dialog-reset-default');
  if(rb)rb.style.display='none';
  document.getElementById('ace-dry-dialog').classList.remove('open');
}

function aceDryDialogIsCustomPreset(key){
  return /^custom_[123]$/.test(String(key||''));
}

function aceDryDialogSyncCustomButtonNames(){
  ['custom_1','custom_2','custom_3'].forEach(function(k){
    var b=document.querySelector('.ace-dry-preset-btn[data-preset="'+k+'"]');
    if(b)b.textContent=(ACE_DRY_PRESETS[k]&&ACE_DRY_PRESETS[k].name)||('Custom '+k.slice(-1));
  });
}

function aceDryDialogUpdateCustomNameUi(){
  var row=document.getElementById('ace-dry-dialog-custom-name-row');
  var input=document.getElementById('ace-dry-dialog-custom-name');
  if(!row||!input)return;
  if(!aceDryDialogIsCustomPreset(_aceDryDialogPresetKey)){
    row.style.display='none';
    return;
  }
  row.style.display='flex';
  input.value=(ACE_DRY_PRESETS[_aceDryDialogPresetKey]&&ACE_DRY_PRESETS[_aceDryDialogPresetKey].name)||'';
}

function aceDryDialogCurrentValues(){
  var t=parseInt(document.getElementById('ace-dry-dialog-temp').value||45,10);
  var h=parseInt(document.getElementById('ace-dry-dialog-h').value||0,10);
  var m=parseInt(document.getElementById('ace-dry-dialog-m').value||0,10);
  var s=parseInt(document.getElementById('ace-dry-dialog-s').value||0,10);
  t=Math.max(30,Math.min(80,t));
  h=Math.max(0,Math.min(24,h));
  m=Math.max(0,Math.min(59,m));
  s=Math.max(0,Math.min(59,s));
  var totalSec=(h*3600)+(m*60)+s;
  totalSec=Math.max(10*60,Math.min(24*3600,totalSec));
  return {temp:t,duration_sec:totalSec};
}

function aceDryDialogUpdateSaveButton(){
  var btn=document.getElementById('ace-dry-dialog-save-preset');
  if(!btn)return;
  var key=_aceDryDialogPresetKey||'';
  if(!key||!ACE_DRY_PRESETS[key]){btn.style.display='none';return;}
  var p=_aceDryDialogPresetOriginals[key]||ACE_DRY_PRESETS[key];
  var cur=aceDryDialogCurrentValues();
  var changed=(cur.temp!==Number(p.temp)||cur.duration_sec!==Number(p.duration_sec));
  if(aceDryDialogIsCustomPreset(key)){
    var nameInp=document.getElementById('ace-dry-dialog-custom-name');
    var n=((nameInp&&nameInp.value)||'').trim();
    var old=(p&&p.name?String(p.name):('Custom '+key.slice(-1))).trim();
    if((n||old)!==old)changed=true;
  }
  btn.style.display=changed?'':'none';
}

function aceDryDialogUpdateResetButton(){
  var btn=document.getElementById('ace-dry-dialog-reset-default');
  if(!btn)return;
  var key=_aceDryDialogPresetKey||'';
  var d=ACE_DRY_PRESET_DEFAULTS[key];
  if(!key||!d){btn.style.display='none';return;}
  var cur=aceDryDialogCurrentValues();
  var changed=(cur.temp!==Number(d.temp)||cur.duration_sec!==Number(d.duration_sec));
  btn.style.display=changed?'':'none';
}

function aceDryDialogInputsChanged(){
  if(aceDryDialogIsCustomPreset(_aceDryDialogPresetKey)){
    var b=document.querySelector('.ace-dry-preset-btn[data-preset="'+_aceDryDialogPresetKey+'"]');
    var i=document.getElementById('ace-dry-dialog-custom-name');
    if(b&&i){
      var t=(i.value||'').trim();
      b.textContent=t||((ACE_DRY_PRESETS[_aceDryDialogPresetKey]&&ACE_DRY_PRESETS[_aceDryDialogPresetKey].name)||('Custom '+_aceDryDialogPresetKey.slice(-1)));
    }
  }
  aceDryDialogUpdateSaveButton();
  aceDryDialogUpdateResetButton();
}

function aceDryDialogHighlightPreset(presetKey){
  _aceDryDialogPresetKey=presetKey||'';
  document.querySelectorAll('.ace-dry-preset-btn').forEach(function(btn){
    var on=(btn.getAttribute('data-preset')===presetKey);
    btn.style.background=on?'var(--accent)':'var(--raised)';
    btn.style.color=on?'#fff':'var(--txt2)';
    btn.style.borderColor=on?'var(--accent)':'var(--border)';
  });
  aceDryDialogUpdateCustomNameUi();
}

function aceDryDialogPreset(presetKey){
  var p=ACE_DRY_PRESETS[presetKey];
  if(!p)return;
  var sec=p.duration_sec;
  document.getElementById('ace-dry-dialog-temp').value=p.temp;
  document.getElementById('ace-dry-dialog-h').value=Math.floor(sec/3600);
  document.getElementById('ace-dry-dialog-m').value=Math.floor((sec%3600)/60);
  document.getElementById('ace-dry-dialog-s').value=sec%60;
  aceDryDialogHighlightPreset(presetKey);
  aceDryDialogSyncCustomButtonNames();
  aceDryDialogUpdateSaveButton();
  aceDryDialogUpdateResetButton();
}

function resetAceDryPresetToDefault(){
  var key=_aceDryDialogPresetKey||'';
  var d=ACE_DRY_PRESET_DEFAULTS[key];
  if(!key||!d)return;
  var sec=Number(d.duration_sec)||0;
  document.getElementById('ace-dry-dialog-temp').value=Number(d.temp)||45;
  document.getElementById('ace-dry-dialog-h').value=Math.floor(sec/3600);
  document.getElementById('ace-dry-dialog-m').value=Math.floor((sec%3600)/60);
  document.getElementById('ace-dry-dialog-s').value=sec%60;
  aceDryDialogInputsChanged();
}

function saveAceDryPresetAndRestart(){
  var key=_aceDryDialogPresetKey||'';
  var btn=document.getElementById('ace-dry-dialog-save-preset');
  if(!key||!ACE_DRY_PRESETS[key]||!btn)return;
  var cur=aceDryDialogCurrentValues();
  if(!ACE_DRY_PRESETS[key])ACE_DRY_PRESETS[key]={};
  ACE_DRY_PRESETS[key].temp=cur.temp;
  ACE_DRY_PRESETS[key].duration_sec=cur.duration_sec;
  if(aceDryDialogIsCustomPreset(key)){
    var nameInp=document.getElementById('ace-dry-dialog-custom-name');
    var nm=((nameInp&&nameInp.value)||'').trim();
    ACE_DRY_PRESETS[key].name=nm||('Custom '+key.slice(-1));
  }
  btn.disabled=true;
  btn.textContent='…';
  fetch(_apiUrl('/api/settings')).then(function(r){return r.json();}).then(function(d){
    d.ace_dry_presets={
      pla:{temp:ACE_DRY_PRESETS.pla.temp,duration_sec:ACE_DRY_PRESETS.pla.duration_sec},
      pla_plus:{temp:ACE_DRY_PRESETS.pla_plus.temp,duration_sec:ACE_DRY_PRESETS.pla_plus.duration_sec},
      petg:{temp:ACE_DRY_PRESETS.petg.temp,duration_sec:ACE_DRY_PRESETS.petg.duration_sec},
      tpu:{temp:ACE_DRY_PRESETS.tpu.temp,duration_sec:ACE_DRY_PRESETS.tpu.duration_sec},
      abs_asa:{temp:ACE_DRY_PRESETS.abs_asa.temp,duration_sec:ACE_DRY_PRESETS.abs_asa.duration_sec},
      pa_pc:{temp:ACE_DRY_PRESETS.pa_pc.temp,duration_sec:ACE_DRY_PRESETS.pa_pc.duration_sec},
      custom_1:{name:ACE_DRY_PRESETS.custom_1.name,temp:ACE_DRY_PRESETS.custom_1.temp,duration_sec:ACE_DRY_PRESETS.custom_1.duration_sec},
      custom_2:{name:ACE_DRY_PRESETS.custom_2.name,temp:ACE_DRY_PRESETS.custom_2.temp,duration_sec:ACE_DRY_PRESETS.custom_2.duration_sec},
      custom_3:{name:ACE_DRY_PRESETS.custom_3.name,temp:ACE_DRY_PRESETS.custom_3.temp,duration_sec:ACE_DRY_PRESETS.custom_3.duration_sec}
    };
    return post('/api/settings',d);
  }).then(function(){
    clog('ACE preset '+key+' '+(T.settings_save||'Save & Restart'),'msg-ok');
    closeAceDryDialog();
  }).catch(function(e){
    btn.disabled=false;
    btn.textContent=T.ace_dry_dialog_save_restart||'Save & Restart';
    clog('ACE-Preset Fehler: '+e,'msg-err');
  });
}

function confirmAceDryDialog(){
  if(_aceDryDialogAceId<0)return;
  var t=parseInt(document.getElementById('ace-dry-dialog-temp').value||45,10);
  var h=parseInt(document.getElementById('ace-dry-dialog-h').value||0,10);
  var m=parseInt(document.getElementById('ace-dry-dialog-m').value||0,10);
  var s=parseInt(document.getElementById('ace-dry-dialog-s').value||0,10);
  t=Math.max(30,Math.min(80,t));
  h=Math.max(0,Math.min(24,h));
  m=Math.max(0,Math.min(59,m));
  s=Math.max(0,Math.min(59,s));
  var totalSec=(h*3600)+(m*60)+s;
  totalSec=Math.max(10*60,Math.min(24*3600,totalSec));
  var preset=_aceDryDialogPresetKey||'';
  _aceDryProfileSet(_aceDryDialogAceId,t,totalSec,preset);
  closeAceDryDialog();
  applyState();
}

function aceDryToggle(aceId,on){
  if(on)return aceDryStart(aceId);
  return aceDryStop(aceId);
}

function toggleCam(){if(camOn)camStop();else camStart()}

function aceDryStop(aceId){
  aceId=(typeof aceId==='number'&&aceId>=0)?aceId:0;
  return post('/api/ace/dry',{action:'stop',ace_id:aceId})
    .then(function(r){return r.json();})
    .then(function(r){
      if(r.error){throw new Error(r.error);}
      clog('ACE '+(aceId+1)+' - '+(T.ace_dry_dryer||'Dryer')+': '+(T.ace_dry_stop||'stop'),'msg-ok');
      poll();
    })
    .catch(function(e){clog('ACE-Fehler: '+e,'msg-err');});
}

function loadStore(){
  fetch(_apiUrl('/kx/files')).then(function(r){return r.json()}).then(function(d){
    storeFiles=d.result||[];
    renderStore();
  }).catch(function(e){clog('Store-Fehler: '+e,'msg-err')});
}

function renderStore(){
  var grid=document.getElementById('store-grid');
  var empty=document.getElementById('store-empty');

  // Suche
  var q=(document.getElementById('store-search')||{value:''}).value.toLowerCase().trim();
  // Filter
  var filter=(document.getElementById('store-filter')||{value:'all'}).value;
  // Sortierung
  var sort=(document.getElementById('store-sort')||{value:'date_desc'}).value;

  var files=storeFiles.filter(function(f){
    if(q&&f.filename.toLowerCase().indexOf(q)===-1) return false;
    if(filter==='completed'&&f.last_print_status!=='completed') return false;
    if(filter==='failed'&&(f.last_print_status!=='cancelled'&&f.last_print_status!=='failed')) return false;
    if(filter==='never'&&f.last_print_status) return false;
    return true;
  });

  files.sort(function(a,b){
    if(sort==='name_asc') return a.filename.localeCompare(b.filename);
    if(sort==='duration_asc'){
      var da=a.last_print_duration||a.est_print_time_sec||0;
      var db=b.last_print_duration||b.est_print_time_sec||0;
      return da-db;
    }
    // date_desc (default)
    return (b.uploaded_at||'').localeCompare(a.uploaded_at||'');
  });

  if(!storeFiles.length){
    empty.textContent=T.store_empty;
    grid.innerHTML='';
    empty.style.display='block';
    return;
  }
  if(!files.length){
    empty.textContent=T.store_no_results;
    grid.innerHTML='';
    empty.style.display='block';
    return;
  }
  empty.style.display='none';
  grid.innerHTML=files.map(function(f){
    var thumb=f.thumbnail_b64
      ? '<img src="data:image/png;base64,'+f.thumbnail_b64+'" style="width:100%;height:130px;object-fit:cover;border-radius:6px;display:block;margin-bottom:8px">'
      : '<div style="width:100%;height:130px;background:var(--raised);border-radius:6px;display:flex;align-items:center;justify-content:center;margin-bottom:8px;font-size:32px">🖨</div>';
    var name=f.filename.length>28?f.filename.slice(0,25)+'…':f.filename;
    var date=f.uploaded_at?f.uploaded_at.replace('T',' ').slice(0,16):'';
    var est=f.est_print_time_sec?formatDur(f.est_print_time_sec):'–';
    var statusBadge='';
    var lastInfo='';
    if(f.last_print_status==='completed'){
      statusBadge='<span style="background:#2a7a3b;color:#fff;border-radius:4px;padding:1px 6px;font-size:10px;margin-left:4px">✓</span>';
      if(f.last_print_duration) lastInfo='<div style="font-size:11px;color:var(--ok);margin-bottom:2px">✓ '+formatDur(f.last_print_duration)+'</div>';
    } else if(f.last_print_status==='cancelled'||f.last_print_status==='failed'){
      statusBadge='<span style="background:#a04020;color:#fff;border-radius:4px;padding:1px 6px;font-size:10px;margin-left:4px">✗</span>';
      lastInfo='<div style="font-size:11px;color:var(--err);margin-bottom:2px">✗ '+f.last_print_status+'</div>';
    } else if(!f.last_print_status){
      lastInfo='<div style="font-size:11px;color:var(--txt2);margin-bottom:2px;opacity:.6">'+T.store_never+'</div>';
    }
    return '<div style="background:var(--raised);border:1px solid var(--border);border-radius:8px;padding:10px;display:flex;flex-direction:column">'+
      thumb+
      '<div title="'+f.filename+'" style="font-size:12px;font-weight:600;margin-bottom:4px;color:var(--txt)">'+name+statusBadge+'</div>'+
      lastInfo+
      '<div style="font-size:11px;color:var(--txt2);margin-bottom:2px">⏱ Schätzung: '+est+'</div>'+
      '<div style="font-size:11px;color:var(--txt2);margin-bottom:8px">📅 '+date+'</div>'+
      '<div style="display:flex;gap:6px;margin-top:auto">'+
        '<button onclick="storePrint(\''+f.id+'\',\''+f.filename.replace(/'/g,"\\'")+'\')" '+
          'style="flex:1;font-size:12px;padding:5px;background:var(--accent);color:#fff;border:none;border-radius:6px;cursor:pointer">'+T.store_print+'</button>'+
        '<button onclick="storeDelete(\''+f.id+'\')" '+
          'style="font-size:12px;padding:5px 8px;background:var(--raised);border:1px solid var(--border);border-radius:6px;color:var(--txt2);cursor:pointer">🗑</button>'+
      '</div>'+
    '</div>';
  }).join('');
}

function formatDur(sec){
  var h=Math.floor(sec/3600),m=Math.floor((sec%3600)/60);
  return h?h+'h '+m+'m':m+'m';
}

var _storeFileId=null;
var _storeFilename=null;
var _filamentDialogMode='store'; // 'store' oder 'banner'

var _gcodeFilaments=[];

function _setGcodeFilamentsFromFileObj(fileObj){
  try{
    if(fileObj&&Array.isArray(fileObj.gcode_filaments)){
      _gcodeFilaments=fileObj.gcode_filaments;
    }else if(fileObj&&typeof fileObj.gcode_filaments==='string'&&fileObj.gcode_filaments){
      _gcodeFilaments=JSON.parse(fileObj.gcode_filaments);
    }else{
      _gcodeFilaments=[];
    }
  }catch(e){
    _gcodeFilaments=[];
  }
}

function storePrint(fileId, filename){
  _storeFileId=fileId;
  _storeFilename=filename;
  _filamentDialogMode='store';
  // GCode-Filamente aus Store-Datei holen (für Vorschau im Dialog)
  var fileObj=storeFiles.find(function(f){return f.id===fileId;});
  _setGcodeFilamentsFromFileObj(fileObj);
  fetch(_apiUrl('/kx/filament/slots')).then(function(r){return r.json()}).then(function(d){
    openFilamentDialog(d.result||[]);
  }).catch(function(){openFilamentDialog([]);});
}

function startReadyFileWithSlots(){
  _filamentDialogMode='banner';
  _storeFilename=S.file_ready||'';
  // Banner must never reuse stale store-file context.
  _storeFileId=null;
  _gcodeFilaments=[];

  function openWithSlots(){
    fetch(_apiUrl('/kx/filament/slots')).then(function(r){return r.json()}).then(function(d){
      openFilamentDialog(d.result||[]);
    }).catch(function(){openFilamentDialog([]);});
  }

  var fileObj=(storeFiles||[]).find(function(f){return f.filename===_storeFilename;});
  if(fileObj){
    _storeFileId=fileObj.id;
    _setGcodeFilamentsFromFileObj(fileObj);
    openWithSlots();
    return;
  }

  // Fallback: refresh file list, then resolve current file by filename.
  fetch(_apiUrl('/kx/files')).then(function(r){return r.json()}).then(function(d){
    storeFiles=d.result||[];
    var refreshed=(storeFiles||[]).find(function(f){return f.filename===_storeFilename;});
    if(refreshed){
      _storeFileId=refreshed.id;
      _setGcodeFilamentsFromFileObj(refreshed);
    }
    openWithSlots();
  }).catch(function(){
    openWithSlots();
  });
}

var _amsSlots=[];
var _printObjects=[]; // [{name, skip}] für aktuell offenen Dialog
var _printObjectsSvg=''; // base64-SVG aus DB für Visualisierung

// Hilfsfunktionen für farbige Kanal/Slot-Marker (Issue #23)
function _contrastText(hex){
  // Helle Farbe → dunkler Text, dunkle Farbe → heller Text
  var c=(hex||'').replace('#','');
  if(c.length===3)c=c[0]+c[0]+c[1]+c[1]+c[2]+c[2];
  if(c.length<6)return '#fff';
  var r=parseInt(c.slice(0,2),16),g=parseInt(c.slice(2,4),16),b=parseInt(c.slice(4,6),16);
  // YIQ-Helligkeit
  var y=(r*299 + g*587 + b*114)/1000;
  return y>=140?'#111':'#fff';
}
function _normalizeMaterialKey(material){
  var key=(material||'').toUpperCase().replace(/[^A-Z0-9+]/g,'');
  // Orca often uses PLA for PLA+, while AMS may report PLA+.
  if(key==='PLA+'||key==='PLAPLUS') return 'PLA';
  return key;
}
function _materialsCompatible(a,b){
  return _normalizeMaterialKey(a)===_normalizeMaterialKey(b);
}
function _updateSlotMarker(sel){
  var opt=sel.options[sel.selectedIndex];
  var color=opt&&opt.dataset.color?opt.dataset.color:'#888';
  var slotIdx=parseInt(opt.value);
  var paintIdx=sel.dataset.paint;
  var marker=document.querySelector('.fd-slot-marker[data-for-paint="'+paintIdx+'"]');
  if(marker){
    marker.style.background=color;
    marker.style.color=_contrastText(color);
    marker.textContent=(slotIdx+1);
  }
}

function openFilamentDialog(slots){
  _amsSlots=slots
    .filter(function(s){return s.status==='loaded';})
    .sort(function(a,b){return (a.slot_index||0)-(b.slot_index||0);});
  var dlg=document.getElementById('filament-dialog');
  var title=document.getElementById('fd-title');
  var body=document.getElementById('fd-slots');
  if(title)title.textContent='▶ '+_storeFilename;
  // Objekt-Liste laden (nur Store-Modus: per File-ID; Banner-Modus hat keine ID)
  _printObjects=[];
  _printObjectsSvg='';
  var objSection=document.getElementById('fd-objects-section');
  if(objSection)objSection.style.display='none';
  if(_filamentDialogMode==='store'&&_storeFileId){
    fetch(_apiUrl('/kx/files/'+encodeURIComponent(_storeFileId)+'/objects'))
      .then(function(r){return r.json()})
      .then(function(d){
        var names=(d.result&&d.result.names)||[];
        _printObjectsSvg=(d.result&&d.result.svg_b64)||'';
        if(names.length>=2){
          _printObjects=names.map(function(n){return {name:n,skip:false};});
          renderObjectChecklist(); renderObjectSvg();
          if(objSection)objSection.style.display='block';
        }
      }).catch(function(){});
  }

  // GCode-Kanäle: bevorzugt aus _gcodeFilaments, sonst aus belegten AMS-Slots ableiten
  var channels=_gcodeFilaments.length?_gcodeFilaments:_amsSlots.map(function(s,i){
    return {slot_index:i,color_hex:s.color_hex,material:s.material};
  });

  // Default mapping strategy:
  // 1) keep order where possible (row i -> nearest compatible slot i)
  // 2) keep defaults unique while compatible slots are available
  // 3) use color proximity as tie-breaker
  function _hexToRgb(hex){
    var c=(hex||'').replace('#','');
    if(c.length===3)c=c[0]+c[0]+c[1]+c[1]+c[2]+c[2];
    if(c.length<6)return [255,255,255];
    return [parseInt(c.slice(0,2),16),parseInt(c.slice(2,4),16),parseInt(c.slice(4,6),16)];
  }
  function _colorDist(a,b){
    var ar=_hexToRgb(a), br=_hexToRgb(b);
    var dr=ar[0]-br[0], dg=ar[1]-br[1], db=ar[2]-br[2];
    return (dr*dr + dg*dg + db*db);
  }
  var defaultSlotByPaint={};
  var usedDefaultSlot={};
  channels.forEach(function(gc,i){
    var compatible=_amsSlots.filter(function(s){
      return _materialsCompatible(gc.material, s.material);
    });
    if(!compatible.length){
      defaultSlotByPaint[i]=-1;
      return;
    }

    var ranked=compatible.slice().sort(function(a,b){
      var da=Math.abs((a.slot_index||0)-i), db=Math.abs((b.slot_index||0)-i);
      if(da!==db)return da-db;
      var ca=_colorDist(gc.color_hex, a.color_hex), cb=_colorDist(gc.color_hex, b.color_hex);
      if(ca!==cb)return ca-cb;
      return (a.slot_index||0)-(b.slot_index||0);
    });

    var chosen=ranked.find(function(s){return !usedDefaultSlot[s.slot_index];}) || ranked[0];
    defaultSlotByPaint[i]=chosen?chosen.slot_index:-1;
    if(chosen) usedDefaultSlot[chosen.slot_index]=1;
  });

  if(!_amsSlots.length){
    body.innerHTML='<p style="color:var(--txt2);font-size:13px;text-align:center;padding:16px 0">Keine belegten AMS-Slots.<br>Druck trotzdem starten?</p>';
  } else {
    body.innerHTML=channels.map(function(gc,i){
      var isUsed=(gc&&gc.is_used!==false);
      // Only allow material-compatible slots.
      var compatible=_amsSlots.filter(function(s){
        return _materialsCompatible(gc.material, s.material);
      });

      var defaultSlotIndex=(defaultSlotByPaint.hasOwnProperty(i)?defaultSlotByPaint[i]:-1);
      var defaultSlot=compatible.find(function(s){return s.slot_index===defaultSlotIndex;})||null;
      var opts=compatible.map(function(s){
        var sel=(defaultSlot&&s.slot_index===defaultSlot.slot_index)?'selected':'';
        return '<option value="'+s.slot_index+'" data-color="'+s.color_hex+'" data-material="'+s.material+'" '+sel+'>'+
          '● Slot '+(s.slot_index+1)+' · '+s.material+'</option>';
      }).join('');
      if(!compatible.length){
        opts='<option value="-1" data-color="#888888" data-material="" selected>⚠ No matching material</option>';
      }
      // Kanal-Box (links): farbige Box mit Nummer + auto Kontrast-Text
      var txt=_contrastText(gc.color_hex);
      var slotColor=defaultSlot?defaultSlot.color_hex:'#888';
      var slotTxt=_contrastText(slotColor);
      var usedBadge=isUsed
        ? '<span style="font-size:10px;color:var(--ok);font-weight:700;min-width:32px">USED</span>'
        : '<span style="font-size:10px;color:var(--txt2);font-weight:700;min-width:32px;opacity:.75">USED</span>';
      return '<div style="display:flex;align-items:center;gap:8px;padding:8px;border-radius:6px;background:var(--raised);border:1px solid var(--border)">'+
        '<span style="display:inline-flex;align-items:center;justify-content:center;width:28px;height:28px;border-radius:6px;background:'+gc.color_hex+';color:'+txt+';font-weight:700;font-size:13px;border:1px solid var(--border);flex-shrink:0">'+(i+1)+'</span>'+
        '<span style="font-size:11px;color:var(--txt2);min-width:36px">'+gc.material+'</span>'+
        usedBadge+
        '<span style="font-size:16px;color:var(--txt2)">→</span>'+
        '<span class="fd-slot-marker" data-for-paint="'+i+'" style="display:inline-flex;align-items:center;justify-content:center;width:24px;height:24px;border-radius:5px;background:'+slotColor+';color:'+slotTxt+';font-weight:700;font-size:12px;border:1px solid var(--border);flex-shrink:0">'+(defaultSlot?defaultSlot.slot_index+1:'?')+'</span>'+
        '<select data-paint="'+i+'" data-paint-color="'+gc.color_hex+'" data-is-used="'+(isUsed?'1':'0')+'" data-has-compatible="'+(compatible.length?'1':'0')+'" '+(compatible.length?'':'disabled')+' onchange="_updateSlotMarker(this)" style="flex:1;min-width:0;padding:4px 6px;border-radius:6px;border:1px solid var(--border);background:var(--raised);color:var(--txt);font-size:12px">'+
        opts+'</select>'+
      '</div>';
    }).join('');
  }
  if(dlg)dlg.classList.add('open');
}

function closeFilamentDialog(){
  var dlg=document.getElementById('filament-dialog');
  if(dlg)dlg.classList.remove('open');
}

function confirmFilamentPrint(){
  var selects=document.querySelectorAll('#fd-slots select');
  var assignments=[];
  var missingCompatible=0;
  selects.forEach(function(sel){
    var paintIdx=parseInt(sel.dataset.paint);
    var paintColor=sel.dataset.paintColor;
    var isUsed=(sel.dataset.isUsed==='1');
    var hasCompatible=(sel.dataset.hasCompatible==='1');
    var opt=sel.options[sel.selectedIndex];
    var amsIdx=parseInt(opt&&opt.value);
    if(!hasCompatible || Number.isNaN(amsIdx) || amsIdx < 0){
      if(isUsed) missingCompatible += 1;
      amsIdx = -1;
    }
    var amsSlot=_amsSlots.find(function(s){return s.slot_index===amsIdx;})||{};
    // Farbe als [R,G,B,255]
    function hexToRgba(h){
      var c=h.replace('#','');
      if(c.length===3)c=c[0]+c[0]+c[1]+c[1]+c[2]+c[2];
      return [parseInt(c.slice(0,2),16),parseInt(c.slice(2,4),16),parseInt(c.slice(4,6),16),255];
    }
    assignments.push({
      paint_index:  paintIdx,
      is_used:      isUsed,
      slot_index:   amsIdx,
      material:     opt.dataset.material||'PLA',
      paint_color:  hexToRgba(paintColor||'#ffffff'),
      ams_color:    hexToRgba(amsSlot.color_hex||'#ffffff'),
    });
  });
  if(missingCompatible>0){
    clog('Cannot start print: '+missingCompatible+' used paint(s) have no matching material slot','msg-err');
    return;
  }
  // Pre-Print Skip: Namen der abgehakten Objekte sammeln
  var excludedObjects=_printObjects.filter(function(o){return o.skip;}).map(function(o){return o.name;});
  closeFilamentDialog();
  if(_filamentDialogMode==='banner'){
    // Banner-Modus: normaler print/start mit Slot-Override
    var btn=document.getElementById('file-ready-btn');
    if(btn){btn.disabled=true;btn.textContent='…';}
    post('/printer/print/start',{filename:S.file_ready,filament_assignments:assignments,excluded_objects:excludedObjects})
      .then(function(r){return r.json();})
      .then(function(){
        document.getElementById('file-ready-banner').style.display='none';
        if(btn){btn.disabled=false;setText('file-ready-btn',T.file_ready_btn);}
      })
      .catch(function(e){
        clog((T.log_error||'Error:')+' '+e,'msg-err');
        if(btn){btn.disabled=false;setText('file-ready-btn',T.file_ready_btn);}
      });
  } else {
    // Store-Modus: POST /kx/print
    fetch(_apiUrl('/kx/print'),{
      method:'POST',
      headers:{'Content-Type':'application/json'},
      body:JSON.stringify({file_id:_storeFileId,filament_assignments:assignments,excluded_objects:excludedObjects})
    }).then(function(r){return r.json()}).then(function(d){
      if(d.result==='ok'){clog('Druckstart: '+_storeFilename,'msg-ok');showPanel('dashboard');}
      else{clog('Druckfehler: '+(d.error||'?'),'msg-err');}
    }).catch(function(e){clog('Druckfehler: '+e,'msg-err');});
  }
}

function renderObjectChecklist(){
  var box=document.getElementById('fd-objects');
  if(!box)return;
  box.innerHTML=_printObjects.map(function(o,i){
    var label=o.name;
    // Klipper-Namen sind oft "Datei.stl_id_N_copy_M" → schöner darstellen
    var m=label.match(/^(.+)\.stl_id_(\d+)_copy_(\d+)$/);
    if(m)label=m[1]+' #'+(parseInt(m[2])+1)+(m[3]!=='0'?' ('+(parseInt(m[3])+1)+')':'');
    return '<label style="display:flex;align-items:center;gap:8px;padding:6px 8px;border-radius:6px;background:var(--raised);border:1px solid var(--border);cursor:pointer;font-size:12px">'+
      '<input type="checkbox" data-idx="'+i+'" '+(o.skip?'checked':'')+' onchange="_toggleObjectSkip('+i+',this.checked)">'+
      '<span style="word-break:break-all">'+label+'</span>'+
      '</label>';
  }).join('');
}
function _toggleObjectSkip(idx,val){
  if(_printObjects[idx])_printObjects[idx].skip=!!val;
  renderObjectSvg();
}
function renderObjectSvg(){
  var box=document.getElementById('fd-objects-svg');
  if(!box)return;
  if(!_printObjectsSvg||!_printObjects.length){box.style.display='none';box.innerHTML='';return;}
  box.style.display='block';
  var svg=''; try{ svg=atob(_printObjectsSvg);}catch(e){ box.style.display='none'; return; }
  box.innerHTML=svg;
  var svgEl=box.querySelector('svg');
  if(!svgEl)return;
  svgEl.style.width='100%'; svgEl.style.maxHeight='200px'; svgEl.style.height='auto';
  _printObjects.forEach(function(o,i){
    var g=svgEl.querySelector('g[id="'+CSS.escape(o.name)+'"]');
    if(!g)return;
    var path=g.querySelector('path');
    g.style.cursor='pointer';
    g.setAttribute('opacity', o.skip?'0.8':'0.35');
    if(path){
      path.setAttribute('fill', o.skip?'#ff5e5b':'#5fa7ff');
      path.setAttribute('fill-opacity', o.skip?'0.4':'0.18');
    }
    g.onclick=function(){
      _printObjects[i].skip=!_printObjects[i].skip;
      renderObjectChecklist(); renderObjectSvg();
    };
  });
}

// ── Mid-Print Skip ──
var _skipObjects=[]; // [{name, skipped, willSkip}]
var _skipSvg='';
function openSkipDialog(){
  document.getElementById('skip-status').textContent='';
  document.getElementById('skip-confirm').disabled=false;
  _refreshSkipDialog();
  document.getElementById('skip-dialog').classList.add('open');
}
function _refreshSkipDialog(){
  // Erst aktueller State (mit DB-Objects + svg), dann query_obj für frischen skipped
  fetch(_apiUrl('/kx/skip/state')).then(function(r){return r.json()}).then(function(d){
    var s=d.result||{};
    _skipSvg=s.svg_b64||'';
    _skipObjects=(s.objects||[]).map(function(n){
      return {name:n, skipped:(s.skipped||[]).indexOf(n)>=0, willSkip:false};
    });
    renderSkipList(); renderSkipSvg();
  });
  // Frisch nachfragen (skipped-Liste aktualisieren)
  fetch(_apiUrl('/kx/skip/query'),{method:'POST'}).then(function(r){return r.json()}).then(function(){
    setTimeout(function(){
      fetch(_apiUrl('/kx/skip/state')).then(function(r){return r.json()}).then(function(d){
        var s=d.result||{};
        var skipped=s.skipped||[];
        _skipObjects.forEach(function(o){ o.skipped=skipped.indexOf(o.name)>=0; if(o.skipped)o.willSkip=false; });
        renderSkipList(); renderSkipSvg();
      });
    }, 500);
  }).catch(function(){});
}
function closeSkipDialog(){
  document.getElementById('skip-dialog').classList.remove('open');
}
function _shortLabel(name){
  var m=name.match(/^(.+)\.[sS][tT][lL]_id_(\d+)_copy_(\d+)$/);
  if(!m)return name;
  return m[1]+' #'+(parseInt(m[2])+1)+(m[3]!=='0'?' ('+(parseInt(m[3])+1)+')':'');
}
function renderSkipList(){
  var box=document.getElementById('skip-list');
  if(!box)return;
  if(!_skipObjects.length){
    box.innerHTML='<div style="color:var(--txt2);font-size:12px;padding:12px;text-align:center">'+(T.skip_no_objects||'Keine Objekte in diesem Druck.')+'</div>';
    return;
  }
  box.innerHTML=_skipObjects.map(function(o,i){
    var label=_shortLabel(o.name);
    var dis=o.skipped?'disabled':'';
    var note=o.skipped?'<span style="font-size:11px;color:var(--warn);margin-left:auto">'+(T.skip_already||'übersprungen')+'</span>':'';
    return '<label style="display:flex;align-items:center;gap:8px;padding:6px 8px;border-radius:6px;background:var(--raised);border:1px solid var(--border);font-size:12px;'+(o.skipped?'opacity:0.5':'')+'">'+
      '<input type="checkbox" data-idx="'+i+'" '+(o.willSkip?'checked':'')+' '+dis+' onchange="_toggleWillSkip('+i+',this.checked)">'+
      '<span style="word-break:break-all">'+label+'</span>'+note+
      '</label>';
  }).join('');
}
function renderSkipSvg(){
  var box=document.getElementById('skip-svg');
  if(!box)return;
  if(!_skipSvg||!_skipObjects.length){box.style.display='none';box.innerHTML='';return;}
  box.style.display='block';
  // SVG aus base64 dekodieren
  var svg='';
  try{ svg=atob(_skipSvg); }catch(e){ box.style.display='none'; return; }
  box.innerHTML=svg;
  // Polygone interaktiv machen: jeder <g id="..."> entspricht einem Objekt
  var svgEl=box.querySelector('svg');
  if(!svgEl)return;
  svgEl.style.width='100%'; svgEl.style.maxHeight='280px'; svgEl.style.height='auto';
  _skipObjects.forEach(function(o,i){
    var g=svgEl.querySelector('g[id="'+CSS.escape(o.name)+'"]');
    if(!g)return;
    var path=g.querySelector('path');
    if(o.skipped){
      // bereits übersprungen → ausgegraut, kein Klick
      g.setAttribute('opacity','0.25');
      if(path){path.setAttribute('fill','#888');path.setAttribute('fill-opacity','0.3');}
      g.style.cursor='not-allowed';
    } else {
      g.style.cursor='pointer';
      g.setAttribute('opacity', o.willSkip?'0.8':'0.35');
      if(path){
        path.setAttribute('fill', o.willSkip?'#ff5e5b':'#5fa7ff');
        path.setAttribute('fill-opacity', o.willSkip?'0.4':'0.18');
      }
      g.onclick=function(){
        _skipObjects[i].willSkip=!_skipObjects[i].willSkip;
        renderSkipList(); renderSkipSvg();
      };
    }
  });
}
function _toggleWillSkip(idx,val){
  if(_skipObjects[idx])_skipObjects[idx].willSkip=!!val;
  renderSkipSvg();
}
function confirmSkip(){
  var names=_skipObjects.filter(function(o){return o.willSkip;}).map(function(o){return o.name;});
  var st=document.getElementById('skip-status');
  var btn=document.getElementById('skip-confirm');
  if(!names.length){st.textContent=T.skip_select_at_least_one||'Bitte mindestens ein Objekt wählen.';st.style.color='var(--warn)';return;}
  btn.disabled=true; st.textContent=T.skip_sending||'Sende …'; st.style.color='var(--txt2)';
  fetch(_apiUrl('/kx/skip'),{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({names:names})})
    .then(function(r){return r.json().then(function(j){return {ok:r.ok,j:j};});})
    .then(function(res){
      if(!res.ok){st.textContent=(res.j&&res.j.error)||'Fehler';st.style.color='var(--err)';btn.disabled=false;return;}
      st.textContent=T.skip_success||'Objekte werden übersprungen.';st.style.color='var(--ok)';
      // Dialog offen lassen + neu laden damit der "übersprungen"-Status erscheint
      setTimeout(function(){ _refreshSkipDialog(); btn.disabled=false; st.textContent=''; }, 1500);
    })
    .catch(function(e){st.textContent=''+e;st.style.color='var(--err)';btn.disabled=false;});
}

function storeDelete(fileId){
  if(!confirm(T.store_delete_confirm)) return;
  fetch(_apiUrl('/kx/files/'+fileId),{method:'DELETE'}).then(function(r){
    if(r.ok){loadStore();}
    else{clog('Löschen fehlgeschlagen','msg-err');}
  });
}

// ── Drucker hinzufügen ──
function openAddPrinterDialog(){
  document.getElementById('apd-ip').value='';
  document.getElementById('apd-name').value='';
  var st=document.getElementById('apd-status');st.textContent='';st.style.color='var(--txt2)';
  document.getElementById('apd-confirm').disabled=false;
  document.getElementById('add-printer-dialog').classList.add('open');
}
function closeAddPrinterDialog(){
  document.getElementById('add-printer-dialog').classList.remove('open');
}
function confirmAddPrinter(){
  var ip=document.getElementById('apd-ip').value.trim();
  var name=document.getElementById('apd-name').value.trim();
  var st=document.getElementById('apd-status'),btn=document.getElementById('apd-confirm');
  if(!ip){st.textContent=T.apd_err_ip;st.style.color='var(--err)';return;}
  st.textContent=T.apd_fetching;st.style.color='var(--txt2)';btn.disabled=true;
  fetch('/kx/printers/add',{method:'POST',headers:{'Content-Type':'application/json'},
    body:JSON.stringify({printer_ip:ip,name:name})})
    .then(function(r){return r.json().then(function(j){return {ok:r.ok,j:j};});})
    .then(function(res){
      if(!res.ok){st.textContent=(res.j&&res.j.error)||'Fehler';st.style.color='var(--err)';btn.disabled=false;return;}
      st.textContent=T.apd_success;st.style.color='var(--ok)';
      setTimeout(function(){location.reload();},2500);
    })
    .catch(function(e){st.textContent=''+e;st.style.color='var(--err)';btn.disabled=false;});
}
function removePrinter(id,name){
  if(!confirm(T.printers_remove_confirm.replace('{name}',name)))return;
  fetch('/kx/printers/'+encodeURIComponent(id),{method:'DELETE'})
    .then(function(r){return r.json().then(function(j){return {ok:r.ok,j:j};});})
    .then(function(res){
      if(!res.ok){alert((res.j&&res.j.error)||'Fehler');return;}
      setTimeout(function(){location.href='/printer1';},2000);
    })
    .catch(function(e){alert(''+e);});
}

// ── Drucker-Tab ──
function loadPrinterTab(){
  var grid=document.getElementById('printers-grid');
  if(grid)grid.innerHTML='<div style="color:var(--txt2);font-size:13px;padding:20px">'+T.printers_loading+'</div>';
  // Drucker-Liste von lokaler Instanz holen
  fetch('/kx/printers').then(function(r){return r.json()}).then(function(d){
    var printers=d.result||[];
    if(!printers.length){
      if(grid)grid.innerHTML='<div style="grid-column:1/-1;text-align:center;padding:40px 20px;color:var(--txt2)">'+
        '<div style="font-size:32px;margin-bottom:8px">🖨</div>'+
        '<div style="font-size:14px;margin-bottom:14px">'+T.printers_empty_hint+'</div>'+
        '<button onclick="openAddPrinterDialog()" style="font-size:13px;padding:8px 18px;background:var(--accent);border:none;border-radius:8px;color:#fff;cursor:pointer;font-weight:600">+ '+T.add_printer+'</button>'+
      '</div>';
      return;
    }
    // Status jedes Druckers parallel abrufen
    var fetches=printers.map(function(p){
      var url=(p.bridge_url||'').replace(/\/+$/,'');
      return fetch(url+'/api/state',{signal:AbortSignal.timeout(3000)})
        .then(function(r){return r.json()})
        .then(function(s){return {printer:p,state:s,online:true};})
        .catch(function(){return {printer:p,state:{},online:false};});
    });
    Promise.all(fetches).then(function(results){
      var activeId=_activePrinter?String(_activePrinter.id):null;
      if(grid)grid.innerHTML=results.map(function(res){
        var p=res.printer,s=res.state,online=res.online;
        var isActive=String(p.id)===activeId;
        var url=(p.bridge_url||'').replace(/\/+$/,'');
        var printerNum=p.id;
        var ks=online?(s.kobra_state||'free'):'offline';
        var stateKey='kobra_'+ks;
        var stateLabel=T[stateKey]||ks;
        var stateColor=ks==='free'?'var(--ok)':ks==='printing'?'var(--accent)':ks==='offline'?'var(--txt2)':'var(--warn)';
        var progress=online&&s.progress?Math.round(s.progress*100):null;
        var filename=online&&s.filename?s.filename:'';
        var nt=online&&s.nozzle_temp?s.nozzle_temp.toFixed(1):'–';
        var bt=online&&s.bed_temp?s.bed_temp.toFixed(1):'–';
        var border=isActive?'2px solid var(--accent)':'1px solid var(--border)';
        var nameEsc=String(p.name).replace(/\\/g,'\\\\').replace(/'/g,"\\'");
        return '<div style="background:var(--raised);border:'+border+';border-radius:10px;padding:14px;display:flex;flex-direction:column;gap:8px">'+
          '<div style="display:flex;align-items:center;justify-content:space-between;gap:8px">'+
            '<span style="font-weight:700;font-size:14px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap">🖨 '+p.name+'</span>'+
            '<span style="display:flex;align-items:center;gap:8px;flex-shrink:0">'+
              (isActive?'<span style="font-size:11px;color:var(--accent);font-weight:600">'+T.printers_active+'</span>':'')+
              '<button onclick="removePrinter(\''+printerNum+'\',\''+nameEsc+'\')" title="'+T.printers_remove+'" style="background:none;border:none;color:var(--txt2);font-size:16px;cursor:pointer;line-height:1;padding:0">✕</button>'+
            '</span>'+
          '</div>'+
          '<div style="display:flex;align-items:center;gap:6px">'+
            '<span style="width:8px;height:8px;border-radius:50%;background:'+stateColor+';display:inline-block"></span>'+
            '<span style="font-size:13px;color:var(--txt2)">'+stateLabel+'</span>'+
          '</div>'+
          (p.printer_ip?'<div style="font-size:12px;color:var(--txt2)">🌐 '+p.printer_ip+'</div>':'')+
          (filename?'<div style="font-size:12px;color:var(--txt2);white-space:nowrap;overflow:hidden;text-overflow:ellipsis" title="'+filename+'">📄 '+filename+'</div>':'')+
          (progress!==null?'<div style="background:var(--border);border-radius:4px;height:6px;overflow:hidden"><div style="background:var(--accent);height:100%;width:'+progress+'%"></div></div>':'')+
          '<div style="font-size:12px;color:var(--txt2);display:flex;gap:12px">'+
            '<span>🌡 '+nt+'°C</span><span>🛏 '+bt+'°C</span>'+
          '</div>'+
          (!isActive?'<a href="/printer'+printerNum+'" style="display:block;text-align:center;padding:7px;background:var(--accent);color:#fff;border-radius:7px;font-size:13px;font-weight:600;text-decoration:none;margin-top:4px">'+T.printers_switch+'</a>':'<div style="text-align:center;padding:7px;font-size:12px;color:var(--txt2)">'+T.printers_current+'</div>')+
        '</div>';
      }).join('');
    });
  }).catch(function(e){
    if(grid)grid.innerHTML='<div style="color:var(--err);font-size:13px;padding:20px">Fehler: '+e+'</div>';
  });
}
</script>
<!-- Filament-Slot-Dialog -->
<div class="modal-overlay" id="filament-dialog" onclick="if(event.target===this)closeFilamentDialog()">
  <div class="modal-box" style="max-width:380px;width:100%">
    <div class="modal-header" style="margin-bottom:14px">
      <span class="modal-title" id="fd-title" style="font-size:14px;word-break:break-all"></span>
      <button onclick="closeFilamentDialog()" style="background:none;border:none;font-size:18px;cursor:pointer;color:var(--txt2)">✕</button>
    </div>
    <p id="fd-slots-hint" style="font-size:12px;color:var(--txt2);margin-bottom:10px">GCode-Kanal → AMS-Slot zuweisen:</p>
    <div id="fd-slots" style="display:flex;flex-direction:column;gap:8px;margin-bottom:16px"></div>
    <div id="fd-objects-section" style="display:none;margin-bottom:16px">
      <p id="fd-objects-hint" style="font-size:12px;color:var(--txt2);margin-bottom:8px">Objekte überspringen (optional):</p>
      <div id="fd-objects-svg" style="display:none;background:var(--raised);border:1px solid var(--border);border-radius:8px;padding:6px;margin-bottom:8px;text-align:center"></div>
      <div id="fd-objects" style="display:flex;flex-direction:column;gap:6px;max-height:140px;overflow-y:auto"></div>
    </div>
    <div style="display:flex;gap:8px;justify-content:flex-end">
      <button id="fd-cancel" onclick="closeFilamentDialog()" style="padding:8px 16px;background:var(--raised);border:1px solid var(--border);border-radius:8px;color:var(--txt);cursor:pointer">Abbrechen</button>
      <button id="fd-print" onclick="confirmFilamentPrint()" style="padding:8px 18px;background:var(--accent);color:#fff;border:none;border-radius:8px;cursor:pointer;font-weight:600">▶ Drucken</button>
    </div>
  </div>
</div>
<!-- Drucker-hinzufügen-Dialog -->
<div class="modal-overlay" id="add-printer-dialog" onclick="if(event.target===this)closeAddPrinterDialog()">
  <div class="modal-box" style="max-width:380px;width:100%">
    <div class="modal-header" style="margin-bottom:14px">
      <span class="modal-title" id="apd-title">Drucker hinzufügen</span>
      <button onclick="closeAddPrinterDialog()" style="background:none;border:none;font-size:18px;cursor:pointer;color:var(--txt2)">✕</button>
    </div>
    <label id="apd-lbl-ip" style="display:block;font-size:12px;color:var(--txt2);margin-bottom:4px">Drucker-IP</label>
    <input type="text" id="apd-ip" placeholder="192.168.1.100" style="width:100%;box-sizing:border-box;padding:8px;background:var(--raised);border:1px solid var(--border);border-radius:6px;color:var(--txt);margin-bottom:10px">
    <label id="apd-lbl-name" style="display:block;font-size:12px;color:var(--txt2);margin-bottom:4px">Name (optional)</label>
    <input type="text" id="apd-name" placeholder="z.B. Kobra X Wohnzimmer" style="width:100%;box-sizing:border-box;padding:8px;background:var(--raised);border:1px solid var(--border);border-radius:6px;color:var(--txt);margin-bottom:6px">
    <div id="apd-status" style="font-size:12px;margin:8px 0;min-height:16px;color:var(--txt2)"></div>
    <div style="display:flex;gap:8px;justify-content:flex-end">
      <button onclick="closeAddPrinterDialog()" style="padding:8px 16px;background:var(--raised);border:1px solid var(--border);border-radius:8px;color:var(--txt);cursor:pointer">Abbrechen</button>
      <button id="apd-confirm" onclick="confirmAddPrinter()" style="padding:8px 18px;background:var(--accent);color:#fff;border:none;border-radius:8px;cursor:pointer;font-weight:600">Hinzufügen</button>
    </div>
  </div>
</div>
<!-- Mid-Print Skip-Dialog -->
<div class="modal-overlay" id="skip-dialog" onclick="if(event.target===this)closeSkipDialog()">
  <div class="modal-box" style="max-width:420px;width:100%">
    <div class="modal-header" style="margin-bottom:14px">
      <span class="modal-title" id="skip-title">✂ Objekte überspringen</span>
      <button onclick="closeSkipDialog()" style="background:none;border:none;font-size:18px;cursor:pointer;color:var(--txt2)">✕</button>
    </div>
    <p id="skip-hint" style="font-size:12px;color:var(--txt2);margin-bottom:10px">Objekte abwählen, die nicht weiter gedruckt werden sollen:</p>
    <div id="skip-svg" style="display:none;background:var(--raised);border:1px solid var(--border);border-radius:8px;padding:6px;margin-bottom:10px;text-align:center"></div>
    <div id="skip-list" style="display:flex;flex-direction:column;gap:6px;max-height:200px;overflow-y:auto;margin-bottom:12px"></div>
    <div id="skip-status" style="font-size:12px;color:var(--txt2);min-height:16px;margin-bottom:8px"></div>
    <div style="display:flex;gap:8px;justify-content:flex-end">
      <button onclick="closeSkipDialog()" style="padding:8px 16px;background:var(--raised);border:1px solid var(--border);border-radius:8px;color:var(--txt);cursor:pointer">Abbrechen</button>
      <button id="skip-confirm" onclick="confirmSkip()" style="padding:8px 18px;background:var(--accent);color:#fff;border:none;border-radius:8px;cursor:pointer;font-weight:600">Überspringen</button>
    </div>
  </div>
</div>

<!-- ACE Dryer Temp/Time Settings Dialog -->
<div class="modal-overlay" id="ace-dry-dialog" onclick="if(event.target===this)closeAceDryDialog()">
  <div class="modal-box" style="max-width:560px;width:100%">
    <div class="modal-header" style="margin-bottom:10px">
      <span class="modal-title" id="ace-dry-dialog-title">Dryer Temp/Time Settings</span>
      <button onclick="closeAceDryDialog()" style="background:none;border:none;font-size:18px;cursor:pointer;color:var(--txt2)">✕</button>
    </div>
    <div style="display:flex;align-items:center;gap:12px;margin-bottom:8px">
      <label id="ace-dry-dialog-temp-label" style="min-width:190px;font-size:12px;color:var(--txt)">Temperature (30-80°C)</label>
      <input id="ace-dry-dialog-temp" type="number" min="30" max="80" step="1"
        oninput="aceDryDialogInputsChanged()"
        style="width:130px;padding:8px;background:var(--raised);border:1px solid var(--border);border-radius:6px;color:var(--txt);text-align:center" value="45">
    </div>
    <div style="display:flex;align-items:center;gap:12px;margin-bottom:16px">
      <label id="ace-dry-dialog-time-label" style="min-width:190px;font-size:12px;color:var(--txt)">Rem. Time (h:m:s)</label>
      <div style="display:flex;align-items:center;gap:8px">
        <input id="ace-dry-dialog-h" type="number" min="0" max="24" step="1" value="4"
          oninput="aceDryDialogInputsChanged()"
          style="width:70px;padding:8px;background:var(--raised);border:1px solid var(--border);border-radius:6px;color:var(--txt);text-align:center">
        <span style="color:var(--txt2)">:</span>
        <input id="ace-dry-dialog-m" type="number" min="0" max="59" step="1" value="0"
          oninput="aceDryDialogInputsChanged()"
          style="width:70px;padding:8px;background:var(--raised);border:1px solid var(--border);border-radius:6px;color:var(--txt);text-align:center">
        <span style="color:var(--txt2)">:</span>
        <input id="ace-dry-dialog-s" type="number" min="0" max="59" step="1" value="0"
          oninput="aceDryDialogInputsChanged()"
          style="width:70px;padding:8px;background:var(--raised);border:1px solid var(--border);border-radius:6px;color:var(--txt);text-align:center">
      </div>
    </div>
    <div style="display:grid;grid-template-columns:repeat(3,1fr);gap:8px;margin-bottom:8px">
      <button class="ace-dry-preset-btn" data-preset="pla" onclick="aceDryDialogPreset('pla')" style="padding:8px;border-radius:8px;border:1px solid var(--border);background:var(--raised);color:var(--txt2);cursor:pointer">PLA</button>
      <button class="ace-dry-preset-btn" data-preset="pla_plus" onclick="aceDryDialogPreset('pla_plus')" style="padding:8px;border-radius:8px;border:1px solid var(--border);background:var(--raised);color:var(--txt2);cursor:pointer">PLA+</button>
      <button class="ace-dry-preset-btn" data-preset="petg" onclick="aceDryDialogPreset('petg')" style="padding:8px;border-radius:8px;border:1px solid var(--border);background:var(--raised);color:var(--txt2);cursor:pointer">PETG</button>
      <button class="ace-dry-preset-btn" data-preset="tpu" onclick="aceDryDialogPreset('tpu')" style="padding:8px;border-radius:8px;border:1px solid var(--border);background:var(--raised);color:var(--txt2);cursor:pointer">TPU</button>
      <button class="ace-dry-preset-btn" data-preset="abs_asa" onclick="aceDryDialogPreset('abs_asa')" style="padding:8px;border-radius:8px;border:1px solid var(--border);background:var(--raised);color:var(--txt2);cursor:pointer">ABS / ASA</button>
      <button class="ace-dry-preset-btn" data-preset="pa_pc" onclick="aceDryDialogPreset('pa_pc')" style="padding:8px;border-radius:8px;border:1px solid var(--border);background:var(--raised);color:var(--txt2);cursor:pointer">PA / PC</button>
      <button class="ace-dry-preset-btn" data-preset="custom_1" onclick="aceDryDialogPreset('custom_1')" style="padding:8px;border-radius:8px;border:1px solid var(--border);background:var(--raised);color:var(--txt2);cursor:pointer">Custom 1</button>
      <button class="ace-dry-preset-btn" data-preset="custom_2" onclick="aceDryDialogPreset('custom_2')" style="padding:8px;border-radius:8px;border:1px solid var(--border);background:var(--raised);color:var(--txt2);cursor:pointer">Custom 2</button>
      <button class="ace-dry-preset-btn" data-preset="custom_3" onclick="aceDryDialogPreset('custom_3')" style="padding:8px;border-radius:8px;border:1px solid var(--border);background:var(--raised);color:var(--txt2);cursor:pointer">Custom 3</button>
    </div>
    <div id="ace-dry-dialog-custom-name-row" style="display:none;align-items:center;gap:12px;margin-bottom:14px">
      <label id="ace-dry-dialog-custom-name-label" style="min-width:190px;font-size:12px;color:var(--txt)">Custom Name</label>
      <input id="ace-dry-dialog-custom-name" type="text" maxlength="32" oninput="aceDryDialogInputsChanged()"
        style="width:220px;padding:8px;background:var(--raised);border:1px solid var(--border);border-radius:6px;color:var(--txt)">
    </div>
    <div style="display:flex;justify-content:flex-end;gap:8px">
      <button id="ace-dry-dialog-reset-default" onclick="resetAceDryPresetToDefault()" style="display:none;padding:8px 14px;background:var(--raised);border:1px solid var(--border);border-radius:8px;color:var(--txt);cursor:pointer">Reset to Default</button>
      <button id="ace-dry-dialog-save-preset" onclick="saveAceDryPresetAndRestart()" style="display:none;padding:8px 14px;background:var(--warn);border:1px solid transparent;border-radius:8px;color:#fff;cursor:pointer">Save & Restart</button>
      <button id="ace-dry-dialog-cancel" onclick="closeAceDryDialog()" style="padding:8px 14px;background:var(--raised);border:1px solid var(--border);border-radius:8px;color:var(--txt);cursor:pointer">Cancel</button>
      <button id="ace-dry-dialog-confirm" onclick="confirmAceDryDialog()" style="padding:8px 16px;background:var(--accent);color:#fff;border:none;border-radius:8px;cursor:pointer;font-weight:600">Confirm</button>
    </div>
  </div>
</div>

<footer style="text-align:center;padding:12px;font-size:11px;color:var(--txt2);border-top:1px solid var(--border);margin-top:auto">
  &copy; ViewIT 2026
</footer>
</body>
</html>
"""
