// ── State ──
var S={nozzle_temp:0,nozzle_target:0,bed_temp:0,bed_target:0,
  print_state:'standby',filename:'',progress:0,print_duration:0,remain_time:0,
  curr_layer:0,total_layers:0,printer_name:'Kobra X',firmware_version:'–',
  camera_url:'',fan_speed:0,print_speed_mode:2,light_on:false,light_brightness:80,
  ams_slots:[],filament_mode:'toolhead',ace_units:[],ace_dry_presets:null,ace_drying:{status:0,target_temp:0,duration:0,remain_time:0,humidity:null,current_temp:null,units:[]},web_upload_warning:1};
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
var currentLang='de';
var T={};
var _langCache={};

function tr(key,fallback){
  var v=T&&T[key];
  return (typeof v==='string'&&v.length)?v:(fallback!==undefined?fallback:'');
}

function _langToggleLabel(lang){
  if(lang==='de')return 'Deutsch';
  if(lang==='en')return 'English';
  if(lang==='zh-cn')return '简体中文';
  return 'Espanol';
}

function _mapSupportedLang(lang){
  if(!lang)return '';
  var l=String(lang).toLowerCase().replace(/_/g,'-').trim();
  if(l==='de'||l==='en'||l==='es'||l==='zh-cn')return l;

  var base=l.split('-')[0];
  if(base==='de'||base==='en'||base==='es')return base;

  if(base==='zh'){
    if(l.indexOf('cn')>=0||l.indexOf('hans')>=0||l==='zh')return 'zh-cn';
  }
  return '';
}

function _normalizeLang(lang){
  return _mapSupportedLang(lang)||'de';
}

function _detectBrowserLanguage(){
  var prefs=[];
  if(Array.isArray(navigator.languages)&&navigator.languages.length)prefs=navigator.languages;
  else if(navigator.language)prefs=[navigator.language];
  for(var i=0;i<prefs.length;i++){
    var mapped=_mapSupportedLang(prefs[i]);
    if(mapped)return mapped;
  }
  return '';
}

function _resolveInitialLanguage(){
  var saved=localStorage.getItem('lang');
  var mappedSaved=_mapSupportedLang(saved);
  if(mappedSaved)return mappedSaved;
  return _detectBrowserLanguage()||'de';
}

async function _loadLanguage(lang){
  var l=_normalizeLang(lang);
  if(_langCache[l])return _langCache[l];
  var res=await fetch('/kx/ui/translations/'+l+'.json');
  if(!res.ok)throw new Error('failed to load translations: '+l);
  var data=await res.json();
  _langCache[l]=data||{};
  return _langCache[l];
}

async function setLanguage(lang){
  var l=_normalizeLang(lang);
  try{
    T=await _loadLanguage(l);
  }catch(_){
    var fb=(l==='de')?'en':'de';
    T=await _loadLanguage(fb);
    l=fb;
  }
  currentLang=l;
  localStorage.setItem('lang',l);
  var langSel=document.getElementById('lang-select');
  if(langSel)langSel.value=l;
  document.documentElement.setAttribute('lang',l);
  applyLang();
}

