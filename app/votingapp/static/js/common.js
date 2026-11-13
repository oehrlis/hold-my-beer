/* Gemeinsame Helfer: API-Aufrufe mit CSRF, Polling mit Backoff, Countdown, Balkendiagramm. */
(function () {
  'use strict';
  var meta = document.querySelector('meta[name="csrf-token"]');
  var csrf = meta ? meta.content : '';

  function el(tag, cls, text) {
    var e = document.createElement(tag);
    if (cls) e.className = cls;
    if (text !== undefined) e.textContent = text;
    return e;
  }

  // Liefert {status, body}; wirft bei Netzwerkfehlern.
  function api(method, url, payload) {
    var opts = { method: method, credentials: 'same-origin', headers: { 'Accept': 'application/json' } };
    if (method !== 'GET') {
      opts.headers['Content-Type'] = 'application/json';
      opts.headers['X-CSRFToken'] = csrf;
      opts.body = JSON.stringify(payload || {});
    }
    return fetch(url, opts).then(function (r) {
      return r.json().catch(function () { return { ok: false, error: { code: 'bad_response', message: 'Unerwartete Antwort.' } }; })
        .then(function (body) { return { status: r.status, body: body }; });
    });
  }

  // Pollt url alle `base` ms; bei Fehlern Backoff bis max 10 s; setzt selbst wieder auf.
  function poll(url, onData, onNet, base) {
    base = base || 2000;
    var delay = base, timer = null, running = false;
    function tick() {
      if (running) return;
      running = true;
      api('GET', url).then(function (res) {
        if (res.status === 401) { location.reload(); return; }
        if (res.body && res.body.ok) {
          delay = base; onNet(true);
          if (window.OLVTheme && res.body.data) window.OLVTheme.server(res.body.data.theme);
          onData(res.body.data);
        }
        else throw new Error('http ' + res.status);
      }).catch(function () {
        delay = Math.min(delay * 2, 10000); onNet(false);
      }).then(function () { running = false; timer = setTimeout(tick, delay); });
    }
    document.addEventListener('visibilitychange', function () {
      if (!document.hidden && !running) { clearTimeout(timer); tick(); }
    });
    tick();
  }

  function netIndicator(id) {
    var node = document.getElementById(id || 'net');
    return function (okay) { if (node) node.hidden = okay; };
  }

  // Countdown nur zur Anzeige; Restzeit stammt vom Server (kein Uhrenabgleich noetig).
  function countdown(node) {
    var deadline = null;
    function fmt(ms) {
      var s = Math.max(0, Math.ceil(ms / 1000));
      return Math.floor(s / 60) + ':' + ('0' + (s % 60)).slice(-2);
    }
    function paint() {
      if (deadline === null) { node.textContent = '--'; return; }
      var left = deadline - performance.now();
      node.textContent = fmt(left);
      node.classList.toggle('urgent', left <= 10000);
    }
    setInterval(paint, 250);
    return function (remainingSeconds) {
      deadline = (remainingSeconds === null || remainingSeconds === undefined) ? null : performance.now() + remainingSeconds * 1000;
      paint();
    };
  }

  function bars(container, result, options) {
    container.replaceChildren();
    var max = Math.max(1, result.total);
    options.forEach(function (o) {
      if (result.counts[o.key] === undefined) return;
      var n = result.counts[o.key];
      var win = result.winner === o.key;
      var row = el('div', 'bar-row' + (win ? ' win' : '') + (result.selected === o.key ? ' selected' : ''));
      row.appendChild(el('div', 'bar-label', o.key + ' · ' + o.title));
      var track = el('div', 'bar-track');
      var fill = el('div', 'bar-fill');
      fill.style.width = (n / max * 100) + '%';
      track.appendChild(fill);
      row.appendChild(track);
      row.appendChild(el('div', 'bar-n', n + (n === 1 ? ' Stimme' : ' Stimmen')));
      container.appendChild(row);
    });
  }

  function winnerText(result, options) {
    if (result.total === 0) return 'Keine Stimmen abgegeben.';
    if (result.tie) return 'Gleichstand zwischen ' + result.tied.join(' und ') + ' – der Admin entscheidet.';
    var t = options.filter(function (o) { return o.key === result.winner; })[0];
    return 'Gewinner: ' + result.winner + (t ? ' · ' + t.title : '');
  }

  function meta2(o) {
    return [o.owner, o.category, o.difficulty].filter(Boolean).join(' · ');
  }

  // Notfall-Reset direkt von der Teilnehmer-/Beamerseite (Admin-Passwort wird abgefragt).
  var qr = document.getElementById('quick-reset');
  if (qr) qr.addEventListener('click', function () {
    var pw = window.prompt('Admin-Passwort für den Reset:');
    if (!pw) return;
    var whole = window.confirm('OK = GESAMTE Session zurücksetzen (alle Runden, alle Stimmen).\nAbbrechen = nur die aktuelle Runde zurücksetzen.');
    if (whole && !window.confirm('Wirklich ALLES zurücksetzen?')) return;
    api('POST', '/admin/quick-reset', { password: pw, scope: whole ? 'session' : 'round' }).then(function (res) {
      window.alert(res.body.ok ? 'Zurückgesetzt.' : res.body.error.message);
      if (res.body.ok) location.reload();
    }).catch(function () { window.alert('Netzwerkfehler.'); });
  });

  window.OLV = { api: api, poll: poll, net: netIndicator, countdown: countdown, bars: bars,
                 winnerText: winnerText, el: el, meta: meta2 };
})();
