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

/* ═══ TEXT SELECTION — allow copying doctype names & output everywhere ═══ */
.dkst-panel-area, .dkst-panel-area * { user-select: text; -webkit-user-select: text; }
.dkst-term { user-select: text; -webkit-user-select: text; }
.dkst-statusbar { user-select: text; -webkit-user-select: text; }
/* Keep nav items non-selectable (they are clickable buttons) */
.dkst-sb-item, .dkst-sb-section, .dkst-sb-logo-title { user-select: none; -webkit-user-select: none; }

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
.dkst-sb-search-wrap {
  padding: 8px 10px 6px;
  background: rgba(0,0,0,.12);
  border-bottom: 1px solid rgba(255,255,255,.06);
  flex-shrink: 0;
}
.dkst-sb-search {
  width: 100%;
  box-sizing: border-box;
  background: rgba(255,255,255,.07);
  border: 1px solid rgba(255,255,255,.12);
  border-radius: 5px;
  color: #d4c8f8;
  font-size: 12px;
  padding: 5px 8px 5px 26px;
  outline: none;
  transition: border-color .15s, background .15s;
}
.dkst-sb-search::placeholder { color: #6a5ea0; }
.dkst-sb-search:focus { border-color: #7a5cc0; background: rgba(255,255,255,.11); }
.dkst-sb-search-ico {
  position: absolute;
  left: 18px;
  top: 50%;
  transform: translateY(-50%);
  pointer-events: none;
  color: #6a5ea0;
}
.dkst-sb-search-wrap { position: relative; }
.dkst-sb-body {
  flex: 1;
  overflow-y: auto;
  padding: 8px 0 16px;
}
.dkst-sb-body::-webkit-scrollbar { width: 3px; }
.dkst-sb-body::-webkit-scrollbar-thumb { background: #4a3880; border-radius: 2px; }
.dkst-sb-section {
  padding: 16px 14px 5px;
  font-size: 11px;
  font-weight: 800;
  letter-spacing: .10em;
  text-transform: uppercase;
  color: #a090d8;
  background: rgba(255,255,255,.03);
  border-left: 3px solid rgba(155,125,224,.50);
  margin: 6px 0 0;
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

/* ═══ DOT PATH WIDGET ═══ */
.dkst-dotpath-inp {
  font-family: 'Consolas', 'Courier New', monospace !important;
  font-size: 12.5px !important;
  letter-spacing: .02em;
  transition: border-color .15s, box-shadow .15s;
}
.dkst-dotpath-inp.dp-valid   { border-color: #27ae60 !important; box-shadow: 0 0 0 2px rgba(39,174,96,.14) !important; }
.dkst-dotpath-inp.dp-invalid { border-color: #c0392b !important; box-shadow: 0 0 0 2px rgba(192,57,43,.12) !important; }
.dkst-dotpath-preview {
  display: flex; flex-wrap: wrap; align-items: center; gap: 2px;
  min-height: 0; margin-top: 7px; padding: 4px 8px; border-radius: 5px;
  background: #f7f4ff; border: 1px solid #e8e0f8;
}
.dkst-dotpath-preview:empty { display: none; }
.dkst-dps { display: inline-block; border-radius: 3px; padding: 2px 7px; font-size: 11px; font-family: Consolas, monospace; font-weight: 600; }
.dkst-dps-app { background: #ede8ff; color: #4a3880; border: 1px solid #c8b8f0; }
.dkst-dps-mod { background: #eaf5ea; color: #1a6a20; border: 1px solid #b0d4b0; }
.dkst-dps-fn  { background: #fff7e0; color: #7a4a10; border: 1px solid #d8c060; }
.dkst-dotpath-dot { color: #9880c8; font-weight: 800; font-size: 14px; margin: 0 1px; line-height: 1; align-self: center; }
.dkst-dotpath-err { color: #c0392b; font-size: 11px; font-family: monospace; }
.dkst-dp-autofill {
  padding: 5px 11px; font-size: 11.5px; white-space: nowrap; flex-shrink: 0;
  background: #f0ebff; color: #5c4da8; border: 1px solid #c8b8f0; border-radius: 5px;
  cursor: pointer; font-weight: 600; transition: background .12s;
}
.dkst-dp-autofill:hover { background: #e0d8ff; }

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

/* ═══ HTML EDITOR WIDGET ═══ */
.dkst-html-editor {
  border: 1px solid #d0c8e8; border-radius: 7px; overflow: hidden;
  background: #fff; margin-top: 2px;
}
.dkst-html-mode-tabs {
  display: flex; align-items: flex-end; padding: 6px 10px 0;
  background: #f3f0fb; border-bottom: 1px solid #d0c8e8; gap: 2px;
}
.dkst-html-mode-tab {
  padding: 5px 16px; font-size: 12px; cursor: pointer; color: #7060a8;
  border: 1px solid transparent; border-bottom: none;
  border-radius: 5px 5px 0 0; font-weight: 500; transition: all .1s;
}
.dkst-html-mode-tab.active {
  background: #fff; border-color: #d0c8e8; color: #1e1a2e; font-weight: 700;
  margin-bottom: -1px; padding-bottom: 6px;
}
.dkst-html-tb {
  display: flex; gap: 3px; align-items: center; flex-wrap: wrap;
  padding: 6px 10px; background: #faf8ff; border-bottom: 1px solid #e8e0f8;
}
.dkst-html-tb-btn {
  padding: 3px 9px; font-size: 11.5px; border: 1px solid #d0c8e8;
  border-radius: 4px; background: #fff; cursor: pointer; color: #4a4070;
  font-family: inherit; line-height: 1.5; transition: all .1s;
}
.dkst-html-tb-btn:hover { background: #ede8ff; border-color: #9b7de0; color: #1e1a2e; }
.dkst-html-tb-sep { width: 1px; height: 18px; background: #d8d0f0; margin: 0 3px; flex-shrink: 0; }
.dkst-html-inp {
  border: none !important; border-radius: 0 !important; resize: vertical;
  font-family: 'Consolas', 'Courier New', monospace !important;
  font-size: 12.5px !important; line-height: 1.75 !important;
  min-height: 200px; width: 100%; box-shadow: none !important;
  color: #1e1a2e; padding: 14px 16px !important; outline: none !important;
  background: #fff;
}
.dkst-html-inp:focus { box-shadow: none !important; outline: none !important; }
.dkst-html-preview-area {
  background: #fff; min-height: 180px;
  border-top: 1px solid #e8e0f8; position: relative;
}
.dkst-html-preview-area iframe {
  width: 100%; border: none; min-height: 180px; display: block; background: #fff;
}
.dkst-html-jinja-note {
  font-size: 11px; color: #7a70a8; padding: 6px 12px;
  background: #f7f4ff; border-bottom: 1px solid #ede8f8;
  display: flex; gap: 14px; align-items: center;
}
.dkst-jinja-badge { padding: 1px 6px; border-radius: 3px; font-family: monospace; font-size: 11px; }
.dkst-jinja-var  { background: #d4edda; color: #155724; border: 1px solid #b8ddc8; }
.dkst-jinja-tag  { background: #fff3cd; color: #856404; border: 1px solid #e8d88c; }

/* ═══ QUERY EDITOR ═══ */
.dkqe-root { display: flex; flex-direction: column; height: 100%; gap: 0; }
.dkqe-toolbar {
  display: flex; align-items: center; gap: 8px; flex-wrap: wrap;
  padding: 10px 18px; background: #fff; border-bottom: 1px solid #e8e0f8;
  flex-shrink: 0;
}
.dkqe-site-sel {
  font-size: 12px; padding: 5px 28px 5px 10px; border-radius: 5px;
  border: 1px solid #d0c8e8; background: #fff; color: #1e1a2e;
  min-width: 160px; appearance: none;
  background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='10' height='6'%3E%3Cpath d='M0 0l5 6 5-6z' fill='%239b7de0'/%3E%3C/svg%3E");
  background-repeat: no-repeat; background-position: right 8px center;
}
.dkqe-run-btn {
  display: flex; align-items: center; gap: 6px;
  background: #6c3fc5; color: #fff; border: none; border-radius: 5px;
  font-size: 12.5px; font-weight: 600; padding: 6px 14px; cursor: pointer;
  transition: background .15s;
}
.dkqe-run-btn:hover { background: #5c32a8; }
.dkqe-run-btn:disabled { background: #b0a0d8; cursor: not-allowed; }
.dkqe-limit-sel {
  font-size: 12px; padding: 5px 8px; border-radius: 5px;
  border: 1px solid #d0c8e8; background: #fff; color: #5c4da8;
}
.dkqe-tb-sep { width: 1px; height: 20px; background: #e0d8f0; margin: 0 2px; flex-shrink: 0; }
.dkqe-snippet-btn {
  font-size: 11.5px; padding: 4px 9px; border-radius: 4px; cursor: pointer;
  border: 1px solid #d0c8e8; background: #f7f4ff; color: #5c4da8;
  transition: background .12s;
}
.dkqe-snippet-btn:hover { background: #ede8ff; border-color: #9b7de0; }
.dkqe-editor-area {
  display: flex; flex: 1; min-height: 0; overflow: hidden;
}
.dkqe-left { display: flex; flex-direction: column; width: 220px; min-width: 180px; flex-shrink: 0; background: #faf8ff; border-right: 1px solid #e8e0f8; overflow-y: auto; }
.dkqe-left-hdr { font-size: 10px; font-weight: 700; text-transform: uppercase; letter-spacing: .10em; color: #9080b8; padding: 10px 12px 4px; }
.dkqe-tbl-item { font-size: 12px; padding: 5px 12px; cursor: pointer; color: #3a2e5e; display: flex; align-items: center; gap: 6px; border-radius: 0; transition: background .1s; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.dkqe-tbl-item:hover { background: #ede8ff; color: #5c4da8; }
.dkqe-tbl-item.active { background: #e0d8f8; color: #5c4da8; font-weight: 600; }
.dkqe-tbl-item svg { flex-shrink: 0; opacity: .6; }
.dkqe-center { display: flex; flex-direction: column; flex: 1; min-width: 0; overflow: hidden; }
.dkqe-editor-wrap {
  flex-shrink: 0; border-bottom: 1px solid #e8e0f8; position: relative;
  background: #fff; min-height: 200px; height: 240px; display: flex; flex-direction: column;
}
.dkqe-resize-handle {
  height: 5px; background: #2a2440; cursor: row-resize; flex-shrink: 0;
  border-top: 1px solid #3a2e5e; border-bottom: 1px solid #3a2e5e;
  transition: background .15s;
}
.dkqe-resize-handle:hover { background: #7a5cc0; }
.dkqe-editor {
  width: 100%; box-sizing: border-box; resize: none;
  font-family: 'Consolas', 'Monaco', 'Courier New', monospace !important;
  font-size: 13px !important; line-height: 1.65 !important;
  color: #e8e0ff; background: #1e1a2e;
  border: none; outline: none; padding: 14px 16px;
  tab-size: 4;
}
.dkqe-editor::selection { background: #4a3880; }
.dkqe-editor:focus { outline: none; box-shadow: none !important; }
.dkqe-editor-footer {
  display: flex; align-items: center; gap: 12px; padding: 4px 12px;
  background: #2a2440; border-top: 1px solid #3a2e5e;
  font-size: 11px; color: #7a6aa8; flex-shrink: 0;
}
.dkqe-results-area { flex: 1; overflow: hidden; display: flex; flex-direction: column; min-height: 0; background: #fff; }
.dkqe-results-hdr {
  display: flex; align-items: center; gap: 10px; padding: 8px 14px;
  background: #f7f4ff; border-bottom: 1px solid #e8e0f8; flex-shrink: 0; flex-wrap: wrap;
}
.dkqe-results-title { font-size: 12px; font-weight: 700; color: #3a2e5e; }
.dkqe-results-meta { font-size: 11px; color: #9080b8; }
.dkqe-export-btn {
  margin-left: auto; font-size: 11px; padding: 3px 10px; border-radius: 4px;
  border: 1px solid #d0c8e8; background: #fff; color: #5c4da8; cursor: pointer;
}
.dkqe-export-btn:hover { background: #ede8ff; }
.dkqe-results-scroll { flex: 1; overflow-x: auto; overflow-y: auto; min-width: 0; width: 100%; }
.dkqe-res-tbl { border-collapse: collapse; width: 100%; min-width: max-content; font-size: 12.5px; }
.dkqe-res-tbl thead { position: sticky; top: 0; z-index: 2; }
.dkqe-res-tbl th {
  background: #2a2440; color: #c8b8f0; font-weight: 600; font-size: 11.5px;
  padding: 7px 12px; text-align: left; white-space: nowrap;
  border-right: 1px solid #3a2e5e; letter-spacing: .04em;
}
.dkqe-res-tbl th:last-child { border-right: none; }
.dkqe-res-tbl td {
  padding: 6px 12px; border-bottom: 1px solid #f0ecf8;
  color: #1e1a2e; max-width: 360px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;
  font-family: 'Consolas', monospace; font-size: 12px;
}
.dkqe-res-tbl tr:nth-child(even) td { background: #faf8ff; }
.dkqe-res-tbl tr:hover td { background: #f0eaff; }
.dkqe-res-tbl td.null-val { color: #b0a0c8; font-style: italic; }
.dkqe-res-tbl td.num-val  { color: #1a6ea8; text-align: right; }
.dkqe-res-tbl td.bool-val { color: #1a7a3a; font-weight: 600; }
.dkqe-res-tbl td.date-val { color: #7a5cc0; }
.dkqe-res-tbl td.json-val { color: #c47a00; max-width: 280px; }
.dkqe-error { padding: 20px; color: #c0392b; font-family: monospace; font-size: 13px; background: #fff5f5; border-left: 4px solid #c0392b; margin: 16px; border-radius: 4px; white-space: pre-wrap; word-break: break-all; }
.dkqe-empty { text-align: center; padding: 60px 20px; color: #b0a8c8; font-size: 14px; }
.dkqe-spinner { display: flex; align-items: center; justify-content: center; padding: 60px; gap: 12px; color: #9080b8; font-size: 14px; }
.dkqe-affected { padding: 20px; color: #1a7a3a; font-size: 13px; font-weight: 600; background: #f0faf4; border-left: 4px solid #27ae60; margin: 16px; border-radius: 4px; }
.dkqe-history-item { padding: 6px 12px; font-size: 11.5px; font-family: monospace; cursor: pointer; border-bottom: 1px solid #f0ecf8; color: #3a2e5e; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.dkqe-history-item:hover { background: #f0eaff; }
.dkqe-col-num { background: #3a2e5e !important; color: #7a6aa8 !important; width: 40px; text-align: right !important; user-select: none; font-size: 11px; }
.dkqe-td-expand { cursor: pointer; }
.dkqe-tab-bar { display: flex; gap: 0; border-bottom: 1px solid #e8e0f8; background: #f7f4ff; flex-shrink: 0; }
.dkqe-tab { font-size: 12px; padding: 7px 16px; cursor: pointer; color: #7a70a8; border-bottom: 2px solid transparent; font-weight: 500; }
.dkqe-tab.active { color: #5c4da8; border-bottom-color: #7a5cc0; font-weight: 700; background: #fff; }

/* ── SQL Autocomplete ── */
.dkqe-ac-drop {
  position: fixed; z-index: 99999;
  background: #1e1a2e; border: 1px solid #4a3880;
  border-radius: 7px; box-shadow: 0 10px 36px rgba(0,0,0,.55);
  min-width: 230px; max-width: 420px; max-height: 270px;
  overflow-y: auto; font-family: 'Consolas','Monaco',monospace; font-size: 12.5px;
  padding: 4px 0; scrollbar-width: thin; scrollbar-color: #4a3880 #1e1a2e;
}
.dkqe-ac-drop::-webkit-scrollbar { width: 5px; }
.dkqe-ac-drop::-webkit-scrollbar-track { background: #1e1a2e; }
.dkqe-ac-drop::-webkit-scrollbar-thumb { background: #4a3880; border-radius: 3px; }
.dkqe-ac-section {
  font-size: 9.5px; font-weight: 700; text-transform: uppercase; letter-spacing: .10em;
  color: #4a3870; padding: 6px 10px 2px; border-top: 1px solid #2a2040; margin-top: 2px;
}
.dkqe-ac-section:first-child { border-top: none; margin-top: 0; }
.dkqe-ac-item {
  display: flex; align-items: center; gap: 7px;
  padding: 5px 10px; cursor: pointer; color: #c8b8f0;
  white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
}
.dkqe-ac-item:hover, .dkqe-ac-item.sel { background: #30265a; color: #e8e0ff; }
.dkqe-ac-ico {
  font-size: 9px; font-weight: 700; padding: 1px 4px; border-radius: 3px;
  flex-shrink: 0; letter-spacing: .02em; font-family: 'Segoe UI',sans-serif;
  min-width: 20px; text-align: center;
}
.dkqe-ac-keyword  .dkqe-ac-ico { background: #5c3da0; color: #ddd0ff; }
.dkqe-ac-function .dkqe-ac-ico { background: #1a5870; color: #a0d8f0; }
.dkqe-ac-table    .dkqe-ac-ico { background: #4a2060; color: #d0a0f8; }
.dkqe-ac-column   .dkqe-ac-ico { background: #1a5a30; color: #90e0a8; }
.dkqe-ac-lbl { flex: 1; overflow: hidden; text-overflow: ellipsis; font-size: 12px; }
.dkqe-ac-detail { font-size: 10px; color: #5a4870; margin-left: auto; padding-left: 8px; flex-shrink: 0; }
.dkqe-ac-hint {
  font-size: 10px; color: #3a2e60; padding: 3px 8px 4px;
  border-top: 1px solid #2a2040; text-align: right; letter-spacing: .02em;
}

/* ── Snippet categories ── */
.dkqe-sn-group-hdr {
  font-size: 9.5px; font-weight: 700; text-transform: uppercase; letter-spacing: .10em;
  color: #9b7de0; padding: 6px 12px 2px; border-top: 1px solid #e8e0f8;
  background: #f7f4ff; cursor: default; user-select: none;
}
.dkqe-sn-group-hdr:first-child { border-top: none; }

/* ═══ WEB & PAGE BUILDER ═══ */
.dkpb-root { display:flex;flex-direction:column;height:100%;overflow:hidden;padding:0 }
.dkpb-toolbar { display:flex;align-items:center;gap:6px;flex-wrap:wrap;padding:8px 14px;background:#fff;border-bottom:1px solid #e8e0f8;flex-shrink:0 }
.dkpb-area { display:flex;flex:1;min-height:0;overflow:hidden }
.dkpb-left { width:220px;min-width:170px;flex-shrink:0;background:#faf8ff;border-right:1px solid #e8e0f8;display:flex;flex-direction:column;overflow:hidden }
.dkpb-left-hdr { font-size:10px;font-weight:700;text-transform:uppercase;letter-spacing:.10em;color:#9080b8;padding:8px 12px 4px;flex-shrink:0 }
.dkpb-search { display:block;margin:4px 8px;width:calc(100% - 16px);box-sizing:border-box;font-size:11.5px;padding:4px 8px;border:1px solid #d0c8e8;border-radius:4px;background:#fff;color:#1e1a2e;outline:none }
.dkpb-search:focus { border-color:#9b7de0 }
.dkpb-tree { flex:1;overflow-y:auto }
/* file tree nodes */
.dkpb-node { display:flex;align-items:center;gap:5px;padding:4px 8px;cursor:pointer;font-size:12px;color:#3a2e5e;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;user-select:none }
.dkpb-node:hover { background:#ede8ff }
.dkpb-node.sel { background:#e0d8f8;color:#5c4da8;font-weight:600 }
.dkpb-node.dir-nd { font-weight:600;color:#5c4da8;font-size:11.5px }
.dkpb-node .xb { font-size:9px;font-weight:700;padding:1px 4px;border-radius:3px;flex-shrink:0;min-width:20px;text-align:center;font-family:'Segoe UI',sans-serif }
.xb-html { background:#7a5cc020;color:#7a5cc0 }
.xb-py   { background:#1a6a3a20;color:#1a6a3a }
.xb-md   { background:#1a5a7020;color:#1a5a70 }
.xb-css  { background:#c47a0020;color:#c47a00 }
.xb-js   { background:#8a6a0020;color:#8a6a00 }
.xb-json { background:#6a3a0020;color:#6a3a00 }
.dkpb-nd-lbl { flex:1;overflow:hidden;text-overflow:ellipsis }
.dkpb-nd-comp { font-size:9px;color:#c8a0e8;flex-shrink:0;padding-left:2px }
/* page list */
.dkpb-page-item { display:flex;align-items:center;gap:7px;padding:6px 10px;cursor:pointer;font-size:12px;color:#3a2e5e;border-bottom:1px solid #f0ecf8 }
.dkpb-page-item:hover { background:#ede8ff }
.dkpb-page-item.sel { background:#e0d8f8;font-weight:600 }
.dkpb-page-item .pg-title { flex:1;overflow:hidden;text-overflow:ellipsis;white-space:nowrap }
.dkpb-page-item .pg-type { font-size:9px;color:#9080b8;padding:1px 4px;border-radius:3px;background:#ede8ff;flex-shrink:0 }
.dkpb-dot-pub { width:7px;height:7px;border-radius:50%;background:#27ae60;flex-shrink:0 }
.dkpb-dot-drft { width:7px;height:7px;border-radius:50%;background:#b0a8c8;flex-shrink:0 }
/* center / editor */
.dkpb-center { display:flex;flex-direction:column;flex:1;min-width:0;overflow:hidden }
.dkpb-tab-bar { display:flex;border-bottom:1px solid #e8e0f8;background:#f7f4ff;flex-shrink:0 }
.dkpb-tab { font-size:12px;padding:6px 14px;cursor:pointer;color:#7a70a8;border-bottom:2px solid transparent;font-weight:500;white-space:nowrap }
.dkpb-tab.active { color:#5c4da8;border-bottom-color:#7a5cc0;font-weight:700;background:#fff }
.dkpb-breadcrumb { font-size:11px;color:#5c4da8;padding:4px 12px;background:#f0ecf8;border-bottom:1px solid #e8e0f8;flex-shrink:0;font-family:monospace;display:flex;align-items:center;gap:6px }
.dkpb-dirty-dot { width:7px;height:7px;border-radius:50%;background:#e8a020;display:inline-block }
.dkpb-ed-wrap { flex:1;display:flex;flex-direction:column;min-height:0;overflow:hidden;background:#fff }
.dkpb-editor { width:100%;box-sizing:border-box;resize:none;flex:1;font-family:'Consolas','Monaco',monospace!important;font-size:13px!important;line-height:1.65!important;color:#1e1a2e;background:#fff;border:none;outline:none;padding:12px 16px;tab-size:4 }
.dkpb-editor:focus { outline:none;box-shadow:none!important }
.dkpb-ed-monaco { flex:1;min-height:0;width:100%;height:100%;overflow:hidden;border:none }
.dkpb-comp-tabs { display:flex;background:#f7f4ff;border-bottom:1px solid #e8e0f8;flex-shrink:0 }
.dkpb-comp-tab { font-size:11px;padding:4px 12px;cursor:pointer;color:#7a70a8;border-right:1px solid #e8e0f8;font-family:monospace;font-weight:500 }
.dkpb-comp-tab.active { color:#5c4da8;background:#fff;font-weight:700 }
/* split pane */
.dkpb-split-h { display:flex;flex:1;min-height:0;overflow:hidden }
.dkpb-split-pane { flex:1;display:flex;flex-direction:column;min-width:0;overflow:hidden }
.dkpb-split-handle { width:5px;background:#e0d8f0;cursor:col-resize;flex-shrink:0;border-left:1px solid #d0c8e8;transition:background .15s }
.dkpb-split-handle:hover { background:#9b7de0 }
/* preview */
.dkpb-preview-area { flex:1;display:flex;flex-direction:column;overflow:hidden;background:#fff }
.dkpb-preview-bar { display:flex;align-items:center;gap:8px;padding:5px 10px;background:#f7f4ff;border-bottom:1px solid #e8e0f8;font-size:11px;color:#7a70a8;flex-shrink:0 }
.dkpb-preview-frame { flex:1;width:100%;border:none }
/* right props panel */
.dkpb-right { width:240px;flex-shrink:0;background:#faf8ff;border-left:1px solid #e8e0f8;display:flex;flex-direction:column;overflow:hidden }
.dkpb-right-hdr { font-size:10px;font-weight:700;text-transform:uppercase;letter-spacing:.10em;color:#9080b8;padding:8px 12px 4px;border-bottom:1px solid #e8e0f8;flex-shrink:0 }
.dkpb-right-body { flex:1;overflow-y:auto;padding:10px 12px }
.dkpb-field { margin-bottom:9px }
.dkpb-lbl { font-size:10.5px;font-weight:600;color:#5a4870;margin-bottom:3px;display:block }
.dkpb-inp { width:100%;box-sizing:border-box;padding:5px 8px;font-size:12px;border:1px solid #d0c8e8;border-radius:4px;background:#fff;color:#1e1a2e;outline:none }
.dkpb-inp:focus { border-color:#9b7de0 }
.dkpb-inp-ta { resize:vertical;min-height:50px }
.dkpb-inp-sel { width:100%;box-sizing:border-box;padding:5px 8px;font-size:12px;border:1px solid #d0c8e8;border-radius:4px;background:#fff;color:#1e1a2e;outline:none }
.dkpb-toggle { display:flex;align-items:center;gap:7px;font-size:12px;color:#3a2e5e;cursor:pointer;user-select:none }
.dkpb-toggle input { accent-color:#6c3fc5 }
.dkpb-divider { height:1px;background:#e8e0f8;margin:8px 0 }
.dkpb-btn-full { width:100%;padding:6px;font-size:12px;border-radius:5px;cursor:pointer;border:none;font-weight:600;margin-bottom:5px;transition:background .12s }
.dkpb-btn-p { background:#6c3fc5;color:#fff }
.dkpb-btn-p:hover { background:#5c32a8 }
.dkpb-btn-p:disabled { background:#b0a0d8;cursor:not-allowed }
.dkpb-btn-s { background:#ede8ff;color:#5c4da8;border:1px solid #d0c8e8 }
.dkpb-btn-s:hover { background:#e0d8f8 }
.dkpb-btn-d { background:#fff5f5;color:#c0392b;border:1px solid #f0c0c0 }
.dkpb-btn-d:hover { background:#ffe0e0 }
/* toolbar buttons */
.dkpb-tsep { width:1px;height:20px;background:#e0d8f0;flex-shrink:0 }
.dkpb-btn { font-size:11.5px;padding:4px 10px;border-radius:4px;cursor:pointer;border:1px solid #d0c8e8;background:#fff;color:#5c4da8;transition:background .12s;white-space:nowrap }
.dkpb-btn:hover { background:#ede8ff;border-color:#9b7de0 }
.dkpb-btn:disabled { opacity:.5;cursor:not-allowed }
.dkpb-btn-accent { background:#6c3fc5;color:#fff;border-color:#6c3fc5;font-weight:600 }
.dkpb-btn-accent:hover { background:#5c32a8 }
.dkpb-btn-accent:disabled { background:#b0a0d8;cursor:not-allowed }
/* block builder */
.dkpb-blk-lib { width:190px;flex-shrink:0;background:#fff;border-right:1px solid #e8e0f8;display:flex;flex-direction:column;overflow:hidden }
.dkpb-blk-lib-hdr { font-size:10px;font-weight:700;text-transform:uppercase;letter-spacing:.10em;color:#9080b8;padding:8px 10px 4px;border-bottom:1px solid #e8e0f8;flex-shrink:0 }
.dkpb-blk-lib-item { display:flex;align-items:center;gap:6px;padding:7px 10px;cursor:pointer;font-size:12px;color:#3a2e5e;border-bottom:1px solid #f0ecf8 }
.dkpb-blk-lib-item:hover { background:#ede8ff }
.dkpb-blk-ico { font-size:14px }
.dkpb-canvas { flex:1;overflow-y:auto;padding:10px;background:#f3f0fa;display:flex;flex-direction:column;gap:8px }
.dkpb-canvas-empty { text-align:center;padding:40px 20px;color:#b0a8c8;font-size:13px;border:2px dashed #d0c8e8;border-radius:8px;flex:1 }
.dkpb-block { background:#fff;border:1px solid #d0c8e8;border-radius:6px;overflow:hidden;transition:box-shadow .15s }
.dkpb-block:hover { box-shadow:0 2px 12px rgba(108,63,197,.12) }
.dkpb-block.drag-over { border-color:#9b7de0;box-shadow:0 0 0 2px #9b7de040 }
.dkpb-block-hdr { display:flex;align-items:center;gap:8px;padding:6px 10px;background:#f0ecf8;cursor:grab;border-bottom:1px solid #e0d8f0 }
.dkpb-block-hdr:active { cursor:grabbing }
.dkpb-block-ttl { flex:1;font-size:12px;font-weight:600;color:#3a2e5e }
.dkpb-block-del { font-size:12px;color:#b0a0c0;cursor:pointer;padding:1px 6px;border-radius:3px;border:none;background:none }
.dkpb-block-del:hover { background:#ffe0e0;color:#c0392b }
.dkpb-block-body { padding:10px;display:grid;grid-template-columns:1fr 1fr;gap:8px }
.dkpb-bf { display:flex;flex-direction:column;gap:2px }
.dkpb-bf.full { grid-column:1/-1 }
.dkpb-bf label { font-size:10px;color:#5a4870;font-weight:600 }
.dkpb-bf input,.dkpb-bf textarea,.dkpb-bf select { padding:4px 6px;font-size:11px;border:1px solid #d0c8e8;border-radius:3px;outline:none;background:#faf8ff;color:#1e1a2e }
.dkpb-bf input:focus,.dkpb-bf textarea:focus { border-color:#9b7de0 }
.dkpb-empty { text-align:center;padding:50px 20px;color:#b0a8c8;font-size:13px }
/* mode tabs at top of panel */
.dkpb-mode-bar { display:flex;gap:0;background:#f7f4ff;border-bottom:2px solid #e0d8f0;flex-shrink:0 }
.dkpb-mode-tab { font-size:12px;font-weight:600;padding:8px 18px;cursor:pointer;color:#7a70a8;border-bottom:3px solid transparent;margin-bottom:-2px;white-space:nowrap }
.dkpb-mode-tab.active { color:#5c4da8;border-bottom-color:#6c3fc5;background:#fff }
/* desk page file tabs */
.dkpb-file-tabs { display:flex;gap:0;background:#f7f4ff;border-bottom:1px solid #e8e0f8;flex-shrink:0;overflow-x:auto }
.dkpb-file-tab { font-size:11px;padding:5px 12px;cursor:pointer;color:#7a70a8;border-right:1px solid #e8e0f8;font-family:monospace;white-space:nowrap;font-weight:500 }
.dkpb-file-tab.active { color:#5c4da8;background:#fff;font-weight:700 }
.dkpb-file-tab .dirty { width:6px;height:6px;border-radius:50%;background:#e8a020;display:inline-block;margin-left:4px }

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

/* ═══ WIDGET PRESET PANELS (Number Card / Dashboard Chart) ═══ */
.dkwc-action-bar {
  display: flex; align-items: center; gap: 10px; flex-wrap: wrap;
  padding: 10px 14px; margin-top: 10px;
  background: linear-gradient(135deg, #f0ebff 0%, #e8dfff 100%);
  border: 1.5px solid #c4b5fd; border-radius: 8px;
}
.dkwc-sel-count {
  font-size: 12.5px; font-weight: 700; color: #5c4da8;
}
.dkwc-badge {
  display: inline-flex; align-items: center; justify-content: center;
  min-width: 22px; height: 22px; border-radius: 11px;
  background: #5c4da8; color: #fff; font-size: 10px; font-weight: 900;
  padding: 0 6px; margin-left: 4px;
}
.dkwc-desel {
  margin-left: auto; padding: 3px 12px; border-radius: 5px;
  border: 1.5px solid #c4b5fd; background: #fff; color: #7c5cbf;
  font-size: 11px; cursor: pointer; font-weight: 600; font-family: inherit;
}
.dkwc-desel:hover { background: #ede9fe; }
.dkwc-scaffold-btn {
  padding: 6px 18px; border-radius: 6px; border: none; cursor: pointer;
  background: linear-gradient(135deg, #5c4da8 0%, #8b5cf6 100%);
  color: #fff; font-size: 12px; font-weight: 700; font-family: inherit;
  box-shadow: 0 2px 8px rgba(92,77,168,.35);
  transition: box-shadow .15s, transform .15s;
}
.dkwc-scaffold-btn:hover { box-shadow: 0 3px 14px rgba(139,92,246,.55); transform: translateY(-1px); }
.dkwc-scaffold-btn:disabled { opacity: .45; cursor: not-allowed; transform: none; }
/* ═══ PAGE PRESET DIALOG ═══ */
.dkpp-dialog-body { max-height: 70vh; overflow-y: auto; }
.dkpp-preset-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(148px, 1fr));
  gap: 10px; margin-bottom: 16px;
}
.dkpp-preset-card {
  border: 2px solid #e0d8f4; border-radius: 10px; cursor: pointer;
  background: #fff; transition: border-color .15s, box-shadow .15s, transform .12s;
  overflow: hidden; text-align: left;
}
.dkpp-preset-card:hover { border-color: #9070d8; box-shadow: 0 4px 16px rgba(92,77,168,.20); transform: translateY(-1px); }
.dkpp-preset-card.selected {
  border-color: #5c4da8; border-width: 2.5px;
  background: linear-gradient(160deg, #f0ebff 0%, #e8dfff 100%);
  box-shadow: 0 0 0 3px rgba(92,77,168,.20);
}
.dkpp-preset-card.selected::after {
  content: '✓'; position: absolute; top: 6px; right: 6px;
  width: 18px; height: 18px; background: #5c4da8; color: #fff;
  border-radius: 50%; font-size: 10px; font-weight: 900;
  line-height: 18px; text-align: center;
}
.dkpp-preset-top { height: 5px; }
.dkpp-preset-body { padding: 10px; }
.dkpp-preset-ico { font-size: 22px; line-height: 1; margin-bottom: 5px; }
.dkpp-preset-nm { font-size: 11.5px; font-weight: 700; color: #2a2050; margin-bottom: 2px; }
.dkpp-preset-ds { font-size: 10px; color: #9080b8; line-height: 1.35; min-height: 24px; }
.dkpp-preset-tag { display:inline-block;font-size:9px;font-weight:700;padding:1px 7px;border-radius:3px;margin-top:5px; }

.dkwc-chart-type-badge {
  display: inline-block; font-size: 9px; font-weight: 700; padding: 1px 5px;
  border-radius: 3px; margin-top: 2px; background: rgba(255,255,255,.25); color: #fff;
}

/* ═══ REPORT PRESET CARDS ═══ */
.dkrb-preset-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(142px, 1fr));
  gap: 10px;
  margin-bottom: 4px;
}
.dkrb-preset-card {
  position: relative;
  border: 2px solid #e0d8f4;
  border-radius: 8px;
  padding: 0;
  cursor: pointer;
  background: #fff;
  transition: border-color .15s, box-shadow .15s, transform .12s, background .12s;
  overflow: hidden;
  text-align: left;
}
.dkrb-preset-card:hover {
  border-color: #9070d8;
  box-shadow: 0 4px 16px rgba(92,77,168,.20);
  transform: translateY(-1px);
}
.dkrb-preset-card.selected {
  border-color: #5c4da8;
  border-width: 2.5px;
  background: linear-gradient(160deg, #f0ebff 0%, #e8dfff 100%);
  box-shadow: 0 0 0 3px rgba(92,77,168,.20), 0 4px 18px rgba(92,77,168,.28);
  transform: translateY(-1px);
}
.dkrb-preset-card.selected::after {
  content: '✓';
  position: absolute;
  top: 7px; right: 7px;
  width: 18px; height: 18px;
  background: #5c4da8;
  color: #fff;
  border-radius: 50%;
  font-size: 11px;
  font-weight: 900;
  line-height: 18px;
  text-align: center;
  box-shadow: 0 1px 4px rgba(92,77,168,.40);
}
.dkrb-preset-top { height: 4px; flex-shrink: 0; }
.dkrb-preset-body { padding: 10px 10px 9px; }
.dkrb-preset-ico { font-size: 20px; line-height: 1; margin-bottom: 6px; }
.dkrb-preset-nm { font-size: 11.5px; font-weight: 700; color: #2a2050; margin-bottom: 3px; }
.dkrb-preset-ds { font-size: 10px; color: #9080b8; line-height: 1.4; min-height: 26px; }
.dkrb-preset-tag {
  display: inline-block; font-size: 9px; font-weight: 700;
  padding: 1px 7px; border-radius: 3px; margin-top: 6px;
}
.dkrb-preset-card.selected .dkrb-preset-nm { color: #4a3a90; }
.dkrb-preset-card.selected .dkrb-preset-ds { color: #7060a0; }
.dkrb-preset-search-wrap {
  display: flex; align-items: center; gap: 8px;
  margin-bottom: 10px;
}
.dkrb-preset-search {
  flex: 1; padding: 6px 10px 6px 30px;
  border: 1.5px solid #d0c8ec; border-radius: 6px;
  font-size: 12px; background: #fff;
  background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='14' height='14' viewBox='0 0 24 24' fill='none' stroke='%239080b8' stroke-width='2.2' stroke-linecap='round' stroke-linejoin='round'%3E%3Ccircle cx='11' cy='11' r='8'/%3E%3Cline x1='21' y1='21' x2='16.65' y2='16.65'/%3E%3C/svg%3E");
  background-repeat: no-repeat; background-position: 8px center;
  outline: none;
}
.dkrb-preset-search:focus { border-color: #5c4da8; box-shadow: 0 0 0 2px rgba(92,77,168,.15); }
.dkrb-preset-count { font-size: 10.5px; color: #9080b8; white-space: nowrap; }
.dkrb-preset-card.dkrb-hidden { display: none; }
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
	let _dtsByApp={};
	function loadDtsByApp(app) {
		if (_dtsByApp[app]) return Promise.resolve(_dtsByApp[app]);
		return loadMods(app).then(mods => {
			return Promise.all(mods.map(m => loadDts(m)));
		}).then(results => {
			const all = [].concat(...results).sort();
			_dtsByApp[app] = all;
			return all;
		});
	}
	function fillSel(el, items, ph) {
		$(el).empty();
		if (ph) $(`<option value="">— ${ph} —</option>`).appendTo(el);
		items.forEach(v => $(`<option value="${v}">${v}</option>`).appendTo(el));
	}
	function wireAD($scope, aId, dId) {
		loadApps().then(() => fillSel($scope.find(`#${aId}`), _apps, "select app"));
		$scope.find(`#${aId}`).on("change", function() {
			const app = this.value;
			const $d = $scope.find(`#${dId}`);
			if (!$d.is("select")) return;
			$d.prop("disabled", true).html('<option value="">— select doctype —</option>');
			if (!app) return;
			$d.html('<option value="">— loading doctypes —</option>');
			loadDtsByApp(app).then(ds => { fillSel($d, ds, "select doctype"); $d.prop("disabled", false); });
		});
	}
	function wireAMD($scope, aId, mId, dId) {
		loadApps().then(() => fillSel($scope.find(`#${aId}`), _apps, "select app"));
		$scope.find(`#${aId}`).on("change", function() {
			const app=this.value;
			const $m=$scope.find(`#${mId}`);
			$m.prop("disabled",!app).html('<option value="">— select module —</option>');
			if (!app) {
				if (dId) $scope.find(`#${dId}`).prop("disabled",true).html('<option value="">— select doctype —</option>');
				return;
			}
			loadMods(app).then(ms => { fillSel($m,ms,"select module"); $m.prop("disabled",false); });
			// If doctype field is a <select>, populate all app doctypes immediately
			if (dId) {
				const $d = $scope.find(`#${dId}`);
				if ($d.is("select")) {
					$d.prop("disabled",true).html('<option value="">— loading doctypes —</option>');
					loadDtsByApp(app).then(ds => { fillSel($d,ds,"select doctype"); $d.prop("disabled",false); });
				}
			}
		});
		if (mId && dId) {
			$scope.find(`#${mId}`).on("change", function() {
				const mod=this.value;
				const $d=$scope.find(`#${dId}`);
				if (!$d.is("select")) return;
				$d.prop("disabled",!mod).html('<option value="">— select doctype —</option>');
				if (!mod) return;
				// Narrow to this module's doctypes
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
	const $sbSearchWrap = $(`<div class="dkst-sb-search-wrap">
		<svg class="dkst-sb-search-ico" width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><circle cx="11" cy="11" r="7"/><line x1="16.5" y1="16.5" x2="22" y2="22"/></svg>
		<input class="dkst-sb-search" id="dkst-sb-search" placeholder="Search tools…" autocomplete="off" spellcheck="false">
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
		{ sec:"⌨  Code Editor" },
		{ id:"code_editor",      lbl:"Open Code Editor",     ico:icoCode()     },
		{ id:"query_editor",     lbl:"SQL Query Editor",     ico:icoDatabase() },
		{ sep:true },
		{ sec:"◈  Scaffold" },
		{ id:"app",              lbl:"New App",              ico:icoBox()      },
		{ id:"module",           lbl:"New Module",           ico:icoFolder()   },
		{ id:"doctype",          lbl:"DocType",              ico:icoFile()     },
		{ id:"child",            lbl:"Child Table",          ico:icoGrid()     },
		{ id:"single",           lbl:"Single / Settings",    ico:icoSettings() },
		{ id:"report",           lbl:"Report",               ico:icoChart()    },
		{ sep:true },
		{ sec:"✦  Customize" },
		{ id:"custom_field",     lbl:"Custom Field",         ico:icoSliders()  },
		{ id:"property",         lbl:"Property Setter",      ico:icoEdit()     },
		{ id:"client_script",    lbl:"Client Script",        ico:icoCode()     },
		{ sep:true },
		{ sec:"⚙  Dev Tools" },
		{ id:"hook",             lbl:"Add Hook",             ico:icoLink()     },
		{ id:"override",         lbl:"Override File",        ico:icoCode()     },
		{ id:"patch",            lbl:"Patch",                ico:icoBolt()     },
		{ id:"tasks",            lbl:"Tasks / Scheduler",    ico:icoClock()    },
		{ id:"perms",            lbl:"Permissions",          ico:icoShield()   },
		{ sep:true },
		{ sec:"◉  UI & Widgets" },
		{ id:"workspace",        lbl:"Workspace",            ico:icoLayout()   },
		{ id:"dashboard_chart",  lbl:"Dashboard Chart",      ico:icoChart()    },
		{ id:"number_card",      lbl:"Number Card",          ico:icoHash()     },
		{ id:"notification",     lbl:"Notification",         ico:icoBell()     },
		{ id:"server_script",    lbl:"Server Script",        ico:icoTerminal() },
		{ id:"role_perm",        lbl:"Role Permissions",     ico:icoShield()   },
		{ sep:true },
		{ sec:"◎  Fixtures & Migrate" },
		{ id:"migrate",          lbl:"Migrate & Cache",      ico:icoRefresh()  },
		{ id:"export",           lbl:"Export Fixtures",      ico:icoExport()   },
		{ sep:true },
		{ sec:"⊙  Inspector & Logs" },
		{ id:"dt_inspector",     lbl:"DocType Inspector",    ico:icoSearch()   },
		{ id:"health_check",     lbl:"App Health Check",     ico:icoHeart()    },
		{ id:"fixture_diff",     lbl:"Fixture Diff",         ico:icoDiff()     },
		{ id:"fixture_mgr",      lbl:"Fixture Manager",      ico:icoExport()   },
		{ id:"log",              lbl:"Scaffold Log",         ico:icoList()     },
		{ sep:true },
		{ sec:"⬡  App & Site Manager" },
		{ id:"app_manager",      lbl:"App Manager",          ico:icoPackage()  },
		{ id:"site_overview",    lbl:"Site Overview",        ico:icoGlobe()    },
		{ id:"site_create",      lbl:"Create Site",          ico:icoPlus()     },
		{ id:"site_backup",      lbl:"Backup & Restore",     ico:icoSave()     },
		{ id:"site_config",      lbl:"Site Config",          ico:icoSliders()  },
		{ id:"site_ops",         lbl:"Site Operations",      ico:icoTools()    },
		{ sep:true },
		{ sec:"🌐  Web & Page Builder" },
		{ id:"www_editor",       lbl:"WWW File Manager",     ico:icoGlobe()    },
		{ id:"desk_page_mgr",    lbl:"Desk Page Editor",     ico:icoMonitor()  },
	];

	NAV.forEach(n => {
		if (n.sec) { $(`<div class="dkst-sb-section" data-sec="${n.sec}">${n.sec}</div>`).appendTo($sbBody); return; }
		if (n.sep) { $(`<div class="dkst-sb-sep dkst-sb-sep-auto"></div>`).appendTo($sbBody); return; }
		$(`<button class="dkst-sb-item" data-id="${n.id}" data-lbl="${n.lbl.toLowerCase()}">${n.ico}<span>${n.lbl}</span></button>`)
			.appendTo($sbBody).on("click", () => activatePanel(n.id));
	});

	// ── Sidebar search filtering ──
	$('#dkst-sb-search').on('input', function() {
		const q = this.value.trim().toLowerCase();
		if (!q) {
			// Show everything
			$sbBody.find('.dkst-sb-item, .dkst-sb-section, .dkst-sb-sep-auto').show();
			return;
		}
		// Hide all items first
		$sbBody.find('.dkst-sb-item').each(function() {
			const match = $(this).data('lbl').includes(q);
			$(this).toggle(match);
		});
		// Show/hide sections: show if any item in their group matches
		$sbBody.find('.dkst-sb-section').each(function() {
			let hasVisible = false;
			let $el = $(this).next();
			while ($el.length && !$el.hasClass('dkst-sb-section')) {
				if ($el.hasClass('dkst-sb-item') && $el.is(':visible')) { hasVisible = true; break; }
				$el = $el.next();
			}
			$(this).toggle(hasVisible);
		});
		// Hide separators during search
		$sbBody.find('.dkst-sb-sep-auto').hide();
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

	// ── Dot Path Widget ─────────────────────────────────────────────
	// Renders a monospace input with live segment preview + ⚡ Auto-fill button.
	// opts: { label, required, full, appSel, dtSel, evSel, pattern }
	// pattern tokens: {app} {dt_snake} {dt_pascal} {ev}
	function DotPathHtml(id, placeholder, opts={}) {
		const lbl  = opts.label    || 'Path';
		const req  = opts.required ? ' dkst-req' : '';
		const full = opts.full !== false ? ' dkst-full' : '';
		const autoBtn = opts.appSel ? `<button class="dkst-dp-autofill"
			data-dp-target="${id}"
			data-dp-app="${opts.appSel||''}"
			data-dp-dt="${opts.dtSel||''}"
			data-dp-ev="${opts.evSel||''}"
			data-dp-pat="${(opts.pattern||'').replace(/"/g,'&quot;')}"
			title="Auto-generate path from selected App / DocType">⚡ Auto-fill</button>` : '';
		return `<div class="dkst-fld${full}">
			<label class="dkst-lbl${req}">${lbl}</label>
			<div style="display:flex;gap:7px;align-items:center">
				<input class="dkst-inp dkst-dotpath-inp" id="${id}"
					placeholder="${placeholder}"
					autocomplete="off" spellcheck="false" style="flex:1">
				${autoBtn}
			</div>
			<div class="dkst-dotpath-preview" data-dp-for="${id}"></div>
		</div>`;
	}

	// live preview updater — called on input event
	function _dpUpdate($inp) {
		const val = $inp.val().trim();
		const id  = $inp.attr('id');
		const $pr = $(`.dkst-dotpath-preview[data-dp-for="${id}"]`);
		$pr.empty();
		$inp.removeClass('dp-valid dp-invalid');
		if (!val) return;
		const segs = val.split('.');
		const valid = segs.length > 1 && segs.every(s => /^[a-zA-Z_][a-zA-Z0-9_]*$/.test(s));
		$inp.toggleClass('dp-valid', valid).toggleClass('dp-invalid', !valid);
		segs.forEach((s, i) => {
			if (i > 0) $pr.append('<span class="dkst-dotpath-dot">.</span>');
			const cls = i === 0 ? 'app' : i === segs.length - 1 ? 'fn' : 'mod';
			const ok  = /^[a-zA-Z_][a-zA-Z0-9_]*$/.test(s);
			$pr.append(ok
				? `<span class="dkst-dps dkst-dps-${cls}">${s}</span>`
				: `<span class="dkst-dotpath-err">✕ ${s||'?'}</span>`);
		});
	}

	// auto-fill button handler
	$(document).on('input', '.dkst-dotpath-inp', function() { _dpUpdate($(this)); });
	$(document).on('click', '.dkst-dp-autofill', function(e) {
		e.preventDefault();
		const $b = $(this);
		const app = $(`#${$b.data('dp-app')}`).val() || '';
		const dt  = $(`#${$b.data('dp-dt')}`).val()  || '';
		const ev  = $(`#${$b.data('dp-ev')}`).val()  || '';
		if (!app) { frappe.show_alert({ message: 'Select an app first', indicator: 'orange' }, 3); return; }
		const dtSnake  = dt ? dt.toLowerCase().replace(/[\s\-]+/g, '_') : 'my_doctype';
		const dtPascal = dt ? dt.replace(/\s+/g, '') : 'MyDocType';
		const path = $b.data('dp-pat')
			.replace('{app}',      app)
			.replace('{dt_snake}', dtSnake)
			.replace('{dt_pascal}',dtPascal)
			.replace('{ev}',       ev || 'validate');
		const $inp = $(`#${$b.data('dp-target')}`);
		$inp.val(path).trigger('input');
		frappe.show_alert({ message: `Path auto-filled from <b>${app}</b>${dt?' + '+dt:''}`, indicator: 'green' }, 3);
	});

	// ── HTML Editor Widget ────────────────────────────────────────────
	// Creates a professional HTML/Jinja2 editor with toolbar + live preview.
	// Returns the jQuery textarea so .val() still works normally.
	function insertAtCursor(el, text) {
		const s = el.selectionStart, e = el.selectionEnd;
		el.value = el.value.substring(0, s) + text + el.value.substring(e);
		// Put cursor inside tag pair if applicable
		const inner = text.indexOf('><') !== -1 ? s + text.indexOf('><') + 1 : s + text.length;
		el.selectionStart = el.selectionEnd = inner;
		el.focus();
		$(el).trigger('input');
	}

	function makeHtmlEditor($parent, id, defaultVal) {
		const $wrap = $('<div class="dkst-html-editor"></div>').appendTo($parent);

		// ── Mode tabs (HTML / Preview)
		const $modeTabs = $('<div class="dkst-html-mode-tabs"></div>').appendTo($wrap);
		const $tabCode  = $('<div class="dkst-html-mode-tab active">✎ HTML / Jinja2</div>').appendTo($modeTabs);
		const $tabPrev  = $('<div class="dkst-html-mode-tab">👁 Preview</div>').appendTo($modeTabs);

		// ── Toolbar
		const $tb = $('<div class="dkst-html-tb"></div>').appendTo($wrap);
		const sep = () => $('<div class="dkst-html-tb-sep"></div>').appendTo($tb);
		const btn = (lbl, tip, ins) =>
			$(`<button class="dkst-html-tb-btn" title="${tip}">${lbl}</button>`)
				.appendTo($tb)
				.on('click', () => insertAtCursor($inp[0], ins));

		btn('<b>B</b>',   'Bold',           '<b></b>');
		btn('<i>I</i>',   'Italic',          '<i></i>');
		btn('<u>U</u>',   'Underline',       '<u></u>');
		sep();
		btn('H1',  'Heading 1',  '<h1></h1>');
		btn('H2',  'Heading 2',  '<h2></h2>');
		btn('H3',  'Heading 3',  '<h3></h3>');
		btn('P',   'Paragraph',  '<p></p>');
		sep();
		btn('Link',  'Hyperlink',      '<a href="">Link Text</a>');
		btn('Img',   'Image',          '<img src="" alt="" style="max-width:100%">');
		btn('HR',    'Horizontal rule','<hr>');
		sep();
		btn('Table', 'Insert table',
			'<table border="1" cellpadding="6" style="border-collapse:collapse;width:100%">\n'
			+'  <thead><tr><th>Column 1</th><th>Column 2</th></tr></thead>\n'
			+'  <tbody><tr><td></td><td></td></tr></tbody>\n</table>');
		sep();
		btn('{{ field }}', 'Jinja2 field value',   '{{ doc. }}');
		btn('{% if %}',    'Jinja2 if block',       '{% if doc.field %}\n\n{% endif %}');
		btn('{% for %}',   'Jinja2 for loop',       '{% for item in doc.items %}\n  {{ item.item_name }}\n{% endfor %}');
		$(`<button class="dkst-html-tb-btn" title="Format/indent HTML (basic)" style="margin-left:auto">⇅ Format</button>`)
			.appendTo($tb)
			.on('click', () => {
				// basic indent: insert newline after block tags
				let v = $inp.val();
				v = v.replace(/>\s*</g, '>\n<')
					.split('\n').map(l => l.trim()).filter(l => l).join('\n');
				$inp.val(v).trigger('input');
			});

		// ── Code area
		const $codeArea = $('<div></div>').appendTo($wrap);
		const $inp = $(`<textarea class="dkst-ta dkst-html-inp" id="${id}" rows="12" spellcheck="false"></textarea>`)
			.val(defaultVal || '').appendTo($codeArea);

		// ── Preview area
		const $prevArea = $('<div class="dkst-html-preview-area" style="display:none"></div>').appendTo($wrap);
		$prevArea.append(`<div class="dkst-html-jinja-note">
			Preview renders HTML — Jinja2 expressions are highlighted:
			<span class="dkst-jinja-badge dkst-jinja-var">{{ var }}</span>
			<span class="dkst-jinja-badge dkst-jinja-tag">{% tag %}</span>
		</div>`);
		const $iframe = $('<iframe class="dkst-html-preview-area-frame" style="width:100%;border:none;min-height:180px;display:block;background:#fff"></iframe>').appendTo($prevArea);

		function renderPreview() {
			const raw = $inp.val();
			const html = raw
				.replace(/\{%\s*([\s\S]*?)\s*%\}/g, '<span style="background:#fff3cd;color:#856404;padding:2px 5px;border-radius:3px;font-size:11px;font-family:monospace">{%&thinsp;$1&thinsp;%}</span>')
				.replace(/\{\{\s*([\s\S]*?)\s*\}\}/g, '<span style="background:#d4edda;color:#155724;padding:2px 5px;border-radius:3px;font-size:11px;font-family:monospace">{{&thinsp;$1&thinsp;}}</span>');
			const doc = $iframe[0].contentDocument || $iframe[0].contentWindow.document;
			doc.open();
			doc.write(`<!DOCTYPE html><html><head><meta charset="utf-8"><style>
				body { font-family: Arial, sans-serif; padding: 16px 20px; font-size: 13.5px;
					margin: 0; color: #1e1a2e; line-height: 1.7; }
				table { border-collapse: collapse; width: 100%; }
				th, td { border: 1px solid #ccc; padding: 7px 10px; text-align: left; }
				th { background: #f5f4fb; font-weight: 600; }
				a { color: #5c4da8; } h1,h2,h3 { color: #1e1a2e; }
			</style></head><body>${html}</body></html>`);
			doc.close();
			setTimeout(() => {
				try {
					const h = $iframe[0].contentDocument.body.scrollHeight;
					$iframe.height(Math.max(h + 20, 180));
				} catch(e) {}
			}, 80);
		}

		// Tab switching
		$tabCode.on('click', () => {
			$tabCode.addClass('active'); $tabPrev.removeClass('active');
			$tb.show(); $codeArea.show(); $prevArea.hide();
		});
		$tabPrev.on('click', () => {
			$tabPrev.addClass('active'); $tabCode.removeClass('active');
			$tb.hide(); $codeArea.hide(); $prevArea.show();
			renderPreview();
		});

		return $inp;
	}

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
		$c4.append(info("System Manager and All roles are added by default. Select or type extra roles below."));
		$c4.append(`<div class="dkst-tbl-wrap"><table class="dkst-tbl" style="width:100%">
			<thead><tr><th>Role</th><th style="width:36px"></th></tr></thead>
			<tbody id="dt-role-rows"></tbody>
		</table></div>`);
		$(`<div class="dkst-add-row" id="dt-add-role">+ Add Role</div>`).appendTo($c4);

		let _dtRoles = [];
		function _loadRoles() {
			if (_dtRoles.length) return;
			frappe.call({ method:'frappe.client.get_list',
				args:{doctype:'Role', fields:['name'], filters:[['name','not in',['All','Guest']]], limit_page_length:200, order_by:'name asc'},
				callback: r => {
					_dtRoles = (r.message||[]).map(x=>x.name);
					// Update any existing selects
					$("#dt-role-rows select").each(function(){
						const cur=$(this).val();
						$(this).empty().append('<option value="">— select role —</option>');
						_dtRoles.forEach(r2=>$(this).append(`<option value="${r2}">${r2}</option>`));
						$(this).append('<option value="__custom">Custom…</option>');
						$(this).val(cur);
					});
				}
			});
		}
		function _addRoleRow(val='') {
			_loadRoles();
			const $tr=$(`<tr>
				<td style="display:flex;gap:6px;align-items:center">
					<select class="dkst-sel dt-role-sel" style="flex:1">
						<option value="">— select role —</option>
						${_dtRoles.map(r=>`<option value="${r}"${r===val?' selected':''}>${r}</option>`).join('')}
						<option value="__custom"${val&&!_dtRoles.includes(val)?' selected':''}>Custom…</option>
					</select>
					<input class="dkst-inp dt-role-custom" value="${val&&!_dtRoles.includes(val)?val:''}" placeholder="Custom role name" style="flex:1;display:${val&&!_dtRoles.includes(val)?'block':'none'}">
				</td>
				<td><button class="dkst-del-btn">×</button></td>
			</tr>`);
			$tr.find('.dt-role-sel').on('change', function(){
				$tr.find('.dt-role-custom').toggle($(this).val()==='__custom');
			});
			$tr.find('.dkst-del-btn').on('click',()=>$tr.remove());
			$('#dt-role-rows').append($tr);
		}
		$c4.on('click','#dt-add-role',()=>_addRoleRow());
		_addRoleRow('Accounts Manager');
		_addRoleRow('Sales Manager');

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
				$("#dt-role-rows tr").each(function(){
					const sel=$(this).find('.dt-role-sel').val();
					const r = sel==='__custom' ? $(this).find('.dt-role-custom').val().trim() : sel;
					if(r) perms.push({role:r,read:1,write:1,create:1});
				});
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
		/* ── Preset definitions ── */
		const REPORT_PRESETS = [
			// ── GENERAL ──
			{
				id:"blank", name:"Blank", ico:"📄", color:"#6b7280", tag:"Starter", tagBg:"#f3f4f6", tagColor:"#374151",
				desc:"Empty scaffold — start from scratch.",
				report_type:"Script Report", ref_doctype:"",
				joins:[], filters:[], columns:[]
			},
			// ── SALES ──
			{
				id:"sales_invoice", name:"Sales Summary", ico:"💰", color:"#1d4ed8", tag:"Sales", tagBg:"#dbeafe", tagColor:"#1e40af",
				desc:"Sales invoices by date, customer, status.",
				report_type:"Script Report", ref_doctype:"Sales Invoice",
				joins:[{type:"LEFT",table:"Customer",alias:"cust",on:"t.customer = cust.name"}],
				filters:[
					{fn:"company",ft:"Link",lbl:"Company",op:"Company",req:1},
					{fn:"from_date",ft:"Date",lbl:"From Date",def:"Today",req:1},
					{fn:"to_date",ft:"Date",lbl:"To Date",def:"Today",req:1},
					{fn:"customer",ft:"Link",lbl:"Customer",op:"Customer"},
					{fn:"customer_group",ft:"Link",lbl:"Customer Group",op:"Customer Group"},
					{fn:"status",ft:"Select",lbl:"Status",op:"Draft\nSubmitted\nCancelled\nPaid\nUnpaid\nOverdue\nPartly Paid"},
				],
				columns:[
					{fn:"name",ft:"Link",lbl:"Invoice",w:160,op:"Sales Invoice",ta:"t"},
					{fn:"posting_date",ft:"Date",lbl:"Date",w:100,ta:"t"},
					{fn:"customer",ft:"Link",lbl:"Customer",w:150,op:"Customer",ta:"t"},
					{fn:"customer_name",ft:"Data",lbl:"Customer Name",w:180,ta:"t"},
					{fn:"territory",ft:"Data",lbl:"Territory",w:110,ta:"cust"},
					{fn:"grand_total",ft:"Currency",lbl:"Grand Total",w:120,al:"right",ta:"t"},
					{fn:"outstanding_amount",ft:"Currency",lbl:"Outstanding",w:120,al:"right",ta:"t"},
					{fn:"status",ft:"Data",lbl:"Status",w:100,ta:"t"},
				]
			},
			{
				id:"sales_order", name:"Sales Order Status", ico:"📝", color:"#2563eb", tag:"Sales", tagBg:"#dbeafe", tagColor:"#1d4ed8",
				desc:"Sales orders: pending, delivered, billing status.",
				report_type:"Script Report", ref_doctype:"Sales Order",
				joins:[
					{type:"LEFT",table:"Customer",alias:"cust",on:"t.customer = cust.name"},
					{type:"LEFT",table:"Territory",alias:"terr",on:"t.territory = terr.name"},
				],
				filters:[
					{fn:"company",ft:"Link",lbl:"Company",op:"Company",req:1},
					{fn:"from_date",ft:"Date",lbl:"From Date",def:"Today",req:1},
					{fn:"to_date",ft:"Date",lbl:"To Date",def:"Today",req:1},
					{fn:"customer",ft:"Link",lbl:"Customer",op:"Customer"},
					{fn:"status",ft:"Select",lbl:"Status",op:"Draft\nTo Deliver and Bill\nTo Bill\nTo Deliver\nCompleted\nCancelled\nClosed"},
				],
				columns:[
					{fn:"name",ft:"Link",lbl:"Sales Order",w:160,op:"Sales Order",ta:"t"},
					{fn:"transaction_date",ft:"Date",lbl:"Date",w:100,ta:"t"},
					{fn:"delivery_date",ft:"Date",lbl:"Delivery Date",w:110,ta:"t"},
					{fn:"customer",ft:"Link",lbl:"Customer",w:150,op:"Customer",ta:"t"},
					{fn:"customer_name",ft:"Data",lbl:"Customer Name",w:180,ta:"t"},
					{fn:"grand_total",ft:"Currency",lbl:"Grand Total",w:120,al:"right",ta:"t"},
					{fn:"per_delivered",ft:"Percent",lbl:"Delivered %",w:90,al:"right",ta:"t"},
					{fn:"per_billed",ft:"Percent",lbl:"Billed %",w:80,al:"right",ta:"t"},
					{fn:"status",ft:"Data",lbl:"Status",w:120,ta:"t"},
				]
			},
			{
				id:"quotation", name:"Quotation Pipeline", ico:"📋", color:"#0369a1", tag:"CRM", tagBg:"#e0f2fe", tagColor:"#0369a1",
				desc:"Quotations by customer, lead, status.",
				report_type:"Script Report", ref_doctype:"Quotation",
				joins:[
					{type:"LEFT",table:"Customer",alias:"cust",on:"t.party_name = cust.name AND t.quotation_to = 'Customer'"},
				],
				filters:[
					{fn:"company",ft:"Link",lbl:"Company",op:"Company",req:1},
					{fn:"from_date",ft:"Date",lbl:"From Date",def:"Today",req:1},
					{fn:"to_date",ft:"Date",lbl:"To Date",def:"Today",req:1},
					{fn:"status",ft:"Select",lbl:"Status",op:"Draft\nOpen\nReplied\nOrdered\nLost\nCancelled\nExpired"},
					{fn:"quotation_to",ft:"Select",lbl:"Quotation To",op:"Customer\nLead\nProspect"},
				],
				columns:[
					{fn:"name",ft:"Link",lbl:"Quotation",w:160,op:"Quotation",ta:"t"},
					{fn:"transaction_date",ft:"Date",lbl:"Date",w:100,ta:"t"},
					{fn:"valid_till",ft:"Date",lbl:"Valid Till",w:100,ta:"t"},
					{fn:"party_name",ft:"Data",lbl:"Customer/Lead",w:160,ta:"t"},
					{fn:"grand_total",ft:"Currency",lbl:"Amount",w:120,al:"right",ta:"t"},
					{fn:"status",ft:"Data",lbl:"Status",w:100,ta:"t"},
					{fn:"order_lost_reason",ft:"Data",lbl:"Lost Reason",w:160,ta:"t"},
				]
			},
			{
				id:"item_wise_sales", name:"Item-wise Sales", ico:"🏷️", color:"#0ea5e9", tag:"Sales", tagBg:"#e0f2fe", tagColor:"#0284c7",
				desc:"Sales breakdown per item via invoice child table.",
				report_type:"Script Report", ref_doctype:"Sales Invoice Item",
				joins:[
					{type:"INNER",table:"Sales Invoice",alias:"si",on:"t.parent = si.name"},
					{type:"LEFT",table:"Item",alias:"itm",on:"t.item_code = itm.name"},
					{type:"LEFT",table:"Customer",alias:"cust",on:"si.customer = cust.name"},
				],
				filters:[
					{fn:"company",ft:"Link",lbl:"Company",op:"Company",req:1},
					{fn:"from_date",ft:"Date",lbl:"From Date",def:"Today",req:1},
					{fn:"to_date",ft:"Date",lbl:"To Date",def:"Today",req:1},
					{fn:"customer",ft:"Link",lbl:"Customer",op:"Customer"},
					{fn:"item_code",ft:"Link",lbl:"Item",op:"Item"},
					{fn:"item_group",ft:"Link",lbl:"Item Group",op:"Item Group"},
				],
				columns:[
					{fn:"item_code",ft:"Link",lbl:"Item Code",w:140,op:"Item",ta:"t"},
					{fn:"item_name",ft:"Data",lbl:"Item Name",w:180,ta:"t"},
					{fn:"item_group",ft:"Link",lbl:"Group",w:120,op:"Item Group",ta:"itm"},
					{fn:"qty",ft:"Float",lbl:"Qty",w:80,al:"right",ta:"t"},
					{fn:"rate",ft:"Currency",lbl:"Rate",w:100,al:"right",ta:"t"},
					{fn:"amount",ft:"Currency",lbl:"Amount",w:110,al:"right",ta:"t"},
					{fn:"customer",ft:"Link",lbl:"Customer",w:150,op:"Customer",ta:"si"},
					{fn:"posting_date",ft:"Date",lbl:"Date",w:100,ta:"si"},
				]
			},
			// ── BUYING ──
			{
				id:"purchase_invoice", name:"Purchase Summary", ico:"🛒", color:"#ea580c", tag:"Buying", tagBg:"#ffedd5", tagColor:"#c2410c",
				desc:"Purchase invoices by date, supplier.",
				report_type:"Script Report", ref_doctype:"Purchase Invoice",
				joins:[{type:"LEFT",table:"Supplier",alias:"sup",on:"t.supplier = sup.name"}],
				filters:[
					{fn:"company",ft:"Link",lbl:"Company",op:"Company",req:1},
					{fn:"from_date",ft:"Date",lbl:"From Date",def:"Today",req:1},
					{fn:"to_date",ft:"Date",lbl:"To Date",def:"Today",req:1},
					{fn:"supplier",ft:"Link",lbl:"Supplier",op:"Supplier"},
					{fn:"supplier_group",ft:"Link",lbl:"Supplier Group",op:"Supplier Group"},
					{fn:"status",ft:"Select",lbl:"Status",op:"Draft\nSubmitted\nCancelled\nPaid\nUnpaid\nOverdue\nPartly Paid"},
				],
				columns:[
					{fn:"name",ft:"Link",lbl:"Invoice",w:160,op:"Purchase Invoice",ta:"t"},
					{fn:"posting_date",ft:"Date",lbl:"Date",w:100,ta:"t"},
					{fn:"supplier",ft:"Link",lbl:"Supplier",w:150,op:"Supplier",ta:"t"},
					{fn:"supplier_name",ft:"Data",lbl:"Supplier Name",w:180,ta:"t"},
					{fn:"grand_total",ft:"Currency",lbl:"Grand Total",w:120,al:"right",ta:"t"},
					{fn:"outstanding_amount",ft:"Currency",lbl:"Outstanding",w:120,al:"right",ta:"t"},
					{fn:"bill_no",ft:"Data",lbl:"Bill No",w:120,ta:"t"},
					{fn:"bill_date",ft:"Date",lbl:"Bill Date",w:100,ta:"t"},
				]
			},
			{
				id:"purchase_order", name:"Purchase Order Status", ico:"📦", color:"#f97316", tag:"Buying", tagBg:"#ffedd5", tagColor:"#c2410c",
				desc:"Purchase orders: pending receipt and billing.",
				report_type:"Script Report", ref_doctype:"Purchase Order",
				joins:[{type:"LEFT",table:"Supplier",alias:"sup",on:"t.supplier = sup.name"}],
				filters:[
					{fn:"company",ft:"Link",lbl:"Company",op:"Company",req:1},
					{fn:"from_date",ft:"Date",lbl:"From Date",def:"Today",req:1},
					{fn:"to_date",ft:"Date",lbl:"To Date",def:"Today",req:1},
					{fn:"supplier",ft:"Link",lbl:"Supplier",op:"Supplier"},
					{fn:"status",ft:"Select",lbl:"Status",op:"Draft\nTo Receive and Bill\nTo Bill\nTo Receive\nCompleted\nCancelled\nClosed"},
				],
				columns:[
					{fn:"name",ft:"Link",lbl:"Purchase Order",w:160,op:"Purchase Order",ta:"t"},
					{fn:"transaction_date",ft:"Date",lbl:"Date",w:100,ta:"t"},
					{fn:"schedule_date",ft:"Date",lbl:"Required By",w:110,ta:"t"},
					{fn:"supplier",ft:"Link",lbl:"Supplier",w:150,op:"Supplier",ta:"t"},
					{fn:"supplier_name",ft:"Data",lbl:"Supplier Name",w:180,ta:"t"},
					{fn:"grand_total",ft:"Currency",lbl:"Grand Total",w:120,al:"right",ta:"t"},
					{fn:"per_received",ft:"Percent",lbl:"Received %",w:90,al:"right",ta:"t"},
					{fn:"per_billed",ft:"Percent",lbl:"Billed %",w:80,al:"right",ta:"t"},
					{fn:"status",ft:"Data",lbl:"Status",w:120,ta:"t"},
				]
			},
			{
				id:"purchase_receipt_items", name:"Purchase Receipt Items", ico:"📥", color:"#b45309", tag:"Buying", tagBg:"#fef3c7", tagColor:"#92400e",
				desc:"Items received via purchase receipts.",
				report_type:"Script Report", ref_doctype:"Purchase Receipt Item",
				joins:[
					{type:"INNER",table:"Purchase Receipt",alias:"pr",on:"t.parent = pr.name"},
					{type:"LEFT",table:"Item",alias:"itm",on:"t.item_code = itm.name"},
					{type:"LEFT",table:"Supplier",alias:"sup",on:"pr.supplier = sup.name"},
				],
				filters:[
					{fn:"company",ft:"Link",lbl:"Company",op:"Company",req:1},
					{fn:"from_date",ft:"Date",lbl:"From Date",def:"Today",req:1},
					{fn:"to_date",ft:"Date",lbl:"To Date",def:"Today",req:1},
					{fn:"supplier",ft:"Link",lbl:"Supplier",op:"Supplier"},
					{fn:"warehouse",ft:"Link",lbl:"Warehouse",op:"Warehouse"},
					{fn:"item_code",ft:"Link",lbl:"Item",op:"Item"},
				],
				columns:[
					{fn:"posting_date",ft:"Date",lbl:"Date",w:100,ta:"pr"},
					{fn:"name",ft:"Link",lbl:"Receipt",w:150,op:"Purchase Receipt",ta:"pr"},
					{fn:"supplier_name",ft:"Data",lbl:"Supplier",w:160,ta:"pr"},
					{fn:"item_code",ft:"Link",lbl:"Item Code",w:140,op:"Item",ta:"t"},
					{fn:"item_name",ft:"Data",lbl:"Item Name",w:180,ta:"t"},
					{fn:"qty",ft:"Float",lbl:"Qty",w:80,al:"right",ta:"t"},
					{fn:"rate",ft:"Currency",lbl:"Rate",w:100,al:"right",ta:"t"},
					{fn:"amount",ft:"Currency",lbl:"Amount",w:110,al:"right",ta:"t"},
					{fn:"warehouse",ft:"Link",lbl:"Warehouse",w:140,op:"Warehouse",ta:"t"},
				]
			},
			// ── ACCOUNTS ──
			{
				id:"accounts_receivable", name:"Accounts Receivable", ico:"📈", color:"#16a34a", tag:"Accounts", tagBg:"#dcfce7", tagColor:"#15803d",
				desc:"AR aging: customers with outstanding balances.",
				report_type:"Script Report", ref_doctype:"Sales Invoice",
				joins:[
					{type:"LEFT",table:"Customer",alias:"cust",on:"t.customer = cust.name"},
					{type:"LEFT",table:"Territory",alias:"terr",on:"cust.territory = terr.name"},
				],
				filters:[
					{fn:"company",ft:"Link",lbl:"Company",op:"Company",req:1},
					{fn:"report_date",ft:"Date",lbl:"As On Date",def:"Today",req:1},
					{fn:"customer",ft:"Link",lbl:"Customer",op:"Customer"},
					{fn:"territory",ft:"Link",lbl:"Territory",op:"Territory"},
					{fn:"customer_group",ft:"Link",lbl:"Customer Group",op:"Customer Group"},
					{fn:"ageing_based_on",ft:"Select",lbl:"Ageing Based On",op:"Due Date\nPosting Date"},
				],
				columns:[
					{fn:"customer",ft:"Link",lbl:"Customer",w:150,op:"Customer",ta:"t"},
					{fn:"customer_name",ft:"Data",lbl:"Customer Name",w:180,ta:"t"},
					{fn:"territory",ft:"Data",lbl:"Territory",w:110,ta:"cust"},
					{fn:"outstanding_amount",ft:"Currency",lbl:"Outstanding",w:130,al:"right",ta:"t"},
					{fn:"payment_terms_template",ft:"Data",lbl:"Payment Terms",w:130,ta:"t"},
					{fn:"due_date",ft:"Date",lbl:"Due Date",w:100,ta:"t"},
				]
			},
			{
				id:"accounts_payable", name:"Accounts Payable", ico:"📉", color:"#dc2626", tag:"Accounts", tagBg:"#fee2e2", tagColor:"#b91c1c",
				desc:"AP aging: suppliers with outstanding balances.",
				report_type:"Script Report", ref_doctype:"Purchase Invoice",
				joins:[{type:"LEFT",table:"Supplier",alias:"sup",on:"t.supplier = sup.name"}],
				filters:[
					{fn:"company",ft:"Link",lbl:"Company",op:"Company",req:1},
					{fn:"report_date",ft:"Date",lbl:"As On Date",def:"Today",req:1},
					{fn:"supplier",ft:"Link",lbl:"Supplier",op:"Supplier"},
					{fn:"supplier_group",ft:"Link",lbl:"Supplier Group",op:"Supplier Group"},
					{fn:"ageing_based_on",ft:"Select",lbl:"Ageing Based On",op:"Due Date\nPosting Date"},
				],
				columns:[
					{fn:"supplier",ft:"Link",lbl:"Supplier",w:150,op:"Supplier",ta:"t"},
					{fn:"supplier_name",ft:"Data",lbl:"Supplier Name",w:180,ta:"t"},
					{fn:"outstanding_amount",ft:"Currency",lbl:"Outstanding",w:130,al:"right",ta:"t"},
					{fn:"due_date",ft:"Date",lbl:"Due Date",w:100,ta:"t"},
					{fn:"bill_no",ft:"Data",lbl:"Bill No",w:120,ta:"t"},
				]
			},
			{
				id:"payment_register", name:"Payment Register", ico:"💳", color:"#059669", tag:"Accounts", tagBg:"#d1fae5", tagColor:"#065f46",
				desc:"Payment entries: received and paid by party.",
				report_type:"Script Report", ref_doctype:"Payment Entry",
				joins:[
					{type:"LEFT",table:"Account",alias:"acct",on:"t.paid_to = acct.name"},
				],
				filters:[
					{fn:"company",ft:"Link",lbl:"Company",op:"Company",req:1},
					{fn:"from_date",ft:"Date",lbl:"From Date",def:"Today",req:1},
					{fn:"to_date",ft:"Date",lbl:"To Date",def:"Today",req:1},
					{fn:"payment_type",ft:"Select",lbl:"Payment Type",op:"Receive\nPay\nInternal Transfer"},
					{fn:"party_type",ft:"Select",lbl:"Party Type",op:"Customer\nSupplier\nEmployee\nShareholder"},
					{fn:"party",ft:"Dynamic Link",lbl:"Party",op:"party_type"},
					{fn:"mode_of_payment",ft:"Link",lbl:"Mode of Payment",op:"Mode of Payment"},
				],
				columns:[
					{fn:"name",ft:"Link",lbl:"Payment Entry",w:160,op:"Payment Entry",ta:"t"},
					{fn:"posting_date",ft:"Date",lbl:"Date",w:100,ta:"t"},
					{fn:"payment_type",ft:"Data",lbl:"Type",w:100,ta:"t"},
					{fn:"party_type",ft:"Data",lbl:"Party Type",w:100,ta:"t"},
					{fn:"party",ft:"Dynamic Link",lbl:"Party",w:150,op:"party_type",ta:"t"},
					{fn:"party_name",ft:"Data",lbl:"Party Name",w:180,ta:"t"},
					{fn:"paid_amount",ft:"Currency",lbl:"Amount",w:120,al:"right",ta:"t"},
					{fn:"mode_of_payment",ft:"Data",lbl:"Mode",w:110,ta:"t"},
					{fn:"reference_no",ft:"Data",lbl:"Reference No",w:130,ta:"t"},
				]
			},
			{
				id:"gl_ledger", name:"GL Ledger Entry", ico:"📒", color:"#7c3aed", tag:"Accounts", tagBg:"#ede9fe", tagColor:"#6d28d9",
				desc:"General Ledger entries by account, cost center.",
				report_type:"Script Report", ref_doctype:"GL Entry",
				joins:[
					{type:"LEFT",table:"Account",alias:"acct",on:"t.account = acct.name"},
					{type:"LEFT",table:"Cost Center",alias:"cc",on:"t.cost_center = cc.name"},
				],
				filters:[
					{fn:"company",ft:"Link",lbl:"Company",op:"Company",req:1},
					{fn:"from_date",ft:"Date",lbl:"From Date",def:"Today",req:1},
					{fn:"to_date",ft:"Date",lbl:"To Date",def:"Today",req:1},
					{fn:"account",ft:"Link",lbl:"Account",op:"Account"},
					{fn:"cost_center",ft:"Link",lbl:"Cost Center",op:"Cost Center"},
					{fn:"party_type",ft:"Select",lbl:"Party Type",op:"Customer\nSupplier\nEmployee"},
					{fn:"party",ft:"Dynamic Link",lbl:"Party",op:"party_type"},
					{fn:"voucher_type",ft:"Select",lbl:"Voucher Type",op:"Sales Invoice\nPurchase Invoice\nPayment Entry\nJournal Entry\nSales Order\nPurchase Order"},
				],
				columns:[
					{fn:"posting_date",ft:"Date",lbl:"Date",w:100,ta:"t"},
					{fn:"account",ft:"Link",lbl:"Account",w:180,op:"Account",ta:"t"},
					{fn:"party_type",ft:"Data",lbl:"Party Type",w:100,ta:"t"},
					{fn:"party",ft:"Dynamic Link",lbl:"Party",w:140,op:"party_type",ta:"t"},
					{fn:"voucher_type",ft:"Data",lbl:"Voucher Type",w:130,ta:"t"},
					{fn:"voucher_no",ft:"Dynamic Link",lbl:"Voucher No",w:150,op:"voucher_type",ta:"t"},
					{fn:"debit",ft:"Currency",lbl:"Debit",w:110,al:"right",ta:"t"},
					{fn:"credit",ft:"Currency",lbl:"Credit",w:110,al:"right",ta:"t"},
					{fn:"cost_center",ft:"Link",lbl:"Cost Center",w:130,op:"Cost Center",ta:"t"},
					{fn:"remarks",ft:"Data",lbl:"Remarks",w:200,ta:"t"},
				]
			},
			{
				id:"journal_entry", name:"Journal Entry", ico:"📓", color:"#6d28d9", tag:"Accounts", tagBg:"#ede9fe", tagColor:"#5b21b6",
				desc:"Journal entries with accounts, amounts, narration.",
				report_type:"Script Report", ref_doctype:"Journal Entry",
				joins:[
					{type:"LEFT",table:"Journal Entry Account",alias:"jea",on:"jea.parent = t.name"},
					{type:"LEFT",table:"Account",alias:"acct",on:"jea.account = acct.name"},
				],
				filters:[
					{fn:"company",ft:"Link",lbl:"Company",op:"Company",req:1},
					{fn:"from_date",ft:"Date",lbl:"From Date",def:"Today",req:1},
					{fn:"to_date",ft:"Date",lbl:"To Date",def:"Today",req:1},
					{fn:"voucher_type",ft:"Select",lbl:"Voucher Type",op:"Journal Entry\nBank Entry\nCash Entry\nCredit Card Entry\nDebit Note\nCredit Note"},
					{fn:"account",ft:"Link",lbl:"Account",op:"Account"},
				],
				columns:[
					{fn:"posting_date",ft:"Date",lbl:"Date",w:100,ta:"t"},
					{fn:"name",ft:"Link",lbl:"Journal Entry",w:160,op:"Journal Entry",ta:"t"},
					{fn:"voucher_type",ft:"Data",lbl:"Voucher Type",w:130,ta:"t"},
					{fn:"account",ft:"Link",lbl:"Account",w:180,op:"Account",ta:"jea"},
					{fn:"debit_in_account_currency",ft:"Currency",lbl:"Debit",w:110,al:"right",ta:"jea"},
					{fn:"credit_in_account_currency",ft:"Currency",lbl:"Credit",w:110,al:"right",ta:"jea"},
					{fn:"user_remark",ft:"Data",lbl:"Narration",w:200,ta:"t"},
				]
			},
			// ── STOCK ──
			{
				id:"stock_movement", name:"Stock Movement", ico:"🔄", color:"#9333ea", tag:"Stock", tagBg:"#f3e8ff", tagColor:"#7e22ce",
				desc:"Stock ledger: IN/OUT by item, warehouse, voucher.",
				report_type:"Script Report", ref_doctype:"Stock Ledger Entry",
				joins:[
					{type:"LEFT",table:"Item",alias:"itm",on:"t.item_code = itm.name"},
					{type:"LEFT",table:"Warehouse",alias:"wh",on:"t.warehouse = wh.name"},
				],
				filters:[
					{fn:"company",ft:"Link",lbl:"Company",op:"Company",req:1},
					{fn:"from_date",ft:"Date",lbl:"From Date",def:"Today",req:1},
					{fn:"to_date",ft:"Date",lbl:"To Date",def:"Today",req:1},
					{fn:"warehouse",ft:"Link",lbl:"Warehouse",op:"Warehouse"},
					{fn:"item_code",ft:"Link",lbl:"Item",op:"Item"},
					{fn:"item_group",ft:"Link",lbl:"Item Group",op:"Item Group"},
					{fn:"voucher_type",ft:"Select",lbl:"Voucher Type",op:"Purchase Receipt\nDelivery Note\nSales Invoice\nStock Entry\nMaterial Transfer\nManufacturing"},
				],
				columns:[
					{fn:"posting_date",ft:"Date",lbl:"Date",w:100,ta:"t"},
					{fn:"item_code",ft:"Link",lbl:"Item Code",w:140,op:"Item",ta:"t"},
					{fn:"item_name",ft:"Data",lbl:"Item Name",w:180,ta:"t"},
					{fn:"warehouse",ft:"Link",lbl:"Warehouse",w:140,op:"Warehouse",ta:"t"},
					{fn:"actual_qty",ft:"Float",lbl:"Qty In/Out",w:90,al:"right",ta:"t"},
					{fn:"qty_after_transaction",ft:"Float",lbl:"Balance Qty",w:100,al:"right",ta:"t"},
					{fn:"stock_uom",ft:"Data",lbl:"UOM",w:70,ta:"t"},
					{fn:"valuation_rate",ft:"Currency",lbl:"Rate",w:100,al:"right",ta:"t"},
					{fn:"stock_value_difference",ft:"Currency",lbl:"Value Change",w:110,al:"right",ta:"t"},
					{fn:"voucher_type",ft:"Data",lbl:"Voucher Type",w:130,ta:"t"},
					{fn:"voucher_no",ft:"Dynamic Link",lbl:"Voucher No",w:160,op:"voucher_type",ta:"t"},
				]
			},
			{
				id:"inventory_valuation", name:"Inventory Valuation", ico:"🏭", color:"#0891b2", tag:"Stock", tagBg:"#cffafe", tagColor:"#0e7490",
				desc:"Current stock value by item and warehouse (Bin).",
				report_type:"Script Report", ref_doctype:"Item",
				joins:[
					{type:"INNER",table:"Bin",alias:"bin",on:"t.name = bin.item_code"},
					{type:"LEFT",table:"Warehouse",alias:"wh",on:"bin.warehouse = wh.name"},
				],
				filters:[
					{fn:"company",ft:"Link",lbl:"Company",op:"Company",req:1},
					{fn:"item_code",ft:"Link",lbl:"Item",op:"Item"},
					{fn:"item_group",ft:"Link",lbl:"Item Group",op:"Item Group"},
					{fn:"warehouse",ft:"Link",lbl:"Warehouse",op:"Warehouse"},
				],
				columns:[
					{fn:"name",ft:"Link",lbl:"Item Code",w:140,op:"Item",ta:"t"},
					{fn:"item_name",ft:"Data",lbl:"Item Name",w:200,ta:"t"},
					{fn:"item_group",ft:"Link",lbl:"Item Group",w:130,op:"Item Group",ta:"t"},
					{fn:"warehouse",ft:"Link",lbl:"Warehouse",w:150,op:"Warehouse",ta:"bin"},
					{fn:"actual_qty",ft:"Float",lbl:"Qty on Hand",w:100,al:"right",ta:"bin"},
					{fn:"ordered_qty",ft:"Float",lbl:"Ordered Qty",w:100,al:"right",ta:"bin"},
					{fn:"reserved_qty",ft:"Float",lbl:"Reserved Qty",w:100,al:"right",ta:"bin"},
					{fn:"valuation_rate",ft:"Currency",lbl:"Val. Rate",w:110,al:"right",ta:"bin"},
					{fn:"stock_value",ft:"Currency",lbl:"Stock Value",w:120,al:"right",ta:"bin"},
				]
			},
			{
				id:"item_price_list", name:"Item Price List", ico:"💲", color:"#0284c7", tag:"Stock", tagBg:"#e0f2fe", tagColor:"#0369a1",
				desc:"Item prices across price lists and rate periods.",
				report_type:"Script Report", ref_doctype:"Item Price",
				joins:[
					{type:"LEFT",table:"Item",alias:"itm",on:"t.item_code = itm.name"},
					{type:"LEFT",table:"Price List",alias:"pl",on:"t.price_list = pl.name"},
				],
				filters:[
					{fn:"item_code",ft:"Link",lbl:"Item",op:"Item"},
					{fn:"item_group",ft:"Link",lbl:"Item Group",op:"Item Group"},
					{fn:"price_list",ft:"Link",lbl:"Price List",op:"Price List"},
					{fn:"customer",ft:"Link",lbl:"Customer",op:"Customer"},
					{fn:"supplier",ft:"Link",lbl:"Supplier",op:"Supplier"},
					{fn:"currency",ft:"Link",lbl:"Currency",op:"Currency"},
				],
				columns:[
					{fn:"item_code",ft:"Link",lbl:"Item Code",w:140,op:"Item",ta:"t"},
					{fn:"item_name",ft:"Data",lbl:"Item Name",w:200,ta:"t"},
					{fn:"item_group",ft:"Link",lbl:"Group",w:120,op:"Item Group",ta:"itm"},
					{fn:"price_list",ft:"Link",lbl:"Price List",w:130,op:"Price List",ta:"t"},
					{fn:"price_list_rate",ft:"Currency",lbl:"Rate",w:110,al:"right",ta:"t"},
					{fn:"currency",ft:"Link",lbl:"Currency",w:80,op:"Currency",ta:"t"},
					{fn:"uom",ft:"Link",lbl:"UOM",w:80,op:"UOM",ta:"t"},
					{fn:"valid_from",ft:"Date",lbl:"Valid From",w:100,ta:"t"},
					{fn:"valid_upto",ft:"Date",lbl:"Valid Upto",w:100,ta:"t"},
				]
			},
			{
				id:"batch_tracking", name:"Batch Tracking", ico:"🔢", color:"#7c3aed", tag:"Stock", tagBg:"#ede9fe", tagColor:"#6d28d9",
				desc:"Batch-wise stock levels, expiry, supplier.",
				report_type:"Script Report", ref_doctype:"Batch",
				joins:[
					{type:"LEFT",table:"Item",alias:"itm",on:"t.item = itm.name"},
					{type:"LEFT",table:"Bin",alias:"bin",on:"bin.item_code = t.item"},
				],
				filters:[
					{fn:"item_code",ft:"Link",lbl:"Item",op:"Item"},
					{fn:"item_group",ft:"Link",lbl:"Item Group",op:"Item Group"},
					{fn:"warehouse",ft:"Link",lbl:"Warehouse",op:"Warehouse"},
					{fn:"expiry_date",ft:"Date",lbl:"Expires Before"},
				],
				columns:[
					{fn:"name",ft:"Link",lbl:"Batch No",w:140,op:"Batch",ta:"t"},
					{fn:"item",ft:"Link",lbl:"Item",w:140,op:"Item",ta:"t"},
					{fn:"item_name",ft:"Data",lbl:"Item Name",w:180,ta:"itm"},
					{fn:"expiry_date",ft:"Date",lbl:"Expiry Date",w:110,ta:"t"},
					{fn:"manufacturing_date",ft:"Date",lbl:"Mfg Date",w:100,ta:"t"},
					{fn:"batch_qty",ft:"Float",lbl:"Batch Qty",w:90,al:"right",ta:"t"},
					{fn:"supplier",ft:"Data",lbl:"Supplier",w:140,ta:"t"},
				]
			},
			// ── MANUFACTURING ──
			{
				id:"bom_summary", name:"BOM Summary", ico:"⚙️", color:"#0f766e", tag:"Manufacturing", tagBg:"#ccfbf1", tagColor:"#0f766e",
				desc:"Bill of Materials: items, operations, costs.",
				report_type:"Script Report", ref_doctype:"BOM",
				joins:[
					{type:"LEFT",table:"Item",alias:"itm",on:"t.item = itm.name"},
					{type:"LEFT",table:"BOM Item",alias:"bomi",on:"bomi.parent = t.name"},
				],
				filters:[
					{fn:"item",ft:"Link",lbl:"Item",op:"Item"},
					{fn:"item_group",ft:"Link",lbl:"Item Group",op:"Item Group"},
					{fn:"is_active",ft:"Check",lbl:"Active Only"},
					{fn:"is_default",ft:"Check",lbl:"Default BOM Only"},
				],
				columns:[
					{fn:"name",ft:"Link",lbl:"BOM",w:160,op:"BOM",ta:"t"},
					{fn:"item",ft:"Link",lbl:"Item",w:140,op:"Item",ta:"t"},
					{fn:"item_name",ft:"Data",lbl:"Item Name",w:180,ta:"itm"},
					{fn:"quantity",ft:"Float",lbl:"BOM Qty",w:80,al:"right",ta:"t"},
					{fn:"uom",ft:"Data",lbl:"UOM",w:70,ta:"t"},
					{fn:"total_cost",ft:"Currency",lbl:"Total Cost",w:120,al:"right",ta:"t"},
					{fn:"is_default",ft:"Check",lbl:"Default",w:70,ta:"t"},
					{fn:"is_active",ft:"Check",lbl:"Active",w:70,ta:"t"},
				]
			},
			{
				id:"work_order", name:"Work Order Progress", ico:"🏗️", color:"#15803d", tag:"Manufacturing", tagBg:"#dcfce7", tagColor:"#166534",
				desc:"Work orders with production progress vs planned.",
				report_type:"Script Report", ref_doctype:"Work Order",
				joins:[
					{type:"LEFT",table:"Item",alias:"itm",on:"t.production_item = itm.name"},
					{type:"LEFT",table:"Warehouse",alias:"wh",on:"t.wip_warehouse = wh.name"},
				],
				filters:[
					{fn:"company",ft:"Link",lbl:"Company",op:"Company",req:1},
					{fn:"from_date",ft:"Date",lbl:"From Date",def:"Today",req:1},
					{fn:"to_date",ft:"Date",lbl:"To Date",def:"Today",req:1},
					{fn:"production_item",ft:"Link",lbl:"Item",op:"Item"},
					{fn:"status",ft:"Select",lbl:"Status",op:"Draft\nSubmitted\nNot Started\nIn Process\nCompleted\nCancelled\nStopped"},
				],
				columns:[
					{fn:"name",ft:"Link",lbl:"Work Order",w:160,op:"Work Order",ta:"t"},
					{fn:"production_item",ft:"Link",lbl:"Item",w:140,op:"Item",ta:"t"},
					{fn:"item_name",ft:"Data",lbl:"Item Name",w:180,ta:"t"},
					{fn:"qty",ft:"Float",lbl:"Planned Qty",w:100,al:"right",ta:"t"},
					{fn:"produced_qty",ft:"Float",lbl:"Produced",w:90,al:"right",ta:"t"},
					{fn:"planned_start_date",ft:"Date",lbl:"Start Date",w:110,ta:"t"},
					{fn:"planned_end_date",ft:"Date",lbl:"End Date",w:110,ta:"t"},
					{fn:"status",ft:"Data",lbl:"Status",w:110,ta:"t"},
				]
			},
			{
				id:"job_card", name:"Job Card / Operations", ico:"🔧", color:"#374151", tag:"Manufacturing", tagBg:"#f3f4f6", tagColor:"#374151",
				desc:"Job card time and operations per work order.",
				report_type:"Script Report", ref_doctype:"Job Card",
				joins:[
					{type:"LEFT",table:"Work Order",alias:"wo",on:"t.work_order = wo.name"},
					{type:"LEFT",table:"Operation",alias:"op_",on:"t.operation = op_.name"},
				],
				filters:[
					{fn:"company",ft:"Link",lbl:"Company",op:"Company"},
					{fn:"from_date",ft:"Date",lbl:"From Date",def:"Today",req:1},
					{fn:"to_date",ft:"Date",lbl:"To Date",def:"Today",req:1},
					{fn:"work_order",ft:"Link",lbl:"Work Order",op:"Work Order"},
					{fn:"operation",ft:"Link",lbl:"Operation",op:"Operation"},
					{fn:"status",ft:"Select",lbl:"Status",op:"Open\nWork In Progress\nCompleted\nCancelled"},
				],
				columns:[
					{fn:"name",ft:"Link",lbl:"Job Card",w:150,op:"Job Card",ta:"t"},
					{fn:"work_order",ft:"Link",lbl:"Work Order",w:150,op:"Work Order",ta:"t"},
					{fn:"production_item",ft:"Data",lbl:"Item",w:140,ta:"t"},
					{fn:"operation",ft:"Data",lbl:"Operation",w:130,ta:"t"},
					{fn:"for_quantity",ft:"Float",lbl:"Qty",w:70,al:"right",ta:"t"},
					{fn:"total_time_in_mins",ft:"Float",lbl:"Time (mins)",w:100,al:"right",ta:"t"},
					{fn:"status",ft:"Data",lbl:"Status",w:110,ta:"t"},
				]
			},
			// ── HR ──
			{
				id:"payroll_summary", name:"Payroll Summary", ico:"💼", color:"#db2777", tag:"Payroll", tagBg:"#fce7f3", tagColor:"#be185d",
				desc:"Salary slips with gross, deductions, net pay.",
				report_type:"Script Report", ref_doctype:"Salary Slip",
				joins:[
					{type:"LEFT",table:"Employee",alias:"emp",on:"t.employee = emp.name"},
					{type:"LEFT",table:"Department",alias:"dept",on:"emp.department = dept.name"},
				],
				filters:[
					{fn:"company",ft:"Link",lbl:"Company",op:"Company",req:1},
					{fn:"start_date",ft:"Date",lbl:"From Date",def:"Today",req:1},
					{fn:"end_date",ft:"Date",lbl:"To Date",def:"Today",req:1},
					{fn:"employee",ft:"Link",lbl:"Employee",op:"Employee"},
					{fn:"department",ft:"Link",lbl:"Department",op:"Department"},
					{fn:"payroll_entry",ft:"Link",lbl:"Payroll Entry",op:"Payroll Entry"},
					{fn:"docstatus",ft:"Select",lbl:"Status",op:"0\n1\n2"},
				],
				columns:[
					{fn:"employee",ft:"Link",lbl:"Employee",w:120,op:"Employee",ta:"t"},
					{fn:"employee_name",ft:"Data",lbl:"Employee Name",w:160,ta:"t"},
					{fn:"department",ft:"Link",lbl:"Department",w:130,op:"Department",ta:"emp"},
					{fn:"designation",ft:"Data",lbl:"Designation",w:130,ta:"emp"},
					{fn:"start_date",ft:"Date",lbl:"From",w:100,ta:"t"},
					{fn:"end_date",ft:"Date",lbl:"To",w:100,ta:"t"},
					{fn:"gross_pay",ft:"Currency",lbl:"Gross Pay",w:110,al:"right",ta:"t"},
					{fn:"total_deduction",ft:"Currency",lbl:"Deduction",w:110,al:"right",ta:"t"},
					{fn:"net_pay",ft:"Currency",lbl:"Net Pay",w:110,al:"right",ta:"t"},
					{fn:"status",ft:"Data",lbl:"Status",w:90,ta:"t"},
				]
			},
			{
				id:"hr_employee", name:"Employee Directory", ico:"👥", color:"#d97706", tag:"HR", tagBg:"#fef3c7", tagColor:"#b45309",
				desc:"All employees with department, designation, status.",
				report_type:"Script Report", ref_doctype:"Employee",
				joins:[
					{type:"LEFT",table:"Department",alias:"dept",on:"t.department = dept.name"},
					{type:"LEFT",table:"Designation",alias:"desig",on:"t.designation = desig.name"},
					{type:"LEFT",table:"Branch",alias:"br",on:"t.branch = br.name"},
				],
				filters:[
					{fn:"company",ft:"Link",lbl:"Company",op:"Company"},
					{fn:"department",ft:"Link",lbl:"Department",op:"Department"},
					{fn:"designation",ft:"Link",lbl:"Designation",op:"Designation"},
					{fn:"status",ft:"Select",lbl:"Status",op:"Active\nInactive\nLeft\nSuspended"},
					{fn:"employment_type",ft:"Link",lbl:"Employment Type",op:"Employment Type"},
					{fn:"gender",ft:"Select",lbl:"Gender",op:"Male\nFemale\nOther"},
				],
				columns:[
					{fn:"name",ft:"Link",lbl:"Employee ID",w:120,op:"Employee",ta:"t"},
					{fn:"employee_name",ft:"Data",lbl:"Employee Name",w:160,ta:"t"},
					{fn:"department",ft:"Link",lbl:"Department",w:130,op:"Department",ta:"t"},
					{fn:"designation",ft:"Data",lbl:"Designation",w:130,ta:"t"},
					{fn:"date_of_joining",ft:"Date",lbl:"Joining Date",w:110,ta:"t"},
					{fn:"gender",ft:"Data",lbl:"Gender",w:80,ta:"t"},
					{fn:"status",ft:"Data",lbl:"Status",w:90,ta:"t"},
					{fn:"cell_number",ft:"Phone",lbl:"Phone",w:110,ta:"t"},
					{fn:"personal_email",ft:"Data",lbl:"Email",w:160,ta:"t"},
				]
			},
			{
				id:"leave_summary", name:"Leave Summary", ico:"🌴", color:"#65a30d", tag:"HR", tagBg:"#ecfccb", tagColor:"#4d7c0f",
				desc:"Leave applications by employee, type, status.",
				report_type:"Script Report", ref_doctype:"Leave Application",
				joins:[
					{type:"LEFT",table:"Employee",alias:"emp",on:"t.employee = emp.name"},
					{type:"LEFT",table:"Leave Type",alias:"lt",on:"t.leave_type = lt.name"},
					{type:"LEFT",table:"Department",alias:"dept",on:"emp.department = dept.name"},
				],
				filters:[
					{fn:"company",ft:"Link",lbl:"Company",op:"Company"},
					{fn:"from_date",ft:"Date",lbl:"From Date",def:"Today",req:1},
					{fn:"to_date",ft:"Date",lbl:"To Date",def:"Today",req:1},
					{fn:"employee",ft:"Link",lbl:"Employee",op:"Employee"},
					{fn:"department",ft:"Link",lbl:"Department",op:"Department"},
					{fn:"leave_type",ft:"Link",lbl:"Leave Type",op:"Leave Type"},
					{fn:"status",ft:"Select",lbl:"Status",op:"Open\nApproved\nRejected\nCancelled"},
				],
				columns:[
					{fn:"employee",ft:"Link",lbl:"Employee",w:120,op:"Employee",ta:"t"},
					{fn:"employee_name",ft:"Data",lbl:"Employee Name",w:160,ta:"t"},
					{fn:"department",ft:"Link",lbl:"Department",w:130,op:"Department",ta:"emp"},
					{fn:"leave_type",ft:"Link",lbl:"Leave Type",w:130,op:"Leave Type",ta:"t"},
					{fn:"from_date",ft:"Date",lbl:"From",w:100,ta:"t"},
					{fn:"to_date",ft:"Date",lbl:"To",w:100,ta:"t"},
					{fn:"total_leave_days",ft:"Float",lbl:"Days",w:70,al:"right",ta:"t"},
					{fn:"status",ft:"Data",lbl:"Status",w:100,ta:"t"},
					{fn:"description",ft:"Small Text",lbl:"Reason",w:200,ta:"t"},
				]
			},
			{
				id:"attendance_report", name:"Attendance Report", ico:"📅", color:"#7c3aed", tag:"HR", tagBg:"#ede9fe", tagColor:"#6d28d9",
				desc:"Daily attendance with status, in/out time, late entry.",
				report_type:"Script Report", ref_doctype:"Attendance",
				joins:[
					{type:"LEFT",table:"Employee",alias:"emp",on:"t.employee = emp.name"},
					{type:"LEFT",table:"Department",alias:"dept",on:"emp.department = dept.name"},
					{type:"LEFT",table:"Shift Type",alias:"shft",on:"t.shift = shft.name"},
				],
				filters:[
					{fn:"company",ft:"Link",lbl:"Company",op:"Company"},
					{fn:"from_date",ft:"Date",lbl:"From Date",def:"Today",req:1},
					{fn:"to_date",ft:"Date",lbl:"To Date",def:"Today",req:1},
					{fn:"employee",ft:"Link",lbl:"Employee",op:"Employee"},
					{fn:"department",ft:"Link",lbl:"Department",op:"Department"},
					{fn:"status",ft:"Select",lbl:"Status",op:"Present\nAbsent\nHalf Day\nWork From Home\nOn Leave"},
				],
				columns:[
					{fn:"attendance_date",ft:"Date",lbl:"Date",w:100,ta:"t"},
					{fn:"employee",ft:"Link",lbl:"Employee",w:120,op:"Employee",ta:"t"},
					{fn:"employee_name",ft:"Data",lbl:"Employee Name",w:160,ta:"t"},
					{fn:"department",ft:"Data",lbl:"Department",w:130,ta:"emp"},
					{fn:"status",ft:"Data",lbl:"Status",w:100,ta:"t"},
					{fn:"in_time",ft:"Datetime",lbl:"In Time",w:130,ta:"t"},
					{fn:"out_time",ft:"Datetime",lbl:"Out Time",w:130,ta:"t"},
					{fn:"working_hours",ft:"Float",lbl:"Working Hours",w:110,al:"right",ta:"t"},
					{fn:"late_entry",ft:"Check",lbl:"Late Entry",w:80,ta:"t"},
					{fn:"early_exit",ft:"Check",lbl:"Early Exit",w:80,ta:"t"},
				]
			},
			{
				id:"expense_claims", name:"Expense Claims", ico:"🧾", color:"#dc2626", tag:"HR", tagBg:"#fee2e2", tagColor:"#b91c1c",
				desc:"Employee expense claims with type, amounts, status.",
				report_type:"Script Report", ref_doctype:"Expense Claim",
				joins:[
					{type:"LEFT",table:"Employee",alias:"emp",on:"t.employee = emp.name"},
					{type:"LEFT",table:"Department",alias:"dept",on:"emp.department = dept.name"},
					{type:"LEFT",table:"Expense Claim Detail",alias:"ecd",on:"ecd.parent = t.name"},
				],
				filters:[
					{fn:"company",ft:"Link",lbl:"Company",op:"Company"},
					{fn:"from_date",ft:"Date",lbl:"From Date",def:"Today",req:1},
					{fn:"to_date",ft:"Date",lbl:"To Date",def:"Today",req:1},
					{fn:"employee",ft:"Link",lbl:"Employee",op:"Employee"},
					{fn:"department",ft:"Link",lbl:"Department",op:"Department"},
					{fn:"approval_status",ft:"Select",lbl:"Approval Status",op:"Draft\nSubmitted\nApproved\nRejected"},
				],
				columns:[
					{fn:"name",ft:"Link",lbl:"Expense Claim",w:160,op:"Expense Claim",ta:"t"},
					{fn:"employee",ft:"Link",lbl:"Employee",w:120,op:"Employee",ta:"t"},
					{fn:"employee_name",ft:"Data",lbl:"Employee Name",w:160,ta:"t"},
					{fn:"department",ft:"Data",lbl:"Department",w:130,ta:"emp"},
					{fn:"expense_date",ft:"Date",lbl:"Date",w:100,ta:"t"},
					{fn:"expense_type",ft:"Data",lbl:"Expense Type",w:140,ta:"ecd"},
					{fn:"total_claimed_amount",ft:"Currency",lbl:"Claimed",w:110,al:"right",ta:"t"},
					{fn:"total_sanctioned_amount",ft:"Currency",lbl:"Sanctioned",w:110,al:"right",ta:"t"},
					{fn:"approval_status",ft:"Data",lbl:"Status",w:100,ta:"t"},
				]
			},
			// ── ASSETS ──
			{
				id:"asset_register", name:"Asset Register", ico:"🏢", color:"#475569", tag:"Assets", tagBg:"#f1f5f9", tagColor:"#334155",
				desc:"Fixed assets with category, location, value.",
				report_type:"Script Report", ref_doctype:"Asset",
				joins:[
					{type:"LEFT",table:"Asset Category",alias:"acat",on:"t.asset_category = acat.name"},
					{type:"LEFT",table:"Location",alias:"loc",on:"t.location = loc.name"},
				],
				filters:[
					{fn:"company",ft:"Link",lbl:"Company",op:"Company",req:1},
					{fn:"asset_category",ft:"Link",lbl:"Asset Category",op:"Asset Category"},
					{fn:"location",ft:"Link",lbl:"Location",op:"Location"},
					{fn:"status",ft:"Select",lbl:"Status",op:"Draft\nSubmitted\nPartially Depreciated\nFully Depreciated\nScrapped\nSold\nIn Maintenance"},
					{fn:"custodian",ft:"Link",lbl:"Custodian",op:"Employee"},
				],
				columns:[
					{fn:"name",ft:"Link",lbl:"Asset",w:160,op:"Asset",ta:"t"},
					{fn:"asset_name",ft:"Data",lbl:"Asset Name",w:180,ta:"t"},
					{fn:"asset_category",ft:"Link",lbl:"Category",w:140,op:"Asset Category",ta:"t"},
					{fn:"purchase_date",ft:"Date",lbl:"Purchase Date",w:110,ta:"t"},
					{fn:"gross_purchase_amount",ft:"Currency",lbl:"Purchase Value",w:120,al:"right",ta:"t"},
					{fn:"accumulated_depreciation_amount",ft:"Currency",lbl:"Acc. Depreciation",w:130,al:"right",ta:"t"},
					{fn:"value_after_depreciation",ft:"Currency",lbl:"Net Book Value",w:120,al:"right",ta:"t"},
					{fn:"location",ft:"Link",lbl:"Location",w:120,op:"Location",ta:"t"},
					{fn:"custodian",ft:"Link",lbl:"Custodian",w:130,op:"Employee",ta:"t"},
					{fn:"status",ft:"Data",lbl:"Status",w:110,ta:"t"},
				]
			},
			// ── PROJECTS ──
			{
				id:"project_tracker", name:"Project Tracker", ico:"📋", color:"#4f46e5", tag:"Projects", tagBg:"#e0e7ff", tagColor:"#3730a3",
				desc:"Projects with tasks, progress, timeline, cost.",
				report_type:"Script Report", ref_doctype:"Project",
				joins:[
					{type:"LEFT",table:"Customer",alias:"cust",on:"t.customer = cust.name"},
				],
				filters:[
					{fn:"company",ft:"Link",lbl:"Company",op:"Company"},
					{fn:"status",ft:"Select",lbl:"Status",op:"Open\nCompleted\nCancelled\nOverdue"},
					{fn:"from_date",ft:"Date",lbl:"From Date"},
					{fn:"to_date",ft:"Date",lbl:"To Date"},
					{fn:"customer",ft:"Link",lbl:"Customer",op:"Customer"},
					{fn:"department",ft:"Link",lbl:"Department",op:"Department"},
				],
				columns:[
					{fn:"name",ft:"Link",lbl:"Project",w:150,op:"Project",ta:"t"},
					{fn:"project_name",ft:"Data",lbl:"Project Name",w:200,ta:"t"},
					{fn:"status",ft:"Data",lbl:"Status",w:100,ta:"t"},
					{fn:"customer",ft:"Link",lbl:"Customer",w:140,op:"Customer",ta:"t"},
					{fn:"expected_start_date",ft:"Date",lbl:"Start Date",w:100,ta:"t"},
					{fn:"expected_end_date",ft:"Date",lbl:"End Date",w:100,ta:"t"},
					{fn:"percent_complete",ft:"Percent",lbl:"Progress %",w:90,al:"right",ta:"t"},
					{fn:"total_costing_amount",ft:"Currency",lbl:"Actual Cost",w:120,al:"right",ta:"t"},
					{fn:"total_budgeted_amount",ft:"Currency",lbl:"Budget",w:110,al:"right",ta:"t"},
				]
			},
			{
				id:"timesheet_summary", name:"Timesheet Summary", ico:"⏱️", color:"#6366f1", tag:"Projects", tagBg:"#e0e7ff", tagColor:"#4338ca",
				desc:"Timesheet hours and billing by employee, project.",
				report_type:"Script Report", ref_doctype:"Timesheet",
				joins:[
					{type:"LEFT",table:"Employee",alias:"emp",on:"t.employee = emp.name"},
					{type:"LEFT",table:"Timesheet Detail",alias:"tsd",on:"tsd.parent = t.name"},
					{type:"LEFT",table:"Project",alias:"proj",on:"tsd.project = proj.name"},
				],
				filters:[
					{fn:"company",ft:"Link",lbl:"Company",op:"Company"},
					{fn:"from_date",ft:"Date",lbl:"From Date",def:"Today",req:1},
					{fn:"to_date",ft:"Date",lbl:"To Date",def:"Today",req:1},
					{fn:"employee",ft:"Link",lbl:"Employee",op:"Employee"},
					{fn:"project",ft:"Link",lbl:"Project",op:"Project"},
					{fn:"status",ft:"Select",lbl:"Status",op:"Draft\nSubmitted\nCancelled\nBilled"},
				],
				columns:[
					{fn:"name",ft:"Link",lbl:"Timesheet",w:150,op:"Timesheet",ta:"t"},
					{fn:"employee",ft:"Link",lbl:"Employee",w:120,op:"Employee",ta:"t"},
					{fn:"employee_name",ft:"Data",lbl:"Employee Name",w:160,ta:"emp"},
					{fn:"start_date",ft:"Date",lbl:"Start Date",w:100,ta:"t"},
					{fn:"end_date",ft:"Date",lbl:"End Date",w:100,ta:"t"},
					{fn:"project",ft:"Link",lbl:"Project",w:150,op:"Project",ta:"tsd"},
					{fn:"hours",ft:"Float",lbl:"Hours",w:80,al:"right",ta:"tsd"},
					{fn:"billing_hours",ft:"Float",lbl:"Billing Hrs",w:90,al:"right",ta:"t"},
					{fn:"total_billed_amount",ft:"Currency",lbl:"Billed Amount",w:120,al:"right",ta:"t"},
					{fn:"status",ft:"Data",lbl:"Status",w:90,ta:"t"},
				]
			},
			// ── CRM ──
			{
				id:"lead_report", name:"Lead Report", ico:"🎯", color:"#e11d48", tag:"CRM", tagBg:"#ffe4e6", tagColor:"#be123c",
				desc:"CRM leads by source, status, territory.",
				report_type:"Script Report", ref_doctype:"Lead",
				joins:[
					{type:"LEFT",table:"Campaign",alias:"camp",on:"t.campaign_name = camp.name"},
				],
				filters:[
					{fn:"company",ft:"Link",lbl:"Company",op:"Company"},
					{fn:"from_date",ft:"Date",lbl:"From Date",def:"Today",req:1},
					{fn:"to_date",ft:"Date",lbl:"To Date",def:"Today",req:1},
					{fn:"status",ft:"Select",lbl:"Status",op:"New\nOpen\nReplied\nOpportunity\nQuotation\nLost Quotation\nInterested\nConverted\nDo Not Contact"},
					{fn:"lead_owner",ft:"Link",lbl:"Lead Owner",op:"User"},
					{fn:"source",ft:"Select",lbl:"Source",op:"Cold Calling\nExhibition\nReferral\nOther"},
					{fn:"territory",ft:"Link",lbl:"Territory",op:"Territory"},
				],
				columns:[
					{fn:"name",ft:"Link",lbl:"Lead",w:140,op:"Lead",ta:"t"},
					{fn:"lead_name",ft:"Data",lbl:"Lead Name",w:160,ta:"t"},
					{fn:"company_name",ft:"Data",lbl:"Company",w:150,ta:"t"},
					{fn:"source",ft:"Data",lbl:"Source",w:110,ta:"t"},
					{fn:"territory",ft:"Link",lbl:"Territory",w:110,op:"Territory",ta:"t"},
					{fn:"status",ft:"Data",lbl:"Status",w:100,ta:"t"},
					{fn:"lead_owner",ft:"Link",lbl:"Owner",w:130,op:"User",ta:"t"},
					{fn:"creation",ft:"Datetime",lbl:"Created",w:130,ta:"t"},
					{fn:"converted",ft:"Check",lbl:"Converted",w:80,ta:"t"},
				]
			},
			{
				id:"opportunity_pipeline", name:"Opportunity Pipeline", ico:"🚀", color:"#be185d", tag:"CRM", tagBg:"#fce7f3", tagColor:"#9d174d",
				desc:"Opportunity pipeline: stage, value, closing date.",
				report_type:"Script Report", ref_doctype:"Opportunity",
				joins:[
					{type:"LEFT",table:"Customer",alias:"cust",on:"t.party_name = cust.name AND t.opportunity_from = 'Customer'"},
				],
				filters:[
					{fn:"company",ft:"Link",lbl:"Company",op:"Company"},
					{fn:"from_date",ft:"Date",lbl:"From Date",def:"Today",req:1},
					{fn:"to_date",ft:"Date",lbl:"To Date",def:"Today",req:1},
					{fn:"status",ft:"Select",lbl:"Status",op:"Open\nQuotation\nConverted\nSuspended\nLost\nClosed"},
					{fn:"sales_stage",ft:"Link",lbl:"Sales Stage",op:"Sales Stage"},
					{fn:"opportunity_owner",ft:"Link",lbl:"Opportunity Owner",op:"User"},
					{fn:"territory",ft:"Link",lbl:"Territory",op:"Territory"},
				],
				columns:[
					{fn:"name",ft:"Link",lbl:"Opportunity",w:160,op:"Opportunity",ta:"t"},
					{fn:"party_name",ft:"Data",lbl:"Customer/Lead",w:160,ta:"t"},
					{fn:"opportunity_amount",ft:"Currency",lbl:"Opp. Amount",w:120,al:"right",ta:"t"},
					{fn:"probability",ft:"Percent",lbl:"Probability %",w:100,al:"right",ta:"t"},
					{fn:"expected_closing",ft:"Date",lbl:"Expected Close",w:120,ta:"t"},
					{fn:"sales_stage",ft:"Data",lbl:"Stage",w:110,ta:"t"},
					{fn:"status",ft:"Data",lbl:"Status",w:100,ta:"t"},
					{fn:"opportunity_owner",ft:"Link",lbl:"Owner",w:130,op:"User",ta:"t"},
					{fn:"source",ft:"Data",lbl:"Source",w:110,ta:"t"},

				]
			},
			// ── ADVANCED ──
			{
				id:"reorder_alert", name:"Reorder Level Alert", ico:"⚠️", color:"#b45309", tag:"Inventory", tagBg:"#fef3c7", tagColor:"#92400e",
				desc:"Items below reorder level — actual vs reorder qty.",
				report_type:"Script Report", ref_doctype:"Item",
				joins:[
					{type:"LEFT",table:"Bin",alias:"bin",on:"t.name = bin.item_code"},
					{type:"LEFT",table:"Item Default",alias:"idef",on:"idef.parent = t.name"},
				],
				filters:[
					{fn:"company",ft:"Link",lbl:"Company",op:"Company",req:1},
					{fn:"warehouse",ft:"Link",lbl:"Warehouse",op:"Warehouse"},
					{fn:"item_group",ft:"Link",lbl:"Item Group",op:"Item Group"},
				],
				columns:[
					{fn:"name",ft:"Link",lbl:"Item Code",w:160,op:"Item",ta:"t"},
					{fn:"item_name",ft:"Data",lbl:"Item Name",w:200,ta:"t"},
					{fn:"item_group",ft:"Link",lbl:"Item Group",w:130,op:"Item Group",ta:"t"},
					{fn:"warehouse",ft:"Link",lbl:"Warehouse",w:150,op:"Warehouse",ta:"bin"},
					{fn:"actual_qty",ft:"Float",lbl:"Actual Qty",w:100,al:"right",ta:"bin"},
					{fn:"reorder_level",ft:"Float",lbl:"Reorder Level",w:110,al:"right",ta:"bin"},
					{fn:"reorder_qty",ft:"Float",lbl:"Reorder Qty",w:110,al:"right",ta:"bin"},
					{fn:"stock_uom",ft:"Data",lbl:"UOM",w:70,ta:"t"},
				]
			},
			{
				id:"delivery_performance", name:"Delivery Performance", ico:"🚚", color:"#0369a1", tag:"Logistics", tagBg:"#e0f2fe", tagColor:"#0c4a6e",
				desc:"Delivery Notes vs Sales Orders: qty ordered, delivered, pending.",
				report_type:"Script Report", ref_doctype:"Delivery Note",
				joins:[
					{type:"LEFT",table:"Delivery Note Item",alias:"dni",on:"dni.parent = t.name"},
					{type:"LEFT",table:"Sales Order",alias:"so",on:"dni.against_sales_order = so.name"},
					{type:"LEFT",table:"Customer",alias:"cust",on:"t.customer = cust.name"},
				],
				filters:[
					{fn:"company",ft:"Link",lbl:"Company",op:"Company",req:1},
					{fn:"from_date",ft:"Date",lbl:"From Date",def:"Today",req:1},
					{fn:"to_date",ft:"Date",lbl:"To Date",def:"Today",req:1},
					{fn:"customer",ft:"Link",lbl:"Customer",op:"Customer"},
					{fn:"status",ft:"Select",lbl:"DN Status",op:"Draft\nSubmitted\nReturn Issued\nCompleted\nCancelled"},
				],
				columns:[
					{fn:"name",ft:"Link",lbl:"Delivery Note",w:160,op:"Delivery Note",ta:"t"},
					{fn:"posting_date",ft:"Date",lbl:"Delivery Date",w:110,ta:"t"},
					{fn:"customer",ft:"Link",lbl:"Customer",w:150,op:"Customer",ta:"t"},
					{fn:"against_sales_order",ft:"Link",lbl:"Sales Order",w:150,op:"Sales Order",ta:"dni"},
					{fn:"item_code",ft:"Link",lbl:"Item",w:140,op:"Item",ta:"dni"},
					{fn:"qty",ft:"Float",lbl:"Ordered Qty",w:100,al:"right",ta:"dni"},
					{fn:"delivered_qty",ft:"Float",lbl:"Delivered",w:100,al:"right",ta:"dni"},
					{fn:"status",ft:"Data",lbl:"Status",w:90,ta:"t"},
				]
			},
			{
				id:"pending_po_receipt", name:"Pending PO Receipt", ico:"📦", color:"#7c3aed", tag:"Purchase", tagBg:"#ede9fe", tagColor:"#5b21b6",
				desc:"Purchase orders with outstanding receipt quantity.",
				report_type:"Script Report", ref_doctype:"Purchase Order",
				joins:[
					{type:"LEFT",table:"Supplier",alias:"sup",on:"t.supplier = sup.name"},
				],
				filters:[
					{fn:"company",ft:"Link",lbl:"Company",op:"Company",req:1},
					{fn:"from_date",ft:"Date",lbl:"From Date",def:"Today",req:1},
					{fn:"to_date",ft:"Date",lbl:"To Date",def:"Today",req:1},
					{fn:"supplier",ft:"Link",lbl:"Supplier",op:"Supplier"},
					{fn:"status",ft:"Select",lbl:"Status",op:"Draft\nTo Receive and Bill\nTo Bill\nCompleted\nCancelled\nClosed"},
				],
				columns:[
					{fn:"name",ft:"Link",lbl:"PO",w:160,op:"Purchase Order",ta:"t"},
					{fn:"transaction_date",ft:"Date",lbl:"PO Date",w:100,ta:"t"},
					{fn:"supplier",ft:"Link",lbl:"Supplier",w:160,op:"Supplier",ta:"t"},
					{fn:"supplier_name",ft:"Data",lbl:"Supplier Name",w:180,ta:"sup"},
					{fn:"grand_total",ft:"Currency",lbl:"PO Total",w:120,al:"right",ta:"t"},
					{fn:"per_received",ft:"Percent",lbl:"% Received",w:100,al:"right",ta:"t"},
					{fn:"per_billed",ft:"Percent",lbl:"% Billed",w:100,al:"right",ta:"t"},
					{fn:"status",ft:"Data",lbl:"Status",w:120,ta:"t"},
					{fn:"schedule_date",ft:"Date",lbl:"Required By",w:110,ta:"t"},
				]
			},
			{
				id:"pl_quick_view", name:"P&L Quick View", ico:"📊", color:"#065f46", tag:"Accounts", tagBg:"#d1fae5", tagColor:"#064e3b",
				desc:"Profit & Loss by account: debit vs credit grouped by account.",
				report_type:"Script Report", ref_doctype:"GL Entry",
				joins:[
					{type:"LEFT",table:"Account",alias:"acc",on:"t.account = acc.name"},
				],
				filters:[
					{fn:"company",ft:"Link",lbl:"Company",op:"Company",req:1},
					{fn:"from_date",ft:"Date",lbl:"From Date",def:"Today",req:1},
					{fn:"to_date",ft:"Date",lbl:"To Date",def:"Today",req:1},
					{fn:"finance_book",ft:"Link",lbl:"Finance Book",op:"Finance Book"},
					{fn:"root_type",ft:"Select",lbl:"Root Type",op:"Income\nExpense\nAsset\nLiability\nEquity"},
				],
				columns:[
					{fn:"account",ft:"Link",lbl:"Account",w:200,op:"Account",ta:"t"},
					{fn:"account_name",ft:"Data",lbl:"Account Name",w:200,ta:"acc"},
					{fn:"root_type",ft:"Data",lbl:"Root Type",w:90,ta:"acc"},
					{fn:"account_type",ft:"Data",lbl:"Account Type",w:120,ta:"acc"},
					{fn:"debit",ft:"Currency",lbl:"Total Debit",w:130,al:"right",ta:"t"},
					{fn:"credit",ft:"Currency",lbl:"Total Credit",w:130,al:"right",ta:"t"},
				]
			},
			{
				id:"service_issue_tracker", name:"Service Issue Tracker", ico:"🎫", color:"#dc2626", tag:"Support", tagBg:"#fee2e2", tagColor:"#991b1b",
				desc:"Support issues by customer, priority, SLA and status.",
				report_type:"Script Report", ref_doctype:"Issue",
				joins:[
					{type:"LEFT",table:"Customer",alias:"cust",on:"t.customer = cust.name"},
					{type:"LEFT",table:"User",alias:"usr",on:"t.assigned_to = usr.name"},
				],
				filters:[
					{fn:"from_date",ft:"Date",lbl:"From Date",def:"Today",req:1},
					{fn:"to_date",ft:"Date",lbl:"To Date",def:"Today",req:1},
					{fn:"status",ft:"Select",lbl:"Status",op:"Open\nReplied\nHold\nResolved\nClosed"},
					{fn:"priority",ft:"Select",lbl:"Priority",op:"Low\nMedium\nHigh\nUrgent"},
					{fn:"customer",ft:"Link",lbl:"Customer",op:"Customer"},
				],
				columns:[
					{fn:"name",ft:"Link",lbl:"Issue",w:150,op:"Issue",ta:"t"},
					{fn:"subject",ft:"Data",lbl:"Subject",w:250,ta:"t"},
					{fn:"customer",ft:"Link",lbl:"Customer",w:150,op:"Customer",ta:"t"},
					{fn:"customer_name",ft:"Data",lbl:"Customer Name",w:180,ta:"cust"},
					{fn:"status",ft:"Data",lbl:"Status",w:90,ta:"t"},
					{fn:"priority",ft:"Data",lbl:"Priority",w:80,ta:"t"},
					{fn:"opening_date",ft:"Date",lbl:"Opened",w:100,ta:"t"},
					{fn:"resolution_date",ft:"Date",lbl:"Resolved",w:100,ta:"t"},
					{fn:"response_by",ft:"Datetime",lbl:"SLA Response",w:130,ta:"t"},
					{fn:"full_name",ft:"Data",lbl:"Assigned To",w:130,ta:"usr"},
				]
			},
			{
				id:"budget_variance", name:"Budget vs Actual", ico:"📉", color:"#1e3a5f", tag:"Accounts", tagBg:"#dbeafe", tagColor:"#1e40af",
				desc:"Budget consumption: allocated budget vs actual GL posting.",
				report_type:"Script Report", ref_doctype:"Budget",
				joins:[
					{type:"LEFT",table:"Budget Account",alias:"ba",on:"ba.parent = t.name"},
					{type:"LEFT",table:"Account",alias:"acc",on:"ba.account = acc.name"},
					{type:"LEFT",table:"Cost Center",alias:"cc",on:"t.cost_center = cc.name"},
				],
				filters:[
					{fn:"company",ft:"Link",lbl:"Company",op:"Company",req:1},
					{fn:"fiscal_year",ft:"Link",lbl:"Fiscal Year",op:"Fiscal Year",req:1},
					{fn:"cost_center",ft:"Link",lbl:"Cost Center",op:"Cost Center"},
					{fn:"budget_against",ft:"Select",lbl:"Budget Against",op:"Cost Center\nProject"},
				],
				columns:[
					{fn:"name",ft:"Link",lbl:"Budget",w:160,op:"Budget",ta:"t"},
					{fn:"cost_center",ft:"Link",lbl:"Cost Center",w:160,op:"Cost Center",ta:"t"},
					{fn:"account",ft:"Link",lbl:"Account",w:180,op:"Account",ta:"ba"},
					{fn:"account_name",ft:"Data",lbl:"Account Name",w:180,ta:"acc"},
					{fn:"budget_amount",ft:"Currency",lbl:"Budgeted",w:120,al:"right",ta:"ba"},
					{fn:"fiscal_year",ft:"Data",lbl:"Fiscal Year",w:100,ta:"t"},
					{fn:"action_if_annual_budget_exceeded",ft:"Data",lbl:"Action",w:100,ta:"t"},
				]
			},
			{
				id:"asset_depreciation_schedule", name:"Asset Depreciation", ico:"🏗️", color:"#374151", tag:"Assets", tagBg:"#f3f4f6", tagColor:"#111827",
				desc:"Fixed asset depreciation schedule by category and method.",
				report_type:"Script Report", ref_doctype:"Asset",
				joins:[
					{type:"LEFT",table:"Asset Finance Book",alias:"afb",on:"afb.parent = t.name"},
					{type:"LEFT",table:"Asset Category",alias:"acat",on:"t.asset_category = acat.name"},
				],
				filters:[
					{fn:"company",ft:"Link",lbl:"Company",op:"Company",req:1},
					{fn:"asset_category",ft:"Link",lbl:"Asset Category",op:"Asset Category"},
					{fn:"status",ft:"Select",lbl:"Status",op:"Draft\nSubmitted\nPartially Depreciated\nFully Depreciated\nScrapped\nSold"},
					{fn:"from_date",ft:"Date",lbl:"Purchase From",def:"Today"},
					{fn:"to_date",ft:"Date",lbl:"Purchase To",def:"Today"},
				],
				columns:[
					{fn:"name",ft:"Link",lbl:"Asset",w:160,op:"Asset",ta:"t"},
					{fn:"asset_name",ft:"Data",lbl:"Asset Name",w:200,ta:"t"},
					{fn:"asset_category",ft:"Link",lbl:"Category",w:140,op:"Asset Category",ta:"t"},
					{fn:"purchase_date",ft:"Date",lbl:"Purchase Date",w:110,ta:"t"},
					{fn:"gross_purchase_amount",ft:"Currency",lbl:"Purchase Value",w:130,al:"right",ta:"t"},
					{fn:"value_after_depreciation",ft:"Currency",lbl:"Current Value",w:130,al:"right",ta:"t"},
					{fn:"depreciation_method",ft:"Data",lbl:"Dep. Method",w:130,ta:"afb"},
					{fn:"total_number_of_depreciations",ft:"Int",lbl:"Total Periods",w:100,al:"right",ta:"afb"},
					{fn:"status",ft:"Data",lbl:"Status",w:110,ta:"t"},
				]
			},
		];

		/* ── Per-preset query conditions (extra WHERE, ORDER BY, GROUP BY, HAVING, LIMIT) ── */
		const PRESET_CONDITIONS = {
			blank:                  { extra_where:"",                                         order_by:"t.modified DESC",                                    group_by:"",                                            having:"",                     limit_rows:0    },
			sales_invoice:          { extra_where:"",                                         order_by:"t.posting_date DESC, t.name DESC",                   group_by:"",                                            having:"",                     limit_rows:0    },
			sales_order:            { extra_where:"",                                         order_by:"t.transaction_date DESC",                            group_by:"",                                            having:"",                     limit_rows:0    },
			quotation:              { extra_where:"AND t.docstatus < 2",                      order_by:"t.transaction_date DESC",                            group_by:"",                                            having:"",                     limit_rows:0    },
			item_wise_sales:        { extra_where:"AND si.docstatus = 1",                     order_by:"SUM(t.amount) DESC",                                 group_by:"t.item_code, t.item_name, itm.item_group",    having:"SUM(t.qty) > 0",       limit_rows:500  },
			purchase_invoice:       { extra_where:"",                                         order_by:"t.posting_date DESC, t.name DESC",                   group_by:"",                                            having:"",                     limit_rows:0    },
			purchase_order:         { extra_where:"",                                         order_by:"t.transaction_date DESC",                            group_by:"",                                            having:"",                     limit_rows:0    },
			purchase_receipt_items: { extra_where:"AND pr.docstatus = 1",                     order_by:"pr.posting_date DESC",                               group_by:"",                                            having:"",                     limit_rows:0    },
			accounts_receivable:    { extra_where:"AND t.outstanding_amount > 0",             order_by:"t.outstanding_amount DESC",                          group_by:"",                                            having:"",                     limit_rows:0    },
			accounts_payable:       { extra_where:"AND t.outstanding_amount > 0",             order_by:"t.outstanding_amount DESC",                          group_by:"",                                            having:"",                     limit_rows:0    },
			payment_register:       { extra_where:"AND t.docstatus = 1",                      order_by:"t.posting_date DESC",                                group_by:"",                                            having:"",                     limit_rows:0    },
			gl_ledger:              { extra_where:"AND t.is_cancelled = 0",                   order_by:"t.posting_date DESC, t.creation DESC",               group_by:"",                                            having:"",                     limit_rows:1000 },
			journal_entry:          { extra_where:"AND t.docstatus = 1",                      order_by:"t.posting_date DESC",                                group_by:"",                                            having:"",                     limit_rows:0    },
			stock_movement:         { extra_where:"",                                         order_by:"t.posting_date DESC, t.posting_time DESC",           group_by:"",                                            having:"",                     limit_rows:1000 },
			inventory_valuation:    { extra_where:"AND bin.actual_qty > 0",                   order_by:"t.item_name ASC, bin.warehouse ASC",                 group_by:"",                                            having:"",                     limit_rows:0    },
			item_price_list:        { extra_where:"",                                         order_by:"t.item_code ASC, t.price_list ASC",                  group_by:"",                                            having:"",                     limit_rows:0    },
			batch_tracking:         { extra_where:"AND t.disabled = 0",                       order_by:"t.expiry_date ASC",                                  group_by:"",                                            having:"",                     limit_rows:0    },
			bom_summary:            { extra_where:"AND t.docstatus = 1 AND t.is_active = 1",  order_by:"t.item ASC",                                         group_by:"",                                            having:"",                     limit_rows:0    },
			work_order:             { extra_where:"",                                         order_by:"t.planned_start_date ASC",                           group_by:"",                                            having:"",                     limit_rows:0    },
			job_card:               { extra_where:"AND t.docstatus < 2",                      order_by:"t.creation DESC",                                    group_by:"",                                            having:"",                     limit_rows:0    },
			payroll_summary:        { extra_where:"AND t.docstatus = 1",                      order_by:"emp.department ASC, t.employee_name ASC",            group_by:"",                                            having:"",                     limit_rows:0    },
			hr_employee:            { extra_where:"",                                         order_by:"t.department ASC, t.employee_name ASC",              group_by:"",                                            having:"",                     limit_rows:0    },
			leave_summary:          { extra_where:"AND t.docstatus = 1",                      order_by:"t.from_date DESC",                                   group_by:"",                                            having:"",                     limit_rows:0    },
			attendance_report:      { extra_where:"AND t.docstatus = 1",                      order_by:"t.attendance_date DESC, t.employee ASC",             group_by:"",                                            having:"",                     limit_rows:0    },
			expense_claims:         { extra_where:"AND t.docstatus < 2",                      order_by:"t.expense_date DESC",                                group_by:"",                                            having:"",                     limit_rows:0    },
			asset_register:         { extra_where:"AND t.docstatus = 1",                      order_by:"t.asset_category ASC, t.asset_name ASC",             group_by:"",                                            having:"",                     limit_rows:0    },
			project_tracker:        { extra_where:"",                                         order_by:"t.expected_end_date ASC, t.status ASC",              group_by:"",                                            having:"",                     limit_rows:0    },
			timesheet_summary:      { extra_where:"AND t.docstatus = 1",                      order_by:"t.start_date DESC, t.employee ASC",                  group_by:"",                                            having:"",                     limit_rows:0    },
			lead_report:            { extra_where:"",                                         order_by:"t.creation DESC",                                    group_by:"",                                            having:"",                     limit_rows:0    },
			opportunity_pipeline:   { extra_where:"AND t.docstatus < 2",                      order_by:"t.expected_closing ASC, t.probability DESC",         group_by:"",                                            having:"",                     limit_rows:0    },
			// ── ADVANCED ──
			reorder_alert:              { extra_where:"AND bin.actual_qty <= bin.reorder_level",    order_by:"bin.actual_qty ASC",                                 group_by:"",                                            having:"",                     limit_rows:0    },
			delivery_performance:       { extra_where:"AND t.docstatus = 1",                       order_by:"t.posting_date DESC",                                group_by:"",                                            having:"",                     limit_rows:0    },
			pending_po_receipt:         { extra_where:"AND t.per_received < 100 AND t.docstatus = 1 AND t.status NOT IN ('Completed','Cancelled','Closed')", order_by:"t.schedule_date ASC", group_by:"",             having:"",                     limit_rows:0    },
			pl_quick_view:              { extra_where:"AND t.is_cancelled = 0",                    order_by:"acc.root_type ASC, t.account ASC",                   group_by:"t.account, acc.account_name, acc.root_type, acc.account_type", having:"", limit_rows:0    },
			service_issue_tracker:      { extra_where:"",                                          order_by:"t.opening_date DESC, t.priority DESC",               group_by:"",                                            having:"",                     limit_rows:0    },
			budget_variance:            { extra_where:"AND t.docstatus = 1",                       order_by:"cc.name ASC, acc.account_name ASC",                  group_by:"",                                            having:"",                     limit_rows:0    },
			asset_depreciation_schedule:{ extra_where:"AND t.docstatus = 1",                       order_by:"t.asset_category ASC, t.asset_name ASC",             group_by:"",                                            having:"",                     limit_rows:0    },
		};

		$p.append(phdr("Report Builder","Scaffold Script / Query reports with presets, multi-table joins, filters and columns.",icoChart(20)));

		/* ── Preset Selector ── */
		const $cp = card($p, "Report Presets");
		$cp.append(info("Select a preset to auto-fill the ref DocType, joins, filters and columns. You can freely edit everything after applying."));
		const $psw = $(`<div class="dkrb-preset-search-wrap"><input id="dkrb-search" class="dkrb-preset-search" type="text" placeholder="Search presets by name, module or keyword…"><span class="dkrb-preset-count" id="dkrb-pcount"></span></div>`).appendTo($cp);
		const $pg = $(`<div class="dkrb-preset-grid"></div>`).appendTo($cp);
		REPORT_PRESETS.forEach(pr => {
			$(`<div class="dkrb-preset-card" data-pid="${pr.id}">
				<div class="dkrb-preset-top" style="background:${pr.color}"></div>
				<div class="dkrb-preset-body">
					<div class="dkrb-preset-ico">${pr.ico}</div>
					<div class="dkrb-preset-nm">${pr.name}</div>
					<div class="dkrb-preset-ds">${pr.desc}</div>
					<div class="dkrb-preset-tag" style="background:${pr.tagBg};color:${pr.tagColor}">${pr.tag}</div>
				</div>
			</div>`).appendTo($pg).on("click", function() {
				$pg.find(".dkrb-preset-card").removeClass("selected");
				$(this).addClass("selected");
				applyPreset(pr);
			});
		});
		// Initialize count and wire search
		const _updatePCount = () => {
			const total = REPORT_PRESETS.length;
			const vis = $pg.find(".dkrb-preset-card:not(.dkrb-hidden)").length;
			$("#dkrb-pcount").text(vis === total ? `${total} presets` : `${vis} of ${total}`);
		};
		_updatePCount();
		$("#dkrb-search").on("input", function() {
			const q = $(this).val().trim().toLowerCase();
			$pg.find(".dkrb-preset-card").each(function() {
				const pid = $(this).data("pid");
				const pr = REPORT_PRESETS.find(p => p.id === pid);
				if (!pr) return;
				const match = !q ||
					pr.name.toLowerCase().includes(q) ||
					pr.tag.toLowerCase().includes(q) ||
					pr.desc.toLowerCase().includes(q) ||
					(pr.ref_doctype||"").toLowerCase().includes(q);
				$(this).toggleClass("dkrb-hidden", !match);
			});
			_updatePCount();
		});

		// "Start from scratch" link
		$cp.append(`<div style="margin-top:8px;text-align:right"><a href="#" id="dkrb-skip" style="font-size:12px;color:#5c4da8;text-decoration:underline">Start from scratch ›</a></div>`);
		$p.on('click','#dkrb-skip',function(e){e.preventDefault();_showBuilder();});

		const $builderWrap = $('<div style="display:none"></div>').appendTo($p);

		/* ── Report Identity ── */
		const $c1 = card($builderWrap, "Report Identity");
		$c1.append(`<div class="dkst-g2">
			${AppSel("rp_app")} ${ModSel("rp_mod")}
			${FR("rp_nm","Report Name","text","My Custom Report")}
			${DtSel("rp_dt","Ref DocType")}
			${F("rp_ty","Report Type","select","","",[["Script Report","Script Report"],["Query Report","Query Report"]])}
			${F("rp_st","Is Standard","select","","",[["Yes","Yes"],["No","No"]])}
		</div>
		<div class="dkst-checks" style="margin-top:12px">
			${CHK("rp_tr","Add Total Row")} ${CHK("rp_ow","Overwrite Existing")}
		</div>`);
		wireAMD($c1,"rp_app","rp_mod","rp_dt");

		/* ── Join Builder ── */
		const $c2 = card($builderWrap, "Table Joins");
		$c2.append(info(`Add tables to JOIN the primary DocType <span class="dkst-code">t</span>. Use alias prefixes in ON conditions — e.g. <span class="dkst-code">t.customer = cust.name</span>. Presets auto-populate joins; you can add, edit or remove rows.`));
		$c2.append(`<div class="dkst-tbl-wrap"><table class="dkst-tbl">
			<thead><tr>
				<th style="width:150px">Join Type</th>
				<th>Table (DocType)</th>
				<th style="width:100px">Alias</th>
				<th>ON Condition</th>
				<th style="width:36px"></th>
			</tr></thead>
			<tbody id="rp-jr"></tbody>
		</table></div>`);
		$(`<div class="dkst-add-row">+ Add Join</div>`).appendTo($c2).on("click", ()=>addRJ());

		/* ── Query Conditions ── */
		const $c3 = card($builderWrap, "Query Conditions");
		$c3.append(info(`Fine-tune the generated SQL. All fields are optional and appended to the scaffolded query. The <span class="dkst-code">get_conditions()</span> function body is auto-generated from preset filters — add any extra SQL fragments here.`));
		$c3.append(`<div class="dkst-g2" style="gap:10px 18px">
			<div class="dkst-fld" style="grid-column:1/-1">
				<label class="dkst-lbl">Extra WHERE Conditions <span style="color:#9080b8;font-weight:400">(raw SQL, appended after preset conditions)</span></label>
				<textarea id="rp_where" class="dkst-inp" rows="3" style="width:100%;font-family:monospace;font-size:12px;resize:vertical" placeholder="AND t.company = %(company)s&#10;AND t.status = 'Submitted'&#10;AND si.customer_group = 'Commercial'"></textarea>
			</div>
			<div class="dkst-fld">
				<label class="dkst-lbl">GROUP BY</label>
				<input id="rp_grp" class="dkst-inp" placeholder="t.customer, t.company">
			</div>
			<div class="dkst-fld">
				<label class="dkst-lbl">HAVING</label>
				<input id="rp_hav" class="dkst-inp" placeholder="SUM(t.grand_total) > 0">
			</div>
			<div class="dkst-fld">
				<label class="dkst-lbl">ORDER BY <span style="color:#9080b8;font-weight:400">(overrides preset default)</span></label>
				<input id="rp_ord" class="dkst-inp" placeholder="t.posting_date DESC, t.name DESC">
			</div>
			<div class="dkst-fld">
				<label class="dkst-lbl">LIMIT <span style="color:#9080b8;font-weight:400">(rows, 0 = no limit)</span></label>
				<input id="rp_lim" class="dkst-inp" type="number" min="0" value="0" style="width:100px">
			</div>
		</div>`);

		/* ── Preset state ── */
		let _presetData = { filters:[], columns:[] };

		/* ── Row helper ── */
		function addRJ(d={}) {
			const JTYPES = [
				["LEFT","LEFT JOIN"],["LEFT OUTER","LEFT OUTER JOIN"],
				["INNER","INNER JOIN"],["RIGHT","RIGHT JOIN"],
				["RIGHT OUTER","RIGHT OUTER JOIN"],["CROSS","CROSS JOIN"],
				["STRAIGHT_JOIN","STRAIGHT_JOIN"],
			];
			const $tr=$(`<tr>
				<td><select class="dkst-sel f-jt" style="width:148px">
					${JTYPES.map(([v,l])=>`<option value="${v}" ${(d.type||"LEFT")===v?"selected":""}>${l}</option>`).join("")}
				</select></td>
				<td><input class="dkst-inp f-jtbl" value="${d.table||""}" placeholder="e.g. Customer"></td>
				<td><input class="dkst-inp f-ja" value="${d.alias||""}" placeholder="cust" style="width:95px"></td>
				<td><input class="dkst-inp f-jo" value="${d.on||""}" placeholder="t.customer = cust.name"></td>
				<td><button class="dkst-del-btn">×</button></td>
			</tr>`);
			$tr.find(".dkst-del-btn").on("click", ()=>$tr.remove());
			$("#rp-jr").append($tr);
		}

		/* ── Show builder ── */
		function _showBuilder() {
			$builderWrap.show();
		}

		/* ── Apply Preset ── */
		function applyPreset(pr) {
			// Ref DocType
			if (pr.ref_doctype) {
				const $dt = $("#rp_dt");
				if ($dt.is("select")) {
					if (!$dt.find(`option[value="${pr.ref_doctype}"]`).length)
						$dt.append(`<option value="${pr.ref_doctype}">${pr.ref_doctype}</option>`);
					$dt.val(pr.ref_doctype);
				} else {
					$dt.val(pr.ref_doctype);
				}
			}
			// Report type
			if (pr.report_type) $("#rp_ty").val(pr.report_type);
			// Joins
			$("#rp-jr").empty(); (pr.joins||[]).forEach(j => addRJ(j));
			// Store filters + columns (used by generate, not shown as editable tables)
			_presetData = { filters: pr.filters||[], columns: pr.columns||[] };
			// Populate query condition fields from PRESET_CONDITIONS map
			const cond = PRESET_CONDITIONS[pr.id] || {};
			$("#rp_where").val(cond.extra_where || "");
			$("#rp_ord").val(cond.order_by || "");
			$("#rp_grp").val(cond.group_by || "");
			$("#rp_hav").val(cond.having || "");
			$("#rp_lim").val(cond.limit_rows || 0);
			// Info badge on identity card
			$("#rp-preset-badge").remove();
			const condParts = [];
			if (cond.extra_where) condParts.push("WHERE");
			if (cond.group_by)    condParts.push("GROUP BY");
			if (cond.having)      condParts.push("HAVING");
			if (cond.order_by)    condParts.push("ORDER BY");
			if (cond.limit_rows)  condParts.push(`LIMIT ${cond.limit_rows}`);
			$(`<div id="rp-preset-badge" style="display:inline-flex;align-items:center;gap:7px;padding:5px 12px;background:linear-gradient(135deg,#5c4da8,#8b5cf6);color:#fff;border-radius:20px;font-size:11.5px;font-weight:600;margin-top:10px;flex-wrap:wrap;">
				<span>${pr.ico}</span><span>${pr.name}</span>
				<span style="opacity:.75;font-weight:400">· ${(pr.filters||[]).length} filters · ${(pr.columns||[]).length} cols · ${(pr.joins||[]).length} joins</span>
				${condParts.length ? `<span style="opacity:.65;font-weight:400;font-size:10.5px">${condParts.join(" · ")}</span>` : ""}
			</div>`).appendTo($c1.find(".dkst-card-body, .dkst-card").first());
			_showBuilder();
			frappe.show_alert({message:`Preset applied: ${pr.name}`, indicator:"green"}, 3);
		}

		/* ── Generate ── */
		const $t = term($builderWrap);
		btns($builderWrap,[{ lbl:"Generate Report", cls:"dkst-btn-p", fn:()=>{
			if(!gv("rp_app")||!gv("rp_mod")||!gv("rp_nm")||!gv("rp_dt")){frappe.throw("App, Module, Name and Ref DocType required");return;}
			const joins=[];
			$("#rp-jr tr").each(function(){
				const r={
					type:$(this).find(".f-jt").val()||"LEFT",
					table:$(this).find(".f-jtbl").val().trim(),
					alias:$(this).find(".f-ja").val().trim(),
					on:$(this).find(".f-jo").val().trim()
				};
				if(r.table&&r.on) joins.push(r);
			});
			const extra_where = $("#rp_where").val().trim();
			const order_by    = gv("rp_ord");
			const group_by    = gv("rp_grp");
			const having      = gv("rp_hav");
			const limit_rows  = parseInt($("#rp_lim").val())||0;
			api("frappe_devkit.api.report_builder.scaffold_report",{
				app_name:gv("rp_app"),module_name:gv("rp_mod"),report_name:gv("rp_nm"),
				report_type:gv("rp_ty"),ref_doctype:gv("rp_dt"),is_standard:gv("rp_st")||"Yes",
				add_total_row:gc("rp_tr")?1:0,overwrite:gc("rp_ow"),
				joins:JSON.stringify(joins),
				filters:JSON.stringify(_presetData.filters),
				columns:JSON.stringify(_presetData.columns),
				extra_where,order_by,group_by,having,limit_rows,
			},$t);
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
			<textarea id="cs_sc" style="display:none"></textarea>
			<div id="cs_sc_mc" style="height:260px;border:1px solid #d0c8e8;border-radius:4px"></div>
		</div>`);
		_mcLoad(mc => {
			const _csMc = _mcCreate($c.find('#cs_sc_mc'), 'javascript',
				'frappe.ui.form.on("MyDocType", {\n  setup(frm) {\n    // runs once on form init\n  },\n  refresh(frm) {\n    // runs on every load\n  },\n  validate(frm) {\n    // runs before save\n  }\n});');
			_csMc.onDidChangeModelContent(() => { $('#cs_sc').val(_csMc.getValue()); });
			$('#cs_sc').val(_csMc.getValue());
		});
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
			${DtSel("de_dt","DocType")}
			${F("de_ev","Event","select","","",[...DOC_EVENTS])}
			${DotPathHtml('de_h','my_app.overrides.sales_invoice.validate',{label:'Handler Path',required:true,appSel:'de_ap',dtSel:'de_dt',evSel:'de_ev',pattern:'{app}.overrides.{dt_snake}.{ev}'})}
		</div>`);
		wireAD($dec,"de_ap","de_dt");
		const $det=term($dec.closest(".dkst-spanel"));
		btns($dec.closest(".dkst-spanel"),[{ lbl:"Add Doc Event", cls:"dkst-btn-p", fn:()=>api("frappe_devkit.api.hook_builder.add_doc_event",{app_name:gv("de_ap"),doctype:gv("de_dt"),event:gv("de_ev"),handler_path:gv("de_h")},$det)}]);

		/* scheduler */
		const $scc=mkSub("sc");
		$scc.append(`<div class="dkst-g2">
			${AppSel("sc_ap")}
			${F("sc_fr","Frequency","select","","",[["daily","daily"],["hourly","hourly"],["weekly","weekly"],["monthly","monthly"],["all","all (every tick)"],["daily_long","daily_long"],["hourly_long","hourly_long"],["weekly_long","weekly_long"],["monthly_long","monthly_long"]])}
			${DotPathHtml('sc_h','my_app.tasks.daily_cleanup',{label:'Handler Path',required:true,appSel:'sc_ap',pattern:'{app}.tasks.daily_cleanup'})}
		</div>`);
		loadApps().then(()=>fillSel($scc.find("#sc_ap"),_apps,"select app"));
		const $sct=term($scc.closest(".dkst-spanel"));
		btns($scc.closest(".dkst-spanel"),[{ lbl:"Add Scheduler Event", cls:"dkst-btn-p", fn:()=>api("frappe_devkit.api.hook_builder.add_scheduler_event",{app_name:gv("sc_ap"),frequency:gv("sc_fr"),handler_path:gv("sc_h")},$sct)}]);

		/* fixture filter */
		const $ffc=mkSub("ff");
		$ffc.append(`<div class="dkst-g2">
			${AppSel("ff_ap")}
			${DtSel("ff_dt","DocType")}
			<div class="dkst-fld dkst-full"><label class="dkst-lbl dkst-req">Filters (JSON array)</label>
				<textarea class="dkst-ta" id="ff_fi" rows="4" style="font-family:'Consolas',monospace;font-size:12.5px">[["dt","in",["Sales Order","Sales Invoice"]],["fieldname","=","my_field"]]</textarea>
				<span class="dkst-hint">Format: [["fieldname","operator","value"],…]</span></div>
		</div>`);
		wireAD($ffc,"ff_ap","ff_dt");
		const $fft=term($ffc.closest(".dkst-spanel"));
		btns($ffc.closest(".dkst-spanel"),[{ lbl:"Add Fixture Filter", cls:"dkst-btn-p", fn:()=>api("frappe_devkit.api.hook_builder.add_fixture_filter",{app_name:gv("ff_ap"),dt:gv("ff_dt"),filters:gv("ff_fi")},$fft)}]);

		/* class override */
		const $coc=mkSub("co");
		$coc.append(`<div class="dkst-g2">
			${AppSel("co_ap")}
			${DtSel("co_dt","DocType")}
			${DotPathHtml('co_cl','my_app.overrides.sales_invoice.CustomSalesInvoice',{label:'Class Path',required:true,appSel:'co_ap',dtSel:'co_dt',pattern:'{app}.overrides.{dt_snake}.Custom{dt_pascal}'})}
		</div>
		<div class="dkst-hint" style="margin-top:6px">Class must extend the original — e.g. <span class="dkst-code">from erpnext.accounts.doctype.sales_invoice.sales_invoice import SalesInvoice</span></div>`);
		wireAD($coc,"co_ap","co_dt");
		const $cot=term($coc.closest(".dkst-spanel"));
		btns($coc.closest(".dkst-spanel"),[{ lbl:"Add Class Override", cls:"dkst-btn-p", fn:()=>api("frappe_devkit.api.hook_builder.add_override_doctype_class",{app_name:gv("co_ap"),doctype:gv("co_dt"),class_path:gv("co_cl")},$cot)}]);

		/* permission query */
		const $pqc=mkSub("pq");
		$pqc.append(`<div class="dkst-g2">
			${AppSel("pq_ap")}
			${DtSel("pq_dt","DocType")}
			${DotPathHtml('pq_h','my_app.permissions.get_permission_query_conditions',{label:'Handler Path',required:true,appSel:'pq_ap',dtSel:'pq_dt',pattern:'{app}.permissions.get_permission_query_for_{dt_snake}'})}
		</div>
		<div class="dkst-hint" style="margin-top:6px">Function must return a SQL WHERE condition string — return empty string for no restriction</div>`);
		wireAD($pqc,"pq_ap","pq_dt");
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
				${DotPathHtml('wm_orig','frappe.desk.doctype.event.event.get_events',{label:'Original Method (Frappe/ERPNext)',required:true,full:false})}
				${DotPathHtml('wm_new','my_app.utils.get_events',{label:'Your Override Method',required:true,full:false,appSel:'wm_ap',pattern:'{app}.utils.get_events'})}
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
			${DtSel("ov_dt","DocType Name")}
		</div>`);
		wireAD($c,"ov_ap","ov_dt");
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
		$p.append(`<div class="dkst-info-box" style="margin:10px 0 4px;font-size:11.5px;line-height:1.7;background:#f7f4ff;border:1px solid #e0d8f8;border-radius:6px;padding:12px 14px">
			<b style="color:#5c4da8">📋 How Patches Work</b><br>
			<ol style="margin:6px 0 0 16px;padding:0;color:#3a2e5e">
				<li>Fill in <b>App</b>, <b>Patch Module</b> (e.g. <code>v1_0.add_status_field</code>), and optionally an <b>Execute Body</b>.</li>
				<li>Click <b>Generate Patch</b> — creates <code>patches/v1_0/add_status_field.py</code> and registers it in <code>patches.txt</code>.</li>
				<li>Edit the generated file if needed, then run <code>bench migrate</code> — the patch executes exactly once and is never run again.</li>
			</ol>
			<div style="margin-top:8px;color:#7a70a8">
				<b>Rules:</b>
				&nbsp;✔ Always write <b>idempotent</b> logic (safe to re-run if migration is re-attempted) &nbsp;
				✔ Call <code>frappe.db.commit()</code> at the end (already included) &nbsp;
				✔ Use version prefixes: <code>v1_0</code>, <code>v14_0</code>, etc.
			</div>
		</div>`);
		const $c=card($p,"Patch Details");
		$c.append(`<div class="dkst-g2">
			${AppSel("pa_ap")}
			${DotPathHtml("pa_mo","v1_0.set_default_fabric_type",{label:"Patch Module (dot path)",required:true,full:false})}
			<div class="dkst-fld dkst-full" style="font-size:11px;color:#7a70a8;padding-top:2px">
				Sub-path within <code>patches/</code> — e.g. <code>v1_0.add_default_status</code> → creates <code>patches/v1_0/add_default_status.py</code>
			</div>
			<div class="dkst-fld dkst-full"><label class="dkst-lbl">Description</label>
				<input class="dkst-inp" id="pa_de" placeholder="What this patch does — appears as docstring in the generated file"></div>
		</div>`);
		loadApps().then(()=>fillSel($c.find("#pa_ap"),_apps,"select app"));
		$("#pa_bd_wrap").remove();
		$c.append(`<div class="dkst-div"></div><div id="pa_bd_wrap" class="dkst-fld">
			<label class="dkst-lbl">Execute Body <span style="font-weight:400;color:#999">(optional Python)</span></label>
			<div style="font-size:11px;color:#7a70a8;margin-bottom:6px;line-height:1.6">
				Write the body of the <code>execute()</code> function — <b>no indentation needed</b>, it will be auto-indented.<br>
				<span style="color:#888">• Use <code>frappe.db.sql()</code>, <code>frappe.get_all()</code>, <code>frappe.db.set_value()</code>, <code>frappe.reload_doc()</code> etc.</span><br>
				<span style="color:#888">• Always make logic <b>idempotent</b> (safe to re-run) — check before modifying.</span>
			</div>
			<textarea id="pa_bd" style="display:none"></textarea>
			<div id="pa_bd_mc" style="height:200px;border:1px solid #d0c8e8;border-radius:4px"></div>
		</div>`);
		_mcLoad(mc => {
			const _paMc = _mcCreate($c.find('#pa_bd_mc'), 'python', '');
			_paMc.onDidChangeModelContent(() => { $('#pa_bd').val(_paMc.getValue()); });
		});
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
		const DC_PRESETS = [
			// ── SALES ──
			{ id:"monthly_sales_rev", name:"Monthly Sales Revenue", ico:"📈", color:"#1d4ed8", tag:"Sales", tagBg:"#dbeafe", tagColor:"#1e40af",
			  desc:"Monthly sum of SI grand total — last 12 months.",
			  doctype:"Sales Invoice", chart_type:"Sum", based_on:"posting_date", value_based_on:"grand_total",
			  time_interval:"Monthly", timespan:"Last Year", visual:"Bar", color_hex:"#1d4ed8",
			  filters_json:'[["docstatus","=","1"]]' },

			{ id:"daily_order_count", name:"Daily Sales Count", ico:"📊", color:"#0369a1", tag:"Sales", tagBg:"#e0f2fe", tagColor:"#0c4a6e",
			  desc:"Daily count of sales invoices — last 30 days.",
			  doctype:"Sales Invoice", chart_type:"Count", based_on:"posting_date", value_based_on:"",
			  time_interval:"Daily", timespan:"Last Month", visual:"Bar", color_hex:"#0369a1",
			  filters_json:'[["docstatus","=","1"]]' },

			{ id:"sales_by_customer_grp", name:"Sales by Customer Group", ico:"🍩", color:"#7c3aed", tag:"Sales", tagBg:"#ede9fe", tagColor:"#5b21b6",
			  desc:"Count of sales invoices grouped by customer group.",
			  doctype:"Sales Invoice", chart_type:"Group By", based_on:"posting_date", value_based_on:"",
			  group_by_based_on:"customer_group", group_by_type:"Count",
			  time_interval:"Monthly", timespan:"Last Year", visual:"Donut", color_hex:"#7c3aed",
			  filters_json:'[["docstatus","=","1"]]' },

			{ id:"quarterly_revenue", name:"Quarterly Revenue Trend", ico:"📉", color:"#059669", tag:"Sales", tagBg:"#d1fae5", tagColor:"#064e3b",
			  desc:"Quarterly revenue trend over last 3 years.",
			  doctype:"Sales Invoice", chart_type:"Sum", based_on:"posting_date", value_based_on:"grand_total",
			  time_interval:"Quarterly", timespan:"Last 3 Years", visual:"Line", color_hex:"#059669",
			  filters_json:'[["docstatus","=","1"]]' },

			{ id:"sales_by_territory", name:"Sales by Territory", ico:"🗺️", color:"#0891b2", tag:"Sales", tagBg:"#cffafe", tagColor:"#155e75",
			  desc:"Sales invoice count by territory.",
			  doctype:"Sales Invoice", chart_type:"Group By", based_on:"posting_date", value_based_on:"",
			  group_by_based_on:"territory", group_by_type:"Count",
			  time_interval:"Monthly", timespan:"Last Year", visual:"Pie", color_hex:"#0891b2",
			  filters_json:'[["docstatus","=","1"]]' },

			// ── PURCHASE ──
			{ id:"monthly_purchase", name:"Monthly Purchase Cost", ico:"🛒", color:"#b45309", tag:"Purchase", tagBg:"#fef3c7", tagColor:"#92400e",
			  desc:"Monthly sum of purchase invoice totals.",
			  doctype:"Purchase Invoice", chart_type:"Sum", based_on:"posting_date", value_based_on:"grand_total",
			  time_interval:"Monthly", timespan:"Last Year", visual:"Bar", color_hex:"#b45309",
			  filters_json:'[["docstatus","=","1"]]' },

			{ id:"purchase_by_supplier", name:"Purchase by Supplier", ico:"🏭", color:"#b91c1c", tag:"Purchase", tagBg:"#fee2e2", tagColor:"#991b1b",
			  desc:"Invoice count grouped by supplier.",
			  doctype:"Purchase Invoice", chart_type:"Group By", based_on:"posting_date", value_based_on:"",
			  group_by_based_on:"supplier", group_by_type:"Count",
			  time_interval:"Monthly", timespan:"Last Year", visual:"Donut", color_hex:"#b91c1c",
			  filters_json:'[["docstatus","=","1"]]' },

			{ id:"po_trend", name:"PO Creation Trend", ico:"📋", color:"#92400e", tag:"Purchase", tagBg:"#fef3c7", tagColor:"#78350f",
			  desc:"Monthly purchase order creation count.",
			  doctype:"Purchase Order", chart_type:"Count", based_on:"transaction_date", value_based_on:"",
			  time_interval:"Monthly", timespan:"Last Year", visual:"Line", color_hex:"#92400e",
			  filters_json:'[]' },

			// ── INVENTORY ──
			{ id:"stock_movement_monthly", name:"Stock Movement", ico:"🔄", color:"#065f46", tag:"Inventory", tagBg:"#d1fae5", tagColor:"#064e3b",
			  desc:"Monthly stock ledger entry count.",
			  doctype:"Stock Ledger Entry", chart_type:"Count", based_on:"posting_date", value_based_on:"",
			  time_interval:"Monthly", timespan:"Last Year", visual:"Bar", color_hex:"#065f46",
			  filters_json:'[]' },

			{ id:"items_by_category", name:"Items by Category", ico:"📦", color:"#0369a1", tag:"Inventory", tagBg:"#e0f2fe", tagColor:"#0c4a6e",
			  desc:"Item count grouped by item group.",
			  doctype:"Item", chart_type:"Group By", based_on:"creation", value_based_on:"",
			  group_by_based_on:"item_group", group_by_type:"Count",
			  time_interval:"Monthly", timespan:"Last Year", visual:"Donut", color_hex:"#0369a1",
			  filters_json:'[["disabled","=","0"]]' },

			// ── HR ──
			{ id:"employees_by_dept", name:"Employees by Department", ico:"👥", color:"#1e3a5f", tag:"HR", tagBg:"#dbeafe", tagColor:"#1e40af",
			  desc:"Active employee count by department.",
			  doctype:"Employee", chart_type:"Group By", based_on:"date_of_joining", value_based_on:"",
			  group_by_based_on:"department", group_by_type:"Count",
			  time_interval:"Monthly", timespan:"Last Year", visual:"Bar", color_hex:"#1e3a5f",
			  filters_json:'[["status","=","Active"]]' },

			{ id:"monthly_attendance", name:"Monthly Attendance", ico:"🗓️", color:"#0369a1", tag:"HR", tagBg:"#e0f2fe", tagColor:"#0c4a6e",
			  desc:"Monthly attendance record count.",
			  doctype:"Attendance", chart_type:"Count", based_on:"attendance_date", value_based_on:"",
			  time_interval:"Monthly", timespan:"Last Year", visual:"Bar", color_hex:"#0369a1",
			  filters_json:'[["docstatus","=","1"]]' },

			{ id:"leave_trend", name:"Leave Applications Trend", ico:"🌴", color:"#15803d", tag:"HR", tagBg:"#dcfce7", tagColor:"#14532d",
			  desc:"Monthly leave application submissions.",
			  doctype:"Leave Application", chart_type:"Count", based_on:"from_date", value_based_on:"",
			  time_interval:"Monthly", timespan:"Last Year", visual:"Line", color_hex:"#15803d",
			  filters_json:'[["docstatus","=","1"]]' },

			{ id:"salary_trend", name:"Monthly Payroll Cost", ico:"💵", color:"#7c3aed", tag:"HR", tagBg:"#ede9fe", tagColor:"#5b21b6",
			  desc:"Sum of gross pay per month.",
			  doctype:"Salary Slip", chart_type:"Sum", based_on:"start_date", value_based_on:"gross_pay",
			  time_interval:"Monthly", timespan:"Last Year", visual:"Bar", color_hex:"#7c3aed",
			  filters_json:'[["docstatus","=","1"]]' },

			// ── ACCOUNTS ──
			{ id:"monthly_payments", name:"Monthly Payments", ico:"💳", color:"#065f46", tag:"Accounts", tagBg:"#d1fae5", tagColor:"#064e3b",
			  desc:"Monthly sum of payment entry paid amounts.",
			  doctype:"Payment Entry", chart_type:"Sum", based_on:"posting_date", value_based_on:"paid_amount",
			  time_interval:"Monthly", timespan:"Last Year", visual:"Bar", color_hex:"#065f46",
			  filters_json:'[["docstatus","=","1"]]' },

			{ id:"gl_by_account_type", name:"GL by Account Type", ico:"📒", color:"#1e3a5f", tag:"Accounts", tagBg:"#dbeafe", tagColor:"#1e40af",
			  desc:"GL entry count grouped by account type.",
			  doctype:"GL Entry", chart_type:"Group By", based_on:"posting_date", value_based_on:"",
			  group_by_based_on:"account_type", group_by_type:"Count",
			  time_interval:"Monthly", timespan:"Last Year", visual:"Donut", color_hex:"#1e3a5f",
			  filters_json:'[["is_cancelled","=","0"]]' },

			{ id:"receivable_trend", name:"Receivable Aging Trend", ico:"⏳", color:"#b45309", tag:"Accounts", tagBg:"#fef3c7", tagColor:"#92400e",
			  desc:"Monthly outstanding invoice count trend.",
			  doctype:"Sales Invoice", chart_type:"Count", based_on:"due_date", value_based_on:"",
			  time_interval:"Monthly", timespan:"Last Year", visual:"Line", color_hex:"#b45309",
			  filters_json:'[["docstatus","=","1"],["outstanding_amount",">","0"]]' },

			// ── CRM ──
			{ id:"leads_by_source", name:"Leads by Source", ico:"🎯", color:"#be185d", tag:"CRM", tagBg:"#fce7f3", tagColor:"#9d174d",
			  desc:"Lead count grouped by lead source.",
			  doctype:"Lead", chart_type:"Group By", based_on:"creation", value_based_on:"",
			  group_by_based_on:"source", group_by_type:"Count",
			  time_interval:"Monthly", timespan:"Last Year", visual:"Pie", color_hex:"#be185d",
			  filters_json:'[]' },

			{ id:"opportunity_pipeline", name:"Opportunity Pipeline", ico:"🚀", color:"#7c3aed", tag:"CRM", tagBg:"#ede9fe", tagColor:"#5b21b6",
			  desc:"Open opportunities by sales stage.",
			  doctype:"Opportunity", chart_type:"Group By", based_on:"creation", value_based_on:"",
			  group_by_based_on:"sales_stage", group_by_type:"Count",
			  time_interval:"Monthly", timespan:"Last Year", visual:"Bar", color_hex:"#7c3aed",
			  filters_json:'[["status","=","Open"]]' },

			// ── SUPPORT ──
			{ id:"issues_by_priority", name:"Issues by Priority", ico:"🎫", color:"#dc2626", tag:"Support", tagBg:"#fee2e2", tagColor:"#991b1b",
			  desc:"Open issue count grouped by priority.",
			  doctype:"Issue", chart_type:"Group By", based_on:"opening_date", value_based_on:"",
			  group_by_based_on:"priority", group_by_type:"Count",
			  time_interval:"Monthly", timespan:"Last Year", visual:"Donut", color_hex:"#dc2626",
			  filters_json:'[["status","!=","Closed"]]' },

			{ id:"issues_resolved_monthly", name:"Monthly Resolved Issues", ico:"✅", color:"#059669", tag:"Support", tagBg:"#d1fae5", tagColor:"#064e3b",
			  desc:"Monthly count of resolved/closed issues.",
			  doctype:"Issue", chart_type:"Count", based_on:"resolution_date", value_based_on:"",
			  time_interval:"Monthly", timespan:"Last Year", visual:"Line", color_hex:"#059669",
			  filters_json:'[["status","in","Resolved,Closed"]]' },

			// ── MANUFACTURING ──
			{ id:"work_orders_by_status", name:"Work Orders by Status", ico:"⚙️", color:"#374151", tag:"Mfg", tagBg:"#f3f4f6", tagColor:"#111827",
			  desc:"Work order count grouped by status.",
			  doctype:"Work Order", chart_type:"Group By", based_on:"planned_start_date", value_based_on:"",
			  group_by_based_on:"status", group_by_type:"Count",
			  time_interval:"Monthly", timespan:"Last Year", visual:"Bar", color_hex:"#374151",
			  filters_json:'[]' },

			{ id:"monthly_production", name:"Monthly Production Orders", ico:"🏭", color:"#4b5563", tag:"Mfg", tagBg:"#f3f4f6", tagColor:"#1f2937",
			  desc:"Monthly work order creation trend.",
			  doctype:"Work Order", chart_type:"Count", based_on:"planned_start_date", value_based_on:"",
			  time_interval:"Monthly", timespan:"Last Year", visual:"Bar", color_hex:"#4b5563",
			  filters_json:'[]' },

			// ── PROJECTS ──
			{ id:"tasks_by_status", name:"Tasks by Status", ico:"✏️", color:"#0891b2", tag:"Projects", tagBg:"#cffafe", tagColor:"#155e75",
			  desc:"Task count grouped by status.",
			  doctype:"Task", chart_type:"Group By", based_on:"creation", value_based_on:"",
			  group_by_based_on:"status", group_by_type:"Count",
			  time_interval:"Monthly", timespan:"Last Year", visual:"Donut", color_hex:"#0891b2",
			  filters_json:'[]' },

			{ id:"project_task_trend", name:"Project Task Trend", ico:"📅", color:"#0369a1", tag:"Projects", tagBg:"#e0f2fe", tagColor:"#0c4a6e",
			  desc:"Monthly task creation trend across projects.",
			  doctype:"Task", chart_type:"Count", based_on:"creation", value_based_on:"",
			  time_interval:"Monthly", timespan:"Last Year", visual:"Line", color_hex:"#0369a1",
			  filters_json:'[]' },
		];

		/* ── Visual type icons ── */
		const VIS_ICO = { Bar:"▬", Line:"📈", Pie:"🥧", Donut:"🍩", Percentage:"📊", Heatmap:"🌡️", Scatter:"✦" };

		let _dcSelected = new Set();

		$p.append(phdr("Dashboard Chart","Scaffold Dashboard Chart fixtures for Frappe Desk dashboards — pick presets or configure manually.",icoChart(20)));

		/* ── App / Module ── */
		const $cam = card($p, "App & Module");
		$cam.append(`<div class="dkst-g2">${AppSel("dc_ap")} ${ModSel("dc_mo")}</div>`);
		wireAMD($p, "dc_ap", "dc_mo", "dc_dt");

		/* ── Preset Selector ── */
		const $cp = card($p, "Dashboard Chart Presets");
		$cp.append(info("Click to select • hold Shift to multi-select • click again to deselect. Apply auto-fills the form below for individual customisation."));

		const $psw = $(`<div class="dkrb-preset-search-wrap">
			<input id="dc-search" class="dkrb-preset-search" type="text" placeholder="Search charts by name, module or keyword…">
			<span class="dkrb-preset-count" id="dc-pcount"></span>
		</div>`).appendTo($cp);

		const $pg = $(`<div class="dkrb-preset-grid"></div>`).appendTo($cp);
		DC_PRESETS.forEach(pr => {
			$(`<div class="dkrb-preset-card" data-pid="${pr.id}" style="cursor:pointer">
				<div class="dkrb-preset-top" style="background:${pr.color}">
					<span class="dkwc-chart-type-badge">${pr.visual} ${VIS_ICO[pr.visual]||""}</span>
				</div>
				<div class="dkrb-preset-body">
					<div class="dkrb-preset-ico">${pr.ico}</div>
					<div class="dkrb-preset-nm">${pr.name}</div>
					<div class="dkrb-preset-ds">${pr.desc}</div>
					<div class="dkrb-preset-tag" style="background:${pr.tagBg};color:${pr.tagColor}">${pr.tag}</div>
				</div>
			</div>`).appendTo($pg).on("click", function() {
				const pid = $(this).data("pid");
				if (_dcSelected.has(pid)) { _dcSelected.delete(pid); $(this).removeClass("selected"); }
				else { _dcSelected.add(pid); $(this).addClass("selected"); }
				_dcUpdateBar();
				// Also apply to form
				const pr2 = DC_PRESETS.find(p => p.id === pid);
				if (pr2 && _dcSelected.has(pid)) _dcApply(pr2);
			});
		});

		/* ── Selection action bar ── */
		const $bar = $(`<div class="dkwc-action-bar" style="display:none">
			<span class="dkwc-sel-count">Selected</span>
			<span class="dkwc-badge" id="dc-sel-n">0</span>
			<button class="dkwc-scaffold-btn" id="dc-batch-btn" disabled>⚡ Scaffold All Selected</button>
			<button class="dkwc-desel" id="dc-desel-btn">✕ Clear</button>
		</div>`).appendTo($cp);

		function _dcUpdateBar() {
			const n = _dcSelected.size;
			$("#dc-sel-n").text(n);
			$bar.toggle(n > 0);
			$("#dc-batch-btn").prop("disabled", n === 0);
		}

		function _dcApply(pr) {
			$dcCustomWrap.show();
			$("#dc_nm").val(pr.name);
			$("#dc_ty").val(pr.chart_type);
			$("#dc_dt").trigger && ($("#dc_dt").val(pr.doctype));
			$("#dc_bo").val(pr.based_on || "");
			$("#dc_vl").val(pr.value_based_on || "");
			$("#dc_gb").val(pr.group_by_based_on || "");
			$("#dc_gbt").val(pr.group_by_type || "Count");
			$("#dc_ti").val(pr.time_interval || "Monthly");
			$("#dc_ts").val(pr.timespan || "Last Year");
			$("#dc_vty").val(pr.visual || "Bar");
			$("#dc_cl").val(pr.color_hex || "#7c5cbf");
			$("#dc_fi").val(pr.filters_json || "[]");
		}

		/* ── Search ── */
		const _dcUpdateCount = () => {
			const total = DC_PRESETS.length, vis = $pg.find(".dkrb-preset-card:not(.dkrb-hidden)").length;
			$("#dc-pcount").text(vis === total ? `${total} presets` : `${vis} of ${total}`);
		};
		_dcUpdateCount();
		$("#dc-search").on("input", function() {
			const q = $(this).val().trim().toLowerCase();
			$pg.find(".dkrb-preset-card").each(function() {
				const pr = DC_PRESETS.find(p => p.id === $(this).data("pid"));
				if (!pr) return;
				const match = !q || pr.name.toLowerCase().includes(q) || pr.tag.toLowerCase().includes(q) || pr.desc.toLowerCase().includes(q) || (pr.doctype||"").toLowerCase().includes(q);
				$(this).toggleClass("dkrb-hidden", !match);
			});
			_dcUpdateCount();
		});
		$("#dc-desel-btn").on("click", () => {
			_dcSelected.clear(); $pg.find(".dkrb-preset-card").removeClass("selected"); _dcUpdateBar();
		});

		/* ── Batch scaffold ── */
		$("#dc-batch-btn").on("click", function() {
			const app = $("#dc_ap").val();
			if (!app) { frappe.throw("Select an App first"); return; }
			const charts = DC_PRESETS.filter(p => _dcSelected.has(p.id)).map(p => ({
				chart_name: p.name, chart_type: p.chart_type, doctype: p.doctype,
				based_on: p.based_on||"", value_based_on: p.value_based_on||"",
				group_by_based_on: p.group_by_based_on||"", group_by_type: p.group_by_type||"Count",
				time_interval: p.time_interval||"Monthly", timespan: p.timespan||"Last Year",
				visual_type: p.visual||"Bar", color: p.color_hex||"#7c5cbf",
				filters_json: p.filters_json||"[]",
			}));
			api("frappe_devkit.api.advanced_builder.scaffold_dashboard_charts_batch",
				{ app_name: app, module_name: $("#dc_mo").val()||"", charts_json: JSON.stringify(charts) }, $t);
		});

		/* ── Customise / Single card form ── */
		$cp.append(`<div style="margin-top:8px;text-align:right"><a href="#" id="dc-custom-skip" style="font-size:12px;color:#5c4da8;text-decoration:underline">Add custom chart ›</a></div>`);
		$p.on('click','#dc-custom-skip',function(e){e.preventDefault();$dcCustomWrap.show();});
		const $dcCustomWrap = $('<div style="display:none"></div>').appendTo($p);
		const $cc = card($dcCustomWrap, "Customise & Add Single Chart");
		$cc.append(`<div class="dkst-g2">
			${FR("dc_nm","Chart Name","text","Monthly Sales")}
			${F("dc_ty","Chart Type","select","","",[["Count","Count"],["Sum","Sum"],["Average","Average"],["Group By","Group By"]])}
			${DtSel("dc_dt","DocType")}
			${F("dc_bo","Based On (date field)","text","posting_date")}
			${F("dc_vl","Value Field (Sum / Avg)","text","grand_total")}
			${F("dc_gb","Group By Field","text","customer_group")}
			${F("dc_gbt","Group By Function","select","","",[["Count","Count"],["Sum","Sum"],["Average","Average"]])}
			${F("dc_ti","Time Interval","select","","",[["Daily","Daily"],["Weekly","Weekly"],["Monthly","Monthly"],["Quarterly","Quarterly"],["Yearly","Yearly"]])}
			${F("dc_ts","Timespan","select","","",[["Last Week","Last Week"],["Last Month","Last Month"],["Last Quarter","Last Quarter"],["Last Year","Last Year"],["Last 3 Years","Last 3 Years"]])}
			${F("dc_vty","Visual Type","select","","",[["Bar","Bar"],["Line","Line"],["Pie","Pie"],["Donut","Donut"],["Percentage","Percentage"],["Heatmap","Heatmap"],["Scatter","Scatter"]])}
			<div class="dkst-fld"><label class="dkst-lbl">Color</label>
				<input type="color" id="dc_cl" value="#7c5cbf" style="width:60px;height:36px;border:1px solid #d0c8e8;border-radius:5px;cursor:pointer;"></div>
			<div class="dkst-fld"><label class="dkst-lbl">Filters JSON</label>
				<textarea class="dkst-ta" id="dc_fi" rows="2" style="font-family:monospace;font-size:12px">[]</textarea></div>
		</div>`);
		// doctype wired via wireAMD($p, ...) above

		const $t = term($dcCustomWrap);
		btns($dcCustomWrap,[{ lbl:"Add This Chart", cls:"dkst-btn-p", fn:()=>{
			if(!$("#dc_ap").val()||!$("#dc_nm").val()||!$("#dc_dt").val()){frappe.throw("App, Name and DocType required");return;}
			api("frappe_devkit.api.advanced_builder.scaffold_dashboard_chart",{
				app_name:$("#dc_ap").val(), module_name:$("#dc_mo").val()||"",
				chart_name:$("#dc_nm").val(), chart_type:$("#dc_ty").val(),
				doctype:$("#dc_dt").val(), based_on:$("#dc_bo").val(),
				value_based_on:$("#dc_vl").val(), group_by_based_on:$("#dc_gb").val(),
				group_by_type:$("#dc_gbt").val(), time_interval:$("#dc_ti").val(),
				timespan:$("#dc_ts").val(), visual_type:$("#dc_vty").val(),
				color:$('#dc_cl').val(), filters_json:$("#dc_fi").val()||"[]",
			},$t);
		}}]);
	};

	/* ── Number Card ── */
	PANELS.number_card = function($p) {
		const NC_PRESETS = [
			// ── SALES ──
			{ id:"sales_today", name:"Sales Today", ico:"💰", color:"#1d4ed8", tag:"Sales", tagBg:"#dbeafe", tagColor:"#1e40af",
			  desc:"Sum of submitted sales invoices posted today.",
			  doctype:"Sales Invoice", func:"Sum", agg_field:"grand_total",
			  filters_json:'[["docstatus","=","1"],["posting_date","=","Today"]]', color_hex:"#1d4ed8" },

			{ id:"open_sales_orders", name:"Open Sales Orders", ico:"📑", color:"#0369a1", tag:"Sales", tagBg:"#e0f2fe", tagColor:"#0c4a6e",
			  desc:"Count of sales orders that are open.",
			  doctype:"Sales Order", func:"Count", agg_field:"",
			  filters_json:'[["status","in","Draft,To Deliver and Bill,To Deliver,To Bill"]]', color_hex:"#0369a1" },

			{ id:"monthly_revenue", name:"Monthly Revenue", ico:"📊", color:"#7c3aed", tag:"Sales", tagBg:"#ede9fe", tagColor:"#5b21b6",
			  desc:"Sum of sales invoices this calendar month.",
			  doctype:"Sales Invoice", func:"Sum", agg_field:"grand_total",
			  filters_json:'[["docstatus","=","1"],["posting_date",">=","01-01-2024"]]', color_hex:"#7c3aed" },

			{ id:"unpaid_invoices", name:"Unpaid Invoices", ico:"⚠️", color:"#dc2626", tag:"Sales", tagBg:"#fee2e2", tagColor:"#991b1b",
			  desc:"Count of submitted invoices with outstanding amount.",
			  doctype:"Sales Invoice", func:"Count", agg_field:"",
			  filters_json:'[["docstatus","=","1"],["outstanding_amount",">","0"]]', color_hex:"#dc2626" },

			{ id:"total_receivable", name:"Total Receivable", ico:"💳", color:"#b45309", tag:"Accounts", tagBg:"#fef3c7", tagColor:"#92400e",
			  desc:"Sum of outstanding amounts on submitted sales invoices.",
			  doctype:"Sales Invoice", func:"Sum", agg_field:"outstanding_amount",
			  filters_json:'[["docstatus","=","1"],["outstanding_amount",">","0"]]', color_hex:"#b45309" },

			// ── PURCHASE ──
			{ id:"pending_pos", name:"Pending PO Receipt", ico:"📦", color:"#92400e", tag:"Purchase", tagBg:"#fef3c7", tagColor:"#78350f",
			  desc:"Purchase orders awaiting goods receipt.",
			  doctype:"Purchase Order", func:"Count", agg_field:"",
			  filters_json:'[["status","in","To Receive and Bill,To Receive"]]', color_hex:"#92400e" },

			{ id:"purchase_this_month", name:"Purchase This Month", ico:"🛒", color:"#b91c1c", tag:"Purchase", tagBg:"#fee2e2", tagColor:"#991b1b",
			  desc:"Sum of purchase invoices this month.",
			  doctype:"Purchase Invoice", func:"Sum", agg_field:"grand_total",
			  filters_json:'[["docstatus","=","1"]]', color_hex:"#b91c1c" },

			{ id:"total_payable", name:"Total Payable", ico:"🏦", color:"#7c3aed", tag:"Accounts", tagBg:"#ede9fe", tagColor:"#5b21b6",
			  desc:"Sum of outstanding amounts on purchase invoices.",
			  doctype:"Purchase Invoice", func:"Sum", agg_field:"outstanding_amount",
			  filters_json:'[["docstatus","=","1"],["outstanding_amount",">","0"]]', color_hex:"#7c3aed" },

			{ id:"overdue_bills", name:"Overdue Bills", ico:"🔴", color:"#dc2626", tag:"Purchase", tagBg:"#fee2e2", tagColor:"#991b1b",
			  desc:"Purchase invoices past due date with outstanding amount.",
			  doctype:"Purchase Invoice", func:"Count", agg_field:"",
			  filters_json:'[["docstatus","=","1"],["outstanding_amount",">","0"],["due_date","<","Today"]]', color_hex:"#dc2626" },

			// ── INVENTORY ──
			{ id:"total_items", name:"Total Active Items", ico:"📦", color:"#065f46", tag:"Inventory", tagBg:"#d1fae5", tagColor:"#064e3b",
			  desc:"Count of all active, non-disabled items.",
			  doctype:"Item", func:"Count", agg_field:"",
			  filters_json:'[["disabled","=","0"]]', color_hex:"#065f46" },

			{ id:"low_stock_items", name:"Low / Zero Stock Items", ico:"⚠️", color:"#b45309", tag:"Inventory", tagBg:"#fef3c7", tagColor:"#92400e",
			  desc:"Items where actual quantity is at or below reorder level.",
			  doctype:"Bin", func:"Count", agg_field:"",
			  filters_json:'[["actual_qty","<=","reorder_level"]]', color_hex:"#b45309" },

			{ id:"negative_stock", name:"Negative Stock Items", ico:"📉", color:"#dc2626", tag:"Inventory", tagBg:"#fee2e2", tagColor:"#991b1b",
			  desc:"Warehouse bins with negative actual quantity.",
			  doctype:"Bin", func:"Count", agg_field:"",
			  filters_json:'[["actual_qty","<","0"]]', color_hex:"#dc2626" },

			// ── HR ──
			{ id:"active_employees", name:"Active Employees", ico:"👥", color:"#1e3a5f", tag:"HR", tagBg:"#dbeafe", tagColor:"#1e40af",
			  desc:"Count of employees with Active status.",
			  doctype:"Employee", func:"Count", agg_field:"",
			  filters_json:'[["status","=","Active"]]', color_hex:"#1e3a5f" },

			{ id:"open_leave_requests", name:"Open Leave Requests", ico:"🌴", color:"#15803d", tag:"HR", tagBg:"#dcfce7", tagColor:"#14532d",
			  desc:"Leave applications awaiting approval.",
			  doctype:"Leave Application", func:"Count", agg_field:"",
			  filters_json:'[["status","=","Open"],["docstatus","=","1"]]', color_hex:"#15803d" },

			{ id:"pending_expense_claims", name:"Pending Expense Claims", ico:"🧾", color:"#0369a1", tag:"HR", tagBg:"#e0f2fe", tagColor:"#0c4a6e",
			  desc:"Expense claims submitted but not approved.",
			  doctype:"Expense Claim", func:"Count", agg_field:"",
			  filters_json:'[["status","=","Submitted"],["docstatus","=","1"]]', color_hex:"#0369a1" },

			{ id:"total_payroll", name:"Total Monthly Payroll", ico:"💵", color:"#7c3aed", tag:"HR", tagBg:"#ede9fe", tagColor:"#5b21b6",
			  desc:"Sum of gross pay on submitted salary slips this month.",
			  doctype:"Salary Slip", func:"Sum", agg_field:"gross_pay",
			  filters_json:'[["docstatus","=","1"]]', color_hex:"#7c3aed" },

			// ── PROJECTS ──
			{ id:"open_tasks", name:"Open Tasks", ico:"✏️", color:"#0891b2", tag:"Projects", tagBg:"#cffafe", tagColor:"#155e75",
			  desc:"Count of open/in-progress project tasks.",
			  doctype:"Task", func:"Count", agg_field:"",
			  filters_json:'[["status","in","Open,Working,Pending Review"]]', color_hex:"#0891b2" },

			{ id:"overdue_tasks", name:"Overdue Tasks", ico:"🔔", color:"#dc2626", tag:"Projects", tagBg:"#fee2e2", tagColor:"#991b1b",
			  desc:"Tasks past their expected end date.",
			  doctype:"Task", func:"Count", agg_field:"",
			  filters_json:'[["status","!=","Completed"],["exp_end_date","<","Today"]]', color_hex:"#dc2626" },

			{ id:"active_projects", name:"Active Projects", ico:"🗂️", color:"#1e3a5f", tag:"Projects", tagBg:"#dbeafe", tagColor:"#1e40af",
			  desc:"Count of currently open projects.",
			  doctype:"Project", func:"Count", agg_field:"",
			  filters_json:'[["status","=","Open"]]', color_hex:"#1e3a5f" },

			// ── SUPPORT ──
			{ id:"open_issues", name:"Open Issues", ico:"🎫", color:"#dc2626", tag:"Support", tagBg:"#fee2e2", tagColor:"#991b1b",
			  desc:"Count of open support issues.",
			  doctype:"Issue", func:"Count", agg_field:"",
			  filters_json:'[["status","in","Open,Replied,Hold"]]', color_hex:"#dc2626" },

			{ id:"high_priority_issues", name:"High Priority Issues", ico:"🔥", color:"#b91c1c", tag:"Support", tagBg:"#fee2e2", tagColor:"#7f1d1d",
			  desc:"High or Urgent priority open issues.",
			  doctype:"Issue", func:"Count", agg_field:"",
			  filters_json:'[["priority","in","High,Urgent"],["status","!=","Closed"]]', color_hex:"#b91c1c" },

			{ id:"sla_breached", name:"SLA Breached Issues", ico:"💥", color:"#7c3aed", tag:"Support", tagBg:"#ede9fe", tagColor:"#5b21b6",
			  desc:"Issues where SLA agreement status is Failed.",
			  doctype:"Issue", func:"Count", agg_field:"",
			  filters_json:'[["agreement_status","=","Failed"]]', color_hex:"#7c3aed" },

			// ── MANUFACTURING ──
			{ id:"work_orders_in_progress", name:"Work Orders In Progress", ico:"⚙️", color:"#374151", tag:"Mfg", tagBg:"#f3f4f6", tagColor:"#111827",
			  desc:"Work orders currently being manufactured.",
			  doctype:"Work Order", func:"Count", agg_field:"",
			  filters_json:'[["status","=","In Process"]]', color_hex:"#374151" },

			{ id:"pending_job_cards", name:"Pending Job Cards", ico:"🗒️", color:"#4b5563", tag:"Mfg", tagBg:"#f3f4f6", tagColor:"#1f2937",
			  desc:"Open job cards awaiting work.",
			  doctype:"Job Card", func:"Count", agg_field:"",
			  filters_json:'[["status","=","Open"]]', color_hex:"#4b5563" },

			// ── CRM ──
			{ id:"new_leads_month", name:"New Leads This Month", ico:"🎯", color:"#be185d", tag:"CRM", tagBg:"#fce7f3", tagColor:"#9d174d",
			  desc:"Leads created in the current month.",
			  doctype:"Lead", func:"Count", agg_field:"",
			  filters_json:'[]', color_hex:"#be185d" },

			{ id:"open_opportunities", name:"Open Opportunities", ico:"🚀", color:"#7c3aed", tag:"CRM", tagBg:"#ede9fe", tagColor:"#5b21b6",
			  desc:"Open opportunities in the CRM pipeline.",
			  doctype:"Opportunity", func:"Count", agg_field:"",
			  filters_json:'[["status","=","Open"]]', color_hex:"#7c3aed" },

			// ── ASSETS ──
			{ id:"active_assets", name:"Active Assets", ico:"🏗️", color:"#374151", tag:"Assets", tagBg:"#f3f4f6", tagColor:"#111827",
			  desc:"Submitted, active fixed assets.",
			  doctype:"Asset", func:"Count", agg_field:"",
			  filters_json:'[["docstatus","=","1"],["status","in","Submitted,Partially Depreciated"]]', color_hex:"#374151" },

			{ id:"fully_depreciated", name:"Fully Depreciated Assets", ico:"📦", color:"#6b7280", tag:"Assets", tagBg:"#f3f4f6", tagColor:"#374151",
			  desc:"Assets that have been fully depreciated.",
			  doctype:"Asset", func:"Count", agg_field:"",
			  filters_json:'[["status","=","Fully Depreciated"]]', color_hex:"#6b7280" },

			// ── ACCOUNTS ──
			{ id:"journal_entries_today", name:"Journal Entries Today", ico:"📒", color:"#1e3a5f", tag:"Accounts", tagBg:"#dbeafe", tagColor:"#1e40af",
			  desc:"Journal entries posted today.",
			  doctype:"Journal Entry", func:"Count", agg_field:"",
			  filters_json:'[["docstatus","=","1"],["posting_date","=","Today"]]', color_hex:"#1e3a5f" },
		];

		let _ncSelected = new Set();

		$p.append(phdr("Number Card","Scaffold Number Card fixtures — pick presets or configure a custom card.",icoHash(20)));

		/* ── App / Module ── */
		const $cam = card($p, "App & Module");
		$cam.append(`<div class="dkst-g2">${AppSel("nc_ap")} ${ModSel("nc_mo")}</div>`);
		wireAMD($p, "nc_ap", "nc_mo", "nc_dt");

		/* ── Preset Selector ── */
		const $cp = card($p, "Number Card Presets");
		$cp.append(info("Click cards to select • click again to deselect. Use Scaffold All Selected to create multiple cards at once."));

		$cp.append(`<div class="dkrb-preset-search-wrap">
			<input id="nc-search" class="dkrb-preset-search" type="text" placeholder="Search cards by name, module or keyword…">
			<span class="dkrb-preset-count" id="nc-pcount"></span>
		</div>`);
		const $pg = $(`<div class="dkrb-preset-grid"></div>`).appendTo($cp);

		NC_PRESETS.forEach(pr => {
			const funcBadge = `<span class="dkwc-chart-type-badge">${pr.func}</span>`;
			$(`<div class="dkrb-preset-card" data-pid="${pr.id}">
				<div class="dkrb-preset-top" style="background:${pr.color}">${funcBadge}</div>
				<div class="dkrb-preset-body">
					<div class="dkrb-preset-ico">${pr.ico}</div>
					<div class="dkrb-preset-nm">${pr.name}</div>
					<div class="dkrb-preset-ds">${pr.desc}</div>
					<div class="dkrb-preset-tag" style="background:${pr.tagBg};color:${pr.tagColor}">${pr.tag}</div>
				</div>
			</div>`).appendTo($pg).on("click", function() {
				const pid = $(this).data("pid");
				if (_ncSelected.has(pid)) { _ncSelected.delete(pid); $(this).removeClass("selected"); }
				else { _ncSelected.add(pid); $(this).addClass("selected"); }
				_ncUpdateBar();
				const pr2 = NC_PRESETS.find(p => p.id === pid);
				if (pr2 && _ncSelected.has(pid)) _ncApply(pr2);
			});
		});

		/* ── Selection bar ── */
		const $bar = $(`<div class="dkwc-action-bar" style="display:none">
			<span class="dkwc-sel-count">Selected</span>
			<span class="dkwc-badge" id="nc-sel-n">0</span>
			<button class="dkwc-scaffold-btn" id="nc-batch-btn" disabled>⚡ Scaffold All Selected</button>
			<button class="dkwc-desel" id="nc-desel-btn">✕ Clear</button>
		</div>`).appendTo($cp);

		function _ncUpdateBar() {
			const n = _ncSelected.size;
			$("#nc-sel-n").text(n);
			$bar.toggle(n > 0);
			$("#nc-batch-btn").prop("disabled", n === 0);
		}

		function _ncApply(pr) {
			$ncCustomWrap.show();
			$("#nc_nm").val(pr.name);
			$("#nc_dt").val(pr.doctype);
			$("#nc_fn").val(pr.func);
			$("#nc_af").val(pr.agg_field || "");
			$("#nc_fi").val(pr.filters_json || "[]");
			$("#nc_cl").val(pr.color_hex || "#5c4da8");
		}

		/* ── Search ── */
		const _ncUpdateCount = () => {
			const total = NC_PRESETS.length, vis = $pg.find(".dkrb-preset-card:not(.dkrb-hidden)").length;
			$("#nc-pcount").text(vis === total ? `${total} presets` : `${vis} of ${total}`);
		};
		_ncUpdateCount();
		$("#nc-search").on("input", function() {
			const q = $(this).val().trim().toLowerCase();
			$pg.find(".dkrb-preset-card").each(function() {
				const pr = NC_PRESETS.find(p => p.id === $(this).data("pid"));
				if (!pr) return;
				const match = !q || pr.name.toLowerCase().includes(q) || pr.tag.toLowerCase().includes(q) || pr.desc.toLowerCase().includes(q) || (pr.doctype||"").toLowerCase().includes(q);
				$(this).toggleClass("dkrb-hidden", !match);
			});
			_ncUpdateCount();
		});
		$("#nc-desel-btn").on("click", () => {
			_ncSelected.clear(); $pg.find(".dkrb-preset-card").removeClass("selected"); _ncUpdateBar();
		});

		/* ── Batch scaffold ── */
		$("#nc-batch-btn").on("click", function() {
			const app = $("#nc_ap").val();
			if (!app) { frappe.throw("Select an App first"); return; }
			const cards = NC_PRESETS.filter(p => _ncSelected.has(p.id)).map(p => ({
				card_name: p.name, doctype: p.doctype, function: p.func,
				aggregate_function_based_on: p.agg_field||"",
				filters_json: p.filters_json||"[]", color: p.color_hex||"#5c4da8",
			}));
			api("frappe_devkit.api.advanced_builder.scaffold_number_cards_batch",
				{ app_name: app, module_name: $("#nc_mo").val()||"", cards_json: JSON.stringify(cards) }, $t);
		});

		/* ── Customise / single card form ── */
		$cp.append(`<div style="margin-top:8px;text-align:right"><a href="#" id="nc-custom-skip" style="font-size:12px;color:#5c4da8;text-decoration:underline">Add custom card ›</a></div>`);
		const $ncCustomWrap = $('<div style="display:none"></div>').appendTo($p);
		$p.on('click','#nc-custom-skip',function(e){e.preventDefault();$ncCustomWrap.show();});
		const $cc = card($ncCustomWrap, "Customise & Add Single Card");
		$cc.append(`<div class="dkst-g2">
			${FR("nc_nm","Card Name","text","Total Open Orders")}
			${DtSel("nc_dt","DocType")}
			${F("nc_fn","Function","select","","",[["Count","Count"],["Sum","Sum"],["Average","Average"],["Minimum","Minimum"],["Maximum","Maximum"]])}
			${F("nc_af","Aggregate Field (Sum / Avg / Min / Max)","text","grand_total")}
			${F("nc_si","Stats Time Interval","select","","",[["Daily","Daily"],["Weekly","Weekly"],["Monthly","Monthly"]])}
			<div class="dkst-fld"><label class="dkst-lbl">Color</label>
				<input type="color" id="nc_cl" value="#5c4da8" style="width:60px;height:36px;border:1px solid #d0c8e8;border-radius:5px;cursor:pointer;"></div>
			<div class="dkst-fld"><label class="dkst-lbl">Filters JSON</label>
				<textarea class="dkst-ta" id="nc_fi" rows="2" style="font-family:monospace;font-size:12px">[["status","=","Open"]]</textarea></div>
		</div>`);
		// doctype wired via wireAMD($p, ...) above

		const $t = term($ncCustomWrap);
		btns($ncCustomWrap,[{ lbl:"Add This Card", cls:"dkst-btn-p", fn:()=>{
			if(!$("#nc_ap").val()||!$("#nc_nm").val()||!$("#nc_dt").val()){frappe.throw("App, Name and DocType required");return;}
			api("frappe_devkit.api.advanced_builder.scaffold_number_card",{
				app_name:$("#nc_ap").val(), module_name:$("#nc_mo").val()||"",
				card_name:$("#nc_nm").val(), doctype:$("#nc_dt").val(),
				function:$("#nc_fn").val(), aggregate_function_based_on:$("#nc_af").val(),
				stats_time_interval:$("#nc_si").val()||"Monthly",
				filters_json:$("#nc_fi").val()||"[]", color:$('#nc_cl').val(),
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
			${DtSel("nt_dt","DocType")}
			${F("nt_ev","Event","select","","",[["New","New"],["Save","Save"],["Submit","Submit"],["Cancel","Cancel"],["Days After","Days After"],["Days Before","Days Before"],["Value Change","Value Change"],["Custom","Custom"]])}
			${F("nt_cd","Condition (Python)","text","doc.grand_total > 100000")}
		</div>`);
		wireAD($c1,"nt_ap","nt_dt");

		const $c2=card($p,"Email Content");
		$c2.append(`<div class="dkst-fld" style="margin-bottom:12px"><label class="dkst-lbl">Subject</label>
			<input class="dkst-inp" id="nt_su" placeholder="[{{ doc.doctype }}] {{ doc.name }} has been submitted"></div>`);
		$c2.append(`<div class="dkst-fld"><label class="dkst-lbl">Message (HTML / Jinja2)</label></div>`);
		makeHtmlEditor($c2,'nt_ms',`<h3>{{ doc.name }}</h3>\n<p>Document has been {{ doc.docstatus == 1 and 'submitted' or 'saved' }}.</p>\n<table border="1" cellpadding="5">\n  <tr><td>Customer</td><td>{{ doc.customer }}</td></tr>\n  <tr><td>Amount</td><td>{{ doc.grand_total }}</td></tr>\n</table>\n<p><a href="{{ frappe.utils.get_url_to_form(doc.doctype, doc.name) }}">View in ERPNext</a></p>`);

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
			${DtSel("ss_dt","DocType (for DocType Event)")}
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
		wireAD($c,"ss_ap","ss_dt");

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
			${DtSel("rp2_dt","DocType")}
		</div>`);
		wireAD($c1,"rp2_ap","rp2_dt");

		const $matrix = $(`<div class="dkst-card" style="display:none"><div class="dkst-card-title">Permission Matrix</div>
			<div class="dkst-tbl-wrap"><table class="dkst-tbl" id="perm-tbl">
			<thead><tr><th>Role</th><th>Read</th><th>Write</th><th>Create</th><th>Delete</th><th>Submit</th><th>Cancel</th><th>Amend</th><th>Print</th><th>Email</th><th>Export</th><th>Share</th><th>If Owner</th><th></th></tr></thead>
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
			${AppSel("ins_ap")}
			${DtSel("ins_dt","DocType")}
			${ModSel("ins_mo","Narrow by Module")}
		</div>`);

		// Wire app → doctypes immediately; module narrows further
		wireAD($c,"ins_ap","ins_dt");
		const $modSel=$c.find("#ins_mo");
		const $dtSel =$c.find("#ins_dt");
		$c.find("#ins_ap").on("change", function() {
			const app = this.value;
			$modSel.prop("disabled",!app).html('<option value="">— all modules —</option>');
			if (!app) return;
			loadMods(app).then(ms => { fillSel($modSel, ms, "all modules"); $modSel.prop("disabled",false); });
		});
		$modSel.on("change",function(){
			const mod=this.value;
			if(!mod) {
				// reset to all app doctypes
				const app=$c.find("#ins_ap").val();
				if(app) loadDtsByApp(app).then(ds=>{fillSel($dtSel,ds,"select doctype");$dtSel.prop("disabled",false);});
				return;
			}
			$dtSel.prop("disabled",true).html('<option value="">— select doctype —</option>');
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

	PANELS.fixture_mgr = function($p) {
		$p.append(phdr("Fixture Manager","View, inspect and manage fixture JSON files for any app.",icoExport(20)));

		const $sel = card($p, "App Selection");
		$sel.append(`<div class="dkst-g2">${AppSel("fm_ap")}</div>`);
		loadApps().then(() => fillSel($sel.find("#fm_ap"), _apps, "select app"));

		const $filesWrap = $(`<div id="fm-files-wrap" style="display:none"></div>`).appendTo($p);
		const $filesCard = card($filesWrap, "Fixture Files");
		$filesCard.append(`<div style="display:flex;gap:10px;margin-bottom:10px;align-items:center">
			<button class="dkst-btn dkst-btn-s" id="fm-refresh">↻ Refresh</button>
			<button class="dkst-btn dkst-btn-p" id="fm-export">⬆ Export Fixtures</button>
			<span style="flex:1"></span>
			<span style="font-size:12px;color:#9080b8" id="fm-file-count"></span>
		</div>`);
		$filesCard.append(`<div class="dkst-tbl-wrap">
			<table class="dkst-tbl">
				<thead><tr><th>Filename</th><th>DocType</th><th>Records</th><th></th></tr></thead>
				<tbody id="fm-file-rows"></tbody>
			</table>
		</div>`);

		const $recWrap = $(`<div id="fm-rec-wrap" style="display:none"></div>`).appendTo($p);
		const $recCard = card($recWrap, "Records");
		$recCard.append(`<div style="display:flex;gap:10px;margin-bottom:10px;align-items:center">
			<button class="dkst-btn dkst-btn-s" id="fm-rec-back">← Back to Files</button>
			<span style="font-size:13px;font-weight:600;color:#1e1a2e" id="fm-rec-title"></span>
			<span style="flex:1"></span>
			<input class="dkst-inp" id="fm-rec-search" style="width:220px" placeholder="Filter records…">
			<span style="font-size:12px;color:#9080b8" id="fm-rec-count"></span>
		</div>`);
		$recCard.append(`<div class="dkst-tbl-wrap" style="max-height:420px;overflow-y:auto">
			<table class="dkst-tbl">
				<thead><tr><th>#</th><th>Name</th><th>Fields</th><th style="width:60px"></th></tr></thead>
				<tbody id="fm-rec-rows"></tbody>
			</table>
		</div>`);

		const $ft = term($p);
		let _fmApp = '', _fmFile = '', _fmRecords = [];

		function loadFiles() {
			_fmApp = gv("fm_ap");
			if (!_fmApp) { frappe.throw("Select an app"); return; }
			frappe.call({ method:"frappe_devkit.api.fixture_builder.list_fixture_files",
				args:{app_name:_fmApp},
				callback: r => {
					const files = r.message?.files || [];
					$("#fm-file-count").text(`${files.length} fixture file${files.length!==1?'s':''}`);
					const $tbody = $("#fm-file-rows").empty();
					if (!files.length) {
						$tbody.html(`<tr><td colspan="4" class="dkst-empty">No fixture files found for this app.</td></tr>`);
					} else {
						files.forEach(f => {
							$tbody.append(`<tr>
								<td style="font-family:monospace;font-size:12px;color:#0055cc">${f.filename}</td>
								<td>${f.doctype}</td>
								<td><span class="dkst-pill dkst-pill-b">${f.count}</span></td>
								<td><button class="dkst-btn dkst-btn-s fm-view-btn" data-fn="${f.filename}">View</button></td>
							</tr>`);
						});
					}
					$filesWrap.show();
					$recWrap.hide();
				}
			});
		}

		function loadRecords(filename) {
			_fmFile = filename;
			$("#fm-rec-title").text(filename);
			$("#fm-rec-rows").html(`<tr><td colspan="4" class="dkst-empty">Loading…</td></tr>`);
			$filesWrap.hide(); $recWrap.show();
			frappe.call({ method:"frappe_devkit.api.fixture_builder.read_fixture_file",
				args:{app_name:_fmApp, filename},
				callback: r => {
					_fmRecords = r.message?.records || [];
					renderRecords(_fmRecords);
				}
			});
		}

		function renderRecords(records) {
			const $tbody = $("#fm-rec-rows").empty();
			$("#fm-rec-count").text(`${records.length} record${records.length!==1?'s':''}`);
			if (!records.length) {
				$tbody.html(`<tr><td colspan="4" class="dkst-empty">No records in this fixture file.</td></tr>`);
				return;
			}
			records.forEach((rec, i) => {
				const keys = Object.keys(rec).filter(k => k !== 'doctype').slice(0,6).join(', ');
				$tbody.append(`<tr>
					<td style="color:#b0a8c8;width:40px">${i+1}</td>
					<td style="font-weight:600;color:#1e1a2e;word-break:break-all">${frappe.utils.escape_html(rec.name||'—')}</td>
					<td style="font-size:11.5px;color:#7a70a8">${frappe.utils.escape_html(keys)}</td>
					<td><button class="dkst-btn dkst-btn-r fm-del-btn" style="padding:2px 8px;font-size:11px" data-name="${frappe.utils.escape_html(rec.name||'')}">✕</button></td>
				</tr>`);
			});
		}

		$sel.on('change', '#fm_ap', loadFiles);
		$p.on('click', '#fm-refresh', loadFiles);
		$p.on('click', '#fm-export', () => {
			if (!_fmApp) return;
			api("frappe_devkit.api.fixture_builder.export_fixtures", {app_name:_fmApp}, $ft);
		});
		$p.on('click', '.fm-view-btn', function() { loadRecords($(this).data('fn')); });
		$p.on('click', '#fm-rec-back', () => { $recWrap.hide(); $filesWrap.show(); });
		$p.on('input', '#fm-rec-search', function() {
			const q = this.value.toLowerCase();
			const filtered = q ? _fmRecords.filter(r => (r.name||'').toLowerCase().includes(q)) : _fmRecords;
			renderRecords(filtered);
		});
		$p.on('click', '.fm-del-btn', function() {
			const name = $(this).data('name');
			if (!name || !_fmFile) return;
			frappe.confirm(`Remove <b>${frappe.utils.escape_html(name)}</b> from fixture file <b>${_fmFile}</b>?`, () => {
				frappe.call({ method:"frappe_devkit.api.fixture_builder.delete_fixture_record",
					args:{app_name:_fmApp, filename:_fmFile, record_name:name},
					callback: r => {
						frappe.show_alert({message:`Removed from fixture`, indicator:'green'}, 3);
						loadRecords(_fmFile);
					}
				});
			});
		});
	};

	PANELS.fixture_diff = function($p) {
		$p.append(phdr("Fixture Diff","Compare fixture JSON file records with current database records.",icoDiff(20)));
		$p.append(info("Identifies records that exist only in the fixture file, only in the DB, or are in sync."));
		const $c=card($p,"Select App & DocType");
		$c.append(`<div class="dkst-g2">
			${AppSel("fd_ap")}
			${DtSel("fd_dt","DocType (fixture file name)")}
		</div>
		<div class="dkst-hint" style="margin-top:6px">e.g. "Custom Field" looks for <span class="dkst-code">fixtures/custom_field.json</span></div>`);
		wireAD($c,"fd_ap","fd_dt");

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

					// Render table — each installed site shown as its own pill
					_bench_apps.forEach(a => {
						const txtOk  = a.in_sites_txt;
						const jsonOk = a.in_apps_json;
						const regCell = `<div style="display:flex;flex-direction:column;gap:3px">
							<span class="dkst-pill ${txtOk?'dkst-pill-g':'dkst-pill-r'}" style="font-size:10px">${txtOk?'✓':'✗'} sites/apps.txt</span>
							<span class="dkst-pill ${jsonOk?'dkst-pill-g':'dkst-pill-r'}" style="font-size:10px">${jsonOk?'✓':'✗'} apps.json</span>
						</div>`;
						const sites = a.installed_on || [];
						const installCell = sites.length
							? `<div style="display:flex;flex-direction:column;gap:3px">${
								sites.map(s => `<span class="dkst-pill dkst-pill-b" style="font-size:11px;font-family:monospace">${s}</span>`).join('')
							  }</div>`
							: `<span style="color:#b0a8c8;font-size:12px;font-style:italic">not installed</span>`;
						const isCore   = ["frappe","erpnext","hrms"].includes(a.app);
						const needsFix = !txtOk || !jsonOk;
						const fixBtn   = (!isCore && needsFix)
							? `<button class="dkst-btn dkst-btn-s" style="padding:3px 10px;font-size:11px"
								onclick="frappe.call({method:'frappe_devkit.api.app_builder.register_existing_app',args:{app_name:'${a.app}'},callback:r=>frappe.show_alert({message:r.message?.message,indicator:'green'})})">⚡ Fix</button>`
							: (isCore ? `<span style="font-size:11px;color:#b0a8c8">core</span>` : '');
						$arows.append(`<tr>
							<td style="min-width:110px">
								<div style="font-weight:700;color:#5c4da8;font-size:13px;font-family:monospace">${a.app}</div>
								<div style="font-size:11px;color:#9080b8;margin-top:2px">${a.publisher||''}</div>
							</td>
							<td style="min-width:140px">
								<div style="color:#1e1a2e;font-weight:600">${a.title||a.app}</div>
								<div style="font-size:11px;color:#9080b8;margin-top:3px;max-width:220px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap" title="${(a.description||'').replace(/"/g,'&quot;')}">${a.description||''}</div>
							</td>
							<td style="white-space:nowrap"><span class="dkst-pill dkst-pill-p" style="font-family:monospace">${a.version}</span></td>
							<td style="min-width:130px">${installCell}</td>
							<td style="min-width:140px">${regCell}</td>
							<td style="white-space:nowrap">${fixBtn}</td>
						</tr>`);
					});
					setStatus("Ready");
				}
			});

			// Load sites — use list_sites (proven, returns full installed list)
			const $sitesDiv = $("#am-sites-list");
			$sitesDiv.html(`<div class="dkst-empty">Loading sites…</div>`);
			frappe.call({ method: "frappe_devkit.api.site_manager.list_sites",
				callback: r => {
					_bench_sites = r.message?.sites || [];
					$sitesDiv.empty();

					// Populate site selector in the install/uninstall card
					const $siteSel = $ac.find("#am-sel-site");
					$siteSel.html('<option value="">— select site —</option>');
					_bench_sites.forEach(s => {
						const cnt = (s.installed || []).length;
						$siteSel.append(`<option value="${s.site}">${s.site} (${cnt} app${cnt!==1?'s':''})</option>`);
					});

					if (!_bench_sites.length) {
						$sitesDiv.html(`<div class="dkst-empty">No sites found in this bench.</div>`);
						return;
					}

					// Render sites as cards
					const $grid = $(`<div class="dkst-g2"></div>`).appendTo($sitesDiv);
					_bench_sites.forEach(s => {
						const appList = Array.isArray(s.installed) ? s.installed : [];
						const active  = !s.maintenance;
						const accentColor = active ? '#27ae60' : '#c0392b';
						const $c2 = $(`<div class="dkst-card" style="border-left:4px solid ${accentColor};padding:16px 18px"></div>`).appendTo($grid);

						// Header row: site name + status + app count
						$c2.append(`<div style="display:flex;align-items:center;gap:8px;margin-bottom:12px;flex-wrap:wrap">
							<div style="font-weight:700;color:#1e1a2e;font-size:14px;font-family:monospace;flex:1">${s.site}</div>
							${active
								? '<span class="dkst-pill dkst-pill-g" style="font-size:10px">● Active</span>'
								: '<span class="dkst-pill dkst-pill-r" style="font-size:10px">⚠ Maintenance</span>'}
							<span class="dkst-pill dkst-pill-p" style="font-size:10px">${appList.length} app${appList.length!==1?'s':''}</span>
						</div>`);

						// Installed apps label + pills
						$c2.append(`<div style="font-size:10px;color:#9080b8;font-weight:700;text-transform:uppercase;letter-spacing:.12em;margin-bottom:8px">Installed Apps</div>`);
						if (appList.length) {
							const pills = appList.map(a =>
								`<span class="dkst-pill dkst-pill-p" style="font-family:monospace;font-size:11.5px;font-weight:600">${a}</span>`
							).join('');
							$c2.append(`<div style="display:flex;flex-wrap:wrap;gap:6px">${pills}</div>`);
						} else {
							$c2.append(`<div style="font-size:12px;color:#b0a8c8;font-style:italic">No apps installed on this site.</div>`);
						}

						// DB info row
						if (s.db_name || s.db_type) {
							$c2.append(`<div style="margin-top:10px;padding-top:10px;border-top:1px solid #f0ecf8;font-size:11px;color:#9080b8;display:flex;gap:14px">
								${s.db_name ? `<span>DB: <code style="color:#5c4da8">${s.db_name}</code></span>` : ''}
								${s.db_type ? `<span>Engine: <code style="color:#5c4da8">${s.db_type}</code></span>` : ''}
							</div>`);
						}
					});
				}
			});
		}

		// Populate site select on demand via siteSelRow-like approach
		const $siteSel = $ac.find("#am-sel-site");
		$('<button class="dkst-btn dkst-btn-s" style="margin-top:8px;font-size:12px">↻ Load Sites</button>')
			.insertAfter($siteSel)
			.on('click', function() { loadSiteSelect($siteSel, 'select site', true); });

		$p.on("click","#am-refresh-apps,#am-refresh-sites", loadAppsAndSites);
		// Show placeholder — do NOT auto-load
		$("#am-app-rows").html('<tr><td colspan="6" class="dkst-empty" style="padding:20px">Click <b>↻ Refresh</b> to list bench apps.</td></tr>');
		$("#am-sites-list").html('<div class="dkst-empty" style="padding:20px">Click <b>↻ Refresh</b> to list bench sites.</div>');
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
	// Cache of sites for lazy loading
	let _sites_cache = null;
	function loadSiteSelect($sel, ph, forceRefresh) {
		if (_sites_cache && !forceRefresh) {
			$sel.empty().prop('disabled', false);
			if (ph) $sel.append(`<option value="">— ${ph} —</option>`);
			_sites_cache.forEach(s => $sel.append(`<option value="${s.site}">${s.site}</option>`));
			return;
		}
		$sel.html('<option value="">— loading sites… —</option>').prop('disabled', true);
		frappe.call({ method: 'frappe_devkit.api.site_manager.list_sites',
			callback: r => {
				_sites_cache = r.message?.sites || [];
				$sel.empty().prop('disabled', false);
				if (ph) $sel.append(`<option value="">— ${ph} —</option>`);
				if (!_sites_cache.length) {
					$sel.append('<option value="" disabled>No sites found</option>');
					return;
				}
				_sites_cache.forEach(s => $sel.append(`<option value="${s.site}">${s.site} (${s.app_count} apps)</option>`));
			},
			error: () => { $sel.html('<option value="">— failed to load —</option>').prop('disabled', false); }
		});
	}
	// Attach a refresh button next to any site select
	function siteSelRow($parent, selId, ph) {
		const $row = $(`<div style="display:flex;gap:8px;align-items:center"></div>`).appendTo($parent);
		const $sel = $(`<select class="dkst-sel" id="${selId}" style="flex:1"><option value="">— select site —</option></select>`).appendTo($row);
		$(`<button class="dkst-btn dkst-btn-s" style="padding:5px 10px;font-size:12px;flex-shrink:0" title="Load / Refresh site list">↻</button>`)
			.appendTo($row)
			.on('click', function() {
				loadSiteSelect($sel, ph, true);
			});
		loadSiteSelect($sel, ph);
		return $sel;
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
	// Bench command hints per API method
	const _benchCmds = {
		'frappe_devkit.api.site_manager.migrate_site':       (a) => `bench --site ${a.site||'<site>'} migrate${a.skip_failing?' --skip-failing-patches':''}`,
		'frappe_devkit.api.site_manager.clear_site_cache':   (a) => `bench --site ${a.site||'<site>'} clear-cache`,
		'frappe_devkit.api.site_manager.clear_website_cache':(a) => `bench --site ${a.site||'<site>'} clear-website-cache`,
		'frappe_devkit.api.site_manager.backup_site':        (a) => `bench --site ${a.site||'<site>'} backup${a.with_files?' --with-files':''}${a.compress?' --compress':''}`,
		'frappe_devkit.api.site_manager.restore_site':       (a) => `bench --site ${a.site||'<site>'} restore ${a.backup_file||'<db-file>'}${a.with_private_files?' --with-private-files '+a.with_private_files:''}${a.with_public_files?' --with-public-files '+a.with_public_files:''}${a.admin_password?' --admin-password <pwd>':''}${parseInt(a.force)?' --force':''}`,
		'frappe_devkit.api.site_manager.create_site':        (a) => `bench new-site ${a.site||'<site>'} --admin-password <pwd> --db-type ${a.db_type||'mariadb'}`,
		'frappe_devkit.api.site_manager.drop_site':          (a) => `bench drop-site ${a.site||'<site>'}${a.force?' --force':''}`,
		'frappe_devkit.api.site_manager.set_admin_password': (a) => `bench --site ${a.site||'<site>'} set-admin-password <new-password>`,
		'frappe_devkit.api.site_manager.set_maintenance_mode':(a)=> `bench --site ${a.site||'<site>'} set-maintenance-mode ${a.enable?'on':'off'}`,
		'frappe_devkit.api.site_manager.scheduler_action':   (a) => `bench --site ${a.site||'<site>'} scheduler ${a.action||'status'}`,
		'frappe_devkit.api.site_manager.use_site':           (a) => `bench use ${a.site||'<site>'}`,
		'frappe_devkit.api.site_manager.get_site_config':    (a) => `cat sites/${a.site||'<site>'}/site_config.json`,
		'frappe_devkit.api.site_manager.set_site_config':    (a) => `bench --site ${a.site||'<site>'} set-config ${a.key||'<key>'} "${a.value||''}"`,
		'frappe_devkit.api.site_manager.remove_site_config': (a) => `# removes key '${a.key||'<key>'}' from sites/${a.site||'<site>'}/site_config.json`,
		'frappe_devkit.api.site_manager.execute_script':     (a) => `bench --site ${a.site||'<site>'} execute frappe.utils.execute_script`,
		'frappe_devkit.api.app_builder.install_app_on_site': (a) => `bench --site ${a.site||'<site>'} install-app ${a.app_name||'<app>'}`,
		'frappe_devkit.api.app_builder.uninstall_app_from_site':(a)=>`bench --site ${a.site||'<site>'} uninstall-app ${a.app_name||'<app>'}`,
		'frappe_devkit.api.app_builder.register_existing_app':(a) => `echo '${a.app_name||'<app>'}' >> apps.txt && bench update --no-pull`,
	};

	function smApi(method, args, $t, benchCmd) {
		const cmd = benchCmd || (_benchCmds[method] ? _benchCmds[method](args) : null);
		let initial = '▶  Running…';
		if (cmd) initial = `$ ${cmd}\n\n▶  Running…`;
		$t.text(initial).removeClass('ok err');
		frappe.call({ method, args,
			callback: r => {
				const m = r.message;
				if (m?.status === 'success') {
					$t.addClass('ok');
					let out = cmd ? `$ ${cmd}\n\n` : '';
					out += `✓  ${m.message}`;
					if (m.stdout?.trim()) out += `\n\n── Output ──\n${m.stdout.trim()}`;
					if (m.stderr?.trim()) out += `\n\n── Stderr ──\n${m.stderr.trim()}`;
					if (m.info)   out += `\n\n── Info ──\n${JSON.stringify(m.info, null, 2)}`;
					if (m.config) out += `\n\n── Config ──\n${JSON.stringify(m.config, null, 2)}`;
					if (m.backups?.length) {
						out += '\n\n── Backups ──\n';
						m.backups.slice(0,20).forEach(b => out += `  ${b.type.padEnd(10)} ${b.size.padEnd(10)} ${b.date}  ${b.name}\n`);
					}
					$t.text(out);
					frappe.show_alert({ message: m.message, indicator: 'green' });
				} else {
					$t.addClass('err');
					let out = cmd ? `$ ${cmd}\n\n` : '';
					out += `✗  ${m?.message || 'Operation failed'}`;
					if (m?.stdout?.trim()) out += `\n\n── Output ──\n${m.stdout.trim()}`;
					if (m?.stderr?.trim()) out += `\n\n── Stderr ──\n${m.stderr.trim()}`;
					$t.text(out);
					frappe.show_alert({ message: m?.message || 'Operation failed', indicator: 'red' });
				}
			},
			error: e => {
				$t.addClass('err');
				const msg = e.responseJSON?.exception || e.responseJSON?.message || 'Network or server error';
				$t.text((cmd?`$ ${cmd}\n\n`:'')+`✗  ${msg}`);
			}
		});
	}
	function smGv(id) { return ($(`#${id}`).val() || '').trim(); }
	function smReq(id, label) {
		const v = smGv(id);
		if (!v) { frappe.throw(`${label} is required`); return null; }
		return v;
	}

	// ── Site Overview ──────────────────────────────────
	PANELS.site_overview = function($p) {
		$p.append(phdr('Site Overview', 'All bench sites — installed apps, status, database.', icoGlobe(20)));
		$p.append(info('Lists all sites in this bench. Click <b>Load Sites</b> to fetch current state. Use <span class="dkst-code">bench --site &lt;site&gt; …</span> commands for per-site operations.'));
		const $tb = $(`<div style="display:flex;gap:10px;margin-bottom:16px;align-items:center">
			<button class="dkst-btn dkst-btn-p" id="sov-load">Load Sites</button>
			<button class="dkst-btn dkst-btn-s" id="sov-ref" style="display:none">↻ Refresh</button>
			<span style="flex:1"></span>
			<span style="font-size:12px;color:#9080b8" id="sov-cnt"></span>
		</div>`).appendTo($p);
		const $grid = $('<div id="sov-grid"><div class="dkst-empty" style="padding:40px 0">Click <b>Load Sites</b> to list all sites in this bench.</div></div>').appendTo($p);

		function loadOverview() {
			$('#sov-cnt').text('');
			$grid.html('<div class="dkst-empty">Loading…</div>');
			_sites_cache = null; // force refresh
			frappe.call({ method: 'frappe_devkit.api.site_manager.list_sites',
				callback: r => {
					const sites = r.message?.sites || [];
					_sites_cache = sites;
					$grid.empty();
					$('#sov-cnt').text(`${sites.length} site${sites.length!==1?'s':''}`);
					$('#sov-ref').show(); $('#sov-load').text('↻ Reload');
					if (!sites.length) { $grid.html('<div class="dkst-empty">No sites found in this bench.</div>'); return; }
					sites.forEach(s => {
						const active = !s.maintenance;
						const col = active ? '#1a7a3a' : '#c0392b';
						const $c = $(`<div class="dkst-card" style="border-left:4px solid ${col};margin-bottom:14px"></div>`).appendTo($grid);
						$c.append(`<div style="display:flex;align-items:center;gap:10px;margin-bottom:10px">
							<div style="font-size:15px;font-weight:700;color:#1e1a2e;flex:1;font-family:monospace">${s.site}</div>
							${active ? '<span class="dkst-pill dkst-pill-g">● Active</span>' : '<span class="dkst-pill dkst-pill-r">⚠ Maintenance</span>'}
						</div>`);
						const pills = (s.installed||[]).map(a => `<span class="dkst-pill dkst-pill-p" style="font-size:11px">${a}</span>`).join(' ');
						$c.append(`<div style="margin-bottom:8px">
							<span style="font-size:11px;color:#9080b8;font-weight:700;text-transform:uppercase;letter-spacing:.07em">Apps (${s.app_count})</span>
							<div style="margin-top:6px;display:flex;flex-wrap:wrap;gap:5px">${pills||'<span style="color:#b0a8c8;font-size:12px">none</span>'}</div>
						</div>`);
						const meta = [];
						if (s.db_name) meta.push(`DB: <span class="dkst-code">${s.db_name}</span>`);
						if (s.db_type) meta.push(`Engine: <span class="dkst-code">${s.db_type}</span>`);
						if (meta.length) $c.append(`<div style="font-size:12px;color:#7a70a8;display:flex;gap:16px">${meta.join('')}</div>`);
					});
				},
				error: () => $grid.html('<div class="dkst-empty" style="color:#c0392b">Failed to load sites. Check server logs.</div>')
			});
		}
		$p.on('click', '#sov-load,#sov-ref', loadOverview);
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
		$c2.append('<div style="font-size:12px;color:#7a70a8;margin-bottom:10px">Select apps to install during site creation. <b>frappe</b> is always included.</div>');
		const $appWrap = $('<div class="dkst-checks" id="sc-apps"><span style="color:#9080b8;font-size:12px">Click Load to see available apps.</span></div>').appendTo($c2);
		$('<button class="dkst-btn dkst-btn-s" style="margin-top:10px;font-size:12px">↻ Load Available Apps</button>')
			.appendTo($c2)
			.on('click', function() {
				$(this).prop('disabled',true).text('Loading…');
				const $btn = $(this);
				frappe.call({ method: 'frappe_devkit.api.app_builder.get_bench_apps',
					callback: r => {
						$appWrap.empty();
						const apps = (r.message?.apps || []).filter(a => a.app !== 'frappe');
						if (!apps.length) { $appWrap.html('<span style="color:#9080b8;font-size:12px">No additional apps found.</span>'); }
						apps.forEach(a =>
							$appWrap.append(`<label class="dkst-chk"><input type="checkbox" class="sc-app-chk" value="${a.app}"><span>${a.app} <span style="color:#9080b8;font-size:11px">v${a.version}</span></span></label>`)
						);
						$btn.text('↻ Reload').prop('disabled',false);
					}
				});
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
		$p.append(phdr('Backup & Restore', 'Take, schedule and restore site backups via bench commands.', icoSave(20)));
		$p.append(info('Backups stored in <span class="dkst-code">sites/&lt;site&gt;/private/backups/</span>. Click a backup row to auto-fill the Restore form.'));

		// shared backup list cache per site (key = site name, value = array of backup objects)
		const _bkCache = {};

		function _downloadBackup(site, filename) {
			const url = `/api/method/frappe_devkit.api.site_manager.download_backup_file?site=${encodeURIComponent(site)}&filename=${encodeURIComponent(filename)}`;
			const a = document.createElement('a');
			a.href = url; a.download = filename; a.style.display = 'none';
			document.body.appendChild(a); a.click();
			setTimeout(() => document.body.removeChild(a), 200);
		}

		// helper: load backup list into $target container, call onSelect(backup) when a db row is clicked
		function loadBkList(site, $target, onSelect) {
			$target.html('<div style="color:#9080b8;font-size:12px;padding:8px 0">Loading…</div>');
			frappe.call({ method: 'frappe_devkit.api.site_manager.list_backups', args: { site },
				callback: r => {
					const bks = r.message?.backups || [];
					_bkCache[site] = bks;
					$target.empty();
					if (!bks.length) {
						$target.html('<div style="color:#9080b8;font-size:12px;padding:8px 0">No backups found. Take a backup first.</div>');
						return;
					}
					// Group by date prefix (first 15 chars of filename to group db+files together)
					const groups = {};
					bks.forEach(b => {
						const key = b.name.substring(0, 15);
						if (!groups[key]) groups[key] = { date: b.date, db: null, priv: null, pub: null };
						if (b.type === 'database') groups[key].db = b;
						else if (b.name.includes('private')) groups[key].priv = b;
						else if (b.name.includes('files') && !b.name.includes('private')) groups[key].pub = b;
					});
					const $tbl = $(`<table class="dkst-tbl">
						<thead><tr>
							<th style="width:110px">Date</th>
							<th>DB Backup</th>
							<th>DB Size</th>
							<th style="width:80px">Files?</th>
							<th style="width:90px">Use</th>
							<th style="width:145px">Download</th>
						</tr></thead>
						<tbody></tbody>
					</table>`).appendTo($target);
					Object.values(groups).sort((a,b)=>b.date.localeCompare(a.date)).forEach(g => {
						const hasFiles = !!(g.priv || g.pub);
						const $tr = $(`<tr>
							<td style="white-space:nowrap;color:#7a70a8;font-size:11px">${g.date}</td>
							<td style="font-family:monospace;font-size:11px;color:#5c4da8;word-break:break-all">${g.db ? g.db.name : '<span style="color:#c0392b">missing</span>'}</td>
							<td style="white-space:nowrap">${g.db ? g.db.size : '—'}</td>
							<td style="text-align:center">${hasFiles ? '<span class="dkst-pill dkst-pill-g" style="font-size:10px">yes</span>' : '<span style="color:#ccc;font-size:11px">—</span>'}</td>
							<td></td>
							<td style="white-space:nowrap"></td>
						</tr>`).appendTo($tbl.find('tbody'));
						if (g.db && onSelect) {
							const $btn = $('<button class="dkst-btn dkst-btn-s" style="font-size:11px;padding:3px 10px">Select ↓</button>').appendTo($tr.find('td:nth-child(5)'));
							$btn.on('click', () => onSelect(g));
						}
						const $dlTd = $tr.find('td:last');
						if (g.db)   $('<button class="dkst-btn dkst-btn-s" style="font-size:11px;padding:2px 7px;margin-right:2px" title="Download database backup">⬇ DB</button>').appendTo($dlTd).on('click', () => _downloadBackup(site, g.db.name));
						if (g.pub)  $('<button class="dkst-btn dkst-btn-s" style="font-size:11px;padding:2px 7px;margin-right:2px" title="Download public files">⬇ Pub</button>').appendTo($dlTd).on('click', () => _downloadBackup(site, g.pub.name));
						if (g.priv) $('<button class="dkst-btn dkst-btn-s" style="font-size:11px;padding:2px 7px" title="Download private files">⬇ Priv</button>').appendTo($dlTd).on('click', () => _downloadBackup(site, g.priv.name));
					});
				}
			});
		}

		// ── Take Backup ──────────────────────────────────
		const $bc = smCard($p, 'Take Backup');
		$bc.append(`<div style="font-size:12px;color:#7a70a8;margin-bottom:12px">
			Equivalent: <span class="dkst-code">bench --site &lt;site&gt; backup</span>
			<span style="color:#9080b8"> &nbsp;·&nbsp; Output saved to <span class="dkst-code">sites/&lt;site&gt;/private/backups/</span></span>
		</div>`);
		const $bkSiteRow = $('<div class="dkst-fld"><label class="dkst-lbl dkst-req">Site</label></div>').appendTo($bc);
		const $bkSite = siteSelRow($bkSiteRow, 'bk-site', 'select site');
		$bc.append(`<div class="dkst-g2" style="margin-top:12px">
			<div class="dkst-fld"><label class="dkst-lbl">Backup Name (optional)</label>
				<input class="dkst-inp" id="bk-name" placeholder="Auto-generated if blank">
				<span class="dkst-hint">Prefix for backup file names</span></div>
		</div>
		<div class="dkst-checks" style="margin-top:10px">
			<label class="dkst-chk"><input type="checkbox" id="bk-files"><span>Include uploaded files <span style="color:#9080b8;font-size:11px">(--with-files · slower)</span></span></label>
			<label class="dkst-chk"><input type="checkbox" id="bk-comp" checked><span>Compress output <span style="color:#9080b8;font-size:11px">(--compress · .gz)</span></span></label>
			<label class="dkst-chk"><input type="checkbox" id="bk-verbose"><span>Verbose output</span></label>
		</div>`);
		const $t1 = smTerm($p);
		smBtns($bc, [{ lbl: 'Take Backup Now', cls: 'dkst-btn-p', fn: () => {
			const site = $bkSite.val();
			if (!site) { frappe.throw('Select a site'); return; }
			smApi('frappe_devkit.api.site_manager.backup_site', {
				site, with_files: $('#bk-files').is(':checked') ? 1 : 0,
				compress: $('#bk-comp').is(':checked') ? 1 : 0,
			}, $t1);
		}}]);

		// ── Browse & List Backups ──────────────────────────────────
		const $lc = smCard($p, 'Browse Backups');
		$lc.append(`<div style="font-size:12px;color:#7a70a8;margin-bottom:10px">
			Lists all backups for the selected site. Click <b>Select ↓</b> to auto-fill the Restore form below.
		</div>`);
		const $blSiteRow = $('<div class="dkst-fld"><label class="dkst-lbl dkst-req">Site</label></div>').appendTo($lc);
		const $blSite = siteSelRow($blSiteRow, 'bl-site', 'select site');
		const $blRes = $('<div id="bl-res" style="margin-top:12px"></div>').appendTo($lc);

		// when site changes, auto-load
		$blSite.on('change', function() {
			const site = this.value;
			$blRes.empty();
			if (!site) return;
			loadBkList(site, $blRes, g => {
				// scroll to restore card and fill fields
				$rsSite.val(site).trigger('change');
				$('#rs-file').val(g.db ? g.db.path : '');
				$('#rs-priv').val(g.priv ? g.priv.path : '');
				$('#rs-pub').val(g.pub ? g.pub.path : '');
				$p.closest('.dkst-panel-area').animate({ scrollTop: $rc.offset().top }, 400);
				frappe.show_alert({ message: 'Backup selected — review the Restore form below.', indicator: 'green' }, 4);
			});
		});
		smBtns($lc, [{ lbl: '↻ Refresh List', cls: 'dkst-btn-s', fn: () => {
			const site = $blSite.val();
			if (!site) { frappe.throw('Select a site first'); return; }
			loadBkList(site, $blRes, g => {
				$rsSite.val(site).trigger('change');
				$('#rs-file').val(g.db ? g.db.path : '');
				$('#rs-priv').val(g.priv ? g.priv.path : '');
				$('#rs-pub').val(g.pub ? g.pub.path : '');
				$p.closest('.dkst-panel-area').animate({ scrollTop: $rc.offset().top }, 400);
				frappe.show_alert({ message: 'Backup selected — review the Restore form below.', indicator: 'green' }, 4);
			});
		}}]);

		// ── Upload Backup ──────────────────────────────────
		const $uc = smCard($p, 'Upload Backup Files');
		$uc.append(`<div style="font-size:12px;color:#7a70a8;margin-bottom:12px">
			Upload backup files from your computer directly to
			<span class="dkst-code">sites/&lt;site&gt;/private/backups/</span>.
			Supported: <code>.sql.gz</code> / <code>.sql</code> (database) and <code>.tar</code> (files).
		</div>`);
		const $ucSiteRow = $('<div class="dkst-fld"><label class="dkst-lbl dkst-req">Site</label></div>').appendTo($uc);
		const $ucSite = siteSelRow($ucSiteRow, 'uc-site', 'select site');

		function _makeUploadRow(lbl, accept, fileType, hint) {
			const $row = $(`<div class="dkst-fld" style="margin-top:12px">
				<label class="dkst-lbl">${lbl}</label>
				<div style="display:flex;gap:8px;align-items:center">
					<input type="file" class="dkst-inp" style="flex:1;padding:4px 8px;font-size:12px" accept="${accept}">
					<button class="dkst-btn dkst-btn-s" style="flex-shrink:0;white-space:nowrap">\u2b06 Upload</button>
				</div>
				<div class="uc-status" style="font-size:11px;margin-top:4px;min-height:16px;color:#7a70a8">${hint}</div>
			</div>`);
			$row.find('.dkst-btn').on('click', function() {
				const site = $ucSite.val();
				if (!site) { frappe.show_alert({ message:'Select a site first', indicator:'orange' }); return; }
				const fileInput = $row.find('input[type=file]')[0];
				if (!fileInput.files.length) { frappe.show_alert({ message:'Select a file first', indicator:'orange' }); return; }
				const $status = $row.find('.uc-status');
				const $btn = $(this);
				$status.text('Uploading\u2026').css('color','#5c4da8');
				$btn.prop('disabled', true);
				const fd = new FormData();
				fd.append('file', fileInput.files[0]);
				fd.append('site', site);
				fd.append('file_type', fileType);
				$.ajax({
					url: '/api/method/frappe_devkit.api.site_manager.upload_backup_file',
					type: 'POST',
					data: fd,
					processData: false,
					contentType: false,
					headers: { 'X-Frappe-CSRF-Token': frappe.csrf_token },
					success: r => {
						$btn.prop('disabled', false);
						if (r.message?.uploaded) {
							$status.text(`\u2713 Uploaded: ${r.message.filename} (${r.message.size})`).css('color','#27ae60');
							fileInput.value = '';
						} else {
							$status.text('Upload failed').css('color','#c0392b');
						}
					},
					error: xhr => {
						$btn.prop('disabled', false);
						const msg = xhr.responseJSON?.exc_type || xhr.responseJSON?._server_messages || 'Upload failed';
						$status.text(`\u2717 ${String(msg).substring(0,120)}`).css('color','#c0392b');
					}
				});
			});
			return $row;
		}
		$uc.append(_makeUploadRow('Database Backup (.sql.gz / .sql)', '.sql.gz,.sql', 'database', 'Upload a .sql.gz compressed database backup'));
		$uc.append(_makeUploadRow('Public Files Backup (-files.tar)', '.tar', 'public_files', 'Upload a *-files.tar archive'));
		$uc.append(_makeUploadRow('Private Files Backup (-private-files.tar)', '.tar', 'private_files', 'Upload a *-private-files.tar archive'));

		// ── Restore from Backup ──────────────────────────────────
		const $rc = smCard($p, 'Restore from Backup');
		$rc.append(`<div style="background:#fde8e6;border:1px solid #e8a8a0;border-radius:6px;padding:12px 16px;margin-bottom:16px">
			<div style="font-size:13px;font-weight:700;color:#c0392b;margin-bottom:4px">⚠ Danger — Data will be overwritten</div>
			<div style="font-size:12px;color:#7a2020;line-height:1.7">
				Equivalent: <code>bench --site &lt;site&gt; restore &lt;db-file&gt;</code><br>
				This <b>overwrites the entire database</b>. All current data will be lost. Cannot be undone.<br>
				Use <b>Browse Backups ↑</b> to click-select files, or enter paths manually below.
			</div>
		</div>`);
		const $rsSiteRow = $('<div class="dkst-fld"><label class="dkst-lbl dkst-req">Target Site</label></div>').appendTo($rc);
		const $rsSite = siteSelRow($rsSiteRow, 'rs-site', 'select site');

		// File path rows with "Browse" button (opens Frappe dialog listing server backup files)
		function fileRow(id, lbl, ph, hint, required) {
			const $row = $(`<div class="dkst-fld" style="margin-top:12px">
				<label class="dkst-lbl${required?' dkst-req':''}">${lbl}</label>
				<div style="display:flex;gap:8px;align-items:center">
					<input class="dkst-inp" id="${id}" placeholder="${ph}" style="flex:1;font-family:monospace;font-size:12px">
					<button class="dkst-btn dkst-btn-s" data-browse="${id}" style="padding:5px 10px;font-size:12px;flex-shrink:0;white-space:nowrap" title="Browse server backup files">📂 Browse</button>
				</div>
				<span class="dkst-hint">${hint}</span>
			</div>`);
			return $row;
		}

		const $dbRow   = fileRow('rs-file','DB Backup File','sites/&lt;site&gt;/private/backups/&lt;date&gt;-database.sql.gz','Full server path to the <b>.sql.gz</b> database backup',true);
		const $privRow = fileRow('rs-priv','Private Files Backup (optional)','sites/&lt;site&gt;/private/backups/&lt;date&gt;-private-files.tar','Path to <b>-private-files.tar</b> — leave blank to skip',false);
		const $pubRow  = fileRow('rs-pub', 'Public Files Backup (optional)','sites/&lt;site&gt;/private/backups/&lt;date&gt;-files.tar','Path to <b>-files.tar</b> — leave blank to skip',false);
		$rc.append($dbRow).append($privRow).append($pubRow);

		$rc.append(`<div class="dkst-g2" style="margin-top:12px">
			<div class="dkst-fld"><label class="dkst-lbl">Reset Admin Password</label>
				<input class="dkst-inp" type="password" id="rs-apwd" placeholder="Leave blank to keep current">
				<span class="dkst-hint">Set a new admin password after restore completes</span></div>
			<div class="dkst-fld"><label class="dkst-lbl">DB Root Password</label>
				<input class="dkst-inp" type="password" id="rs-rpwd" placeholder="Required by some MariaDB setups">
				<span class="dkst-hint">Leave blank if bench manages DB credentials</span></div>
		</div>
		<div class="dkst-checks" style="margin-top:12px">
			<label class="dkst-chk"><input type="checkbox" id="rs-force"><span>Force restore — skip errors <span style="color:#9080b8;font-size:11px">(--force)</span></span></label>
			<label class="dkst-chk" style="color:#c0392b;font-weight:600"><input type="checkbox" id="rs-ok"><span>I understand all current data will be replaced</span></label>
		</div>`);

		const $t2 = smTerm($p);
		smBtns($rc, [{ lbl: 'Restore Site', cls: 'dkst-btn-r', fn: () => {
			if (!$('#rs-ok').is(':checked')) { frappe.throw('Check the confirmation box to proceed'); return; }
			const site = $rsSite.val();
			const file = $('#rs-file').val().trim();
			if (!site) { frappe.throw('Select a target site'); return; }
			if (!file) { frappe.throw('DB backup file path is required — use Browse Backups above to select'); return; }
			frappe.confirm(`<b>Restore site <code>${site}</code>?</b><br><br>
				DB file: <code style="font-size:11px;word-break:break-all">${file}</code><br><br>
				All current data will be <b>permanently replaced</b>. This cannot be undone.`, () => {
				smApi('frappe_devkit.api.site_manager.restore_site', {
					site, backup_file: file,
					with_private_files: $('#rs-priv').val().trim() || '',
					with_public_files:  $('#rs-pub').val().trim()  || '',
					admin_password:     $('#rs-apwd').val().trim() || '',
					force: $('#rs-force').is(':checked') ? 1 : 0,
				}, $t2);
			});
		}}]);

		// ── Browse dialog: lists server backup files for a site ──
		$rc.on('click', '[data-browse]', function() {
			const targetId = $(this).data('browse');
			const site = $rsSite.val();
			if (!site) { frappe.throw('Select a site first to browse its backups'); return; }

			// determine filter type from target field
			const isDb   = targetId === 'rs-file';
			const isPriv = targetId === 'rs-priv';
			const isPub  = targetId === 'rs-pub';

			const doLoad = (bks) => {
				const filtered = bks.filter(b => {
					if (isDb)   return b.type === 'database';
					if (isPriv) return b.name.includes('private');
					if (isPub)  return b.name.includes('files') && !b.name.includes('private') && b.type !== 'database';
					return true;
				});

				const d = new frappe.ui.Dialog({
					title: `Browse Backup Files — ${site}`,
					size: 'large',
				});
				const $body = d.$wrapper.find('.modal-body');
				if (!filtered.length) {
					$body.html('<div style="padding:20px;color:#9080b8;text-align:center">No matching backup files found for this site.</div>');
				} else {
					const $tbl = $(`<table style="width:100%;border-collapse:collapse;font-size:12.5px">
						<thead><tr style="background:#f3f0fb">
							<th style="text-align:left;padding:8px 10px;border-bottom:1px solid #e0d8f8">File Name</th>
							<th style="text-align:right;padding:8px 10px;border-bottom:1px solid #e0d8f8;white-space:nowrap">Size</th>
							<th style="text-align:right;padding:8px 10px;border-bottom:1px solid #e0d8f8;white-space:nowrap">Date</th>
							<th style="padding:8px 10px;border-bottom:1px solid #e0d8f8"></th>
						</tr></thead><tbody></tbody>
					</table>`).appendTo($body);
					filtered.forEach(b => {
						const $tr = $(`<tr style="border-bottom:1px solid #f0ecf8;cursor:pointer" class="bk-file-row">
							<td style="padding:8px 10px;font-family:monospace;font-size:11px;color:#5c4da8;word-break:break-all">${b.name}</td>
							<td style="padding:8px 10px;text-align:right;white-space:nowrap;color:#7a70a8">${b.size}</td>
							<td style="padding:8px 10px;text-align:right;white-space:nowrap;color:#7a70a8">${b.date}</td>
							<td style="padding:8px 10px"><button class="dkst-btn dkst-btn-p" style="font-size:11px;padding:3px 12px">Use</button></td>
						</tr>`).appendTo($tbl.find('tbody'));
						$tr.find('button, td').on('click', () => {
							$(`#${targetId}`).val(b.path);
							d.hide();
						});
					});
				}
				d.show();
			};

			if (_bkCache[site]) {
				doLoad(_bkCache[site]);
			} else {
				frappe.call({ method: 'frappe_devkit.api.site_manager.list_backups', args: { site },
					callback: r => { _bkCache[site] = r.message?.backups || []; doLoad(_bkCache[site]); }
				});
			}
		});
	};

	// ── Site Config ──────────────────────────────────
	PANELS.site_config = function($p) {
		$p.append(phdr('Site Config', 'Read, set and remove keys in site_config.json.', icoSliders(20)));
		$p.append(info('Config file location: <span class="dkst-code">sites/&lt;site&gt;/site_config.json</span>. Changes take effect immediately without restart.'));

		// Read config — auto-loads when site is selected
		const $rc = smCard($p, 'Read Config');
		const $cfgSiteRow = $('<div class="dkst-fld"><label class="dkst-lbl dkst-req">Site</label></div>').appendTo($rc);
		const $cfgSite = siteSelRow($cfgSiteRow, 'cfg-site', 'select site');
		const $cfgTable = $('<div id="cfg-table" style="margin-top:14px"></div>').appendTo($rc);
		$cfgSite.on('change', function() {
			const site = this.value; if (!site) { $cfgTable.empty(); return; }
			$cfgTable.html('<div style="color:#9080b8;font-size:12px">Loading…</div>');
			frappe.call({ method: 'frappe_devkit.api.site_manager.get_site_config', args: { site },
				callback: r => {
					const cfg = r.message?.config || {};
					$cfgTable.empty();
					const entries = Object.entries(cfg);
					if (!entries.length) { $cfgTable.html('<div style="color:#9080b8;font-size:12px">No config keys found.</div>'); return; }
					const $tbl = $('<table class="dkst-tbl"><thead><tr><th>Key</th><th>Value</th></tr></thead><tbody></tbody></table>').appendTo($cfgTable);
					entries.forEach(([k, v]) => $tbl.find('tbody').append(`<tr>
						<td style="font-family:monospace;color:#5c4da8;font-weight:600">${k}</td>
						<td style="font-family:monospace;font-size:12px;color:#1e1a2e">${JSON.stringify(v)}</td>
					</tr>`));
				}
			});
		});

		// Set/Remove config
		const $sc = smCard($p, 'Set / Remove Config Key');
		$sc.append(`<div style="font-size:12px;color:#7a70a8;margin-bottom:12px">
			Equivalent: <span class="dkst-code">bench --site &lt;site&gt; set-config &lt;key&gt; &lt;value&gt;</span>
		</div>`);
		const $setSiteRow = $('<div class="dkst-fld"><label class="dkst-lbl dkst-req">Site</label></div>').appendTo($sc);
		const $setSite = siteSelRow($setSiteRow, 'set-site', 'select site');
		$sc.append(`<div class="dkst-g2" style="margin-top:12px">
			<div class="dkst-fld"><label class="dkst-lbl dkst-req">Key</label>
				<input class="dkst-inp" id="set-key" placeholder="e.g. max_file_size, developer_mode">
				<span class="dkst-hint">Config key name (snake_case)</span></div>
			<div class="dkst-fld"><label class="dkst-lbl">Value</label>
				<input class="dkst-inp" id="set-val" placeholder="e.g. 10485760, 1, true">
				<span class="dkst-hint">Leave blank when removing</span></div>
			<div class="dkst-fld"><label class="dkst-lbl">Value Type</label>
				<select class="dkst-sel" id="set-type">
					<option value="string">String</option>
					<option value="int">Integer</option>
					<option value="bool">Boolean (0 / 1)</option>
					<option value="json">JSON object</option>
				</select></div>
		</div>`);
		const $t3 = smTerm($p);
		smBtns($sc, [
			{ lbl: 'Set Config Key', cls: 'dkst-btn-p', fn: () => {
				const site = $setSite.val();
				const key = smGv('set-key'); const val = smGv('set-val');
				if (!site) { frappe.throw('Select a site'); return; }
				if (!key)  { frappe.throw('Key is required'); return; }
				if (!val)  { frappe.throw('Value is required — use Remove to delete a key'); return; }
				smApi('frappe_devkit.api.site_manager.set_site_config', {
					site, key, value: val, value_type: $('#set-type').val()
				}, $t3);
			}},
			{ lbl: 'Remove Key', cls: 'dkst-btn-r', fn: () => {
				const site = $setSite.val();
				const key = smGv('set-key');
				if (!site) { frappe.throw('Select a site'); return; }
				if (!key)  { frappe.throw('Key is required'); return; }
				frappe.confirm(`Remove key <b>${key}</b> from <b>${site}</b>?`, () => {
					smApi('frappe_devkit.api.site_manager.remove_site_config', { site, key }, $t3);
				});
			}},
		]);

		// Common site config (sites/common_site_config.json)
		const $cc = smCard($p, 'Common Site Config');
		$cc.append('<div style="font-size:12px;color:#7a70a8;margin-bottom:10px">Shared by all sites — <span class="dkst-code">sites/common_site_config.json</span></div>');
		const $ccd = $('<div style="color:#9080b8;font-size:12px">Click <b>Load</b> to view.</div>').appendTo($cc);
		smBtns($cc, [{ lbl: 'Load Common Config', cls: 'dkst-btn-s', fn: () => {
			$ccd.html('<div style="color:#9080b8;font-size:12px">Loading…</div>');
			frappe.call({ method: 'frappe_devkit.api.site_manager.get_common_config',
				callback: r => {
					const cfg = r.message?.config || {};
					$ccd.empty();
					const entries = Object.entries(cfg);
					if (!entries.length) { $ccd.html('<div style="color:#9080b8;font-size:12px">No common config keys.</div>'); return; }
					const $tbl = $('<table class="dkst-tbl"><thead><tr><th>Key</th><th>Value</th></tr></thead><tbody></tbody></table>').appendTo($ccd);
					entries.forEach(([k,v]) => $tbl.find('tbody').append(`<tr>
						<td style="font-family:monospace;color:#5c4da8;font-weight:600">${k}</td>
						<td style="font-family:monospace;font-size:12px">${JSON.stringify(v)}</td>
					</tr>`));
				}
			});
		}}]);
	};

	// ── Site Apps ──────────────────────────────────
	PANELS.site_apps = function($p) {
		$p.append(phdr('Install / Remove Apps', 'Install or uninstall apps on any site.', icoPackage(20)));
		$p.append(info('Install bench apps on a site or remove them. Apps must be fetched into the bench first via <span class="dkst-code">bench get-app &lt;app&gt;</span>.'));
		const $c = smCard($p, 'App on Site');
		$c.append(`<div style="font-size:12px;color:#7a70a8;margin-bottom:12px">
			<span class="dkst-code">bench --site &lt;site&gt; install-app &lt;app&gt;</span>
			<span style="color:#9080b8"> &nbsp;·&nbsp; </span>
			<span class="dkst-code">bench --site &lt;site&gt; uninstall-app &lt;app&gt;</span>
		</div>`);

		const $siteRow = $('<div class="dkst-fld"><label class="dkst-lbl dkst-req">Site</label></div>').appendTo($c);
		const $saSite = siteSelRow($siteRow, 'sa-site', 'select site');

		$c.append(`<div class="dkst-fld" style="margin-top:12px">
			<div style="display:flex;align-items:center;justify-content:space-between;gap:8px;margin-bottom:5px;">
				<label class="dkst-lbl dkst-req" style="margin:0;">App</label>
				<button class="dkst-ce-link" data-app-sel="sa-app" title="Open in DevKit Code Editor">⌨ Open in Editor ↗</button>
			</div>
			<select class="dkst-sel" id="sa-app"><option value="">— loading apps… —</option></select>
			<span class="dkst-hint">Apps currently fetched in this bench</span></div>`);

		$c.append(`<div class="dkst-checks" style="margin-top:12px">
			<label class="dkst-chk"><input type="checkbox" id="sa-force"><span>Force reinstall (<code>--force</code>)</span></label>
			<label class="dkst-chk"><input type="checkbox" id="sa-dry"><span>Dry run — preview uninstall only</span></label>
		</div>
		<div id="sa-installed" style="margin-top:14px"></div>`);

		frappe.call({ method: 'frappe_devkit.api.app_builder.get_bench_apps',
			callback: r => {
				const $appSel = $c.find('#sa-app').empty().append('<option value="">— select app —</option>');
				(r.message?.apps || []).forEach(a =>
					$appSel.append(`<option value="${a.app}">${a.app} (${a.version})</option>`)
				);
			}
		});
		$saSite.on('change', function() {
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
				const site = $saSite.val(); const app = $('#sa-app').val();
				if (!site||!app) { frappe.throw('Site and App required'); return; }
				smApi('frappe_devkit.api.app_builder.install_app_on_site', {
					app_name: app, site, force: $('#sa-force').is(':checked') ? 1 : 0
				}, $t);
			}},
			{ lbl: 'Uninstall App', cls: 'dkst-btn-r', fn: () => {
				const site = $saSite.val(); const app = $('#sa-app').val();
				if (!site||!app) { frappe.throw('Site and App required'); return; }
				frappe.confirm(`Uninstall <b>${app}</b> from <b>${site}</b>?<br>
					This removes all app data and cannot be undone.`, () => {
					smApi('frappe_devkit.api.app_builder.uninstall_app_from_site', {
						app_name: app, site, dry_run: $('#sa-dry').is(':checked') ? 1 : 0
					}, $t);
				});
			}},
		]);
	};

	// ── Site Operations ──────────────────────────────────
	PANELS.site_ops = function($p) {
		$p.append(phdr('Operations', 'Migrate, cache, scheduler, maintenance, password, execute, drop.', icoTools(20)));
		$p.append(info('All operations below target the selected site. Equivalent bench commands are shown in the terminal output.'));

		// Global site selector
		const $sel = smCard($p, 'Target Site');
		const $siteRow = $('<div class="dkst-fld"><label class="dkst-lbl dkst-req">Site</label></div>').appendTo($sel);
		const $opsSite = siteSelRow($siteRow, 'ops-site', 'select site');
		function gsite() { const s = $opsSite.val(); if (!s) { frappe.throw('Select a site first'); return ''; } return s; }

		// Sub tabs
		const $tabs = $(`<div class="dkst-stabs">
			<div class="dkst-stab active" data-t="mig">Migrate</div>
			<div class="dkst-stab" data-t="cch">Cache</div>
			<div class="dkst-stab" data-t="sch">Scheduler</div>
			<div class="dkst-stab" data-t="mnt">Maintenance</div>
			<div class="dkst-stab" data-t="pwd">Admin Password</div>
			<div class="dkst-stab" data-t="exc">Execute</div>
			<div class="dkst-stab" data-t="bld">Build & Restart</div>
		<div class="dkst-stab" data-t="drp" style="color:#c0392b">Drop Site</div>
		</div>`).appendTo($p);
		const $pp = $('<div></div>').appendTo($p);
		function mkSub(id) {
			return $(`<div class="dkst-spanel ${id==='mig'?'active':''}" data-t="${id}"></div>`).appendTo($pp);
		}

		// Migrate
		const $mig = mkSub('mig');
		const $mc = smCard($mig, 'Migrate Site');
		$mc.append(`<div style="font-size:12px;color:#7a70a8;margin-bottom:10px">
			Equivalent: <span class="dkst-code">bench --site &lt;site&gt; migrate</span>
			<span style="color:#9080b8"> &nbsp;·&nbsp; Runs DB patches, syncs doctypes, rebuilds assets</span>
		</div>`);
		$mc.append('<div class="dkst-checks"><label class="dkst-chk"><input type="checkbox" id="mig-skip"><span>Skip failing patches (<code>--skip-failing-patches</code>)</span></label></div>');
		const $mt = smTerm($mig);
		smBtns($mc, [{ lbl: 'Run Migrate', cls: 'dkst-btn-p', fn: () => {
			const site = gsite(); if (!site) return;
			smApi('frappe_devkit.api.site_manager.migrate_site', { site, skip_failing: $('#mig-skip').is(':checked')?1:0 }, $mt);
		}}]);

		// Cache
		const $cch = mkSub('cch');
		const $cc = smCard($cch, 'Cache & Default Site');
		$cc.append(`<div style="font-size:12px;color:#7a70a8;margin-bottom:10px">
			<span class="dkst-code">bench --site &lt;site&gt; clear-cache</span>
			<span style="color:#9080b8"> &nbsp;·&nbsp; </span>
			<span class="dkst-code">bench --site &lt;site&gt; clear-website-cache</span>
			<span style="color:#9080b8"> &nbsp;·&nbsp; </span>
			<span class="dkst-code">bench use &lt;site&gt;</span>
		</div>`);
		const $ct = smTerm($cch);
		smBtns($cc, [
			{ lbl: 'Clear Cache',         cls: 'dkst-btn-p', fn: () => { const s=gsite(); if(s) smApi('frappe_devkit.api.site_manager.clear_site_cache',    { site: s }, $ct); } },
			{ lbl: 'Clear Website Cache', cls: 'dkst-btn-s', fn: () => { const s=gsite(); if(s) smApi('frappe_devkit.api.site_manager.clear_website_cache', { site: s }, $ct); } },
			{ lbl: 'Set as Default Site', cls: 'dkst-btn-s', fn: () => { const s=gsite(); if(s) smApi('frappe_devkit.api.site_manager.use_site',            { site: s }, $ct); } },
		]);

		// Scheduler
		const $sch = mkSub('sch');
		const $sc = smCard($sch, 'Scheduler Control');
		$sc.append(`<div style="font-size:12.5px;color:#4a4470;margin-bottom:12px;line-height:1.7">
			Equivalent: <span class="dkst-code">bench --site &lt;site&gt; scheduler &lt;action&gt;</span><br>
			<span class="dkst-code">enable/disable</span> — permanent &nbsp;·&nbsp;
			<span class="dkst-code">resume/suspend</span> — until restart &nbsp;·&nbsp;
			<span class="dkst-code">run-jobs</span> — trigger immediately
		</div>`);
		const $st = smTerm($sch);
		smBtns($sc, [
			{ lbl: 'Status',   cls: 'dkst-btn-s', fn: () => { const s=gsite(); if(s) smApi('frappe_devkit.api.site_manager.scheduler_action', { site: s, action: 'status' },   $st); } },
			{ lbl: 'Enable',   cls: 'dkst-btn-g', fn: () => { const s=gsite(); if(s) smApi('frappe_devkit.api.site_manager.scheduler_action', { site: s, action: 'enable' },   $st); } },
			{ lbl: 'Disable',  cls: 'dkst-btn-r', fn: () => { const s=gsite(); if(s) smApi('frappe_devkit.api.site_manager.scheduler_action', { site: s, action: 'disable' },  $st); } },
			{ lbl: 'Resume',   cls: 'dkst-btn-g', fn: () => { const s=gsite(); if(s) smApi('frappe_devkit.api.site_manager.scheduler_action', { site: s, action: 'resume' },   $st); } },
			{ lbl: 'Suspend',  cls: 'dkst-btn-s', fn: () => { const s=gsite(); if(s) smApi('frappe_devkit.api.site_manager.scheduler_action', { site: s, action: 'suspend' },  $st); } },
			{ lbl: 'Run Jobs', cls: 'dkst-btn-p', fn: () => { const s=gsite(); if(s) smApi('frappe_devkit.api.site_manager.scheduler_action', { site: s, action: 'run-jobs' }, $st); } },
		]);

		// Maintenance
		const $mnt = mkSub('mnt');
		const $mn = smCard($mnt, 'Maintenance Mode');
		$mn.append(`<div style="font-size:12.5px;color:#4a4470;margin-bottom:14px;line-height:1.7">
			Equivalent: <span class="dkst-code">bench --site &lt;site&gt; set-maintenance-mode on|off</span><br>
			While ON, visitors see a maintenance page. Administrators can still log in.
		</div>`);
		const $mnt2 = smTerm($mnt);
		smBtns($mn, [
			{ lbl: 'Enable Maintenance',  cls: 'dkst-btn-r', fn: () => { const s=gsite(); if(s) smApi('frappe_devkit.api.site_manager.set_maintenance_mode', { site: s, enable: 1 }, $mnt2); } },
			{ lbl: 'Disable Maintenance', cls: 'dkst-btn-g', fn: () => { const s=gsite(); if(s) smApi('frappe_devkit.api.site_manager.set_maintenance_mode', { site: s, enable: 0 }, $mnt2); } },
		]);

		// Admin Password
		const $pwd = mkSub('pwd');
		const $pc = smCard($pwd, 'Reset Admin Password');
		$pc.append(`<div style="font-size:12px;color:#7a70a8;margin-bottom:12px">
			Equivalent: <span class="dkst-code">bench --site &lt;site&gt; set-admin-password &lt;new-password&gt;</span>
		</div>`);
		$pc.append('<div class="dkst-g2"><div class="dkst-fld"><label class="dkst-lbl dkst-req">New Password</label><input class="dkst-inp" type="password" id="pwd-new" placeholder="Min 6 characters"></div><div class="dkst-fld"><label class="dkst-lbl dkst-req">Confirm</label><input class="dkst-inp" type="password" id="pwd-cf" placeholder="Repeat password"></div></div>');
		const $pt = smTerm($pwd);
		smBtns($pc, [{ lbl: 'Set Password', cls: 'dkst-btn-p', fn: () => {
			const site = gsite(); if (!site) return;
			const p1 = $('#pwd-new').val().trim(); const p2 = $('#pwd-cf').val().trim();
			if (!p1 || p1.length < 6) { frappe.throw('Password must be at least 6 characters'); return; }
			if (p1 !== p2) { frappe.throw('Passwords do not match'); return; }
			smApi('frappe_devkit.api.site_manager.set_admin_password', { site, new_password: p1 }, $pt);
		}}]);

		// Execute
		const $exc = mkSub('exc');
		const $ec = smCard($exc, 'Execute Python Expression');
		$ec.append(`<div style="font-size:12.5px;color:#4a4070;margin-bottom:10px;line-height:1.7">
			Equivalent: <span class="dkst-code">bench --site &lt;site&gt; execute &lt;expression&gt;</span><br>
			Runs in the site context with full Frappe/ERPNext access. Destructive operations are blocked.
		</div>`);
		$ec.append(`<div class="dkst-fld"><label class="dkst-lbl dkst-req">Python Expression</label>
			<textarea id="exc-sc" style="display:none">frappe.db.count("Sales Invoice", {"status": "Open"})</textarea>
			<div id="exc-sc-mc" style="height:180px;border:1px solid #d0c8e8;border-radius:4px;margin-bottom:4px"></div>
			<span class="dkst-hint">Any Python expression: frappe.db.get_value(), frappe.get_doc(), frappe.cache().get_value(), etc.</span>
		</div>`);
		_mcLoad(mc => {
			const _excMc = _mcCreate($exc.find('#exc-sc-mc'), 'python', 'frappe.db.count("Sales Invoice", {"status": "Open"})');
			_excMc.onDidChangeModelContent(() => { $('#exc-sc').val(_excMc.getValue()); });
			$('#exc-sc').val(_excMc.getValue());
		});
		const $et = smTerm($exc);
		smBtns($ec, [{ lbl: 'Execute', cls: 'dkst-btn-p', fn: () => {
			const site = gsite(); if (!site) return;
			const sc = smGv('exc-sc'); if (!sc) { frappe.throw('Expression required'); return; }
			smApi('frappe_devkit.api.site_manager.execute_script', { site, script: sc }, $et);
		}}]);

		// Build & Restart
		const $bld = mkSub('bld');
		const $bc = smCard($bld, 'Build Assets & Restart Workers');
		$bc.append(`<div style="font-size:12px;color:#7a70a8;margin-bottom:12px;line-height:1.7">
			<span class="dkst-code">bench build</span> — rebuild JS/CSS assets &nbsp;·&nbsp;
			<span class="dkst-code">bench build --app &lt;app&gt;</span> — single app &nbsp;·&nbsp;
			<span class="dkst-code">bench restart</span> — reload workers
		</div>`);
		$bc.append(`<div class="dkst-g2" style="margin-bottom:12px">
			<div class="dkst-fld"><label class="dkst-lbl">App (optional — leave blank for all apps)</label>
			<input class="dkst-inp" id="bld-app" placeholder="e.g. frappe, erpnext, my_app"></div>
		</div>`);
		const $bt = smTerm($bld);
		smBtns($bc, [
			{ lbl: 'Build Assets',     cls: 'dkst-btn-p', fn: () => {
				const app = $('#bld-app').val().trim();
				smApi('frappe_devkit.api.site_manager.build_assets', { app_name: app }, $bt);
			}},
			{ lbl: 'Restart Workers',  cls: 'dkst-btn-s', fn: () => {
				smApi('frappe_devkit.api.site_manager.restart_workers', {}, $bt);
			}},
		]);

		// Drop Site
		const $drp = mkSub('drp');
		const $dc = smCard($drp);
		$dc.append(`<div style="background:#fde8e6;border:1px solid #e8a8a0;border-radius:6px;padding:16px 18px;margin-bottom:16px">
			<div style="font-size:14px;font-weight:700;color:#c0392b;margin-bottom:6px">⚠ Danger Zone — Irreversible</div>
			<div style="font-size:12.5px;color:#7a2020;line-height:1.7">
				Equivalent: <code>bench drop-site &lt;site&gt;</code><br>
				Permanently deletes the MariaDB database and all files in <code>sites/&lt;site&gt;/</code>.
				<b>Cannot be undone.</b> Always take a backup first.
			</div>
		</div>
		<div class="dkst-g2"><div class="dkst-fld"><label class="dkst-lbl">MariaDB Root Password</label>
			<input class="dkst-inp" type="password" id="drp-rpwd" placeholder="If required by your MariaDB setup">
			<span class="dkst-hint">Leave blank if bench manages DB credentials automatically</span></div></div>
		<div class="dkst-checks" style="margin-top:12px">
			<label class="dkst-chk"><input type="checkbox" id="drp-force"><span>Force drop — skip errors (<code>--force</code>)</span></label>
			<label class="dkst-chk" style="color:#c0392b;font-weight:600"><input type="checkbox" id="drp-ok"><span>I understand this action is permanent and irreversible</span></label>
		</div>`);
		const $dt = smTerm($drp);
		smBtns($dc, [{ lbl: 'Drop Site', cls: 'dkst-btn-r', fn: () => {
			if (!$('#drp-ok').is(':checked')) { frappe.throw('Check the confirmation box to proceed'); return; }
			const site = gsite(); if (!site) return;
			frappe.confirm(`<b>PERMANENTLY DROP site <code>${site}</code>?</b><br><br>
				The database and all site files will be deleted. This cannot be undone.`, () => {
				smApi('frappe_devkit.api.site_manager.drop_site', {
					site, force: $('#drp-force').is(':checked')?1:0,
					root_password: $('#drp-rpwd').val().trim(),
				}, $dt);
			});
		}}]);

		// Sub-tab switching
		$tabs.on('click', '.dkst-stab', function() {
			const t = $(this).data('t');
			$tabs.find('.dkst-stab').removeClass('active'); $(this).addClass('active');
			$pp.find('.dkst-spanel').removeClass('active'); $pp.find(`[data-t="${t}"]`).addClass('active');
		});
	};

	/* ══════════════════════════════════════════════════════════════════
	   QUERY EDITOR
	   ══════════════════════════════════════════════════════════════════ */
	PANELS.query_editor = function($p) {
		// Full-height layout — override panel padding
		$p.css({ padding: 0, display: 'flex', flexDirection: 'column', overflow: 'hidden', height: '100%' });

		/* ── state ── */
		let _qeSite = '', _tables = [], _queryHistory = [], _abortCtrl = null;

		/* ── SQL Snippets (grouped) ── */
		const SNIPPET_GROUPS = [
			{ label: '⚡ Basic', items: {
				'SELECT *':              (t) => `SELECT * FROM \`${t||'tabDocType'}\` LIMIT 50`,
				'SELECT fields':         (t) => `SELECT name, creation, modified, owner, modified_by\nFROM \`${t||'tabDocType'}\`\nWHERE 1=1\nORDER BY creation DESC\nLIMIT 50`,
				'COUNT rows':            (t) => `SELECT COUNT(*) AS total FROM \`${t||'tabDocType'}\``,
				'DESCRIBE table':        (t) => `DESCRIBE \`${t||'tabDocType'}\``,
				'SHOW TABLES':           ()  => `SHOW TABLES`,
				'SHOW FULL TABLES':      ()  => `SHOW FULL TABLES`,
				'SHOW INDEXES':          (t) => `SHOW INDEXES FROM \`${t||'tabDocType'}\``,
				'SHOW CREATE TABLE':     (t) => `SHOW CREATE TABLE \`${t||'tabDocType'}\``,
			}},
			{ label: '🔗 Joins & Filters', items: {
				'INNER JOIN':            ()  => `SELECT a.name, b.fieldname, b.fieldtype\nFROM \`tabDocType\` a\nINNER JOIN \`tabDocField\` b ON b.parent = a.name\nWHERE 1=1\nLIMIT 50`,
				'LEFT JOIN':             ()  => `SELECT a.name, b.name AS child\nFROM \`tabDocType\` a\nLEFT JOIN \`tabDocField\` b ON b.parent = a.name\nLIMIT 50`,
				'WHERE + LIKE':          (t) => `SELECT * FROM \`${t||'tabDocType'}\`\nWHERE name LIKE '%keyword%'\nLIMIT 50`,
				'WHERE date range':      (t) => `SELECT * FROM \`${t||'tabDocType'}\`\nWHERE creation BETWEEN '2024-01-01' AND '2024-12-31'\nORDER BY creation DESC`,
				'WHERE IN list':         (t) => `SELECT * FROM \`${t||'tabDocType'}\`\nWHERE name IN ('val1','val2','val3')`,
				'CASE expression':       ()  => `SELECT name,\n  CASE docstatus\n    WHEN 0 THEN 'Draft'\n    WHEN 1 THEN 'Submitted'\n    WHEN 2 THEN 'Cancelled'\n    ELSE 'Unknown'\n  END AS status_label\nFROM \`tabSales Invoice\`\nLIMIT 50`,
			}},
			{ label: '📊 Aggregation', items: {
				'GROUP BY count':        (t) => `SELECT owner, COUNT(*) AS cnt\nFROM \`${t||'tabDocType'}\`\nGROUP BY owner\nORDER BY cnt DESC\nLIMIT 20`,
				'SUM by field':          (t) => `SELECT owner, SUM(grand_total) AS total\nFROM \`${t||'tabSales Invoice'}\`\nGROUP BY owner\nORDER BY total DESC`,
				'Date histogram':        (t) => `SELECT DATE(creation) AS day, COUNT(*) AS cnt\nFROM \`${t||'tabDocType'}\`\nGROUP BY day\nORDER BY day DESC\nLIMIT 30`,
				'Monthly summary':       (t) => `SELECT DATE_FORMAT(creation,'%Y-%m') AS month, COUNT(*) AS cnt\nFROM \`${t||'tabDocType'}\`\nGROUP BY month\nORDER BY month DESC`,
				'HAVING filter':         (t) => `SELECT owner, COUNT(*) AS cnt\nFROM \`${t||'tabDocType'}\`\nGROUP BY owner\nHAVING cnt > 10\nORDER BY cnt DESC`,
				'DISTINCT values':       (t) => `SELECT DISTINCT owner FROM \`${t||'tabDocType'}\`\nORDER BY owner`,
			}},
			{ label: '🌿 Frappe Core', items: {
				'DocType fields':        (t) => `SELECT fieldname, label, fieldtype, options, reqd, in_list_view\nFROM \`tabDocField\`\nWHERE parent='${t||'Sales Invoice'}'\nORDER BY idx`,
				'Recent docs':           (t) => `SELECT name, creation, owner, docstatus, modified_by\nFROM \`tab${t||'Sales Invoice'}\`\nORDER BY creation DESC\nLIMIT 20`,
				'Custom fields':         (t) => `SELECT name, dt, fieldname, label, fieldtype, insert_after\nFROM \`tabCustom Field\`\nWHERE dt='${t||'Sales Invoice'}'\nORDER BY idx`,
				'Print formats':         (t) => `SELECT name, doc_type, module, disabled, standard\nFROM \`tabPrint Format\`\nWHERE doc_type='${t||'Sales Invoice'}'`,
				'DocType list':          ()  => `SELECT name, module, issingle, istable, is_submittable, custom\nFROM \`tabDocType\`\nORDER BY name\nLIMIT 100`,
				'Error log':             ()  => `SELECT name, creation, method, error\nFROM \`tabError Log\`\nORDER BY creation DESC\nLIMIT 30`,
				'Activity log':          ()  => `SELECT creation, owner, subject, reference_doctype, reference_name\nFROM \`tabActivity Log\`\nORDER BY creation DESC\nLIMIT 30`,
				'Email queue':           ()  => `SELECT name, sender, recipients, status, creation, error\nFROM \`tabEmail Queue\`\nORDER BY creation DESC\nLIMIT 30`,
				'Scheduled jobs':        ()  => `SELECT name, method, status, scheduled_time, creation\nFROM \`tabScheduled Job Log\`\nORDER BY creation DESC\nLIMIT 30`,
				'Users & last login':    ()  => `SELECT name, full_name, email, enabled, last_login\nFROM \`tabUser\`\nWHERE name NOT IN ('Administrator','Guest')\nORDER BY last_login DESC`,
				'User roles':            ()  => `SELECT parent AS user, role\nFROM \`tabHas Role\`\nWHERE parenttype='User'\nORDER BY parent, role`,
				'Workflows':             ()  => `SELECT name, document_type, is_active\nFROM \`tabWorkflow\`\nORDER BY document_type`,
				'Version/audit log':     ()  => `SELECT name, ref_doctype, docname, creation, owner\nFROM \`tabVersion\`\nORDER BY creation DESC\nLIMIT 30`,
				'DocType permissions':   (t) => `SELECT role, permlevel, \`read\`, \`write\`, \`create\`, \`delete\`, submit, cancel\nFROM \`tabDocPerm\`\nWHERE parent='${t||'Sales Invoice'}'`,
			}},
			{ label: '💼 ERPNext', items: {
				'Open Sales Orders':     ()  => `SELECT name, customer, transaction_date, grand_total, status\nFROM \`tabSales Order\`\nWHERE status NOT IN ('Cancelled','Closed')\nORDER BY creation DESC\nLIMIT 50`,
				'Overdue invoices':      ()  => `SELECT name, customer, due_date, outstanding_amount\nFROM \`tabSales Invoice\`\nWHERE docstatus=1 AND outstanding_amount > 0 AND due_date < CURDATE()\nORDER BY due_date\nLIMIT 50`,
				'Pending POs':           ()  => `SELECT name, supplier, transaction_date, grand_total, status\nFROM \`tabPurchase Order\`\nWHERE status NOT IN ('Cancelled','Closed')\nORDER BY creation DESC\nLIMIT 30`,
				'Stock summary':         ()  => `SELECT item_code, warehouse, actual_qty, valuation_rate,\n  actual_qty*valuation_rate AS stock_value\nFROM \`tabBin\`\nWHERE actual_qty != 0\nORDER BY stock_value DESC\nLIMIT 50`,
				'Item prices':           ()  => `SELECT item_code, price_list, price_list_rate, currency\nFROM \`tabItem Price\`\nWHERE price_list='Standard Selling'\nORDER BY item_code\nLIMIT 50`,
				'GL entries':            ()  => `SELECT posting_date, account, debit, credit, voucher_type, voucher_no\nFROM \`tabGL Entry\`\nWHERE is_cancelled=0\nORDER BY posting_date DESC\nLIMIT 50`,
				'Customer balances':     ()  => `SELECT party, SUM(debit-credit) AS balance\nFROM \`tabGL Entry\`\nWHERE party_type='Customer' AND is_cancelled=0\nGROUP BY party\nHAVING balance != 0\nORDER BY balance DESC\nLIMIT 50`,
				'Top customers':         ()  => `SELECT customer, SUM(grand_total) AS revenue\nFROM \`tabSales Invoice\`\nWHERE docstatus=1\nGROUP BY customer\nORDER BY revenue DESC\nLIMIT 20`,
			}},
			{ label: '⚙️ Performance & Info', items: {
				'Table sizes':           ()  => `SELECT table_name,\n  ROUND(data_length/1024/1024,2) AS data_mb,\n  ROUND(index_length/1024/1024,2) AS index_mb,\n  table_rows\nFROM information_schema.TABLES\nWHERE table_schema = DATABASE()\nORDER BY data_length DESC\nLIMIT 30`,
				'EXPLAIN query':         (t) => `EXPLAIN SELECT * FROM \`${t||'tabDocType'}\` WHERE name = 'test'`,
				'Show processlist':      ()  => `SHOW PROCESSLIST`,
				'Show status':           ()  => `SHOW STATUS WHERE Variable_name IN\n('Uptime','Questions','Threads_connected','Slow_queries','Open_tables')`,
				'Character set':         ()  => `SHOW VARIABLES LIKE '%character%'`,
				'InnoDB status':         ()  => `SHOW VARIABLES LIKE 'innodb%'`,
				'Max connections':       ()  => `SHOW VARIABLES LIKE '%max_connections%'`,
			}},
		];

		/* ── toolbar ── */
		const $toolbar = $(`<div class="dkqe-toolbar"></div>`).appendTo($p);

		// Site selector
		$toolbar.append(`<select class="dkqe-site-sel" id="qe-site" title="Target site"></select>`);
		const $qeSiteSel = $toolbar.find('#qe-site');
		$qeSiteSel.append('<option value="">— select site —</option>');

		// Load sites
		frappe.call({ method: 'frappe_devkit.api.site_manager.list_sites', callback: r => {
			const sites = r.message?.sites || [];
			sites.forEach(s => $qeSiteSel.append(`<option value="${s.site}">${s.site}</option>`));
			// Pre-select current site
			const cur = frappe.boot?.sitename || '';
			if (cur) $qeSiteSel.val(cur).trigger('change');
		}});

		$toolbar.append(`<div class="dkqe-tb-sep"></div>`);

		// Run button
		const $runBtn = $(`<button class="dkqe-run-btn" id="qe-run" title="Run query (Ctrl+Enter)">${icoPlay(14)}&nbsp;Run</button>`).appendTo($toolbar);

		// Limit
		$toolbar.append(`<select class="dkqe-limit-sel" id="qe-limit" title="Max rows">
			<option value="50">50 rows</option>
			<option value="200">200 rows</option>
			<option value="500" selected>500 rows</option>
			<option value="1000">1000 rows</option>
			<option value="5000">5000 rows</option>
		</select>`);

		// Allow write toggle
		$toolbar.append(`<label style="display:flex;align-items:center;gap:5px;font-size:12px;color:#7a70a8;cursor:pointer;user-select:none">
			<input type="checkbox" id="qe-allow-write" style="accent-color:#c0392b"> Allow write
		</label>`);

		$toolbar.append(`<div class="dkqe-tb-sep"></div>`);

		// Snippets dropdown (grouped)
		const $snippetBtn = $(`<div style="position:relative;display:inline-block">
			<button class="dkqe-snippet-btn" id="qe-snippets">⚡ Snippets ▾</button>
			<div id="qe-snippet-menu" style="display:none;position:absolute;top:100%;left:0;z-index:999;background:#fff;border:1px solid #d0c8e8;border-radius:6px;box-shadow:0 4px 16px rgba(0,0,0,.18);min-width:260px;padding:4px 0;max-height:480px;overflow-y:auto;scrollbar-width:thin"></div>
		</div>`).appendTo($toolbar);
		const $snMenu = $snippetBtn.find('#qe-snippet-menu');

		// Build grouped snippet menu
		SNIPPET_GROUPS.forEach(group => {
			$(`<div class="dkqe-sn-group-hdr">${group.label}</div>`).appendTo($snMenu);
			Object.keys(group.items).forEach(k => {
				const fn = group.items[k];
				$(`<div class="dkqe-history-item" style="padding:6px 14px;font-size:12px">${k}</div>`)
					.appendTo($snMenu)
					.on('click', () => {
						const active = $p.find('.dkqe-tbl-item.active').data('tbl') || '';
						const sql = fn(active);
						$editor.val(sql);
						_updateFooter();
						$snMenu.hide();
						$editor.focus();
					});
			});
		});

		$('#qe-snippets').on('click', (e) => { e.stopPropagation(); $snMenu.toggle(); });
		$(document).on('click.qe', () => $snMenu.hide());

		/* ── main area ── */
		const $area = $(`<div class="dkqe-editor-area"></div>`).appendTo($p);

		/* ── LEFT: table browser ── */
		const $left = $(`<div class="dkqe-left"></div>`).appendTo($area);
		$left.append(`<div class="dkqe-left-hdr">${icoTable(11)} Tables</div>`);
		const $tblSearch = $(`<input style="margin:4px 8px;width:calc(100% - 16px);box-sizing:border-box;font-size:11.5px;padding:4px 8px;border:1px solid #d0c8e8;border-radius:4px;background:#fff;color:#1e1a2e;outline:none" placeholder="Filter tables…">`).appendTo($left);
		const $tblList = $(`<div></div>`).appendTo($left);

		function renderTables(filter) {
			$tblList.empty();
			const q = (filter||'').toLowerCase();
			const filtered = q ? _tables.filter(t => t.toLowerCase().includes(q)) : _tables;
			if (!filtered.length) {
				$tblList.append(`<div style="font-size:11px;color:#b0a8c8;padding:8px 12px">${_tables.length ? 'No match' : 'Select a site to load tables'}</div>`);
				return;
			}
			filtered.forEach(t => {
				$(`<div class="dkqe-tbl-item" data-tbl="${t}">${icoDatabase(11)}<span title="${t}">${t}</span></div>`)
					.appendTo($tblList)
					.on('click', function() {
						$tblList.find('.dkqe-tbl-item').removeClass('active');
						$(this).addClass('active');
					})
					.on('dblclick', function() {
						const cur = $editor.val().trim();
						const snip = `SELECT * FROM \`${t}\` LIMIT 50`;
						$editor.val(cur ? cur + '\n' + snip : snip);
						_updateFooter();
					});
			});
		}
		$tblSearch.on('input', () => renderTables($tblSearch.val()));

		/* ── CENTER: editor + results ── */
		const $center = $(`<div class="dkqe-center"></div>`).appendTo($area);

		// Editor wrap — Monaco
		const $edWrap = $(`<div class="dkqe-editor-wrap"></div>`).appendTo($center);
		const $edMcDiv = $(`<div id="qe-editor-mc" style="flex:1;height:100%;min-height:180px"></div>`).appendTo($edWrap);
		const $edFooter = $(`<div class="dkqe-editor-footer">
			<span id="qe-cursor-pos">Ln 1, Col 1</span>
			<span class="dkqe-tb-sep"></span>
			<span id="qe-char-count">0 chars</span>
			<span class="dkqe-tb-sep"></span>
			<span style="color:#5c4da8">MariaDB / SQL</span>
		</div>`).appendTo($edWrap);

		// Shim: $editor.val() / $editor.val(v) work via Monaco
		let _qeMonaco = null;
		const $editor = {
			val(v) {
				if (_qeMonaco) {
					if (v === undefined) return _qeMonaco.getValue();
					_qeMonaco.setValue(v); return;
				}
				return '';
			},
			focus() { _qeMonaco && _qeMonaco.focus(); },
			on() { return $editor; }, // no-op: keyup/click handled by Monaco
		};
		function _updateFooter() {
			if (!_qeMonaco) return;
			const pos = _qeMonaco.getPosition();
			const val = _qeMonaco.getValue();
			$('#qe-cursor-pos').text(`Ln ${pos.lineNumber}, Col ${pos.column}`);
			$('#qe-char-count').text(`${val.length} chars`);
		}
		_mcLoad(mc => {
			_qeMonaco = _mcCreate($edMcDiv, 'sql',
				'-- Write your SQL here (Ctrl+Enter to run)\nSELECT * FROM `tabDocType` LIMIT 20');
			_qeMonaco.addCommand(mc.KeyMod.CtrlCmd | mc.KeyCode.Enter, () => { $runBtn.trigger('click'); });
			_qeMonaco.onDidChangeCursorPosition(_updateFooter);
			_qeMonaco.onDidChangeModelContent(_updateFooter);
			// Register SQL completions with dynamic table + column support
			mc.languages.registerCompletionItemProvider('sql', {
				provideCompletionItems(model, position) {
					const word = model.getWordUntilPosition(position);
					const range = { startLineNumber: position.lineNumber, endLineNumber: position.lineNumber,
						startColumn: word.startColumn, endColumn: word.endColumn };
					const wUp = word.word.toUpperCase();
					if (!wUp) return { suggestions: [] };
					// Prefetch columns for tables mentioned in the query
					const qUp = model.getValue().toUpperCase();
					_tables.filter(t => qUp.includes(t.toUpperCase())).slice(0,5).forEach(_fetchCols);
					const sugg = [];
					SQL_KW.filter(k => k.startsWith(wUp)).forEach(k => sugg.push({
						label: k, kind: mc.languages.CompletionItemKind.Keyword,
						insertText: k, range, detail: 'keyword',
					}));
					SQL_FN.filter(fn => fn.toUpperCase().startsWith(wUp)).forEach(fn => sugg.push({
						label: fn, kind: mc.languages.CompletionItemKind.Function,
						insertText: fn, range, detail: 'function',
					}));
					_tables.filter(t => t.toUpperCase().includes(wUp)).slice(0, 16).forEach(t => sugg.push({
						label: t, kind: mc.languages.CompletionItemKind.Class,
						insertText: '`' + t + '`', range, detail: 'table',
					}));
					// Column completions from schema cache
					Object.entries(_ac.schema).forEach(([tbl, cols]) => {
						if (Array.isArray(cols)) cols.filter(c => c.toUpperCase().includes(wUp)).forEach(c => sugg.push({
							label: c, kind: mc.languages.CompletionItemKind.Field,
							insertText: c, range, detail: tbl,
						}));
					});
					return { suggestions: sugg.slice(0, 24) };
				}
			});
		});

		/* ── SQL Autocomplete ── */
		const SQL_KW = ['SELECT','FROM','WHERE','AND','OR','NOT','IN','IS','NULL',
			'LIKE','BETWEEN','EXISTS','CASE','WHEN','THEN','ELSE','END','ORDER','BY',
			'GROUP','HAVING','LIMIT','OFFSET','JOIN','LEFT','RIGHT','INNER','OUTER',
			'FULL','CROSS','ON','AS','DISTINCT','INSERT','INTO','VALUES','UPDATE',
			'SET','DELETE','CREATE','TABLE','DROP','ALTER','SHOW','DESCRIBE','EXPLAIN',
			'USE','UNION','ALL','WITH','RECURSIVE','COMMIT','ROLLBACK','TRANSACTION',
			'START','BEGIN','DECLARE','SIGNAL','SQLSTATE','HANDLER','TRIGGER','VIEW',
			'INDEX','PRIMARY','UNIQUE','FOREIGN','KEY','REFERENCES','CONSTRAINT',
			'DEFAULT','NOT','AUTO_INCREMENT','ENGINE','CHARSET','COLLATE','COMMENT'];

		const SQL_FN = ['COUNT(*)','COUNT(','SUM(','AVG(','MAX(','MIN(',
			'COALESCE(','IFNULL(','IF(','NULLIF(','GREATEST(','LEAST(',
			'CONCAT(','CONCAT_WS(','GROUP_CONCAT(','FIND_IN_SET(',
			'DATE(','NOW()','CURDATE()','CURTIME()','SYSDATE()',
			'DATE_FORMAT(','DATE_ADD(','DATE_SUB(','DATEDIFF(','TIMESTAMPDIFF(',
			'YEAR(','MONTH(','DAY(','HOUR(','MINUTE(','SECOND(',
			'CAST(','CONVERT(','FORMAT(',
			'TRIM(','LTRIM(','RTRIM(','LOWER(','UPPER(','LENGTH(','CHAR_LENGTH(',
			'SUBSTRING(','LEFT(','RIGHT(','INSTR(','LOCATE(','REPLACE(',
			'LPAD(','RPAD(','REPEAT(','REVERSE(',
			'ROUND(','FLOOR(','CEIL(','ABS(','MOD(','POWER(','SQRT(',
			'MD5(','SHA1(','UUID()',
			'JSON_VALUE(','JSON_EXTRACT(','JSON_OBJECT(','JSON_ARRAY(',
			'ROW_NUMBER()','RANK()','DENSE_RANK()','LAG(','LEAD(','OVER('];

		const _ac = { schema: {}, pending: {} };

		function _fetchCols(table) {
			if (_ac.schema[table] !== undefined || _ac.pending[table] || !_qeSite) return;
			_ac.pending[table] = true;
			frappe.call({
				method: 'frappe_devkit.api.query_editor.get_columns',
				args: { site: _qeSite, table },
				callback: r => { delete _ac.pending[table]; _ac.schema[table] = r.message?.columns || []; },
				error:    () => { delete _ac.pending[table]; _ac.schema[table] = []; },
			});
		}

		// Drag-resize handle between editor and results
		const $resizeHandle = $(`<div class="dkqe-resize-handle" title="Drag to resize"></div>`).appendTo($center);
		let _dragging = false, _dragY = 0, _edH = 0;
		$resizeHandle.on('mousedown', function(e) {
			_dragging = true; _dragY = e.clientY; _edH = $edWrap.height();
			$('body').css('cursor','row-resize').on('mousemove.qe-resize', function(ev) {
				if (!_dragging) return;
				const newH = Math.max(60, Math.min(_edH + (ev.clientY - _dragY), $center.height() - 100));
				$edWrap.height(newH);
				if (_qeMonaco) _qeMonaco.layout();
			}).on('mouseup.qe-resize', function() {
				_dragging = false;
				$('body').css('cursor','').off('.qe-resize');
			});
		});

		// Results area
		const $resultsArea = $(`<div class="dkqe-results-area"></div>`).appendTo($center);
		const $resHdr = $(`<div class="dkqe-results-hdr" style="display:none">
			<span class="dkqe-results-title" id="qe-res-title">Results</span>
			<span class="dkqe-results-meta" id="qe-res-meta"></span>
			<button class="dkqe-export-btn" id="qe-export-csv" title="Export to CSV">${icoDownload(12)} CSV</button>
		</div>`).appendTo($resultsArea);
		const $resScroll = $(`<div class="dkqe-results-scroll"></div>`).appendTo($resultsArea);
		$resScroll.append(`<div class="dkqe-empty">${icoDatabase(32)}<br><br>Run a query to see results here.<br><span style="font-size:12px">Ctrl+Enter to execute</span></div>`);

		let _lastResult = null;

		/* ── History panel (tab) ── */
		const $histArea = $(`<div style="display:none;flex-direction:column;flex:1;overflow:hidden;background:#faf8ff;border-left:1px solid #e8e0f8"></div>`).appendTo($area);
		$histArea.append(`<div class="dkqe-left-hdr" style="padding:10px 12px 6px">${icoHistory(11)} History</div>`);
		const $histList = $(`<div style="overflow-y:auto;flex:1"></div>`).appendTo($histArea);

		/* ── Tab bar (Results / History) ── */
		const $tabBar = $(`<div class="dkqe-tab-bar"></div>`).prependTo($resultsArea);
		const $tabRes  = $(`<div class="dkqe-tab active" data-tab="results">▤ Results</div>`).appendTo($tabBar);
		const $tabHist = $(`<div class="dkqe-tab" data-tab="history">${icoHistory(13)} History</div>`).appendTo($tabBar);
		$tabBar.on('click', '.dkqe-tab', function() {
			const t = $(this).data('tab');
			$tabBar.find('.dkqe-tab').removeClass('active'); $(this).addClass('active');
			if (t === 'results') { $resHdr.show(); $resScroll.show(); $histArea.hide(); }
			else { $resHdr.hide(); $resScroll.hide(); $histArea.show().css('display','flex'); }
		});

		/* ── Site change → load tables ── */
		$qeSiteSel.on('change', function() {
			_qeSite = this.value;
			_tables = [];
			// Reset autocomplete schema cache on site change
			_ac.schema = {}; _ac.pending = {};
			$tblList.html(`<div style="font-size:11px;color:#b0a8c8;padding:8px 12px">Loading…</div>`);
			if (!_qeSite) { renderTables(''); return; }
			frappe.call({
				method: 'frappe_devkit.api.query_editor.get_tables',
				args: { site: _qeSite },
				callback: r => {
					_tables = r.message?.tables || [];
					renderTables($tblSearch.val());
				},
				error: () => {
					$tblList.html(`<div style="font-size:11px;color:#c0392b;padding:8px 12px">Failed to load tables</div>`);
				}
			});
		});

		/* ── Run ── */
		function _showSpinner() {
			$resScroll.html(`<div class="dkqe-spinner"><div class="dkst-spin"></div> Executing query…</div>`);
			$resHdr.hide();
		}

		function _renderResult(res) {
			_lastResult = res;
			$resScroll.empty();
			$resHdr.show();

			if (res.type === 'error') {
				$('#qe-res-title').text('Error');
				$('#qe-res-meta').html(`<span style="color:#c0392b">${icoStop(12)} Query failed</span>`);
				$resScroll.append(`<div class="dkqe-error">${frappe.utils.escape_html(res.error)}</div>`);
				$('#qe-export-csv').hide();
				return;
			}

			if (res.type === 'write') {
				$('#qe-res-title').text('Write OK');
				$('#qe-res-meta').text(`${res.affected_rows} row(s) affected · ${res.elapsed_ms}ms`);
				$resScroll.append(`<div class="dkqe-affected">${icoPlay(14)} Query executed successfully — ${res.affected_rows} row(s) affected</div>`);
				$('#qe-export-csv').hide();
				return;
			}

			// SELECT result
			const { columns, rows, row_count, elapsed_ms, truncated } = res;
			$('#qe-res-title').text(`Results`);
			let metaHtml = `<strong>${row_count}</strong> row${row_count!==1?'s':''} · ${elapsed_ms}ms`;
			if (truncated) metaHtml += ` <span style="color:#c47a00"> · truncated (limit reached)</span>`;
			$('#qe-res-meta').html(metaHtml);
			$('#qe-export-csv').show();

			if (!row_count) {
				$resScroll.append(`<div class="dkqe-empty" style="padding:30px">No rows returned.</div>`);
				return;
			}

			const $tbl = $(`<table class="dkqe-res-tbl"><thead></thead><tbody></tbody></table>`);
			const $thead = $tbl.find('thead');
			const $tbody = $tbl.find('tbody');

			// Header
			let thHtml = `<tr><th class="dkqe-col-num">#</th>`;
			columns.forEach(c => { thHtml += `<th title="${c}">${c}</th>`; });
			thHtml += '</tr>';
			$thead.html(thHtml);

			// Body
			rows.forEach((row, i) => {
				let tr = `<tr><td class="dkqe-col-num">${i+1}</td>`;
				columns.forEach(c => {
					const cell = row[c] || { v: '', c: '' };
					const escaped = frappe.utils.escape_html(cell.v);
					const title = cell.v.length > 40 ? ` title="${escaped}"` : '';
					tr += `<td class="${cell.c} dkqe-td-expand"${title}>${escaped || (cell.c==='null-val'?'<em>NULL</em>':'')}</td>`;
				});
				tr += '</tr>';
				$tbody.append(tr);
			});

			$resScroll.append($tbl);
		}

		// Cell expand on click
		$(document).on('click', '.dkqe-td-expand', function() {
			const text = $(this).attr('title') || $(this).text();
			if (text && text.length > 60) frappe.msgprint(`<pre style="white-space:pre-wrap;word-break:break-all;font-family:monospace;font-size:12.5px">${frappe.utils.escape_html(text)}</pre>`);
		});

		// CSV export
		$('#qe-export-csv').on('click', () => {
			if (!_lastResult?.columns) return;
			const { columns, rows } = _lastResult;
			const esc = v => '"' + v.replace(/"/g, '""') + '"';
			let csv = columns.map(esc).join(',') + '\n';
			rows.forEach(row => {
				csv += columns.map(c => esc(row[c]?.v||'')).join(',') + '\n';
			});
			const blob = new Blob([csv], { type: 'text/csv' });
			const url = URL.createObjectURL(blob);
			$(`<a href="${url}" download="query_result.csv"></a>`)[0].click();
			URL.revokeObjectURL(url);
		});

		$runBtn.on('click', function() {
			const site = $qeSiteSel.val();
			if (!site) { frappe.throw('Select a site first'); return; }
			const sql = (_qeMonaco ? _qeMonaco.getValue() : '').trim();
			if (!sql) { frappe.throw('Query is empty'); return; }

			$runBtn.prop('disabled', true).html(`<div class="dkst-spin"></div>&nbsp;Running…`);
			_showSpinner();

			const args = {
				site,
				sql,
				allow_write: $('#qe-allow-write').is(':checked') ? 1 : 0,
				limit: $('#qe-limit').val(),
			};

			// Add to history
			_queryHistory.unshift({ sql, site, ts: new Date().toLocaleTimeString() });
			if (_queryHistory.length > 50) _queryHistory.pop();
			$histList.empty();
			_queryHistory.forEach(h => {
				$(`<div class="dkqe-history-item" title="${frappe.utils.escape_html(h.sql)}">[${h.ts}] ${frappe.utils.escape_html(h.sql.substring(0,80))}${h.sql.length>80?'…':''}</div>`)
					.appendTo($histList).on('click', () => {
						$editor.val(h.sql);
						_updateFooter();
						$tabRes.trigger('click');
					});
			});

			frappe.call({
				method: 'frappe_devkit.api.query_editor.execute_query',
				args,
				callback: r => {
					$runBtn.prop('disabled', false).html(`${icoPlay(14)}&nbsp;Run`);
					if (r.message) _renderResult(r.message);
					else _renderResult({ type: 'error', error: 'No response from server' });
				},
				error: (r) => {
					$runBtn.prop('disabled', false).html(`${icoPlay(14)}&nbsp;Run`);
					const msg = r.responseJSON?.exc_type || r.responseJSON?.message || 'Server error';
					_renderResult({ type: 'error', error: msg });
				}
			});
		});

		// Table double-click → describe
		$tblList.on('dblclick', '.dkqe-tbl-item', function() {
			const tbl = $(this).data('tbl');
			if (_qeMonaco) _qeMonaco.setValue(`DESCRIBE \`${tbl}\``);
			$runBtn.trigger('click');
		});

		renderTables('');
	};

	/* ══════════════════════════════════════════════════════════════════
	   MONACO EDITOR — shared loader + helpers
	   ══════════════════════════════════════════════════════════════════ */
	const _MC_CDN = 'https://cdnjs.cloudflare.com/ajax/libs/monaco-editor/0.44.0/min/vs';
	let _mcInstance = null, _mcQueue = [];

	function _mcLoad(cb) {
		if (_mcInstance) { cb(_mcInstance); return; }
		_mcQueue.push(cb);
		if (_mcQueue.length > 1) return;
		function _boot() {
			window.require.config({ paths: { vs: _MC_CDN } });
			window.require(['vs/editor/editor.main'], mc => {
				_mcRegisterCompletions(mc);
				_mcInstance = mc;
				_mcQueue.forEach(fn => fn(mc));
				_mcQueue = [];
			});
		}
		if (window.require && window.require.config) { _boot(); }
		else {
			const s = document.createElement('script');
			s.src = _MC_CDN + '/loader.min.js';
			s.onload = _boot;
			document.head.appendChild(s);
		}
	}

	function _mcRegisterCompletions(mc) {
		mc.languages.registerCompletionItemProvider('python', {
			triggerCharacters: ['.'],
			provideCompletionItems(model, position) {
				const word = model.getWordUntilPosition(position);
				const range = { startLineNumber: position.lineNumber, endLineNumber: position.lineNumber,
				                startColumn: word.startColumn, endColumn: word.endColumn };
				const methods = [
					'frappe.get_doc','frappe.new_doc','frappe.get_list','frappe.get_all',
					'frappe.get_value','frappe.set_value','frappe.db.get_value','frappe.db.set_value',
					'frappe.db.get_list','frappe.db.get_all','frappe.db.insert','frappe.db.delete',
					'frappe.db.exists','frappe.db.count','frappe.db.sql','frappe.throw',
					'frappe.msgprint','frappe.log_error','frappe.get_cached_doc',
					'frappe.session.user','frappe.local.site','frappe.utils.now',
					'frappe.utils.now_datetime','frappe.utils.today','frappe.utils.get_url',
					'frappe.has_permission','frappe.only_for','frappe.whitelist',
					'frappe.response','context.title','context.no_cache',
				];
				return { suggestions: methods.map(m => ({
					label: m, kind: mc.languages.CompletionItemKind.Function,
					insertText: m.split('.').pop(), range, detail: 'Frappe API',
				})) };
			}
		});
		mc.languages.registerCompletionItemProvider('html', {
			triggerCharacters: ['{', '%'],
			provideCompletionItems(model, position) {
				const word = model.getWordUntilPosition(position);
				const range = { startLineNumber: position.lineNumber, endLineNumber: position.lineNumber,
				                startColumn: word.startColumn, endColumn: word.endColumn };
				const snippets = [
					{ label:'extends',            insert:'{% extends "templates/web.html" %}' },
					{ label:'block title',         insert:'{% block title %}${1:Title}{% endblock %}' },
					{ label:'block page_content',  insert:'{% block page_content %}\n${1}\n{% endblock %}' },
					{ label:'if',                  insert:'{% if ${1:condition} %}\n${2}\n{% endif %}' },
					{ label:'for',                 insert:'{% for ${1:item} in ${2:items} %}\n${3}\n{% endfor %}' },
					{ label:'include',             insert:'{%' + ' include "${1:template.html}" %}' },
					{ label:'macro',               insert:'{% macro ${1:name}(${2:args}) %}\n${3}\n{% endmacro %}' },
					{ label:'var',                 insert:'{{ ${1:variable} }}' },
					{ label:'trans',               insert:'{% trans %}${1:text}{% endtrans %}' },
					{ label:'set',                 insert:'{% set ${1:var} = ${2:value} %}' },
				];
				return { suggestions: snippets.map(s => ({
					label: s.label, kind: mc.languages.CompletionItemKind.Snippet,
					insertText: s.insert,
					insertTextRules: mc.languages.CompletionItemInsertTextRule.InsertAsSnippet,
					range, detail: 'Jinja2/Frappe',
				})) };
			}
		});
	}

	function _mcCreate($container, lang, value) {
		return _mcInstance.editor.create($container[0], {
			value: value || '',
			language: lang || 'html',
			theme: 'vs',
			fontSize: 13,
			lineHeight: 20,
			fontFamily: "'Consolas','Monaco','Courier New',monospace",
			minimap: { enabled: false },
			scrollBeyondLastLine: false,
			wordWrap: 'on',
			automaticLayout: true,
			tabSize: 4,
			renderLineHighlight: 'line',
			suggestOnTriggerCharacters: true,
			quickSuggestions: { other: true, comments: false, strings: false },
			padding: { top: 8, bottom: 8 },
			scrollbar: { vertical: 'auto', horizontal: 'auto' },
		});
	}

	function _mcLang(ext) {
		return { '.html':'html', '.py':'python', '.js':'javascript', '.css':'css',
		         '.md':'markdown', '.json':'json', '.txt':'plaintext',
		         '.xml':'xml', '.jinja2':'html' }[ext] || 'plaintext';
	}
	function _mcSetLang(editor, lang) {
		if (editor && _mcInstance) _mcInstance.editor.setModelLanguage(editor.getModel(), lang);
	}


	/* ══════════════════════════════════════════════════════════════════
	   WWW FILE MANAGER
	   ══════════════════════════════════════════════════════════════════ */
	PANELS.www_editor = function($p) {
		$p.css({ padding:0, display:'flex', flexDirection:'column', overflow:'hidden', height:'100%' });

		/* ── state ── */
		let _app = '', _tree = [], _file = null, _dirty = false, _companion = null, _activeComp = 'main';

		/* ── toolbar ── */
		const $tb = $('<div class="dkpb-toolbar"></div>').appendTo($p);
		const $appSel = $('<select class="dkqe-site-sel" id="www-app-sel" style="min-width:150px" title="App"></select>').appendTo($tb);
		$appSel.append('<option value="">— select app —</option>');
		frappe.call({ method:'frappe_devkit.api.page_builder.list_apps_with_www', callback: r => {
			(r.message?.apps||[]).filter(a => a.has_www).forEach(a => $appSel.append(`<option value="${a.app}">${a.app}</option>`));
		}});
		$tb.append('<button class="dkst-ce-link" data-app-sel="www-app-sel" title="Edit this app in Code Editor">⌨ Edit in Editor</button>');

		$tb.append('<div class="dkpb-tsep"></div>');
		const $newBtn  = $('<button class="dkpb-btn">＋ New Page</button>').appendTo($tb);
		const $saveBtn = $('<button class="dkpb-btn dkpb-btn-accent" disabled>💾 Save  <kbd style="font-size:9px;opacity:.7">Ctrl+S</kbd></button>').appendTo($tb);
		const $delBtn  = $('<button class="dkpb-btn" style="color:#c0392b" disabled>🗑 Delete</button>').appendTo($tb);
		$tb.append('<div class="dkpb-tsep"></div>');
		const $prevToggle = $('<button class="dkpb-btn active" title="Toggle preview pane" style="background:#ede8ff">👁 Preview</button>').appendTo($tb);
		let _showPreview = true;

		/* ── layout ── */
		const $area = $('<div class="dkpb-area"></div>').appendTo($p);

		/* ── LEFT: file tree ── */
		const $left = $('<div class="dkpb-left"></div>').appendTo($area);
		$left.append('<div class="dkpb-left-hdr">📁 WWW Files</div>');
		const $ftSearch = $('<input class="dkpb-search" placeholder="Filter files…">').appendTo($left);
		const $ftList   = $('<div class="dkpb-tree"></div>').appendTo($left);

		const _extMap = { '.html':'html','.py':'py','.md':'md','.css':'css','.js':'js','.json':'json' };
		const _extIcon = { '.html':'📄','.py':'🐍','.md':'📝','.css':'🎨','.js':'⚡','.json':'{}' };
		const _collapsed = new Set();

		function _renderTree(filter) {
			$ftList.empty();
			const q = (filter||'').toLowerCase();
			_tree.forEach(node => {
				if (node.type === 'dir') {
					if (q && !_tree.some(n => n.type==='file' && n.path.startsWith(node.path+'/') && n.name.toLowerCase().includes(q))) return;
					const open = !_collapsed.has(node.path);
					$(`<div class="dkpb-node dir-nd" data-path="${node.path}" style="padding-left:${8+node.depth*10}px">
						<span style="font-size:11px">${open?'▾':'▸'}</span>
						<span>📁 ${frappe.utils.escape_html(node.name)}</span>
					</div>`).appendTo($ftList).on('click', function() {
						if (_collapsed.has(node.path)) _collapsed.delete(node.path); else _collapsed.add(node.path);
						_renderTree($ftSearch.val());
					});
				} else {
					// Check if parent dir is collapsed
					const parts = node.path.split('/'); parts.pop();
					if (parts.some((_,i) => _collapsed.has(parts.slice(0,i+1).join('/')))) return;
					if (q && !node.name.toLowerCase().includes(q)) return;
					const xb = _extMap[node.ext] || '';
					const ico = _extIcon[node.ext] || '📄';
					const compDot = node.companion ? `<span class="dkpb-nd-comp" title="Has companion file">⊕</span>` : '';
					$(`<div class="dkpb-node${_file?.path===node.path?' sel':''}" data-path="${node.path}" style="padding-left:${12+node.depth*10}px">
						<span>${ico}</span>
						<span class="xb xb-${xb}">${node.ext.replace('.','')||'?'}</span>
						<span class="dkpb-nd-lbl" title="${node.path}">${frappe.utils.escape_html(node.name)}</span>
						${compDot}
					</div>`).appendTo($ftList).on('click', function() {
						if (_dirty && !confirm('Unsaved changes. Leave?')) return;
						_openFile(node);
					});
				}
			});
		}
		$ftSearch.on('input', () => _renderTree($ftSearch.val()));

		/* ── CENTER: editor + optional split preview ── */
		const $center = $('<div class="dkpb-center" style="flex:1;min-width:0"></div>').appendTo($area);

		// Breadcrumb
		const $bc = $('<div class="dkpb-breadcrumb" style="display:none"></div>').appendTo($center);

		// Companion tabs
		const $compTabs = $('<div class="dkpb-comp-tabs" style="display:none"></div>').appendTo($center);

		// Split: editor | preview
		const $splitArea = $('<div class="dkpb-split-h" style="flex:1;min-height:0;overflow:hidden"></div>').appendTo($center);

		// Editor half
		const $edHalf = $('<div class="dkpb-split-pane dkpb-ed-wrap"></div>').appendTo($splitArea);
		const $edMonacoWWW = $('<div class="dkpb-ed-monaco"></div>').appendTo($edHalf);
		let _wwwEd = null;

		function _wwwGetEd(cb) {
			if (_wwwEd) { cb(_wwwEd); return; }
			_mcLoad(mc => {
				_wwwEd = _mcCreate($edMonacoWWW, 'html', '');
				_wwwEd.addCommand(mc.KeyMod.CtrlCmd | mc.KeyCode.KeyS, _save);
				_wwwEd.onDidChangeModelContent(() => {
					_dirty = true; $saveBtn.prop('disabled', false);
					if (_file && _activeComp === 'main') _file.content = _wwwEd.getValue();
				});
				cb(_wwwEd);
			});
		}

		// Resizer
		const $resHandle = $('<div class="dkpb-split-handle"></div>').appendTo($splitArea);

		// Preview half
		const $prevHalf = $('<div class="dkpb-split-pane" style="background:#fff;min-width:0;overflow:hidden;display:flex;flex-direction:column"></div>').appendTo($splitArea);
		const $prevBar2 = $('<div class="dkpb-preview-bar"><span style="flex:1;font-size:10.5px">HTML Preview</span><button class="dkpb-btn" id="wwwe-refresh-prev">↺ Refresh</button></div>').appendTo($prevHalf);
		const $prevFrame = $('<iframe class="dkpb-preview-frame" sandbox="allow-scripts"></iframe>').appendTo($prevHalf);

		// Empty state
		const $emptyMsg = $('<div class="dkpb-empty">Select an app and file to start editing</div>').appendTo($center);

		// Resize split handle
		let _dragW = false, _dragX = 0, _splitW = 0;
		$resHandle.on('mousedown', e => {
			_dragW = true; _dragX = e.clientX; _splitW = $edHalf.width();
			$('body').css('cursor','col-resize').on('mousemove.wwwe', ev => {
				if (!_dragW) return;
				const nw = Math.max(200, Math.min(_splitW + (ev.clientX - _dragX), $splitArea.width() - 200));
				$edHalf.width(nw);
			}).on('mouseup.wwwe', () => { _dragW = false; $('body').css('cursor','').off('.wwwe'); });
		});

		function _togglePreview(show) {
			_showPreview = show;
			$prevHalf.toggle(show); $resHandle.toggle(show);
			$prevToggle.toggleClass('active', show).css('background', show ? '#ede8ff' : '');
		}
		$prevToggle.on('click', () => _togglePreview(!_showPreview));

		/* ── file open ── */
		function _openFile(node, forceContent) {
			const path = typeof node === 'string' ? node : node.path;
			frappe.call({
				method: 'frappe_devkit.api.page_builder.get_www_file',
				args: { app: _app, path },
				callback: r => {
					const data = r.message;
					if (!data) return;
					_file = { path, ext: data.ext, content: data.content };
					_dirty = false;
					$saveBtn.prop('disabled', true);
					$delBtn.prop('disabled', false);
					$emptyMsg.hide();
					$bc.show().html(`<span>${_app}</span><span style="color:#5a4870">/www/</span><strong>${path}</strong>`);

					// Companion tabs
					const compNode = _tree.find(n => n.path === path);
					if (compNode?.companion) {
						_companion = compNode.companion;
						$compTabs.show().html(`
							<span class="dkpb-comp-tab active" data-which="main">${frappe.utils.escape_html(path.split('/').pop())}</span>
							<span class="dkpb-comp-tab" data-which="companion">${frappe.utils.escape_html(_companion.split('/').pop())}</span>
						`);
					} else {
						_companion = null; $compTabs.hide();
					}
					_activeComp = 'main';
					const _wwwContent = forceContent !== undefined ? forceContent : data.content;
					_wwwGetEd(ed => { ed.setValue(_wwwContent); _mcSetLang(ed, _mcLang(data.ext)); });

					// Auto-show preview for HTML
					if (data.ext === '.html') {
						_showPreview || _togglePreview(true);
						_refreshPreview();
					} else {
						_togglePreview(false);
					}

					_renderTree($ftSearch.val());
				}
			});
		}

		$compTabs.on('click', '.dkpb-comp-tab', function() {
			$compTabs.find('.dkpb-comp-tab').removeClass('active'); $(this).addClass('active');
			_activeComp = $(this).data('which');
			if (_activeComp === 'main') {
				_wwwGetEd(ed => {
					ed.setValue(_file?.content || '');
					_mcSetLang(ed, _mcLang(_file?.ext || '.html'));
				});
			} else {
				frappe.call({
					method: 'frappe_devkit.api.page_builder.get_www_file',
					args: { app: _app, path: _companion },
					callback: r => {
						const cExt = '.' + (_companion || '').split('.').pop();
						_wwwGetEd(ed => { ed.setValue(r.message?.content || ''); _mcSetLang(ed, _mcLang(cExt)); });
					}
				});
			}
		});

		/* ── preview ── */
		function _refreshPreview() {
			const html = _wwwEd ? _wwwEd.getValue() : (_file?.content || '');
			if (!html.trim()) return;
			// Wrap bare HTML content in a basic page if it's a Frappe template
			const srcdoc = html.includes('{% extends') || html.includes('{%') || html.includes('{{')
				? `<!DOCTYPE html><html><head><meta charset="utf-8"><style>body{font-family:-apple-system,sans-serif;padding:20px;color:#333}</style></head><body><div style="background:#fff3cd;padding:10px;border-radius:4px;font-size:12px;margin-bottom:16px">⚠️ Jinja2 template — raw source shown below. Use "Open in browser" for rendered output.</div><pre style="font-size:12px;white-space:pre-wrap;word-break:break-all">${frappe.utils.escape_html(html)}</pre></body></html>`
				: `<!DOCTYPE html><html><head><meta charset="utf-8"><link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap@4.6.2/dist/css/bootstrap.min.css"><style>body{padding:20px}</style></head><body>${html}</body></html>`;
			$prevFrame.attr('srcdoc', srcdoc);
		}

		$('#wwwe-refresh-prev').on('click', _refreshPreview);

		/* ── save ── */
		function _save() {
			if (!_file || !_app) return;
			const path = _activeComp === 'companion' ? _companion : _file.path;
			const content = _wwwEd ? _wwwEd.getValue() : (_file?.content || '');
			$saveBtn.prop('disabled', true).text('Saving…');
			frappe.call({
				method: 'frappe_devkit.api.page_builder.save_www_file',
				args: { app: _app, path, content },
				callback: r => {
					$saveBtn.text('💾 Save');
					if (r.message?.saved) {
						_dirty = false; $saveBtn.prop('disabled', true);
						if (_activeComp === 'main') _file.content = content;
						frappe.show_alert({ message:`Saved: ${path}`, indicator:'green' }, 3);
						if (path.endsWith('.html')) _refreshPreview();
					}
				},
				error: () => { $saveBtn.prop('disabled',false).text('💾 Save'); }
			});
		}
		$saveBtn.on('click', _save);

		/* ── delete ── */
		$delBtn.on('click', function() {
			if (!_file) return;
			const path = _activeComp === 'companion' ? _companion : _file.path;
			frappe.confirm(`Delete <b>${frappe.utils.escape_html(path)}</b>?`, () => {
				frappe.call({
					method: 'frappe_devkit.api.page_builder.delete_www_file',
					args: { app:_app, path },
					callback: r => {
						if (r.message?.deleted) {
							_tree = _tree.filter(n => n.path !== path);
							_file = null; _dirty = false;
							$bc.hide(); $compTabs.hide(); $emptyMsg.show();
							(_wwwEd?.setValue('')); $saveBtn.prop('disabled',true); $delBtn.prop('disabled',true);
							_renderTree($ftSearch.val());
							frappe.show_alert({ message:'File deleted', indicator:'red' }, 3);
						}
					}
				});
			});
		});

		/* ── new page ── */
		$newBtn.on('click', function() {
			if (!_app) { frappe.show_alert({ message:'Select an app first', indicator:'orange' }); return; }

			const WWW_PRESETS = [
				{ id:"blank",          name:"Blank Page",         ico:"📄", color:"#6b7280", tag:"General",  tagBg:"#f3f4f6", tagColor:"#374151", desc:"Minimal starter — clean HTML + PY stub." },
				{ id:"landing",        name:"Landing Page",       ico:"🚀", color:"#5c4da8", tag:"Marketing",tagBg:"#ede9fe", tagColor:"#4c1d95", desc:"Hero, features, stats band, CTA section." },
				{ id:"product_detail", name:"Product Detail",     ico:"📦", color:"#0369a1", tag:"eCommerce",tagBg:"#e0f2fe", tagColor:"#0c4a6e", desc:"Image gallery, pricing, specs, add to cart." },
				{ id:"contact_form",   name:"Contact Form",       ico:"✉️", color:"#059669", tag:"Forms",    tagBg:"#d1fae5", tagColor:"#064e3b", desc:"Full contact form with validation + info cards." },
				{ id:"portal_dashboard",name:"Portal Dashboard",  ico:"📊", color:"#1d4ed8", tag:"Portal",   tagBg:"#dbeafe", tagColor:"#1e40af", desc:"Auth-protected KPI dashboard + data table." },
				{ id:"list_directory", name:"List / Directory",   ico:"🗂️", color:"#7c3aed", tag:"Catalog",  tagBg:"#ede9fe", tagColor:"#5b21b6", desc:"Searchable grid of records with pagination." },
				{ id:"pricing",        name:"Pricing Page",       ico:"💳", color:"#b45309", tag:"Marketing",tagBg:"#fef3c7", tagColor:"#92400e", desc:"3-tier pricing cards with feature lists." },
				{ id:"faq",            name:"FAQ Page",           ico:"❓", color:"#be185d", tag:"Support",  tagBg:"#fce7f3", tagColor:"#9d174d", desc:"Searchable accordion FAQ with CTA footer." },
				{ id:"blog_post",      name:"Blog Post",          ico:"✍️", color:"#0891b2", tag:"Blog",     tagBg:"#cffafe", tagColor:"#155e75", desc:"Article layout with sidebar + share buttons." },
				{ id:"ecommerce_cart", name:"Shopping Cart",      ico:"🛒", color:"#dc2626", tag:"eCommerce", tagBg:"#fee2e2", tagColor:"#991b1b", desc:"Cart, checkout form, order summary, upsell strip." },
				{ id:"user_profile",   name:"User Profile",       ico:"👤", color:"#0369a1", tag:"Portal",    tagBg:"#e0f2fe", tagColor:"#0c4a6e", desc:"Account details, avatar, activity & preferences." },
				{ id:"news_feed",      name:"News Feed",          ico:"📰", color:"#15803d", tag:"Blog",      tagBg:"#dcfce7", tagColor:"#14532d", desc:"Infinite-scroll article feed with category pills." },
				{ id:"event_detail",   name:"Event Detail",       ico:"🎟️", color:"#9333ea", tag:"Events",    tagBg:"#f3e8ff", tagColor:"#581c87", desc:"Event header, schedule, speakers, register CTA." },
				{ id:"knowledge_base", name:"Knowledge Base",     ico:"📚", color:"#0f766e", tag:"Support",   tagBg:"#ccfbf1", tagColor:"#134e4a", desc:"Searchable articles with breadcrumb + TOC sidebar." },
				{ id:"coming_soon",    name:"Coming Soon",        ico:"⏳", color:"#7c3aed", tag:"Marketing", tagBg:"#ede9fe", tagColor:"#4c1d95", desc:"Countdown timer, email capture, social links." },
				/* ── Advanced UI/UX — full-site layouts with all nav styles ── */
				{ id:"topnav_multipage", name:"Multi-Page Top Nav",   ico:"🧭", color:"#1d4ed8", tag:"Full Site",  tagBg:"#dbeafe", tagColor:"#1e40af", desc:"Sticky responsive navbar + dropdowns + hero + features + testimonials + 4-col footer." },
				{ id:"leftnav_sidebar",  name:"Left Sidebar Nav",     ico:"◧",  color:"#7c3aed", tag:"App Shell",  tagBg:"#ede9fe", tagColor:"#5b21b6", desc:"Fixed collapsible sidebar + top header + breadcrumb + KPI cards. Full app-shell." },
				{ id:"spa_scrollnav",    name:"Single-Page App",      ico:"∞",  color:"#0891b2", tag:"SPA",        tagBg:"#cffafe", tagColor:"#155e75", desc:"Sticky scroll-spy nav, all sections one page, progress bar, back-to-top FAB." },
				{ id:"saas_landing",     name:"SaaS Landing",         ico:"🛸", color:"#6d28d9", tag:"Marketing",  tagBg:"#ede9fe", tagColor:"#4c1d95", desc:"Announcement bar + hero + logos + alternating features + pricing + testimonials + FAQ." },
				{ id:"agency_portfolio", name:"Agency / Portfolio",   ico:"🎨", color:"#be185d", tag:"Creative",   tagBg:"#fce7f3", tagColor:"#9d174d", desc:"Fullscreen hero + filterable work grid with hover overlay + services + team + contact." },
				{ id:"docs_leftnav",     name:"Documentation",        ico:"📖", color:"#0f766e", tag:"Docs",       tagBg:"#ccfbf1", tagColor:"#134e4a", desc:"3-panel docs: sidebar nav tree + article with TOC + code blocks + prev/next nav." },
			];

			let _selPreset = 'blank';

			const $dlg = $(`<div style="padding:4px 0">
				<div class="dkpp-preset-grid" id="www-pg"></div>
				<hr style="border-color:#ede9fe;margin:10px 0">
				<div style="display:grid;grid-template-columns:1fr 1fr;gap:10px;margin-bottom:4px">
					<div>
						<label style="font-size:11px;font-weight:700;color:#5c4da8;display:block;margin-bottom:4px">File / Route *</label>
						<input id="www-new-route" class="dkst-inp" placeholder="about-us or products/my-item" style="width:100%">
						<div style="font-size:10px;color:#9080b8;margin-top:3px">No leading slash — .html added automatically</div>
					</div>
					<div>
						<label style="font-size:11px;font-weight:700;color:#5c4da8;display:block;margin-bottom:4px">Python Handler</label>
						<label style="cursor:pointer;font-size:12px"><input type="checkbox" id="www-new-py" checked style="margin-right:6px">Create .py file</label>
					</div>
				</div>
			</div>`);

			const d = new frappe.ui.Dialog({
				title: '✨ New WWW Page',
				fields: [{ fieldtype:'HTML', options: $dlg[0].outerHTML }],
				primary_action_label: 'Create Page',
				primary_action() {
					const route = d.$wrapper.find('#www-new-route').val().trim();
					if (!route) { frappe.show_alert({ message:'File name required', indicator:'orange' }); return; }
					const create_py = d.$wrapper.find('#www-new-py').is(':checked') ? 1 : 0;
					d.hide();
					frappe.call({
						method: 'frappe_devkit.api.page_builder.create_www_page',
						args: { app: _app, route, create_py, preset: _selPreset },
						callback: r => {
							if (r.message?.created) {
								frappe.show_alert({ message:`✅ Created: ${r.message.created.join(', ')}`, indicator:'green' }, 4);
								_loadTree(_app, r.message.path);
							}
						}
					});
				}
			});
			d.show();

			// Render preset cards after dialog is shown
			const $pg = d.$wrapper.find('#www-pg');
			WWW_PRESETS.forEach(pr => {
				$(`<div class="dkpp-preset-card${pr.id==='blank'?' selected':''}" data-pid="${pr.id}" style="position:relative">
					<div class="dkpp-preset-top" style="background:${pr.color}"></div>
					<div class="dkpp-preset-body">
						<div class="dkpp-preset-ico">${pr.ico}</div>
						<div class="dkpp-preset-nm">${pr.name}</div>
						<div class="dkpp-preset-ds">${pr.desc}</div>
						<div class="dkpp-preset-tag" style="background:${pr.tagBg};color:${pr.tagColor}">${pr.tag}</div>
					</div>
				</div>`).appendTo($pg).on('click', function() {
					$pg.find('.dkpp-preset-card').removeClass('selected');
					$(this).addClass('selected');
					_selPreset = pr.id;
					if (!d.$wrapper.find('#www-new-route').val()) {
						d.$wrapper.find('#www-new-route').val(pr.id.replace(/_/g,'-'));
					}
				});
			});
		});

		/* ── app change ── */
		function _loadTree(app, autoOpenPath) {
			$ftList.html('<div class="dkpb-empty" style="font-size:11.5px">Loading…</div>');
			frappe.call({
				method: 'frappe_devkit.api.page_builder.list_www_tree',
				args: { app },
				callback: r => {
					_tree = r.message?.tree || [];
					_renderTree($ftSearch.val());
					if (autoOpenPath) {
						const node = _tree.find(n => n.path === autoOpenPath);
						if (node) _openFile(node);
					}
				},
				error: () => { $ftList.html('<div class="dkpb-empty" style="font-size:11.5px;color:#c0392b">Failed to load</div>'); }
			});
		}

		$appSel.on('change', function() {
			_app = this.value; _file = null; _dirty = false; _tree = [];
			$bc.hide(); $compTabs.hide(); $emptyMsg.show();
			(_wwwEd?.setValue('')); $saveBtn.prop('disabled',true); $delBtn.prop('disabled',true);
			$tb.find('.dkst-ce-link').toggleClass('visible', !!_app);
			if (_app) _loadTree(_app);
		});
	};


	/* ══════════════════════════════════════════════════════════════════
	   DESK PAGE EDITOR
	   ══════════════════════════════════════════════════════════════════ */
	PANELS.desk_page_mgr = function($p) {
		$p.css({ padding:0, display:'flex', flexDirection:'column', overflow:'hidden', height:'100%' });

		let _app = '', _pages = [], _curPage = null, _openFiles = {}, _activeFile = null, _dirty = {};

		/* ── toolbar ── */
		const $tb = $('<div class="dkpb-toolbar"></div>').appendTo($p);
		const $appSel = $('<select class="dkqe-site-sel" id="desk-app-sel" style="min-width:150px"></select>').appendTo($tb);
		$appSel.append('<option value="">— select app —</option>');
		frappe.call({ method:'frappe_devkit.api.page_builder.list_apps_with_www', callback: r => {
			(r.message?.apps||[]).forEach(a => $appSel.append(`<option value="${a.app}">${a.app}</option>`));
		}});
		$tb.append('<button class="dkst-ce-link" data-app-sel="desk-app-sel" title="Edit this app in Code Editor">⌨ Edit in Editor</button>');
		$tb.append('<div class="dkpb-tsep"></div>');
		const $saveBtn = $('<button class="dkpb-btn dkpb-btn-accent" disabled>💾 Save <kbd style="font-size:9px;opacity:.7">Ctrl+S</kbd></button>').appendTo($tb);
		$tb.append('<div class="dkpb-tsep"></div>');
		const $newDeskBtn  = $('<button class="dkpb-btn">＋ New Page</button>').appendTo($tb);
		const $editDeskBtn = $('<button class="dkpb-btn" disabled>✏ Edit Page</button>').appendTo($tb);
		const $delDeskBtn  = $('<button class="dkpb-btn" style="color:#c0392b" disabled>🗑 Delete Page</button>').appendTo($tb);

		/* ── layout ── */
		const $area = $('<div class="dkpb-area"></div>').appendTo($p);

		/* ── LEFT ── */
		const $left = $('<div class="dkpb-left"></div>').appendTo($area);
		$left.append('<div class="dkpb-left-hdr">🖥 Desk Pages</div>');
		const $pgSearch = $('<input class="dkpb-search" placeholder="Filter pages…">').appendTo($left);
		const $pgList   = $('<div class="dkpb-tree"></div>').appendTo($left);

		function _renderPgList(filter) {
			$pgList.empty();
			const q = (filter||'').toLowerCase();
			const filtered = q ? _pages.filter(p => p.name.toLowerCase().includes(q)) : _pages;
			if (!filtered.length) {
				$pgList.html(`<div class="dkpb-empty" style="font-size:11.5px">${_pages.length?'No match':'Select an app'}</div>`);
				return;
			}
			filtered.forEach(pg => {
				$(`<div class="dkpb-node${_curPage?.name===pg.name?' sel':''}" data-name="${pg.name}">
					🖥 <span class="dkpb-nd-lbl">${frappe.utils.escape_html(pg.name)}</span>
					<span style="font-size:9px;color:#9080b8;margin-left:auto">${pg.files.length}f</span>
				</div>`).appendTo($pgList).on('click', () => _openPage(pg));
			});
		}
		$pgSearch.on('input', () => _renderPgList($pgSearch.val()));

		/* ── CENTER ── */
		const $center = $('<div class="dkpb-center"></div>').appendTo($area);
		const $fileTabs = $('<div class="dkpb-file-tabs" style="display:none"></div>').appendTo($center);
		const $edWrap = $('<div class="dkpb-ed-wrap" style="flex:1;min-height:0;display:none"></div>').appendTo($center);
		const $edMonacoDesk = $('<div class="dkpb-ed-monaco"></div>').appendTo($edWrap);
		const $emptyMsg = $('<div class="dkpb-empty">Select a desk page to edit its files</div>').appendTo($center);
		let _deskEd = null;
		const _deskModels = {};

		function _deskGetEd(cb) {
			if (_deskEd) { cb(_deskEd); return; }
			_mcLoad(mc => {
				_deskEd = _mcCreate($edMonacoDesk, 'javascript', '');
				_deskEd.addCommand(mc.KeyMod.CtrlCmd | mc.KeyCode.KeyS, _save);
				_deskEd.onDidChangeModelContent(() => {
					if (!_activeFile) return;
					_openFiles[_activeFile] = _deskEd.getValue();
					_dirty[_activeFile] = true;
					$saveBtn.prop('disabled', false);
					$fileTabs.find(`[data-file="${_activeFile}"]`)
						.html(`${_activeFile}<span class="dirty"></span>`).addClass('active');
				});
				cb(_deskEd);
			});
		}

		/* ── open page ── */
		function _openPage(pg) {
			_curPage = pg; _openFiles = {}; _dirty = {}; _activeFile = null;
			$delDeskBtn.prop('disabled', false);
			$editDeskBtn.prop('disabled', false);
			// Dispose Monaco models from previous page
			if (_mcInstance) {
				Object.values(_deskModels).forEach(m => { try { m.dispose(); } catch(e) {} });
			}
			Object.keys(_deskModels).forEach(k => delete _deskModels[k]);
			_renderPgList($pgSearch.val());
			$fileTabs.show().empty();
			pg.files.forEach(fname => {
				$(`<span class="dkpb-file-tab" data-file="${fname}">${fname}</span>`).appendTo($fileTabs)
					.on('click', function() { _openFile(fname); });
			});
			const autoOpen = pg.files.find(f => f.endsWith('.js')) || pg.files[0];
			if (autoOpen) _openFile(autoOpen);
		}

		function _openFile(fname) {
			if (_activeFile && _dirty[_activeFile] && _deskEd) {
				_openFiles[_activeFile] = _deskEd.getValue();
			}
			_activeFile = fname;
			$fileTabs.find('.dkpb-file-tab').removeClass('active');
			$fileTabs.find(`[data-file="${fname}"]`).addClass('active');
			const lang = _mcLang('.' + fname.split('.').pop());

			function _setContent(content) {
				$emptyMsg.hide(); $edWrap.css('display','flex');
				_deskGetEd(ed => {
					if (!_deskModels[fname]) {
						_deskModels[fname] = _mcInstance.editor.createModel(content, lang);
					}
					ed.setModel(_deskModels[fname]);
					$saveBtn.prop('disabled', !_dirty[fname]);
				});
			}

			if (_openFiles[fname] !== undefined) { _setContent(_openFiles[fname]); return; }

			frappe.call({
				method: 'frappe_devkit.api.page_builder.get_desk_page_file',
				args: { app:_app, rel_page_path:_curPage.path, filename:fname },
				callback: r => {
					if (!r.message) return;
					_openFiles[fname] = r.message.content;
					_setContent(r.message.content);
				}
			});
		}

		function _save() {
			if (!_curPage || !_activeFile) return;
			const content = _deskEd ? _deskEd.getValue() : (_openFiles[_activeFile] || '');
			$saveBtn.prop('disabled', true).text('Saving…');
			frappe.call({
				method: 'frappe_devkit.api.page_builder.save_desk_page_file',
				args: { app:_app, rel_page_path:_curPage.path, filename:_activeFile, content },
				callback: r => {
					$saveBtn.text('💾 Save');
					if (r.message?.saved) {
						_dirty[_activeFile] = false;
						$fileTabs.find('.dkpb-file-tab.active').html(_activeFile).addClass('active');
						frappe.show_alert({ message:`Saved: ${_activeFile}`, indicator:'green' }, 3);
					}
				},
				error: () => { $saveBtn.prop('disabled',false).text('💾 Save'); }
			});
		}
		$saveBtn.on('click', _save);

		/* ── new desk page ── */
		$newDeskBtn.on('click', function() {
			if (!_app) { frappe.show_alert({ message:'Select an app first', indicator:'orange' }); return; }

			const DESK_PRESETS = [
				{ id:"blank",      name:"Blank Page",       ico:"📄", color:"#6b7280", tag:"General",    tagBg:"#f3f4f6", tagColor:"#374151", desc:"Minimal JS + PY + Jinja2 starter." },
				{ id:"dashboard",  name:"Dashboard",        ico:"📊", color:"#5c4da8", tag:"Analytics",  tagBg:"#ede9fe", tagColor:"#4c1d95", desc:"KPI cards, data table, chart hooks." },
				{ id:"list_tool",  name:"List / Report",    ico:"🗂️", color:"#0369a1", tag:"Data",       tagBg:"#e0f2fe", tagColor:"#0c4a6e", desc:"Filterable list with action buttons." },
				{ id:"form_tool",  name:"Form Tool",        ico:"📝", color:"#059669", tag:"Forms",      tagBg:"#d1fae5", tagColor:"#064e3b", desc:"Input form with validation + submit." },
				{ id:"analytics",  name:"Analytics",        ico:"📈", color:"#7c3aed", tag:"Charts",     tagBg:"#ede9fe", tagColor:"#5b21b6", desc:"Charts + summary tables." },
				{ id:"settings",   name:"Settings Page",    ico:"⚙️", color:"#374151", tag:"Config",     tagBg:"#f3f4f6", tagColor:"#111827", desc:"App configuration with sections." },
				{ id:"wizard",     name:"Multi-step Wizard",ico:"🧙", color:"#b45309", tag:"Workflow",   tagBg:"#fef3c7", tagColor:"#92400e", desc:"Guided step-by-step workflow." },
				{ id:"kanban",     name:"Kanban Board",     ico:"🗃️", color:"#be185d", tag:"Board",      tagBg:"#fce7f3", tagColor:"#9d174d", desc:"Drag-drop card board by status." },
				{ id:"import_export",name:"Import / Export",ico:"⬆️", color:"#0891b2", tag:"Tools",      tagBg:"#cffafe", tagColor:"#155e75", desc:"CSV/Excel import + export tooling." },
				{ id:"approval_inbox", name:"Approval Inbox",    ico:"✅", color:"#15803d", tag:"Workflow",  tagBg:"#dcfce7", tagColor:"#14532d", desc:"Pending approvals queue with batch approve/reject." },
				{ id:"report_viewer",  name:"Report Viewer",     ico:"📊", color:"#0369a1", tag:"Reports",   tagBg:"#e0f2fe", tagColor:"#0c4a6e", desc:"Dynamic filters + tabular report + CSV export." },
				{ id:"calendar_view",  name:"Calendar View",     ico:"📅", color:"#9333ea", tag:"Planning",  tagBg:"#f3e8ff", tagColor:"#581c87", desc:"Month/week calendar with event create & drill-down." },
				{ id:"audit_trail",    name:"Audit Trail",       ico:"🔍", color:"#374151", tag:"Admin",     tagBg:"#f3f4f6", tagColor:"#111827", desc:"Filterable activity log with diff viewer." },
				{ id:"notification_center",name:"Notification Hub",ico:"🔔", color:"#b45309", tag:"Admin",  tagBg:"#fef3c7", tagColor:"#92400e", desc:"Read/unread notifications with bulk mark + filter." },
				{ id:"bulk_ops",       name:"Bulk Operations",   ico:"⚡", color:"#dc2626", tag:"Tools",     tagBg:"#fee2e2", tagColor:"#991b1b", desc:"Select records, choose action, run with progress bar." },
				/* ── Advanced UI/UX desk layouts ── */
				{ id:"app_shell_sidebar", name:"App Shell + Sidebar", ico:"◧",  color:"#1d4ed8", tag:"Advanced", tagBg:"#dbeafe", tagColor:"#1e40af", desc:"Fixed sidebar nav + top header + tabbed content. Full app-shell with CSS vars." },
				{ id:"split_explorer",    name:"Split Explorer",      ico:"⫿",  color:"#0891b2", tag:"Advanced", tagBg:"#cffafe", tagColor:"#155e75", desc:"Resizable split pane: filterable list left, full detail view right with tabs." },
				{ id:"adv_dashboard",     name:"Adv. Dashboard",      ico:"📊", color:"#6d28d9", tag:"Advanced", tagBg:"#ede9fe", tagColor:"#5b21b6", desc:"Chart.js area chart + KPI row with trends + activity feed + quick-action panel." },
			];

			let _selPreset = 'blank';
			let _mods = [];

			// Fetch modules then open dialog
			frappe.call({
				method: 'frappe_devkit.api.page_builder.list_app_modules',
				args: { app: _app },
				callback: r => {
					_mods = r.message?.modules || [];

					const $dlg = $(`<div style="padding:4px 0">
						<div class="dkpp-preset-grid" id="desk-pg"></div>
						<hr style="border-color:#ede9fe;margin:10px 0">
						<div style="display:grid;grid-template-columns:1fr 1fr 1fr;gap:10px;margin-bottom:4px">
							<div>
								<label style="font-size:11px;font-weight:700;color:#5c4da8;display:block;margin-bottom:4px">Module *</label>
								<select id="desk-new-mod" class="dkst-inp" style="width:100%">
									<option value="">— select module —</option>
									${_mods.map(m=>`<option value="${m}">${m}</option>`).join('')}
								</select>
							</div>
							<div>
								<label style="font-size:11px;font-weight:700;color:#5c4da8;display:block;margin-bottom:4px">Page ID *</label>
								<input id="desk-new-name" class="dkst-inp" placeholder="my-dashboard" style="width:100%">
								<div style="font-size:10px;color:#9080b8;margin-top:3px">Letters, numbers, hyphens</div>
							</div>
							<div>
								<label style="font-size:11px;font-weight:700;color:#5c4da8;display:block;margin-bottom:4px">Page Title *</label>
								<input id="desk-new-title" class="dkst-inp" placeholder="My Dashboard" style="width:100%">
							</div>
						</div>
					</div>`);

					const d = new frappe.ui.Dialog({
						title: '✨ New Desk Page',
						fields: [{ fieldtype:'HTML', options: $dlg[0].outerHTML }],
						primary_action_label: 'Create Page',
						primary_action() {
							const mod   = d.$wrapper.find('#desk-new-mod').val();
							const pname = d.$wrapper.find('#desk-new-name').val().trim();
							const ptitle= d.$wrapper.find('#desk-new-title').val().trim();
							if (!mod)    { frappe.show_alert({ message:'Select a module', indicator:'orange' }); return; }
							if (!pname)  { frappe.show_alert({ message:'Page ID required', indicator:'orange' }); return; }
							if (!ptitle) { frappe.show_alert({ message:'Page Title required', indicator:'orange' }); return; }
							d.hide();
							frappe.call({
								method: 'frappe_devkit.api.page_builder.create_desk_page',
								args: { app:_app, module:mod, page_name:pname, title:ptitle, preset:_selPreset },
								callback: r => {
									if (r.message?.created) {
										frappe.show_alert({ message:`✅ Page '${pname}' created`, indicator:'green' }, 4);
										frappe.call({
											method: 'frappe_devkit.api.page_builder.list_desk_pages',
											args: { app: _app },
											callback: r2 => {
												_pages = r2.message?.pages || []; _renderPgList($pgSearch.val());
												const newPg = _pages.find(p => p.name === pname);
												if (newPg) _openPage(newPg);
											}
										});
									}
								}
							});
						}
					});
					d.show();

					// Render preset cards after dialog shown
					const $pg2 = d.$wrapper.find('#desk-pg');
					DESK_PRESETS.forEach(pr => {
						$(`<div class="dkpp-preset-card${pr.id==='blank'?' selected':''}" data-pid="${pr.id}" style="position:relative">
							<div class="dkpp-preset-top" style="background:${pr.color}"></div>
							<div class="dkpp-preset-body">
								<div class="dkpp-preset-ico">${pr.ico}</div>
								<div class="dkpp-preset-nm">${pr.name}</div>
								<div class="dkpp-preset-ds">${pr.desc}</div>
								<div class="dkpp-preset-tag" style="background:${pr.tagBg};color:${pr.tagColor}">${pr.tag}</div>
							</div>
						</div>`).appendTo($pg2).on('click', function() {
							$pg2.find('.dkpp-preset-card').removeClass('selected');
							$(this).addClass('selected');
							_selPreset = pr.id;
							if (!d.$wrapper.find('#desk-new-name').val()) {
								d.$wrapper.find('#desk-new-name').val(pr.id.replace(/_/g,'-'));
								d.$wrapper.find('#desk-new-title').val(pr.name);
							}
						});
					});
				}
			});
		});

		/* ── delete page ── */
		$delDeskBtn.on('click', function() {
			if (!_curPage || !_app) return;
			frappe.confirm(`Delete desk page "<b>${frappe.utils.escape_html(_curPage.name)}</b>" and all its files? This cannot be undone.`, () => {
				frappe.call({
					method: 'frappe_devkit.api.page_builder.delete_desk_page',
					args: { app: _app, rel_page_path: _curPage.path },
					callback: r => {
						if (r.message?.deleted) {
							frappe.show_alert({ message:`Page '${_curPage.name}' deleted`, indicator:'red' }, 3);
							_pages = _pages.filter(p => p.name !== _curPage.name);
							_curPage = null; _activeFile = null;
							$fileTabs.hide(); $edWrap.hide(); $emptyMsg.show();
							$delDeskBtn.prop('disabled', true);
							$editDeskBtn.prop('disabled', true);
							$saveBtn.prop('disabled', true);
							_renderPgList($pgSearch.val());
						}
					}
				});
			});
		});

		/* ── edit (update) page metadata ── */
		$editDeskBtn.on('click', function() {
			if (!_curPage || !_app) return;
			frappe.call({
				method: 'frappe_devkit.api.page_builder.get_desk_page_meta',
				args: { app: _app, rel_page_path: _curPage.path },
				callback: r => {
					if (!r.message) return;
					const { title, roles } = r.message;
					frappe.prompt([
						{ label:'Page Title', fieldname:'title', fieldtype:'Data', reqd:1,
						  default: title,
						  description:'Human-readable title shown in the desk sidebar' },
						{ label:'Roles (comma-separated)', fieldname:'roles', fieldtype:'Data',
						  default: roles.join(', '),
						  description:'e.g. System Manager, Administrator' },
					], values => {
						const roleList = values.roles
							? values.roles.split(',').map(r => r.trim()).filter(Boolean)
							: [];
						frappe.call({
							method: 'frappe_devkit.api.page_builder.update_desk_page_meta',
							args: {
								app: _app,
								rel_page_path: _curPage.path,
								title: values.title,
								roles: JSON.stringify(roleList),
							},
							callback: r2 => {
								if (r2.message?.updated) {
									frappe.show_alert({ message:`Updated: ${_curPage.name}`, indicator:'green' }, 3);
									// Refresh the .json model if it is open
									const jsonFile = _curPage.name + '.json';
									if (_openFiles[jsonFile] !== undefined) {
										delete _openFiles[jsonFile];
										if (_deskModels[jsonFile]) {
											try { _deskModels[jsonFile].dispose(); } catch(e) {}
											delete _deskModels[jsonFile];
										}
										if (_activeFile === jsonFile) _openFile(jsonFile);
									}
								}
							}
						});
					}, 'Edit Desk Page', 'Update');
				}
			});
		});

		$appSel.on('change', function() {
			_app = this.value; _pages = []; _curPage = null;
			$fileTabs.hide(); $edWrap.hide(); $emptyMsg.show();
			$delDeskBtn.prop('disabled', true);
			$editDeskBtn.prop('disabled', true);
			$tb.find('.dkst-ce-link').toggleClass('visible', !!_app);
			if (_mcInstance) {
				Object.values(_deskModels).forEach(m => { try { m.dispose(); } catch(e) {} });
			}
			Object.keys(_deskModels).forEach(k => delete _deskModels[k]);
			if (!_app) { _renderPgList(''); return; }
			frappe.call({
				method: 'frappe_devkit.api.page_builder.list_desk_pages',
				args: { app: _app },
				callback: r => { _pages = r.message?.pages||[]; _renderPgList($pgSearch.val()); },
				error: () => { $pgList.html('<div class="dkpb-empty" style="font-size:11.5px;color:#c0392b">Failed to load</div>'); }
			});
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
	function icoDatabase(s){return _svg(`<ellipse cx="12" cy="5" rx="9" ry="3"/><path d="M21 12c0 1.66-4 3-9 3s-9-1.34-9-3"/><path d="M3 5v14c0 1.66 4 3 9 3s9-1.34 9-3V5"/>`,s);}
	function icoPlay(s)    {return _svg(`<polygon points="5 3 19 12 5 21 5 3"/>`,s);}
	function icoStop(s)    {return _svg(`<rect x="3" y="3" width="18" height="18" rx="2"/>`,s);}
	function icoDownload(s){return _svg(`<path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="7 10 12 15 17 10"/><line x1="12" y1="15" x2="12" y2="3"/>`,s);}
	function icoTable(s)   {return _svg(`<rect x="3" y="3" width="18" height="18" rx="2"/><path d="M3 9h18M3 15h18M9 3v18M15 3v18"/>`,s);}
	function icoHistory(s) {return _svg(`<polyline points="1 4 1 10 7 10"/><path d="M3.51 15a9 9 0 1 0 .49-4.95"/>`,s);}
	function icoMonitor(s) {return _svg(`<rect x="2" y="3" width="20" height="14" rx="2" ry="2"/><line x1="8" y1="21" x2="16" y2="21"/><line x1="12" y1="17" x2="12" y2="21"/>`,s);}
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