function setLanguageFromSelect(){
  var langSel=document.getElementById('lang-select');
  var next=langSel?langSel.value:'de';
  setLanguage(next).catch(function(){});
}
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
  var apn=document.getElementById('apd-name');if(apn)apn.setAttribute('placeholder',T.apd_placeholder_name);
  setText('apd-cancel',T.apd_cancel);
  setText('apd-confirm',T.apd_confirm);
  setText('fd-slots-hint',T.fd_slots_hint);
  setText('fd-cancel',T.fd_cancel);
  setText('fd-print',T.fd_print);
  setText('store-panel-title','🗂 '+T.panel_browser_title);
  var srb=document.getElementById('store-refresh-btn');if(srb)srb.textContent=T.store_refresh;
  var ssp=document.getElementById('store-search');if(ssp)ssp.setAttribute('placeholder',T.store_search_placeholder);
  setText('store-upload-label-prefix',T.store_upload_label_prefix);
  setText('store-upload-label-browse',T.store_upload_label_browse);
  setText('store-empty',T.store_empty);
  setText('sf-all',T.sf_all);setText('sf-ok',T.sf_ok);setText('sf-err',T.sf_err);setText('sf-new',T.sf_new);
  setText('ss-date',T.ss_date);setText('ss-name',T.ss_name);setText('ss-dur',T.ss_dur);
  setText('store-web-verify-title',T.store_web_verify_title);
  setText('store-web-verify-msg',T.store_web_verify_msg);
  setText('store-web-verify-confirm',T.store_web_verify_confirm);
  setText('store-web-verify-abort',T.store_web_verify_abort);
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
  setText('d-lbl-nozzle',T.label_nozzle);
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
  setText('lbl-camera-on-print',T.settings_camera_on_print);
  setText('lbl-web-upload-warning',T.settings_web_upload_warning);

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
      setText('d-card-ace-dry-'+i,'ACE '+(i+1)+' - '+tr('ace_dry_dryer'));
      setText('d-ace-auto-refill-label-'+i,tr('ace_dry_auto_refill'));
      setText('d-ace-drying-enable-label-'+i,tr('ace_dry_enable'));
      setText('d-ace-dry-humidity-label-'+i,tr('ace_dry_humidity')+':');
      setText('d-ace-dry-current-temp-label-'+i,tr('ace_dry_current_temp')+':');
      setText('d-ace-dry-target-label-'+i,tr('ace_dry_temp_line')+':');
      setText('d-ace-dry-time-label-'+i,tr('ace_dry_time_line')+':');
      setText('d-ace-dry-chart-label-'+i,tr('ace_dry_chart'));
    var adTemp=document.getElementById('ace-dry-temp-'+i);if(adTemp)adTemp.setAttribute('placeholder',T.ace_dry_temp);
    var adDur=document.getElementById('ace-dry-duration-'+i);if(adDur)adDur.setAttribute('placeholder',T.ace_dry_duration);
  }
  setText('ace-dry-dialog-title',tr('ace_dry_dialog_title'));
  setText('ace-dry-dialog-temp-label',tr('ace_dry_dialog_temp'));
  setText('ace-dry-dialog-time-label',tr('ace_dry_dialog_time'));
  setText('ace-dry-dialog-custom-name-label',tr('ace_dry_dialog_custom_name'));
  setText('ace-dry-dialog-cancel',tr('ace_dry_dialog_cancel'));
  setText('ace-dry-dialog-confirm',tr('ace_dry_dialog_confirm'));
  setText('ace-dry-dialog-reset-default',tr('ace_dry_dialog_reset_default'));
  setText('ace-dry-dialog-save-preset',tr('ace_dry_dialog_save_restart'));
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
  setText('loglvl-all',T.log_dir_all);
  setText('log-lbl-level',T.log_lvl_label);
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
  var l=_resolveInitialLanguage();
  currentLang=_normalizeLang(l);
  var langSel=document.getElementById('lang-select');
  if(langSel)langSel.value=currentLang;
  document.documentElement.setAttribute('lang',currentLang);
  // defer until DOM ready
  window.addEventListener('DOMContentLoaded',function(){
    setLanguage(currentLang).catch(function(){});
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
var logLevelFilter='all'; // 'all'|'err'|'warn'
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
  var fullMsg=label+entry.msg;
  // Wiederholungen als Zähler zusammenfassen (×N) statt N identische Zeilen.
  var last=consoleLogs[consoleLogs.length-1];
  if(last&&last.msg===fullMsg&&last.cls===cls){
    last.count=(last.count||1)+1;
    last.ts=entry.ts; // letzte Sichtung
    renderLog();
    return;
  }
  consoleLogs.push({ts:entry.ts,msg:fullMsg,cls:cls,count:1});
  if(consoleLogs.length>500)consoleLogs.shift();
  // Badge + Toast wenn Tab nicht aktiv und Fehler/Warnungen
  if(currentPanel!=='console'&&(cls==='msg-err'||cls==='msg-warn')){
    logBadgeCount++;
    var bc=logBadgeCount>99?'99+':logBadgeCount;
    ['log-badge','log-badge-bot'].forEach(function(id){var b=document.getElementById(id);if(b){b.style.display='inline';b.textContent=bc;}});
  }
  if(cls==='msg-err')showToast(entry.msg.split('\n')[0]);
  renderLog();
}
// Kurze rote Snackbar bei Fehlern (auch wenn Konsole-Tab nicht offen).
var _toastTimer=null;
function showToast(msg){
  var t=document.getElementById('kx-toast');
  if(!t){
    t=document.createElement('div'); t.id='kx-toast';
    t.style.cssText='position:fixed;bottom:20px;left:50%;transform:translateX(-50%);background:var(--err);color:#fff;padding:10px 18px;border-radius:8px;font-size:13px;z-index:9999;max-width:90vw;box-shadow:0 4px 16px rgba(0,0,0,.4);cursor:pointer';
    t.onclick=function(){showPanel('console');t.style.display='none';};
    document.body.appendChild(t);
  }
  t.textContent='⚠ '+msg;
  t.style.display='block';
  clearTimeout(_toastTimer);
  _toastTimer=setTimeout(function(){t.style.display='none';},6000);
}
function setLogDir(dir){
  logDirFilter=dir;
  document.querySelectorAll('.log-dir-btn').forEach(function(b){
    b.style.background=b.id==='logdir-'+dir?'var(--accent)':'var(--raised)';
    b.style.color=b.id==='logdir-'+dir?'#fff':'var(--txt2)';
  });
  renderLog();
}
function setLogLevel(lvl){
  logLevelFilter=lvl;
  document.querySelectorAll('.log-lvl-btn').forEach(function(b){
    b.style.background=b.id==='loglvl-'+lvl?'var(--accent)':'var(--raised)';
    b.style.color=b.id==='loglvl-'+lvl?'#fff':'var(--txt2)';
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
    if(logLevelFilter==='err'&&l.cls!=='msg-err')return false;
    if(logLevelFilter==='warn'&&l.cls!=='msg-err'&&l.cls!=='msg-warn')return false;
    if(fl&&!m.toLowerCase().includes(fl))return false;
    return true;
  });
  var savedScroll=logAutoScroll?null:el.scrollTop;
  el.innerHTML=rows.map(function(l){
    var cnt=(l.count&&l.count>1)?' <span style="opacity:.7">(×'+l.count+')</span>':'';
    return '<div><span class="ts">'+l.ts+'</span><span class="'+l.cls+'">'+escHtml(l.msg)+'</span>'+cnt+'</div>';
  }).join('');
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
  if(banner){if(s.connection_error&&_printers.length>0){banner.textContent='⚠ '+tr('lbl_conn_error')+' '+s.connection_error;banner.style.display='block';}else{banner.style.display='none';}}
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
    var baseTitle=tr('card_ams');
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
        var slotLabel=T.label_slot+' '+(globalIdx+1);
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
        html+='<div class="ams-slot ams-slot-bridge" aria-label="'+T.label_slot+' 4">'
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
    btn.textContent=tr('btn_connect');
  } else {
    btn.className='conn-btn connected';
    btn.textContent=tr('btn_disconnect');
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
    var cop=document.getElementById('s-camera-on-print');if(cop)cop.checked=!!d.camera_on_print;
    var wuw=document.getElementById('s-web-upload-warning');if(wuw)wuw.checked=(d.web_upload_warning===undefined?true:!!d.web_upload_warning);
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
  btn.textContent=_slotEditLoaded?tr('slot_edit_unload'):tr('slot_edit_load');
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
  var currentFile=(storeFiles||[]).find(function(f){return f.filename===S.file_ready;});
  if(currentFile && currentFile.web_unverified && webUploadWarningEnabled()){
    maybeGateWebUpload(currentFile, function(){ startReadyFile(); });
    return;
  }
  var btn=document.getElementById('file-ready-btn');
  if(btn){btn.disabled=true;btn.textContent='…';}
  post('/printer/print/start',{filename:S.file_ready})
    .then(function(r){return r.json();})
    .then(function(r){
      document.getElementById('file-ready-banner').style.display='none';
      if(btn){btn.disabled=false;setText('file-ready-btn',T.file_ready_btn);}
    })
    .catch(function(e){
      clog(tr('log_error')+' '+e,'msg-err');
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
      clog(tr('slot_edit_ok')+' '+(_slotEditIndex+1)+': '+mat+' '+hex,'msg-ok');
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
  var webUploadWarning=(document.getElementById('s-web-upload-warning')||{}).checked?1:0;
  S.web_upload_warning=webUploadWarning;
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
    camera_on_print:  (document.getElementById('s-camera-on-print')||{}).checked?1:0,
    web_upload_warning:webUploadWarning,
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
      document.getElementById('cam-toggle-btn').textContent=tr('btn_cam_start');
      clog(tr('log_error')+' '+tr('cam_stream_unavailable'),'msg-err');
    };
    img.src='/api/camera/stream?t='+Date.now();
    camOn=true;
    document.getElementById('cam-toggle-btn').textContent=tr('btn_cam_stop');
    clog(tr('log_cam_start'),'msg-ok');
    // MJPEG liefert kein onload – Spinner nach kurzem Timeout ausblenden
    setTimeout(function(){
      sp.style.display='none';
      img.style.display='block';
    },1200);
  }).catch(function(e){
    sp.style.display='none';
    ph.style.display='flex';
    clog(tr('log_error')+' '+e,'msg-err');
  });
}

