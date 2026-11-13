(function () {
  'use strict';
  var $ = function (id) { return document.getElementById(id); };
  var el = OLV.el;
  var st = null, built = {};
  var setCount = OLV.countdown($('a-count'));
  var setChTimer = OLV.countdown($('a-ch-timer'));

  function msg(t, err) { var m = $('a-msg'); m.textContent = t || ''; m.classList.toggle('err', !!err); }

  // Liefert ein Promise<boolean> (true = Server hat die Aktion angenommen).
  function act(name, payload, confirmText) {
    if (confirmText && !window.confirm(confirmText)) return Promise.resolve(false);
    return OLV.api('POST', '/admin/api/' + name, payload || {}).then(function (res) {
      if (res.status === 401) { location.reload(); return false; }
      if (res.body.ok) { msg(res.body.message); render(res.body.data); return true; }
      msg(res.body.error.message, true); return false;
    }).catch(function () { msg('Netzwerkfehler – Aktion nicht bestätigt, bitte Status prüfen.', true); return false; });
  }

  function fill(sel, items, keep) {
    var cur = sel.value;
    sel.replaceChildren();
    items.forEach(function (i) { var o = el('option', '', i.label); o.value = i.value; sel.appendChild(o); });
    if (keep && cur) sel.value = cur;
  }

  function radioOpts(opts, name) {
    var box = $('a-ch-opts'); box.replaceChildren();
    opts.forEach(function (o) {
      var l = el('label', 'radio');
      var i = el('input'); i.type = 'radio'; i.name = name; i.value = o.key;
      l.appendChild(i); l.appendChild(document.createTextNode(' ' + o.key + ' · ' + o.title));
      box.appendChild(l);
    });
  }

  function chosen() {
    var c = document.querySelector('input[name="chopt"]:checked');
    return c ? c.value : null;
  }

  function render(d) {
    paintTheme(d.theme);
    st = d;
    var s = d.state, r = d.round;
    $('a-state').textContent = s;
    $('a-round').textContent = r ? 'Runde ' + r.number + ' · ' + r.name : 'keine Runde aktiv';
    $('a-votes').textContent = d.live ? d.live.total : 0;
    var rem = s === 'voting_open' ? d.voting && d.voting.remaining : (s === 'challenge_running' && d.challenge ? d.challenge.remaining : null);
    setCount(s === 'challenge_running' ? null : rem);
    var running = s === 'challenge_running' && d.challenge;
    $('a-ch-timer-box').hidden = !running;
    setChTimer(running ? d.challenge.remaining : null);
    $('p-score').classList.toggle('attn', s === 'scorecard_visible');

    var sig = JSON.stringify(d.rounds.map(function (x) { return [x.id, x.options.map(function (o) { return o.title; })]; })) + (r ? r.id : '');
    if (built.rounds !== sig) {
      built.rounds = sig;
      var items = d.rounds.map(function (x) { return { value: x.id, label: x.number + ' · ' + x.name }; });
      fill($('a-round-sel'), items, false); fill($('a-res-round'), items, true);
      if (r) $('a-round-sel').value = r.id;
    }
    var esig = JSON.stringify(d.rounds.map(function (x) { return [x.id, x.votes, x.played, x.options]; })) + d.state;
    if (built.edit !== esig) {
      built.edit = esig;
      if (!built.editSel) { built.editSel = true; fill($('a-edit-round'), d.rounds.map(function (x) { return { value: x.id, label: x.number + ' · ' + x.name }; }), false); if (r) $('a-edit-round').value = r.id; }
      buildEditor(d);
    }
    var rsig = JSON.stringify(d.reserve);
    if (built.reserve !== rsig) {
      built.reserve = rsig;
      fill($('a-res-topic'), d.reserve.map(function (t) { return { value: t.id, label: t.title + (t.used ? ' (zugeordnet)' : '') }; }), true);
    }
    if (!built.ratings) {
      built.ratings = true;
      var box = $('a-ratings');
      d.ratings.forEach(function (x) {
        var l = el('label', 'check'); var i = el('input'); i.type = 'checkbox'; i.value = x.key;
        l.appendChild(i); l.appendChild(document.createTextNode(' ' + x.label)); box.appendChild(l);
      });
    }
    var osig = r ? r.id + JSON.stringify(r.active) + r.options.map(function (o) { return o.title; }).join('|') : '';
    if (built.opts !== osig) { built.opts = osig; if (r) radioOpts(r.options.filter(function (o) { return r.active.indexOf(o.key) >= 0; }), 'chopt'); }

    if (d.live && !chosen()) {
      var pre = d.live.selected || d.live.winner;
      var rb = pre && document.querySelector('input[name="chopt"][value="' + pre + '"]');
      if (rb) rb.checked = true;
    }
    var live = $('a-live');
    if (d.live && r) OLV.bars(live, d.live, r.options); else live.replaceChildren();
    var w = $('a-winner');
    w.textContent = d.live && d.live.total ? OLV.winnerText(d.live, r.options) + (d.live.runner_up ? ' · Zweiter: ' + d.live.runner_up : '') : '';
    $('a-tie').hidden = !(d.live && d.live.tie && (s === 'voting_closed' || s === 'result_visible'));
    $('a-ch-info').textContent = s === 'scorecard_visible' ? 'Challenge gestoppt – jetzt unten die Scorecard bewerten.' : d.live && d.live.selected ? 'Gewähltes Challenge-Thema: ' + d.live.selected +
      (d.live.deviation_reason ? ' · Begründung: ' + d.live.deviation_reason : '') : 'Noch kein Challenge-Thema gewählt.';

    function en(id, on) { $(id).disabled = !on; }
    en('b-activate', s === 'waiting'); en('b-open', s === 'waiting'); en('b-close', s === 'voting_open');
    en('b-publish', s === 'voting_closed'); en('b-select', s === 'result_visible');
    en('b-chstart', s === 'result_visible'); en('b-chstop', s === 'challenge_running');
    en('b-score', s === 'scorecard_visible'); en('b-next', s === 'scorecard_visible'); en('b-closing', s === 'scorecard_visible');
    en('b-reserve', s === 'waiting');

    var tb = $('a-audit'); tb.replaceChildren();
    d.audit.forEach(function (a) {
      var tr = el('tr');
      [a.at.replace('T', ' ').replace('Z', ''), a.actor, a.action, a.detail || ''].forEach(function (t) { tr.appendChild(el('td', '', t)); });
      tb.appendChild(tr);
    });
  }

  // ---- Aufgaben-Editor: baut sich nur neu auf, wenn sich Runde oder Serverdaten aendern (nie waehrend des Tippens)
  var DIFF = ['', 'Leicht', 'Mittel', 'Schwer'], RISK = ['', 'Niedrig', 'Mittel', 'Hoch'];
  function field(labelText, node) {
    var l = el('label', 'ef'); l.appendChild(el('span', '', labelText)); l.appendChild(node); return l;
  }
  function input(val, max) { var i = el('input'); i.type = 'text'; i.maxLength = max; i.value = val || ''; i.autocomplete = 'off'; return i; }
  function select(list, val) {
    var s = el('select');
    list.forEach(function (x) { var o = el('option', '', x || '–'); o.value = x; s.appendChild(o); });
    s.value = val || ''; return s;
  }
  function editRow(rid, o, count, editable) {
    var row = el('div', 'edit-row');
    row.appendChild(el('strong', 'edit-key', o ? o.key : 'Neu'));
    var t = input(o && o.title, 200), ow = input(o && o.owner, 40), ca = input(o && o.category, 60);
    var di = select(DIFF, o && o.difficulty), ri = select(RISK, o && o.risk);
    row.appendChild(field('Titel', t)); row.appendChild(field('Owner', ow)); row.appendChild(field('Kategorie', ca));
    row.appendChild(field('Schwierigkeit', di)); row.appendChild(field('Live-Risiko', ri));
    var save = el('button', 'btn btn-primary btn-sm', 'Speichern'); save.type = 'button'; save.disabled = !editable;
    save.addEventListener('click', function () {
      act('save_option', { round_id: rid, option: o ? o.key : 'new', title: t.value, owner: ow.value,
        category: ca.value, difficulty: di.value, risk: ri.value });
    });
    row.appendChild(save);
    if (o) {
      var del = el('button', 'btn btn-danger btn-sm', 'Löschen'); del.type = 'button'; del.disabled = !editable || count <= 2;
      del.addEventListener('click', function () {
        act('delete_option', { round_id: rid, option: o.key }, 'Aufgabe ' + o.key + ' wirklich löschen? Die übrigen werden neu durchbuchstabiert.');
      });
      row.appendChild(del);
    } else {
      var cancel = el('button', 'btn btn-ghost btn-sm', 'Abbrechen'); cancel.type = 'button';
      cancel.addEventListener('click', function () { row.remove(); });
      row.appendChild(cancel);
    }
    return row;
  }
  function buildEditor(d) {
    var rid = parseInt($('a-edit-round').value, 10);
    var rd = d.rounds.filter(function (x) { return x.id === rid; })[0];
    var box = $('a-edit-list'); box.replaceChildren();
    if (!rd) return;
    var editable = d.state === 'waiting' && rd.votes === 0 && !rd.played;
    rd.options.forEach(function (o) { box.appendChild(editRow(rid, o, rd.options.length, editable)); });
    $('b-addopt').disabled = !editable || rd.options.length >= 4;
    $('b-addopt').onclick = function () {
      if (!box.querySelector('.edit-row:last-child .edit-key') || box.lastChild.firstChild.textContent !== 'Neu')
        box.appendChild(editRow(rid, null, rd.options.length, true));
    };
  }

  function on(id, fn) { $(id).addEventListener('click', fn); }
  $('a-edit-round').addEventListener('change', function () { buildEditor(st); });
  on('b-activate', function () { act('activate_round', { round_id: $('a-round-sel').value }); });
  on('b-open', function () { act('open_voting', { duration: $('a-dur').value }); });
  on('b-close', function () { act('close_voting'); });
  on('b-publish', function () { act('publish_result'); });
  on('b-runoff', function () { act('runoff', { confirm: true, duration: $('a-dur').value }, 'Stichwahl starten? Die bisherigen Stimmen dieser Runde werden verworfen (im Auditlog festgehalten).'); });
  on('b-select', function () {
    var o = chosen(); if (!o) { msg('Bitte eine Option wählen.', true); return; }
    act('select_challenge', { option: o, reason: $('a-reason').value });
  });
  on('b-chstart', function () {
    // gewaehlte Option zuerst festlegen (falls noetig), dann Challenge freigeben und Timer starten
    var o = chosen(), cur = st.live && st.live.selected;
    if (o && o !== cur) {
      act('select_challenge', { option: o, reason: $('a-reason').value }).then(function (okay) {
        if (okay) act('start_challenge');
      });
    } else act('start_challenge');
  });
  on('b-chstop', function () {
    act('finish_challenge').then(function (okay) {
      if (okay) { $('p-score').scrollIntoView({ behavior: 'smooth', block: 'start' }); $('a-note').focus({ preventScroll: true }); }
    });
  });
  on('b-score', function () {
    var rs = Array.prototype.map.call(document.querySelectorAll('#a-ratings input:checked'), function (i) { return i.value; });
    act('save_scorecard', { ratings: rs, note: $('a-note').value });
  });
  on('b-next', function () { act('next_round'); });
  on('b-closing', function () { act('show_closing'); });
  on('b-reserve', function () {
    act('assign_reserve', { round_id: $('a-res-round').value, option: $('a-res-opt').value, topic_id: $('a-res-topic').value });
  });
  on('b-rreset', function () {
    act('reset_round', { confirm: true }, 'Aktuelle Runde zurücksetzen? Stimmen, Ergebnis und Scorecard dieser Runde werden gelöscht.');
  });
  on('b-sreset', function () {
    var t = window.prompt('Gesamte Session zurücksetzen? Zur Bestätigung RESET eingeben:');
    if (t === 'RESET') act('reset_session', { confirm: 'RESET' });
  });

  // Layout-Vorgabe fuer alle; das Admin-Geraet selbst folgt ihr (lokale Wahl wird verworfen)
  function paintTheme(t) {
    ['acn', 'hmb'].forEach(function (k) { $('b-theme-' + k).setAttribute('aria-pressed', String(k === t)); });
  }
  ['acn', 'hmb'].forEach(function (k) {
    on('b-theme-' + k, function () {
      act('set_theme', { theme: k }).then(function (okay) { if (okay) { OLVTheme.server(k); OLVTheme.follow(); } });
    });
  });

  OLV.poll('/admin/api/state', render, OLV.net('net'), 2000);
})();
