/**
 * DevKit Code Editor
 * Professional VS Code-like editor for Frappe apps
 * Features: Monaco Editor, file tree, multi-tab, search, git, themes, settings
 */
frappe.pages['devkit-code-editor'].on_page_load = function (wrapper) {
    frappe.ui.make_app_page({ parent: wrapper, title: 'Code Editor', single_column: true });
    const ce = new DevKitCodeEditor(wrapper);
    ce.init();
    wrapper._dkce = ce;
};

// Bump this string whenever the layout HTML or CSS changes so that
// a stale DOM (built by an older version of this JS) is automatically torn down
// and rebuilt without the user needing a hard refresh.
const _DKCE_VERSION = '2025-03-26-v20';

frappe.pages['devkit-code-editor'].on_page_show = function (wrapper) {
    // Ensure Studio overlay (and any other fixed DevKit overlay) is hidden
    const studioRoot = document.getElementById('dkst-root');
    if (studioRoot) studioRoot.style.display = 'none';

    // Tear down stale DOM built by an older version of this file
    const existingRoot = document.getElementById('dkce-root');
    if (existingRoot && existingRoot.dataset.dkceVersion !== _DKCE_VERSION) {
        existingRoot.remove();
        document.getElementById('dkce-style') && document.getElementById('dkce-style').remove();
        wrapper._dkce = null;
    }

    // If the root was removed (or never existed) rebuild the editor from scratch
    if (!document.getElementById('dkce-root')) {
        const ce = new DevKitCodeEditor(wrapper);
        // Pick up app pre-selection from Studio link
        if (frappe.route_options && frappe.route_options.open_app) {
            ce._pendingApp = frappe.route_options.open_app;
            frappe.route_options = null;
        }
        ce.init();
        wrapper._dkce = ce;
        return;
    }

    // Handle open_app when editor is already loaded
    if (frappe.route_options && frappe.route_options.open_app) {
        const app = frappe.route_options.open_app;
        frappe.route_options = null;
        const ce = wrapper._dkce;
        if (ce) ce._selectApp(app);
    }

    // Recalculate navbar offset (height can change, e.g. after collapse)
    const nb = document.querySelector('.navbar');
    if (nb) document.getElementById('dkce-root').style.top = nb.offsetHeight + 'px';

    $('#dkce-root').show();
    const ce = wrapper._dkce;
    if (!ce) return;

    if (ce.editor) {
        requestAnimationFrame(() => {
            ce.editor.layout();
            ce.monaco && ce.monaco.editor.setTheme(ce.state.theme);
        });
    } else if (!ce._monacoLoading) {
        ce._loadMonaco();
    }
};

frappe.pages['devkit-code-editor'].on_page_hide = function () {
    $('#dkce-root').hide();
};

// ─────────────────────────────────────────────────────────────────────────────
// Main Editor Class
// ─────────────────────────────────────────────────────────────────────────────
class DevKitCodeEditor {
    constructor(wrapper) {
        this.wrapper = wrapper;
        this.monaco = null;         // monaco namespace
        this.editor = null;         // monaco editor instance

        this.state = {
            currentApp: '',
            tabs: [],               // [{id, appName, filePath, fileName, language, model, viewState, isModified, origContent}]
            activeTabId: null,
            sidePanel: 'explorer',  // explorer | search | git
            treeCache: {},          // path -> items
            expandedPaths: new Set(),
            selectedDir: '',
            clipboard: null,        // { path, isDir } — copy/paste
            gitInfo: { branch: '', changes: {} },
            theme: 'vs-dark',
            settings: {
                fontSize: 14,
                minimap: true,
                wordWrap: 'off',
                tabSize: 4,
                insertSpaces: true,
                lineNumbers: 'on',
                autoSave: false,
                renderWhitespace: 'none',
                smoothScrolling: true,
                sidebarWidth: 260,   // px — file explorer panel width
                treeFontSize: 13,    // px — file tree item font size
                toolbarSize:  'normal', // 'compact' | 'normal' | 'large'
            },
            terminal: {
                visible: false,
                height: 220,        // px
                cwd: '',            // relative to bench root
                history: [],        // command history
                historyIdx: -1,     // navigation index
                running: false,     // command in progress
            },
        };
    }

    // ── Entry point ────────────────────────────────────────────────────────
    init() {
        this._loadPersistedSettings();   // must run before _buildLayout
        this._injectStyles();
        this._buildLayout();
        this._bindEvents();
        this._loadApps();
        this._loadMonaco();
        // Apply all settings (sidebar width, tree font, editor options, theme)
        requestAnimationFrame(() => this._applySettings());
    }

    // ── Styles ─────────────────────────────────────────────────────────────
    _injectStyles() {
        // Always replace so code updates take effect without a hard refresh
        const existing = document.getElementById('dkce-style');
        if (existing) existing.remove();
        const s = document.createElement('style');
        s.id = 'dkce-style';
        s.textContent = `
/* Hide Frappe chrome — scoped to this page only so it never breaks other pages */
#page-devkit-code-editor .page-head,
#page-devkit-code-editor .page-head-content { display: none !important; }
#page-devkit-code-editor .layout-main-section-wrapper { padding: 0 !important; margin: 0 !important; }
#page-devkit-code-editor .layout-main { padding: 0 !important; }
#page-devkit-code-editor .page-content { padding: 0 !important; }

/* Root */
.dkce-root {
    position: fixed; inset: 60px 0 0 0;
    display: flex; flex-direction: column;
    background: #1e1e1e; color: #cccccc;
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
    font-size: 13px; z-index: 100; overflow: hidden;
}
.dkce-root.light { background: #fff; color: #333; }

/* ── Toolbar ── */
.dkce-toolbar {
    display: flex; align-items: center; gap: 2px;
    background: #2d2d2d; padding: 3px 8px;
    border-bottom: 1px solid #1e1e1e; flex-shrink: 0;
    height: var(--dkce-tb-h, 36px);
}
.dkce-root.light .dkce-toolbar { background: #f0f0f0; border-color: #ddd; }
.dkce-tb-sep { width: 1px; height: 18px; background: #454545; margin: 0 4px; }
.dkce-root.light .dkce-tb-sep { background: #ccc; }
.dkce-tb-btn {
    background: none; border: none; color: #ccc; cursor: pointer;
    padding: 3px 9px; border-radius: 4px; font-size: var(--dkce-tb-fs, 13px);
    display: flex; align-items: center; gap: 4px; white-space: nowrap;
    transition: background .12s, color .12s;
}
.dkce-tb-btn:hover { background: #454545; color: #fff; }
.dkce-root.light .dkce-tb-btn { color: #555; }
.dkce-root.light .dkce-tb-btn:hover { background: #ddd; color: #000; }
.dkce-tb-btn.active { background: #1a1a1a; color: #fff; }
#dkce-btn-terminal.active { background: #0a1520; color: #60cdff; border: 1px solid #1e3a52; }
/* ── Professional back button ── */
#dkce-btn-back {
    display: flex; align-items: center; gap: 5px;
    background: #1a1a2e; border: 1px solid #3a3a5c; color: #9ba4f4;
    padding: 5px 10px; border-radius: 4px; font-size: 12px; font-weight: 500;
    cursor: pointer; transition: background .12s, border-color .12s, color .12s;
}
#dkce-btn-back:hover { background: #2a2a4e; border-color: #6366f1; color: #c7d0ff; }
.dkce-root.light #dkce-btn-back { background: #ededff; border-color: #9ba4f4; color: #4f46e5; }
.dkce-root.light #dkce-btn-back:hover { background: #dde0ff; border-color: #4f46e5; }
/* ── App searchable dropdown ── */
.dkce-app-dd { position: relative; min-width: 160px; }
.dkce-app-dd-trigger {
    display: flex; align-items: center; gap: 4px;
    background: #2d2d2d; color: #ccc; border: 1px solid #555;
    border-radius: 3px; padding: 5px 6px 5px 8px; font-size: 12px; cursor: pointer;
    min-width: 160px; user-select: none; white-space: nowrap;
}
.dkce-app-dd-trigger:hover { border-color: #888; }
.dkce-app-dd-trigger .dkce-app-dd-label { flex: 1; overflow: hidden; text-overflow: ellipsis; }
.dkce-app-dd-trigger .dkce-app-dd-arrow { font-size: 9px; color: #888; flex-shrink: 0; }
.dkce-app-dd-popup {
    position: absolute; top: calc(100% + 3px); left: 0; z-index: 9000;
    background: #252526; border: 1px solid #555; border-radius: 4px;
    min-width: 200px; max-width: 320px; box-shadow: 0 4px 16px rgba(0,0,0,0.5);
    display: none; flex-direction: column;
}
.dkce-app-dd-popup.open { display: flex; }
.dkce-app-dd-search {
    margin: 6px 6px 4px; padding: 4px 8px; background: #3c3c3c; border: 1px solid #555;
    border-radius: 3px; color: #ccc; font-size: 12px; outline: none;
}
.dkce-app-dd-search::placeholder { color: #777; }
.dkce-app-dd-list { overflow-y: auto; max-height: 480px; padding-bottom: 4px; }
.dkce-app-dd-item {
    padding: 5px 10px; font-size: 12px; color: #ccc; cursor: pointer; white-space: nowrap;
}
.dkce-app-dd-item:hover, .dkce-app-dd-item.focused { background: #094771; color: #fff; }
.dkce-app-dd-item.selected { color: #73c9a0; }
.dkce-app-dd-empty { padding: 6px 10px; font-size: 11px; color: #666; font-style: italic; }
.dkce-root.light .dkce-app-dd-trigger { background: #fff; color: #333; border-color: #ccc; }
.dkce-root.light .dkce-app-dd-popup { background: #fff; border-color: #ccc; box-shadow: 0 4px 12px rgba(0,0,0,0.15); }
.dkce-root.light .dkce-app-dd-search { background: #f5f5f5; border-color: #ccc; color: #333; }
.dkce-root.light .dkce-app-dd-item { color: #333; }
.dkce-root.light .dkce-app-dd-item:hover, .dkce-root.light .dkce-app-dd-item.focused { background: #dde8f5; color: #000; }
.dkce-tb-spacer { flex: 1; }
.dkce-font-sz { color: #ccc; font-size: 12px; padding: 0 4px; min-width: 28px; text-align: center; }
.dkce-root.light .dkce-font-sz { color: #555; }

/* ── Body ── */
.dkce-body { flex: 1; display: flex; overflow: hidden; min-height: 0; }

/* ── Activity bar ── */
.dkce-act-bar {
    width: 46px; background: #333; display: flex; flex-direction: column;
    align-items: center; padding-top: 4px; flex-shrink: 0; gap: 2px;
}
.dkce-root.light .dkce-act-bar { background: #e8e8e8; }
.dkce-act-btn {
    width: 42px; height: 42px; display: flex; align-items: center;
    justify-content: center; cursor: pointer; border-radius: 4px;
    color: #aaa; transition: color .1s, background .1s;
    font-size: 20px; border: none; background: none; position: relative;
}
.dkce-act-btn:hover { color: #fff; background: #404040; }
.dkce-act-btn.active { color: #fff; background: #094771; }
.dkce-root.light .dkce-act-btn { color: #666; }
.dkce-root.light .dkce-act-btn:hover { color: #000; background: #ddd; }
.dkce-root.light .dkce-act-btn.active { color: #fff; background: #005fb8; }

/* ── Sidebar ── */
.dkce-root { --dkce-sidebar-w: 260px; --dkce-tree-fs: 13px; }
.dkce-sidebar {
    width: var(--dkce-sidebar-w, 260px); background: #252526; display: flex; flex-direction: column;
    overflow: hidden; flex-shrink: 0; border-right: 1px solid #1e1e1e;
    transition: width .15s;
}
.dkce-sidebar.collapsed { width: 0; }
.dkce-root.light .dkce-sidebar { background: #f3f3f3; border-color: #ddd; }
.dkce-sidebar-resize {
    width: 4px; cursor: col-resize; flex-shrink: 0; background: transparent; z-index: 10;
}
.dkce-sidebar-resize:hover, .dkce-sidebar-resize.dragging { background: rgba(0,122,204,.55); }

.dkce-panel-hdr {
    padding: 7px 12px; font-size: 11px; font-weight: 700;
    letter-spacing: .08em; color: #bbb; text-transform: uppercase;
    border-bottom: 1px solid #1e1e1e; flex-shrink: 0; user-select: none;
    display: flex; align-items: center; justify-content: space-between;
}
.dkce-root.light .dkce-panel-hdr { color: #666; border-color: #ddd; }
.dkce-panel-hdr-btn {
    background: none; border: none; color: #888; cursor: pointer;
    padding: 2px; border-radius: 3px; font-size: 14px;
}
.dkce-panel-hdr-btn:hover { color: #ccc; background: #3c3c3c; }

/* File tree */
.dkce-file-tree {
    flex: 1; overflow-y: auto; overflow-x: hidden; padding: 4px 0;
}
.dkce-file-tree::-webkit-scrollbar { width: 6px; }
.dkce-file-tree::-webkit-scrollbar-thumb { background: #555; border-radius: 3px; }
.dkce-tree-item {
    display: flex; align-items: center; padding: 1px 4px;
    cursor: pointer; user-select: none; color: #ccc; position: relative;
    height: 22px; border-radius: 2px; margin: 0 2px;
}
.dkce-tree-item:hover { background: #2a2d2e; }
.dkce-tree-item.active { background: #094771 !important; color: #fff; }
.dkce-root.light .dkce-tree-item { color: #333; }
.dkce-root.light .dkce-tree-item:hover { background: #e4e4e4; }
.dkce-root.light .dkce-tree-item.active { background: #b8d4e8 !important; color: #000; }
.dkce-tree-arr {
    width: 16px; flex-shrink: 0; text-align: center; font-size: 10px;
    color: #888; transition: transform .15s; display: inline-block;
}
.dkce-tree-arr.open { transform: rotate(90deg); }
.dkce-tree-icon { margin-right: 5px; font-size: 14px; flex-shrink: 0; }
.dkce-tree-name {
    flex: 1; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;
    font-size: var(--dkce-tree-fs, 13px);
}
.dkce-tree-item { height: auto; min-height: 22px; }
.dkce-tree-icon { font-size: calc(var(--dkce-tree-fs, 13px) + 1px); }
.dkce-tree-badge {
    font-size: 10px; font-weight: bold; margin-left: 4px; flex-shrink: 0;
}
.dkce-git-M { color: #e2a91b; }
.dkce-git-A { color: #73c991; }
.dkce-git-D { color: #f44747; }
.dkce-git-U { color: #75beff; }
.dkce-tree-children { padding-left: 0; }
.dkce-tree-loading {
    padding: 6px 16px; color: #888; font-size: 12px; font-style: italic;
}

/* Panels */
.dkce-panel { display: none; flex-direction: column; flex: 1; overflow: hidden; }
.dkce-panel.active { display: flex; }

/* Search panel */
.dkce-search-wrap { padding: 8px; border-bottom: 1px solid #1e1e1e; flex-shrink: 0; }
.dkce-search-inp {
    width: 100%; background: #3c3c3c; border: 1px solid #555; color: #ccc;
    padding: 5px 8px; border-radius: 3px; font-size: 12px; margin-bottom: 4px;
    box-sizing: border-box;
}
.dkce-search-inp:focus { outline: none; border-color: #007acc; }
.dkce-root.light .dkce-search-inp { background: #fff; color: #333; border-color: #ccc; }
.dkce-search-opts { display: flex; gap: 6px; align-items: center; }
.dkce-search-opt-label { font-size: 11px; color: #888; }
.dkce-search-opt-inp { background: #3c3c3c; border: 1px solid #555; color: #ccc; padding: 3px 6px; border-radius: 3px; font-size: 11px; flex: 1; }
.dkce-search-btn { padding: 3px 10px; background: #0e639c; border: none; color: #fff; border-radius: 3px; cursor: pointer; font-size: 11px; }
.dkce-search-btn:hover { background: #1177bb; }
.dkce-search-results { overflow-y: auto; flex: 1; padding: 4px 0; }
.dkce-search-results::-webkit-scrollbar { width: 5px; }
.dkce-search-results::-webkit-scrollbar-thumb { background: #555; border-radius: 3px; }
.dkce-search-file-hdr {
    padding: 4px 8px; font-weight: bold; color: #ccc; cursor: pointer;
    font-size: 12px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
}
.dkce-search-file-hdr:hover { background: #2a2d2e; }
.dkce-search-match {
    padding: 2px 8px 2px 20px; cursor: pointer; color: #969696;
    font-size: 12px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
    font-family: 'Consolas', 'Monaco', monospace;
}
.dkce-search-match:hover { background: #2a2d2e; color: #ccc; }
.dkce-hl { background: #c18a1b; color: #000; border-radius: 2px; }
.dkce-search-count { padding: 4px 8px; color: #888; font-size: 11px; }

/* Git panel */
.dkce-git-scroll { overflow-y: auto; flex: 1; }
.dkce-git-file {
    display: flex; align-items: center; padding: 3px 8px; cursor: pointer;
    font-size: 12px; color: #ccc; gap: 6px;
}
.dkce-git-file:hover { background: #2a2d2e; }
.dkce-git-code { font-size: 11px; font-weight: bold; width: 18px; text-align: center; flex-shrink: 0; }
.dkce-git-fname { flex: 1; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.dkce-git-branch { padding: 6px 10px; font-size: 12px; color: #888; border-bottom: 1px solid #1e1e1e; }

/* ── Editor area ── */
.dkce-editor-area { flex: 1; display: flex; flex-direction: column; overflow: hidden; min-width: 0; min-height: 0; }

/* Tab bar */
.dkce-tab-bar {
    display: flex; background: #2d2d2d; overflow-x: auto;
    flex-shrink: 0; height: 35px; border-bottom: 1px solid #252526;
    scrollbar-width: thin;
}
.dkce-tab-bar::-webkit-scrollbar { height: 4px; }
.dkce-tab-bar::-webkit-scrollbar-thumb { background: #555; border-radius: 2px; }
.dkce-root.light .dkce-tab-bar { background: #ececec; border-color: #ddd; }
.dkce-tab {
    display: flex; align-items: center; padding: 0 10px;
    min-width: 100px; max-width: 200px; cursor: pointer;
    border-right: 1px solid #1e1e1e; white-space: nowrap;
    font-size: 12px; color: #969696; background: #2d2d2d;
    flex-shrink: 0; gap: 6px; position: relative;
    transition: background .1s;
}
.dkce-tab:hover { background: #1e1e1e; color: #ccc; }
.dkce-tab.active { background: #1e1e1e; color: #fff; border-top: 2px solid #007acc; }
.dkce-root.light .dkce-tab { background: #ececec; color: #777; border-color: #ddd; }
.dkce-root.light .dkce-tab.active { background: #fff; color: #333; border-top-color: #005fb8; }
.dkce-tab-icon { font-size: 14px; flex-shrink: 0; }
.dkce-tab-name { flex: 1; overflow: hidden; text-overflow: ellipsis; max-width: 130px; }
.dkce-tab-dot {
    width: 7px; height: 7px; border-radius: 50%; background: #e2a91b;
    flex-shrink: 0; display: none;
}
.dkce-tab.modified .dkce-tab-dot { display: block; }
.dkce-tab-close {
    width: 16px; height: 16px; display: flex; align-items: center;
    justify-content: center; border-radius: 3px; opacity: 0;
    font-size: 13px; flex-shrink: 0; color: #ccc; transition: opacity .1s;
}
.dkce-tab:hover .dkce-tab-close, .dkce-tab.active .dkce-tab-close { opacity: 0.6; }
.dkce-tab-close:hover { opacity: 1 !important; background: #555; }

/* Editor container */
.dkce-editor-wrap { flex: 1; overflow: hidden; position: relative; min-height: 0; }
.dkce-editor-container { width: 100%; height: 100%; min-height: 0; }
.dkce-breadcrumb {
    padding: 2px 12px; font-size: 11px; color: #888; background: #1e1e1e;
    border-bottom: 1px solid #2d2d2d; white-space: nowrap; overflow: hidden;
    text-overflow: ellipsis; flex-shrink: 0; height: 20px; line-height: 20px;
}
.dkce-root.light .dkce-breadcrumb { background: #fff; color: #888; border-color: #ddd; }
.dkce-breadcrumb-sep { color: #555; margin: 0 4px; }

/* Empty state */
.dkce-empty {
    position: absolute; inset: 0; display: flex; flex-direction: column;
    align-items: center; justify-content: center; color: #555; user-select: none;
    gap: 10px;
}
.dkce-empty-icon { font-size: 48px; opacity: .4; }
.dkce-empty-title { font-size: 20px; font-weight: 300; }
.dkce-empty-sub { font-size: 13px; opacity: .6; }
.dkce-root.light .dkce-empty { color: #999; }

/* Status bar */
.dkce-statusbar {
    display: flex; align-items: center; background: #007acc; color: #fff;
    height: 22px; font-size: 12px; flex-shrink: 0; padding: 0 4px;
}
.dkce-root.light .dkce-statusbar { background: #005fb8; }
.dkce-sb-item {
    padding: 0 8px; cursor: pointer; height: 22px;
    display: flex; align-items: center; gap: 4px; white-space: nowrap;
    border-radius: 2px; transition: background .1s;
}
.dkce-sb-item:hover { background: rgba(255,255,255,.15); }
.dkce-sb-spacer { flex: 1; }
.dkce-sb-save { font-size: 11px; opacity: .8; }

/* Notifications */
.dkce-toast {
    position: fixed; bottom: 30px; right: 20px; z-index: 99999;
    padding: 8px 14px; border-radius: 4px; font-size: 12px; max-width: 360px;
    animation: dkce-in .2s ease; pointer-events: none;
}
@keyframes dkce-in { from { transform: translateX(30px); opacity: 0; } to { transform: none; opacity: 1; } }
.dkce-toast.success { background: #073922; border: 1px solid #2b6c40; color: #73c991; }
.dkce-toast.error   { background: #3a0707; border: 1px solid #7a1414; color: #f44747; }
.dkce-toast.info    { background: #041c2e; border: 1px solid #0d4a7a; color: #75beff; }
.dkce-toast.warn    { background: #2a1800; border: 1px solid #8a5000; color: #e2a91b; }

/* Context menu */
.dkce-ctx {
    position: fixed; background: #252526; border: 1px solid #454545;
    border-radius: 4px; padding: 4px 0; z-index: 99998; min-width: 180px;
    box-shadow: 0 4px 16px rgba(0,0,0,.5);
}
.dkce-ctx-item {
    padding: 6px 20px; font-size: 13px; color: #ccc; cursor: pointer;
    display: flex; align-items: center; gap: 8px;
}
.dkce-ctx-item:hover { background: #094771; color: #fff; }
.dkce-ctx-sep { height: 1px; background: #454545; margin: 4px 0; }
.dkce-root.light .dkce-ctx { background: #fff; border-color: #ccc; }
.dkce-root.light .dkce-ctx-item { color: #333; }
.dkce-root.light .dkce-ctx-item:hover { background: #0060c0; color: #fff; }

/* Settings dialog */
.dkce-overlay {
    position: fixed; inset: 0; background: rgba(0,0,0,.6);
    z-index: 99990; display: flex; align-items: center; justify-content: center;
}
.dkce-dialog {
    background: #252526; border: 1px solid #454545; border-radius: 8px;
    width: 480px; max-height: 80vh; overflow-y: auto; padding: 20px;
}
.dkce-root.light .dkce-dialog { background: #fff; border-color: #ccc; }
.dkce-dialog h3 { margin: 0 0 16px; font-size: 16px; color: #ccc; font-weight: 600; }
.dkce-root.light .dkce-dialog h3 { color: #333; }
.dkce-dialog-close { float: right; background: none; border: none; color: #888; cursor: pointer; font-size: 18px; }
.dkce-dialog-close:hover { color: #ccc; }
.dkce-setting-row { margin-bottom: 14px; }
.dkce-setting-row label { display: block; font-size: 12px; color: #aaa; margin-bottom: 5px; }
.dkce-root.light .dkce-setting-row label { color: #666; }
.dkce-setting-ctrl {
    width: 100%; background: #3c3c3c; border: 1px solid #555; color: #ccc;
    padding: 6px 10px; border-radius: 3px; font-size: 13px; box-sizing: border-box;
}
.dkce-setting-ctrl:focus { outline: none; border-color: #007acc; }
.dkce-root.light .dkce-setting-ctrl { background: #f5f5f5; color: #333; border-color: #ccc; }
.dkce-dialog-footer { margin-top: 20px; display: flex; justify-content: flex-end; gap: 8px; }
.dkce-dialog-btn {
    padding: 7px 18px; border-radius: 4px; border: none; cursor: pointer; font-size: 13px;
}
.dkce-dialog-btn.primary { background: #0e639c; color: #fff; }
.dkce-dialog-btn.primary:hover { background: #1177bb; }
.dkce-dialog-btn.secondary { background: #3c3c3c; color: #ccc; }
.dkce-dialog-btn.secondary:hover { background: #505050; }

/* Diff panel */
.dkce-diff-panel { flex: 1; overflow: auto; padding: 8px; }
.dkce-diff-line { font-family: monospace; font-size: 12px; white-space: pre; padding: 1px 4px; }
.dkce-diff-add { color: #73c991; background: rgba(115,201,145,.1); }
.dkce-diff-del { color: #f44747; background: rgba(244,71,71,.1); }
.dkce-diff-meta { color: #75beff; }

/* Scrollbar global */
::-webkit-scrollbar { width: 8px; height: 8px; }
::-webkit-scrollbar-track { background: transparent; }
::-webkit-scrollbar-thumb { background: #555; border-radius: 4px; }
::-webkit-scrollbar-thumb:hover { background: #777; }

/* ── Local History Panel ── */
.dkce-hist-scroll { overflow-y: auto; flex: 1; }
.dkce-hist-item { display: flex; align-items: center; padding: 5px 8px; font-size: 12px; color: #ccc; gap: 6px; border-bottom: 1px solid #1e1e1e; cursor: pointer; }
.dkce-hist-item:hover { background: #2a2d2e; }
.dkce-hist-item.active { background: #1e3a52; }
.dkce-hist-ts { flex: 1; font-size: 11px; color: #aaa; }
.dkce-hist-size { font-size: 10px; color: #666; flex-shrink: 0; }
.dkce-hist-btn { padding: 2px 8px; background: #094771; border: none; color: #fff; border-radius: 3px; cursor: pointer; font-size: 11px; flex-shrink: 0; }
.dkce-hist-btn:hover { background: #0e639c; }
.dkce-hist-btn-restore { padding: 2px 8px; background: #1e6a2e; border: none; color: #fff; border-radius: 3px; cursor: pointer; font-size: 11px; flex-shrink: 0; }
.dkce-hist-btn-restore:hover { background: #27903e; }
.dkce-hist-empty { padding: 12px 8px; color: #666; font-size: 12px; font-style: italic; }
.dkce-hist-file-info { padding: 5px 8px; font-size: 11px; color: #888; border-bottom: 1px solid #1e1e1e; word-break: break-all; flex-shrink: 0; }
/* ── History Diff Modal ── */
.dkce-hist-diff-overlay { position: fixed; inset: 0; z-index: 9999; background: rgba(0,0,0,0.75); display: flex; flex-direction: column; align-items: center; justify-content: center; }
.dkce-hist-diff-dialog { display: flex; flex-direction: column; width: 90vw; height: 85vh; background: #1e1e1e; border: 1px solid #444; border-radius: 6px; overflow: hidden; box-shadow: 0 8px 40px rgba(0,0,0,0.6); }
.dkce-hist-diff-header { display: flex; align-items: center; padding: 8px 14px; background: #252526; border-bottom: 1px solid #333; gap: 10px; flex-shrink: 0; }
.dkce-hist-diff-title { flex: 1; font-size: 13px; color: #ccc; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.dkce-hist-diff-labels { display: flex; gap: 20px; font-size: 11px; color: #888; flex-shrink: 0; }
.dkce-hist-diff-labels span { display: flex; align-items: center; gap: 5px; }
.dkce-hist-diff-labels .dot-old { width: 8px; height: 8px; border-radius: 50%; background: #c72e3a; display: inline-block; }
.dkce-hist-diff-labels .dot-new { width: 8px; height: 8px; border-radius: 50%; background: #2ea043; display: inline-block; }
.dkce-hist-diff-editor { flex: 1; min-height: 0; }
.dkce-hist-diff-footer { display: flex; align-items: center; justify-content: flex-end; padding: 8px 14px; background: #252526; border-top: 1px solid #333; gap: 8px; flex-shrink: 0; }
.dkce-hist-diff-close { padding: 4px 14px; background: #3c3c3c; border: 1px solid #555; color: #ccc; border-radius: 3px; cursor: pointer; font-size: 12px; }
.dkce-hist-diff-close:hover { background: #4c4c4c; }
.dkce-hist-diff-do-restore { padding: 4px 14px; background: #1e6a2e; border: none; color: #fff; border-radius: 3px; cursor: pointer; font-size: 12px; }
.dkce-hist-diff-do-restore:hover { background: #27903e; }

/* ── Claude AI Panel ── */
.dkce-claude-chat { flex: 1; overflow-y: auto; padding: 8px; display: flex; flex-direction: column; gap: 8px; }
.dkce-claude-chat::-webkit-scrollbar { width: 5px; }
.dkce-claude-chat::-webkit-scrollbar-thumb { background: #555; border-radius: 3px; }
.dkce-claude-msg { padding: 8px 10px; border-radius: 6px; font-size: 12px; line-height: 1.5; max-width: 96%; word-break: break-word; }
.dkce-claude-msg.user { background: #094771; color: #dde; align-self: flex-end; }
.dkce-claude-msg.assistant { background: #2d2d2d; color: #ccc; align-self: flex-start; }
.dkce-claude-msg.error-msg { background: #3a0707; color: #f44747; align-self: flex-start; }
.dkce-claude-msg pre { background: #1a1a1a; padding: 7px 9px; border-radius: 4px; overflow-x: auto; font-size: 11px; margin: 5px 0; border: 1px solid #333; }
.dkce-claude-msg code { background: #1a1a1a; padding: 1px 4px; border-radius: 2px; font-size: 11px; }
.dkce-claude-msg pre code { background: none; padding: 0; }
.dkce-claude-msg strong { color: #e2a91b; }
.dkce-claude-input-area { padding: 8px; border-top: 1px solid #1e1e1e; flex-shrink: 0; background: #252526; }
.dkce-claude-ctx-row { display: flex; align-items: center; gap: 6px; margin-bottom: 5px; }
.dkce-claude-ctx-label { font-size: 11px; color: #888; cursor: pointer; user-select: none; }
.dkce-claude-inp { width: 100%; background: #3c3c3c; border: 1px solid #555; color: #ccc; padding: 6px 8px; border-radius: 3px; font-size: 12px; resize: vertical; min-height: 56px; max-height: 150px; box-sizing: border-box; font-family: inherit; line-height: 1.4; }
.dkce-claude-inp:focus { outline: none; border-color: #007acc; }
.dkce-claude-actions { display: flex; justify-content: space-between; align-items: center; margin-top: 5px; }
.dkce-claude-send { padding: 5px 14px; background: #0e639c; border: none; color: #fff; border-radius: 3px; cursor: pointer; font-size: 12px; }
.dkce-claude-send:hover { background: #1177bb; }
.dkce-claude-send:disabled { background: #555; cursor: not-allowed; }
.dkce-claude-status { font-size: 11px; color: #888; }
/* Claude connect screen */
.dkce-claude-connect { padding: 16px 12px; display: flex; flex-direction: column; gap: 0; }
.dkce-claude-connect-logo { font-size: 32px; text-align: center; margin-bottom: 10px; }
.dkce-claude-connect-title { font-size: 14px; font-weight: 600; color: #ddd; text-align: center; margin-bottom: 4px; }
.dkce-claude-connect-sub { font-size: 11px; color: #888; text-align: center; margin-bottom: 14px; line-height: 1.5; }
.dkce-claude-connect-field { margin-bottom: 10px; }
.dkce-claude-connect-label { display: block; font-size: 11px; color: #aaa; margin-bottom: 4px; letter-spacing: .03em; }
.dkce-claude-connect-inp { width: 100%; background: #2d2d2d; border: 1px solid #555; color: #ddd; padding: 7px 10px; border-radius: 4px; font-size: 12px; box-sizing: border-box; transition: border-color .15s; }
.dkce-claude-connect-inp:focus { outline: none; border-color: #007acc; background: #333; }
.dkce-claude-connect-hint { font-size: 10px; color: #666; margin-top: 3px; }
.dkce-claude-connect-hint a { color: #75beff; cursor: pointer; text-decoration: none; }
.dkce-claude-connect-hint a:hover { text-decoration: underline; }
.dkce-claude-connect-btn { width: 100%; padding: 8px; background: #0e639c; border: none; color: #fff; border-radius: 4px; cursor: pointer; font-size: 13px; font-weight: 500; margin-top: 4px; transition: background .15s; }
.dkce-claude-connect-btn:hover { background: #1177bb; }
.dkce-claude-connect-btn:disabled { background: #555; cursor: not-allowed; }
.dkce-claude-connect-err { font-size: 11px; color: #f44747; margin-top: 6px; min-height: 14px; }
/* Claude connected status bar */
.dkce-claude-connected-bar { display: flex; align-items: center; gap: 6px; padding: 5px 8px; background: #073922; border-bottom: 1px solid #2b6c40; flex-shrink: 0; }
.dkce-claude-connected-dot { width: 7px; height: 7px; border-radius: 50%; background: #73c991; flex-shrink: 0; }
.dkce-claude-connected-info { flex: 1; font-size: 11px; color: #73c991; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.dkce-claude-disconnect-btn { background: none; border: 1px solid #2b6c40; color: #73c991; border-radius: 3px; padding: 1px 7px; font-size: 10px; cursor: pointer; flex-shrink: 0; }
.dkce-claude-disconnect-btn:hover { background: #0d5a34; }
/* Claude quick-action bar */
.dkce-claude-actions-bar { display: flex; flex-wrap: wrap; gap: 4px; padding: 6px 8px; border-bottom: 1px solid #1e1e1e; flex-shrink: 0; background: #1e1e1e; }
.dkce-claude-action-btn { padding: 3px 8px; background: #2d2d2d; border: 1px solid #444; color: #bbb; border-radius: 3px; cursor: pointer; font-size: 11px; white-space: nowrap; transition: background .1s, color .1s; }
.dkce-claude-action-btn:hover { background: #094771; border-color: #0e639c; color: #fff; }
/* Selection context badge */
.dkce-claude-sel-badge { display: none; align-items: center; gap: 5px; padding: 3px 8px; background: #1a2d1a; border: 1px solid #2b6c40; border-radius: 3px; font-size: 11px; color: #73c991; margin-bottom: 5px; }
.dkce-claude-sel-badge.visible { display: flex; }
.dkce-claude-sel-badge-clear { background: none; border: none; color: #73c991; cursor: pointer; font-size: 12px; padding: 0 2px; line-height: 1; }
/* Insert code button in responses */
.dkce-claude-msg .dkce-code-block-wrap { position: relative; }
.dkce-claude-msg .dkce-insert-btn { position: absolute; top: 4px; right: 4px; padding: 2px 7px; background: #094771; border: none; color: #fff; border-radius: 2px; font-size: 10px; cursor: pointer; opacity: 0; transition: opacity .15s; }
.dkce-claude-msg .dkce-code-block-wrap:hover .dkce-insert-btn { opacity: 1; }
.dkce-claude-msg .dkce-copy-btn { position: absolute; top: 4px; right: 62px; padding: 2px 7px; background: #333; border: 1px solid #555; color: #ccc; border-radius: 2px; font-size: 10px; cursor: pointer; opacity: 0; transition: opacity .15s; }
.dkce-claude-msg .dkce-code-block-wrap:hover .dkce-copy-btn { opacity: 1; }


/* ── Enhanced Git Actions ── */
.dkce-git-actions { padding: 5px 6px; display: flex; gap: 3px; flex-wrap: wrap; border-bottom: 1px solid #1e1e1e; flex-shrink: 0; background: #1e1e1e; }
.dkce-git-act-btn { padding: 3px 8px; border: 1px solid transparent; border-radius: 3px; cursor: pointer; font-size: 11px; white-space: nowrap; }
.dkce-git-act-btn.commit  { background: #094771; color: #75beff; border-color: #0a5288; }
.dkce-git-act-btn.commit:hover  { background: #0e639c; }
.dkce-git-act-btn.push    { background: #073922; color: #73c991; border-color: #2b6c40; }
.dkce-git-act-btn.push:hover    { background: #0d5a34; }
.dkce-git-act-btn.pull    { background: #041c2e; color: #75beff; border-color: #0d4a7a; }
.dkce-git-act-btn.pull:hover    { background: #073554; }
.dkce-git-act-btn.branch  { background: #2a1800; color: #e2a91b; border-color: #8a5000; }
.dkce-git-act-btn.branch:hover  { background: #3d2500; }
.dkce-git-act-btn.neutral { background: #2d2d2d; color: #ccc; border-color: #454545; }
.dkce-git-act-btn.neutral:hover { background: #3c3c3c; }
.dkce-git-act-btn.stage-all   { background: #073922; color: #73c991; border-color: #2b6c40; }
.dkce-git-act-btn.stage-all:hover   { background: #0d5a34; }
.dkce-git-act-btn.unstage-all { background: #2a1800; color: #e2a91b; border-color: #8a5000; }
.dkce-git-act-btn.unstage-all:hover { background: #3d2500; }
.dkce-git-act-btn.discard-all { background: #3a0707; color: #f44747; border-color: #7a1414; }
.dkce-git-act-btn.discard-all:hover { background: #550a0a; }
.dkce-git-section-hdr { padding: 4px 8px; font-size: 10px; font-weight: 700; color: #777; text-transform: uppercase; letter-spacing: .06em; background: #1a1a1a; border-bottom: 1px solid #252526; flex-shrink: 0; }
.dkce-git-file-acts { display: flex; gap: 2px; flex-shrink: 0; }
.dkce-git-file-act { padding: 1px 6px; border: 1px solid transparent; border-radius: 2px; cursor: pointer; font-size: 10px; line-height: 14px; }
.dkce-git-file-act.stage   { background: #073922; color: #73c991; border-color: #2b6c40; }
.dkce-git-file-act.unstage { background: #2a1800; color: #e2a91b; border-color: #8a5000; }
.dkce-git-file-act.discard { background: #3a0707; color: #f44747; border-color: #7a1414; }
.dkce-gitlog-item { padding: 6px 8px; border-bottom: 1px solid #1e1e1e; }
.dkce-gitlog-hash { font-size: 10px; color: #75beff; font-family: monospace; }
.dkce-gitlog-msg { font-size: 12px; color: #ccc; margin: 2px 0; word-break: break-word; }
.dkce-gitlog-meta { font-size: 10px; color: #666; }

/* ── Terminal panel ── */
.dkce-terminal-panel {
    display: none; flex-direction: column;
    height: var(--dkce-term-h, 280px);
    border-top: 2px solid #007acc; background: #0d0d0d; flex-shrink: 0;
}
.dkce-terminal-panel.visible { display: flex; }
.dkce-terminal-resize {
    height: 4px; cursor: row-resize; flex-shrink: 0; background: transparent;
}
.dkce-terminal-resize:hover, .dkce-terminal-resize.dragging { background: rgba(0,122,204,.55); }
.dkce-terminal-hdr {
    display: flex; align-items: center; gap: 4px;
    background: #1e1e1e; padding: 2px 8px;
    border-bottom: 1px solid #2a2a2a; flex-shrink: 0; user-select: none;
}
.dkce-terminal-hdr-title { font-size: 11px; font-weight: 600; color: #aaa; margin-right: 4px; white-space: nowrap; letter-spacing: .04em; }
.dkce-term-shortcuts { display: flex; gap: 4px; flex: 1; overflow: hidden; align-items: center; }
.dkce-term-sc-btn {
    background: #b8b8c0; border: none; color: #1a1a1a;
    border-radius: 4px; padding: 0 10px; font-size: 11px; cursor: pointer;
    white-space: nowrap; line-height: 22px; height: 22px; flex-shrink: 0;
    font-family: 'Cascadia Code','Consolas',monospace; letter-spacing: 0;
    transition: background .1s, color .1s;
}
.dkce-term-sc-btn:hover { background: #cdcdd4; color: #111; }
.dkce-term-sc-btn:active { background: #a0a0a8; }
.dkce-terminal-hdr-btn {
    background: none; border: none; color: #606060; cursor: pointer;
    padding: 4px 7px; line-height: 1; border-radius: 3px;
    flex-shrink: 0; transition: background .12s, color .12s;
    display: flex; align-items: center; justify-content: center;
}
.dkce-terminal-hdr-btn:hover { background: #2d2d2d; color: #c0c0c0; }
/* Output area */
.dkce-terminal-output {
    flex: 1; overflow-y: auto; padding: 6px 14px 2px;
    font-family: 'Cascadia Code','Consolas','Courier New',monospace;
    font-size: 13px; line-height: 1.55; min-height: 0; color: #cccccc;
}
.dkce-terminal-output::-webkit-scrollbar { width: 8px; }
.dkce-terminal-output::-webkit-scrollbar-track { background: transparent; }
.dkce-terminal-output::-webkit-scrollbar-thumb { background: #333; border-radius: 4px; }
.dkce-term-row { display: block; white-space: pre-wrap; word-break: break-word; min-height: 1em; }
.dkce-term-row.prompt-row { color: #cccccc; }
.dkce-term-row.stderr-row { color: #f48771; }
.dkce-term-row.info-row { color: #75beff; font-style: italic; }
/* Input row */
.dkce-terminal-input-row {
    display: flex; align-items: center; gap: 0;
    padding: 4px 14px 6px; border-top: 1px solid #0a1e30;
    background: #071521; flex-shrink: 0; position: relative;
}
.dkce-term-prompt-label {
    color: #ffffff; font-family: 'Cascadia Code','Consolas',monospace;
    font-size: 13px; white-space: nowrap; user-select: none; flex-shrink: 0;
}
.dkce-term-dollar { color: #ffffff; margin: 0 6px 0 4px; flex-shrink: 0; user-select: none; }
.dkce-term-input {
    flex: 1; background: none; border: none; outline: none;
    color: #ffffff; font-family: 'Cascadia Code','Consolas',monospace;
    font-size: 13px; caret-color: #ffffff; padding: 0; min-width: 0;
}
/* Completion popup — anchored inside input-row */
.dkce-term-comp-popup {
    position: absolute; bottom: 100%; left: 14px;
    background: #252526; border: 1px solid #454545;
    border-radius: 4px; z-index: 9999; min-width: 240px; max-width: 480px;
    max-height: 200px; overflow-y: auto;
    box-shadow: 0 -4px 20px rgba(0,0,0,.7);
    font-family: 'Cascadia Code','Consolas',monospace; font-size: 12px;
    display: none;
}
.dkce-term-comp-popup.open { display: block; }
.dkce-term-comp-item {
    padding: 3px 12px; cursor: pointer; white-space: nowrap;
    color: #ccc; display: flex; align-items: center; gap: 6px;
}
.dkce-term-comp-item:hover, .dkce-term-comp-item.sel { background: #094771; color: #fff; }
.dkce-term-comp-icon { color: #75beff; width: 12px; text-align: center; flex-shrink: 0; }
.dkce-term-comp-name { flex: 1; }
.dkce-term-comp-tag { font-size: 10px; color: #555; }
.dkce-term-comp-item.sel .dkce-term-comp-tag { color: #aaa; }
/* light theme */
.dkce-root.light .dkce-terminal-panel { background: #f8f8f8; border-top-color: #005fb8; }
.dkce-root.light .dkce-terminal-hdr { background: #f0f0f0; border-color: #e0e0e0; }
.dkce-root.light .dkce-terminal-hdr-title { color: #444; }
.dkce-root.light .dkce-term-sc-btn { border-color: #ccc; color: #555; }
.dkce-root.light .dkce-term-sc-btn:hover { background: #e8e8e8; color: #222; border-color: #aaa; }
.dkce-root.light .dkce-terminal-output { color: #333; background: #f8f8f8; }
.dkce-root.light .dkce-terminal-input-row { background: #ffffff; border-color: #e0e0e0; }
.dkce-root.light .dkce-term-input { color: #222; caret-color: #222; }
.dkce-root.light .dkce-term-prompt-label { color: #007700; }
.dkce-root.light .dkce-term-dollar { color: #444; }
.dkce-root.light .dkce-term-comp-popup { background: #fff; border-color: #ccc; }
.dkce-root.light .dkce-term-comp-item { color: #333; }
.dkce-root.light .dkce-term-comp-item.sel { background: #0060c0; color: #fff; }
        `;
        document.head.appendChild(s);
    }

