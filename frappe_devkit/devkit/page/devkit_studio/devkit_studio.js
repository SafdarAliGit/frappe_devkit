frappe.pages["devkit-studio"].on_page_load = function (wrapper) {
	frappe.ui.make_app_page({ parent: wrapper, title: "DevKit Studio", single_column: true });

	/* ── full-width CSS override via <style> tag (jQuery can't do !important) ── */
	if (!document.getElementById("dkst-fw")) {
		const fw = document.createElement("style");
		fw.id = "dkst-fw";
		fw.textContent = [
			"#page-devkit-studio .page-head { display:none !important; }",
			"#page-devkit-studio, #page-devkit-studio .page-wrapper,",
			"#page-devkit-studio .page-content,",
			"#page-devkit-studio .layout-main-section-wrapper,",
			"#page-devkit-studio .layout-main-section,",
			"#page-devkit-studio .layout-main,",
			"#page-devkit-studio .container,",
			"#page-devkit-studio .container-fluid,",
			"#page-devkit-studio .row,",
			"#page-devkit-studio .col-md-12,",
			"#page-devkit-studio .col-xs-12 {",
			"  padding: 0 !important; margin: 0 !important;",
			"  max-width: none !important; width: 100% !important;",
			"}",
			"#page-devkit-studio .layout-side-section { display:none !important; }",
			"#page-devkit-studio .page-content { overflow:hidden !important; }",
		].join("\n");
		document.head.appendChild(fw);
	}

	/* ── position root below navbar ── */
	const nukePadding = () => {
		const nb = document.querySelector(".navbar");
		const el = document.getElementById("dkst-root");
		if (nb && el) {
			el.style.top = nb.offsetHeight + "px";
		}
	};
	nukePadding();
	setTimeout(nukePadding, 50);
	setTimeout(nukePadding, 300);

	/* ── inject styles ── */
	if (!document.getElementById("dkst-css")) {
		const el = document.createElement("style");
		el.id = "dkst-css";
		el.textContent = `
/* ═══ RESET within scope ═══ */
.dkst-root * { box-sizing: border-box; margin: 0; padding: 0; }

/* ═══ ROOT SHELL — true 100vh ═══ */
.dkst-root {
  position: fixed;
  top: 0; left: 0; right: 0; bottom: 0;
  z-index: 100;
  display: flex;
  flex-direction: row;
  font-family: 'Segoe UI', system-ui, -apple-system, sans-serif;
  font-size: 13px;
  color: #1e1a2e;
  background: #f3f0fb;
  overflow: hidden;
  box-sizing: border-box;
}

/* ═══ SIDEBAR ═══ */
.dkst-sb {
  width: 230px;
  min-width: 230px;
  background: #2b1d52;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  border-right: 1px solid #1a1035;
}
.dkst-sb-logo {
  padding: 14px 16px 12px;
  border-bottom: 1px solid rgba(255,255,255,.08);
  flex-shrink: 0;
}
.dkst-sb-logo-title {
  font-size: 15px;
  font-weight: 700;
  color: #e0d8ff;
  letter-spacing: .01em;
  display: flex;
  align-items: center;
  gap: 8px;
}
.dkst-sb-logo-sub {
  font-size: 10.5px;
  color: #7060a8;
  margin-top: 2px;
  letter-spacing: .04em;
}
.dkst-sb-body {
  flex: 1;
  overflow-y: auto;
  padding: 8px 0 16px;
}
.dkst-sb-body::-webkit-scrollbar { width: 3px; }
.dkst-sb-body::-webkit-scrollbar-thumb { background: #4a3880; border-radius: 2px; }
.dkst-sb-section {
  padding: 14px 14px 3px;
  font-size: 10px;
  font-weight: 700;
  letter-spacing: .12em;
  text-transform: uppercase;
  color: #5a4888;
}
.dkst-sb-sep {
  height: 1px;
  background: rgba(255,255,255,.06);
  margin: 8px 12px;
}
.dkst-sb-item {
  display: flex;
  align-items: center;
  gap: 9px;
  padding: 8px 14px;
  cursor: pointer;
  color: #a898d0;
  font-size: 12.5px;
  border: none;
  background: none;
  width: 100%;
  text-align: left;
  border-left: 2px solid transparent;
  transition: all .12s;
  line-height: 1.3;
}
.dkst-sb-item:hover  { background: rgba(255,255,255,.06); color: #d4c8f8; }
.dkst-sb-item.active { background: rgba(124,100,200,.25); color: #fff; border-left-color: #9b7de0; font-weight: 500; }
.dkst-sb-item svg    { flex-shrink: 0; opacity: .7; }
.dkst-sb-item.active svg { opacity: 1; }
.dkst-sb-bottom {
  padding: 10px 14px;
  border-top: 1px solid rgba(255,255,255,.07);
  flex-shrink: 0;
  display: flex;
  align-items: center;
  justify-content: space-between;
}
.dkst-sb-ver { font-size: 10px; color: #5a4888; }

/* ═══ MAIN CONTENT ═══ */
.dkst-main {
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  background: #f8f6fe;
}

/* ═══ PANEL AREA ═══ */
.dkst-panel-area {
  flex: 1;
  overflow-y: auto;
  padding: 32px 40px 64px;
}
.dkst-panel-area::-webkit-scrollbar { width: 8px; }
.dkst-panel-area::-webkit-scrollbar-thumb { background: #c8bce8; border-radius: 4px; }

/* ═══ STATUS BAR ═══ */
.dkst-statusbar {
  height: 26px;
  background: #5c4da8;
  display: flex;
  align-items: center;
  padding: 0 14px;
  gap: 16px;
  font-size: 11.5px;
  color: rgba(255,255,255,.9);
  flex-shrink: 0;
}
.dkst-st-pill {
  display: flex;
  align-items: center;
  gap: 4px;
  padding: 0 6px;
  height: 100%;
  white-space: nowrap;
}
.dkst-st-pill:hover { background: rgba(255,255,255,.12); cursor: default; }

/* ═══ PANEL HEADER ═══ */
.dkst-phdr {
  margin-bottom: 22px;
  padding-bottom: 16px;
  border-bottom: 2px solid #e0d8f8;
  display: flex;
  align-items: flex-start;
  gap: 14px;
}
.dkst-phdr-icon {
  width: 42px; height: 42px;
  background: #ede8ff;
  border-radius: 8px;
  display: flex; align-items: center; justify-content: center;
  color: #5c4da8;
  flex-shrink: 0;
}
.dkst-phdr-text {}
.dkst-ptitle { font-size: 20px; font-weight: 700; color: #1e1a2e; margin-bottom: 3px; }
.dkst-psub   { font-size: 12.5px; color: #7a70a8; line-height: 1.5; }

/* ═══ CARDS ═══ */
.dkst-card {
  background: #ffffff;
  border: 1px solid #e0d8f0;
  border-radius: 8px;
  padding: 20px 22px;
  margin-bottom: 16px;
  box-shadow: 0 1px 4px rgba(92,77,168,.06);
}
.dkst-card-title {
  font-size: 11px;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: .1em;
  color: #5c4da8;
  margin-bottom: 16px;
  display: flex;
  align-items: center;
  gap: 8px;
  padding-bottom: 10px;
  border-bottom: 1px solid #f0ebff;
}

/* ═══ GRID ═══ */
.dkst-g2 { display: grid; grid-template-columns: 1fr 1fr; gap: 16px; }
.dkst-g3 { display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 16px; }
.dkst-g4 { display: grid; grid-template-columns: 1fr 1fr 1fr 1fr; gap: 16px; }
.dkst-span2 { grid-column: span 2; }
.dkst-full  { grid-column: 1 / -1; }

/* ═══ FORM FIELDS ═══ */
.dkst-fld   { display: flex; flex-direction: column; gap: 5px; }
.dkst-lbl   {
  font-size: 11.5px; font-weight: 600;
  color: #4a4470; letter-spacing: .02em;
  display: flex; align-items: center; gap: 4px;
}
.dkst-req::after { content: ' *'; color: #7c4da8; font-weight: 700; }
.dkst-hint  { font-size: 11px; color: #9890c0; margin-top: 2px; line-height: 1.4; }

.dkst-inp, .dkst-sel, .dkst-ta {
  width: 100%;
  padding: 8px 11px;
  border: 1px solid #d0c8e8;
  border-radius: 5px;
  background: #fdfdff;
  color: #1e1a2e;
  font-size: 13px;
  font-family: inherit;
  outline: none;
  box-sizing: border-box;
  transition: border-color .15s, box-shadow .15s;
  line-height: 1.4;
}
.dkst-inp:focus, .dkst-sel:focus, .dkst-ta:focus {
  border-color: #7c5cbf;
  box-shadow: 0 0 0 3px rgba(124,92,191,.14);
  background: #fff;
}
.dkst-inp:disabled, .dkst-sel:disabled {
  background: #f4f2f9;
  color: #9890c0;
  cursor: not-allowed;
  border-color: #e0d8f0;
}
.dkst-inp::placeholder { color: #b0a8d0; }
.dkst-ta { resize: vertical; min-height: 76px; }
.dkst-sel option { background: #fff; color: #1e1a2e; }

/* ═══ FIELD TABLE ═══ */
.dkst-tbl-wrap { overflow-x: auto; }
.dkst-tbl { width: 100%; border-collapse: collapse; min-width: 700px; }
.dkst-tbl thead tr { background: #f4f0fc; }
.dkst-tbl th {
  padding: 8px 10px;
  text-align: left;
  font-size: 11px;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: .07em;
  color: #7060a8;
  border-bottom: 2px solid #e0d8f0;
  white-space: nowrap;
}
.dkst-tbl td {
  padding: 5px 4px;
  border-bottom: 1px solid #f0ebfa;
  vertical-align: middle;
}
.dkst-tbl tbody tr:hover td { background: #faf8ff; }
.dkst-tbl .dkst-inp, .dkst-tbl .dkst-sel { padding: 6px 8px; font-size: 12px; }
.dkst-add-row {
  display: flex; align-items: center; justify-content: center; gap: 6px;
  margin-top: 10px; padding: 8px 12px;
  border: 1.5px dashed #c8bce8; border-radius: 6px;
  cursor: pointer; color: #9080c0; font-size: 12.5px;
  transition: all .15s;
}
.dkst-add-row:hover { border-color: #7c5cbf; color: #5c4da8; background: #f8f4ff; }
.dkst-del-btn {
  background: none; border: none; cursor: pointer;
  color: #b0a8c8; font-size: 16px; padding: 3px 6px;
  border-radius: 4px; line-height: 1; transition: all .12s;
}
.dkst-del-btn:hover { color: #c0392b; background: #fde8e6; }

/* ═══ CHECKBOXES ═══ */
.dkst-checks { display: flex; flex-wrap: wrap; gap: 10px 22px; padding: 2px 0; }
.dkst-chk {
  display: flex; align-items: center; gap: 7px;
  cursor: pointer; font-size: 12.5px;
  color: #3a3460; user-select: none;
}
.dkst-chk input[type=checkbox] {
  width: 15px; height: 15px;
  accent-color: #5c4da8; cursor: pointer;
  border-radius: 3px;
}

/* ═══ OPEN-IN-EDITOR LINK ═══ */
.dkst-ce-link {
  display: none; align-items: center; gap: 4px;
  padding: 2px 9px; border-radius: 20px;
  background: linear-gradient(135deg, #5c4da8 0%, #8b5cf6 100%);
  color: #fff; font-size: 10px; font-weight: 700; letter-spacing: .04em;
  cursor: pointer; border: none; font-family: inherit;
  box-shadow: 0 2px 8px rgba(92,77,168,.40);
  transition: box-shadow .15s, transform .15s, background .15s;
  white-space: nowrap; text-transform: uppercase;
}
.dkst-ce-link:hover {
  background: linear-gradient(135deg, #7c5cbf 0%, #a78bfa 100%);
  box-shadow: 0 3px 14px rgba(139,92,246,.55);
  transform: translateY(-1px);
}
.dkst-ce-link:active { transform: translateY(0); box-shadow: 0 1px 5px rgba(92,77,168,.30); }
.dkst-ce-link.visible { display: inline-flex; }

/* ═══ BUTTONS ═══ */
.dkst-btnrow { display: flex; gap: 10px; margin-top: 20px; flex-wrap: wrap; align-items: center; }
.dkst-btn {
  padding: 8px 20px; border-radius: 5px;
  font-size: 13px; font-weight: 600;
  cursor: pointer; border: 1.5px solid transparent;
  font-family: inherit; transition: all .15s;
  display: inline-flex; align-items: center; gap: 6px;
  line-height: 1.3;
}
.dkst-btn-p  { background: #5c4da8; color: #fff; border-color: #5c4da8; }
.dkst-btn-p:hover { background: #7c5cbf; border-color: #7c5cbf; }
.dkst-btn-s  { background: #fff; color: #4a4470; border-color: #c8bce8; }
.dkst-btn-s:hover { border-color: #7c5cbf; color: #5c4da8; background: #f8f4ff; }
.dkst-btn-g  { background: #1a7a3a; color: #fff; border-color: #1a7a3a; }
.dkst-btn-g:hover { background: #1e8f44; border-color: #1e8f44; }
.dkst-btn-r  { background: #fff; color: #c0392b; border-color: #e8a8a0; }
.dkst-btn-r:hover { background: #fde8e6; border-color: #c0392b; }
.dkst-btn:disabled { opacity: .45; cursor: not-allowed; }

/* ═══ SUB-TABS ═══ */
.dkst-stabs {
  display: flex; border-bottom: 2px solid #e0d8f0;
  margin-bottom: 18px; gap: 0;
}
.dkst-stab {
  padding: 9px 20px; cursor: pointer;
  font-size: 12.5px; font-weight: 500;
  color: #9080b8; border-bottom: 2px solid transparent;
  margin-bottom: -2px; transition: all .12s;
}
.dkst-stab:hover  { color: #4a4470; }
.dkst-stab.active { color: #5c4da8; border-bottom-color: #5c4da8; font-weight: 600; }
.dkst-spanel { display: none; }
.dkst-spanel.active { display: block; }

/* ═══ TERMINAL ═══ */
.dkst-term {
  background: #16112a;
  border: 1px solid #2c2250;
  border-radius: 6px;
  padding: 14px 16px;
  font-family: 'Consolas','Cascadia Code','Courier New',monospace;
  font-size: 12.5px; line-height: 1.7;
  white-space: pre-wrap; max-height: 220px; overflow-y: auto;
  color: #c0b8e8; margin-top: 16px;
  box-shadow: inset 0 2px 8px rgba(0,0,0,.2);
}
.dkst-term:before { content: "OUTPUT  "; font-size: 10px; letter-spacing: .1em; color: #5a4888; display: block; margin-bottom: 4px; }
.dkst-term.ok  { border-color: #2a6040; color: #7ec89a; }
.dkst-term.err { border-color: #6a2020; color: #f08080; }
.dkst-term::-webkit-scrollbar { width: 5px; }
.dkst-term::-webkit-scrollbar-thumb { background: #3a2a60; border-radius: 3px; }

/* ═══ BADGE PILLS ═══ */
.dkst-pill { display: inline-flex; align-items: center; padding: 2px 9px; border-radius: 3px; font-size: 11px; font-weight: 700; }
.dkst-pill-p { background: #ede8ff; color: #5c4da8; }
.dkst-pill-g { background: #dff0e0; color: #1a7a3a; }
.dkst-pill-b { background: #e0eeff; color: #0055cc; }
.dkst-pill-y { background: #fff4cc; color: #7a5c00; }
.dkst-pill-r { background: #fde8e6; color: #c0392b; }

/* ═══ LOG TABLE ═══ */
.dkst-log-tbl { width: 100%; border-collapse: collapse; font-size: 12.5px; }
.dkst-log-tbl th {
  padding: 9px 14px; text-align: left;
  background: #f4f0fc; color: #7060a8;
  font-size: 11px; font-weight: 700;
  text-transform: uppercase; letter-spacing: .07em;
  border-bottom: 2px solid #e0d8f0;
}
.dkst-log-tbl td {
  padding: 10px 14px;
  border-bottom: 1px solid #f0ebfa;
  vertical-align: middle;
}
.dkst-log-tbl tbody tr:hover td { background: #faf8ff; }

/* ═══ WELCOME ═══ */
.dkst-wcard {
  cursor: pointer;
  transition: border-color .15s, box-shadow .15s, transform .12s;
}
.dkst-wcard:hover {
  border-color: #7c5cbf !important;
  box-shadow: 0 4px 16px rgba(92,77,168,.14) !important;
  transform: translateY(-1px);
}

/* ═══ DIVIDER ═══ */
.dkst-div { height: 1px; background: #e8e0f8; margin: 14px 0; }

/* ═══ EMPTY STATE ═══ */
.dkst-empty { text-align: center; padding: 56px 0; color: #9080b8; font-size: 13px; }

/* ═══ SPINNER ═══ */
.dkst-spin {
  display: inline-block; width: 13px; height: 13px;
  border: 2px solid rgba(255,255,255,.35); border-top-color: #fff;
  border-radius: 50%; animation: dkst-s .5s linear infinite;
}
@keyframes dkst-s { to { transform: rotate(360deg); } }

/* ═══ SECTION LABEL ═══ */
.dkst-sec-lbl {
  font-size: 10.5px; font-weight: 700; text-transform: uppercase;
  letter-spacing: .1em; color: #9080b8; margin-bottom: 10px;
  display: flex; align-items: center; gap: 8px;
}
.dkst-sec-lbl::after { content: ''; flex: 1; height: 1px; background: #e8e0f8; }

/* ═══ INFO BOX ═══ */
.dkst-info {
  background: #f0ecff; border: 1px solid #d8d0f0; border-radius: 5px;
  padding: 10px 14px; font-size: 12px; color: #4a4070;
  margin-bottom: 14px; line-height: 1.6;
}
.dkst-info-icon { color: #7c5cbf; font-weight: 700; margin-right: 4px; }

/* ═══ INLINE CODE ═══ */
.dkst-code { font-family: 'Consolas','Courier New',monospace; font-size: 12px; background: #f0ecff; color: #5c4da8; padding: 1px 5px; border-radius: 3px; }
`;
		document.head.appendChild(el);
	}

	/* ══════════════════════════════════════════════
	   DATA LOADING — live from Frappe DB
	   ══════════════════════════════════════════════ */
	let _apps=[], _mods={}, _dts={};

	function loadApps() {
		if (_apps.length) return Promise.resolve();
		return frappe.call({ method:"frappe.client.get_list",
			args:{ doctype:"Module Def", fields:["app_name"], limit_page_length:300 }
		}).then(r => {
			const seen=new Set();
			(r.message||[]).forEach(m => { if(m.app_name&&!seen.has(m.app_name)){ seen.add(m.app_name); _apps.push(m.app_name); } });
		});
	}
	function loadMods(app) {
		if (_mods[app]) return Promise.resolve(_mods[app]);
		return frappe.call({ method:"frappe.client.get_list",
			args:{ doctype:"Module Def", fields:["module_name"], filters:[["app_name","=",app]], limit_page_length:100 }
		}).then(r => { _mods[app]=(r.message||[]).map(m=>m.module_name); return _mods[app]; });
	}
	function loadDts(mod) {
		if (_dts[mod]) return Promise.resolve(_dts[mod]);
		return frappe.call({ method:"frappe.client.get_list",
			args:{ doctype:"DocType", fields:["name"], filters:[["module","=",mod]], limit_page_length:500 }
		}).then(r => { _dts[mod]=(r.message||[]).map(d=>d.name); return _dts[mod]; });
	}
	function fillSel(el, items, ph) {
		$(el).empty();
		if (ph) $(`<option value="">— ${ph} —</option>`).appendTo(el);
		items.forEach(v => $(`<option value="${v}">${v}</option>`).appendTo(el));
	}
	function wireAMD($scope, aId, mId, dId) {
		loadApps().then(() => fillSel($scope.find(`#${aId}`), _apps, "select app"));
		$scope.find(`#${aId}`).on("change", function() {
			const app=this.value;
			const $m=$scope.find(`#${mId}`);
			$m.prop("disabled",!app).html('<option value="">— select module —</option>');
			if (dId) $scope.find(`#${dId}`).prop("disabled",true).html('<option value="">— select doctype —</option>');
			if (!app) return;
			loadMods(app).then(ms => { fillSel($m,ms,"select module"); $m.prop("disabled",false); });
		});
		if (mId && dId) {
			$scope.find(`#${mId}`).on("change", function() {
				const mod=this.value;
				const $d=$scope.find(`#${dId}`);
				$d.prop("disabled",!mod).html('<option value="">— select doctype —</option>');
				if (!mod) return;
				loadDts(mod).then(ds => { fillSel($d,ds,"select doctype"); $d.prop("disabled",false); });
			});
		}
	}

	/* ══════════════════════════════════════════════
	   BUILD SHELL
	   ══════════════════════════════════════════════ */
	/* Mount to body so position:fixed works regardless of Frappe container heights */
	$("#dkst-root").remove(); // remove any stale instance
	const $root = $('<div class="dkst-root" id="dkst-root"></div>').appendTo("body");

	/* ── Sidebar ── */
	const $sb = $(`<div class="dkst-sb"></div>`).appendTo($root);
	$(`<div class="dkst-sb-logo">
		<div class="dkst-sb-logo-title">${icoLogo(20)}&nbsp;DevKit Studio</div>
		<div class="dkst-sb-logo-sub">Frappe / ERPNext Developer Assistant</div>
	</div>`).appendTo($sb);
	const $sbBody = $(`<div class="dkst-sb-body"></div>`).appendTo($sb);
	$(`<div class="dkst-sb-bottom">
		<span class="dkst-sb-ver">v1.0 · ERPNext 15</span>
	</div>`).appendTo($sb);

	/* ── Main ── */
	const $main   = $(`<div class="dkst-main"></div>`).appendTo($root);
	const $panels  = $(`<div class="dkst-panel-area" id="dkst-panels"></div>`).appendTo($main);
	$(`<div class="dkst-statusbar">
		<span class="dkst-st-pill">${icoBolt(12)}&nbsp;<span id="dkst-stmsg">Ready</span></span>
		<span style="flex:1"></span>
		<span class="dkst-st-pill">${icoCode(12)}&nbsp;Python · JS · JSON</span>
		<span class="dkst-st-pill">Frappe v15</span>
		<span class="dkst-st-pill">ERPNext v15</span>
	</div>`).appendTo($main);

	/* ══════════════════════════════════════════════
	   SIDEBAR NAV
	   ══════════════════════════════════════════════ */
	const NAV = [
		{ sec:"Scaffold" },
		{ id:"app",       lbl:"New App",           ico:icoBox()      },
		{ id:"doctype",   lbl:"DocType",            ico:icoFile()     },
		{ id:"child",     lbl:"Child Table",        ico:icoGrid()     },
		{ id:"single",    lbl:"Single / Settings",  ico:icoSettings() },
		{ id:"report",    lbl:"Report",             ico:icoChart()    },
		{ id:"print_fmt", lbl:"Print Format",       ico:icoPrint()    },
		{ sep:true },
		{ sec:"Customize" },
		{ id:"custom_field",  lbl:"Custom Field",   ico:icoSliders()  },
		{ id:"property",      lbl:"Property Setter",ico:icoEdit()     },
		{ id:"client_script", lbl:"Client Script",  ico:icoCode()     },
		{ sep:true },
		{ sec:"Dev Tools" },
		{ id:"hook",     lbl:"Add Hook",            ico:icoLink()     },
		{ id:"override", lbl:"Override File",       ico:icoCode()     },
		{ id:"patch",    lbl:"Patch",               ico:icoBolt()     },
		{ id:"tasks",    lbl:"Tasks / Scheduler",   ico:icoClock()    },
		{ id:"perms",    lbl:"Permissions",         ico:icoShield()   },
		{ sep:true },
		{ sec:"Utilities" },
		{ id:"migrate",  lbl:"Migrate & Cache",     ico:icoRefresh()  },
		{ id:"export",   lbl:"Export Fixtures",     ico:icoExport()   },
		{ id:"log",      lbl:"Scaffold Log",        ico:icoList()     },
		{ sep:true },
		{ sec:"Advanced" },
		{ id:"module",       lbl:"New Module",          ico:icoFolder()   },
		{ id:"workspace",    lbl:"Workspace",           ico:icoLayout()   },
		{ id:"dashboard_chart", lbl:"Dashboard Chart",  ico:icoChart()    },
		{ id:"number_card",  lbl:"Number Card",         ico:icoHash()     },
		{ id:"notification", lbl:"Notification",        ico:icoBell()     },
		{ id:"server_script",lbl:"Server Script",       ico:icoTerminal() },
		{ id:"role_perm",    lbl:"Role Permissions",    ico:icoShield()   },
		{ sep:true },
		{ sec:"Inspector" },
		{ id:"dt_inspector", lbl:"DocType Inspector",   ico:icoSearch()   },
		{ id:"health_check", lbl:"App Health Check",    ico:icoHeart()    },
		{ id:"fixture_diff",  lbl:"Fixture Diff",        ico:icoDiff()     },
		{ sep:true },
		{ sec:"App Manager" },
		{ id:"app_manager",   lbl:"App Manager",         ico:icoPackage()  },
		{ sep:true },
		{ sec:"Code Editor" },
		{ id:"code_editor",   lbl:"Open Code Editor",    ico:icoCode()     },
		{ sep:true },
		{ sec:"Site Manager" },
		{ id:"site_overview", lbl:"Site Overview",       ico:icoGlobe()    },
		{ id:"site_create",   lbl:"Create Site",         ico:icoPlus()     },
		{ id:"site_backup",   lbl:"Backup & Restore",    ico:icoSave()     },
		{ id:"site_config",   lbl:"Site Config",         ico:icoSliders()  },
		{ id:"site_apps",     lbl:"Install / Remove Apps",ico:icoPackage() },
		{ id:"site_ops",      lbl:"Operations",          ico:icoTools()    },
	];

	NAV.forEach(n => {
		if (n.sec) { $(`<div class="dkst-sb-section">${n.sec}</div>`).appendTo($sbBody); return; }
		if (n.sep) { $(`<div class="dkst-sb-sep"></div>`).appendTo($sbBody); return; }
		$(`<button class="dkst-sb-item" data-id="${n.id}">${n.ico}<span>${n.lbl}</span></button>`)
			.appendTo($sbBody).on("click", () => activatePanel(n.id));
	});

	function activatePanel(id) {
		$sbBody.find(".dkst-sb-item").removeClass("active");
		$sbBody.find(`[data-id="${id}"]`).addClass("active");
		$panels.empty();
		setStatus(`${NAV.find(n=>n.id===id)?.lbl||id}`);
		PANELS[id]?.($panels);
	}
	function setStatus(msg) { $("#dkst-stmsg").text(msg); }

	/* ══════════════════════════════════════════════
	   HELPERS
	   ══════════════════════════════════════════════ */
	function phdr(title, sub, icon) {
		return `<div class="dkst-phdr">
			<div class="dkst-phdr-icon">${icon||icoFile(20)}</div>
			<div class="dkst-phdr-text">
				<div class="dkst-ptitle">${title}</div>
				<div class="dkst-psub">${sub}</div>
			</div>
		</div>`;
	}
	function card($p, title) {
		const $c=$(`<div class="dkst-card"></div>`).appendTo($p);
		if(title) $(`<div class="dkst-card-title">${title}</div>`).appendTo($c);
		return $c;
	}
	function info(msg) { return `<div class="dkst-info"><span class="dkst-info-icon">ℹ</span>${msg}</div>`; }
	function secLbl(t) { return `<div class="dkst-sec-lbl">${t}</div>`; }

	/* form field builders */
	function F(id,lbl,type,ph,cls="",opts=[]) {
		if(type==="select") return `<div class="dkst-fld ${cls}"><label class="dkst-lbl">${lbl}</label>
			<select class="dkst-sel" id="${id}">${opts.map(([v,l])=>`<option value="${v}">${l}</option>`).join("")}</select></div>`;
		if(type==="textarea") return `<div class="dkst-fld ${cls}"><label class="dkst-lbl">${lbl}</label>
			<textarea class="dkst-ta" id="${id}" placeholder="${ph}"></textarea></div>`;
		return `<div class="dkst-fld ${cls}"><label class="dkst-lbl">${lbl}</label>
			<input class="dkst-inp" type="${type}" id="${id}" placeholder="${ph}"></div>`;
	}
	function FR(id,lbl,type,ph,opts=[]) { // required variant
		if(type==="select") return `<div class="dkst-fld"><label class="dkst-lbl dkst-req">${lbl}</label>
			<select class="dkst-sel" id="${id}">${opts.map(([v,l])=>`<option value="${v}">${l}</option>`).join("")}</select></div>`;
		return `<div class="dkst-fld"><label class="dkst-lbl dkst-req">${lbl}</label>
			<input class="dkst-inp" type="${type}" id="${id}" placeholder="${ph}"></div>`;
	}
	function AppSel(id) { return `<div class="dkst-fld">
		<div style="display:flex;align-items:center;justify-content:space-between;gap:8px;margin-bottom:5px;">
			<label class="dkst-lbl dkst-req" style="margin:0;">App</label>
			<button class="dkst-ce-link" data-app-sel="${id}" title="Open this app in DevKit Code Editor">⌨ Open in Editor ↗</button>
		</div>
		<select class="dkst-sel" id="${id}"><option value="">— select app —</option></select></div>`; }
	function ModSel(id) { return `<div class="dkst-fld"><label class="dkst-lbl dkst-req">Module</label>
		<select class="dkst-sel" id="${id}" disabled><option value="">— select module —</option></select></div>`; }
	function DtSel(id, lbl="DocType") { return `<div class="dkst-fld"><label class="dkst-lbl">${lbl}</label>
		<select class="dkst-sel" id="${id}" disabled><option value="">— select doctype —</option></select></div>`; }
	function CHK(id,lbl,def=0) { return `<label class="dkst-chk"><input type="checkbox" id="${id}" ${def?"checked":""}><span>${lbl}</span></label>`; }

	function gv(id)  { return ($(`#${id}`).val()||"").trim(); }
	function gc(id)  { return $(`#${id}`).is(":checked"); }

	function term($p) {
		return $(`<div class="dkst-term">▶  Ready — waiting for command.</div>`).appendTo($p);
	}
	function btns($p, list) {
		const $r=$(`<div class="dkst-btnrow"></div>`).appendTo($p);
		list.forEach(b => {
			const $b=$(`<button class="dkst-btn ${b.cls}">${b.lbl}</button>`).appendTo($r);
			$b.on("click", () => {
				$b.html(`<span class="dkst-spin"></span> Working…`).prop("disabled",true);
				setTimeout(() => { try { b.fn(); } catch(e){console.error(e);} }, 60);
				setTimeout(() => { $b.html(b.lbl).prop("disabled",false); }, 5000);
			});
		});
	}
	function api(method, args, $t) {
		$t.text(`▶  Calling ${method.split(".").pop()}() …`).removeClass("ok err");
		frappe.call({ method, args,
			callback: r => {
				const m=r.message;
				if (m?.status==="success") {
					$t.addClass("ok");
					let out=`✓  ${m.message||"Done"}`;
					if (m.importable)           out+=`\n\nimportable: ${m.importable}`;
					if (m.bench_apps_txt)       out+=`\n${m.bench_apps_txt}`;
					if (m.sites_apps_txt)       out+=`\n${m.sites_apps_txt}`;
					if (m.bench_txt)            out+=`\nbench/apps.txt: ${m.bench_txt}`;
					if (m.apps_txt)             out+=`\napps.txt: ${m.apps_txt}`;
					if (m.apps_json)            out+=`\n${m.apps_json}`;
					if (m.next_steps)           out+=`\n\nNext steps:\n${m.next_steps}`;
					if (m.stdout?.trim())       out+=`\n\nOutput:\n${m.stdout.trim()}`;
					if (m.stderr?.trim())       out+=`\n\nStderr:\n${m.stderr.trim()}`;
					if (m.files?.length)        out+=`\n\nFiles created:\n`+m.files.map(f=>`   ${f}`).join("\n");
					if (m.path)                 out+=`\nPath: ${m.path}`;
					if (m.patches_txt)          out+=`\nPatches: ${m.patches_txt}`;
					if (m.summary)              out+=`\n\n${m.summary}`;
					$t.text(out);
					setStatus(`✓  ${m.message||"Done"}`);
					frappe.show_alert({message:m.message||"Done",indicator:"green"});
				} else if (m?.status==="exists") {
					$t.text(`ℹ  ${m.message}`);
				} else {
					// Show full bench error output — critical for debugging install failures
					$t.addClass("err");
					let out=`✗  ${m?.message||"Error"}`;
					if (m?.importable)          out+=`\n\nimportable: ${m.importable}`;
					if (m?.bench_txt)           out+=`\nbench/apps.txt: ${m.bench_txt}`;
					if (m?.stdout?.trim())      out+=`\n\nCommand output:\n${m.stdout.trim()}`;
					if (m?.stderr?.trim())      out+=`\n\nStderr:\n${m.stderr.trim()}`;
					if (!m?.stdout && !m?.stderr) out+=`\n\n${JSON.stringify(m,null,2)}`;
					$t.text(out);
					setStatus(`✗  ${m?.message||"Error"}`);
				}
			},
			error: e => {
				$t.addClass("err").text(`✗  ${e.responseJSON?.exception||JSON.stringify(e)}`);
				setStatus("Error");
			}
		});
	}

	const FT_ALL = ["Data","Link","Select","Check","Currency","Float","Int","Percent",
		"Date","Datetime","Time","Text","Small Text","Long Text","Text Editor","Code",
		"HTML Editor","Markdown Editor","Password","Attach","Attach Image","Table",
		"Table MultiSelect","Section Break","Column Break","Tab Break","Heading",
		"HTML","Button","Barcode","Color","Duration","Geolocation","JSON","Rating",
		"Signature","Read Only","Dynamic Link","Image","Phone"];

	const FT_MINI = ["Data","Link","Date","Datetime","Select","Check","Currency","Float",
		"Int","Percent","Text","Small Text","Attach","Attach Image","Phone"];

	const NAMING_OPTS = [["By fieldname","By fieldname"],['By "Naming Series" field','By Naming Series field'],
		["Autoincrement","Autoincrement"],["Expression","Expression"],["Random","Random"],["Set by user","Set by user"]];

	const DOC_EVENTS = [["validate","validate"],["before_save","before_save"],["on_update","on_update"],
		["before_insert","before_insert"],["after_insert","after_insert"],["on_submit","on_submit"],
		["before_submit","before_submit"],["on_cancel","on_cancel"],["before_cancel","before_cancel"],
		["on_update_after_submit","on_update_after_submit"],["on_trash","on_trash"],
		["after_delete","after_delete"],["has_permission","has_permission"],["before_rename","before_rename"],
		["after_rename","after_rename"],["on_change","on_change"]];

	/* ══════════════════════════════════════════════
	   PANELS
	   ══════════════════════════════════════════════ */
	const PANELS = {};

	/* ── Code Editor (external page) ── */
	PANELS["code_editor"] = function($p) {
		$p.html(`<div style="max-width:480px;margin:80px auto;text-align:center;">
			<div style="font-size:48px;margin-bottom:16px">⌨</div>
			<div style="font-size:22px;font-weight:700;color:#1e1a2e;margin-bottom:10px">DevKit Code Editor</div>
			<div style="font-size:14px;color:#7a70a8;margin-bottom:28px">
				A professional VS Code-like editor for Python, JS, HTML, CSS and more.<br>
				Browse your app's file tree, edit code with Monaco Editor, and save directly.
			</div>
			<button class="dkst-btn-p" id="dkst-open-ce" style="padding:10px 28px;font-size:14px;">
				🚀 Open Code Editor
			</button>
		</div>`);
		$p.find("#dkst-open-ce").on("click", () => frappe.set_route("devkit-code-editor"));
	};

	/* ── Welcome (initial) ── */
	function showWelcome() {
		$panels.empty();
		const $w=$(`<div style="max-width:640px;margin:48px auto;"></div>`).appendTo($panels);
		$w.append(`<div style="text-align:center;margin-bottom:36px;">
			<div style="color:#5c4da8;margin-bottom:14px">${icoLogo(52)}</div>
			<div style="font-size:28px;font-weight:800;color:#1e1a2e;margin-bottom:6px">DevKit Studio</div>
			<div style="font-size:14px;color:#7a70a8;line-height:1.7">Your personal Frappe / ERPNext developer assistant.<br>Select a tool from the Explorer sidebar to begin.</div>
		</div>`);
		const $g=$(`<div style="display:grid;grid-template-columns:1fr 1fr;gap:16px;"></div>`).appendTo($w);
		[
			["DocType Builder",    "Scaffold regular, child, single or tree DocTypes with full controller, JS and list view.", "doctype",      icoFile(22)],
			["Report Builder",     "Create Script or Query reports with filters, columns and auto-generated Python stubs.",    "report",       icoChart(22)],
			["Custom Field",       "Add custom fields to any existing DocType via app fixtures — no direct DB changes.",       "custom_field", icoSliders(22)],
			["Hooks Manager",      "Register doc_events, scheduler tasks, class overrides and permission handlers.",           "hook",         icoLink(22)],
			["Patch Builder",      "Scaffold one-time migration patches that run automatically during bench migrate.",         "patch",        icoBolt(22)],
			["Scaffold Log",       "View the complete history of all files generated by DevKit Studio.",                       "log",          icoList(22)],
		].forEach(([t,d,id,ico]) => {
			$(`<div class="dkst-card dkst-wcard" data-id="${id}" style="border-left:3px solid #7c5cbf;">
				<div style="display:flex;align-items:center;gap:10px;color:#5c4da8;font-weight:700;font-size:14px;margin-bottom:8px">${ico}&nbsp;${t}</div>
				<div style="font-size:12.5px;color:#6a6090;line-height:1.6">${d}</div>
			</div>`).appendTo($g).on("click",function(){ activatePanel($(this).data("id")); });
		});
	}

	/* ── New App ── */
	PANELS.app = function($p) {
		$p.append(phdr("New App","Scaffold a complete Frappe app boilerplate inside bench/apps/.",icoBox(20)));
		$p.append(info("Creates <span class='dkst-code'>hooks.py</span>, <span class='dkst-code'>setup.py</span>, <span class='dkst-code'>pyproject.toml</span>, module folder, fixtures/, overrides/ and all standard files."));
		const $c=card($p,"App Identity");
		$c.append(`<div class="dkst-g2">
			${FR("na_n","App Name (snake_case)","text","my_textile_app")}
			${FR("na_t","App Title","text","My Textile App")}
			${FR("na_p","Publisher","text","Safdar")}
			${F("na_e","Email","email","you@example.com")}
			${F("na_l","License","select","","",[["MIT","MIT"],["GNU GPL","GNU GPL"],["AGPL","AGPL"],["Proprietary","Proprietary"]])}
			${F("na_v","Version","text","0.0.1")}
			<div class="dkst-fld dkst-full">${FR("na_d","Description","text","Short description of your app")}</div>
			<div class="dkst-fld dkst-full"><label class="dkst-lbl">Required Apps (comma-separated)</label>
				<input class="dkst-inp" id="na_r" value="frappe,erpnext">
				<span class="dkst-hint">e.g. frappe,erpnext — these apps must be installed before this one</span></div>
		</div>`);
		const $t=term($p);
		btns($p,[{ lbl:"Generate App", cls:"dkst-btn-p", fn:()=>{
			if(!gv("na_n")||!gv("na_t")||!gv("na_p")){frappe.throw("Name, Title, Publisher required");return;}
			api("frappe_devkit.api.app_builder.scaffold_app",{
				app_name:gv("na_n"),app_title:gv("na_t"),app_publisher:gv("na_p"),
				app_description:gv("na_d"),app_email:gv("na_e"),
				app_license:gv("na_l")||"MIT",app_version:gv("na_v")||"0.0.1",
				required_apps:JSON.stringify(gv("na_r").split(",").map(s=>s.trim()).filter(Boolean))
			},$t);
		}}]);
	};

	/* ── DocType builder (shared) ── */
	function buildDT($p, mode) {
		const cfg = {
			normal:{ title:"DocType Builder",        sub:"Generate DocType with Python controller, JS client file and List View.",    ico:icoFile(20) },
			child :{ title:"Child Table Builder",     sub:"Generate a child table DocType used as Table fields inside parent DocTypes.", ico:icoGrid(20) },
			single:{ title:"Single / Settings Builder",sub:"Generate a singleton Settings-style DocType.",                             ico:icoSettings(20) },
		}[mode];
		$p.append(phdr(cfg.title, cfg.sub, cfg.ico));

		const $c1=card($p,"Identity & Naming");

		// ── Load existing DocType to edit ──────────────────
		const $loadBar = $(`<div class="dkst-info" style="margin-bottom:14px;display:flex;align-items:center;gap:10px;flex-wrap:wrap">
			<span style="font-weight:600;color:#4a4070;white-space:nowrap">📂 Load existing DocType:</span>
			<select class="dkst-sel" id="dt-load-mod" style="width:160px" disabled><option value="">— select module —</option></select>
			<select class="dkst-sel" id="dt-load-dt"  style="width:200px" disabled><option value="">— select doctype —</option></select>
			<button class="dkst-btn dkst-btn-s" id="dt-load-btn" style="padding:6px 14px;font-size:12px" disabled>Load →</button>
			<span id="dt-load-status" style="font-size:12px;color:#9080b8"></span>
		</div>`).appendTo($c1);

		// Populate module dropdown from all installed modules
		frappe.call({ method:"frappe.client.get_list",
			args:{ doctype:"Module Def", fields:["module_name","app_name"], limit_page_length:300, order_by:"module_name asc" },
			callback: r => {
				const $ms = $c1.find("#dt-load-mod");
				$ms.prop("disabled", false);
				(r.message||[]).forEach(m =>
					$ms.append(`<option value="${m.module_name}">${m.module_name} (${m.app_name})</option>`)
				);
			}
		});

		// When module selected → load doctypes for that module
		$c1.find("#dt-load-mod").on("change", function() {
			const mod = this.value;
			const $dt = $c1.find("#dt-load-dt");
			$dt.html('<option value="">— select doctype —</option>').prop("disabled", !mod);
			$c1.find("#dt-load-btn").prop("disabled", true);
			if (!mod) return;
			frappe.call({ method:"frappe.client.get_list",
				args:{ doctype:"DocType", fields:["name"], filters:[["module","=",mod]], limit_page_length:500, order_by:"name asc" },
				callback: r => {
					(r.message||[]).forEach(d => $dt.append(`<option value="${d.name}">${d.name}</option>`));
					$dt.prop("disabled", false);
				}
			});
		});

		// Enable Load button when doctype selected
		$c1.find("#dt-load-dt").on("change", function() {
			$c1.find("#dt-load-btn").prop("disabled", !this.value);
		});

		// Load button → fetch full meta and populate all form fields
		$c1.find("#dt-load-btn").on("click", function() {
			const dtName = $c1.find("#dt-load-dt").val();
			if (!dtName) return;
			const $status = $c1.find("#dt-load-status");
			$status.text("Loading…");
			$(this).prop("disabled", true);
			const $btn = $(this);

			frappe.call({ method:"frappe.client.get",
				args:{ doctype:"DocType", name:dtName },
				callback: r => {
					$btn.prop("disabled", false);
					const d = r.message;
					if (!d) { $status.text("Not found"); return; }

					// ── Populate Identity fields ──────────────────
					$("#dt_nm").val(d.name);
					$("#dt_nr").val(d.naming_rule || "By fieldname");
					$("#dt_au").val(d.autoname || "");
					$("#dt_tf").val(d.title_field || "");
					$("#dt_sf").val(d.search_fields || "");
					$("#dt_so").val(d.sort_field || "modified");

					// ── Populate Flags ────────────────────────────
					$("#dt_sub").prop("checked", !!d.is_submittable);
					$("#dt_edg").prop("checked", !!d.editable_grid);
					$("#dt_isg").prop("checked", !!d.issingle);
					$("#dt_tre").prop("checked", !!d.is_tree);
					$("#dt_qe").prop("checked",  !!d.quick_entry);
					$("#dt_trk").prop("checked", !!d.track_changes);
					$("#dt_trs").prop("checked", !!d.track_seen);
					$("#dt_ai").prop("checked",  !!d.allow_import);
					$("#dt_ar").prop("checked",  !!d.allow_rename);

					// ── Populate Fields table ─────────────────────
					$("#dt-rows").empty();
					(d.fields || []).forEach(f => {
						addRow({
							fn   : f.fieldname,
							ft   : f.fieldtype,
							lbl  : f.label || "",
							op   : f.options || (f.default || ""),
							dep  : f.depends_on || "",
							req  : f.reqd,
							list : f.in_list_view,
							ro   : f.read_only,
							bold : f.bold,
							ph   : f.print_hide,
						});
					});

					// ── Set module in module selector ─────────────
					// Try to pre-select the app/module dropdowns
					frappe.call({ method:"frappe.client.get_list",
						args:{ doctype:"Module Def", fields:["app_name"], filters:[["module_name","=",d.module]], limit_page_length:1 },
						callback: r2 => {
							const app = r2.message?.[0]?.app_name;
							if (app) {
								// Load apps then select
								loadApps().then(() => {
									fillSel($c1.find("#dt_app"), _apps, "select app");
									$("#dt_app").val(app).trigger("change");
									setTimeout(() => {
										loadMods(app).then(ms => {
											fillSel($c1.find("#dt_mod"), ms, "select module");
											$c1.find("#dt_mod").prop("disabled", false).val(d.module);
										});
									}, 100);
								});
							}
						}
					});

					$status.html(`<span style="color:#1a7a3a">✓ Loaded ${d.fields?.length || 0} fields from <strong>${dtName}</strong></span>`);
					$("#dt_ow").prop("checked", true); // auto-enable overwrite since we're editing
					$('#dt-load-status').css('color','#1a7a3a');
				},
				error: () => {
					$btn.prop("disabled", false);
					$status.text("Error loading DocType");
				}
			});
		});

		// ── Standard identity form ─────────────────────────
		$c1.append(`<div class="dkst-g2">
			${AppSel("dt_app")} ${ModSel("dt_mod")}
			${FR("dt_nm","DocType Name","text","My Document")}
			${F("dt_nr","Naming Rule","select","","",[...NAMING_OPTS])}
			${F("dt_au","Autoname Pattern","text","SINV-.YYYY.-.####")}
			${F("dt_tf","Title Field","text","name")}
			${F("dt_sf","Search Fields","text","name,status")}
			${F("dt_so","Sort Field","text","modified")}
		</div>`);
		wireAMD($c1,"dt_app","dt_mod",null);

		const $c2=card($p,"Flags & Options");
		$c2.append(`<div class="dkst-checks">
			${mode!=="child" ? CHK("dt_sub","Submittable") : ""}
			${mode==="child" ? CHK("dt_edg","Editable Grid",1) : ""}
			${mode==="single"? CHK("dt_isg","issingle",1) : ""}
			${mode==="normal"? CHK("dt_tre","Tree / Hierarchy") : ""}
			${mode!=="single"? CHK("dt_qe","Quick Entry") : ""}
			${CHK("dt_trk","Track Changes",1)}
			${CHK("dt_trs","Track Seen")}
			${CHK("dt_ai","Allow Import",1)}
			${CHK("dt_ar","Allow Rename",mode==="normal"?1:0)}
			${CHK("dt_ow","Overwrite Existing Files")}
		</div>`);

		const $c3=card($p,"Fields");
		$c3.append(`<div class="dkst-tbl-wrap">
		<table class="dkst-tbl">
			<thead><tr>
				<th style="width:14%">Fieldname</th>
				<th style="width:15%">Fieldtype</th>
				<th style="width:14%">Label</th>
				<th style="width:16%">Options / Default</th>
				<th style="width:11%">Depends On</th>
				<th style="width:6%" title="Required">Req</th>
				<th style="width:6%" title="In List View">List</th>
				<th style="width:6%" title="Read Only">RO</th>
				<th style="width:6%" title="Bold">Bld</th>
				<th style="width:6%" title="Print Hide">PH</th>
				<th style="width:20px"></th>
			</tr></thead>
			<tbody id="dt-rows"></tbody>
		</table></div>`);
		$(`<div class="dkst-add-row">+ Add Field</div>`).appendTo($c3).on("click",()=>addRow());

		const seeds={
			normal:[
				{fn:"naming_series",ft:"Select",lbl:"Series",op:"DOC-.YYYY.-.####",req:1},
				{fn:"customer",ft:"Link",lbl:"Customer",op:"Customer",req:1,list:1,bold:1},
				{fn:"customer_name",ft:"Data",lbl:"Customer Name",ro:1,list:1},
				{fn:"posting_date",ft:"Date",lbl:"Posting Date",op:"Today",req:1,list:1},
				{fn:"company",ft:"Link",lbl:"Company",op:"Company",req:1},
				{fn:"section_items",ft:"Section Break",lbl:"Items"},
				{fn:"items",ft:"Table",lbl:"Items",op:""},
				{fn:"section_totals",ft:"Section Break",lbl:"Totals"},
				{fn:"total_amount",ft:"Currency",lbl:"Total Amount",ro:1},
				{fn:"status",ft:"Select",lbl:"Status",op:"\\nDraft\\nOpen\\nClosed\\nCancelled",list:1,bold:1},
				{fn:"remarks",ft:"Small Text",lbl:"Remarks"},
			],
			child:[
				{fn:"item_code",ft:"Link",lbl:"Item",op:"Item",req:1,list:1,bold:1},
				{fn:"item_name",ft:"Data",lbl:"Item Name",list:1,ro:1},
				{fn:"description",ft:"Small Text",lbl:"Description"},
				{fn:"uom",ft:"Link",lbl:"UOM",op:"UOM",req:1,list:1},
				{fn:"qty",ft:"Float",lbl:"Qty",op:"1",req:1,list:1},
				{fn:"rate",ft:"Currency",lbl:"Rate",req:1,list:1},
				{fn:"discount_percentage",ft:"Percent",lbl:"Discount %"},
				{fn:"amount",ft:"Currency",lbl:"Amount",list:1,ro:1},
				{fn:"warehouse",ft:"Link",lbl:"Warehouse",op:"Warehouse"},
			],
			single:[
				{fn:"section_general",ft:"Section Break",lbl:"General Settings"},
				{fn:"company",ft:"Link",lbl:"Default Company",op:"Company"},
				{fn:"enabled",ft:"Check",lbl:"Enable"},
				{fn:"col1",ft:"Column Break"},
				{fn:"currency",ft:"Link",lbl:"Currency",op:"Currency"},
			]
		};
		(seeds[mode]||[]).forEach(d=>addRow(d));

		function addRow(d={}) {
			const $tr=$(`<tr>
				<td><input class="dkst-inp f-fn" value="${d.fn||""}" placeholder="field_name"></td>
				<td><select class="dkst-sel f-ft">${FT_ALL.map(t=>`<option value="${t}" ${t===(d.ft||"Data")?"selected":""}>${t}</option>`).join("")}</select></td>
				<td><input class="dkst-inp f-lbl" value="${d.lbl||""}" placeholder="Label"></td>
				<td><input class="dkst-inp f-op"  value="${d.op||""}"  placeholder="options/default"></td>
				<td><input class="dkst-inp f-dep" value="${d.dep||""}" placeholder="eval:doc.x=='y'"></td>
				<td style="text-align:center"><input type="checkbox" class="f-req"  ${d.req?"checked":""}></td>
				<td style="text-align:center"><input type="checkbox" class="f-list" ${d.list?"checked":""}></td>
				<td style="text-align:center"><input type="checkbox" class="f-ro"   ${d.ro?"checked":""}></td>
				<td style="text-align:center"><input type="checkbox" class="f-bold" ${d.bold?"checked":""}></td>
				<td style="text-align:center"><input type="checkbox" class="f-ph"   ${d.ph?"checked":""}></td>
				<td><button class="dkst-del-btn">×</button></td>
			</tr>`);
			$tr.find(".dkst-del-btn").on("click",()=>$tr.remove());
			$("#dt-rows").append($tr);
		}

		const $c4=card($p,"Permissions");
		$c4.append(info("System Manager and All roles are added by default. Add extra roles below."));
		$c4.append(`<div class="dkst-g3">
			${F("dt_r1","Extra Role 1","text","Accounts Manager")}
			${F("dt_r2","Extra Role 2","text","Sales Manager")}
			${F("dt_r3","Extra Role 3","text","")}
		</div>`);

		const $t=term($p);
		btns($p,[
			{ lbl:`Generate ${cfg.title}`, cls:"dkst-btn-p", fn:()=>{
				if(!gv("dt_app")||!gv("dt_mod")||!gv("dt_nm")){frappe.throw("App, Module and DocType Name required");return;}
				const fields=[];
				$("#dt-rows tr").each(function(){
					const fn=$(this).find(".f-fn").val().trim();
					const ft=$(this).find(".f-ft").val();
					const lbl=$(this).find(".f-lbl").val().trim();
					const op=$(this).find(".f-op").val().trim();
					const dep=$(this).find(".f-dep").val().trim();
					const row={fieldname:fn,fieldtype:ft};
					if(lbl) row.label=lbl;
					if(op)  { if(ft==="Date"&&op.toLowerCase()==="today") row.default="Today"; else row.options=op; }
					if(dep) row.depends_on=dep;
					if($(this).find(".f-req").is(":checked"))  row.reqd=1;
					if($(this).find(".f-list").is(":checked")) row.in_list_view=1;
					if($(this).find(".f-ro").is(":checked"))   row.read_only=1;
					if($(this).find(".f-bold").is(":checked")) row.bold=1;
					if($(this).find(".f-ph").is(":checked"))   row.print_hide=1;
					fields.push(row);
				});
				if(!fields.length){frappe.throw("Add at least one field");return;}
				const perms=[];
				[gv("dt_r1"),gv("dt_r2"),gv("dt_r3")].filter(Boolean).forEach(r=>perms.push({role:r,read:1,write:1,create:1}));
				api("frappe_devkit.api.doctype_builder.scaffold_doctype",{
					app_name:gv("dt_app"),module_name:gv("dt_mod"),doctype_name:gv("dt_nm"),
					fields:JSON.stringify(fields),
					is_child_table:mode==="child"?1:0,
					is_submittable:gc("dt_sub")?1:0,
					is_single:mode==="single"||gc("dt_isg")?1:0,
					is_tree:gc("dt_tre")?1:0,
					quick_entry:gc("dt_qe")?1:0,
					editable_grid:gc("dt_edg")?1:0,
					track_changes:gc("dt_trk")?1:0,
					track_seen:gc("dt_trs")?1:0,
					naming_rule:gv("dt_nr")||"By fieldname",
					autoname:gv("dt_au"),title_field:gv("dt_tf"),
					search_fields:gv("dt_sf"),sort_field:gv("dt_so")||"modified",
					permissions:perms.length?JSON.stringify(perms):null,
					overwrite:gc("dt_ow"),
				},$t);
			}},
			{ lbl:"Clear Fields", cls:"dkst-btn-s", fn:()=>$("#dt-rows").empty() },
			{ lbl:"Add 5 Standard Fields", cls:"dkst-btn-s", fn:()=>{
				[{fn:"amended_from",ft:"Link",lbl:"Amended From",op:"",ro:1,ph:1},
				 {fn:"naming_series",ft:"Select",lbl:"Series",op:"DOC-.YYYY.-.####",req:1},
				 {fn:"posting_date",ft:"Date",lbl:"Posting Date",op:"Today",req:1,list:1},
				 {fn:"company",ft:"Link",lbl:"Company",op:"Company",req:1},
				 {fn:"status",ft:"Select",lbl:"Status",op:"\\nDraft\\nOpen\\nClosed",list:1}
				].forEach(addRow);
			}},
		]);
	}
	PANELS.doctype = $p=>buildDT($p,"normal");
	PANELS.child   = $p=>buildDT($p,"child");
	PANELS.single  = $p=>buildDT($p,"single");

	/* ── Report ── */
	PANELS.report = function($p) {
		$p.append(phdr("Report Builder","Generate Script or Query reports with filters, columns and Python stubs.",icoChart(20)));
		const $c1=card($p,"Report Identity");
		$c1.append(`<div class="dkst-g2">
			${AppSel("rp_app")} ${ModSel("rp_mod")}
			${FR("rp_nm","Report Name","text","My Report")}
			${FR("rp_dt","Ref DocType","text","Sales Invoice")}
			${F("rp_ty","Report Type","select","","",[["Script Report","Script Report"],["Query Report","Query Report"]])}
			${F("rp_st","Is Standard","select","","",[["Yes","Yes"],["No","No"]])}
		</div>
		<div class="dkst-checks" style="margin-top:12px">
			${CHK("rp_tr","Add Total Row")} ${CHK("rp_ow","Overwrite Existing")}
		</div>`);
		wireAMD($c1,"rp_app","rp_mod",null);

		const $c2=card($p,"Filters");
		$c2.append(`<div class="dkst-tbl-wrap"><table class="dkst-tbl">
			<thead><tr><th>Fieldname</th><th>Fieldtype</th><th>Label</th><th>Options</th><th>Default</th><th>Req</th><th></th></tr></thead>
			<tbody id="rp-fr"></tbody>
		</table></div>`);
		$(`<div class="dkst-add-row">+ Add Filter</div>`).appendTo($c2).on("click",()=>addRF());
		[{fn:"company",ft:"Link",lbl:"Company",op:"Company",req:1},
		 {fn:"from_date",ft:"Date",lbl:"From Date",def:"Today",req:1},
		 {fn:"to_date",ft:"Date",lbl:"To Date",def:"Today",req:1},
		 {fn:"customer",ft:"Link",lbl:"Customer",op:"Customer"}].forEach(addRF);

		const $c3=card($p,"Columns");
		$c3.append(`<div class="dkst-tbl-wrap"><table class="dkst-tbl">
			<thead><tr><th>Fieldname</th><th>Fieldtype</th><th>Label</th><th>Width</th><th>Options (Link)</th><th>Align</th><th></th></tr></thead>
			<tbody id="rp-cr"></tbody>
		</table></div>`);
		$(`<div class="dkst-add-row">+ Add Column</div>`).appendTo($c3).on("click",()=>addRC());
		[{fn:"name",ft:"Link",lbl:"Document",w:150,op:"Sales Invoice"},
		 {fn:"posting_date",ft:"Date",lbl:"Date",w:100},
		 {fn:"customer",ft:"Link",lbl:"Customer",w:150,op:"Customer"},
		 {fn:"total_amount",ft:"Currency",lbl:"Amount",w:120,al:"right"}].forEach(addRC);

		function addRF(d={}) {
			const $tr=$(`<tr>
				<td><input class="dkst-inp f-fn" value="${d.fn||""}" placeholder="company"></td>
				<td><select class="dkst-sel f-ft">${FT_MINI.map(t=>`<option ${t===(d.ft||"Data")?"selected":""}>${t}</option>`).join("")}</select></td>
				<td><input class="dkst-inp f-lbl" value="${d.lbl||""}" placeholder="Company"></td>
				<td><input class="dkst-inp f-op"  value="${d.op||""}"  placeholder="Link DocType"></td>
				<td><input class="dkst-inp f-def" value="${d.def||""}" placeholder="default value"></td>
				<td style="text-align:center"><input type="checkbox" class="f-req" ${d.req?"checked":""}></td>
				<td><button class="dkst-del-btn">×</button></td>
			</tr>`);
			$tr.find(".dkst-del-btn").on("click",()=>$tr.remove());
			$("#rp-fr").append($tr);
		}
		function addRC(d={}) {
			const $tr=$(`<tr>
				<td><input class="dkst-inp f-fn" value="${d.fn||""}" placeholder="total_amount"></td>
				<td><select class="dkst-sel f-ft">${FT_MINI.map(t=>`<option ${t===(d.ft||"Data")?"selected":""}>${t}</option>`).join("")}</select></td>
				<td><input class="dkst-inp f-lbl" value="${d.lbl||""}" placeholder="Total Amount"></td>
				<td><input class="dkst-inp f-w" value="${d.w||120}" style="width:64px"></td>
				<td><input class="dkst-inp f-op" value="${d.op||""}" placeholder="DocType (Link)"></td>
				<td><select class="dkst-sel f-al" style="width:80px"><option value="">—</option><option ${d.al==="left"?"selected":""}>left</option><option ${d.al==="right"?"selected":""}>right</option><option ${d.al==="center"?"selected":""}>center</option></select></td>
				<td><button class="dkst-del-btn">×</button></td>
			</tr>`);
			$tr.find(".dkst-del-btn").on("click",()=>$tr.remove());
			$("#rp-cr").append($tr);
		}

		const $t=term($p);
		btns($p,[{ lbl:"Generate Report", cls:"dkst-btn-p", fn:()=>{
			if(!gv("rp_app")||!gv("rp_mod")||!gv("rp_nm")||!gv("rp_dt")){frappe.throw("App, Module, Name and Ref DocType required");return;}
			const filters=[],columns=[];
			$("#rp-fr tr").each(function(){
				const r={fieldname:$(this).find(".f-fn").val().trim(),fieldtype:$(this).find(".f-ft").val(),label:$(this).find(".f-lbl").val().trim()};
				const op=$(this).find(".f-op").val().trim(); if(op) r.options=op;
				const def=$(this).find(".f-def").val().trim(); if(def) r.default=def;
				if($(this).find(".f-req").is(":checked")) r.reqd=1;
				if(r.fieldname) filters.push(r);
			});
			$("#rp-cr tr").each(function(){
				const r={fieldname:$(this).find(".f-fn").val().trim(),fieldtype:$(this).find(".f-ft").val(),label:$(this).find(".f-lbl").val().trim(),width:parseInt($(this).find(".f-w").val())||120};
				const op=$(this).find(".f-op").val().trim(); if(op) r.options=op;
				const al=$(this).find(".f-al").val().trim(); if(al) r.align=al;
				if(r.fieldname) columns.push(r);
			});
			api("frappe_devkit.api.report_builder.scaffold_report",{
				app_name:gv("rp_app"),module_name:gv("rp_mod"),report_name:gv("rp_nm"),
				report_type:gv("rp_ty"),ref_doctype:gv("rp_dt"),is_standard:gv("rp_st")||"Yes",
				add_total_row:gc("rp_tr")?1:0,overwrite:gc("rp_ow"),
				filters:JSON.stringify(filters),columns:JSON.stringify(columns),
			},$t);
		}}]);
	};

	/* ── Print Format ── */
	PANELS.print_fmt = function($p) {
		$p.append(phdr("Print Format","Scaffold a Jinja2 HTML print format with a starter template.",icoPrint(20)));
		const $c=card($p,"Print Format Details");
		$c.append(`<div class="dkst-g2">
			${AppSel("pf_app")} ${ModSel("pf_mod")}
			${FR("pf_nm","Print Format Name","text","My Invoice Print")}
			${DtSel("pf_dt","DocType")}
			${F("pf_st","Standard","select","","",[["Yes","Yes"],["No","No"]])}
			${F("pf_css","Custom CSS","text","/* optional CSS */")}
		</div>`);
		wireAMD($c,"pf_app","pf_mod","pf_dt");
		const $t=term($p);
		btns($p,[{ lbl:"Generate Print Format", cls:"dkst-btn-p", fn:()=>{
			if(!gv("pf_app")||!gv("pf_mod")||!gv("pf_nm")){frappe.throw("App, Module and Name required");return;}
			api("frappe_devkit.api.fixture_builder.scaffold_print_format",{app_name:gv("pf_app"),module_name:gv("pf_mod"),print_format_name:gv("pf_nm"),dt:gv("pf_dt"),standard:gv("pf_st")||"Yes",css:gv("pf_css")},$t);
		}}]);
	};

	/* ── Custom Field ── */
	PANELS.custom_field = function($p) {
		$p.append(phdr("Custom Field","Add a custom field to any DocType via app fixtures.",icoSliders(20)));
		$p.append(info("Fields are stored in <span class='dkst-code'>fixtures/custom_field.json</span> and deployed via <span class='dkst-code'>bench migrate</span>."));

		const $c1=card($p,"Target DocType");
		$c1.append(`<div class="dkst-g2">
			${AppSel("cf_app")} ${ModSel("cf_mod")}
			${DtSel("cf_dt","Target DocType")}
			${F("cf_af","Insert After (fieldname)","text","customer")}
		</div>`);
		wireAMD($c1,"cf_app","cf_mod","cf_dt");

		const $c2=card($p,"Field Definition");
		$c2.append(`<div class="dkst-g2">
			${FR("cf_fn","Fieldname","text","my_field")}
			${F("cf_ft","Fieldtype","select","","",[
				["Data","Data"],["Link","Link"],["Select","Select"],["Check","Check"],
				["Currency","Currency"],["Float","Float"],["Int","Int"],["Date","Date"],
				["Datetime","Datetime"],["Time","Time"],["Text","Text"],["Small Text","Small Text"],
				["Long Text","Long Text"],["Text Editor","Text Editor"],["Code","Code"],
				["Attach","Attach"],["Attach Image","Attach Image"],["Percent","Percent"],
				["Password","Password"],["Phone","Phone"],["Color","Color"],["Rating","Rating"],
				["Table","Table"],["Table MultiSelect","Table MultiSelect"],["Dynamic Link","Dynamic Link"],["Image","Image"],
			])}
			${FR("cf_lbl","Label","text","My Field")}
			${F("cf_op","Options","text","Customer (for Link) or choices for Select")}
			${F("cf_def","Default Value","text","")}
			${F("cf_pr","Precision (Float/Currency)","text","")}
			${F("cf_dep","Depends On","text","eval:doc.status=='Open'")}
			${F("cf_mrd","Mandatory Depends On","text","eval:doc.type=='Special'")}
			${F("cf_rod","Read Only Depends On","text","eval:doc.docstatus==1")}
			${F("cf_ff","Fetch From","text","customer.customer_name")}
			<div class="dkst-fld dkst-full">${F("cf_dc","Description / Help Text","text","")}</div>
		</div>`);

		const $c3=card($p,"Field Flags");
		$c3.append(`<div class="dkst-checks">
			${CHK("cf_rq","Required")}     ${CHK("cf_bl","Bold")}
			${CHK("cf_li","In List View")} ${CHK("cf_fi","In Standard Filter")}
			${CHK("cf_gs","In Global Search")} ${CHK("cf_nc","No Copy")}
			${CHK("cf_ro","Read Only")}    ${CHK("cf_hd","Hidden")}
			${CHK("cf_ph","Print Hide")}   ${CHK("cf_as","Allow On Submit")}
			${CHK("cf_uq","Unique")}       ${CHK("cf_si","Search Index")}
			${CHK("cf_tr","Translatable")} ${CHK("cf_fi2","Fetch If Empty")}
		</div>`);

		const $t=term($p);
		btns($p,[{ lbl:"Add to Fixtures", cls:"dkst-btn-p", fn:()=>{
			if(!gv("cf_app")||!gv("cf_fn")||!gv("cf_lbl")){frappe.throw("App, Fieldname and Label required");return;}
			api("frappe_devkit.api.fixture_builder.scaffold_custom_field",{
				app_name:gv("cf_app"),dt:gv("cf_dt"),
				fieldname:gv("cf_fn"),fieldtype:gv("cf_ft"),label:gv("cf_lbl"),
				insert_after:gv("cf_af"),options:gv("cf_op"),default:gv("cf_def"),
				precision:gv("cf_pr"),depends_on:gv("cf_dep"),
				mandatory_depends_on:gv("cf_mrd"),read_only_depends_on:gv("cf_rod"),
				fetch_from:gv("cf_ff"),description:gv("cf_dc"),
				reqd:gc("cf_rq")?1:0,bold:gc("cf_bl")?1:0,in_list_view:gc("cf_li")?1:0,
				in_standard_filter:gc("cf_fi")?1:0,in_global_search:gc("cf_gs")?1:0,
				no_copy:gc("cf_nc")?1:0,read_only:gc("cf_ro")?1:0,hidden:gc("cf_hd")?1:0,
				print_hide:gc("cf_ph")?1:0,allow_on_submit:gc("cf_as")?1:0,
				unique:gc("cf_uq")?1:0,search_index:gc("cf_si")?1:0,
				translatable:gc("cf_tr")?1:0,fetch_if_empty:gc("cf_fi2")?1:0,
			},$t);
		}}]);
	};

	/* ── Property Setter ── */
	PANELS.property = function($p) {
		$p.append(phdr("Property Setter","Override standard DocType or field properties without patching core ERPNext.",icoEdit(20)));
		$p.append(info("Property Setters are stored in <span class='dkst-code'>fixtures/property_setter.json</span> and applied on migrate. Leave Fieldname empty for DocType-level properties."));
		const $c=card($p,"Property Setter Definition");
		$c.append(`<div class="dkst-g2">
			${AppSel("ps_app")} ${ModSel("ps_mod")}
			${DtSel("ps_dt","DocType")}
			${F("ps_fn","Fieldname (empty = DocType level)","text","po_no")}
			${F("ps_pr","Property","select","","",[
				["reqd","reqd"],["hidden","hidden"],["read_only","read_only"],["bold","bold"],
				["in_list_view","in_list_view"],["in_standard_filter","in_standard_filter"],
				["in_global_search","in_global_search"],["search_index","search_index"],
				["default","default"],["options","options"],["label","label"],
				["description","description"],["precision","precision"],["length","length"],
				["no_copy","no_copy"],["print_hide","print_hide"],["report_hide","report_hide"],
				["allow_on_submit","allow_on_submit"],["depends_on","depends_on"],
				["mandatory_depends_on","mandatory_depends_on"],["read_only_depends_on","read_only_depends_on"],
				["allow_import","allow_import"],["quick_entry","quick_entry"],
				["title_field","title_field"],["search_fields","search_fields"],
				["sort_field","sort_field"],["max_attachments","max_attachments"],
				["editable_grid","editable_grid"],["track_changes","track_changes"],
			])}
			${FR("ps_vl","Value","text","1")}
			${F("ps_ty","Property Type","select","","",[["Check","Check"],["Data","Data"],["Int","Int"],["Select","Select"],["Text","Text"],["Code","Code"]])}
		</div>`);
		wireAMD($c,"ps_app","ps_mod","ps_dt");
		const $t=term($p);
		btns($p,[{ lbl:"Add Property Setter", cls:"dkst-btn-p", fn:()=>{
			if(!gv("ps_app")||!gv("ps_dt")||!gv("ps_pr")){frappe.throw("App, DocType and Property required");return;}
			api("frappe_devkit.api.fixture_builder.scaffold_property_setter",{
				app_name:gv("ps_app"),dt:gv("ps_dt"),fieldname:gv("ps_fn"),
				property_name:gv("ps_pr"),value:gv("ps_vl"),
				property_type:gv("ps_ty")||"Data",
				doctype_or_field:gv("ps_fn")?"DocField":"DocType",
			},$t);
		}}]);
	};

	/* ── Client Script ── */
	PANELS.client_script = function($p) {
		$p.append(phdr("Client Script","Add a Client Script fixture for deployment.",icoCode(20)));
		const $c=card($p,"Client Script");
		$c.append(`<div class="dkst-g2">
			${AppSel("cs_app")} ${ModSel("cs_mod")}
			${DtSel("cs_dt","DocType")}
			${F("cs_vw","View","select","","",[["Form","Form"],["List","List"],["Report","Report"],["View","View"]])}
		</div>`);
		$c.append(`<div class="dkst-fld" style="margin-top:14px">
			<label class="dkst-lbl">JavaScript Code</label>
			<textarea class="dkst-ta" id="cs_sc" rows="10" style="font-family:'Consolas','Courier New',monospace;font-size:12.5px;line-height:1.6">frappe.ui.form.on("MyDocType", {
  setup(frm) {
    // runs once on form init
  },
  refresh(frm) {
    // runs on every load
  },
  validate(frm) {
    // runs before save
  }
});</textarea></div>`);
		wireAMD($c,"cs_app","cs_mod","cs_dt");
		const $t=term($p);
		btns($p,[{ lbl:"Add Client Script to Fixtures", cls:"dkst-btn-p", fn:()=>{
			if(!gv("cs_app")||!gv("cs_dt")){frappe.throw("App and DocType required");return;}
			api("frappe_devkit.api.fixture_builder.scaffold_client_script",{app_name:gv("cs_app"),dt:gv("cs_dt"),script:gv("cs_sc"),view:gv("cs_vw")||"Form"},$t);
		}}]);
	};

	/* ── Hook ── */
	PANELS.hook = function($p) {
		$p.append(phdr("Add Hook","Register handlers in hooks.py — doc events, schedulers, overrides and more.",icoLink(20)));
		const $tabs=$(`<div class="dkst-stabs">
			<div class="dkst-stab active" data-t="de">Doc Event</div>
			<div class="dkst-stab" data-t="sc">Scheduler</div>
			<div class="dkst-stab" data-t="ff">Fixture Filter</div>
			<div class="dkst-stab" data-t="co">Class Override</div>
			<div class="dkst-stab" data-t="pq">Permission Query</div>
			<div class="dkst-stab" data-t="wm">Whitelist Method</div>
		</div>`).appendTo($p);
		const $pp=$(`<div></div>`).appendTo($p);

		function mkSub(id) {
			const $s=$(`<div class="dkst-spanel ${id==='de'?'active':''}" data-t="${id}"></div>`).appendTo($pp);
			return card($s);
		}

		/* doc event */
		const $dec=mkSub("de");
		$dec.append(`<div class="dkst-g2">
			${AppSel("de_ap")}
			${F("de_dt","DocType","text","Sales Invoice","",[])}
			${F("de_ev","Event","select","","",[...DOC_EVENTS])}
			<div class="dkst-fld dkst-full"><label class="dkst-lbl dkst-req">Handler Path</label>
				<input class="dkst-inp" id="de_h" placeholder="my_app.overrides.sales_invoice.validate">
				<span class="dkst-hint">Python dotted path to the function that will be called</span></div>
		</div>`);
		loadApps().then(()=>fillSel($dec.find("#de_ap"),_apps,"select app"));
		const $det=term($dec.closest(".dkst-spanel"));
		btns($dec.closest(".dkst-spanel"),[{ lbl:"Add Doc Event", cls:"dkst-btn-p", fn:()=>api("frappe_devkit.api.hook_builder.add_doc_event",{app_name:gv("de_ap"),doctype:gv("de_dt"),event:gv("de_ev"),handler_path:gv("de_h")},$det)}]);

		/* scheduler */
		const $scc=mkSub("sc");
		$scc.append(`<div class="dkst-g2">
			${AppSel("sc_ap")}
			${F("sc_fr","Frequency","select","","",[["daily","daily"],["hourly","hourly"],["weekly","weekly"],["monthly","monthly"],["all","all (every tick)"],["daily_long","daily_long"],["hourly_long","hourly_long"],["weekly_long","weekly_long"],["monthly_long","monthly_long"]])}
			<div class="dkst-fld dkst-full"><label class="dkst-lbl dkst-req">Handler Path</label>
				<input class="dkst-inp" id="sc_h" placeholder="my_app.tasks.daily_cleanup">
				<span class="dkst-hint">Python dotted path — function takes no arguments</span></div>
		</div>`);
		loadApps().then(()=>fillSel($scc.find("#sc_ap"),_apps,"select app"));
		const $sct=term($scc.closest(".dkst-spanel"));
		btns($scc.closest(".dkst-spanel"),[{ lbl:"Add Scheduler Event", cls:"dkst-btn-p", fn:()=>api("frappe_devkit.api.hook_builder.add_scheduler_event",{app_name:gv("sc_ap"),frequency:gv("sc_fr"),handler_path:gv("sc_h")},$sct)}]);

		/* fixture filter */
		const $ffc=mkSub("ff");
		$ffc.append(`<div class="dkst-g2">
			${AppSel("ff_ap")}
			${F("ff_dt","DocType","text","Custom Field","")}
			<div class="dkst-fld dkst-full"><label class="dkst-lbl dkst-req">Filters (JSON array)</label>
				<textarea class="dkst-ta" id="ff_fi" rows="4" style="font-family:'Consolas',monospace;font-size:12.5px">[["dt","in",["Sales Order","Sales Invoice"]],["fieldname","=","my_field"]]</textarea>
				<span class="dkst-hint">Format: [["fieldname","operator","value"],…]</span></div>
		</div>`);
		loadApps().then(()=>fillSel($ffc.find("#ff_ap"),_apps,"select app"));
		const $fft=term($ffc.closest(".dkst-spanel"));
		btns($ffc.closest(".dkst-spanel"),[{ lbl:"Add Fixture Filter", cls:"dkst-btn-p", fn:()=>api("frappe_devkit.api.hook_builder.add_fixture_filter",{app_name:gv("ff_ap"),dt:gv("ff_dt"),filters:gv("ff_fi")},$fft)}]);

		/* class override */
		const $coc=mkSub("co");
		$coc.append(`<div class="dkst-g2">
			${AppSel("co_ap")}
			${F("co_dt","DocType","text","Sales Invoice","")}
			<div class="dkst-fld dkst-full"><label class="dkst-lbl dkst-req">Class Path</label>
				<input class="dkst-inp" id="co_cl" placeholder="my_app.overrides.sales_invoice.CustomSalesInvoice">
				<span class="dkst-hint">Must extend the original class — <span class="dkst-code">from erpnext.accounts.doctype.sales_invoice.sales_invoice import SalesInvoice</span></span></div>
		</div>`);
		loadApps().then(()=>fillSel($coc.find("#co_ap"),_apps,"select app"));
		const $cot=term($coc.closest(".dkst-spanel"));
		btns($coc.closest(".dkst-spanel"),[{ lbl:"Add Class Override", cls:"dkst-btn-p", fn:()=>api("frappe_devkit.api.hook_builder.add_override_doctype_class",{app_name:gv("co_ap"),doctype:gv("co_dt"),class_path:gv("co_cl")},$cot)}]);

		/* permission query */
		const $pqc=mkSub("pq");
		$pqc.append(`<div class="dkst-g2">
			${AppSel("pq_ap")}
			${F("pq_dt","DocType","text","Sales Invoice","")}
			<div class="dkst-fld dkst-full"><label class="dkst-lbl dkst-req">Handler Path</label>
				<input class="dkst-inp" id="pq_h" placeholder="my_app.permissions.get_permission_query_conditions">
				<span class="dkst-hint">Function must return a SQL WHERE condition string — empty string = no restriction</span></div>
		</div>`);
		loadApps().then(()=>fillSel($pqc.find("#pq_ap"),_apps,"select app"));
		const $pqt=term($pqc.closest(".dkst-spanel"));
		btns($pqc.closest(".dkst-spanel"),[{ lbl:"Add Permission Query", cls:"dkst-btn-p", fn:()=>api("frappe_devkit.api.hook_builder.add_permission_query",{app_name:gv("pq_ap"),doctype:gv("pq_dt"),handler_path:gv("pq_h")},$pqt)}]);

		/* whitelist method */
		const $wmc=mkSub("wm");
		$wmc.append($(`<div class="dkst-g2"></div>`));
		$wmc.find(".dkst-g2").append(AppSel("wm_ap"));
		loadApps().then(()=>fillSel($wmc.find("#wm_ap"),_apps,"select app"));
		$wmc.append(`
			<div class="dkst-div"></div>
			${secLbl("Override whitelisted method")}
			<div class="dkst-g2">
				<div class="dkst-fld"><label class="dkst-lbl dkst-req">Original Method</label>
					<input class="dkst-inp" id="wm_orig" placeholder="frappe.desk.doctype.event.event.get_events">
					<span class="dkst-hint">Full dotted path of the original Frappe/ERPNext method</span></div>
				<div class="dkst-fld"><label class="dkst-lbl dkst-req">Override Method</label>
					<input class="dkst-inp" id="wm_new" placeholder="my_app.utils.get_events">
					<span class="dkst-hint">Your replacement function</span></div>
			</div>`);
		const $wmt=term($wmc.closest(".dkst-spanel"));
		btns($wmc.closest(".dkst-spanel"),[{ lbl:"Add Whitelist Override", cls:"dkst-btn-p", fn:()=>{
			const $h=$wmc.find("#wm_ap").val();
			if(!$h||!gv("wm_orig")||!gv("wm_new")){frappe.throw("All fields required");return;}
			/* write directly into hooks.py */
			frappe.call({ method:"frappe_devkit.api.hook_builder.add_whitelist_override",
				args:{app_name:$h,original:gv("wm_orig"),override:gv("wm_new")},
				callback:r=>{ const m=r.message; $wmt.addClass(m?.status==="success"?"ok":"err").text(m?.status==="success"?`✓  ${m.message}`:JSON.stringify(m)); }
			});
		}}]);

		$tabs.on("click",".dkst-stab",function(){
			const t=$(this).data("t");
			$tabs.find(".dkst-stab").removeClass("active"); $(this).addClass("active");
			$pp.find(".dkst-spanel").removeClass("active"); $pp.find(`[data-t="${t}"]`).addClass("active");
		});
	};

	/* ── Override File ── */
	PANELS.override = function($p) {
		$p.append(phdr("Override File","Scaffold a Python override file in overrides/ with all event stubs ready to fill in.",icoCode(20)));
		const EVTS=["validate","before_save","on_update","before_insert","after_insert",
			"on_submit","before_submit","on_cancel","before_cancel","on_update_after_submit",
			"on_trash","after_delete","has_permission","on_change","before_rename","after_rename"];
		const $c=card($p,"Override File Details");
		$c.append(`<div class="dkst-g2">
			${AppSel("ov_ap")}
			${F("ov_dt","DocType Name","text","Sales Invoice","")}
		</div>`);
		loadApps().then(()=>fillSel($c.find("#ov_ap"),_apps,"select app"));
		$c.append(`<div class="dkst-div"></div>`);
		$c.append(secLbl("Events to include as function stubs"));
		$c.append(`<div class="dkst-checks">${EVTS.map(e=>CHK("ov_"+e,e,["validate","before_save","on_submit","on_cancel"].includes(e)?1:0)).join("")}</div>`);
		const $t=term($p);
		btns($p,[
			{ lbl:"Generate Override File", cls:"dkst-btn-p", fn:()=>{
				const evts=EVTS.filter(e=>gc("ov_"+e));
				if(!evts.length){frappe.throw("Select at least one event");return;}
				api("frappe_devkit.api.hook_builder.scaffold_override_file",{app_name:gv("ov_ap"),doctype_name:gv("ov_dt"),events:JSON.stringify(evts)},$t);
			}},
			{ lbl:"Select All", cls:"dkst-btn-s", fn:()=>EVTS.forEach(e=>$(`#ov_${e}`).prop("checked",true)) },
			{ lbl:"Clear All",  cls:"dkst-btn-s", fn:()=>EVTS.forEach(e=>$(`#ov_${e}`).prop("checked",false)) },
		]);
	};

	/* ── Patch ── */
	PANELS.patch = function($p) {
		$p.append(phdr("Patch Builder","Scaffold a one-time migration patch registered in patches.txt.",icoBolt(20)));
		$p.append(info("Patches run exactly once during <span class='dkst-code'>bench migrate</span>. Once executed they are never run again. Make them idempotent."));
		const $c=card($p,"Patch Details");
		$c.append(`<div class="dkst-g2">
			${AppSel("pa_ap")}
			${FR("pa_mo","Patch Module (dot path)","text","v1_0.set_default_fabric_type")}
			<div class="dkst-fld dkst-full"><label class="dkst-lbl">Description</label>
				<input class="dkst-inp" id="pa_de" placeholder="What this patch does — appears as docstring in the generated file"></div>
		</div>`);
		loadApps().then(()=>fillSel($c.find("#pa_ap"),_apps,"select app"));
		$("#pa_bd_wrap").remove();
		$c.append('<div class="dkst-div"></div><div id="pa_bd_wrap" class="dkst-fld"><label class="dkst-lbl">Execute Body (optional Python)</label><textarea class="dkst-ta" id="pa_bd" rows="6" style="font-family:Consolas,monospace;font-size:12px"></textarea></div>');
		const $t=term($p);
		btns($p,[{ lbl:"Generate Patch", cls:"dkst-btn-p", fn:()=>{
			if(!gv("pa_ap")||!gv("pa_mo")){frappe.throw("App and Patch Module required");return;}
			api("frappe_devkit.api.patch_builder.scaffold_patch",{app_name:gv("pa_ap"),patch_module:gv("pa_mo"),description:gv("pa_de"),execute_body:gv("pa_bd")},$t);
		}}]);
	};

	/* ── Tasks / Scheduler ── */
	PANELS.tasks = function($p) {
		$p.append(phdr("Tasks / Scheduler","Scaffold tasks.py with all frequency stubs ready to implement.",icoClock(20)));
		$p.append(info("Register task functions in hooks.py via the <b>Add Hook → Scheduler</b> panel after generating tasks.py."));
		const $c=card($p,"Target App");
		$c.append(`<div class="dkst-g2">${AppSel("tk_ap")}</div>`);
		loadApps().then(()=>fillSel($c.find("#tk_ap"),_apps,"select app"));
		$c.append(`<div class="dkst-div"></div>
		${secLbl("Frequency stubs that will be generated")}
		<div class="dkst-checks">
			${CHK("tk_all","all — every tick (~1 min)")} ${CHK("tk_d","daily",1)} ${CHK("tk_h","hourly",1)}
			${CHK("tk_w","weekly",1)} ${CHK("tk_m","monthly",1)}
			${CHK("tk_dl","daily_long")} ${CHK("tk_hl","hourly_long")} ${CHK("tk_wl","weekly_long")} ${CHK("tk_ml","monthly_long")}
		</div>`);
		const $t=term($p);
		btns($p,[{ lbl:"Generate tasks.py", cls:"dkst-btn-p", fn:()=>{
			if(!gv("tk_ap")){frappe.throw("Select an app");return;}
			api("frappe_devkit.api.patch_builder.scaffold_tasks_file",{app_name:gv("tk_ap")},$t);
		}}]);
	};

	/* ── Permissions ── */
	PANELS.perms = function($p) {
		$p.append(phdr("Permissions","Scaffold permissions.py with query conditions and has_permission stubs.",icoShield(20)));
		$p.append(info("Register the generated functions in <span class='dkst-code'>hooks.py</span> under <span class='dkst-code'>permission_query_conditions</span> and <span class='dkst-code'>has_permission</span>."));
		const $c=card($p,"Target App");
		$c.append(`<div class="dkst-g2">${AppSel("pm_ap")}</div>`);
		loadApps().then(()=>fillSel($c.find("#pm_ap"),_apps,"select app"));
		const $t=term($p);
		btns($p,[{ lbl:"Generate permissions.py", cls:"dkst-btn-p", fn:()=>{
			if(!gv("pm_ap")){frappe.throw("Select an app");return;}
			api("frappe_devkit.api.patch_builder.scaffold_permissions_file",{app_name:gv("pm_ap")},$t);
		}}]);
	};

	/* ── Migrate & Cache ── */
	PANELS.migrate = function($p) {
		$p.append(phdr("Migrate & Cache","Run bench migrate and clear-cache directly from the UI.",icoRefresh(20)));
		const $c=card($p,"Site Operations");
		$c.append(`<div class="dkst-checks">
			${CHK("mg_v","Verbose output")}
		</div>`);
		const $t=term($p);
		btns($p,[
			{ lbl:"Run Migrate",  cls:"dkst-btn-p", fn:()=>api("frappe_devkit.api.fixture_builder.run_migrate",{},$t) },
			{ lbl:"Clear Cache",  cls:"dkst-btn-s", fn:()=>api("frappe_devkit.api.fixture_builder.clear_cache",{},$t) },
		]);
	};

	/* ── Export Fixtures ── */
	PANELS.export = function($p) {
		$p.append(phdr("Export Fixtures","Export app fixtures to JSON — Custom Fields, Property Setters, Client Scripts etc.",icoExport(20)));
		$p.append(info("This runs <span class='dkst-code'>bench export-fixtures --app &lt;app&gt;</span> and writes the records currently in the DB into your fixtures/ JSON files."));
		const $c=card($p,"App Selection");
		$c.append(`<div class="dkst-g2">${AppSel("ex_ap")}</div>`);
		loadApps().then(()=>fillSel($c.find("#ex_ap"),_apps,"select app"));
		const $t=term($p);
		btns($p,[{ lbl:"Export Fixtures", cls:"dkst-btn-p", fn:()=>{
			if(!gv("ex_ap")){frappe.throw("Select an app");return;}
			api("frappe_devkit.api.fixture_builder.export_fixtures",{app_name:gv("ex_ap")},$t);
		}}]);
	};

	/* ── Scaffold Log ── */
	PANELS.log = function($p) {
		$p.append(phdr("Scaffold Log","Complete history of all files generated by DevKit Studio.",icoList(20)));
		const $tb=$(`<div style="display:flex;gap:10px;margin-bottom:16px;align-items:center">
			<button class="dkst-btn dkst-btn-s" id="lg-ref">↻ Refresh</button>
			<input class="dkst-inp" id="lg-q" style="width:260px" placeholder="Filter by app, action, reference…">
			<span style="flex:1"></span>
			<span style="font-size:12px;color:#9080b8" id="lg-cnt"></span>
		</div>`).appendTo($p);
		const $wrap=$(`<div class="dkst-card" style="padding:0;overflow:hidden"></div>`).appendTo($p);
		$wrap.append(`<table class="dkst-log-tbl">
			<thead><tr><th>#</th><th>Action</th><th>Reference</th><th>App</th><th>Module</th><th>When</th><th></th></tr></thead>
			<tbody id="dkst-lb"></tbody>
		</table>`);
		let all=[];
		const PILL={DocType:"p",Report:"g",App:"g","Custom Field":"p","Property Setter":"p",Hook:"b",Patch:"y","Print Format":"y"};
		function load(){
			frappe.call({method:"frappe.client.get_list",args:{doctype:"DevKit Scaffold Log",fields:["name","action","reference","app_name","module","scaffolded_on"],order_by:"scaffolded_on desc",limit_page_length:200},
				callback:r=>{all=r.message||[];render(all);}});
		}
		function render(rows){
			const $b=$("#dkst-lb"); $b.empty();
			$("#lg-cnt").text(`${rows.length} entries`);
			if(!rows.length){$b.html(`<tr><td colspan="7" class="dkst-empty">No scaffold history yet. Generate something!</td></tr>`);return;}
			rows.forEach((r,i)=>{
				const pc=PILL[r.action]||"p";
				$b.append(`<tr>
					<td style="color:#b0a8c8;width:40px">${i+1}</td>
					<td><span class="dkst-pill dkst-pill-${pc}">${r.action||""}</span></td>
					<td style="font-weight:600;color:#1e1a2e">${r.reference||""}</td>
					<td style="font-family:'Consolas',monospace;font-size:12px;color:#0055cc">${r.app_name||""}</td>
					<td style="color:#9080b8">${r.module||"—"}</td>
					<td style="color:#9080b8;font-size:12px">${frappe.datetime.str_to_user(r.scaffolded_on)||""}</td>
					<td><a href="/app/devkit-scaffold-log/${r.name}" target="_blank" style="color:#5c4da8;font-size:13px;font-weight:600">→</a></td>
				</tr>`);
			});
		}
		$p.on("click","#lg-ref",load);
		$p.on("input","#lg-q",function(){
			const q=this.value.toLowerCase();
			render(all.filter(r=>(r.app_name||"").toLowerCase().includes(q)||(r.action||"").toLowerCase().includes(q)||(r.reference||"").toLowerCase().includes(q)));
		});
		load();
	};


	/* ── Module Scaffold ── */
	PANELS.module = function($p) {
		$p.append(phdr("New Module","Scaffold a new module folder with all standard subdirectories and Module Def fixture.",icoFolder(20)));
		$p.append(info("Creates <span class='dkst-code'>doctype/</span>, <span class='dkst-code'>report/</span>, <span class='dkst-code'>print_format/</span>, <span class='dkst-code'>page/</span>, <span class='dkst-code'>workspace/</span> folders and adds entry to <span class='dkst-code'>modules.txt</span>."));
		const $c=card($p,"Module Details");
		$c.append(`<div class="dkst-g2">
			${AppSel("mod_ap")}
			${FR("mod_nm","Module Name","text","My Module")}
		</div>`);
		loadApps().then(()=>fillSel($c.find("#mod_ap"),_apps,"select app"));
		const $t=term($p);
		btns($p,[{ lbl:"Create Module", cls:"dkst-btn-p", fn:()=>{
			if(!gv("mod_ap")||!gv("mod_nm")){frappe.throw("App and Module Name required");return;}
			api("frappe_devkit.api.advanced_builder.scaffold_module",{app_name:gv("mod_ap"),module_name:gv("mod_nm")},$t);
		}}]);
	};

	/* ── Workspace ── */
	PANELS.workspace = function($p) {
		$p.append(phdr("Workspace","Scaffold a Desk Workspace with shortcuts, charts and number cards.",icoLayout(20)));
		const $c1=card($p,"Workspace Identity");
		$c1.append(`<div class="dkst-g2">
			${AppSel("ws_ap")} ${ModSel("ws_mo")}
			${FR("ws_nm","Workspace Name","text","My Workspace")}
			${F("ws_std","Is Standard","select","","",[["Yes","Yes"],["No","No"]])}
			<div class="dkst-fld"><label class="dkst-lbl">Roles (comma-separated)</label>
				<input class="dkst-inp" id="ws_rl" placeholder="System Manager,Accounts Manager"></div>
		</div>`);
		wireAMD($c1,"ws_ap","ws_mo",null);

		const $c2=card($p,"Shortcuts");
		$c2.append(`<div class="dkst-tbl-wrap"><table class="dkst-tbl">
			<thead><tr><th>Label</th><th>Link To (DocType/Page/Report)</th><th>Type</th><th>Color</th><th></th></tr></thead>
			<tbody id="ws-srows"></tbody>
		</table></div>`);
		$(`<div class="dkst-add-row">+ Add Shortcut</div>`).appendTo($c2).on("click",()=>addWsS());
		[{lbl:"Sales Order",lt:"Sales Order",ty:"DocType",col:"#5c4da8"},
		 {lbl:"Sales Invoice",lt:"Sales Invoice",ty:"DocType",col:"#1a7a3a"}].forEach(addWsS);

		function addWsS(d={}) {
			const $tr=$(`<tr>
				<td><input class="dkst-inp f-lbl" value="${d.lbl||''}" placeholder="Sales Order"></td>
				<td><input class="dkst-inp f-lt"  value="${d.lt||''}"  placeholder="Sales Order"></td>
				<td><select class="dkst-sel f-ty"><option ${d.ty==="DocType"?"selected":""}>DocType</option><option ${d.ty==="Page"?"selected":""}>Page</option><option ${d.ty==="Report"?"selected":""}>Report</option><option ${d.ty==="URL"?"selected":""}>URL</option></select></td>
				<td><input type="color" value="${d.col||'#5c4da8'}" class="f-col" style="width:40px;height:32px;border:none;cursor:pointer;background:none;"></td>
				<td><button class="dkst-del-btn">×</button></td>
			</tr>`);
			$tr.find(".dkst-del-btn").on("click",()=>$tr.remove());
			$("#ws-srows").append($tr);
		}

		const $t=term($p);
		btns($p,[{ lbl:"Generate Workspace", cls:"dkst-btn-p", fn:()=>{
			if(!gv("ws_ap")||!gv("ws_mo")||!gv("ws_nm")){frappe.throw("App, Module and Name required");return;}
			const shortcuts=[];
			$("#ws-srows tr").each(function(){
				const lbl=$(this).find(".f-lbl").val().trim();
				if(lbl) shortcuts.push({label:lbl,link_to:$(this).find(".f-lt").val().trim(),type:$(this).find(".f-ty").val(),color:$(this).find(".f-col").val()});
			});
			const roles=gv("ws_rl").split(",").map(s=>s.trim()).filter(Boolean);
			api("frappe_devkit.api.advanced_builder.scaffold_workspace",{
				app_name:gv("ws_ap"),module_name:gv("ws_mo"),workspace_name:gv("ws_nm"),
				is_standard:gv("ws_std")||"Yes",
				roles:JSON.stringify(roles),shortcuts:JSON.stringify(shortcuts),
			},$t);
		}}]);
	};

	/* ── Dashboard Chart ── */
	PANELS.dashboard_chart = function($p) {
		$p.append(phdr("Dashboard Chart","Scaffold a Dashboard Chart fixture for Frappe Desk dashboards.",icoChart(20)));
		const $c=card($p,"Chart Configuration");
		$c.append(`<div class="dkst-g2">
			${AppSel("dc_ap")} ${ModSel("dc_mo")}
			${FR("dc_nm","Chart Name","text","Monthly Sales")}
			${F("dc_ty","Chart Type","select","","",[["Count","Count"],["Sum","Sum"],["Average","Average"],["Group By","Group By"]])}
			${FR("dc_dt","DocType","text","Sales Invoice")}
			${F("dc_bo","Based On (date field)","text","posting_date")}
			${F("dc_vl","Value Field (for Sum/Avg)","text","grand_total")}
			${F("dc_ti","Time Interval","select","","",[["Daily","Daily"],["Weekly","Weekly"],["Monthly","Monthly"],["Quarterly","Quarterly"],["Yearly","Yearly"]])}
			${F("dc_ts","Timespan","select","","",[["Last Month","Last Month"],["Last Quarter","Last Quarter"],["Last Year","Last Year"],["Last 3 Years","Last 3 Years"]])}
			<div class="dkst-fld"><label class="dkst-lbl">Color</label>
				<input type="color" id="dc_cl" value="#7c5cbf" style="width:60px;height:36px;border:1px solid #d0c8e8;border-radius:5px;cursor:pointer;"></div>
		</div>`);
		wireAMD($c,"dc_ap","dc_mo",null);
		const $t=term($p);
		btns($p,[{ lbl:"Add Dashboard Chart", cls:"dkst-btn-p", fn:()=>{
			if(!gv("dc_ap")||!gv("dc_nm")||!gv("dc_dt")){frappe.throw("App, Name and DocType required");return;}
			api("frappe_devkit.api.advanced_builder.scaffold_dashboard_chart",{
				app_name:gv("dc_ap"),module_name:gv("dc_mo"),chart_name:gv("dc_nm"),
				chart_type:gv("dc_ty"),doctype:gv("dc_dt"),based_on:gv("dc_bo"),
				value_based_on:gv("dc_vl"),time_interval:gv("dc_ti"),timespan:gv("dc_ts"),
				color:$('#dc_cl').val(),
			},$t);
		}}]);
	};

	/* ── Number Card ── */
	PANELS.number_card = function($p) {
		$p.append(phdr("Number Card","Scaffold a Number Card for dashboards showing counts, sums or averages.",icoHash(20)));
		const $c=card($p,"Number Card Configuration");
		$c.append(`<div class="dkst-g2">
			${AppSel("nc_ap")} ${ModSel("nc_mo")}
			${FR("nc_nm","Card Name","text","Total Open Orders")}
			${FR("nc_dt","DocType","text","Sales Order")}
			${F("nc_fn","Function","select","","",[["Count","Count"],["Sum","Sum"],["Average","Average"],["Minimum","Minimum"],["Maximum","Maximum"]])}
			${F("nc_af","Aggregate Field (Sum/Avg)","text","grand_total")}
			<div class="dkst-fld"><label class="dkst-lbl">Color</label>
				<input type="color" id="nc_cl" value="#5c4da8" style="width:60px;height:36px;border:1px solid #d0c8e8;border-radius:5px;cursor:pointer;"></div>
			<div class="dkst-fld"><label class="dkst-lbl">Filters JSON</label>
				<textarea class="dkst-ta" id="nc_fi" rows="3" style="font-family:monospace;font-size:12px">[["status","=","Open"]]</textarea></div>
		</div>`);
		wireAMD($c,"nc_ap","nc_mo",null);
		const $t=term($p);
		btns($p,[{ lbl:"Add Number Card", cls:"dkst-btn-p", fn:()=>{
			if(!gv("nc_ap")||!gv("nc_nm")||!gv("nc_dt")){frappe.throw("App, Name and DocType required");return;}
			api("frappe_devkit.api.advanced_builder.scaffold_number_card",{
				app_name:gv("nc_ap"),module_name:gv("nc_mo"),card_name:gv("nc_nm"),
				doctype:gv("nc_dt"),function:gv("nc_fn"),aggregate_function_based_on:gv("nc_af"),
				filters_json:gv("nc_fi"),color:$('#nc_cl').val(),
			},$t);
		}}]);
	};

	/* ── Notification ── */
	PANELS.notification = function($p) {
		$p.append(phdr("Notification","Scaffold a Frappe Notification fixture — email, system or Slack alerts.",icoBell(20)));
		const $c1=card($p,"Notification Settings");
		$c1.append(`<div class="dkst-g2">
			${AppSel("nt_ap")}
			${FR("nt_nm","Notification Name","text","New Sales Order Alert")}
			${F("nt_ch","Channel","select","","",[["Email","Email"],["System Notification","System Notification"],["Slack","Slack"],["SMS","SMS"]])}
			${F("nt_dt","DocType","text","Sales Order")}
			${F("nt_ev","Event","select","","",[["New","New"],["Save","Save"],["Submit","Submit"],["Cancel","Cancel"],["Days After","Days After"],["Days Before","Days Before"],["Value Change","Value Change"],["Custom","Custom"]])}
			${F("nt_cd","Condition (Python)","text","doc.grand_total > 100000")}
		</div>`);
		loadApps().then(()=>fillSel($c1.find("#nt_ap"),_apps,"select app"));

		const $c2=card($p,"Email Content");
		$c2.append(`<div class="dkst-fld" style="margin-bottom:12px"><label class="dkst-lbl">Subject</label>
			<input class="dkst-inp" id="nt_su" placeholder="[{{ doc.doctype }}] {{ doc.name }} has been submitted"></div>
		<div class="dkst-fld"><label class="dkst-lbl">Message (HTML / Jinja2)</label>
		<textarea class="dkst-ta" id="nt_ms" rows="8" style="font-family:monospace;font-size:12.5px"><h3>{{ doc.name }}</h3>
<p>Document has been {{ doc.docstatus == 1 and 'submitted' or 'saved' }}.</p>
<table border="1" cellpadding="5">
  <tr><td>Customer</td><td>{{ doc.customer }}</td></tr>
  <tr><td>Amount</td><td>{{ doc.grand_total }}</td></tr>
</table>
<p><a href="{{ frappe.utils.get_url_to_form(doc.doctype, doc.name) }}">View in ERPNext</a></p></textarea></div>`);

		const $t=term($p);
		btns($p,[{ lbl:"Add Notification", cls:"dkst-btn-p", fn:()=>{
			if(!gv("nt_ap")||!gv("nt_nm")||!gv("nt_dt")){frappe.throw("App, Name and DocType required");return;}
			api("frappe_devkit.api.advanced_builder.scaffold_notification",{
				app_name:gv("nt_ap"),notification_name:gv("nt_nm"),doctype:gv("nt_dt"),
				event:gv("nt_ev"),condition:gv("nt_cd"),channel:gv("nt_ch"),
				subject:gv("nt_su"),message:gv("nt_ms"),
			},$t);
		}}]);
	};

	/* ── Server Script ── */
	PANELS.server_script = function($p) {
		$p.append(phdr("Server Script","Create a Server Script fixture — runs Python on DocType events, schedule or as API.",icoTerminal(20)));
		const $c=card($p,"Script Configuration");
		$c.append(`<div class="dkst-g2">
			${AppSel("ss_ap")}
			${FR("ss_nm","Script Name","text","My Server Script")}
			${F("ss_ty","Script Type","select","","",[["DocType Event","DocType Event"],["Scheduler Event","Scheduler Event"],["API","API"],["Permission Query","Permission Query"]])}
			${F("ss_dt","DocType (for DocType Event)","text","Sales Invoice")}
			${F("ss_ev","Event","select","","",[["before_insert","before_insert"],["validate","validate"],["on_submit","on_submit"],["on_cancel","on_cancel"],["after_insert","after_insert"],["on_trash","on_trash"]])}
		</div>
		<div class="dkst-fld" style="margin-top:12px">
			<label class="dkst-lbl">Script (Python)</label>
			<textarea class="dkst-ta" id="ss_sc" rows="12" style="font-family:'Consolas','Courier New',monospace;font-size:12.5px;line-height:1.7"># doc and method are available as globals
# frappe, _ are available

if doc.status == "Open":
    doc.custom_field = frappe.utils.nowdate()

frappe.msgprint(f"Processed {doc.name}")</textarea>
		</div>`);
		loadApps().then(()=>fillSel($c.find("#ss_ap"),_apps,"select app"));

		// Auto-update script template when type changes
		$c.find("#ss_ty").on("change",function(){
			const templates = {
				"DocType Event": "# doc and method are available\nif doc.status == \"Open\":\n    doc.custom_field = frappe.utils.nowdate()",
				"Scheduler Event": "import frappe\n\n# Runs on schedule\nresult = frappe.db.sql(\"SELECT COUNT(*) FROM `tabSales Order` WHERE status=%s\", \"Open\")\nfrappe.logger().info(f\"Open orders: {result}\")",
				"API": "# Accessible at /api/method/<api_method>\nimport frappe\n\nfrappe.response[\"message\"] = {\n    \"status\": \"success\",\n    \"data\": []\n}",
				"Permission Query": "# Return SQL WHERE condition string\nconditions = \"\"\nuser = frappe.session.user\nif not frappe.db.exists(\"Sales Person\", {\"user\": user}):\n    conditions = \"1=2\"  # Hide all for non-sales persons\n",
			};
			const tpl = templates[$(this).val()];
			if(tpl) $("#ss_sc").val(tpl);
		});

		const $t=term($p);
		btns($p,[{ lbl:"Add Server Script", cls:"dkst-btn-p", fn:()=>{
			if(!gv("ss_ap")||!gv("ss_nm")){frappe.throw("App and Script Name required");return;}
			api("frappe_devkit.api.advanced_builder.scaffold_server_script",{
				app_name:gv("ss_ap"),script_type:gv("ss_ty"),name:gv("ss_nm"),
				doctype:gv("ss_dt"),event:gv("ss_ev"),script:gv("ss_sc"),
			},$t);
		}}]);
	};

	/* ── Role Permissions ── */
	PANELS.role_perm = function($p) {
		$p.append(phdr("Role Permissions","Inspect and scaffold custom permission matrix for any DocType.",icoShield(20)));
		const $c1=card($p,"Load DocType Permissions");
		$c1.append(`<div class="dkst-g2">
			${AppSel("rp2_ap")}
			<div class="dkst-fld"><label class="dkst-lbl dkst-req">DocType</label>
				<input class="dkst-inp" id="rp2_dt" placeholder="Sales Invoice"></div>
		</div>`);
		loadApps().then(()=>fillSel($c1.find("#rp2_ap"),_apps,"select app"));

		const $matrix = $(`<div class="dkst-card" style="display:none"><div class="dkst-card-title">Permission Matrix</div>
			<div class="dkst-tbl-wrap"><table class="dkst-tbl" id="perm-tbl">
			<thead><tr><th>Role</th><th>R</th><th>W</th><th>C</th><th>D</th><th>Sub</th><th>Can</th><th>Amd</th><th>Prt</th><th>Eml</th><th>Exp</th><th>Shr</th><th>Own</th><th></th></tr></thead>
			<tbody id="perm-rows"></tbody>
			</table></div>
			<div class="dkst-add-row" id="perm-add-row">+ Add Role</div>
		</div>`).appendTo($p);

		const $t=term($p);

		btns($c1,[{ lbl:"Load Permissions", cls:"dkst-btn-s", fn:()=>{
			if(!gv("rp2_dt")){frappe.throw("DocType required");return;}
			frappe.call({method:"frappe_devkit.api.advanced_builder.get_doctype_permissions",
				args:{doctype:gv("rp2_dt")},
				callback:r=>{
					if(r.message?.status!=="success"){frappe.throw(r.message?.message||"Error");return;}
					$("#perm-rows").empty();
					r.message.permissions.forEach(p=>addPermRow(p));
					$matrix.show();
				}
			});
		}}]);

		$matrix.find("#perm-add-row").on("click",()=>addPermRow({}));

		function addPermRow(p={}) {
			const fields=["read","write","create","delete","submit","cancel","amend","print","email","export","share","if_owner"];
			const checks=fields.map(f=>`<td style="text-align:center"><input type="checkbox" class="f-${f}" ${p[f]?"checked":""}></td>`).join("");
			const $tr=$(`<tr>
				<td><input class="dkst-inp f-role" value="${p.role||''}" placeholder="System Manager" style="width:160px"></td>
				${checks}
				<td><button class="dkst-del-btn">×</button></td>
			</tr>`);
			$tr.find(".dkst-del-btn").on("click",()=>$tr.remove());
			$("#perm-rows").append($tr);
		}

		btns($p,[{ lbl:"Save to Fixtures", cls:"dkst-btn-p", fn:()=>{
			if(!gv("rp2_ap")||!gv("rp2_dt")){frappe.throw("App and DocType required");return;}
			const perms=[];
			$("#perm-rows tr").each(function(){
				const role=$(this).find(".f-role").val().trim();
				if(!role) return;
				perms.push({role,
					read:$(this).find(".f-read").is(":checked")?1:0,
					write:$(this).find(".f-write").is(":checked")?1:0,
					create:$(this).find(".f-create").is(":checked")?1:0,
					delete:$(this).find(".f-delete").is(":checked")?1:0,
					submit:$(this).find(".f-submit").is(":checked")?1:0,
					cancel:$(this).find(".f-cancel").is(":checked")?1:0,
					amend:$(this).find(".f-amend").is(":checked")?1:0,
					print:$(this).find(".f-print").is(":checked")?1:0,
					email:$(this).find(".f-email").is(":checked")?1:0,
					export:$(this).find(".f-export").is(":checked")?1:0,
					share:$(this).find(".f-share").is(":checked")?1:0,
					if_owner:$(this).find(".f-if_owner").is(":checked")?1:0,
				});
			});
			api("frappe_devkit.api.advanced_builder.scaffold_role_permission",{
				app_name:gv("rp2_ap"),doctype:gv("rp2_dt"),permissions:JSON.stringify(perms),
			},$t);
		}}]);
	};

	/* ── DocType Inspector ── */
	PANELS.dt_inspector = function($p) {
		$p.append(phdr("DocType Inspector","Inspect full meta-information — fields, permissions, hooks, DB columns.",icoSearch(20)));
		const $c=card($p,"Inspect");
		$c.append(`<div class="dkst-g2">
			${DtSel("ins_dt","DocType")}
			${ModSel("ins_mo","Filter Module")}
		</div>`);

		// Wire: load all doctypes without app filter
		const $modSel=$c.find("#ins_mo");
		const $dtSel =$c.find("#ins_dt");
		loadApps().then(()=>{
			const allMods=Object.values(_mods).flat();
			if(allMods.length) { fillSel($modSel,allMods,"all modules"); $modSel.prop("disabled",false); }
			else frappe.call({method:"frappe.client.get_list",args:{doctype:"Module Def",fields:["module_name"],limit_page_length:300},
				callback:r=>{
					const mods=(r.message||[]).map(m=>m.module_name);
					fillSel($modSel,mods,"all modules"); $modSel.prop("disabled",false);
				}});
		});
		$modSel.on("change",function(){
			const mod=this.value;
			$dtSel.prop("disabled",!mod).html('<option value="">— select doctype —</option>');
			if(!mod) return;
			loadDts(mod).then(ds=>{fillSel($dtSel,ds,"select doctype");$dtSel.prop("disabled",false);});
		});

		const $result=$(`<div id="ins-result" style="display:none"></div>`).appendTo($p);

		btns($c,[{ lbl:"Inspect", cls:"dkst-btn-p", fn:()=>{
			const dt=$dtSel.val()||gv("ins_dt");
			if(!dt){frappe.throw("Select a DocType");return;}
			frappe.call({method:"frappe_devkit.api.advanced_builder.inspect_doctype",
				args:{doctype:dt},
				callback:r=>{
					if(r.message?.status!=="success"){frappe.throw(r.message?.message||"Error");return;}
					const d=r.message;
					$result.show().empty();

					// Summary cards
					const $sum=$(`<div class="dkst-g4" style="margin-bottom:16px"></div>`).appendTo($result);
					[
						["Fields",d.field_count,"#5c4da8"],
						["DB Columns",d.db_columns.length,"#1a7a3a"],
						["Permissions",d.permissions.length,"#0055cc"],
						["Hooks",d.hooks.length,"#c0392b"],
					].forEach(([lbl,val,col])=>{
						$sum.append(`<div class="dkst-card" style="text-align:center;border-top:3px solid ${col};padding:14px">
							<div style="font-size:26px;font-weight:800;color:${col}">${val}</div>
							<div style="font-size:11px;color:#9080b8;font-weight:600;text-transform:uppercase;letter-spacing:.08em;margin-top:4px">${lbl}</div>
						</div>`);
					});

					// Flags
					const flags=[];
					if(d.is_submittable) flags.push(`<span class="dkst-pill dkst-pill-p">Submittable</span>`);
					if(d.is_single)      flags.push(`<span class="dkst-pill dkst-pill-b">Single</span>`);
					if(d.is_child)       flags.push(`<span class="dkst-pill dkst-pill-y">Child Table</span>`);
					if(flags.length) $result.append(`<div style="margin-bottom:12px;display:flex;gap:6px">${flags.join("")}</div>`);

					// Fields table
					const $fc=card($result,"Fields ("+d.field_count+")");
					$fc.append(`<div class="dkst-tbl-wrap"><table class="dkst-tbl">
						<thead><tr><th>Fieldname</th><th>Fieldtype</th><th>Label</th><th>Options</th><th>Req</th><th>List</th><th>Custom</th></tr></thead>
						<tbody>${d.fields.map(f=>`<tr>
							<td class="dkst-code" style="color:#5c4da8">${f.fieldname}</td>
							<td><span class="dkst-pill dkst-pill-p" style="font-size:10px">${f.fieldtype}</span></td>
							<td>${f.label||""}</td>
							<td style="font-size:12px;color:#7080a0">${f.options||""}</td>
							<td style="text-align:center">${f.reqd?"✓":""}</td>
							<td style="text-align:center">${f.in_list_view?"✓":""}</td>
							<td style="text-align:center">${f.is_custom?`<span class="dkst-pill dkst-pill-y" style="font-size:10px">custom</span>`:""}</td>
						</tr>`).join("")}</tbody>
					</table></div>`);

					// Hooks
					if(d.hooks.length) {
						const $hc=card($result,"Registered Hooks ("+d.hooks.length+")");
						$hc.append(`<table class="dkst-tbl">
							<thead><tr><th>App</th><th>Event</th><th>Handler</th></tr></thead>
							<tbody>${d.hooks.map(h=>`<tr><td>${h.app}</td><td>${h.event}</td><td class="dkst-code" style="font-size:12px">${h.handler}</td></tr>`).join("")}</tbody>
						</table>`);
					}

					// DB columns not in meta
					const metaFields=new Set(d.fields.map(f=>f.fieldname));
					const orphanCols=d.db_columns.filter(c=>!metaFields.has(c)&&!["name","creation","modified","modified_by","owner","docstatus","parent","parentfield","parenttype","idx"].includes(c));
					if(orphanCols.length) {
						const $oc=card($result,`⚠ DB Columns Not in Meta (${orphanCols.length}) — may be stale`);
						$oc.append(`<div style="display:flex;flex-wrap:wrap;gap:6px">${orphanCols.map(c=>`<span class="dkst-pill dkst-pill-r">${c}</span>`).join("")}</div>`);
					}
				}
			});
		}}]);
	};

	/* ── App Health Check ── */
	PANELS.health_check = function($p) {
		$p.append(phdr("App Health Check","Run a sanity check on any installed app — hooks, modules, fixtures, patches, syntax.",icoHeart(20)));
		const $c=card($p,"Select App");
		$c.append(`<div class="dkst-g2">${AppSel("hc_ap")}</div>`);
		loadApps().then(()=>fillSel($c.find("#hc_ap"),_apps,"select app"));

		const $res=$(`<div id="hc-result" style="display:none"></div>`).appendTo($p);

		btns($c,[{ lbl:"Run Health Check", cls:"dkst-btn-p", fn:()=>{
			if(!gv("hc_ap")){frappe.throw("Select an app");return;}
			$res.hide().empty();
			frappe.call({method:"frappe_devkit.api.advanced_builder.app_health_check",
				args:{app_name:gv("hc_ap")},
				callback:r=>{
					if(r.message?.status!=="success"){frappe.throw(r.message?.message||"Error");return;}
					const d=r.message;
					$res.show().empty();

					// Summary
					const {ok,warn,error}=d.results;
					$res.append(`<div class="dkst-g3" style="margin-bottom:16px">
						<div class="dkst-card" style="border-top:3px solid #1a7a3a;text-align:center;padding:14px">
							<div style="font-size:28px;font-weight:800;color:#1a7a3a">${ok.length}</div>
							<div style="font-size:11px;color:#9080b8;text-transform:uppercase;letter-spacing:.08em;margin-top:4px">Passed</div>
						</div>
						<div class="dkst-card" style="border-top:3px solid #c07a00;text-align:center;padding:14px">
							<div style="font-size:28px;font-weight:800;color:#c07a00">${warn.length}</div>
							<div style="font-size:11px;color:#9080b8;text-transform:uppercase;letter-spacing:.08em;margin-top:4px">Warnings</div>
						</div>
						<div class="dkst-card" style="border-top:3px solid #c0392b;text-align:center;padding:14px">
							<div style="font-size:28px;font-weight:800;color:#c0392b">${error.length}</div>
							<div style="font-size:11px;color:#9080b8;text-transform:uppercase;letter-spacing:.08em;margin-top:4px">Errors</div>
						</div>
					</div>`);

					if(error.length) {
						const $ec=card($res,"✗ Errors");
						error.forEach(e=>$ec.append(`<div style="padding:6px 0;border-bottom:1px solid #f0ebfa;color:#c0392b;font-size:12.5px">✗ ${e}</div>`));
					}
					if(warn.length) {
						const $wc=card($res,"⚠ Warnings");
						warn.forEach(w=>$wc.append(`<div style="padding:6px 0;border-bottom:1px solid #f0ebfa;color:#c07a00;font-size:12.5px">⚠ ${w}</div>`));
					}
					if(ok.length) {
						const $oc=card($res,"✓ Passed");
						ok.forEach(o=>$oc.append(`<div style="padding:5px 0;border-bottom:1px solid #f0ebfa;color:#1a7a3a;font-size:12px">✓ ${o}</div>`));
					}
				}
			});
		}}]);
	};

	/* ── Fixture Diff ── */
	PANELS.fixture_diff = function($p) {
		$p.append(phdr("Fixture Diff","Compare fixture JSON file records with current database records.",icoDiff(20)));
		$p.append(info("Identifies records that exist only in the fixture file, only in the DB, or are in sync."));
		const $c=card($p,"Select App & DocType");
		$c.append(`<div class="dkst-g2">
			${AppSel("fd_ap")}
			${F("fd_dt","DocType (fixture file name)","text","Custom Field","dkst-req")}
		</div>
		<div class="dkst-hint" style="margin-top:6px">e.g. "Custom Field" looks for <span class="dkst-code">fixtures/custom_field.json</span></div>`);
		loadApps().then(()=>fillSel($c.find("#fd_ap"),_apps,"select app"));

		const $res=$(`<div id="fd-result" style="display:none"></div>`).appendTo($p);

		btns($c,[{ lbl:"Run Diff", cls:"dkst-btn-p", fn:()=>{
			if(!gv("fd_ap")||!gv("fd_dt")){frappe.throw("App and DocType required");return;}
			$res.hide().empty();
			frappe.call({method:"frappe_devkit.api.advanced_builder.fixture_diff",
				args:{app_name:gv("fd_ap"),doctype:gv("fd_dt")},
				callback:r=>{
					if(r.message?.status!=="success"){frappe.throw(r.message?.message||"Error");return;}
					const d=r.message;
					$res.show().empty();
					$res.append(`<div class="dkst-g3" style="margin-bottom:16px">
						<div class="dkst-card" style="border-top:3px solid #1a7a3a;text-align:center;padding:14px">
							<div style="font-size:28px;font-weight:800;color:#1a7a3a">${d.in_both.length}</div>
							<div style="font-size:11px;color:#9080b8;text-transform:uppercase;letter-spacing:.08em;margin-top:4px">In Sync</div>
						</div>
						<div class="dkst-card" style="border-top:3px solid #0055cc;text-align:center;padding:14px">
							<div style="font-size:28px;font-weight:800;color:#0055cc">${d.only_in_file.length}</div>
							<div style="font-size:11px;color:#9080b8;text-transform:uppercase;letter-spacing:.08em;margin-top:4px">Only in File</div>
						</div>
						<div class="dkst-card" style="border-top:3px solid #c0392b;text-align:center;padding:14px">
							<div style="font-size:28px;font-weight:800;color:#c0392b">${d.only_in_db.length}</div>
							<div style="font-size:11px;color:#9080b8;text-transform:uppercase;letter-spacing:.08em;margin-top:4px">Only in DB</div>
						</div>
					</div>`);

					if(d.only_in_file.length) {
						const $c2=card($res,"Only in File — will be created on next migrate");
						$c2.append(`<div style="display:flex;flex-wrap:wrap;gap:6px">${d.only_in_file.map(n=>`<span class="dkst-pill dkst-pill-b">${n}</span>`).join("")}</div>`);
					}
					if(d.only_in_db.length) {
						const $c3=card($res,"Only in DB — not exported to fixture");
						$c3.append(`<div style="display:flex;flex-wrap:wrap;gap:6px">${d.only_in_db.map(n=>`<span class="dkst-pill dkst-pill-r">${n}</span>`).join("")}</div>`);
					}
					if(d.in_both.length) {
						const $c4=card($res,"In Sync ("+d.in_both.length+" records)");
						$c4.append(`<div style="display:flex;flex-wrap:wrap;gap:6px">${d.in_both.slice(0,50).map(n=>`<span class="dkst-pill dkst-pill-g">${n}</span>`).join("")}${d.in_both.length>50?`<span class="dkst-pill dkst-pill-p">+${d.in_both.length-50} more</span>`:""}</div>`);
					}
				}
			});
		}}]);
	};



	/* ── App Manager ── */
	PANELS.app_manager = function($p) {
		$p.append(phdr("App Manager","Install, uninstall and manage Frappe apps across bench sites.",icoPackage(20)));

		// ── Installed Apps Overview ──
		const $oc = card($p, "Bench Apps");
		$oc.append(`<div style="display:flex;gap:10px;margin-bottom:12px;align-items:center">
			<button class="dkst-btn dkst-btn-s" id="am-refresh-apps">↻ Refresh</button>
			<span style="flex:1"></span>
			<span style="font-size:12px;color:#9080b8" id="am-app-count"></span>
		</div>`);
		$oc.append(`<div class="dkst-tbl-wrap">
			<table class="dkst-tbl">
				<thead><tr>
					<th>App</th>
					<th>Title / Description</th>
					<th>Version</th>
					<th>Installed On</th>
					<th>Registry</th>
					<th></th>
				</tr></thead>
				<tbody id="am-app-rows"></tbody>
			</table>
		</div>`);

		// ── Sites Overview ──
		const $sc = card($p, "Bench Sites & Installed Apps");
		$sc.append(`<div style="display:flex;gap:10px;margin-bottom:12px;align-items:center">
			<button class="dkst-btn dkst-btn-s" id="am-refresh-sites">↻ Refresh</button>
		</div>
		<div id="am-sites-list"></div>`);

		// ── Install / Uninstall Panel ──
		const $ac = card($p, "Install / Uninstall App on Site");
		$ac.append(`<div class="dkst-g2">
			<div class="dkst-fld">
				<div style="display:flex;align-items:center;justify-content:space-between;gap:8px;margin-bottom:5px;">
					<label class="dkst-lbl dkst-req" style="margin:0;">App</label>
					<button class="dkst-ce-link" data-app-sel="am-sel-app" title="Open in DevKit Code Editor">⌨ Open in Editor ↗</button>
				</div>
				<select class="dkst-sel" id="am-sel-app"><option value="">— select app —</option></select></div>
			<div class="dkst-fld"><label class="dkst-lbl dkst-req">Site</label>
				<select class="dkst-sel" id="am-sel-site"><option value="">— select site —</option></select></div>
		</div>
		<div class="dkst-checks" style="margin-top:12px">
			<label class="dkst-chk"><input type="checkbox" id="am-force"><span>Force reinstall</span></label>
			<label class="dkst-chk"><input type="checkbox" id="am-dry-run"><span>Dry run (uninstall only)</span></label>
		</div>`);
		const $t = term($p);

		btns($ac, [
			{ lbl:"Install App on Site", cls:"dkst-btn-p", fn:() => {
				const app = $ac.find("#am-sel-app").val();
				const site = $ac.find("#am-sel-site").val();
				if (!app||!site) { frappe.throw("Select an app and a site"); return; }
				api("frappe_devkit.api.app_builder.install_app_on_site", {
					app_name: app, site: site,
					force: $ac.find("#am-force").is(":checked") ? 1 : 0,
				}, $t);
			}},
			{ lbl:"Uninstall App from Site", cls:"dkst-btn-r", fn:() => {
				const app = $ac.find("#am-sel-app").val();
				const site = $ac.find("#am-sel-site").val();
				if (!app||!site) { frappe.throw("Select an app and a site"); return; }
				if (!confirm(`Uninstall '${app}' from '${site}'? This will remove all data.`)) return;
				api("frappe_devkit.api.app_builder.uninstall_app_from_site", {
					app_name: app, site: site,
					dry_run: $ac.find("#am-dry-run").is(":checked") ? 1 : 0,
				}, $t);
			}},
			{ lbl:"Register in apps.txt + apps.json", cls:"dkst-btn-s", fn:() => {
				const app = $ac.find("#am-sel-app").val();
				if (!app) { frappe.throw("Select an app"); return; }
				api("frappe_devkit.api.app_builder.register_existing_app", { app_name: app }, $t);
			}},
		]);

		// ── load functions ──
		let _bench_apps = [], _bench_sites = [];

		function loadAppsAndSites() {
			setStatus("Loading bench apps and sites...");
			const $arows = $("#am-app-rows");
			$arows.html(`<tr><td colspan="6" class="dkst-empty">Loading...</td></tr>`);

			// Load apps
			frappe.call({ method: "frappe_devkit.api.app_builder.get_bench_apps",
				callback: r => {
					_bench_apps = r.message?.apps || [];
					$("#am-app-count").text(_bench_apps.length + " apps");
					$arows.empty();

					if (!_bench_apps.length) {
						$arows.html(`<tr><td colspan="6" class="dkst-empty">No apps found in bench/apps/</td></tr>`);
						return;
					}

					// Populate app selector
					const $appSel = $ac.find("#am-sel-app");
					$appSel.html('<option value="">— select app —</option>');
					_bench_apps.forEach(a => {
						$appSel.append(`<option value="${a.app}">${a.app} (${a.version})</option>`);
					});

					// Render table
					_bench_apps.forEach(a => {
						const txtPill  = a.in_sites_txt
							? `<span class="dkst-pill dkst-pill-g">✓ apps.txt</span>`
							: `<span class="dkst-pill dkst-pill-r">✗ apps.txt</span>`;
						const jsonPill = a.in_apps_json
							? `<span class="dkst-pill dkst-pill-g">✓ apps.json</span>`
							: `<span class="dkst-pill dkst-pill-r">✗ apps.json</span>`;
						const installPill = a.install_count > 0
							? `<span class="dkst-pill dkst-pill-b" title="${a.installed_on.join(', ')}">${a.install_count} site${a.install_count>1?'s':''}</span>`
							: `<span class="dkst-pill" style="background:#f4f0fc;color:#9080b8">not installed</span>`;
						const isCore   = ["frappe","erpnext","hrms"].includes(a.app);
						const needsFix = !a.in_sites_txt || !a.in_apps_json;
						const fixBtn   = (!isCore && needsFix)
							? `<button class="dkst-btn dkst-btn-s" style="padding:3px 10px;font-size:11px"
								onclick="frappe.call({method:'frappe_devkit.api.app_builder.register_existing_app',args:{app_name:'${a.app}'},callback:r=>frappe.show_alert({message:r.message?.message,indicator:'green'})})">⚡ Fix</button>`
							: '';
						$arows.append(`<tr>
							<td>
								<div style="font-weight:700;color:#5c4da8;font-size:13px">${a.app}</div>
								<div style="font-size:11px;color:#9080b8;margin-top:2px">${a.publisher||''}</div>
							</td>
							<td>
								<div style="color:#1e1a2e;font-weight:500">${a.title||a.app}</div>
								<div style="font-size:11px;color:#9080b8;margin-top:2px;max-width:200px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap" title="${a.description||''}">${a.description||''}</div>
							</td>
							<td><span class="dkst-pill dkst-pill-p">${a.version}</span></td>
							<td>${installPill}</td>
							<td style="white-space:nowrap">${txtPill}&nbsp;${jsonPill}</td>
							<td>${fixBtn}</td>
						</tr>`);
					});
					setStatus("Ready");
				}
			});

			// Load sites
			const $sitesDiv = $("#am-sites-list");
			$sitesDiv.html(`<div class="dkst-empty">Loading...</div>`);
			frappe.call({ method: "frappe_devkit.api.app_builder.get_bench_sites",
				callback: r => {
					_bench_sites = r.message?.sites || [];
					$sitesDiv.empty();

					// Populate site selector
					const $siteSel = $ac.find("#am-sel-site");
					$siteSel.html('<option value="">— select site —</option>');
					_bench_sites.forEach(s => {
						$siteSel.append(`<option value="${s.site}">${s.site} (${s.app_count} apps)</option>`);
					});

					if (!_bench_sites.length) {
						$sitesDiv.html(`<div class="dkst-empty">No sites found</div>`);
						return;
					}

					// Render sites as cards
					const $grid = $(`<div class="dkst-g2"></div>`).appendTo($sitesDiv);
					_bench_sites.forEach(s => {
						const $c2 = $(`<div class="dkst-card" style="border-left:3px solid #5c4da8;padding:14px 18px"></div>`).appendTo($grid);
						$c2.append(`<div style="font-weight:700;color:#1e1a2e;font-size:14px;margin-bottom:8px">${s.site}</div>`);
						$c2.append(`<div style="font-size:11px;color:#9080b8;margin-bottom:8px">${s.app_count} apps installed</div>`);
						$c2.append(`<div style="display:flex;flex-wrap:wrap;gap:5px">
							${s.installed.map(a => `<span class="dkst-pill dkst-pill-p">${a}</span>`).join("")}
						</div>`);
					});
				}
			});
		}

		$p.on("click","#am-refresh-apps,#am-refresh-sites", loadAppsAndSites);
		loadAppsAndSites();
	};


	/* ── site manager icon helpers ── */
	// ─── minimal SVG icons needed by site panels ─────────────────────────────────
	function _svgG(s)  { return `<svg width="${s}" height="${s}" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><line x1="2" y1="12" x2="22" y2="12"/><path d="M12 2a15.3 15.3 0 0 1 4 10 15.3 15.3 0 0 1-4 10 15.3 15.3 0 0 1-4-10 15.3 15.3 0 0 1 4-10z"/></svg>`; }
	function _svgP(s)  { return `<svg width="${s}" height="${s}" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="16"/><line x1="8" y1="12" x2="16" y2="12"/></svg>`; }
	function _svgS(s)  { return `<svg width="${s}" height="${s}" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M19 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11l5 5v11a2 2 0 0 1-2 2z"/><polyline points="17 21 17 13 7 13 7 21"/><polyline points="7 3 7 8 15 8"/></svg>`; }
	function _svgSl(s) { return `<svg width="${s}" height="${s}" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="4" y1="21" x2="4" y2="14"/><line x1="4" y1="10" x2="4" y2="3"/><line x1="12" y1="21" x2="12" y2="12"/><line x1="12" y1="8" x2="12" y2="3"/><line x1="20" y1="21" x2="20" y2="16"/><line x1="20" y1="12" x2="20" y2="3"/><line x1="1" y1="14" x2="7" y2="14"/><line x1="9" y1="8" x2="15" y2="8"/><line x1="17" y1="16" x2="23" y2="16"/></svg>`; }
	function _svgPkg(s){ return `<svg width="${s}" height="${s}" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="16.5" y1="9.4" x2="7.5" y2="4.21"/><path d="M21 16V8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.73l7 4a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16z"/><polyline points="3.27 6.96 12 12.01 20.73 6.96"/><line x1="12" y1="22.08" x2="12" y2="12"/></svg>`; }
	function _svgT(s)  { return `<svg width="${s}" height="${s}" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M14.7 6.3a1 1 0 0 0 0 1.4l1.6 1.6a1 1 0 0 0 1.4 0l3.77-3.77a6 6 0 0 1-7.94 7.94l-6.91 6.91a2.12 2.12 0 0 1-3-3l6.91-6.91a6 6 0 0 1 7.94-7.94l-3.76 3.76z"/></svg>`; }
	



	/* ═══════════════════════════════════════════════════
	   SITE MANAGER
	   ═══════════════════════════════════════════════════ */

	// ── Site helpers ──────────────────────────────────
	function loadSiteSelect($sel, ph) {
		$sel.html('<option value="">— loading... —</option>').prop('disabled', true);
		frappe.call({ method: 'frappe_devkit.api.site_manager.list_sites',
			callback: r => {
				$sel.empty().prop('disabled', false);
				if (ph) $sel.append(`<option value="">— ${ph} —</option>`);
				(r.message?.sites || []).forEach(s =>
					$sel.append(`<option value="${s.site}">${s.site} (${s.app_count} apps)</option>`)
				);
			}
		});
	}
	function smCard($p, title) {
		const $c = $('<div class="dkst-card"></div>').appendTo($p);
		if (title) $c.append(`<div class="dkst-card-title">${title}</div>`);
		return $c;
	}
	function smTerm($p) {
		return $('<div class="dkst-term">▶  Ready.</div>').appendTo($p);
	}
	function smBtns($p, list) {
		const $r = $('<div class="dkst-btnrow"></div>').appendTo($p);
		list.forEach(b => {
			const $b = $(`<button class="dkst-btn ${b.cls || 'dkst-btn-p'}">${b.lbl}</button>`).appendTo($r);
			$b.on('click', () => {
				$b.html('<span class="dkst-spin"></span> Running…').prop('disabled', true);
				setTimeout(() => { try { b.fn(); } catch(e){ console.error(e); } }, 60);
				setTimeout(() => { $b.html(b.lbl).prop('disabled', false); }, 8000);
			});
		});
		return $r;
	}
	function smApi(method, args, $t) {
		$t.text('▶  Running…').removeClass('ok err');
		frappe.call({ method, args,
			callback: r => {
				const m = r.message;
				if (m?.status === 'success') {
					$t.addClass('ok');
					let out = `✓  ${m.message}`;
					if (m.stdout?.trim()) out += `\n\nOutput:\n${m.stdout.trim()}`;
					if (m.stderr?.trim()) out += `\n\nStderr:\n${m.stderr.trim()}`;
					if (m.info)   out += `\n\n${JSON.stringify(m.info, null, 2)}`;
					if (m.config) out += `\n\n${JSON.stringify(m.config, null, 2)}`;
					if (m.backups?.length) {
						out += '\n\nBackups:\n';
						m.backups.slice(0,10).forEach(b => out += `  ${b.name}  (${b.size}  ${b.date})\n`);
					}
					$t.text(out);
					frappe.show_alert({ message: m.message, indicator: 'green' });
				} else {
					$t.addClass('err');
					let out = `✗  ${m?.message || 'Error'}`;
					if (m?.stdout?.trim()) out += `\n\nOutput:\n${m.stdout.trim()}`;
					if (m?.stderr?.trim()) out += `\n\nStderr:\n${m.stderr.trim()}`;
					$t.text(out);
				}
			},
			error: e => $t.addClass('err').text(`✗  ${e.responseJSON?.exception || JSON.stringify(e)}`)
		});
	}
	function smGv(id) { return ($(`#${id}`).val() || '').trim(); }
	function smSite(formSel) {
		const s = $(formSel).val();
		if (!s) { frappe.throw('Select a site first'); }
		return s;
	}

	// ── Site Overview ──────────────────────────────────
	PANELS.site_overview = function($p) {
		$p.append(phdr('Site Overview', 'All bench sites — apps, status, config, disk.', icoGlobe(20)));
		const $tb = $('<div style="display:flex;gap:10px;margin-bottom:16px;align-items:center"></div>').appendTo($p);
		$('<button class="dkst-btn dkst-btn-s" id="sov-ref">↻ Refresh</button>').appendTo($tb);
		$('<span style="flex:1"></span>').appendTo($tb);
		$('<span style="font-size:12px;color:#9080b8" id="sov-cnt"></span>').appendTo($tb);
		const $grid = $('<div id="sov-grid"></div>').appendTo($p);

		function loadOverview() {
			$grid.html('<div class="dkst-empty">Loading…</div>');
			frappe.call({ method: 'frappe_devkit.api.site_manager.list_sites',
				callback: r => {
					const sites = r.message?.sites || [];
					$grid.empty();
					$('#sov-cnt').text(`${sites.length} site(s)`);
					if (!sites.length) { $grid.html('<div class="dkst-empty">No sites found in this bench.</div>'); return; }
					sites.forEach(s => {
						const col = s.maintenance ? '#c0392b' : '#5c4da8';
						const $c = $(`<div class="dkst-card" style="border-left:3px solid ${col};margin-bottom:14px"></div>`).appendTo($grid);
						$c.append(`<div style="display:flex;align-items:center;gap:10px;margin-bottom:10px">
							<div style="font-size:15px;font-weight:700;color:#1e1a2e;flex:1">${s.site}</div>
							${s.maintenance ? '<span class="dkst-pill dkst-pill-r">⚠ Maintenance</span>' : '<span class="dkst-pill dkst-pill-g">● Active</span>'}
						</div>`);
						const pills = s.installed.map(a => `<span class="dkst-pill dkst-pill-p" style="font-size:11px">${a}</span>`).join(' ');
						$c.append(`<div style="margin-bottom:6px"><span style="font-size:11px;color:#9080b8;font-weight:700;text-transform:uppercase;letter-spacing:.07em">Apps (${s.app_count})</span><div style="margin-top:5px;display:flex;flex-wrap:wrap;gap:5px">${pills || '<span style="color:#b0a8c8;font-size:12px">none</span>'}</div></div>`);
						if (s.db_name) $c.append(`<div style="font-size:12px;color:#7a70a8">DB: <span class="dkst-code">${s.db_name}</span></div>`);
					});
				}
			});
		}
		$p.on('click', '#sov-ref', loadOverview);
		loadOverview();
	};

	// ── Create Site ──────────────────────────────────
	PANELS.site_create = function($p) {
		$p.append(phdr('Create Site', 'Scaffold a new Frappe site: bench new-site <site>', icoPlus(20)));
		const $c = smCard($p, 'New Site Details');
		$c.append(`<div class="dkst-g2">
			<div class="dkst-fld dkst-full"><label class="dkst-lbl dkst-req">Site Name (FQDN)</label>
				<input class="dkst-inp" id="sc-name" placeholder="mysite.localhost">
				<span class="dkst-hint">Use .localhost for local dev e.g. myapp.localhost</span></div>
			<div class="dkst-fld"><label class="dkst-lbl dkst-req">Admin Password</label>
				<input class="dkst-inp" type="password" id="sc-apwd" placeholder="Administrator password"></div>
			<div class="dkst-fld"><label class="dkst-lbl">MariaDB Root Password</label>
				<input class="dkst-inp" type="password" id="sc-dbpwd" placeholder="Leave empty if not required"></div>
			<div class="dkst-fld"><label class="dkst-lbl">DB Name (optional)</label>
				<input class="dkst-inp" id="sc-dbn" placeholder="auto-generated if empty"></div>
			<div class="dkst-fld"><label class="dkst-lbl">DB Type</label>
				<select class="dkst-sel" id="sc-dbt">
					<option value="mariadb">MariaDB (default)</option>
					<option value="postgres">PostgreSQL</option>
				</select></div>
		</div>`);

		const $c2 = smCard($p, 'Apps to Install');
		$c2.append('<div style="font-size:12px;color:#7a70a8;margin-bottom:10px">Apps to install during site creation (frappe is always included).</div>');
		const $appWrap = $('<div class="dkst-checks" id="sc-apps"></div>').appendTo($c2);
		frappe.call({ method: 'frappe_devkit.api.app_builder.get_bench_apps',
			callback: r => {
				$appWrap.empty();
				(r.message?.apps || []).filter(a => a.app !== 'frappe').forEach(a =>
					$appWrap.append(`<label class="dkst-chk"><input type="checkbox" class="sc-app-chk" value="${a.app}"><span>${a.app} <span style="color:#9080b8;font-size:11px">v${a.version}</span></span></label>`)
				);
			}
		});

		const $t = smTerm($p);
		smBtns($p, [{ lbl: 'Create Site', cls: 'dkst-btn-p', fn: () => {
			const name = smGv('sc-name');
			const apwd = $c.find('#sc-apwd').val().trim();
			if (!name) { frappe.throw('Site name required'); return; }
			if (!apwd) { frappe.throw('Admin password required'); return; }
			const apps = [];
			$('.sc-app-chk:checked').each(function() { apps.push($(this).val()); });
			smApi('frappe_devkit.api.site_manager.create_site', {
				site: name, admin_password: apwd,
				db_password: $c.find('#sc-dbpwd').val().trim(),
				db_name: smGv('sc-dbn'), db_type: $c.find('#sc-dbt').val(),
				apps: JSON.stringify(apps),
			}, $t);
		}}]);
	};

	// ── Backup & Restore ──────────────────────────────────
	PANELS.site_backup = function($p) {
		$p.append(phdr('Backup & Restore', 'Take, list and restore site backups.', icoSave(20)));

		// Take backup
		const $bc = smCard($p, 'Take Backup');
		$bc.append(`<div class="dkst-g2">
			<div class="dkst-fld"><label class="dkst-lbl dkst-req">Site</label>
				<select class="dkst-sel" id="bk-site"></select></div>
			<div class="dkst-fld"><label class="dkst-lbl">Options</label>
				<div class="dkst-checks" style="margin-top:6px">
					<label class="dkst-chk"><input type="checkbox" id="bk-files"><span>Include files</span></label>
					<label class="dkst-chk"><input type="checkbox" id="bk-comp" checked><span>Compress</span></label>
				</div></div>
		</div>`);
		loadSiteSelect($bc.find('#bk-site'), 'select site');
		const $t1 = smTerm($p);
		smBtns($bc, [{ lbl: 'Take Backup', cls: 'dkst-btn-p', fn: () => {
			const site = $bc.find('#bk-site').val();
			if (!site) { frappe.throw('Select a site'); return; }
			smApi('frappe_devkit.api.site_manager.backup_site', {
				site, with_files: $('#bk-files').is(':checked') ? 1 : 0,
				compress: $('#bk-comp').is(':checked') ? 1 : 0,
			}, $t1);
		}}]);

		// List backups
		const $lc = smCard($p, 'List Backups');
		$lc.append(`<div class="dkst-g2"><div class="dkst-fld"><label class="dkst-lbl dkst-req">Site</label>
			<select class="dkst-sel" id="bl-site"></select></div></div>
		<div id="bl-res" style="margin-top:12px"></div>`);
		loadSiteSelect($lc.find('#bl-site'), 'select site');
		smBtns($lc, [{ lbl: 'List Backups', cls: 'dkst-btn-s', fn: () => {
			const site = $lc.find('#bl-site').val();
			if (!site) { frappe.throw('Select a site'); return; }
			frappe.call({ method: 'frappe_devkit.api.site_manager.list_backups', args: { site },
				callback: r => {
					const bks = r.message?.backups || [];
					const $d = $('#bl-res').empty();
					if (!bks.length) { $d.html('<div style="color:#9080b8;font-size:12px">No backups found.</div>'); return; }
					const $tbl = $('<table class="dkst-tbl"><thead><tr><th>File</th><th>Size</th><th>Date</th><th>Type</th></tr></thead><tbody></tbody></table>').appendTo($d);
					bks.forEach(b => $tbl.find('tbody').append(`<tr>
						<td style="font-family:monospace;font-size:12px;color:#5c4da8">${b.name}</td>
						<td>${b.size}</td><td>${b.date}</td>
						<td><span class="dkst-pill dkst-pill-${b.type==='database'?'p':'b'}">${b.type}</span></td>
					</tr>`));
				}
			});
		}}]);

		// Restore
		const $rc = smCard($p, 'Restore from Backup');
		$rc.append(`<div class="dkst-g2">
			<div class="dkst-fld"><label class="dkst-lbl dkst-req">Site</label>
				<select class="dkst-sel" id="rs-site"></select></div>
			<div class="dkst-fld"><label class="dkst-lbl dkst-req">DB Backup File (full path)</label>
				<input class="dkst-inp" id="rs-file" placeholder="/path/to/backup-database.sql.gz"></div>
			<div class="dkst-fld"><label class="dkst-lbl">Private Files Backup</label>
				<input class="dkst-inp" id="rs-priv" placeholder="/path/to/private-files.tar"></div>
			<div class="dkst-fld"><label class="dkst-lbl">Public Files Backup</label>
				<input class="dkst-inp" id="rs-pub" placeholder="/path/to/public-files.tar"></div>
			<div class="dkst-fld"><label class="dkst-lbl">Reset Admin Password</label>
				<input class="dkst-inp" type="password" id="rs-apwd" placeholder="optional"></div>
		</div>
		<div style="background:#fde8e6;border:1px solid #e8a8a0;border-radius:5px;padding:10px 14px;font-size:12px;color:#7a2020;margin-top:10px">
			⚠ Restore overwrites all existing data in the site database.
		</div>`);
		loadSiteSelect($rc.find('#rs-site'), 'select site');
		const $t2 = smTerm($p);
		smBtns($p, [{ lbl: 'Restore Site', cls: 'dkst-btn-r', fn: () => {
			const site = $rc.find('#rs-site').val();
			const file = smGv('rs-file');
			if (!site || !file) { frappe.throw('Site and DB backup file required'); return; }
			if (!confirm(`Restore '${site}' from backup? This overwrites ALL current data.`)) return;
			smApi('frappe_devkit.api.site_manager.restore_site', {
				site, backup_file: file,
				with_private_files: smGv('rs-priv'),
				with_public_files: smGv('rs-pub'),
				admin_password: $rc.find('#rs-apwd').val().trim(),
			}, $t2);
		}}]);
	};

	// ── Site Config ──────────────────────────────────
	PANELS.site_config = function($p) {
		$p.append(phdr('Site Config', 'Read, set and remove site_config.json keys.', icoSliders(20)));

		// Read config
		const $rc = smCard($p, 'Read Config');
		$rc.append(`<div class="dkst-g2"><div class="dkst-fld"><label class="dkst-lbl dkst-req">Site</label>
			<select class="dkst-sel" id="cfg-site"></select></div></div>
		<div id="cfg-table" style="margin-top:12px"></div>`);
		loadSiteSelect($rc.find('#cfg-site'), 'select site');
		$rc.find('#cfg-site').on('change', function() {
			const site = this.value; if (!site) return;
			frappe.call({ method: 'frappe_devkit.api.site_manager.get_site_config', args: { site },
				callback: r => {
					const cfg = r.message?.config || {};
					const $d = $('#cfg-table').empty();
					const $tbl = $('<table class="dkst-tbl"><thead><tr><th>Key</th><th>Value</th></tr></thead><tbody></tbody></table>').appendTo($d);
					Object.entries(cfg).forEach(([k, v]) => $tbl.find('tbody').append(`<tr>
						<td style="font-family:monospace;color:#5c4da8;font-weight:600">${k}</td>
						<td style="font-family:monospace;font-size:12px;color:#1e1a2e">${JSON.stringify(v)}</td>
					</tr>`));
				}
			});
		});

		// Set config
		const $sc = smCard($p, 'Set / Update Config Key');
		$sc.append(`<div class="dkst-g2">
			<div class="dkst-fld"><label class="dkst-lbl dkst-req">Site</label>
				<select class="dkst-sel" id="set-site"></select></div>
			<div class="dkst-fld"><label class="dkst-lbl dkst-req">Key</label>
				<input class="dkst-inp" id="set-key" placeholder="e.g. max_file_size"></div>
			<div class="dkst-fld"><label class="dkst-lbl dkst-req">Value</label>
				<input class="dkst-inp" id="set-val" placeholder="value"></div>
			<div class="dkst-fld"><label class="dkst-lbl">Value Type</label>
				<select class="dkst-sel" id="set-type">
					<option value="string">String</option>
					<option value="int">Integer</option>
					<option value="bool">Boolean (0/1)</option>
					<option value="json">JSON</option>
				</select></div>
		</div>`);
		loadSiteSelect($sc.find('#set-site'), 'select site');
		const $t3 = smTerm($p);
		smBtns($sc, [
			{ lbl: 'Set Config', cls: 'dkst-btn-p', fn: () => {
				const site = $sc.find('#set-site').val();
				const key = smGv('set-key'); const val = smGv('set-val');
				if (!site||!key||!val) { frappe.throw('Site, Key and Value required'); return; }
				smApi('frappe_devkit.api.site_manager.set_site_config', {
					site, key, value: val, value_type: $sc.find('#set-type').val()
				}, $t3);
			}},
			{ lbl: 'Remove Key', cls: 'dkst-btn-r', fn: () => {
				const site = $sc.find('#set-site').val();
				const key = smGv('set-key');
				if (!site||!key) { frappe.throw('Site and Key required'); return; }
				if (!confirm(`Remove key '${key}' from '${site}'?`)) return;
				smApi('frappe_devkit.api.site_manager.remove_site_config', { site, key }, $t3);
			}},
		]);

		// Common config
		const $cc = smCard($p, 'Common Site Config (shared by all sites)');
		const $ccd = $('<div style="color:#9080b8;font-size:12px">Click to load…</div>').appendTo($cc);
		smBtns($cc, [{ lbl: 'Load Common Config', cls: 'dkst-btn-s', fn: () => {
			frappe.call({ method: 'frappe_devkit.api.site_manager.get_common_config',
				callback: r => {
					const cfg = r.message?.config || {};
					$ccd.empty();
					const $tbl = $('<table class="dkst-tbl"><thead><tr><th>Key</th><th>Value</th></tr></thead><tbody></tbody></table>').appendTo($ccd);
					Object.entries(cfg).forEach(([k,v]) => $tbl.find('tbody').append(`<tr>
						<td style="font-family:monospace;color:#5c4da8">${k}</td>
						<td style="font-family:monospace;font-size:12px">${JSON.stringify(v)}</td>
					</tr>`));
				}
			});
		}}]);
	};

	// ── Site Apps ──────────────────────────────────
	PANELS.site_apps = function($p) {
		$p.append(phdr('Install / Remove Apps', 'Install or uninstall apps on any site.', icoPackage(20)));
		const $c = smCard($p, 'App on Site');
		$c.append(`<div class="dkst-g2">
			<div class="dkst-fld"><label class="dkst-lbl dkst-req">Site</label>
				<select class="dkst-sel" id="sa-site"></select></div>
			<div class="dkst-fld">
				<div style="display:flex;align-items:center;justify-content:space-between;gap:8px;margin-bottom:5px;">
					<label class="dkst-lbl dkst-req" style="margin:0;">App</label>
					<button class="dkst-ce-link" data-app-sel="sa-app" title="Open in DevKit Code Editor">⌨ Open in Editor ↗</button>
				</div>
				<select class="dkst-sel" id="sa-app"><option value="">— select app —</option></select></div>
		</div>
		<div class="dkst-checks" style="margin-top:12px">
			<label class="dkst-chk"><input type="checkbox" id="sa-force"><span>Force reinstall</span></label>
			<label class="dkst-chk"><input type="checkbox" id="sa-dry"><span>Dry run (uninstall only)</span></label>
		</div>
		<div id="sa-installed" style="margin-top:14px"></div>`);

		loadSiteSelect($c.find('#sa-site'), 'select site');
		frappe.call({ method: 'frappe_devkit.api.app_builder.get_bench_apps',
			callback: r => {
				(r.message?.apps || []).forEach(a =>
					$c.find('#sa-app').append(`<option value="${a.app}">${a.app} (${a.version})</option>`)
				);
			}
		});
		$c.find('#sa-site').on('change', function() {
			const site = this.value;
			const $d = $('#sa-installed').empty();
			if (!site) return;
			frappe.call({ method: 'frappe_devkit.api.site_manager.list_sites',
				callback: r => {
					const s = (r.message?.sites || []).find(x => x.site === site);
					if (!s) return;
					$d.append(`<div style="font-size:11px;color:#9080b8;font-weight:700;text-transform:uppercase;letter-spacing:.08em;margin-bottom:6px">Currently installed on ${site}</div>
					<div style="display:flex;flex-wrap:wrap;gap:6px">
					${s.installed.map(a => `<span class="dkst-pill dkst-pill-p">${a}</span>`).join('')}
					</div>`);
				}
			});
		});

		const $t = smTerm($p);
		smBtns($p, [
			{ lbl: 'Install App', cls: 'dkst-btn-p', fn: () => {
				const site = $c.find('#sa-site').val(); const app = $c.find('#sa-app').val();
				if (!site||!app) { frappe.throw('Site and App required'); return; }
				smApi('frappe_devkit.api.app_builder.install_app_on_site', {
					app_name: app, site, force: $('#sa-force').is(':checked') ? 1 : 0
				}, $t);
			}},
			{ lbl: 'Uninstall App', cls: 'dkst-btn-r', fn: () => {
				const site = $c.find('#sa-site').val(); const app = $c.find('#sa-app').val();
				if (!site||!app) { frappe.throw('Site and App required'); return; }
				if (!confirm(`Uninstall '${app}' from '${site}'? This removes all app data.`)) return;
				smApi('frappe_devkit.api.app_builder.uninstall_app_from_site', {
					app_name: app, site, dry_run: $('#sa-dry').is(':checked') ? 1 : 0
				}, $t);
			}},
		]);
	};

	// ── Site Operations ──────────────────────────────────
	PANELS.site_ops = function($p) {
		$p.append(phdr('Operations', 'Migrate, cache, scheduler, maintenance, password, execute, drop.', icoTools(20)));

		// Global site selector
		const $sel = smCard($p, 'Site');
		$sel.append('<div class="dkst-g2"><div class="dkst-fld"><label class="dkst-lbl dkst-req">Select Site</label><select class="dkst-sel" id="ops-site"></select></div></div>');
		loadSiteSelect($sel.find('#ops-site'), 'select site');
		function gsite() { const s=$('#ops-site').val(); if(!s) frappe.throw('Select a site first'); return s; }

		// Sub tabs
		const $tabs = $(`<div class="dkst-stabs">
			<div class="dkst-stab active" data-t="mig">Migrate</div>
			<div class="dkst-stab" data-t="cch">Cache</div>
			<div class="dkst-stab" data-t="sch">Scheduler</div>
			<div class="dkst-stab" data-t="mnt">Maintenance</div>
			<div class="dkst-stab" data-t="pwd">Admin Password</div>
			<div class="dkst-stab" data-t="exc">Execute</div>
			<div class="dkst-stab" data-t="drp" style="color:#c0392b">Drop Site</div>
		</div>`).appendTo($p);
		const $pp = $('<div></div>').appendTo($p);
		function mkSub(id) {
			return $(`<div class="dkst-spanel ${id==='mig'?'active':''}" data-t="${id}"></div>`).appendTo($pp);
		}

		// Migrate
		const $mig = mkSub('mig');
		const $mc = smCard($mig, 'Migrate Site');
		$mc.append('<div class="dkst-checks"><label class="dkst-chk"><input type="checkbox" id="mig-skip"><span>Skip failing patches</span></label></div>');
		const $mt = smTerm($mig);
		smBtns($mc, [{ lbl: 'Run Migrate', cls: 'dkst-btn-p', fn: () => {
			smApi('frappe_devkit.api.site_manager.migrate_site', { site: gsite(), skip_failing: $('#mig-skip').is(':checked')?1:0 }, $mt);
		}}]);

		// Cache
		const $cch = mkSub('cch');
		const $cc = smCard($cch, 'Clear Cache');
		const $ct = smTerm($cch);
		smBtns($cc, [
			{ lbl: 'Clear Cache',         cls: 'dkst-btn-p', fn: () => smApi('frappe_devkit.api.site_manager.clear_site_cache',    { site: gsite() }, $ct) },
			{ lbl: 'Clear Website Cache', cls: 'dkst-btn-s', fn: () => smApi('frappe_devkit.api.site_manager.clear_website_cache', { site: gsite() }, $ct) },
			{ lbl: 'Set as Default Site', cls: 'dkst-btn-s', fn: () => smApi('frappe_devkit.api.site_manager.use_site',            { site: gsite() }, $ct) },
		]);

		// Scheduler
		const $sch = mkSub('sch');
		const $sc = smCard($sch, 'Scheduler Control');
		$sc.append('<div style="font-size:12.5px;color:#4a4470;margin-bottom:12px;line-height:1.7"><span class="dkst-code">enable/disable</span> — permanent &nbsp;·&nbsp; <span class="dkst-code">resume/suspend</span> — until restart</div>');
		const $st = smTerm($sch);
		smBtns($sc, [
			{ lbl: 'Status',   cls: 'dkst-btn-s', fn: () => smApi('frappe_devkit.api.site_manager.scheduler_action', { site: gsite(), action: 'status' },   $st) },
			{ lbl: 'Enable',   cls: 'dkst-btn-g', fn: () => smApi('frappe_devkit.api.site_manager.scheduler_action', { site: gsite(), action: 'enable' },   $st) },
			{ lbl: 'Disable',  cls: 'dkst-btn-s', fn: () => smApi('frappe_devkit.api.site_manager.scheduler_action', { site: gsite(), action: 'disable' },  $st) },
			{ lbl: 'Resume',   cls: 'dkst-btn-g', fn: () => smApi('frappe_devkit.api.site_manager.scheduler_action', { site: gsite(), action: 'resume' },   $st) },
			{ lbl: 'Suspend',  cls: 'dkst-btn-s', fn: () => smApi('frappe_devkit.api.site_manager.scheduler_action', { site: gsite(), action: 'suspend' },  $st) },
			{ lbl: 'Run Jobs', cls: 'dkst-btn-s', fn: () => smApi('frappe_devkit.api.site_manager.scheduler_action', { site: gsite(), action: 'run-jobs' }, $st) },
		]);

		// Maintenance
		const $mnt = mkSub('mnt');
		const $mn = smCard($mnt, 'Maintenance Mode');
		$mn.append('<div style="font-size:12.5px;color:#4a4470;margin-bottom:14px;line-height:1.7">While ON, visitors see a maintenance page. Administrators can still log in.</div>');
		const $mnt2 = smTerm($mnt);
		smBtns($mn, [
			{ lbl: 'Enable Maintenance',  cls: 'dkst-btn-r', fn: () => smApi('frappe_devkit.api.site_manager.set_maintenance_mode', { site: gsite(), enable: 1 }, $mnt2) },
			{ lbl: 'Disable Maintenance', cls: 'dkst-btn-g', fn: () => smApi('frappe_devkit.api.site_manager.set_maintenance_mode', { site: gsite(), enable: 0 }, $mnt2) },
		]);

		// Admin Password
		const $pwd = mkSub('pwd');
		const $pc = smCard($pwd, 'Reset Admin Password');
		$pc.append('<div class="dkst-g2"><div class="dkst-fld"><label class="dkst-lbl dkst-req">New Password</label><input class="dkst-inp" type="password" id="pwd-new" placeholder="Min 6 characters"></div><div class="dkst-fld"><label class="dkst-lbl dkst-req">Confirm</label><input class="dkst-inp" type="password" id="pwd-cf" placeholder="Repeat password"></div></div>');
		const $pt = smTerm($pwd);
		smBtns($pc, [{ lbl: 'Set Password', cls: 'dkst-btn-p', fn: () => {
			const p1 = $('#pwd-new').val().trim(); const p2 = $('#pwd-cf').val().trim();
			if (!p1 || p1.length < 6) { frappe.throw('Password must be at least 6 characters'); return; }
			if (p1 !== p2) { frappe.throw('Passwords do not match'); return; }
			smApi('frappe_devkit.api.site_manager.set_admin_password', { site: gsite(), new_password: p1 }, $pt);
		}}]);

		// Execute
		const $exc = mkSub('exc');
		const $ec = smCard($exc, 'Execute Python Expression');
		$ec.append('<div style="font-size:12.5px;color:#4a4070;margin-bottom:10px">Runs via <span class="dkst-code">bench execute</span> in the site context. Destructive operations are blocked.</div>');
		$ec.append('<div class="dkst-fld"><label class="dkst-lbl dkst-req">Expression</label><textarea class="dkst-ta" id="exc-sc" rows="6" style="font-family:Consolas,monospace;font-size:12.5px">frappe.db.count("Sales Invoice", {"status": "Open"})</textarea></div>');
		const $et = smTerm($exc);
		smBtns($ec, [{ lbl: 'Execute', cls: 'dkst-btn-p', fn: () => {
			const sc = smGv('exc-sc'); if (!sc) { frappe.throw('Expression required'); return; }
			smApi('frappe_devkit.api.site_manager.execute_script', { site: gsite(), script: sc }, $et);
		}}]);

		// Drop Site
		const $drp = mkSub('drp');
		const $dc = smCard($drp);
		$dc.append(`<div style="background:#fde8e6;border:1px solid #e8a8a0;border-radius:6px;padding:16px 18px;margin-bottom:16px">
			<div style="font-size:14px;font-weight:700;color:#c0392b;margin-bottom:6px">⚠ Danger Zone</div>
			<div style="font-size:12.5px;color:#7a2020;line-height:1.7">Permanently deletes the database and all site files. Cannot be undone. Make a backup first.</div>
		</div>
		<div class="dkst-g2"><div class="dkst-fld"><label class="dkst-lbl">MariaDB Root Password</label>
			<input class="dkst-inp" type="password" id="drp-rpwd" placeholder="If required by MariaDB setup"></div></div>
		<div class="dkst-checks" style="margin-top:12px">
			<label class="dkst-chk"><input type="checkbox" id="drp-force"><span>Force drop (skip errors)</span></label>
			<label class="dkst-chk" style="color:#c0392b"><input type="checkbox" id="drp-ok"><span>I understand this is irreversible</span></label>
		</div>`);
		const $dt = smTerm($drp);
		smBtns($dc, [{ lbl: 'Drop Site', cls: 'dkst-btn-r', fn: () => {
			if (!$('#drp-ok').is(':checked')) { frappe.throw('Check the confirmation box first'); return; }
			const site = gsite();
			if (!confirm(`PERMANENTLY DROP '${site}'? Type OK to confirm.`)) return;
			smApi('frappe_devkit.api.site_manager.drop_site', {
				site, force: $('#drp-force').is(':checked')?1:0,
				root_password: $('#drp-rpwd').val().trim(),
			}, $dt);
		}}]);

		// Sub-tab switching
		$tabs.on('click', '.dkst-stab', function() {
			const t = $(this).data('t');
			$tabs.find('.dkst-stab').removeClass('active'); $(this).addClass('active');
			$pp.find('.dkst-spanel').removeClass('active'); $pp.find(`[data-t="${t}"]`).addClass('active');
		});
	};

	/* ── Global: Open-in-Editor link — covers every AppSel instance ── */
	$(document).on("change", "select.dkst-sel", function() {
		const $link = $(`[data-app-sel="${this.id}"]`);
		if ($link.length) $link.toggleClass("visible", !!this.value);
	});
	$(document).on("click", ".dkst-ce-link", function() {
		const selId = $(this).data("app-sel");
		const app   = selId ? ($(`#${selId}`).val() || "") : "";
		if (!app) return;
		frappe.route_options = { open_app: app };
		frappe.set_route("devkit-code-editor");
	});

	/* open default */
	showWelcome();
	activatePanel("doctype");

	/* ══════════════════════════════════════════════
	   SVG ICONS
	   ══════════════════════════════════════════════ */
	function _svg(p,s=15){return `<svg width="${s}" height="${s}" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">${p}</svg>`;}
	function icoBox(s)     {return _svg(`<rect x="2" y="3" width="20" height="14" rx="2"/><path d="M8 21h8M12 17v4"/>`,s);}
	function icoFile(s)    {return _svg(`<path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/>`,s);}
	function icoChart(s)   {return _svg(`<line x1="18" y1="20" x2="18" y2="10"/><line x1="12" y1="20" x2="12" y2="4"/><line x1="6" y1="20" x2="6" y2="14"/>`,s);}
	function icoSliders(s) {return _svg(`<line x1="4" y1="21" x2="4" y2="14"/><line x1="4" y1="10" x2="4" y2="3"/><line x1="12" y1="21" x2="12" y2="12"/><line x1="12" y1="8" x2="12" y2="3"/><line x1="20" y1="21" x2="20" y2="16"/><line x1="20" y1="12" x2="20" y2="3"/><line x1="1" y1="14" x2="7" y2="14"/><line x1="9" y1="8" x2="15" y2="8"/><line x1="17" y1="16" x2="23" y2="16"/>`,s);}
	function icoEdit(s)    {return _svg(`<path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"/><path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z"/>`,s);}
	function icoLink(s)    {return _svg(`<path d="M10 13a5 5 0 0 0 7.54.54l3-3a5 5 0 0 0-7.07-7.07l-1.72 1.71"/><path d="M14 11a5 5 0 0 0-7.54-.54l-3 3a5 5 0 0 0 7.07 7.07l1.71-1.71"/>`,s);}
	function icoCode(s)    {return _svg(`<polyline points="16 18 22 12 16 6"/><polyline points="8 6 2 12 8 18"/>`,s);}
	function icoBolt(s)    {return _svg(`<polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2"/>`,s);}
	function icoList(s)    {return _svg(`<line x1="8" y1="6" x2="21" y2="6"/><line x1="8" y1="12" x2="21" y2="12"/><line x1="8" y1="18" x2="21" y2="18"/><line x1="3" y1="6" x2="3.01" y2="6"/><line x1="3" y1="12" x2="3.01" y2="12"/><line x1="3" y1="18" x2="3.01" y2="18"/>`,s);}
	function icoSettings(s){return _svg(`<circle cx="12" cy="12" r="3"/><path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1-2.83 2.83l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-4 0v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83-2.83l.06-.06A1.65 1.65 0 0 0 4.68 15a1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1 0-4h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 2.83-2.83l.06.06A1.65 1.65 0 0 0 9 4.68a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 4 0v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 2.83l-.06.06A1.65 1.65 0 0 0 19.4 9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 0 4h-.09a1.65 1.65 0 0 0-1.51 1z"/>`,s);}
	function icoGrid(s)    {return _svg(`<rect x="3" y="3" width="18" height="18" rx="2"/><path d="M3 9h18M3 15h18M9 3v18"/>`,s);}
	function icoPrint(s)   {return _svg(`<polyline points="6 9 6 2 18 2 18 9"/><path d="M6 18H4a2 2 0 0 1-2-2v-5a2 2 0 0 1 2-2h16a2 2 0 0 1 2 2v5a2 2 0 0 1-2 2h-2"/><rect x="6" y="14" width="12" height="8"/>`,s);}
	function icoClock(s)   {return _svg(`<circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/>`,s);}
	function icoRefresh(s) {return _svg(`<polyline points="23 4 23 10 17 10"/><polyline points="1 20 1 14 7 14"/><path d="M3.51 9a9 9 0 0 1 14.85-3.36L23 10M1 14l4.64 4.36A9 9 0 0 0 20.49 15"/>`,s);}
	function icoShield(s)  {return _svg(`<path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/>`,s);}
	function icoExport(s)  {return _svg(`<path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="7 10 12 15 17 10"/><line x1="12" y1="15" x2="12" y2="3"/>`,s);}
	function icoLogo(s)    {return _svg(`<polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2"/>`,s);}
	function icoFolder(s)  {return _svg(`<path d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z"/>`,s);}
	function icoLayout(s)  {return _svg(`<rect x="3" y="3" width="18" height="18" rx="2" ry="2"/><line x1="3" y1="9" x2="21" y2="9"/><line x1="9" y1="21" x2="9" y2="9"/>`,s);}
	function icoHash(s)    {return _svg(`<line x1="4" y1="9" x2="20" y2="9"/><line x1="4" y1="15" x2="20" y2="15"/><line x1="10" y1="3" x2="8" y2="21"/><line x1="16" y1="3" x2="14" y2="21"/>`,s);}
	function icoBell(s)    {return _svg(`<path d="M18 8A6 6 0 0 0 6 8c0 7-3 9-3 9h18s-3-2-3-9"/><path d="M13.73 21a2 2 0 0 1-3.46 0"/>`,s);}
	function icoTerminal(s){return _svg(`<polyline points="4 17 10 11 4 5"/><line x1="12" y1="19" x2="20" y2="19"/>`,s);}
	function icoSearch(s)  {return _svg(`<circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/>`,s);}
	function icoHeart(s)   {return _svg(`<path d="M20.84 4.61a5.5 5.5 0 0 0-7.78 0L12 5.67l-1.06-1.06a5.5 5.5 0 0 0-7.78 7.78l1.06 1.06L12 21.23l7.78-7.78 1.06-1.06a5.5 5.5 0 0 0 0-7.78z"/>`,s);}
	function icoDiff(s)    {return _svg(`<line x1="12" y1="5" x2="12" y2="19"/><line x1="5" y1="12" x2="19" y2="12"/>`,s);}
	function icoPackage(s) {return _svg(`<line x1="16.5" y1="9.4" x2="7.5" y2="4.21"/><path d="M21 16V8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.73l7 4a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16z"/><polyline points="3.27 6.96 12 12.01 20.73 6.96"/><line x1="12" y1="22.08" x2="12" y2="12"/>`,s);}
	function icoGlobe(s)   {return _svg(`<circle cx="12" cy="12" r="10"/><line x1="2" y1="12" x2="22" y2="12"/><path d="M12 2a15.3 15.3 0 0 1 4 10 15.3 15.3 0 0 1-4 10 15.3 15.3 0 0 1-4-10 15.3 15.3 0 0 1 4-10z"/>`,s);}
	function icoPlus(s)    {return _svg(`<circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="16"/><line x1="8" y1="12" x2="16" y2="12"/>`,s);}
	function icoSave(s)    {return _svg(`<path d="M19 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11l5 5v11a2 2 0 0 1-2 2z"/><polyline points="17 21 17 13 7 13 7 21"/><polyline points="7 3 7 8 15 8"/>`,s);}
	function icoTools(s)   {return _svg(`<path d="M14.7 6.3a1 1 0 0 0 0 1.4l1.6 1.6a1 1 0 0 0 1.4 0l3.77-3.77a6 6 0 0 1-7.94 7.94l-6.91 6.91a2.12 2.12 0 0 1-3-3l6.91-6.91a6 6 0 0 1 7.94-7.94l-3.76 3.76z"/>`,s);}
};

frappe.pages["devkit-studio"].on_page_show = function (wrapper) {
	// Ensure Code Editor overlay (and any other fixed DevKit overlay) is hidden
	const ceRoot = document.getElementById("dkce-root");
	if (ceRoot) ceRoot.style.display = "none";

	const el = document.getElementById("dkst-root");
	if (!el) {
		frappe.pages["devkit-studio"].on_page_load(wrapper);
		return;
	}
	/* Show the fixed panel and set correct navbar offset */
	el.style.display = "flex";
	const nb = document.querySelector(".navbar");
	if (nb) el.style.top = nb.offsetHeight + "px";
};

frappe.pages["devkit-studio"].on_page_hide = function (wrapper) {
	/* Hide when navigating away — leave DOM intact for fast revisit */
	const el = document.getElementById("dkst-root");
	if (el) el.style.display = "none";
};
