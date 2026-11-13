/* Layout Accenture (acn) <-> Hold my Beer (hmb); same codes and keys as the deck (slides/deck-theme.js).
   Order: ?theme= (this page only), then the local choice of this device (localStorage, key t or the
   ACN | HMB switch in the header), then the admin default (data-theme-default, later from every poll via
   OLVTheme.server). Shift+T drops the local choice and follows the admin again. Loaded in <head>, before
   the first paint, so the other layout never flashes. */
(function () {
  'use strict';
  var KEY = 'hmb-app-theme';
  var THEMES = ['acn', 'hmb'];
  var root = document.documentElement;
  function valid(t) { return THEMES.indexOf(t) >= 0 ? t : null; }
  function stored() { try { return valid(window.localStorage.getItem(KEY)); } catch (err) { return null; } }
  function store(t) {
    try { if (t) window.localStorage.setItem(KEY, t); else window.localStorage.removeItem(KEY); } catch (err) { /* private mode */ }
  }
  var fromUrl = null;
  try { fromUrl = valid(new URLSearchParams(window.location.search).get('theme')); } catch (err) { /* old browser */ }
  var server = valid(root.getAttribute('data-theme-default')) || 'acn';

  function local() { return fromUrl || stored(); }
  function current() { return local() || server; }

  function paint() {
    var t = current();
    root.setAttribute('data-theme', t);
    var sw = document.getElementById('theme-switch');
    if (!sw) return;
    var marks = sw.querySelectorAll('[data-t]');
    for (var i = 0; i < marks.length; i++) marks[i].className = marks[i].getAttribute('data-t') === t ? 'on' : '';
    sw.classList.toggle('local', !!local());
    sw.title = 'Layout Accenture / Hold my Beer (Taste T)' +
      (local() ? ' – lokal gewählt, Vorgabe: ' + server.toUpperCase() + ' (Shift+T)' : ' – Vorgabe des Admins');
  }
  function setLocal(t) { fromUrl = null; store(valid(t)); paint(); }
  function toggle() { setLocal(current() === 'hmb' ? 'acn' : 'hmb'); }

  paint();
  window.OLVTheme = {
    server: function (t) { if (valid(t) && t !== server) { server = t; paint(); } },
    serverTheme: function () { return server; },
    set: setLocal, toggle: toggle, current: current,
    follow: function () { setLocal(null); }
  };

  document.addEventListener('keydown', function (ev) {
    if (ev.ctrlKey || ev.metaKey || ev.altKey) return;
    var tag = ev.target && ev.target.tagName;
    if (tag === 'INPUT' || tag === 'TEXTAREA' || tag === 'SELECT') return;
    if (ev.key === 't') toggle();
    else if (ev.key === 'T') setLocal(null);
  });

  document.addEventListener('DOMContentLoaded', function () {
    var head = document.querySelector('header.brand, header.s-head');
    if (!head) return;
    var sw = document.createElement('button');
    sw.type = 'button';
    sw.id = 'theme-switch';
    sw.className = 'theme-switch';
    sw.innerHTML = '<span data-t="acn">ACN</span> | <span data-t="hmb">HMB</span>';
    sw.addEventListener('click', toggle);
    var net = document.getElementById('net');
    head.insertBefore(sw, net || null);
    paint();
  });
})();