    // ── Layout ─────────────────────────────────────────────────────────────
    _buildLayout() {
        // Remove any stale instance (page revisit), then mount to body so
        // position:fixed works regardless of Frappe container overflow/transform
        $('#dkce-root').remove();
        const navTop = (document.querySelector('.navbar')?.offsetHeight || 60) + 'px';
        const html = `
<div class="dkce-root" id="dkce-root" data-dkce-version="${_DKCE_VERSION}" style="top:${navTop}">
  <!-- Toolbar -->
  <div class="dkce-toolbar">
    <button id="dkce-btn-back" title="Back to DevKit Studio (Alt+←)">‹ DevKit Studio</button>
    <div class="dkce-tb-sep"></div>
    <span style="color:#ccc;font-size:12px;font-weight:600;padding:0 6px;">App:</span>
    <div class="dkce-app-dd" id="dkce-app-dd">
      <div class="dkce-app-dd-trigger" id="dkce-app-dd-trigger">
        <span class="dkce-app-dd-label" id="dkce-app-dd-label">Loading…</span>
        <span class="dkce-app-dd-arrow">▾</span>
      </div>
      <div class="dkce-app-dd-popup" id="dkce-app-dd-popup">
        <input class="dkce-app-dd-search" id="dkce-app-dd-search" placeholder="Search apps…" autocomplete="off" spellcheck="false">
        <div class="dkce-app-dd-list" id="dkce-app-dd-list"></div>
      </div>
    </div>
    <div class="dkce-tb-sep"></div>
    <button class="dkce-tb-btn" id="dkce-btn-save" title="Save (Ctrl+S)">💾 Save</button>
    <button class="dkce-tb-btn" id="dkce-btn-new"  title="New File">+ New</button>
    <button class="dkce-tb-btn" id="dkce-btn-fmt"  title="Format Document (Alt+Shift+F)">⚡ Format</button>
    <div class="dkce-tb-sep"></div>
    <button class="dkce-tb-btn" id="dkce-btn-wrap"    title="Toggle Word Wrap (Alt+Z)">↩ Wrap</button>
    <button class="dkce-tb-btn" id="dkce-btn-minimap" title="Toggle Minimap">📍 Map</button>
    <div class="dkce-tb-sep"></div>
    <button class="dkce-tb-btn" id="dkce-btn-fz-dn" title="Decrease font">A-</button>
    <span class="dkce-font-sz" id="dkce-font-sz">14</span>
    <button class="dkce-tb-btn" id="dkce-btn-fz-up" title="Increase font">A+</button>
    <div class="dkce-tb-sep"></div>
    <button class="dkce-tb-btn" id="dkce-btn-theme"    title="Toggle Light/Dark Theme">🌙 Theme</button>
    <button class="dkce-tb-btn" id="dkce-btn-settings" title="Settings">⚙ Settings</button>
    <div class="dkce-tb-spacer"></div>
    <button class="dkce-tb-btn" id="dkce-btn-refresh-git" title="Refresh Git Status">↻ Git</button>
    <div class="dkce-tb-sep"></div>
    <button class="dkce-tb-btn" id="dkce-btn-terminal" title="Toggle Terminal (Ctrl+\`)"><span style="font-size:12px;opacity:.85">&gt;_</span> Terminal</button>
  </div>

  <!-- Body -->
  <div class="dkce-body">
    <!-- Activity bar -->
    <div class="dkce-act-bar">
      <button class="dkce-act-btn active" id="dkce-act-explorer" title="Explorer (Ctrl+Shift+E)">📁</button>
      <button class="dkce-act-btn"        id="dkce-act-search"   title="Search (Ctrl+Shift+F)">🔍</button>
      <button class="dkce-act-btn"        id="dkce-act-git"      title="Source Control (Ctrl+Shift+G)">⎇</button>
      <button class="dkce-act-btn"        id="dkce-act-history"  title="Local History (Ctrl+Shift+H)">🕐</button>
      <button class="dkce-act-btn"        id="dkce-act-claude"   title="Claude AI (Ctrl+Shift+A)">🤖</button>
    </div>

    <!-- Sidebar -->
    <div class="dkce-sidebar" id="dkce-sidebar">

      <!-- Explorer panel -->
      <div class="dkce-panel active" id="dkce-panel-explorer">
        <div class="dkce-panel-hdr">
          <span>Explorer</span>
          <button class="dkce-panel-hdr-btn" id="dkce-btn-collapse" title="Collapse All">⊟</button>
        </div>
        <div class="dkce-file-tree" id="dkce-file-tree">
          <div class="dkce-tree-loading">Select an app to browse files</div>
        </div>
      </div>

      <!-- Search panel -->
      <div class="dkce-panel" id="dkce-panel-search">
        <div class="dkce-panel-hdr"><span>Search</span></div>
        <div class="dkce-search-wrap">
          <input class="dkce-search-inp" id="dkce-search-q" placeholder="Search text…" />
          <div class="dkce-search-opts">
            <span class="dkce-search-opt-label">Types:</span>
            <input class="dkce-search-opt-inp" id="dkce-search-types" value="py,js,html,css,json" />
            <button class="dkce-search-btn" id="dkce-search-btn">Search</button>
          </div>
        </div>
        <div class="dkce-search-results" id="dkce-search-results">
          <div class="dkce-tree-loading">Enter a query and press Search</div>
        </div>
      </div>

      <!-- Git panel (enhanced) -->
      <div class="dkce-panel" id="dkce-panel-git">
        <div class="dkce-panel-hdr">
          <span>Source Control</span>
          <button class="dkce-panel-hdr-btn" id="dkce-git-btn-refresh" title="Refresh">↻</button>
        </div>
        <div class="dkce-git-branch" id="dkce-git-branch">⎇ —</div>
        <div class="dkce-git-actions">
          <button class="dkce-git-act-btn commit"  id="dkce-git-btn-commit"     title="Commit staged changes">✓ Commit</button>
          <button class="dkce-git-act-btn push"    id="dkce-git-btn-push"       title="Push to remote">↑ Push</button>
          <button class="dkce-git-act-btn pull"    id="dkce-git-btn-pull"       title="Pull from remote">↓ Pull</button>
          <button class="dkce-git-act-btn neutral" id="dkce-git-btn-fetch"      title="Fetch from remote">⇅ Fetch</button>
          <button class="dkce-git-act-btn branch"  id="dkce-git-btn-branch"     title="Branches">⎇ Branch</button>
          <button class="dkce-git-act-btn neutral" id="dkce-git-btn-merge"      title="Merge a branch">⑃ Merge</button>
        </div>
        <div class="dkce-git-actions" style="border-top:1px solid #2a2a2a;">
          <button class="dkce-git-act-btn stage-all" id="dkce-git-btn-stage-all"   title="Stage all changes (git add -A)">+ Stage All</button>
          <button class="dkce-git-act-btn unstage-all" id="dkce-git-btn-unstage-all" title="Unstage all (git reset HEAD)">− Unstage All</button>
          <button class="dkce-git-act-btn discard-all" id="dkce-git-btn-discard-all" title="Discard all unstaged changes">✕ Discard All</button>
          <button class="dkce-git-act-btn neutral" id="dkce-git-btn-diff"        title="Show diff of all changes">≠ Diff</button>
          <button class="dkce-git-act-btn neutral" id="dkce-git-btn-log"         title="Commit log">≡ Log</button>
          <button class="dkce-git-act-btn neutral" id="dkce-git-btn-stash"       title="Stash changes">↯ Stash</button>
          <button class="dkce-git-act-btn neutral" id="dkce-git-btn-reset"       title="Reset HEAD (soft/mixed/hard)">↺ Reset</button>
          <button class="dkce-git-act-btn neutral" id="dkce-git-btn-tag"         title="Create or list tags">🏷 Tag</button>
        </div>
        <div class="dkce-git-scroll" id="dkce-git-scroll" style="overflow-y:auto;flex:1;">
          <div class="dkce-tree-loading">Select an app to see git status</div>
        </div>
      </div>

      <!-- Local History panel -->
      <div class="dkce-panel" id="dkce-panel-history">
        <div class="dkce-panel-hdr">
          <span>Local History</span>
          <button class="dkce-panel-hdr-btn" id="dkce-hist-btn-refresh" title="Refresh">↻</button>
        </div>
        <div class="dkce-hist-file-info" id="dkce-hist-file-info">No file open</div>
        <div class="dkce-hist-scroll" id="dkce-hist-scroll">
          <div class="dkce-hist-empty">Open a file to view its history</div>
        </div>
      </div>

      <!-- Claude AI panel -->
      <div class="dkce-panel" id="dkce-panel-claude">
        <div class="dkce-panel-hdr">
          <span>Claude AI</span>
          <button class="dkce-panel-hdr-btn" id="dkce-claude-btn-clear" title="Clear chat">🗑</button>
        </div>

        <!-- Not connected: per-user connect form -->
        <div id="dkce-claude-connect-section" style="display:none;overflow-y:auto;flex:1;">
          <div class="dkce-claude-connect">
            <div class="dkce-claude-connect-logo">🤖</div>
            <div class="dkce-claude-connect-title">Connect your Anthropic Account</div>
            <div class="dkce-claude-connect-sub">
              Your API key is saved to your Frappe account<br>and never shared with other users.
            </div>
            <div class="dkce-claude-connect-field">
              <label class="dkce-claude-connect-label">Frappe User</label>
              <input class="dkce-claude-connect-inp" id="dkce-claude-frappe-user" type="text" readonly
                style="color:#888;cursor:default;" placeholder="loading…" />
            </div>
            <div class="dkce-claude-connect-field">
              <label class="dkce-claude-connect-label">Anthropic API Key</label>
              <input class="dkce-claude-connect-inp" id="dkce-claude-key-inp" type="password"
                placeholder="sk-ant-api03-…" autocomplete="new-password" />
              <div class="dkce-claude-connect-hint">
                Get your key at
                <a onclick="window.open('https://console.anthropic.com/settings/keys','_blank')">console.anthropic.com</a>
              </div>
            </div>
            <button class="dkce-claude-connect-btn" id="dkce-claude-key-save">Connect Account</button>
            <div class="dkce-claude-connect-err" id="dkce-claude-connect-err"></div>
          </div>
        </div>

        <!-- Connected: chat area -->
        <div id="dkce-claude-main" style="flex:1;display:flex;flex-direction:column;overflow:hidden;min-height:0;">
          <!-- Connected status bar -->
          <div class="dkce-claude-connected-bar" id="dkce-claude-connected-bar">
            <div class="dkce-claude-connected-dot"></div>
            <div class="dkce-claude-connected-info" id="dkce-claude-connected-info">Connected</div>
            <button class="dkce-claude-disconnect-btn" id="dkce-claude-disconnect">Disconnect</button>
          </div>
          <!-- Quick actions -->
          <div class="dkce-claude-actions-bar" id="dkce-claude-actions-bar">
            <button class="dkce-claude-action-btn" data-action="explain">⚡ Explain</button>
            <button class="dkce-claude-action-btn" data-action="refactor">♻ Refactor</button>
            <button class="dkce-claude-action-btn" data-action="fix">🔧 Fix Bug</button>
            <button class="dkce-claude-action-btn" data-action="tests">🧪 Tests</button>
            <button class="dkce-claude-action-btn" data-action="docs">📝 Docs</button>
            <button class="dkce-claude-action-btn" data-action="optimize">🚀 Optimize</button>
            <button class="dkce-claude-action-btn" data-action="complete">✨ Complete</button>
          </div>
          <div class="dkce-claude-chat" id="dkce-claude-chat">
            <div class="dkce-claude-msg assistant">👋 Hi! I'm Claude. Select code and click an action, or type a question below.<br><br><strong>Tips:</strong> Select code in the editor → click an action for targeted help. Use "Insert" on code blocks to paste directly at cursor.</div>
          </div>
          <div class="dkce-claude-input-area">
            <div class="dkce-claude-sel-badge" id="dkce-claude-sel-badge">
              <span id="dkce-claude-sel-info">📌 Selection: 0 lines</span>
              <button class="dkce-claude-sel-badge-clear" id="dkce-claude-sel-clear" title="Clear selection context">✕</button>
            </div>
            <div class="dkce-claude-ctx-row">
              <input type="checkbox" id="dkce-claude-use-ctx" checked>
              <label class="dkce-claude-ctx-label" for="dkce-claude-use-ctx">Include current file</label>
              <input type="checkbox" id="dkce-claude-use-sel">
              <label class="dkce-claude-ctx-label" for="dkce-claude-use-sel">Use selection</label>
            </div>
            <textarea class="dkce-claude-inp" id="dkce-claude-inp" placeholder="Ask Claude anything… (Enter to send, Shift+Enter newline)"></textarea>
            <div class="dkce-claude-actions">
              <span class="dkce-claude-status" id="dkce-claude-status"></span>
              <button class="dkce-claude-send" id="dkce-claude-send">Send ↵</button>
            </div>
          </div>
        </div>
      </div>



    </div>
    <div class="dkce-sidebar-resize" id="dkce-sidebar-resize"></div>

    <!-- Editor area -->
    <div class="dkce-editor-area">
      <!-- Tab bar -->
      <div class="dkce-tab-bar" id="dkce-tab-bar"></div>

      <!-- Breadcrumb -->
      <div class="dkce-breadcrumb" id="dkce-breadcrumb">&nbsp;</div>

      <!-- Editor wrap -->
      <div class="dkce-editor-wrap">
        <div class="dkce-editor-container" id="dkce-editor-container"></div>
        <div class="dkce-empty" id="dkce-empty">
          <div class="dkce-empty-icon">⌨</div>
          <div class="dkce-empty-title">DevKit Code Editor</div>
          <div class="dkce-empty-sub">Select an app • Open a file • Start editing</div>
        </div>
      </div>

      <!-- Terminal panel -->
      <div class="dkce-terminal-panel" id="dkce-terminal-panel">
        <div class="dkce-terminal-resize" id="dkce-terminal-resize"></div>
        <div class="dkce-terminal-hdr">
          <span class="dkce-terminal-hdr-title">TERMINAL</span>
          <div class="dkce-term-shortcuts" id="dkce-term-shortcuts">
            <button class="dkce-term-sc-btn" data-cmd="bench migrate">migrate</button>
            <button class="dkce-term-sc-btn" data-cmd="bench clear-cache">clear-cache</button>
            <button class="dkce-term-sc-btn" data-cmd="bench restart">restart</button>
            <button class="dkce-term-sc-btn" data-cmd="bench update --no-backup">update</button>
            <button class="dkce-term-sc-btn" data-cmd="git status">git status</button>
            <button class="dkce-term-sc-btn" data-cmd="git log --oneline -15">git log</button>
            <button class="dkce-term-sc-btn" data-cmd="ls apps/">apps/</button>
            <button class="dkce-term-sc-btn" data-cmd="ls sites/">sites/</button>
          </div>
          <button class="dkce-terminal-hdr-btn" id="dkce-term-btn-clear" title="Clear (Ctrl+L)"><svg width="14" height="14" viewBox="0 0 16 16" fill="none" xmlns="http://www.w3.org/2000/svg" style="display:block"><path d="M2 13h12M4 10l3-8M8 10l-1-3M12 10L9 2" stroke="currentColor" stroke-width="1.4" stroke-linecap="round" stroke-linejoin="round"/><path d="M1 10h14" stroke="currentColor" stroke-width="1.4" stroke-linecap="round"/></svg></button>
          <button class="dkce-terminal-hdr-btn" id="dkce-term-btn-close" title="Close (Ctrl+\`)"><svg width="14" height="14" viewBox="0 0 16 16" fill="none" xmlns="http://www.w3.org/2000/svg" style="display:block"><path d="M3 8h10M8 3l5 5-5 5" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/></svg></button>
        </div>
        <div class="dkce-terminal-output" id="dkce-terminal-output"></div>
        <div class="dkce-terminal-input-row" id="dkce-terminal-input-row">
          <span class="dkce-term-prompt-label" id="dkce-term-prompt-label">bench</span>
          <span class="dkce-term-dollar">$</span>
          <div style="flex:1;position:relative;min-width:0;">
            <input class="dkce-term-input" id="dkce-term-input"
              type="text" spellcheck="false" autocomplete="off"
              autocorrect="off" autocapitalize="off">
            <div class="dkce-term-comp-popup" id="dkce-term-comp-popup"></div>
          </div>
        </div>
      </div>
    </div>
  </div>

  <!-- Status bar -->
  <div class="dkce-statusbar" id="dkce-statusbar">
    <div class="dkce-sb-item" id="dkce-sb-branch" title="Git branch">⎇ —</div>
    <div class="dkce-sb-spacer"></div>
    <div class="dkce-sb-item" id="dkce-sb-pos"   title="Go to line">Ln 1, Col 1</div>
    <div class="dkce-sb-item" id="dkce-sb-lang"  title="Language">—</div>
    <div class="dkce-sb-item" id="dkce-sb-enc"   title="Encoding">UTF-8</div>
    <div class="dkce-sb-item" id="dkce-sb-tabs"  title="Indent settings">Spaces: 4</div>
    <div class="dkce-sb-item dkce-sb-save" id="dkce-sb-save">✓ Saved</div>
  </div>
</div>`;
        // Append to body — same pattern as devkit_studio (position:fixed needs body context)
        $(html).appendTo('body');
        this.$root = $('#dkce-root');
    }

