(function () {
  'use strict';
  var $ = function (id) { return document.getElementById(id); };
  var el = OLV.el;
  var data = null, selected = null, renderedKey = null, reqId = null, busy = false;

  function lsGet(k) { try { return localStorage.getItem(k); } catch (e) { return null; } }
  function lsSet(k, v) { try { localStorage.setItem(k, v); } catch (e) { /* optional */ } }
  var started = lsGet('olv_started') === '1';
  var setCount = OLV.countdown($('r-count'), $('r-beer'));
  var setChallenge = OLV.countdown($('x-timer'));
  var setLiveCount = OLV.countdown($('live-count'));

  function newReqId() {
    var a = new Uint8Array(16);
    (window.crypto || window.msCrypto).getRandomValues(a);
    return Array.prototype.map.call(a, function (b) { return ('0' + b.toString(16)).slice(-2); }).join('');
  }

  function show(id) {
    ['v-intro', 'v-waiting', 'v-voting', 'v-challenge', 'v-result', 'v-closing'].forEach(function (v) { $(v).hidden = v !== id; });
  }

  function msg(text, err) { var m = $('r-msg'); m.textContent = text || ''; m.classList.toggle('err', !!err); }

  function topicOf(key) {
    var o = data.round.options.filter(function (x) { return x.key === key; })[0];
    return o ? o.key + ' · ' + o.title : key;
  }

  function buildOptions() {
    var box = $('r-options');
    box.replaceChildren();
    data.round.options.forEach(function (o) {
      if (data.round.active.indexOf(o.key) < 0) return;
      var b = el('button', 'opt');
      b.type = 'button'; b.dataset.key = o.key;
      b.setAttribute('role', 'radio'); b.setAttribute('aria-checked', 'false');
      b.appendChild(el('span', 'opt-key', o.key));
      var body = el('span', 'opt-body');
      body.appendChild(el('span', 'opt-title', o.title));
      body.appendChild(el('span', 'opt-meta', OLV.meta(o)));
      b.appendChild(body);
      b.addEventListener('click', function () { if (!data.my_vote) choose(o.key); });
      box.appendChild(b);
    });
  }

  function choose(key) {
    selected = key;
    paintSelection();
  }

  function paintSelection() {
    var voted = data && data.my_vote;
    var cur = voted || selected;
    Array.prototype.forEach.call($('r-options').children, function (b) {
      var on = b.dataset.key === cur;
      b.classList.toggle('selected', on);
      b.setAttribute('aria-checked', on ? 'true' : 'false');
      b.disabled = !!voted;
    });
    $('btn-vote').disabled = !selected || !!voted || busy;
    $('btn-random').disabled = !!voted;
    $('r-actions').hidden = !!voted;
    $('r-done').hidden = !voted;
    if (voted) $('r-done-text').textContent = 'Du hast für ' + topicOf(voted) + ' gestimmt.';
  }

  function render(d) {
    data = d;
    if (!started) { show('v-intro'); return; }
    var r = d.round;
    if (d.state === 'voting_open' && r) {
      show('v-voting');
      var key = r.id + ':' + r.active.join('') + ':' + r.options.map(function (o) { return o.title; }).join('|');
      if (key !== renderedKey) { renderedKey = key; selected = null; reqId = null; msg(''); buildOptions(); }
      $('r-eyebrow').textContent = 'Runde ' + r.number + ' von ' + r.total + ' · ' + r.name + (r.runoff ? ' · Stichwahl' : '');
      $('r-title').textContent = 'Welche Aufgabe bearbeiten wir live?';
      setCount(d.voting.remaining, d.voting.duration);
      if (d.my_vote) msg('');
      paintSelection();
    } else if (d.state === 'challenge_running' && d.challenge) {
      show('v-challenge');
      $('live-topic').textContent = d.challenge.key + ' · ' + d.challenge.topic.title;
      setLiveCount(d.challenge.remaining);
    } else if (d.state === 'result_visible' || d.state === 'scorecard_visible') {
      show('v-result');
      $('x-eyebrow').textContent = 'Runde ' + r.number + ' · ' + r.name;
      $('x-title').textContent = d.state === 'result_visible' ? 'Ergebnis' : (d.state === 'challenge_running' ? 'Challenge läuft!' : 'Ergebnis & Challenge');
      OLV.bars($('x-bars'), d.result, r.options);
      $('x-winner').textContent = OLV.winnerText(d.result, r.options);
      var ch = $('x-ch-body'); ch.replaceChildren();
      $('x-challenge').hidden = !d.challenge;
      if (d.challenge) {
        ch.appendChild(el('p', 'eyebrow', d.state === 'challenge_running' ? 'Challenge läuft' : 'Challenge-Thema'));
        ch.appendChild(el('p', 'card-title', d.challenge.key + ' · ' + d.challenge.topic.title));
        ch.appendChild(el('p', 'muted', OLV.meta(d.challenge.topic)));
        if (d.result.deviation_reason) ch.appendChild(el('p', 'muted', 'Begründung: ' + d.result.deviation_reason));
      }
      var running = d.state === 'challenge_running' && d.challenge;
      $('x-timer-box').hidden = !running;
      setChallenge(running ? d.challenge.remaining : null);
      $('x-timer-note').textContent = running ? (d.challenge.remaining <= 0 ? 'Zeit abgelaufen – gleich geht es weiter.' : 'Die Challenge läuft jetzt live.') : '';
      var sc = $('x-score'); sc.replaceChildren();
      sc.hidden = !(d.scorecard && d.scorecard.ratings.length);
      if (!sc.hidden) {
        sc.appendChild(el('p', 'eyebrow', 'Scorecard'));
        var ul = el('ul', 'chips');
        d.scorecard.ratings.forEach(function (x) { ul.appendChild(el('li', 'chip', x.label)); });
        sc.appendChild(ul);
        if (d.scorecard.note) sc.appendChild(el('p', 'muted', d.scorecard.note));
      }
    } else if (d.state === 'closing') {
      show('v-closing');
      var list = $('c-list'); list.replaceChildren();
      (d.closing || []).forEach(function (c) {
        var li = el('li', '', 'Runde ' + c.number + ' · ' + c.name + ': ' + (c.played ? c.topic : '– nicht gespielt –'));
        list.appendChild(li);
      });
    } else {
      show('v-waiting');
      var closed = d.state === 'voting_closed';
      $('w-eyebrow').textContent = r ? 'Runde ' + r.number + ' von ' + r.total + ' · ' + r.name : '';
      $('w-title').textContent = closed ? 'Voting geschlossen' : 'Gleich geht’s los';
      $('w-text').textContent = closed
        ? 'Danke für deine Stimme! Das Ergebnis wird gleich gezeigt.'
        : 'Warte auf die nächste Abstimmung. Diese Seite aktualisiert sich automatisch.';
    }
  }

  $('btn-start').addEventListener('click', function () {
    started = true; lsSet('olv_started', '1'); if (data) render(data);
  });

  $('btn-random').addEventListener('click', function () {
    var keys = data.round.active;
    choose(keys[Math.floor(Math.random() * keys.length)]);
    msg('Zufällig markiert – noch nicht abgegeben.');
  });

  $('btn-vote').addEventListener('click', function () {
    if (!selected || busy) return;
    busy = true; paintSelection(); msg('Stimme wird gesendet …');
    reqId = reqId || newReqId(); // gleicher Retry => keine zweite Stimme
    OLV.api('POST', '/api/vote', { option: selected, request_id: reqId }).then(function (res) {
      busy = false;
      if (res.body.ok) {
        data.my_vote = res.body.data.option; reqId = null; msg(''); paintSelection();
      } else {
        var code = res.body.error && res.body.error.code;
        msg(res.body.error ? res.body.error.message : 'Fehler.', true);
        if (code === 'already_voted') { reqId = null; }
        if (code === 'csrf_invalid') { setTimeout(function () { location.reload(); }, 1500); }
        paintSelection();
      }
    }).catch(function () {
      busy = false; msg('Netzwerkproblem – bitte erneut tippen. Es wird keine zweite Stimme gezählt.', true); paintSelection();
    });
  });

  OLV.poll('/api/state', render, OLV.net('net'), 2000);
})();