function camStop(){
  var img=document.getElementById('cam-img');
  post('/api/camera/stop',{}).catch(function(){});
  img.src='';
  img.style.display='none';
  document.getElementById('cam-placeholder').style.display='flex';
  camOn=false;
  document.getElementById('cam-toggle-btn').textContent=tr('btn_cam_start');
  clog(tr('log_cam_stop'),'msg-ok');
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
      clog('ACE '+(aceId+1)+' - '+tr('ace_dry_dryer')+': '+tr('ace_dry_start')+' ('+t+'°C, '+d+' min)','msg-ok');
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
      clog('ACE '+(aceId+1)+' - '+tr('ace_dry_auto_refill')+': '+(on?'ON':'OFF'),'msg-ok');
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
  if(sb){sb.disabled=false;sb.textContent=tr('ace_dry_dialog_save_restart');}
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
    clog('ACE preset '+key+' '+tr('settings_save'),'msg-ok');
    closeAceDryDialog();
  }).catch(function(e){
    btn.disabled=false;
    btn.textContent=tr('ace_dry_dialog_save_restart');
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
      clog('ACE '+(aceId+1)+' - '+tr('ace_dry_dryer')+': '+tr('ace_dry_stop'),'msg-ok');
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

function uploadGcode(file){
  if(!file) return;
  var zone=document.getElementById('store-upload-zone');
  var status=document.getElementById('store-upload-status');
  var label=document.getElementById('store-upload-label');
  if(status) { status.textContent=T.store_upload_busy; status.style.display=''; status.className='upload-status-busy'; }
  if(label) label.style.display='none';
  if(zone) zone.style.pointerEvents='none';
  var fd=new FormData();
  fd.append('file', file);
  fd.append('web_upload', 'true');
  fetch(_apiUrl('/api/files/local'),{method:'POST',body:fd})
    .then(function(r){
      if(!r.ok) return r.text().then(function(t){throw new Error(r.status+': '+t);});
      return r.json();
    })
    .then(function(){
      if(status){ status.textContent=T.store_upload_success.replace('{file}',file.name); status.className='upload-status-ok'; }
      loadStore();
      setTimeout(function(){
        if(status){status.style.display='none'; status.className='';}
        if(label) label.style.display='';
        if(zone) zone.style.pointerEvents='';
      }, 3000);
    })
    .catch(function(e){
      if(status){ status.textContent=T.store_upload_error.replace('{error}',e.message); status.className='upload-status-err'; }
      if(label) label.style.display='';
      if(zone) zone.style.pointerEvents='';
      clog('Upload-Fehler: '+e,'msg-err');
    });
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
      '<div style="font-size:11px;color:var(--txt2);margin-bottom:2px">⏱ '+T.store_estimate+': '+est+'</div>'+
      '<div style="font-size:11px;color:var(--txt2);margin-bottom:8px">📅 '+date+'</div>'+
      '<div style="display:flex;gap:6px;margin-top:auto">'+
        '<button onclick="storePrint(\''+f.id+'\',\''+f.filename.replace(/'/g,"\\'")+'\')" '+
          'style="flex:1;font-size:12px;padding:5px;background:var(--accent);color:#fff;border:none;border-radius:6px;cursor:pointer">'+T.store_print+'</button>'+
        '<button onclick="storeDownload(\''+f.id+'\')" title="'+T.store_download+'" '+
          'style="font-size:12px;padding:5px 8px;background:var(--raised);border:1px solid var(--border);border-radius:6px;color:var(--txt2);cursor:pointer">⬇</button>'+
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
var _pendingWebVerifyFileId=null;
var _pendingWebVerifyFilename='';
var _pendingWebVerifyAction=null;
// GCode-Store-Dateiliste. MUSS deklariert sein – sonst ReferenceError, wenn
// "Slots wählen" im Banner geklickt wird, bevor der Browser-Tab je geladen
// wurde (Issue #29 / Theme-Auslagerung PR #27).
var storeFiles=[];

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
  var fileObj=storeFiles.find(function(f){return f.id===fileId;});
  openStorePrintDialog(fileId, filename, fileObj);
}

function openStorePrintDialog(fileId, filename, fileObj){
  _storeFileId=fileId;
  _storeFilename=filename;
  _filamentDialogMode='store';
  maybeGateWebUpload(fileObj, function(){
    // GCode-Filamente aus Store-Datei holen (für Vorschau im Dialog)
    _setGcodeFilamentsFromFileObj(fileObj);
    fetch(_apiUrl('/kx/filament/slots')).then(function(r){return r.json()}).then(function(d){
      openFilamentDialog(d.result||[]);
    }).catch(function(){openFilamentDialog([]);});
  });
}

function webUploadWarningEnabled(){
  return S.web_upload_warning===undefined ? true : !!S.web_upload_warning;
}

function clearWebUploadWarningFlag(fileId, onDone){
  if(!fileId){
    if(onDone) onDone();
    return;
  }
  fetch(_apiUrl('/kx/files/'+encodeURIComponent(fileId)+'/verify'), {method:'POST'})
    .then(function(r){
      if(!r.ok) return r.text().then(function(t){throw new Error(r.status+': '+t);});
      return r.json();
    })
    .then(function(){
      var fileObj=(storeFiles||[]).find(function(f){return f.id===fileId;});
      if(fileObj){fileObj.web_unverified=false;}
      if(onDone) onDone();
      loadStore();
    })
    .catch(function(e){
      clog('Verifizierungs-Fehler: '+e,'msg-err');
    });
}

function maybeGateWebUpload(fileObj, onContinue){
  if(!fileObj || !fileObj.web_unverified){
    if(onContinue) onContinue();
    return;
  }
  if(!webUploadWarningEnabled()){
    if(onContinue) onContinue();
    return;
  }
  openWebVerifyDialog(fileObj.id, fileObj.filename, function(){
    clearWebUploadWarningFlag(fileObj.id, onContinue);
  });
}

function openWebVerifyDialog(fileId, filename, onConfirm){
  _pendingWebVerifyFileId=fileId;
  _pendingWebVerifyFilename=filename;
  _pendingWebVerifyAction=onConfirm||null;
  var status=document.getElementById('store-web-verify-status');
  if(status){status.textContent='';}
  openStoreWebVerifyDialog();
}

function openStoreWebVerifyDialog(){
  var modal=document.getElementById('store-web-verify-dialog');
  if(modal){modal.classList.add('open');}
}

function closeStoreWebVerifyDialog(){
  var modal=document.getElementById('store-web-verify-dialog');
  if(modal){modal.classList.remove('open');}
  _pendingWebVerifyFileId=null;
  _pendingWebVerifyFilename='';
  _pendingWebVerifyAction=null;
}

function confirmStoreWebVerify(){
  if(!_pendingWebVerifyFileId||!_pendingWebVerifyFilename){
    closeStoreWebVerifyDialog();
    return;
  }
  var fileId=_pendingWebVerifyFileId;
  var action=_pendingWebVerifyAction;
  var status=document.getElementById('store-web-verify-status');
  if(status){status.textContent='…';}
  fetch(_apiUrl('/kx/files/'+encodeURIComponent(fileId)+'/verify'), {method:'POST'})
    .then(function(r){
      if(!r.ok) return r.text().then(function(t){throw new Error(r.status+': '+t);});
      return r.json();
    })
    .then(function(){
      var fileObj=(storeFiles||[]).find(function(f){return f.id===fileId;});
      if(fileObj){fileObj.web_unverified=false;}
      _pendingWebVerifyFileId=null;
      _pendingWebVerifyFilename='';
      _pendingWebVerifyAction=null;
      closeStoreWebVerifyDialog();
      loadStore();
      if(typeof action==='function') action();
    })
    .catch(function(e){
      if(status){status.textContent='✗ '+e.message;}
      clog('Verifizierungs-Fehler: '+e,'msg-err');
    });
}

function startReadyFileWithSlots(){
  var currentFile=(storeFiles||[]).find(function(f){return f.filename===S.file_ready;});
  if(currentFile && currentFile.web_unverified && webUploadWarningEnabled()){
    maybeGateWebUpload(currentFile, function(){ startReadyFileWithSlots(); });
    return;
  }
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
    body.innerHTML='<p style="color:var(--txt2);font-size:13px;text-align:center;padding:16px 0">'+T.fd_no_slots_msg.replace('{br}','<br>')+'</p>';
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
          '● '+T.fd_slot+' '+(s.slot_index+1)+' · '+s.material+'</option>';
      }).join('');
      if(!compatible.length){
        opts='<option value="-1" data-color="#888888" data-material="" selected>⚠ '+T.fd_no_matching_material+'</option>';
      }
      // Kanal-Box (links): farbige Box mit Nummer + auto Kontrast-Text
      var txt=_contrastText(gc.color_hex);
      var slotColor=defaultSlot?defaultSlot.color_hex:'#888';
      var slotTxt=_contrastText(slotColor);
      var usedBadge=isUsed
        ? '<span style="font-size:10px;color:var(--ok);font-weight:700;min-width:32px">'+T.fd_used+'</span>'
        : '<span style="font-size:10px;color:var(--txt2);font-weight:700;min-width:32px;opacity:.75">'+T.fd_used+'</span>';
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
        clog(tr('log_error')+' '+e,'msg-err');
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
    box.innerHTML='<div style="color:var(--txt2);font-size:12px;padding:12px;text-align:center">'+tr('skip_no_objects')+'</div>';
    return;
  }
  box.innerHTML=_skipObjects.map(function(o,i){
    var label=_shortLabel(o.name);
    var dis=o.skipped?'disabled':'';
    var note=o.skipped?'<span style="font-size:11px;color:var(--warn);margin-left:auto">'+tr('skip_already')+'</span>':'';
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
  if(!names.length){st.textContent=tr('skip_select_at_least_one');st.style.color='var(--warn)';return;}
  btn.disabled=true; st.textContent=tr('skip_sending'); st.style.color='var(--txt2)';
  fetch(_apiUrl('/kx/skip'),{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({names:names})})
    .then(function(r){return r.json().then(function(j){return {ok:r.ok,j:j};});})
    .then(function(res){
      if(!res.ok){st.textContent=(res.j&&res.j.error)||'Fehler';st.style.color='var(--err)';btn.disabled=false;return;}
      st.textContent=tr('skip_success');st.style.color='var(--ok)';
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

function storeDownload(fileId){
  var a=document.createElement('a');
  a.href=_apiUrl('/kx/files/'+encodeURIComponent(fileId)+'/download');
  a.style.display='none';
  document.body.appendChild(a);
  a.click();
  a.remove();
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