    // ── Monaco Loader ──────────────────────────────────────────────────────
    _loadMonaco() {
        if (window.monaco) { this._onMonacoReady(); return; }
        if (this._monacoLoading) return;
        this._monacoLoading = true;

        // Show a loading indicator inside the editor area
        $('#dkce-empty').html(`
            <div class="dkce-empty-icon" style="font-size:36px;animation:spin 1s linear infinite">⏳</div>
            <div class="dkce-empty-title">Loading Editor…</div>
            <div class="dkce-empty-sub">Downloading Monaco from CDN</div>
            <button id="dkce-retry-monaco" style="margin-top:12px;padding:6px 18px;background:#0e639c;color:#fff;border:none;border-radius:4px;cursor:pointer">Retry</button>
        `);
        $('#dkce-empty').show();
        $('<style>@keyframes spin{to{transform:rotate(360deg)}}</style>').appendTo('head');

        const MONACO_CDN = 'https://cdnjs.cloudflare.com/ajax/libs/monaco-editor/0.44.0/min/vs';

        const doLoad = () => {
            const script = document.createElement('script');
            script.src = MONACO_CDN + '/loader.min.js';
            script.onload = () => {
                // Frappe v15 uses webpack/vite — no global AMD require exists,
                // so we must NOT restore window.require after Monaco sets it.
                // Just configure and load directly.
                window.require.config({ paths: { vs: MONACO_CDN } });
                window.require(['vs/editor/editor.main'], () => {
                    this.monaco = window.monaco;
                    this._onMonacoReady();
                });
            };
            script.onerror = () => {
                this._monacoLoading = false;
                $('#dkce-empty .dkce-empty-title').text('Failed to load Editor');
                $('#dkce-empty .dkce-empty-sub').text('Check internet connectivity. Click Retry to try again.');
                this._toast('Cannot reach Monaco CDN — check internet access', 'error');
            };
            document.head.appendChild(script);
        };

        doLoad();
        $(document).one('click', '#dkce-retry-monaco', () => { this._monacoLoading = false; this._loadMonaco(); });
    }

    _onMonacoReady() {
        this.monaco = window.monaco;
        const container = document.getElementById('dkce-editor-container');
        if (!container) {
            console.error('dkce-editor-container not found — layout may not have mounted to body correctly');
            return;
        }
        const s = this.state.settings;

        this.editor = this.monaco.editor.create(container, {
            value: '',
            language: 'plaintext',
            theme: this.state.theme,
            fontSize: s.fontSize,
            minimap: { enabled: s.minimap },
            wordWrap: s.wordWrap,
            tabSize: s.tabSize,
            insertSpaces: s.insertSpaces,
            lineNumbers: s.lineNumbers,
            scrollBeyondLastLine: false,
            automaticLayout: true,
            renderWhitespace: s.renderWhitespace,
            smoothScrolling: s.smoothScrolling,
            cursorBlinking: 'smooth',
            cursorSmoothCaretAnimation: 'on',
            roundedSelection: true,
            renderLineHighlight: 'all',
            multiCursorModifier: 'ctrlCmd',
            bracketPairColorization: { enabled: true },
            guides: { bracketPairs: true, indentation: true },
            folding: true,
            foldingHighlight: true,
            padding: { top: 8, bottom: 8 },

            // ── Code Intelligence ────────────────────────────────────────
            // fixedOverflowWidgets keeps the suggest popup from being clipped
            // by Frappe's overflow:hidden containers
            fixedOverflowWidgets: true,

            suggest: {
                showIcons: true,
                showStatusBar: true,
                showInlineDetails: true,
                preview: true,
                previewMode: 'subWordSmart',
                insertMode: 'replace',
                filterGraceful: true,
                snippetsPreventQuickSuggestions: false,
                localityBonus: true,
                // Show all completion kinds
                showKeywords: true,
                showSnippets: true,
                showWords: true,
                showMethods: true,
                showFunctions: true,
                showConstructors: true,
                showFields: true,
                showVariables: true,
                showClasses: true,
                showModules: true,
                showProperties: true,
                showEvents: true,
                showColors: true,
                showReferences: true,
                showEnums: true,
                showEnumMembers: true,
                showInterfaces: true,
                showTypeParameters: true,
                showConstants: true,
                showOperators: true,
                showStructs: true,
                showValues: true,
            },

            quickSuggestions: {
                other: 'on',
                comments: 'off',
                strings: 'on',
            },
            quickSuggestionsDelay: 80,
            suggestOnTriggerCharacters: true,
            acceptSuggestionOnCommitCharacter: true,
            acceptSuggestionOnEnter: 'on',
            tabCompletion: 'on',
            wordBasedSuggestions: 'matchingDocuments',

            // ── Hover & Hints ────────────────────────────────────────────
            hover: { enabled: true, delay: 300, sticky: true },
            parameterHints: { enabled: true, cycle: true },
            inlayHints: { enabled: 'on' },
            lightbulb: { enabled: true },
            contextmenu: true,
            mouseWheelZoom: true,
            links: true,
            colorDecorators: true,
            overviewRulerLanes: 3,

            // ── Inline Suggestions (Copilot-style ghost text) ────────────
            inlineSuggest: {
                enabled: true,
                showToolbar: 'onHover',
            },
        });

        // Cursor position -> status bar
        this.editor.onDidChangeCursorPosition(e => {
            const pos = e.position;
            $('#dkce-sb-pos').text(`Ln ${pos.lineNumber}, Col ${pos.column}`);
        });

        // Model change -> unsaved indicator
        this.editor.onDidChangeModelContent(() => {
            const tab = this._activeTab();
            if (!tab) return;
            const changed = this.editor.getValue() !== tab.origContent;
            if (tab.isModified !== changed) {
                tab.isModified = changed;
                $(`#dkce-tab-${tab.id}`).toggleClass('modified', changed);
                $('#dkce-sb-save').text(changed ? '● Unsaved' : '✓ Saved');
            }
        });

        // Ctrl+S shortcut inside editor
        this.editor.addCommand(
            this.monaco.KeyMod.CtrlCmd | this.monaco.KeyCode.KeyS,
            () => this._saveCurrentFile()
        );

        // Claude AI context menu actions in Monaco right-click menu
        const claudeActions = [
            { id: 'claude.explain',  label: '⚡ Claude: Explain',       action: 'explain'  },
            { id: 'claude.refactor', label: '♻ Claude: Refactor',       action: 'refactor' },
            { id: 'claude.fix',      label: '🔧 Claude: Fix Bug',        action: 'fix'      },
            { id: 'claude.tests',    label: '🧪 Claude: Generate Tests', action: 'tests'    },
            { id: 'claude.docs',     label: '📝 Claude: Add Docs',       action: 'docs'     },
            { id: 'claude.optimize', label: '🚀 Claude: Optimize',       action: 'optimize' },
        ];
        claudeActions.forEach(({ id, label, action }) => {
            this.editor.addAction({
                id,
                label,
                contextMenuGroupId: 'claude',
                contextMenuOrder:   claudeActions.indexOf({ id, label, action }),
                run: () => this._sendClaudeAction(action),
            });
        });

        // Restore empty state content and hide it
        $('#dkce-empty').html(`
            <div class="dkce-empty-icon">⌨</div>
            <div class="dkce-empty-title">DevKit Code Editor</div>
            <div class="dkce-empty-sub">Select an app • Open a file • Start editing</div>
        `).hide();

        // Force layout after DOM is fully painted
        requestAnimationFrame(() => this.editor.layout());

        // Open any file that was clicked before Monaco finished loading
        if (this._pendingFile) {
            const { appName, filePath } = this._pendingFile;
            this._pendingFile = null;
            this._openFile(appName, filePath);
        }

        // Register Frappe intelligence providers
        this._registerIntelligence();

        // Register Claude inline completions if already connected
        this._startClaudeCompletion();

        this._toast('Editor ready', 'success');
    }

    // ── Events ─────────────────────────────────────────────────────────────
    _bindEvents() {
        // Back to DevKit Studio
        $(document).on('click', '#dkce-btn-back', () => frappe.set_route('devkit-studio'));

        // App selector (custom searchable dropdown)
        this._initAppDropdown();

        // Toolbar buttons
        $(document).on('click', '#dkce-btn-save',       () => this._saveCurrentFile());
        $(document).on('click', '#dkce-btn-new',        () => this._promptNewFile());
        $(document).on('click', '#dkce-btn-fmt',        () => this._formatDocument());
        $(document).on('click', '#dkce-btn-wrap',       () => this._toggleWrap());
        $(document).on('click', '#dkce-btn-minimap',    () => this._toggleMinimap());
        $(document).on('click', '#dkce-btn-fz-up',      () => this._changeFontSize(1));
        $(document).on('click', '#dkce-btn-fz-dn',      () => this._changeFontSize(-1));
        $(document).on('click', '#dkce-btn-theme',      () => this._toggleTheme());
        $(document).on('click', '#dkce-btn-settings',   () => this._openSettings());
        $(document).on('click', '#dkce-btn-refresh-git',() => this._refreshGit());
        $(document).on('click', '#dkce-btn-terminal',   () => this._toggleTerminal());
        $(document).on('click', '#dkce-btn-collapse',   () => this._collapseAll());

        // Activity bar
        $(document).on('click', '#dkce-act-explorer', () => this._switchPanel('explorer'));
        $(document).on('click', '#dkce-act-search',   () => this._switchPanel('search'));
        $(document).on('click', '#dkce-act-git',      () => this._switchPanel('git'));
        $(document).on('click', '#dkce-act-history',  () => this._switchPanel('history'));
        $(document).on('click', '#dkce-act-claude',   () => this._switchPanel('claude'));

        // Enhanced git actions
        $(document).on('click', '#dkce-git-btn-refresh',     () => this._refreshGit());
        $(document).on('click', '#dkce-git-btn-commit',      () => this._gitCommit());
        $(document).on('click', '#dkce-git-btn-push',        () => this._gitPush());
        $(document).on('click', '#dkce-git-btn-pull',        () => this._gitPull());
        $(document).on('click', '#dkce-git-btn-fetch',       () => this._gitFetch());
        $(document).on('click', '#dkce-git-btn-branch',      () => this._gitBranches());
        $(document).on('click', '#dkce-git-btn-merge',       () => this._gitMerge());
        $(document).on('click', '#dkce-git-btn-stage-all',   () => this._gitStageAll());
        $(document).on('click', '#dkce-git-btn-unstage-all', () => this._gitUnstageAll());
        $(document).on('click', '#dkce-git-btn-discard-all', () => this._gitDiscardAll());
        $(document).on('click', '#dkce-git-btn-diff',        () => this._gitDiff());
        $(document).on('click', '#dkce-git-btn-log',         () => this._gitLog());
        $(document).on('click', '#dkce-git-btn-stash',       () => this._gitStash());
        $(document).on('click', '#dkce-git-btn-reset',       () => this._gitReset());
        $(document).on('click', '#dkce-git-btn-tag',         () => this._gitTag());

        // History panel
        $(document).on('click', '#dkce-hist-btn-refresh', () => this._loadHistory());

        // Claude panel
        $(document).on('click', '#dkce-claude-btn-clear',   () => this._clearClaudeChat());
        $(document).on('click', '#dkce-claude-send',        () => this._sendClaudeMessage());
        $(document).on('click', '#dkce-claude-key-save',    () => this._saveClaudeApiKey());
        $(document).on('click', '#dkce-claude-disconnect',  () => this._disconnectClaude());
        $(document).on('keydown', '#dkce-claude-inp', e => {
            if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); this._sendClaudeMessage(); }
        });
        // Quick action buttons
        $(document).on('click', '#dkce-claude-actions-bar .dkce-claude-action-btn', e => {
            this._sendClaudeAction($(e.currentTarget).data('action'));
        });
        // Clear pinned selection
        $(document).on('click', '#dkce-claude-sel-clear', () => {
            this._claudePinnedSel = null;
            $('#dkce-claude-sel-badge').removeClass('visible');
            $('#dkce-claude-use-sel').prop('checked', false);
        });


        // Search
        $(document).on('click',  '#dkce-search-btn',  () => this._doSearch());
        $(document).on('keydown','#dkce-search-q', e => { if (e.key === 'Enter') this._doSearch(); });

        // Status bar shortcuts
        $(document).on('click', '#dkce-sb-pos',  () => this.editor && this.editor.trigger('', 'editor.action.gotoLine', null));
        $(document).on('click', '#dkce-sb-lang', () => this.editor && this.editor.trigger('', 'editor.action.changeEOL', null));
        $(document).on('click', '#dkce-sb-tabs', () => this._openSettings());

        // Global keyboard
        $(document).on('keydown', e => {
            if ((e.ctrlKey || e.metaKey) && e.key === 's') {
                e.preventDefault();
                this._saveCurrentFile();
            }
            if ((e.ctrlKey || e.metaKey) && e.shiftKey && e.key === 'F') {
                e.preventDefault();
                this._switchPanel('search');
                setTimeout(() => $('#dkce-search-q').focus(), 100);
            }
            if ((e.ctrlKey || e.metaKey) && e.shiftKey && e.key === 'E') {
                e.preventDefault();
                this._switchPanel('explorer');
            }
            if ((e.ctrlKey || e.metaKey) && e.shiftKey && e.key === 'G') {
                e.preventDefault();
                this._switchPanel('git');
            }
            if ((e.ctrlKey || e.metaKey) && e.shiftKey && e.key === 'H') {
                e.preventDefault();
                this._switchPanel('history');
            }
            if ((e.ctrlKey || e.metaKey) && e.shiftKey && e.key === 'A') {
                e.preventDefault();
                this._switchPanel('claude');
                setTimeout(() => $('#dkce-claude-inp').focus(), 100);
            }

            if ((e.ctrlKey || e.metaKey) && e.key === 'w') {
                e.preventDefault();
                if (this.state.activeTabId) this._closeTab(this.state.activeTabId);
            }
            if (e.altKey && e.key === 'z') {
                e.preventDefault();
                this._toggleWrap();
            }
            if (e.altKey && e.shiftKey && e.key === 'F') {
                e.preventDefault();
                this._formatDocument();
            }
            // Ctrl+` — toggle terminal
            if ((e.ctrlKey || e.metaKey) && e.key === '`') {
                e.preventDefault();
                this._toggleTerminal();
            }
        });

        // Terminal header buttons
        $(document).on('click', '#dkce-term-btn-clear', () => this._termClear());
        $(document).on('click', '#dkce-term-btn-close', () => this._toggleTerminal(false));

        // Terminal shortcut buttons
        $(document).on('click', '#dkce-term-shortcuts .dkce-term-sc-btn', e => {
            const cmd = $(e.currentTarget).data('cmd');
            if (cmd) this._termRunShortcut(cmd);
        });

        // Terminal input keydown
        $(document).on('keydown', '#dkce-term-input', e => this._termOnKeydown(e));

        // Completion popup clicks (mousedown so it fires before blur)
        $(document).on('mousedown', '.dkce-term-comp-item', e => {
            e.preventDefault();
            const completion = $(e.currentTarget).data('completion');
            if (completion) this._termApplyCompletion(completion);
        });

        // Hide completions when clicking outside terminal
        $(document).on('mousedown', e => {
            if (!$(e.target).closest('#dkce-terminal-panel').length) {
                this._termHideCompletions();
            }
        });

        // Sidebar resize handle
        $(document).on('mousedown', '#dkce-sidebar-resize', e => this._sidebarResizeStart(e));

        // Terminal resize handle
        $(document).on('mousedown', '#dkce-terminal-resize', e => this._termResizeStart(e));

        // Hide context menu on click outside
        $(document).on('click', e => {
            if (!$(e.target).closest('.dkce-ctx').length) this._hideCtxMenu();
        });

        // Refresh git on tab switch (lightweight)
        $(document).on('click', '.dkce-tab', e => {
            const tabId = $(e.currentTarget).data('tab-id');
            if (tabId) this._switchTab(tabId);
        });
        $(document).on('click', '.dkce-tab-close', e => {
            e.stopPropagation();
            const tabId = $(e.currentTarget).closest('.dkce-tab').data('tab-id');
            this._closeTab(tabId);
        });
    }

    // ── Apps ───────────────────────────────────────────────────────────────
    _loadApps() {
        frappe.call({
            method: 'frappe_devkit.api.code_editor.get_apps',
            callback: r => {
                this._appList = r.message || [];
                this._renderAppDropdownItems(this._appList);
                if (this._pendingApp) {
                    const app = this._pendingApp;
                    this._pendingApp = null;
                    this._selectApp(app);
                } else {
                    $('#dkce-app-dd-label').text('— Select App —');
                }
            }
        });
    }

    _initAppDropdown() {
        this._appList = [];

        // Toggle open/close
        $(document).on('click', '#dkce-app-dd-trigger', e => {
            e.stopPropagation();
            const $popup = $('#dkce-app-dd-popup');
            const isOpen = $popup.hasClass('open');
            $popup.toggleClass('open', !isOpen);
            if (!isOpen) {
                $('#dkce-app-dd-search').val('').trigger('input').focus();
            }
        });

        // Search filter
        $(document).on('input', '#dkce-app-dd-search', () => {
            const q = $('#dkce-app-dd-search').val().trim().toLowerCase();
            const filtered = q ? this._appList.filter(a => a.name.toLowerCase().includes(q)) : this._appList;
            this._renderAppDropdownItems(filtered);
        });

        // Keyboard navigation
        $(document).on('keydown', '#dkce-app-dd-search', e => {
            const $items = $('#dkce-app-dd-list .dkce-app-dd-item');
            const $focused = $items.filter('.focused');
            if (e.key === 'ArrowDown') {
                e.preventDefault();
                const $next = $focused.length ? $focused.next('.dkce-app-dd-item') : $items.first();
                $items.removeClass('focused'); $next.addClass('focused')[0]?.scrollIntoView({ block: 'nearest' });
            } else if (e.key === 'ArrowUp') {
                e.preventDefault();
                const $prev = $focused.length ? $focused.prev('.dkce-app-dd-item') : $items.last();
                $items.removeClass('focused'); $prev.addClass('focused')[0]?.scrollIntoView({ block: 'nearest' });
            } else if (e.key === 'Enter') {
                e.preventDefault();
                const name = $focused.data('name') || ($items.length === 1 ? $items.first().data('name') : null);
                if (name) this._pickApp(name);
            } else if (e.key === 'Escape') {
                this._closeAppDropdown();
            }
        });

        // Item click
        $(document).on('click', '#dkce-app-dd-list .dkce-app-dd-item', e => {
            this._pickApp($(e.currentTarget).data('name'));
        });

        // Close on outside click
        $(document).on('click.dkceappdrop', e => {
            if (!$(e.target).closest('#dkce-app-dd').length) this._closeAppDropdown();
        });
    }

    _renderAppDropdownItems(apps) {
        const current = this.state.currentApp;
        const $list = $('#dkce-app-dd-list').empty();
        if (!apps.length) {
            $list.html('<div class="dkce-app-dd-empty">No apps found</div>');
            return;
        }
        apps.forEach(a => {
            $list.append(
                $(`<div class="dkce-app-dd-item${a.name === current ? ' selected' : ''}" data-name="${_esc(a.name)}">${_esc(a.name)}</div>`)
            );
        });
    }

    _pickApp(name) {
        $('#dkce-app-dd-label').text(name);
        this._closeAppDropdown();
        this._selectApp(name);
    }

    _closeAppDropdown() {
        $('#dkce-app-dd-popup').removeClass('open');
    }

    _selectApp(appName) {
        if (!appName) return;
        this.state.currentApp = appName;
        $('#dkce-app-dd-label').text(appName);
        this.state.treeCache = {};
        this.state.expandedPaths = new Set();
        this._loadTree('', document.getElementById('dkce-file-tree'), 0);
        this._refreshGit();
    }

    // ── File Tree ──────────────────────────────────────────────────────────
    _loadTree(path, container, depth) {
        $(container).html('<div class="dkce-tree-loading">Loading…</div>');
        frappe.call({
            method: 'frappe_devkit.api.code_editor.get_file_tree',
            args: { app_name: this.state.currentApp, path },
            callback: r => {
                const items = r.message || [];
                this.state.treeCache[path || '__root__'] = items;
                $(container).empty();
                if (!items.length) {
                    $(container).html('<div class="dkce-tree-loading" style="color:#666">Empty folder</div>');
                    return;
                }
                this._renderTreeItems(items, container, depth);
            }
        });
    }

    _renderTreeItems(items, container, depth) {
        items.forEach(item => {
            const indent = depth * 12 + 8;
            const icon = item.type === 'dir' ? '📁' : this._fileIcon(item.ext || '');
            const gitCode = this.state.gitInfo.changes[item.path] || '';
            const gitClass = gitCode ? `dkce-git-${gitCode.replace('?','U')}` : '';
            const gitBadge = gitCode ? `<span class="dkce-tree-badge ${gitClass}">${gitCode === '??' ? 'U' : gitCode}</span>` : '';

            const $row = $(`
              <div class="dkce-tree-item ${item.type === 'dir' ? 'dkce-folder' : ''}"
                   style="padding-left:${indent}px"
                   data-path="${item.path}" data-type="${item.type}" data-ext="${item.ext || ''}">
                <span class="dkce-tree-arr">${item.type === 'dir' ? '▶' : ' '}</span>
                <span class="dkce-tree-icon">${icon}</span>
                <span class="dkce-tree-name">${item.name}</span>
                ${gitBadge}
              </div>
            `);

            if (item.type === 'dir') {
                const $children = $('<div class="dkce-tree-children" style="display:none"></div>');
                $row.on('click', e => {
                    e.stopPropagation();
                    $('.dkce-tree-item').removeClass('active');
                    $row.addClass('active');
                    this.state.selectedDir = item.path;
                    this._toggleFolder($row, $children, item.path, depth + 1);
                });
                $row.on('contextmenu', e => {
                    e.preventDefault();
                    this._showDirCtxMenu(e.pageX, e.pageY, item.path);
                });
                $(container).append($row).append($children);
            } else {
                $row.on('click', e => {
                    e.stopPropagation();
                    $('.dkce-tree-item').removeClass('active');
                    $row.addClass('active');
                    // track parent dir so "+ New" places file in same folder
                    const parts = item.path.split('/');
                    this.state.selectedDir = parts.length > 1 ? parts.slice(0, -1).join('/') : '';
                    this._openFile(this.state.currentApp, item.path);
                });
                $row.on('contextmenu', e => {
                    e.preventDefault();
                    this._showFileCtxMenu(e.pageX, e.pageY, item.path, $row);
                });
                $(container).append($row);
            }
        });
    }

    _toggleFolder($row, $children, folderPath, childDepth) {
        const open = $row.find('.dkce-tree-arr').hasClass('open');
        if (open) {
            $row.find('.dkce-tree-arr').removeClass('open').text('▶');
            $row.find('.dkce-tree-icon').text('📁');
            $children.hide();
            this.state.expandedPaths.delete(folderPath);
        } else {
            $row.find('.dkce-tree-arr').addClass('open').text('▼');
            $row.find('.dkce-tree-icon').text('📂');
            this.state.expandedPaths.add(folderPath);
            $children.show();
            if (!$children.children().length) {
                const cached = this.state.treeCache[folderPath];
                if (cached) {
                    this._renderTreeItems(cached, $children[0], childDepth);
                } else {
                    $children.html('<div class="dkce-tree-loading">Loading…</div>');
                    frappe.call({
                        method: 'frappe_devkit.api.code_editor.get_file_tree',
                        args: { app_name: this.state.currentApp, path: folderPath },
                        callback: r => {
                            const items = r.message || [];
                            this.state.treeCache[folderPath] = items;
                            $children.empty();
                            if (!items.length) {
                                $children.html('<div class="dkce-tree-loading" style="color:#666">Empty</div>');
                            } else {
                                this._renderTreeItems(items, $children[0], childDepth);
                            }
                        }
                    });
                }
            }
        }
    }

    _collapseAll() {
        this.state.treeCache = {};
        this.state.expandedPaths = new Set();
        if (this.state.currentApp) {
            this._loadTree('', document.getElementById('dkce-file-tree'), 0);
        }
    }

    // ── Open File / Tabs ───────────────────────────────────────────────────
    _openFile(appName, filePath) {
        // Check if already open
        const existing = this.state.tabs.find(t => t.appName === appName && t.filePath === filePath);
        if (existing) { this._switchTab(existing.id); return; }

        if (!this.editor) {
            // Queue this file — it will open automatically when Monaco finishes loading
            this._pendingFile = { appName, filePath };
            this._toast('Editor loading… file queued, will open automatically', 'info');
            return;
        }

        frappe.call({
            method: 'frappe_devkit.api.code_editor.read_file',
            args: { app_name: appName, file_path: filePath },
            freeze: false,
            callback: r => {
                if (!r || !r.message) {
                    this._toast('Could not read file — check server logs', 'error');
                    return;
                }
                const data = r.message;
                const tabId = 'tab_' + Date.now();
                // Use a safe URI scheme that Monaco handles without extra restrictions
                const uri = this.monaco.Uri.parse(`inmemory://editor/${appName}/${filePath}`);
                let model = this.monaco.editor.getModel(uri);
                if (!model) {
                    model = this.monaco.editor.createModel(
                        data.content || '', data.language || 'plaintext', uri
                    );
                } else {
                    // Already cached — just update content
                    model.setValue(data.content || '');
                }

                const tab = {
                    id: tabId, appName, filePath,
                    fileName: data.name,
                    language: data.language || 'plaintext',
                    model,
                    viewState: null,
                    isModified: false,
                    origContent: data.content || '',
                };
                this.state.tabs.push(tab);
                this._addTab(tab);
                this._switchTab(tabId);
            }
        });
    }

    _addTab(tab) {
        const icon = this._fileIcon(tab.fileName.split('.').pop());
        const $tab = $(`
          <div class="dkce-tab" id="dkce-tab-${tab.id}" data-tab-id="${tab.id}" title="${tab.filePath}">
            <span class="dkce-tab-icon">${icon}</span>
            <span class="dkce-tab-name">${tab.fileName}</span>
            <span class="dkce-tab-dot"></span>
            <span class="dkce-tab-close" title="Close (Ctrl+W)">×</span>
          </div>
        `);
        $('#dkce-tab-bar').append($tab);
        // scroll to new tab
        const bar = document.getElementById('dkce-tab-bar');
        bar.scrollLeft = bar.scrollWidth;
    }

    _switchTab(tabId) {
        const tab = this.state.tabs.find(t => t.id === tabId);
        if (!tab || !this.editor) return;

        // Save current view state
        const curTab = this._activeTab();
        if (curTab) curTab.viewState = this.editor.saveViewState();

        this.state.activeTabId = tabId;
        this.editor.setModel(tab.model);
        if (tab.viewState) this.editor.restoreViewState(tab.viewState);

        // Set language (in case model language needs update)
        this.monaco.editor.setModelLanguage(tab.model, tab.language);

        // UI updates
        $('.dkce-tab').removeClass('active');
        $(`#dkce-tab-${tabId}`).addClass('active');
        this._updateBreadcrumb(tab.filePath);
        this._updateLangStatus(tab.language);
        this._updateSaveStatus(tab.isModified);
        $('#dkce-empty').hide();

        // Force Monaco to recalculate dimensions AFTER the empty-state div
        // is hidden (browser must paint first, hence requestAnimationFrame)
        requestAnimationFrame(() => {
            if (this.editor) {
                this.editor.layout();
                this.editor.focus();
            }
        });
    }

    _closeTab(tabId, force = false) {
        const tab = this.state.tabs.find(t => t.id === tabId);
        if (!tab) return;

        if (tab.isModified && !force) {
            frappe.confirm(
                `"${tab.fileName}" has unsaved changes. Discard?`,
                () => this._closeTab(tabId, true)
            );
            return;
        }

        tab.model.dispose();
        this.state.tabs = this.state.tabs.filter(t => t.id !== tabId);
        $(`#dkce-tab-${tabId}`).remove();

        if (this.state.activeTabId === tabId) {
            this.state.activeTabId = null;
            const next = this.state.tabs[this.state.tabs.length - 1];
            if (next) {
                this._switchTab(next.id);
            } else {
                this.editor && this.editor.setModel(null);
                $('#dkce-empty').show();
                this._updateBreadcrumb('');
                this._updateLangStatus('');
                $('#dkce-sb-save').text('');
            }
        }
    }

    // ── Save ───────────────────────────────────────────────────────────────
    _saveCurrentFile() {
        const tab = this._activeTab();
        if (!tab || !this.editor) return;

        const content = this.editor.getValue();
        frappe.call({
            method: 'frappe_devkit.api.code_editor.write_file',
            args: { app_name: tab.appName, file_path: tab.filePath, content },
            callback: r => {
                if (r.message && r.message.ok) {
                    tab.origContent = content;
                    tab.isModified = false;
                    $(`#dkce-tab-${tab.id}`).removeClass('modified');
                    this._updateSaveStatus(false);
                    this._toast(`Saved: ${tab.fileName}`, 'success');
                }
            }
        });
    }

    // ── Format ─────────────────────────────────────────────────────────────
    _formatDocument() {
        if (!this.editor) return;
        const tab = this._activeTab();
        if (!tab) return;

        if (tab.language === 'python') {
            const content = this.editor.getValue();
            frappe.call({
                method: 'frappe_devkit.api.code_editor.format_python',
                args: { content },
                callback: r => {
                    if (r.message && r.message.ok) {
                        this.editor.setValue(r.message.content);
                        const fmt = r.message.formatter || 'formatter';
                        this._toast('Python formatted (' + fmt + ')', 'success');
                    } else {
                        this._toast(r.message.error || 'No Python formatter available', 'warn');
                    }
                }
            });
        } else {
            // Use Monaco's built-in formatter (works for JS, HTML, CSS, JSON, TypeScript)
            this.editor.trigger('', 'editor.action.formatDocument', null);
        }
    }

    // ── New File ────────────────────────────────────────────────────────────
    _promptNewFile(defaultDir = '') {
        if (!this.state.currentApp) {
            this._toast('Select an app first', 'warn'); return;
        }
        // Use last selected folder if no explicit dir was given
        const dir = defaultDir || this.state.selectedDir || '';
        frappe.prompt([
            { label: 'File path (relative to app root)', fieldname: 'path', fieldtype: 'Data',
              default: dir ? dir + '/' : '', reqd: 1,
              description: 'e.g. frappe_devkit/api/my_module.py' },
            { label: 'Initial content', fieldname: 'content', fieldtype: 'Code', default: '' },
        ], ({ path, content }) => {
            frappe.call({
                method: 'frappe_devkit.api.code_editor.create_file',
                args: { app_name: this.state.currentApp, file_path: path, content: content || '' },
                callback: r => {
                    if (r.message && r.message.ok) {
                        this._toast(`Created: ${path}`, 'success');
                        this._collapseAll();
                        this._openFile(this.state.currentApp, path);
                    }
                }
            });
        }, 'New File', 'Create');
    }

    // ── Context Menus ───────────────────────────────────────────────────────
    _showFileCtxMenu(x, y, filePath, $row) {
        const canPaste = !!this.state.clipboard;
        this._showCtxMenu(x, y, [
            { label: '📂 Open', action: () => this._openFile(this.state.currentApp, filePath) },
            { sep: true },
            { label: '📄 Copy', action: () => this._copyItem(filePath, false) },
            ...(canPaste ? [{ label: '📋 Paste Here', action: () => this._pasteItem(filePath.split('/').slice(0, -1).join('/')) }] : []),
            { sep: true },
            { label: '✏️ Rename', action: () => this._renameFile(filePath, $row) },
            { label: '🗑️ Delete', action: () => this._confirmDelete(filePath) },
            { sep: true },
            { label: '🔗 Copy Path', action: () => navigator.clipboard.writeText(filePath).then(() => this._toast('Copied!', 'info')) },
        ]);
    }

    _showDirCtxMenu(x, y, dirPath) {
        const canPaste = !!this.state.clipboard;
        this._showCtxMenu(x, y, [
            { label: '+ New File Here', action: () => this._promptNewFile(dirPath) },
            { sep: true },
            { label: '📁 Copy Folder', action: () => this._copyItem(dirPath, true) },
            ...(canPaste ? [{ label: '📋 Paste Into Folder', action: () => this._pasteItem(dirPath) }] : []),
            { sep: true },
            { label: '🗑️ Delete Folder', action: () => this._confirmDeleteDir(dirPath) },
        ]);
    }

    _showCtxMenu(x, y, items) {
        this._hideCtxMenu();
        const $menu = $('<div class="dkce-ctx" id="dkce-ctx"></div>');
        items.forEach(item => {
            if (item.sep) {
                $menu.append('<div class="dkce-ctx-sep"></div>');
            } else {
                $('<div class="dkce-ctx-item"></div>').text(item.label)
                    .on('click', () => { this._hideCtxMenu(); item.action(); })
                    .appendTo($menu);
            }
        });
        $menu.css({ left: Math.min(x, window.innerWidth - 200), top: Math.min(y, window.innerHeight - 200) });
        document.body.appendChild($menu[0]);
    }

    _hideCtxMenu() {
        $('#dkce-ctx').remove();
    }

    _renameFile(filePath, $row) {
        const oldName = filePath.split('/').pop();
        const dir = filePath.substring(0, filePath.length - oldName.length);
        frappe.prompt([
            { label: 'New name', fieldname: 'name', fieldtype: 'Data', default: oldName, reqd: 1 }
        ], ({ name }) => {
            const newPath = dir + name;
            frappe.call({
                method: 'frappe_devkit.api.code_editor.rename_file',
                args: { app_name: this.state.currentApp, old_path: filePath, new_path: newPath },
                callback: r => {
                    if (r.message && r.message.ok) {
                        this._toast(`Renamed to ${name}`, 'success');
                        // Close old tab if open
                        const oldTab = this.state.tabs.find(t => t.filePath === filePath);
                        if (oldTab) this._closeTab(oldTab.id, true);
                        $row.data('path', newPath).find('.dkce-tree-name').text(name);
                    }
                }
            });
        }, 'Rename File', 'Rename');
    }

    _confirmDelete(filePath) {
        frappe.confirm(`Delete <b>${filePath}</b>? This cannot be undone.`, () => {
            frappe.call({
                method: 'frappe_devkit.api.code_editor.delete_file',
                args: { app_name: this.state.currentApp, file_path: filePath },
                callback: r => {
                    if (r.message && r.message.ok) {
                        this._toast(`Deleted: ${filePath}`, 'info');
                        const tab = this.state.tabs.find(t => t.filePath === filePath);
                        if (tab) this._closeTab(tab.id, true);
                        this._collapseAll();
                    }
                }
            });
        });
    }

    // ── Copy / Paste ────────────────────────────────────────────────────────
    _copyItem(path, isDir) {
        this.state.clipboard = { path, isDir };
        const name = path.split('/').pop();
        this._toast(`Copied: ${name}`, 'info');
    }

    _pasteItem(destDir) {
        if (!this.state.clipboard) return;
        const { path: srcPath, isDir } = this.state.clipboard;
        const srcName = srcPath.split('/').pop();
        // Build candidate dest path; auto-suffix if name collides
        const baseDest = destDir ? `${destDir}/${srcName}` : srcName;

        frappe.prompt([
            { label: 'Paste as (name)', fieldname: 'name', fieldtype: 'Data',
              default: srcName, reqd: 1,
              description: `Will be created inside: ${destDir || '(app root)'}` },
        ], ({ name }) => {
            const destPath = destDir ? `${destDir}/${name}` : name;
            frappe.call({
                method: 'frappe_devkit.api.code_editor.copy_item',
                args: { app_name: this.state.currentApp, src_path: srcPath, dest_path: destPath },
                callback: r => {
                    if (r.message && r.message.ok) {
                        this._toast(`Pasted as: ${destPath}`, 'success');
                        this._collapseAll();
                        if (!isDir) this._openFile(this.state.currentApp, destPath);
                    }
                }
            });
        }, 'Paste Item', 'Paste');
    }

    _confirmDeleteDir(dirPath) {
        frappe.confirm(`Delete folder <b>${dirPath}</b> and all its contents? This cannot be undone.`, () => {
            frappe.call({
                method: 'frappe_devkit.api.code_editor.delete_dir',
                args: { app_name: this.state.currentApp, dir_path: dirPath },
                callback: r => {
                    if (r.message && r.message.ok) {
                        this._toast(`Deleted folder: ${dirPath}`, 'info');
                        this._collapseAll();
                    }
                }
            });
        });
    }

    // ── Search ─────────────────────────────────────────────────────────────
    _doSearch() {
        const q = $('#dkce-search-q').val().trim();
        const types = $('#dkce-search-types').val().trim() || 'py,js,html,css,json';
        if (!q || !this.state.currentApp) {
            this._toast('Enter a query and select an app', 'warn'); return;
        }
        $('#dkce-search-results').html('<div class="dkce-tree-loading">Searching…</div>');
        frappe.call({
            method: 'frappe_devkit.api.code_editor.search_files',
            args: { app_name: this.state.currentApp, query: q, file_types: types },
            callback: r => {
                const results = r.message || [];
                this._renderSearchResults(results, q);
            }
        });
    }

    _renderSearchResults(results, query) {
        const $res = $('#dkce-search-results').empty();
        if (!results.length) {
            $res.html('<div class="dkce-tree-loading">No results found</div>');
            return;
        }
        $('<div class="dkce-search-count"></div>')
            .text(`${results.length} match${results.length !== 1 ? 'es' : ''}`).appendTo($res);

        // Group by file
        const grouped = {};
        results.forEach(r => { (grouped[r.file] = grouped[r.file] || []).push(r); });
        const ql = query.toLowerCase();

        Object.entries(grouped).forEach(([file, matches]) => {
            const $hdr = $(`<div class="dkce-search-file-hdr" title="${file}">📄 ${file} (${matches.length})</div>`)
                .appendTo($res);
            const $grp = $('<div></div>').appendTo($res);
            let grpVisible = true;
            $hdr.on('click', () => { grpVisible = !grpVisible; $grp.toggle(grpVisible); });

            matches.forEach(m => {
                const raw = m.content;
                const idx = raw.toLowerCase().indexOf(ql);
                let display = raw;
                if (idx >= 0) {
                    const pre = _esc(raw.slice(0, idx));
                    const hl  = _esc(raw.slice(idx, idx + query.length));
                    const post = _esc(raw.slice(idx + query.length));
                    display = `${pre}<span class="dkce-hl">${hl}</span>${post}`;
                } else {
                    display = _esc(raw);
                }
                $(`<div class="dkce-search-match" title="${file}:${m.line}">
                     <span style="color:#555;margin-right:6px">${m.line}</span>${display}
                   </div>`)
                    .on('click', () => this._openFileAtLine(this.state.currentApp, file, m.line))
                    .appendTo($grp);
            });
        });
    }

    _openFileAtLine(appName, filePath, lineNumber) {
        const existing = this.state.tabs.find(t => t.appName === appName && t.filePath === filePath);
        if (existing) {
            this._switchTab(existing.id);
            setTimeout(() => this.editor.revealLineInCenter(lineNumber), 50);
        } else {
            frappe.call({
                method: 'frappe_devkit.api.code_editor.read_file',
                args: { app_name: appName, file_path: filePath },
                callback: r => {
                    const data = r.message;
                    const tabId = 'tab_' + Date.now();
                    const uri = this.monaco.Uri.parse(`file:///${appName}/${filePath}`);
                    let model = this.monaco.editor.getModel(uri);
                    if (!model) model = this.monaco.editor.createModel(data.content, data.language, uri);
                    const tab = { id: tabId, appName, filePath, fileName: data.name, language: data.language,
                                  model, viewState: null, isModified: false, origContent: data.content };
                    this.state.tabs.push(tab);
                    this._addTab(tab);
                    this._switchTab(tabId);
                    setTimeout(() => {
                        this.editor.revealLineInCenter(lineNumber);
                        this.editor.setPosition({ lineNumber, column: 1 });
                        this.editor.focus();
                    }, 100);
                }
            });
        }
    }

    // ── Git ─────────────────────────────────────────────────────────────────
    _refreshGit() {
        if (!this.state.currentApp) return;
        frappe.call({
            method: 'frappe_devkit.api.code_editor.get_git_status',
            args: { app_name: this.state.currentApp },
            callback: r => {
                const info = r.message || {};
                this.state.gitInfo = { branch: info.branch || '', changes: info.changes || {} };
                const branch = info.branch || '—';
                $('#dkce-sb-branch').text(`⎇ ${branch}`);
                $('#dkce-git-branch').text(`⎇ ${branch}`);
                this._renderGitPanel(info.changes || {});
            }
        });
    }

    _renderGitPanel(changes) {
        const $panel = $('#dkce-git-scroll').empty();
        const entries = Object.entries(changes);
        if (!entries.length) {
            $panel.html('<div class="dkce-tree-loading" style="padding:12px 8px;">No changes — working tree clean</div>');
            return;
        }

        // Split by staged (X column) vs unstaged/untracked (Y column)
        const staged   = entries.filter(([, c]) => c[0] !== ' ' && c !== '??');
        const unstaged = entries.filter(([, c]) => c[1] !== ' ' || c === '??');

        const addFile = ($target, fpath, code, isStagedSection) => {
            const isUntracked = code === '??';
            const letter = isStagedSection ? code[0] : (isUntracked ? 'U' : code[1]);
            const colorClass = { M:'dkce-git-M', A:'dkce-git-A', D:'dkce-git-D', U:'dkce-git-U', R:'dkce-git-M' }[letter] || 'dkce-git-U';
            const $row = $(`<div class="dkce-git-file" title="${_esc(fpath)}" style="cursor:pointer;">
                <span class="dkce-git-code ${colorClass}">${_esc(letter)}</span>
                <span class="dkce-git-fname">${_esc(fpath)}</span>
                <div class="dkce-git-file-acts"></div>
            </div>`);
            const $acts = $row.find('.dkce-git-file-acts');
            if (isStagedSection) {
                $('<button class="dkce-git-file-act unstage" title="Unstage">−</button>')
                    .on('click', e => { e.stopPropagation(); this._gitUnstageFile(fpath); })
                    .appendTo($acts);
            } else {
                $('<button class="dkce-git-file-act stage" title="Stage">+</button>')
                    .on('click', e => { e.stopPropagation(); this._gitStageFile(fpath); })
                    .appendTo($acts);
                if (!isUntracked) {
                    $('<button class="dkce-git-file-act discard" title="Discard changes">↩</button>')
                        .on('click', e => { e.stopPropagation(); this._gitDiscardFile(fpath); })
                        .appendTo($acts);
                }
            }
            $row.on('click', () => this._openFile(this.state.currentApp, fpath));
            $target.append($row);
        };

        if (staged.length) {
            $panel.append('<div class="dkce-git-section-hdr">Staged Changes</div>');
            staged.forEach(([f, c]) => addFile($panel, f, c, true));
        }
        if (unstaged.length) {
            $panel.append('<div class="dkce-git-section-hdr">Changes</div>');
            unstaged.forEach(([f, c]) => addFile($panel, f, c, false));
        }
    }

    // ── Panel Switching ────────────────────────────────────────────────────
    _switchPanel(name) {
        this.state.sidePanel = name;
        ['explorer', 'search', 'git', 'history', 'claude'].forEach(p => {
            $(`#dkce-panel-${p}`).toggleClass('active', p === name);
            $(`#dkce-act-${p}`).toggleClass('active', p === name);
        });
        if (name === 'search')  setTimeout(() => $('#dkce-search-q').focus(), 50);
        if (name === 'history') this._loadHistory();
        if (name === 'claude')  this._checkClaudeConfig();
    }

    // ── Theme ──────────────────────────────────────────────────────────────
    _toggleTheme() {
        const isLight = this.state.theme === 'vs';
        this.state.theme = isLight ? 'vs-dark' : 'vs';
        this.monaco && this.monaco.editor.setTheme(this.state.theme);
        $('#dkce-root').toggleClass('light', !isLight);
        $('#dkce-btn-theme').text(isLight ? '🌙 Theme' : '☀ Theme');
        this._saveSettings();
    }

    // ── Font Size ──────────────────────────────────────────────────────────
    _changeFontSize(delta) {
        const s = this.state.settings;
        s.fontSize = Math.max(8, Math.min(32, s.fontSize + delta));
        this.editor && this.editor.updateOptions({ fontSize: s.fontSize });
        $('#dkce-font-sz').text(s.fontSize);
        this._saveSettings();
    }

    // ── Word Wrap / Minimap ────────────────────────────────────────────────
    _toggleWrap() {
        const s = this.state.settings;
        s.wordWrap = s.wordWrap === 'off' ? 'on' : 'off';
        this.editor && this.editor.updateOptions({ wordWrap: s.wordWrap });
        $('#dkce-btn-wrap').toggleClass('active', s.wordWrap === 'on');
        this._saveSettings();
    }

    _toggleMinimap() {
        const s = this.state.settings;
        s.minimap = !s.minimap;
        this.editor && this.editor.updateOptions({ minimap: { enabled: s.minimap } });
        $('#dkce-btn-minimap').toggleClass('active', s.minimap);
        this._saveSettings();
    }

    // ── Settings Dialog ────────────────────────────────────────────────────
    _openSettings() {
        const s = this.state.settings;
        const $overlay = $(`
          <div class="dkce-overlay" id="dkce-settings-overlay">
            <div class="dkce-dialog">
              <button class="dkce-dialog-close" id="dkce-settings-close">×</button>
              <h3>⚙ Editor Settings</h3>
              <div class="dkce-setting-row">
                <label>Font Size</label>
                <input class="dkce-setting-ctrl" id="dkce-s-fontsize" type="number" min="8" max="32" value="${s.fontSize}">
              </div>
              <div class="dkce-setting-row">
                <label>Tab Size</label>
                <select class="dkce-setting-ctrl" id="dkce-s-tabsize">
                  ${[2,3,4,6,8].map(n => `<option ${s.tabSize===n?'selected':''} value="${n}">${n}</option>`).join('')}
                </select>
              </div>
              <div class="dkce-setting-row">
                <label>Indent Style</label>
                <select class="dkce-setting-ctrl" id="dkce-s-indent">
                  <option value="spaces" ${s.insertSpaces?'selected':''}>Spaces</option>
                  <option value="tabs"   ${!s.insertSpaces?'selected':''}>Tabs</option>
                </select>
              </div>
              <div class="dkce-setting-row">
                <label>Word Wrap</label>
                <select class="dkce-setting-ctrl" id="dkce-s-wrap">
                  <option value="off" ${s.wordWrap==='off'?'selected':''}>Off</option>
                  <option value="on"  ${s.wordWrap==='on'?'selected':''}>On</option>
                  <option value="wordWrapColumn" ${s.wordWrap==='wordWrapColumn'?'selected':''}>Column</option>
                </select>
              </div>
              <div class="dkce-setting-row">
                <label>Line Numbers</label>
                <select class="dkce-setting-ctrl" id="dkce-s-linenums">
                  <option value="on"       ${s.lineNumbers==='on'?'selected':''}>On</option>
                  <option value="off"      ${s.lineNumbers==='off'?'selected':''}>Off</option>
                  <option value="relative" ${s.lineNumbers==='relative'?'selected':''}>Relative</option>
                </select>
              </div>
              <div class="dkce-setting-row">
                <label>Render Whitespace</label>
                <select class="dkce-setting-ctrl" id="dkce-s-ws">
                  <option value="none"       ${s.renderWhitespace==='none'?'selected':''}>None</option>
                  <option value="boundary"   ${s.renderWhitespace==='boundary'?'selected':''}>Boundary</option>
                  <option value="all"        ${s.renderWhitespace==='all'?'selected':''}>All</option>
                  <option value="trailing"   ${s.renderWhitespace==='trailing'?'selected':''}>Trailing</option>
                </select>
              </div>
              <div class="dkce-setting-row">
                <label>Minimap</label>
                <select class="dkce-setting-ctrl" id="dkce-s-minimap">
                  <option value="1" ${s.minimap?'selected':''}>Enabled</option>
                  <option value="0" ${!s.minimap?'selected':''}>Disabled</option>
                </select>
              </div>
              <div class="dkce-setting-row">
                <label>Toolbar Size</label>
                <select class="dkce-setting-ctrl" id="dkce-s-tbsize">
                  <option value="compact" ${s.toolbarSize==='compact'?'selected':''}>Compact</option>
                  <option value="normal"  ${s.toolbarSize==='normal'?'selected':''}>Normal</option>
                  <option value="large"   ${s.toolbarSize==='large'?'selected':''}>Large</option>
                </select>
              </div>
              <div style="margin:14px 0 6px;font-size:11px;font-weight:700;color:#888;letter-spacing:.06em;text-transform:uppercase;">File Navigator</div>
              <div class="dkce-setting-row">
                <label>Sidebar Width — <span id="dkce-s-sw-val">${s.sidebarWidth}</span> px</label>
                <input class="dkce-setting-ctrl" type="range" id="dkce-s-sidebarw"
                  min="160" max="520" step="10" value="${s.sidebarWidth}"
                  style="padding:4px 0;cursor:pointer;"
                  oninput="document.getElementById('dkce-s-sw-val').textContent=this.value">
              </div>
              <div class="dkce-setting-row">
                <label>Tree Font Size — <span id="dkce-s-tfs-val">${s.treeFontSize}</span> px</label>
                <input class="dkce-setting-ctrl" type="range" id="dkce-s-treefs"
                  min="10" max="18" step="1" value="${s.treeFontSize}"
                  style="padding:4px 0;cursor:pointer;"
                  oninput="document.getElementById('dkce-s-tfs-val').textContent=this.value">
              </div>
              <div class="dkce-dialog-footer">
                <button class="dkce-dialog-btn secondary" id="dkce-settings-cancel">Cancel</button>
                <button class="dkce-dialog-btn primary"   id="dkce-settings-save">Apply</button>
              </div>
            </div>
          </div>
        `);
        $('body').append($overlay);

        $('#dkce-settings-close, #dkce-settings-cancel').on('click', () => $overlay.remove());
        $('#dkce-settings-save').on('click', () => {
            s.fontSize        = parseInt($('#dkce-s-fontsize').val()) || 14;
            s.tabSize         = parseInt($('#dkce-s-tabsize').val()) || 4;
            s.insertSpaces    = $('#dkce-s-indent').val() === 'spaces';
            s.wordWrap        = $('#dkce-s-wrap').val();
            s.lineNumbers     = $('#dkce-s-linenums').val();
            s.renderWhitespace= $('#dkce-s-ws').val();
            s.minimap         = $('#dkce-s-minimap').val() === '1';
            s.sidebarWidth    = parseInt($('#dkce-s-sidebarw').val()) || 260;
            s.treeFontSize    = parseInt($('#dkce-s-treefs').val()) || 13;
            s.toolbarSize     = $('#dkce-s-tbsize').val() || 'normal';
            this._applySettings();
            $('#dkce-font-sz').text(s.fontSize);
            $overlay.remove();
            this._toast('Settings applied', 'success');
        });
        $overlay.on('click', e => { if (e.target === $overlay[0]) $overlay.remove(); });
    }

    // ── Persistence ────────────────────────────────────────────────────────
    _loadPersistedSettings() {
        try {
            const raw = localStorage.getItem('dkce_editor_settings');
            if (!raw) return;
            const saved = JSON.parse(raw);
            // Merge saved settings into defaults (new keys added later still get defaults)
            if (saved.settings) Object.assign(this.state.settings, saved.settings);
            if (saved.theme)    this.state.theme = saved.theme;
            if (saved.terminalHeight) this.state.terminal.height = saved.terminalHeight;
        } catch (e) { /* corrupt storage — ignore, keep defaults */ }
    }

    _saveSettings() {
        try {
            localStorage.setItem('dkce_editor_settings', JSON.stringify({
                settings:      this.state.settings,
                theme:         this.state.theme,
                terminalHeight: this.state.terminal.height,
            }));
        } catch (e) { /* storage full or unavailable — ignore */ }
    }

    _applySettings() {
        const s = this.state.settings;

        // ── Monaco editor options ──
        if (this.editor) {
            this.editor.updateOptions({
                fontSize:         s.fontSize,
                tabSize:          s.tabSize,
                insertSpaces:     s.insertSpaces,
                wordWrap:         s.wordWrap,
                lineNumbers:      s.lineNumbers,
                renderWhitespace: s.renderWhitespace,
                minimap:          { enabled: s.minimap },
                smoothScrolling:  s.smoothScrolling,
            });
            requestAnimationFrame(() => this.editor.layout());
        }

        // ── Theme ──
        if (this.monaco) this.monaco.editor.setTheme(this.state.theme);
        const isLight = this.state.theme === 'vs';
        $('#dkce-root').toggleClass('light', isLight);
        $('#dkce-btn-theme').text(isLight ? '☀ Theme' : '🌙 Theme');

        // ── Toolbar / status bar labels ──
        $('#dkce-font-sz').text(s.fontSize);
        $('#dkce-sb-tabs').text(`${s.insertSpaces ? 'Spaces' : 'Tabs'}: ${s.tabSize}`);
        $('#dkce-btn-wrap').toggleClass('active', s.wordWrap === 'on');
        $('#dkce-btn-minimap').toggleClass('active', s.minimap);

        // ── Sidebar width, tree font size, toolbar size via CSS custom properties ──
        const root = document.getElementById('dkce-root');
        if (root) {
            root.style.setProperty('--dkce-sidebar-w', s.sidebarWidth + 'px');
            root.style.setProperty('--dkce-tree-fs',   s.treeFontSize  + 'px');
            const tbMap = { compact: '28px', normal: '36px', large: '44px' };
            const tbFsMap = { compact: '11px', normal: '13px', large: '15px' };
            root.style.setProperty('--dkce-tb-h',  tbMap[s.toolbarSize]   || '36px');
            root.style.setProperty('--dkce-tb-fs', tbFsMap[s.toolbarSize] || '12px');
        }

        // ── Persist ──
        this._saveSettings();
    }

    // ── Status Bar Helpers ─────────────────────────────────────────────────
    _updateBreadcrumb(filePath) {
        if (!filePath) { $('#dkce-breadcrumb').html('&nbsp;'); return; }
        const parts = filePath.split('/');
        const html = parts.map((p, i) => {
            const isLast = i === parts.length - 1;
            return `<span style="${isLast ? 'color:#ccc' : 'color:#888'}">${_esc(p)}</span>`;
        }).join('<span class="dkce-breadcrumb-sep">›</span>');
        $('#dkce-breadcrumb').html(
            `<span style="color:#888">${_esc(this.state.currentApp)}</span><span class="dkce-breadcrumb-sep">›</span>${html}`
        );
    }

    _updateLangStatus(language) {
        $('#dkce-sb-lang').text(language || '—');
    }

    _updateSaveStatus(isModified) {
        $('#dkce-sb-save').text(isModified ? '● Unsaved' : '✓ Saved');
    }

    // ── Notifications ──────────────────────────────────────────────────────
    _toast(message, type = 'info') {
        const $t = $(`<div class="dkce-toast ${type}">${_esc(message)}</div>`);
        $('body').append($t);
        setTimeout(() => $t.fadeOut(300, () => $t.remove()), 3000);
    }

    // ── Helpers ─────────────────────────────────────────────────────────────
    _activeTab() {
        return this.state.tabs.find(t => t.id === this.state.activeTabId) || null;
    }

    _fileIcon(ext) {
        const icons = {
            py: '🐍', js: '📜', ts: '📘', jsx: '⚛', tsx: '⚛',
            html: '🌐', css: '🎨', scss: '🎨', less: '🎨',
            json: '{ }', md: '📝', txt: '📄', sh: '⚙',
            yaml: '⚙', yml: '⚙', toml: '⚙', cfg: '⚙', ini: '⚙',
            sql: '🗄', xml: '📋', env: '🔑',
        };
        return icons[ext] || '📄';
    }

    // ── Code Intelligence ───────────────────────────────────────────────────
    _registerIntelligence() {
        const monaco = this.monaco;

        // ── CSS: Style the suggest widget, hover, and parameter hints ────
        if (!document.getElementById('dkce-intel-css')) {
            const sty = document.createElement('style');
            sty.id = 'dkce-intel-css';
            sty.textContent = `
/* ── Suggest Widget ─────────────────────────────────────────── */
.monaco-editor .suggest-widget {
    border-radius: 6px !important;
    border: 1px solid #2a2d2e !important;
    box-shadow: 0 8px 32px rgba(0,0,0,.65) !important;
    overflow: hidden !important;
}
.monaco-editor .suggest-widget .monaco-list {
    font-size: 13px !important;
}
.monaco-editor .suggest-widget .monaco-list .monaco-list-row {
    height: 28px !important;
    line-height: 28px !important;
    border-radius: 0 !important;
}
.monaco-editor .suggest-widget .monaco-list .monaco-list-row .contents {
    padding: 0 12px 0 10px !important;
    box-sizing: border-box !important;
}
.monaco-editor .suggest-widget .monaco-list .monaco-list-row .main {
    display: flex !important;
    align-items: center !important;
    overflow: hidden !important;
}
.monaco-editor .suggest-widget .monaco-list .monaco-list-row.focused,
.monaco-editor .suggest-widget .monaco-list .monaco-list-row:hover {
    background: #094771 !important;
}
.monaco-editor .suggest-widget .details-label {
    font-size: 11px !important;
}
.monaco-editor .suggest-widget .suggest-status-bar {
    font-size: 11px !important;
    border-top: 1px solid #2a2d2e !important;
    padding: 2px 8px !important;
    background: #1a1a1a !important;
}
/* Inline suggestion ghost text */
.monaco-editor .ghost-text-decoration {
    opacity: 0.45 !important;
    font-style: italic !important;
}
/* ── Details/Docs side panel ─── */
.monaco-editor .suggest-widget .suggest-details-container {
    border-left: 1px solid #2a2d2e !important;
    background: #1e1e1e !important;
}
.monaco-editor .suggest-widget .suggest-details {
    padding: 6px 10px !important;
    font-size: 12px !important;
    line-height: 1.6 !important;
}
.monaco-editor .suggest-widget .suggest-details .type-label {
    color: #75beff !important;
    font-size: 11px !important;
}
/* ── Hover widget ─── */
.monaco-editor .monaco-hover {
    border-radius: 6px !important;
    border: 1px solid #2a2d2e !important;
    box-shadow: 0 4px 16px rgba(0,0,0,.55) !important;
    max-width: 520px !important;
}
.monaco-editor .monaco-hover hr {
    border-color: #2a2d2e !important;
}
/* ── Parameter hints ─── */
.monaco-editor .parameter-hints-widget {
    border-radius: 6px !important;
    border: 1px solid #2a2d2e !important;
    box-shadow: 0 4px 16px rgba(0,0,0,.55) !important;
}
.monaco-editor .parameter-hints-widget .signature.has-docs {
    border-bottom: 1px solid #2a2d2e !important;
}
.monaco-editor .parameter-hints-widget .parameter.active {
    color: #e2a91b !important;
    font-weight: bold !important;
}
/* ── Context menu ─── */
.monaco-editor .context-view .monaco-menu {
    border-radius: 6px !important;
    border: 1px solid #3c3c3c !important;
    box-shadow: 0 6px 24px rgba(0,0,0,.55) !important;
    overflow: hidden !important;
}
.monaco-editor .context-view .action-item .action-label {
    font-size: 12px !important;
}
/* ── Code lens ─── */
.monaco-editor .codelens-decoration {
    font-size: 11px !important;
    opacity: 0.7 !important;
}
/* ── Find widget ─── */
.monaco-editor .find-widget {
    border-radius: 6px !important;
    border: 1px solid #2a2d2e !important;
    box-shadow: 0 4px 16px rgba(0,0,0,.55) !important;
}
/* ── Rename input ─── */
.monaco-editor .rename-box {
    border-radius: 4px !important;
    border: 2px solid #007acc !important;
    box-shadow: 0 2px 8px rgba(0,122,204,.4) !important;
}
/* ── Snippet placeholder highlight ─── */
.monaco-editor .snippet-placeholder {
    background: rgba(0,122,204,.18) !important;
    border: 1px solid rgba(0,122,204,.5) !important;
    border-radius: 2px !important;
}
.monaco-editor .final-snippet-placeholder {
    border: 1px solid rgba(0,122,204,.3) !important;
    border-radius: 2px !important;
}
`;
            document.head.appendChild(sty);
        }

        // Guard: only register providers once per session
        if (window._dkceProvidersRegistered) return;
        window._dkceProvidersRegistered = true;

        const providerOpts = {
            python: { triggerCharacters: ['.', '(', '@', '"', "'"] },
            javascript: { triggerCharacters: ['.', '(', '"', "'"] },
            typescript: { triggerCharacters: ['.', '(', '"', "'"] },
        };

        const extractSymbols = (model, position, range) => {
            const K = this.monaco.languages.CompletionItemKind;
            const content = model.getValue();
            const cursorOffset = model.getOffsetAt(position);
            const word = model.getWordUntilPosition(position).word;
            const symbols = new Map();

            // Python: variables (x = ..., for x in, with ... as x, except ... as x)
            // JS: var/let/const/function declarations
            const varPatterns = [
                // Python assignment
                /^[ \t]*([a-zA-Z_]\w*)(?:\s*,\s*[a-zA-Z_]\w*)*\s*=/gm,
                // Python for loop vars
                /\bfor\s+([a-zA-Z_]\w*)(?:\s*,\s*([a-zA-Z_]\w*))*\s+in\b/gm,
                // Python with ... as x
                /\bwith\b.+\bas\s+([a-zA-Z_]\w*)/gm,
                // Python except ... as x
                /\bexcept\b.+\bas\s+([a-zA-Z_]\w*)/gm,
                // Python function/class parameters & def names
                /\bdef\s+([a-zA-Z_]\w*)\s*\(([^)]*)\)/gm,
                /\bclass\s+([a-zA-Z_]\w*)/gm,
                // Python import
                /\bimport\s+([a-zA-Z_][\w.]*(?:\s*,\s*[a-zA-Z_][\w.]*)*)/gm,
                /\bfrom\s+[^\s]+\s+import\s+([a-zA-Z_][\w]*(?:\s*,\s*[a-zA-Z_][\w]*)*)/gm,
                // JS/TS var/let/const
                /\b(?:var|let|const)\s+([a-zA-Z_$][\w$]*)/gm,
                // JS/TS function declarations
                /\bfunction\s+([a-zA-Z_$][\w$]*)/gm,
                // JS/TS arrow / method
                /\b([a-zA-Z_$][\w$]*)\s*[:=]\s*(?:function|\(|async\s*\()/gm,
            ];

            const addSym = (name, kind) => {
                if (!name || name.length < 2 || symbols.has(name)) return;
                // skip Python keywords and common builtins
                const skip = new Set(['if','else','elif','for','while','try','except','finally',
                    'with','as','import','from','return','yield','pass','break','continue',
                    'class','def','lambda','and','or','not','in','is','None','True','False',
                    'var','let','const','function','this','new','return','typeof','instanceof',
                    'true','false','null','undefined','async','await','of']);
                if (skip.has(name)) return;
                symbols.set(name, kind);
            };

            for (const pat of varPatterns) {
                let m;
                while ((m = pat.exec(content)) !== null) {
                    // For def pattern: capture name + params
                    if (pat.source.startsWith('\\bdef')) {
                        addSym(m[1], K.Function);
                        if (m[2]) {
                            m[2].split(',').forEach(p => {
                                const pname = p.trim().replace(/[=:].*/,'').trim().replace(/^\*/,'');
                                addSym(pname, K.Variable);
                            });
                        }
                    } else if (pat.source.startsWith('\\bclass')) {
                        addSym(m[1], K.Class);
                    } else if (pat.source.includes('import')) {
                        m[1].split(',').forEach(n => addSym(n.trim().split('.')[0], K.Module));
                    } else {
                        // multiple capture groups possible (tuple unpacking / for a, b in)
                        for (let i = 1; i < m.length; i++) {
                            if (m[i]) m[i].split(',').forEach(n => addSym(n.trim(), K.Variable));
                        }
                    }
                }
            }

            // Also extract every unique word in the document (length ≥ 3) as a fallback
            const wordRe = /[a-zA-Z_$][a-zA-Z0-9_$]{2,}/g;
            let wm;
            while ((wm = wordRe.exec(content)) !== null) {
                const name = wm[0];
                if (!symbols.has(name)) symbols.set(name, K.Text);
            }

            // Build completion items, exclude current word being typed
            const items = [];
            for (const [name, kind] of symbols) {
                if (name === word) continue;
                items.push({
                    label: name,
                    kind,
                    insertText: name,
                    range,
                    sortText: kind === K.Text ? '9' + name : '5' + name,
                    detail: kind === K.Function ? 'function'
                          : kind === K.Class    ? 'class'
                          : kind === K.Module   ? 'module'
                          : kind === K.Variable ? 'variable'
                          : 'word',
                });
            }
            return items;
        };

        const makeProvider = lang => ({
            ...providerOpts[lang],
            provideCompletionItems: (model, position) => {
                const word = model.getWordUntilPosition(position);
                const range = {
                    startLineNumber: position.lineNumber, endLineNumber: position.lineNumber,
                    startColumn: word.startColumn, endColumn: word.endColumn,
                };
                const snippets = this._getFrappeSnippets(lang, range);
                const keywords = this._getSyntaxKeywords(lang, range);
                const symbols = extractSymbols(model, position, range);
                // Deduplicate: snippets win over keywords/symbols
                const topLabels = new Set(snippets.map(s => s.label));
                const uniqueKeywords = keywords.filter(k => !topLabels.has(k.label));
                const allTopLabels = new Set([...topLabels, ...uniqueKeywords.map(k => k.label)]);
                const uniqueSymbols = symbols.filter(s => !allTopLabels.has(s.label));
                return { suggestions: [...snippets, ...uniqueKeywords, ...uniqueSymbols] };
            },
        });

        monaco.languages.registerCompletionItemProvider('python', makeProvider('python'));
        monaco.languages.registerCompletionItemProvider('javascript', makeProvider('javascript'));
        monaco.languages.registerCompletionItemProvider('typescript', makeProvider('javascript'));
    }

    _getSyntaxKeywords(lang, range) {
        const K = this.monaco.languages.CompletionItemKind;
        const kw = (label, detail, kind = K.Keyword) => ({
            label, kind, detail, insertText: label, range, sortText: '3' + label,
        });
        const bi = (label, detail, kind = K.Function) => ({
            label, kind, detail, insertText: label, range, sortText: '4' + label,
        });

        if (lang === 'python') {
            return [
                // keywords
                kw('if', 'keyword'), kw('else', 'keyword'), kw('elif', 'keyword'),
                kw('for', 'keyword'), kw('while', 'keyword'), kw('with', 'keyword'),
                kw('try', 'keyword'), kw('except', 'keyword'), kw('finally', 'keyword'),
                kw('return', 'keyword'), kw('yield', 'keyword'), kw('raise', 'keyword'),
                kw('import', 'keyword'), kw('from', 'keyword'), kw('as', 'keyword'),
                kw('def', 'keyword'), kw('class', 'keyword'), kw('lambda', 'keyword'),
                kw('pass', 'keyword'), kw('break', 'keyword'), kw('continue', 'keyword'),
                kw('del', 'keyword'), kw('global', 'keyword'), kw('nonlocal', 'keyword'),
                kw('assert', 'keyword'), kw('in', 'keyword'), kw('not', 'keyword'),
                kw('and', 'keyword'), kw('or', 'keyword'), kw('is', 'keyword'),
                kw('True', 'bool'), kw('False', 'bool'), kw('None', 'constant'),
                kw('async', 'keyword'), kw('await', 'keyword'),
                // builtins
                bi('print', 'builtin'), bi('len', 'builtin'), bi('range', 'builtin'),
                bi('str', 'builtin type'), bi('int', 'builtin type'), bi('float', 'builtin type'),
                bi('list', 'builtin type'), bi('dict', 'builtin type'), bi('set', 'builtin type'),
                bi('tuple', 'builtin type'), bi('bool', 'builtin type'), bi('bytes', 'builtin type'),
                bi('type', 'builtin'), bi('isinstance', 'builtin'), bi('issubclass', 'builtin'),
                bi('hasattr', 'builtin'), bi('getattr', 'builtin'), bi('setattr', 'builtin'),
                bi('delattr', 'builtin'), bi('callable', 'builtin'), bi('super', 'builtin'),
                bi('open', 'builtin'), bi('input', 'builtin'), bi('enumerate', 'builtin'),
                bi('zip', 'builtin'), bi('map', 'builtin'), bi('filter', 'builtin'),
                bi('sorted', 'builtin'), bi('reversed', 'builtin'), bi('any', 'builtin'),
                bi('all', 'builtin'), bi('min', 'builtin'), bi('max', 'builtin'),
                bi('sum', 'builtin'), bi('abs', 'builtin'), bi('round', 'builtin'),
                bi('repr', 'builtin'), bi('id', 'builtin'), bi('vars', 'builtin'),
                bi('dir', 'builtin'), bi('help', 'builtin'), bi('next', 'builtin'),
                bi('iter', 'builtin'), bi('hash', 'builtin'), bi('hex', 'builtin'),
                bi('oct', 'builtin'), bi('bin', 'builtin'), bi('chr', 'builtin'),
                bi('ord', 'builtin'), bi('format', 'builtin'), bi('staticmethod', 'builtin'),
                bi('classmethod', 'builtin'), bi('property', 'builtin'),
            ];
        } else {
            // JavaScript / TypeScript
            return [
                // keywords
                kw('var', 'keyword'), kw('let', 'keyword'), kw('const', 'keyword'),
                kw('function', 'keyword'), kw('return', 'keyword'), kw('if', 'keyword'),
                kw('else', 'keyword'), kw('for', 'keyword'), kw('while', 'keyword'),
                kw('do', 'keyword'), kw('switch', 'keyword'), kw('case', 'keyword'),
                kw('break', 'keyword'), kw('continue', 'keyword'), kw('default', 'keyword'),
                kw('try', 'keyword'), kw('catch', 'keyword'), kw('finally', 'keyword'),
                kw('throw', 'keyword'), kw('new', 'keyword'), kw('delete', 'keyword'),
                kw('typeof', 'keyword'), kw('instanceof', 'keyword'), kw('in', 'keyword'),
                kw('of', 'keyword'), kw('class', 'keyword'), kw('extends', 'keyword'),
                kw('super', 'keyword'), kw('this', 'keyword'), kw('import', 'keyword'),
                kw('export', 'keyword'), kw('from', 'keyword'), kw('async', 'keyword'),
                kw('await', 'keyword'), kw('yield', 'keyword'), kw('static', 'keyword'),
                kw('get', 'keyword'), kw('set', 'keyword'), kw('void', 'keyword'),
                kw('true', 'bool'), kw('false', 'bool'), kw('null', 'constant'),
                kw('undefined', 'constant'), kw('NaN', 'constant'), kw('Infinity', 'constant'),
                // builtins
                bi('console', 'global'), bi('window', 'global'), bi('document', 'global'),
                bi('Math', 'global object'), bi('JSON', 'global object'),
                bi('Promise', 'global'), bi('Array', 'global type'), bi('Object', 'global type'),
                bi('String', 'global type'), bi('Number', 'global type'),
                bi('Boolean', 'global type'), bi('Date', 'global type'),
                bi('RegExp', 'global type'), bi('Map', 'global type'), bi('Set', 'global type'),
                bi('Error', 'global type'), bi('Symbol', 'global type'),
                bi('parseInt', 'global'), bi('parseFloat', 'global'),
                bi('isNaN', 'global'), bi('isFinite', 'global'),
                bi('setTimeout', 'global'), bi('setInterval', 'global'),
                bi('clearTimeout', 'global'), bi('clearInterval', 'global'),
                bi('fetch', 'global'), bi('alert', 'global'), bi('confirm', 'global'),
                bi('encodeURIComponent', 'global'), bi('decodeURIComponent', 'global'),
                // Frappe-JS globals
                bi('frappe', 'frappe global'), bi('cur_frm', 'frappe | current form'),
                bi('cur_list', 'frappe | current list'), bi('__', 'frappe | translate'),
            ];
        }
    }

    _getFrappeSnippets(lang, range) {
        const K = this.monaco.languages.CompletionItemKind;
        const R = this.monaco.languages.CompletionItemInsertTextRule.InsertAsSnippet;

        // Helper: snippet with tab-stops
        const s = (label, insert, detail, doc = '', kind = K.Snippet) => ({
            label, kind, detail, documentation: { value: doc },
            insertText: insert, insertTextRules: R, range,
            sortText: '0' + label,   // sort snippets to top
        });
        // Helper: plain word completion
        const w = (label, insert, detail, kind = K.Function) => ({
            label, kind, detail, insertText: insert, range, sortText: '1' + label,
        });

        // ── Python / Frappe ──────────────────────────────────────────────
        if (lang === 'python') {
            return [
                // ── Document operations ──
                s('frappe.get_doc',
                    'frappe.get_doc("${1:DocType}", "${2:name}")',
                    'frappe | get document', '**Get an existing document**\n```py\ndoc = frappe.get_doc("Sales Order", name)\n```'),
                s('frappe.new_doc',
                    'frappe.new_doc("${1:DocType}")',
                    'frappe | new document', '**Create a new unsaved document instance**'),
                s('frappe.get_cached_doc',
                    'frappe.get_cached_doc("${1:DocType}", "${2:name}")',
                    'frappe | cached doc', 'Fetch from request cache, falls back to DB'),
                s('doc-save-pattern',
                    'doc = frappe.get_doc("${1:DocType}", "${2:name}")\ndoc.${3:field} = ${4:value}\ndoc.save(ignore_permissions=True)',
                    'frappe | get → edit → save', 'Full get-edit-save pattern'),

                // ── frappe.db ──
                s('frappe.db.get_value',
                    'frappe.db.get_value("${1:DocType}", {"${2:field}": "${3:value}"}, "${4:fieldname}")',
                    'frappe.db | get value', '**Get a single field value from DB**\n```py\nfrappe.db.get_value("Item", name, "item_name")\n```'),
                s('frappe.db.get_value-multi',
                    'frappe.db.get_value("${1:DocType}", {"${2:field}": "${3:value}"}, ["${4:f1}", "${5:f2}"], as_dict=True)',
                    'frappe.db | get multiple fields', 'Get several fields at once as dict'),
                s('frappe.db.set_value',
                    'frappe.db.set_value("${1:DocType}", "${2:name}", "${3:field}", ${4:value})',
                    'frappe.db | set value', 'Set a field directly in DB without loading the doc'),
                s('frappe.db.get_list',
                    'frappe.db.get_list(\n\t"${1:DocType}",\n\tfields=["${2:name}", "${3:field}"],\n\tfilters={"${4:field}": "${5:value}"},\n\torder_by="${6:creation desc}",\n\tlimit=${7:20},\n)',
                    'frappe.db | get list', 'Query multiple documents'),
                s('frappe.db.get_all',
                    'frappe.db.get_all(\n\t"${1:DocType}",\n\tfields=["${2:name}", "${3:field}"],\n\tfilters={"${4:field}": "${5:value}"},\n)',
                    'frappe.db | get all (no limit)', 'Get all matching records (no default limit)'),
                s('frappe.db.exists',
                    'frappe.db.exists("${1:DocType}", "${2:name}")',
                    'frappe.db | exists', 'Returns name if exists, else None'),
                s('frappe.db.count',
                    'frappe.db.count("${1:DocType}", {"${2:field}": "${3:value}"})',
                    'frappe.db | count', 'Count matching records'),
                s('frappe.db.delete',
                    'frappe.db.delete("${1:DocType}", "${2:name}")',
                    'frappe.db | delete', 'Delete a record'),
                s('frappe.db.sql',
                    'frappe.db.sql(\n\t"""${1:SELECT * FROM `tabDocType` WHERE name = %s}""",\n\t(${2:name},),\n\tas_dict=1\n)',
                    'frappe.db | raw SQL', 'Run parameterized raw SQL'),

                // ── Messages & errors ──
                s('frappe.throw',
                    'frappe.throw(_("${1:Error message}"))',
                    'frappe | throw', 'Raise a ValidationError and stop execution'),
                s('frappe.msgprint',
                    'frappe.msgprint(_("${1:Message}"))',
                    'frappe | msgprint', 'Show a popup message to user'),
                s('frappe.log_error',
                    'frappe.log_error(title="${1:Error}", message=frappe.get_traceback())',
                    'frappe | log error', 'Write to Error Log DocType'),
                s('frappe.log_info',
                    'frappe.logger().info("${1:message}")',
                    'frappe | log info', 'Write to application log'),

                // ── Permissions ──
                s('frappe.has_permission',
                    'frappe.has_permission("${1:DocType}", "${2:read}", throw=True)',
                    'frappe | has permission', 'Check permission, optionally throw'),
                s('frappe.only_for',
                    'frappe.only_for(["${1:System Manager}"])',
                    'frappe | only for roles', 'Raise PermissionError if user lacks role'),

                // ── Decorators & session ──
                s('@frappe.whitelist',
                    '@frappe.whitelist()\ndef ${1:my_function}(${2:}):\n\t${0:pass}',
                    'frappe | @whitelist', 'Expose function to client-side frappe.call()'),
                w('frappe.session.user', 'frappe.session.user', 'frappe | current user', K.Variable),
                w('frappe.local.lang', 'frappe.local.lang', 'frappe | current language', K.Variable),
                w('frappe.flags', 'frappe.flags', 'frappe | request-scoped flags dict', K.Variable),

                // ── Email & jobs ──
                s('frappe.sendmail',
                    'frappe.sendmail(\n\trecipients=["${1:user@example.com}"],\n\tsubject="${2:Subject}",\n\ttemplate="${3:template_name}",\n\targs={\n\t\t"${4:key}": "${5:value}",\n\t},\n)',
                    'frappe | sendmail', 'Send email using a Jinja template'),
                s('frappe.enqueue',
                    'frappe.enqueue(\n\t"${1:app.module.function}",\n\tqueue="${2:default}",\n\tnow=False,\n\t${3:arg}=${4:value},\n)',
                    'frappe | enqueue bg job', 'Run function in RQ background queue'),

                // ── Utility ──
                s('frappe.get_hooks',
                    'frappe.get_hooks("${1:hook_name}")',
                    'frappe | get hooks', 'Get hook values merged across all apps'),
                s('frappe.utils.now',
                    'frappe.utils.now()',
                    'frappe.utils | now', 'Current datetime as string'),
                s('frappe.utils.today',
                    'frappe.utils.today()',
                    'frappe.utils | today', 'Today\'s date as string'),
                s('frappe.utils.add_days',
                    'frappe.utils.add_days(${1:frappe.utils.today()}, ${2:7})',
                    'frappe.utils | add days', 'Add N days to a date'),
                s('frappe.utils.flt',
                    'frappe.utils.flt(${1:value}, ${2:2})',
                    'frappe.utils | flt', 'Convert to float with precision'),
                s('frappe.utils.cint',
                    'frappe.utils.cint(${1:value})',
                    'frappe.utils | cint', 'Convert to int safely'),
                s('frappe.utils.fmt_money',
                    'frappe.utils.fmt_money(${1:amount}, currency="${2:USD}")',
                    'frappe.utils | fmt_money', 'Format as currency string'),

                // ── Class templates ──
                s('doctype-class',
                    'class ${1:MyDocType}(Document):\n\tdef validate(self):\n\t\t${0:pass}\n\n\tdef before_save(self):\n\t\tpass\n\n\tdef on_submit(self):\n\t\tpass\n\n\tdef on_cancel(self):\n\t\tpass\n\n\tdef on_trash(self):\n\t\tpass',
                    'frappe | DocType class template', 'Full DocType controller with hooks'),
                s('test-class',
                    'import frappe\nimport unittest\n\nclass Test${1:DocType}(unittest.TestCase):\n\tdef setUp(self):\n\t\tfrappe.set_user("Administrator")\n\n\tdef test_${2:basic}(self):\n\t\t${0:pass}',
                    'frappe | Test class template', 'Unit test class for a DocType'),
                s('try-frappe',
                    'try:\n\t${1:pass}\nexcept frappe.DoesNotExistError:\n\t${2:frappe.throw(_("Record not found"))}\nexcept Exception:\n\tfrappe.log_error(frappe.get_traceback())\n\tfrappe.throw(_("An error occurred"))',
                    'frappe | try/except pattern', 'Try block with Frappe error handling'),
            ];
        }

        // ── JavaScript / TypeScript / Frappe JS ─────────────────────────
        if (lang === 'javascript') {
            return [
                // ── API calls ──
                s('frappe.call',
                    'frappe.call({\n\tmethod: "${1:app.module.function}",\n\targs: {\n\t\t${2:key}: ${3:value},\n\t},\n\tcallback(r) {\n\t\t${0:console.log(r.message);}\n\t},\n});',
                    'frappe.call()', 'Make a server-side API call'),
                s('frappe.call-async',
                    'const r = await frappe.call({\n\tmethod: "${1:app.module.function}",\n\targs: { ${2:key}: ${3:value} },\n});\nconst result = r.message;',
                    'frappe.call() async/await', 'Async/await server call'),
                s('frappe.call-freeze',
                    'frappe.call({\n\tmethod: "${1:app.module.function}",\n\targs: { ${2:key}: ${3:value} },\n\tfreeze: true,\n\tfreeze_message: "${4:Loading…}",\n\tcallback(r) {\n\t\t${0}\n\t},\n});',
                    'frappe.call() with freeze', 'API call that freezes the screen'),

                // ── frappe.db client ──
                s('frappe.db.get_value',
                    'frappe.db.get_value("${1:DocType}", "${2:name}", "${3:field}")',
                    'frappe.db.get_value()', 'Get field value (client-side, returns Promise)'),
                s('frappe.db.get_list',
                    'frappe.db.get_list("${1:DocType}", {\n\tfields: ["${2:name}", "${3:field}"],\n\tfilters: { ${4:field}: "${5:value}" },\n\tlimit: ${6:20},\n})',
                    'frappe.db.get_list()', 'Query list client-side'),
                s('frappe.db.set_value',
                    'frappe.db.set_value("${1:DocType}", "${2:name}", "${3:field}", ${4:value})',
                    'frappe.db.set_value()', 'Update field value client-side'),
                s('frappe.db.exists',
                    'frappe.db.exists("${1:DocType}", "${2:name}")',
                    'frappe.db.exists()', 'Check if record exists (returns Promise)'),

                // ── Form events ──
                s('frappe.ui.form.on',
                    'frappe.ui.form.on("${1:DocType}", {\n\trefresh(frm) {\n\t\t${0}\n\t},\n\t${2:fieldname}(frm) {\n\t\t\n\t},\n\tbefore_save(frm) {\n\t\t\n\t},\n});',
                    'frappe.ui.form.on()', 'Register form event handlers'),
                s('frm.set_value',
                    'frm.set_value("${1:fieldname}", ${2:value});',
                    'frm.set_value()', 'Set a field value on the current form'),
                s('frm.get_value',
                    'frm.get_value("${1:fieldname}")',
                    'frm.get_value()', 'Read a field value from the form'),
                s('frm.get_field',
                    'frm.get_field("${1:fieldname}")',
                    'frm.get_field()', 'Get the field object (for direct manipulation)'),
                s('frm.set_query',
                    'frm.set_query("${1:link_fieldname}", function() {\n\treturn {\n\t\tfilters: {\n\t\t\t${2:field}: frm.doc.${3:other_field},\n\t\t},\n\t};\n});',
                    'frm.set_query()', 'Add filter to a Link field'),
                s('frm.add_custom_button',
                    'frm.add_custom_button(__("${1:Button Label}"), function() {\n\t${0}\n});',
                    'frm.add_custom_button()', 'Add action button to form toolbar'),
                s('frm.add_custom_button-group',
                    'frm.add_custom_button(__("${1:Action}"), function() {\n\t${0}\n}, __("${2:Group}"));',
                    'frm.add_custom_button() grouped', 'Add button inside a dropdown group'),
                s('frm.set_df_property',
                    'frm.set_df_property("${1:fieldname}", "${2:reqd|hidden|read_only}", ${3:1});',
                    'frm.set_df_property()', 'Set any field property at runtime'),
                s('frm.toggle_reqd',
                    'frm.toggle_reqd("${1:fieldname}", ${2:true});',
                    'frm.toggle_reqd()', 'Toggle mandatory on a field'),
                s('frm.toggle_display',
                    'frm.toggle_display(["${1:fieldname}"], ${2:true});',
                    'frm.toggle_display()', 'Show or hide fields'),
                s('frm.toggle_enable',
                    'frm.toggle_enable("${1:fieldname}", ${2:true});',
                    'frm.toggle_enable()', 'Enable or disable a field'),
                s('frm.trigger',
                    'frm.trigger("${1:fieldname}");',
                    'frm.trigger()', 'Manually fire a field change event'),
                s('frm.save',
                    'frm.save("${1:Save|Submit|Cancel|Update}", null, null, null, function() {\n\t${0}\n});',
                    'frm.save()', 'Save the form programmatically'),
                s('frm.reload_doc',
                    'frm.reload_doc();',
                    'frm.reload_doc()', 'Reload form from server'),

                // ── Child table ──
                s('frm.add_child',
                    'const row = frappe.model.add_child(frm.doc, "${1:table_fieldname}");\nrow.${2:field} = ${3:value};\nfrm.refresh_field("${1:table_fieldname}");',
                    'frm.add_child()', 'Add a row to a child table'),
                s('frappe.model.set_value',
                    'frappe.model.set_value(frm.doctype, frm.docname, "${1:field}", ${2:value});',
                    'frappe.model.set_value()', 'Set value in local model cache'),

                // ── Dialogs ──
                s('frappe.confirm',
                    'frappe.confirm(\n\t__("${1:Are you sure?}"),\n\tfunction() {\n\t\t${0}\n\t}\n);',
                    'frappe.confirm()', 'Show a Yes/No confirmation dialog'),
                s('frappe.prompt',
                    'frappe.prompt(\n\t[\n\t\t{ label: __("${1:Label}"), fieldname: "${2:field}", fieldtype: "${3:Data}", reqd: 1 },\n\t],\n\tfunction(values) {\n\t\t${0}\n\t},\n\t__("${4:Title}"),\n\t__("${5:Submit}")\n);',
                    'frappe.prompt()', 'Show a form prompt dialog'),
                s('frappe.msgprint',
                    'frappe.msgprint({\n\ttitle: __("${1:Notice}"),\n\tindicator: "${2:blue}",\n\tmessage: __("${3:Message}"),\n});',
                    'frappe.msgprint()', 'Show a styled message dialog'),
                s('frappe.show_alert',
                    'frappe.show_alert({ message: __("${1:Done}"), indicator: "${2:green}" }, ${3:3});',
                    'frappe.show_alert()', 'Show brief auto-dismissing notification'),
                s('new-dialog',
                    'const d = new frappe.ui.Dialog({\n\ttitle: __("${1:Title}"),\n\tfields: [\n\t\t{ label: __("${2:Label}"), fieldname: "${3:field}", fieldtype: "${4:Data}", reqd: 1 },\n\t],\n\tprimary_action_label: __("${5:Submit}"),\n\tprimary_action(values) {\n\t\t${0}\n\t\td.hide();\n\t},\n});\nd.show();',
                    'new frappe.ui.Dialog()', 'Create and show a custom dialog'),

                // ── List/Report view ──
                s('frappe.listview_settings',
                    'frappe.listview_settings["${1:DocType}"] = {\n\tformatters: {\n\t\t${2:fieldname}(value, df, doc) {\n\t\t\treturn ${0:value};\n\t\t},\n\t},\n\tadd_fields: ["${3:field}"],\n\tget_indicator(doc) {\n\t\treturn [doc.status, {\n\t\t\tDraft: "orange",\n\t\t\tSubmitted: "blue",\n\t\t}[doc.status] || "grey", "status,=," + doc.status];\n\t},\n};',
                    'frappe.listview_settings', 'Customize List View display'),

                // ── Router ──
                s('frappe.set_route',
                    'frappe.set_route("${1:Form}", "${2:DocType}", "${3:name}");',
                    'frappe.set_route()', 'Navigate to a Frappe route'),

                // ── Utils ──
                s('frappe.format',
                    'frappe.format(${1:value}, { fieldtype: "${2:Currency}" })',
                    'frappe.format()', 'Format a value for display'),
                s('frappe.datetime.now_datetime',
                    'frappe.datetime.now_datetime()',
                    'frappe.datetime | now', 'Current datetime string'),
                s('frappe.datetime.add_days',
                    'frappe.datetime.add_days(${1:frappe.datetime.now_datetime()}, ${2:7})',
                    'frappe.datetime | add days', 'Add N days to a date'),
            ];
        }
        return [];
    }

    // ── Local History ───────────────────────────────────────────────────────
    _loadHistory() {
        const tab = this._activeTab();
        if (!tab) {
            $('#dkce-hist-file-info').text('No file open');
            $('#dkce-hist-scroll').html('<div class="dkce-hist-empty">Open a file to view its history</div>');
            return;
        }
        $('#dkce-hist-file-info').text(tab.filePath);
        $('#dkce-hist-scroll').html('<div class="dkce-hist-empty">Loading…</div>');
        frappe.call({
            method: 'frappe_devkit.api.code_editor.get_history',
            args: { app_name: tab.appName, file_path: tab.filePath },
            freeze: false,
            callback: r => this._renderHistory(r.message || [], tab),
        });
    }

    _renderHistory(snaps, tab) {
        const $scroll = $('#dkce-hist-scroll').empty();
        if (!snaps.length) {
            $scroll.html('<div class="dkce-hist-empty">No history yet. Snapshots are saved automatically on each file save.</div>');
            return;
        }
        snaps.forEach(snap => {
            const sizeKb = (snap.size / 1024).toFixed(1);
            const $item = $(`<div class="dkce-hist-item">
                <span class="dkce-hist-ts">${_esc(snap.label)}</span>
                <span class="dkce-hist-size">${sizeKb} KB</span>
                <button class="dkce-hist-btn dkce-hist-btn-preview">Preview</button>
                <button class="dkce-hist-btn dkce-hist-btn-restore">Restore</button>
            </div>`);
            $item.find('.dkce-hist-btn-preview').on('click', e => { e.stopPropagation(); this._previewHistory(tab, snap.id, snap.label); });
            $item.find('.dkce-hist-btn-restore').on('click', e => { e.stopPropagation(); this._restoreHistory(tab, snap.id, snap.label); });
            $item.on('click', () => this._previewHistory(tab, snap.id, snap.label));
            $scroll.append($item);
        });
    }

    _previewHistory(tab, snapshotId, label) {
        // Mark the selected item
        $('#dkce-hist-scroll .dkce-hist-item').removeClass('active');

        frappe.call({
            method: 'frappe_devkit.api.code_editor.get_history_content',
            args: { app_name: tab.appName, file_path: tab.filePath, snapshot_id: snapshotId },
            freeze: false,
            callback: r => {
                if (r.message === undefined || r.message === null) return;
                const snapContent    = r.message;
                const currentContent = this.editor ? this.editor.getValue() : '';
                const lang           = (this.editor && this.editor.getModel())
                    ? this.editor.getModel().getLanguageId()
                    : 'plaintext';

                // Build overlay
                const $overlay = $(`<div class="dkce-hist-diff-overlay">
                    <div class="dkce-hist-diff-dialog">
                        <div class="dkce-hist-diff-header">
                            <span class="dkce-hist-diff-title">${_esc(tab.filePath)} — ${_esc(label)}</span>
                            <div class="dkce-hist-diff-labels">
                                <span><i class="dot-old"></i> snapshot</span>
                                <span><i class="dot-new"></i> current</span>
                            </div>
                        </div>
                        <div class="dkce-hist-diff-editor" id="dkce-hist-diff-editor-mount"></div>
                        <div class="dkce-hist-diff-footer">
                            <button class="dkce-hist-diff-close">Close</button>
                            <button class="dkce-hist-diff-do-restore">Restore this version</button>
                        </div>
                    </div>
                </div>`);

                $('body').append($overlay);

                const monaco     = this.monaco;
                const mountEl    = document.getElementById('dkce-hist-diff-editor-mount');
                const diffEditor = monaco.editor.createDiffEditor(mountEl, {
                    readOnly:              true,
                    renderSideBySide:      true,
                    ignoreTrimWhitespace:  false,
                    theme:                 'vs-dark',
                    fontSize:              13,
                    minimap:               { enabled: false },
                    scrollBeyondLastLine:  false,
                    renderOverviewRuler:   false,
                });
                diffEditor.setModel({
                    original: monaco.editor.createModel(snapContent, lang),
                    modified: monaco.editor.createModel(currentContent, lang),
                });

                // Cleanup helper
                const _close = () => {
                    diffEditor.dispose();
                    $overlay.remove();
                };

                $overlay.find('.dkce-hist-diff-close').on('click', _close);
                $overlay.on('click', e => { if ($(e.target).hasClass('dkce-hist-diff-overlay')) _close(); });
                $(document).one('keydown.dkcediff', e => { if (e.key === 'Escape') { _close(); $(document).off('keydown.dkcediff'); } });

                $overlay.find('.dkce-hist-diff-do-restore').on('click', () => {
                    _close();
                    this._restoreHistory(tab, snapshotId, label);
                });
            },
        });
    }

    _restoreHistory(tab, snapshotId, label) {
        frappe.confirm(
            `Restore to version from <b>${_esc(label)}</b>?<br><small style="color:#888">Your current editor content will be replaced. Unsaved changes will be lost.</small>`,
            () => {
                frappe.call({
                    method: 'frappe_devkit.api.code_editor.get_history_content',
                    args: { app_name: tab.appName, file_path: tab.filePath, snapshot_id: snapshotId },
                    freeze: false,
                    callback: r => {
                        if (r.message !== undefined && r.message !== null) {
                            this.editor.setValue(r.message);
                            this._toast(`Restored from ${label}`, 'success');
                        }
                    },
                });
            }
        );
    }

    // ── Claude AI ───────────────────────────────────────────────────────────
    _checkClaudeConfig() {
        frappe.call({
            method: 'frappe_devkit.api.code_editor.get_claude_status',
            freeze: false,
            callback: r => {
                const info = r.message || {};
                if (info.configured) {
                    // Show chat area
                    $('#dkce-claude-connect-section').hide();
                    $('#dkce-claude-main').css('display', 'flex');
                    // Update connected bar
                    const src = info.source === 'global' ? 'shared key' : info.user_full_name || info.user;
                    $('#dkce-claude-connected-info').text(`${src}  ·  ${info.masked_key}`);
                    if (info.source === 'global') {
                        // Hide disconnect for shared/global key (only admin can remove it)
                        $('#dkce-claude-disconnect').hide();
                    } else {
                        $('#dkce-claude-disconnect').show();
                    }
                } else {
                    // Show connect screen
                    $('#dkce-claude-main').css('display', 'none');
                    $('#dkce-claude-connect-section').css('display', 'flex');
                    // Pre-fill the Frappe user field
                    const user = info.user || frappe.session.user;
                    $('#dkce-claude-frappe-user').val(user);
                    $('#dkce-claude-connect-err').text('');
                }
            },
        });
    }

    _saveClaudeApiKey() {
        const key = $('#dkce-claude-key-inp').val().trim();
        const $btn = $('#dkce-claude-key-save');
        const $err = $('#dkce-claude-connect-err');
        if (!key) { $err.text('Please enter your Anthropic API key'); return; }
        if (!key.startsWith('sk-ant-')) { $err.text('Invalid key — Anthropic keys start with sk-ant-'); return; }

        $btn.prop('disabled', true).text('Connecting…');
        $err.text('');

        frappe.call({
            method: 'frappe_devkit.api.code_editor.set_claude_api_key',
            args: { api_key: key },
            freeze: false,
            callback: r => {
                $btn.prop('disabled', false).text('Connect Account');
                if (r.message && r.message.ok) {
                    $('#dkce-claude-key-inp').val('');
                    this._toast('Account connected — AI completions active', 'success');
                    this._checkClaudeConfig();
                    this._startClaudeCompletion();
                } else {
                    $err.text((r.message && r.message.error) || 'Failed — check key and try again');
                }
            },
        });
    }

    _disconnectClaude() {
        frappe.confirm(
            'Disconnect your Anthropic account from DevKit?<br><small style="color:#888">Your API key will be removed from this Frappe account.</small>',
            () => {
                frappe.call({
                    method: 'frappe_devkit.api.code_editor.clear_claude_api_key',
                    freeze: false,
                    callback: r => {
                        if (r.message && r.message.ok) {
                            this._clearClaudeChat();
                            this._stopClaudeCompletion();
                            this._toast('Account disconnected', 'info');
                            this._checkClaudeConfig();
                        }
                    },
                });
            }
        );
    }

    _clearClaudeChat() {
        $('#dkce-claude-chat').html('<div class="dkce-claude-msg assistant">👋 Hi! I\'m Claude. Ask me anything about your code, or check "Include file" to share the open file as context.</div>');
        this._claudeMsgs = [];
    }

    _sendClaudeMessage(overrideMsg, action) {
        const $inp = $('#dkce-claude-inp');
        const msg = overrideMsg || $inp.val().trim();
        if (!msg) return;

        const tab     = this._activeTab();
        const lang    = tab ? tab.language : '';
        const filePath = tab ? tab.filePath : '';

        // Determine code context: pinned selection > selection checkbox > file checkbox
        let codeCtx = '';
        const useSel = $('#dkce-claude-use-sel').is(':checked');
        const useCtx = $('#dkce-claude-use-ctx').is(':checked');
        if (useSel && this._claudePinnedSel) {
            codeCtx = this._claudePinnedSel;
        } else if (this.editor) {
            const sel = this.editor.getModel()
                ? this.editor.getModel().getValueInRange(this.editor.getSelection())
                : '';
            if (sel && sel.trim()) {
                codeCtx = sel;
            } else if (useCtx) {
                codeCtx = this.editor.getValue();
            }
        }

        if (!this._claudeMsgs) this._claudeMsgs = [];
        this._claudeMsgs.push({ role: 'user', content: msg });

        this._appendClaudeMsg('user', msg);
        if (!overrideMsg) $inp.val('');

        const $thinking = $('<div class="dkce-claude-msg assistant" id="dkce-thinking">⏳ Thinking…</div>');
        $('#dkce-claude-chat').append($thinking);
        this._scrollClaudeChat();

        $('#dkce-claude-send').prop('disabled', true).text('…');
        $('#dkce-claude-status').text('Claude is thinking…');

        frappe.call({
            method: 'frappe_devkit.api.code_editor.claude_chat',
            args: {
                message: msg,
                code_context: codeCtx.slice(0, 12000),
                language: lang,
                file_path: filePath,
                messages: JSON.stringify(this._claudeMsgs.slice(-20)),
                action: action || '',
            },
            freeze: false,
            callback: r => {
                $('#dkce-thinking').remove();
                $('#dkce-claude-send').prop('disabled', false).text('Send ↵');
                $('#dkce-claude-status').text('');
                if (r.message && r.message.ok) {
                    const content = r.message.content;
                    this._claudeMsgs.push({ role: 'assistant', content });
                    this._appendClaudeMsg('assistant', content);
                } else {
                    const err = (r.message && r.message.error) || (r.exc ? 'Server error' : 'Request failed');
                    this._appendClaudeMsg('error-msg', '⚠ ' + err);
                    this._claudeMsgs.pop();
                }
            },
        });
    }

    _sendClaudeAction(action) {
        // Switch to Claude panel first
        this._switchPanel('claude');

        const tab  = this._activeTab();
        const lang = tab ? tab.language : 'code';

        // Prefer selected text, else whole file
        let code = '';
        if (this.editor) {
            const sel = this.editor.getModel()
                ? this.editor.getModel().getValueInRange(this.editor.getSelection())
                : '';
            code = (sel && sel.trim()) ? sel : this.editor.getValue();
        }

        const prompts = {
            explain:  `Explain this ${lang} code clearly. Describe what it does, key logic, and any important patterns:`,
            refactor: `Refactor this ${lang} code for better readability, maintainability, and best practices. Show the improved version with brief explanation of changes:`,
            fix:      `Analyze this ${lang} code for bugs, errors, or issues. Identify each problem and provide the fixed version:`,
            tests:    `Write comprehensive unit tests for this ${lang} code. Cover normal cases, edge cases, and error scenarios:`,
            docs:     `Add clear documentation/comments to this ${lang} code. Include function descriptions, parameters, return values, and inline comments for complex logic:`,
            optimize: `Optimize this ${lang} code for performance and efficiency. Identify bottlenecks and provide an improved version with explanation:`,
            complete: `Complete or extend this ${lang} code. Continue naturally from where it leaves off, following the same patterns and style:`,
        };

        const prompt = (prompts[action] || `Help with this ${lang} code:`) + '\n\n```' + lang + '\n' + code.slice(0, 12000) + '\n```';

        // Pin the code as context so follow-ups use it
        this._claudePinnedSel = code;
        $('#dkce-claude-sel-info').text(`📌 ${action}: ${code.split('\n').length} lines`);
        $('#dkce-claude-sel-badge').addClass('visible');
        $('#dkce-claude-use-sel').prop('checked', true);

        this._sendClaudeMessage(prompt, action);
    }

    _insertCodeAtCursor(code) {
        if (!this.editor) { this._toast('No file open', 'warn'); return; }
        const pos = this.editor.getPosition();
        this.editor.executeEdits('claude-insert', [{
            range: new this.monaco.Range(pos.lineNumber, pos.column, pos.lineNumber, pos.column),
            text: code,
            forceMoveMarkers: true,
        }]);
        this.editor.focus();
        this._toast('Code inserted at cursor', 'success');
    }

    _appendClaudeMsg(role, content) {
        const $msg = $('<div class="dkce-claude-msg"></div>').addClass(role);
        $msg.html(this._renderClaudeContent(content));
        $('#dkce-claude-chat').append($msg);
        this._scrollClaudeChat();
    }

    _renderClaudeContent(text) {
        // Process fenced code blocks — store raw code for Insert/Copy buttons
        const blocks  = [];
        const rawCode = [];
        let html = text.replace(/```(\w*)\n?([\s\S]*?)```/g, (_, lang, code) => {
            const idx     = blocks.length;
            const trimmed = code.replace(/\n$/, '');
            rawCode.push(trimmed);
            blocks.push(
                `<div class="dkce-code-block-wrap" data-block="${idx}">` +
                `<button class="dkce-copy-btn" data-idx="${idx}">Copy</button>` +
                `<button class="dkce-insert-btn" data-idx="${idx}">Insert ↵</button>` +
                `<pre><code>${_esc(trimmed)}</code></pre>` +
                `</div>`
            );
            return `\x00BLOCK${idx}\x00`;
        });
        html = _esc(html);
        blocks.forEach((b, i) => { html = html.replace(`\x00BLOCK${i}\x00`, b); });
        html = html.replace(/`([^`]+)`/g, (_, c) => `<code>${_esc(c)}</code>`);
        html = html.replace(/\*\*([^*\n]+)\*\*/g, '<strong>$1</strong>');
        html = html.replace(/\n/g, '<br>');
        // Attach events after render via a timeout (element not in DOM yet)
        setTimeout(() => {
            rawCode.forEach((code, idx) => {
                $(`[data-idx="${idx}"].dkce-insert-btn`).off('click').on('click', () => this._insertCodeAtCursor(code));
                $(`[data-idx="${idx}"].dkce-copy-btn`).off('click').on('click', e => {
                    navigator.clipboard.writeText(code).then(() => {
                        const $btn = $(e.currentTarget);
                        $btn.text('✓');
                        setTimeout(() => $btn.text('Copy'), 1200);
                    });
                });
            });
        }, 0);
        return html;
    }

    _scrollClaudeChat() {
        const el = document.getElementById('dkce-claude-chat');
        if (el) requestAnimationFrame(() => { el.scrollTop = el.scrollHeight; });
    }

    // ── Claude Inline Completions ───────────────────────────────────────────
    // Ghost-text widget approach: debounce on typing → call claude_complete →
    // show suggestion at cursor. Tab accepts, Esc dismisses.

    _startClaudeCompletion() {
        if (!this.editor || !this.monaco) return;
        // Check Claude is connected before starting
        frappe.call({
            method: 'frappe_devkit.api.code_editor.get_claude_status',
            freeze: false,
            callback: r => {
                if (r.message && r.message.configured) {
                    this._setupClaudeCompletionListeners();
                    this._updateClaudeCompletionBadge(true);
                }
            },
        });
    }

    _stopClaudeCompletion() {
        ['_ccL1', '_ccL2', '_ccL3'].forEach(k => {
            if (this[k]) { try { this[k].dispose(); } catch(e){} this[k] = null; }
        });
        clearTimeout(this._ccTimer);
        this._clearClaudeGhost();
        this._updateClaudeCompletionBadge(false);
    }

    _updateClaudeCompletionBadge(active) {
        let $badge = $('#dkce-sb-ai-badge');
        if (active) {
            if (!$badge.length) {
                $badge = $('<div id="dkce-sb-ai-badge" class="dkce-sb-item" title="Claude AI completions active" style="color:#73c991;font-weight:600;">✦ AI</div>');
                $('#dkce-sb-save').before($badge);
            }
        } else {
            $badge.remove();
        }
    }

    _setupClaudeCompletionListeners() {
        if (this._ccL1) return; // already set up

        const editor = this.editor;
        const monaco = this.monaco;
        const self   = this;

        // Ghost widget DOM node
        const _dom = document.createElement('span');
        _dom.style.cssText = 'color:rgba(160,160,160,0.55);font-style:italic;pointer-events:none;white-space:pre;font-family:inherit;font-size:inherit;line-height:inherit;display:inline-block;vertical-align:top;';

        let _ghostText = '';
        let _widgetAdded = false;

        const _widget = {
            getId:      () => 'claude.inline.widget',
            getDomNode: () => _dom,
            getPosition: () => {
                const pos = editor.getPosition();
                if (!pos) return null;
                return {
                    position: { lineNumber: pos.lineNumber, column: pos.column },
                    preference: [monaco.editor.ContentWidgetPositionPreference.EXACT],
                };
            },
        };

        const _showGhost = (text) => {
            _ghostText = text;
            const lines   = text.split('\n');
            const display = lines[0] + (lines.length > 1 ? '  ↵…' : '');
            _dom.textContent = display;
            if (!_widgetAdded) {
                editor.addContentWidget(_widget);
                _widgetAdded = true;
            } else {
                editor.layoutContentWidget(_widget);
            }
        };

        const _clearGhost = () => {
            _ghostText = '';
            if (_widgetAdded) {
                editor.removeContentWidget(_widget);
                _widgetAdded = false;
            }
        };
        this._clearClaudeGhost = _clearGhost;

        const _fetch = () => {
            const model = editor.getModel();
            const pos   = editor.getPosition();
            if (!model || !pos) return;
            const full   = model.getValue();
            const offset = model.getOffsetAt(pos);
            const prefix = full.slice(0, offset);
            const suffix = full.slice(offset);
            if (prefix.trim().length < 4) return;

            const snapLn = pos.lineNumber, snapCol = pos.column;
            frappe.call({
                method: 'frappe_devkit.api.code_editor.claude_complete',
                args: {
                    prefix:   prefix.slice(-3000),
                    suffix:   suffix.slice(0, 500),
                    language: model.getLanguageId(),
                },
                freeze: false,
                callback: r => {
                    const c = r.message && r.message.ok && r.message.completion;
                    if (!c) return;
                    const cur = editor.getPosition();
                    if (!cur || cur.lineNumber !== snapLn || cur.column !== snapCol) return;
                    _showGhost(c);
                },
            });
        };

        // Typing → clear ghost, schedule fetch
        this._ccL1 = editor.onDidChangeModelContent(() => {
            _clearGhost();
            clearTimeout(self._ccTimer);
            self._ccTimer = setTimeout(_fetch, 700);
        });

        // Cursor move → clear ghost
        this._ccL2 = editor.onDidChangeCursorPosition(() => {
            if (_ghostText) _clearGhost();
        });

        // Tab → accept, Esc → dismiss
        this._ccL3 = editor.onKeyDown(e => {
            if (!_ghostText) return;
            if (e.keyCode === monaco.KeyCode.Tab) {
                e.preventDefault();
                e.stopPropagation();
                const pos  = editor.getPosition();
                const text = _ghostText;
                _clearGhost();
                editor.executeEdits('claude-inline', [{
                    range: new monaco.Range(pos.lineNumber, pos.column, pos.lineNumber, pos.column),
                    text,
                    forceMoveMarkers: true,
                }]);
                const lines  = text.split('\n');
                const newLn  = pos.lineNumber + lines.length - 1;
                const newCol = lines.length === 1 ? pos.column + text.length : lines[lines.length - 1].length + 1;
                editor.setPosition({ lineNumber: newLn, column: newCol });
                editor.focus();
            } else if (e.keyCode === monaco.KeyCode.Escape) {
                _clearGhost();
            }
        });

        // Alt+\ — manual trigger
        editor.addCommand(
            this.monaco.KeyMod.Alt | this.monaco.KeyCode.Backslash,
            () => { _clearGhost(); clearTimeout(self._ccTimer); _fetch(); }
        );
    }

    // ── Enhanced Git Operations ─────────────────────────────────────────────
    _gitStageFile(filePath) {
        frappe.call({
            method: 'frappe_devkit.api.code_editor.git_stage_file',
            args: { app_name: this.state.currentApp, file_path: filePath },
            freeze: false,
            callback: r => { if (r.message && r.message.ok) { this._toast(`Staged: ${filePath}`, 'success'); this._refreshGit(); } },
        });
    }

    _gitUnstageFile(filePath) {
        frappe.call({
            method: 'frappe_devkit.api.code_editor.git_unstage_file',
            args: { app_name: this.state.currentApp, file_path: filePath },
            freeze: false,
            callback: r => { if (r.message && r.message.ok) { this._toast(`Unstaged: ${filePath}`, 'info'); this._refreshGit(); } },
        });
    }

    _gitDiscardFile(filePath) {
        frappe.confirm(
            `Discard all changes in <b>${_esc(filePath)}</b>?<br><small style="color:#f44747">This cannot be undone.</small>`,
            () => {
                frappe.call({
                    method: 'frappe_devkit.api.code_editor.git_discard_file',
                    args: { app_name: this.state.currentApp, file_path: filePath },
                    freeze: false,
                    callback: r => {
                        if (r.message && r.message.ok) {
                            this._toast(`Discarded: ${filePath}`, 'warn');
                            this._refreshGit();
                            // Reload tab if open
                            const tab = this.state.tabs.find(t => t.filePath === filePath);
                            if (tab) {
                                frappe.call({
                                    method: 'frappe_devkit.api.code_editor.read_file',
                                    args: { app_name: this.state.currentApp, file_path: filePath },
                                    freeze: false,
                                    callback: r2 => {
                                        if (r2.message) {
                                            tab.model.setValue(r2.message.content || '');
                                            tab.origContent = r2.message.content || '';
                                            tab.isModified = false;
                                            $(`#dkce-tab-${tab.id}`).removeClass('modified');
                                            this._updateSaveStatus(false);
                                        }
                                    },
                                });
                            }
                        }
                    },
                });
            }
        );
    }

    _gitCommit() {
        if (!this.state.currentApp) { this._toast('Select an app first', 'warn'); return; }
        frappe.prompt([
            { label: 'Commit message', fieldname: 'msg', fieldtype: 'Data', reqd: 1,
              placeholder: 'feat: describe your change' },
            { label: 'Stage all changes (git add -A)', fieldname: 'stage_all', fieldtype: 'Check', default: 1 },
        ], ({ msg, stage_all }) => {
            frappe.call({
                method: 'frappe_devkit.api.code_editor.git_commit',
                args: { app_name: this.state.currentApp, message: msg, stage_all: stage_all ? 1 : 0 },
                callback: r => {
                    if (r.message && r.message.ok) {
                        this._toast('Committed: ' + msg, 'success');
                        this._refreshGit();
                    } else {
                        this._toast(r.exc ? 'Commit failed — check console' : 'Commit failed', 'error');
                    }
                },
            });
        }, 'Git Commit', 'Commit');
    }

    _gitPush() {
        if (!this.state.currentApp) { this._toast('Select an app first', 'warn'); return; }
        frappe.prompt([
            { label: 'Remote', fieldname: 'remote', fieldtype: 'Data', default: 'origin' },
            { label: 'Branch (blank = current branch)', fieldname: 'branch', fieldtype: 'Data', default: '' },
        ], ({ remote, branch }) => {
            this._toast('Pushing…', 'info');
            frappe.call({
                method: 'frappe_devkit.api.code_editor.git_push',
                args: { app_name: this.state.currentApp, remote: remote || 'origin', branch: branch || '' },
                callback: r => {
                    if (r.message && r.message.ok) {
                        this._toast('Pushed successfully', 'success');
                        this._refreshGit();
                    } else {
                        this._toast('Push failed — check server logs', 'error');
                    }
                },
            });
        }, 'Git Push', 'Push');
    }

    _gitPull() {
        if (!this.state.currentApp) { this._toast('Select an app first', 'warn'); return; }
        frappe.prompt([
            { label: 'Remote', fieldname: 'remote', fieldtype: 'Data', default: 'origin' },
            { label: 'Branch (blank = current branch)', fieldname: 'branch', fieldtype: 'Data', default: '' },
        ], ({ remote, branch }) => {
            this._toast('Pulling…', 'info');
            frappe.call({
                method: 'frappe_devkit.api.code_editor.git_pull',
                args: { app_name: this.state.currentApp, remote: remote || 'origin', branch: branch || '' },
                callback: r => {
                    if (r.message && r.message.ok) {
                        this._toast('Pull complete', 'success');
                        this._refreshGit();
                    } else {
                        this._toast('Pull failed — check server logs', 'error');
                    }
                },
            });
        }, 'Git Pull', 'Pull');
    }

    _gitBranches() {
        if (!this.state.currentApp) { this._toast('Select an app first', 'warn'); return; }
        frappe.call({
            method: 'frappe_devkit.api.code_editor.git_branches',
            args: { app_name: this.state.currentApp },
            callback: r => this._showBranchDialog(r.message || []),
        });
    }

    _showBranchDialog(branches) {
        const branchRows = branches.map(b => `
            <div class="dkce-git-file" style="${b.current ? 'background:#094771;' : ''}" data-branch="${_esc(b.name)}">
                <span class="dkce-git-code" style="color:${b.current ? '#73c991' : '#888'};">${b.current ? '✓' : '○'}</span>
                <span class="dkce-git-fname">${_esc(b.name)}</span>
                ${!b.current ? `<button class="dkce-git-file-act stage dkce-checkout-btn" style="font-size:11px;padding:2px 8px;">Checkout</button>` : ''}
            </div>
        `).join('');

        const $ov = $(`<div class="dkce-overlay">
            <div class="dkce-dialog" style="width:420px;">
                <button class="dkce-dialog-close">×</button>
                <h3>⎇ Branches</h3>
                <div style="max-height:280px;overflow-y:auto;margin-bottom:12px;border:1px solid #333;border-radius:4px;">${branchRows || '<div style="padding:12px;color:#888">No branches found</div>'}</div>
                <div style="display:flex;gap:8px;margin-bottom:12px;">
                    <input class="dkce-setting-ctrl" id="dkce-new-branch-inp" placeholder="New branch name…" style="flex:1;">
                    <button class="dkce-dialog-btn primary" id="dkce-new-branch-btn">+ Create</button>
                </div>
                <div class="dkce-dialog-footer"><button class="dkce-dialog-btn secondary dkce-close-dialog">Close</button></div>
            </div>
        </div>`).appendTo('body');

        $ov.on('click', '.dkce-checkout-btn', e => {
            const branch = $(e.target).closest('[data-branch]').data('branch');
            frappe.call({
                method: 'frappe_devkit.api.code_editor.git_checkout',
                args: { app_name: this.state.currentApp, branch, create: 0 },
                callback: r => {
                    if (r.message && r.message.ok) {
                        this._toast(`Checked out: ${branch}`, 'success');
                        this._refreshGit();
                        $ov.remove();
                    } else { this._toast('Checkout failed', 'error'); }
                },
            });
        });
        $('#dkce-new-branch-btn').on('click', () => {
            const name = $('#dkce-new-branch-inp').val().trim();
            if (!name) return;
            frappe.call({
                method: 'frappe_devkit.api.code_editor.git_checkout',
                args: { app_name: this.state.currentApp, branch: name, create: 1 },
                callback: r => {
                    if (r.message && r.message.ok) {
                        this._toast(`Created & checked out: ${name}`, 'success');
                        this._refreshGit();
                        $ov.remove();
                    } else { this._toast('Create branch failed', 'error'); }
                },
            });
        });
        $ov.on('click', '.dkce-close-dialog, .dkce-dialog-close', () => $ov.remove());
        $ov.on('click', e => { if (e.target === $ov[0]) $ov.remove(); });
    }

    _gitLog() {
        if (!this.state.currentApp) { this._toast('Select an app first', 'warn'); return; }
        frappe.call({
            method: 'frappe_devkit.api.code_editor.git_log',
            args: { app_name: this.state.currentApp, limit: 30 },
            callback: r => this._showGitLogDialog(r.message || []),
        });
    }

    _showGitLogDialog(commits) {
        const rows = commits.map(c => `
            <div class="dkce-gitlog-item">
                <div style="display:flex;gap:8px;align-items:center;">
                    <span class="dkce-gitlog-hash">${_esc(c.hash)}</span>
                    <span class="dkce-gitlog-meta">${_esc(c.author)} · ${_esc(c.time)}</span>
                </div>
                <div class="dkce-gitlog-msg">${_esc(c.message)}</div>
            </div>
        `).join('');

        const $ov = $(`<div class="dkce-overlay">
            <div class="dkce-dialog" style="width:540px;max-height:75vh;">
                <button class="dkce-dialog-close">×</button>
                <h3>📋 Git Log</h3>
                <div style="overflow-y:auto;max-height:55vh;margin:0 -4px 0;">${rows || '<div style="padding:12px;color:#888">No commits found</div>'}</div>
                <div class="dkce-dialog-footer"><button class="dkce-dialog-btn secondary dkce-close-dialog">Close</button></div>
            </div>
        </div>`).appendTo('body');

        $ov.on('click', '.dkce-close-dialog, .dkce-dialog-close', () => $ov.remove());
        $ov.on('click', e => { if (e.target === $ov[0]) $ov.remove(); });
    }

    _gitStash() {
        if (!this.state.currentApp) { this._toast('Select an app first', 'warn'); return; }
        frappe.prompt([
            { label: 'Action', fieldname: 'action', fieldtype: 'Select',
              options: 'save\npop\nlist', default: 'save' },
            { label: 'Message (for save)', fieldname: 'message', fieldtype: 'Data', default: '' },
        ], ({ action, message }) => {
            frappe.call({
                method: 'frappe_devkit.api.code_editor.git_stash',
                args: { app_name: this.state.currentApp, action, message: message || '' },
                callback: r => {
                    if (r.message && r.message.ok) {
                        const out = r.message.output;
                        if (action === 'list') {
                            frappe.msgprint({ title: 'Stash List', message: `<pre style="font-size:12px">${_esc(out || 'No stashes')}</pre>` });
                        } else {
                            this._toast(`git stash ${action}: ${out || 'done'}`, 'success');
                            this._refreshGit();
                        }
                    } else { this._toast(`Stash ${action} failed`, 'error'); }
                },
            });
        }, 'Git Stash', 'Run');
    }

    _gitStageAll() {
        if (!this.state.currentApp) { this._toast('Select an app first', 'warn'); return; }
        frappe.call({
            method: 'frappe_devkit.api.code_editor.git_stage_all',
            args: { app_name: this.state.currentApp },
            freeze: false,
            callback: r => {
                if (r.message && r.message.ok) { this._toast('All changes staged', 'success'); this._refreshGit(); }
                else { this._toast('Stage all failed', 'error'); }
            },
        });
    }

    _gitUnstageAll() {
        if (!this.state.currentApp) { this._toast('Select an app first', 'warn'); return; }
        frappe.call({
            method: 'frappe_devkit.api.code_editor.git_unstage_all',
            args: { app_name: this.state.currentApp },
            freeze: false,
            callback: r => {
                if (r.message && r.message.ok) { this._toast('All changes unstaged', 'info'); this._refreshGit(); }
                else { this._toast('Unstage all failed', 'error'); }
            },
        });
    }

    _gitDiscardAll() {
        if (!this.state.currentApp) { this._toast('Select an app first', 'warn'); return; }
        frappe.confirm(
            `<b>Discard ALL unstaged changes?</b><br><small style="color:#f44747">This cannot be undone. Untracked files are kept.</small>`,
            () => {
                frappe.call({
                    method: 'frappe_devkit.api.code_editor.git_discard_all',
                    args: { app_name: this.state.currentApp },
                    freeze: false,
                    callback: r => {
                        if (r.message && r.message.ok) {
                            this._toast('All unstaged changes discarded', 'warn');
                            this._refreshGit();
                        } else { this._toast('Discard all failed', 'error'); }
                    },
                });
            }
        );
    }

    _gitFetch() {
        if (!this.state.currentApp) { this._toast('Select an app first', 'warn'); return; }
        frappe.prompt([
            { label: 'Remote', fieldname: 'remote', fieldtype: 'Data', default: 'origin' },
        ], ({ remote }) => {
            this._toast('Fetching…', 'info');
            frappe.call({
                method: 'frappe_devkit.api.code_editor.git_fetch',
                args: { app_name: this.state.currentApp, remote: remote || 'origin' },
                callback: r => {
                    if (r.message && r.message.ok) {
                        this._toast(`Fetch complete: ${r.message.output || 'up to date'}`, 'success');
                        this._refreshGit();
                    } else { this._toast('Fetch failed — check server logs', 'error'); }
                },
            });
        }, 'Git Fetch', 'Fetch');
    }

    _gitMerge() {
        if (!this.state.currentApp) { this._toast('Select an app first', 'warn'); return; }
        frappe.call({
            method: 'frappe_devkit.api.code_editor.git_branches',
            args: { app_name: this.state.currentApp },
            callback: r => {
                const branches = (r.message || []).filter(b => !b.current);
                const opts = branches.map(b => b.name).join('\n');
                frappe.prompt([
                    { label: 'Branch to merge into current', fieldname: 'branch', fieldtype: 'Select', options: opts, reqd: 1 },
                    { label: 'No fast-forward (--no-ff)', fieldname: 'no_ff', fieldtype: 'Check', default: 0 },
                ], ({ branch, no_ff }) => {
                    this._toast(`Merging ${branch}…`, 'info');
                    frappe.call({
                        method: 'frappe_devkit.api.code_editor.git_merge',
                        args: { app_name: this.state.currentApp, branch, no_ff: no_ff ? 1 : 0 },
                        callback: r2 => {
                            if (r2.message && r2.message.ok) {
                                frappe.msgprint({ title: 'Merge Complete', message: `<pre style="font-size:12px">${_esc(r2.message.output || 'done')}</pre>` });
                                this._refreshGit();
                            } else { this._toast('Merge failed — check server logs', 'error'); }
                        },
                    });
                }, 'Git Merge', 'Merge');
            },
        });
    }

    _gitDiff() {
        if (!this.state.currentApp) { this._toast('Select an app first', 'warn'); return; }
        const filePath = this.state.activeTab ? this.state.tabs.find(t => t.id === this.state.activeTab)?.filePath : '';
        frappe.prompt([
            { label: 'File path (blank = all changes)', fieldname: 'file_path', fieldtype: 'Data', default: filePath || '' },
            { label: 'Staged only', fieldname: 'staged', fieldtype: 'Check', default: 0 },
        ], ({ file_path, staged }) => {
            frappe.call({
                method: 'frappe_devkit.api.code_editor.git_diff',
                args: { app_name: this.state.currentApp, file_path: file_path || '', staged: staged ? 1 : 0 },
                callback: r => {
                    if (r.message) {
                        const out = r.message.output || '(no diff)';
                        const $ov = $(`<div class="dkce-overlay">
                            <div class="dkce-dialog" style="width:700px;max-height:80vh;">
                                <button class="dkce-dialog-close">×</button>
                                <h3>≠ Git Diff${file_path ? ': ' + _esc(file_path) : ''}</h3>
                                <pre style="font-size:11px;overflow:auto;max-height:60vh;background:#0d0d0d;padding:10px;border-radius:4px;color:#ccc;white-space:pre;font-family:'Cascadia Code','Consolas',monospace;">${_esc(out)}</pre>
                                <div class="dkce-dialog-footer"><button class="dkce-dialog-btn secondary dkce-close-dialog">Close</button></div>
                            </div>
                        </div>`).appendTo('body');
                        $ov.on('click', '.dkce-close-dialog, .dkce-dialog-close', () => $ov.remove());
                        $ov.on('click', e => { if (e.target === $ov[0]) $ov.remove(); });
                    }
                },
            });
        }, 'Git Diff', 'Show Diff');
    }

    _gitReset() {
        if (!this.state.currentApp) { this._toast('Select an app first', 'warn'); return; }
        frappe.prompt([
            { label: 'Mode', fieldname: 'mode', fieldtype: 'Select', options: 'soft\nmixed\nhard', default: 'mixed',
              description: 'soft=keep staged, mixed=unstage all, hard=discard all changes' },
            { label: 'Target (commit hash, HEAD~1, etc.)', fieldname: 'target', fieldtype: 'Data', default: 'HEAD~1' },
        ], ({ mode, target }) => {
            const msg = mode === 'hard'
                ? `<b>Hard reset to ${_esc(target)}?</b><br><small style="color:#f44747">All uncommitted changes will be lost.</small>`
                : `Reset (${mode}) to ${_esc(target)}?`;
            frappe.confirm(msg, () => {
                frappe.call({
                    method: 'frappe_devkit.api.code_editor.git_reset',
                    args: { app_name: this.state.currentApp, mode, target: target || 'HEAD~1' },
                    callback: r => {
                        if (r.message && r.message.ok) {
                            this._toast(`Reset --${mode} to ${target} done`, mode === 'hard' ? 'warn' : 'success');
                            this._refreshGit();
                        } else { this._toast('Reset failed — check server logs', 'error'); }
                    },
                });
            });
        }, 'Git Reset', 'Reset');
    }

    _gitTag() {
        if (!this.state.currentApp) { this._toast('Select an app first', 'warn'); return; }
        frappe.prompt([
            { label: 'Action', fieldname: 'action', fieldtype: 'Select', options: 'list\ncreate\ndelete', default: 'list' },
            { label: 'Tag name (for create/delete)', fieldname: 'name', fieldtype: 'Data', default: '' },
            { label: 'Message (annotated tag, optional)', fieldname: 'message', fieldtype: 'Data', default: '' },
        ], ({ action, name, message }) => {
            frappe.call({
                method: 'frappe_devkit.api.code_editor.git_tag',
                args: { app_name: this.state.currentApp, action, name: name || '', message: message || '' },
                callback: r => {
                    if (r.message && r.message.ok) {
                        if (action === 'list') {
                            frappe.msgprint({ title: 'Tags', message: `<pre style="font-size:12px">${_esc(r.message.output || 'No tags')}</pre>` });
                        } else {
                            this._toast(`Tag ${action}: ${name || 'done'}`, 'success');
                            this._refreshGit();
                        }
                    } else { this._toast(`Tag ${action} failed`, 'error'); }
                },
            });
        }, 'Git Tag', 'Run');
    }

    // ── Terminal ────────────────────────────────────────────────────────────

    _toggleTerminal(forceState) {
        const t = this.state.terminal;
        const visible = forceState !== undefined ? forceState : !t.visible;
        t.visible = visible;
        $('#dkce-terminal-panel').toggleClass('visible', visible);
        $('#dkce-btn-terminal').toggleClass('active', visible);
        if (visible) {
            document.getElementById('dkce-root').style.setProperty('--dkce-term-h', t.height + 'px');
            if (!this._termInited) { this._termInit(); this._termInited = true; }
            setTimeout(() => {
                $('#dkce-term-input').focus();
                if (this.editor) this.editor.layout();
            }, 40);
        } else {
            this._termHideCompletions();
            setTimeout(() => { if (this.editor) this.editor.layout(); }, 30);
        }
    }

    _termInit() {
        this._termPrint(
            'Terminal  —  Tab: autocomplete  |  ↑↓: history  |  Ctrl+L: clear  |  Ctrl+C: cancel',
            'info-row');
    }

    _termUpdatePrompt() {
        const cwd = this.state.terminal.cwd;
        const label = cwd ? `bench/${cwd}` : 'bench';
        $('#dkce-term-prompt-label').text(label);
    }

    // ── Output rendering ────────────────────────────────────────────────────

    /**
     * Write a line (or multi-line string) to the output area.
     * Supports ANSI SGR escape codes → inline HTML colors.
     * @param {string} text
     * @param {'prompt-row'|'stderr-row'|'info-row'|''} cls  extra CSS class for the row
     */
    _termPrint(text, cls = '') {
        const $out = $('#dkce-terminal-output');
        if (!$out.length) return;
        const lines = String(text).split('\n');
        // Drop trailing empty line from output that ends with \n
        if (lines.length > 1 && lines[lines.length - 1] === '') lines.pop();
        lines.forEach(line => {
            $('<div class="dkce-term-row"></div>')
                .addClass(cls)
                .html(this._ansiToHtml(line))
                .appendTo($out);
        });
        const el = $out[0];
        el.scrollTop = el.scrollHeight;
    }

    _termClear() {
        $('#dkce-terminal-output').empty();
        setTimeout(() => $('#dkce-term-input').focus(), 10);
    }

    /** Convert ANSI SGR sequences to inline-styled HTML spans. */
    _ansiToHtml(raw) {
        if (!raw) return '';
        const FG = {
            30:'#7f8c8d', 31:'#e06c75', 32:'#98c379', 33:'#e5c07b',
            34:'#61afef', 35:'#c678dd', 36:'#56b6c2', 37:'#abb2bf',
            90:'#5c6370', 91:'#e06c75', 92:'#98c379', 93:'#e5c07b',
            94:'#61afef', 95:'#c678dd', 96:'#56b6c2', 97:'#ffffff',
        };
        const BG = {
            40:'#1e2127', 41:'#be5046', 42:'#98c379', 43:'#d19a66',
            44:'#61afef', 45:'#c678dd', 46:'#56b6c2', 47:'#abb2bf',
        };
        // Strip non-SGR escape sequences (cursor movement, etc.)
        const cleaned = raw
            .replace(/\x1b\][\s\S]*?(?:\x07|\x1b\\)/g, '')   // OSC
            .replace(/\x1b\[[0-9;]*[A-HJKSTf]/g, '')          // cursor movement
            .replace(/\x1b[()][AB012]/g, '');                  // charset

        const parts = cleaned.split(/(\x1b\[[0-9;]*m)/);
        let html = '';
        let bold = false, italic = false, underline = false;
        let fg = null, bg = null;

        const wrap = txt => {
            if (!txt) return '';
            const styles = [];
            if (fg)        styles.push(`color:${fg}`);
            if (bg)        styles.push(`background:${bg}`);
            if (bold)      styles.push('font-weight:700');
            if (italic)    styles.push('font-style:italic');
            if (underline) styles.push('text-decoration:underline');
            const esc = _esc(txt);
            return styles.length ? `<span style="${styles.join(';')}">${esc}</span>` : esc;
        };

        for (let i = 0; i < parts.length; i++) {
            if (i % 2 === 0) {
                html += wrap(parts[i]);
            } else {
                const inner = parts[i].slice(2, -1);
                const codes = (inner === '' ? ['0'] : inner.split(';')).map(Number);
                for (const c of codes) {
                    if (c === 0)  { bold = italic = underline = false; fg = bg = null; }
                    else if (c === 1)  bold = true;
                    else if (c === 3)  italic = true;
                    else if (c === 4)  underline = true;
                    else if (c === 22) bold = false;
                    else if (c === 23) italic = false;
                    else if (c === 24) underline = false;
                    else if (FG[c])  fg = FG[c];
                    else if (c === 39) fg = null;
                    else if (BG[c])  bg = BG[c];
                    else if (c === 49) bg = null;
                }
            }
        }
        return html;
    }

    // ── Keyboard handler ────────────────────────────────────────────────────

    _termOnKeydown(e) {
        const t = this.state.terminal;
        const $popup = $('#dkce-term-comp-popup');
        const popupOpen = $popup.hasClass('open');

        if (e.key === 'Enter') {
            e.preventDefault();
            if (popupOpen) {
                const $sel = $popup.find('.sel');
                if ($sel.length) this._termApplyCompletion($sel.data('completion'));
                else this._termHideCompletions();
                return;
            }
            const cmd = $('#dkce-term-input').val();
            if (!cmd.trim()) return;
            this._termSubmit(cmd);

        } else if (e.key === 'Tab') {
            e.preventDefault();
            if (popupOpen) {
                this._termCycleCompletion(1);
            } else {
                this._termDoComplete();
            }

        } else if (e.key === 'Escape') {
            e.preventDefault();
            this._termHideCompletions();

        } else if (e.key === 'ArrowUp') {
            if (popupOpen) { e.preventDefault(); this._termCycleCompletion(-1); return; }
            e.preventDefault();
            if (t.historyIdx < t.history.length - 1) {
                t.historyIdx++;
                $('#dkce-term-input').val(t.history[t.historyIdx]);
            }

        } else if (e.key === 'ArrowDown') {
            if (popupOpen) { e.preventDefault(); this._termCycleCompletion(1); return; }
            e.preventDefault();
            if (t.historyIdx > 0) {
                t.historyIdx--;
                $('#dkce-term-input').val(t.history[t.historyIdx]);
            } else {
                t.historyIdx = -1;
                $('#dkce-term-input').val('');
            }

        } else if (e.ctrlKey && e.key === 'l') {
            e.preventDefault();
            this._termClear();

        } else if (e.ctrlKey && e.key === 'c') {
            e.preventDefault();
            const val = $('#dkce-term-input').val();
            if (val) {
                this._termPrint($('#dkce-term-prompt-label').text() + ' $ ' + val + '^C', 'prompt-row');
                $('#dkce-term-input').val('');
            }
            t.running = false;
            t.historyIdx = -1;
            this._termHideCompletions();

        } else if (e.ctrlKey && e.key === 'u') {
            e.preventDefault();
            $('#dkce-term-input').val('');
            this._termHideCompletions();

        } else {
            // Any other printable key → close completions
            if (!['ArrowLeft','ArrowRight','Home','End','Shift','Control','Alt','Meta'].includes(e.key)) {
                this._termHideCompletions();
            }
        }
    }

    // ── Submit & execute ────────────────────────────────────────────────────

    _termSubmit(raw) {
        const cmd = raw.trim();
        const t = this.state.terminal;
        $('#dkce-term-input').val('');
        this._termHideCompletions();

        // Echo command line (plain text — ansiToHtml will escape it)
        const promptText = $('#dkce-term-prompt-label').text();
        this._termPrint(promptText + ' $ ' + cmd, 'prompt-row');


        t.history.unshift(cmd);
        if (t.history.length > 500) t.history.pop();
        t.historyIdx = -1;

        // Built-in: clear
        if (cmd === 'clear' || cmd === 'cls') { this._termClear(); return; }

        // Built-in: cd
        const cdM = cmd.match(/^cd(?:\s+(.*))?$/);
        if (cdM) { this._termCd((cdM[1] || '').trim()); return; }

        if (t.running) {
            this._termPrint('(still busy — wait or Ctrl+C)', 'info-row');
            return;
        }

        t.running = true;
        $('#dkce-term-input').prop('disabled', true);

        const _done = () => {
            t.running = false;
            $('#dkce-term-input').prop('disabled', false);
            setTimeout(() => $('#dkce-term-input').focus(), 10);
        };
        frappe.call({
            method: 'frappe_devkit.api.code_editor.run_terminal_command',
            args: { command: cmd, cwd: t.cwd },
            callback: r => {
                _done();
                if (!r || !r.message) {
                    this._termPrint('Error: no response from server', 'stderr-row');
                    return;
                }
                const res = r.message;
                if (!res.ok) {
                    this._termPrint('Error: ' + (res.error || 'unknown'), 'stderr-row');
                    return;
                }
                if (res.stdout && res.stdout.trim()) this._termPrint(res.stdout);
                if (res.stderr && res.stderr.trim()) this._termPrint(res.stderr, 'stderr-row');
                if (res.exit_code !== 0 && !res.stderr) {
                    this._termPrint(`exit ${res.exit_code}`, 'info-row');
                }
                if (res.cwd !== undefined) {
                    t.cwd = res.cwd;
                    this._termUpdatePrompt();
                }
            },
            error: () => {
                _done();
                this._termPrint('Request failed — check server logs', 'stderr-row');
            },
        });
    }

    _termCd(dir) {
        const t = this.state.terminal;
        if (!dir || dir === '~') {
            t.cwd = '';
            this._termUpdatePrompt();
            return;
        }
        frappe.call({
            method: 'frappe_devkit.api.code_editor.run_terminal_command',
            args: { command: '', cwd: t.cwd, _resolve_cwd: dir },
            callback: r => {
                if (r.message && r.message.ok) {
                    t.cwd = r.message.cwd || '';
                    this._termUpdatePrompt();
                } else {
                    const msg = (r.message && r.message.error) || `${dir}: No such file or directory`;
                    this._termPrint('cd: ' + msg, 'stderr-row');
                }
                setTimeout(() => $('#dkce-term-input').focus(), 10);
            },
        });
    }

    _termRunShortcut(cmd) {
        this._toggleTerminal(true);
        setTimeout(() => {
            $('#dkce-term-input').val(cmd);
            this._termSubmit(cmd);
        }, 50);
    }

    // ── Tab completion ──────────────────────────────────────────────────────

    _termDoComplete() {
        const partial = $('#dkce-term-input').val();
        frappe.call({
            method: 'frappe_devkit.api.code_editor.terminal_complete',
            args: { partial, cwd: this.state.terminal.cwd },
            callback: r => {
                if (!r.message) return;
                const list = r.message.completions || [];
                if (!list.length) return;
                if (list.length === 1) {
                    this._termApplyCompletion(list[0]);
                } else {
                    // Fill common prefix first
                    const word = this._termCompletingWord(partial);
                    const prefix = _commonPrefix(list.map(c => c.slice(word.length)));
                    if (prefix) {
                        const newVal = partial + prefix;
                        $('#dkce-term-input').val(newVal);
                    }
                    this._termShowCompletions(list);
                }
            },
        });
    }

    _termCompletingWord(val) {
        if (!val || val.endsWith(' ')) return '';
        const parts = val.split(/\s+/);
        return parts[parts.length - 1];
    }

    _termApplyCompletion(completion) {
        const val = $('#dkce-term-input').val();
        const word = this._termCompletingWord(val);
        const base = val.slice(0, val.length - word.length);
        const newVal = base + completion + (completion.endsWith('/') ? '' : ' ');
        $('#dkce-term-input').val(newVal);
        this._termHideCompletions();
        $('#dkce-term-input').focus();
    }

    _termShowCompletions(list) {
        this._termHideCompletions();
        const $popup = $('#dkce-term-comp-popup');
        $popup.empty();
        list.slice(0, 50).forEach((c, i) => {
            const isDir = c.endsWith('/');
            const icon = isDir ? '📁' : '📄';
            const $item = $(`
                <div class="dkce-term-comp-item${i === 0 ? ' sel' : ''}" data-completion="${_esc(c)}">
                  <span class="dkce-term-comp-icon">${icon}</span>
                  <span class="dkce-term-comp-name">${_esc(c)}</span>
                  ${isDir ? '<span class="dkce-term-comp-tag">dir</span>' : ''}
                </div>`);
            $item.data('completion', c);
            $popup.append($item);
        });
        $popup.addClass('open');
        $popup.find('.sel')[0]?.scrollIntoView({ block: 'nearest' });
    }

    _termCycleCompletion(dir) {
        const $popup = $('#dkce-term-comp-popup');
        const $items = $popup.find('.dkce-term-comp-item');
        if (!$items.length) return;
        const $cur = $items.filter('.sel');
        let idx = $cur.length ? $items.index($cur) : -1;
        idx = ((idx + dir) + $items.length) % $items.length;
        $items.removeClass('sel');
        const $next = $items.eq(idx).addClass('sel');
        $next[0].scrollIntoView({ block: 'nearest' });
        // Preview the selected completion in the input
        this._termApplyCompletionPreview($next.data('completion'));
    }

    _termApplyCompletionPreview(completion) {
        // Update the input with the highlighted item without closing popup
        const val = $('#dkce-term-input').val();
        const word = this._termCompletingWord(val);
        // Reconstruct: everything before the completing word + completion
        const base = val.slice(0, val.length - word.length);
        $('#dkce-term-input').val(base + completion);
    }

    _termHideCompletions() {
        $('#dkce-term-comp-popup').removeClass('open').empty();
    }

    // ── Resize ──────────────────────────────────────────────────────────────

    _sidebarResizeStart(e) {
        e.preventDefault();
        const s = this.state.settings;
        const startX = e.clientX;
        const startW = s.sidebarWidth;
        $('#dkce-sidebar-resize').addClass('dragging');

        const onMove = ev => {
            const newW = Math.max(160, Math.min(startW + (ev.clientX - startX), 520));
            s.sidebarWidth = Math.round(newW);
            document.getElementById('dkce-root').style.setProperty('--dkce-sidebar-w', s.sidebarWidth + 'px');
            $('#dkce-s-sw-val').text(s.sidebarWidth);
            if (this.editor) this.editor.layout();
        };
        const onUp = () => {
            $('#dkce-sidebar-resize').removeClass('dragging');
            document.removeEventListener('mousemove', onMove);
            document.removeEventListener('mouseup', onUp);
            this._saveSettings();
        };
        document.addEventListener('mousemove', onMove);
        document.addEventListener('mouseup', onUp);
    }

    _termResizeStart(e) {
        e.preventDefault();
        const t = this.state.terminal;
        const startY = e.clientY;
        const startH = t.height;
        $('#dkce-terminal-resize').addClass('dragging');

        const onMove = ev => {
            const newH = Math.max(100, Math.min(startH + (startY - ev.clientY), window.innerHeight * 0.7));
            t.height = Math.round(newH);
            document.getElementById('dkce-root').style.setProperty('--dkce-term-h', t.height + 'px');
            if (this.editor) this.editor.layout();
        };
        const onUp = () => {
            $('#dkce-terminal-resize').removeClass('dragging');
            document.removeEventListener('mousemove', onMove);
            document.removeEventListener('mouseup', onUp);
            this._saveSettings();
        };
        document.addEventListener('mousemove', onMove);
        document.addEventListener('mouseup', onUp);
    }

}

// ── Utility ────────────────────────────────────────────────────────────────
function _esc(str) {
    return String(str)
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;');
}

function _commonPrefix(strings) {
    if (!strings.length) return '';
    let prefix = strings[0];
    for (let i = 1; i < strings.length; i++) {
        while (!strings[i].startsWith(prefix)) {
            prefix = prefix.slice(0, -1);
            if (!prefix) return '';
        }
    }
    return prefix;
}
