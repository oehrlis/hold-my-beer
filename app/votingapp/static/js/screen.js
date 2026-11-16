(function () {
  'use strict';
  var $ = function (id) { return document.getElementById(id); };
  var el = OLV.el;
  var vCount = OLV.countdown($('v-count'), $('v-beer')), cCount = OLV.countdown($('ch-count'));
  var VIEWS = ['s-waiting', 's-voting', 's-closed', 's-result', 's-challenge', 's-score', 's-closing'];
  var optKey = null;

  function show(id) { VIEWS.forEach(function (v) { $(v).hidden = v !== id; }); }

  // Ton standardmaessig aus; der Klick gibt ihn im Browser frei und spielt einmal zur Probe (Saalanlage).
  // Die Taste gibt es nur, wenn auf dem Host BURP_FILE gesetzt ist.
  var soundBtn = $('s-sound');
  if (soundBtn) soundBtn.addEventListener('click', function () {
    var on = soundBtn.getAttribute('aria-pressed') !== 'true';
    OLV.sound(on, soundBtn.dataset.src).then(function (ok) {
      if (!ok) { soundBtn.textContent = 'Ton n/v'; soundBtn.disabled = true; return; }
      soundBtn.setAttribute('aria-pressed', on ? 'true' : 'false');
      soundBtn.textContent = on ? 'Ton an' : 'Ton aus';
      $('s-credit').hidden = !on;
      if (on) OLV.burpSound();
    });
  });

  function render(d) {
    var r = d.round;
    $('s-round').textContent = r ? 'Runde ' + r.number + ' von ' + r.total + ' · ' + r.name : '';
    switch (d.state) {
      case 'voting_open':
        show('s-voting');
        $('v-title').textContent = 'Welche Aufgabe bearbeiten wir live?' + (r.runoff ? ' (Stichwahl)' : '');
        var key = r.id + r.active.join('') + r.options.map(function (o) { return o.title; }).join('|');
        if (key !== optKey) {
          optKey = key;
          var box = $('v-options'); box.replaceChildren();
          r.options.forEach(function (o) {
            if (r.active.indexOf(o.key) < 0) return;
            var c = el('div', 's-opt');
            c.appendChild(el('span', 's-key', o.key));
            c.appendChild(el('span', 's-opt-title', o.title));
            c.appendChild(el('span', 's-opt-meta', OLV.meta(o)));
            box.appendChild(c);
          });
        }
        $('v-votes').textContent = d.voting.votes;
        vCount(d.voting.remaining, d.voting.duration);
        break;
      case 'voting_closed':
        show('s-closed'); $('cl-votes').textContent = d.voting.votes; vCount(null); break;
      case 'result_visible':
        show('s-result');
        OLV.bars($('x-bars'), d.result, r.options);
        $('x-winner').textContent = OLV.winnerText(d.result, r.options);
        break;
      case 'challenge_running':
        show('s-challenge');
        $('ch-title').textContent = d.challenge.key + ' · ' + d.challenge.topic.title;
        cCount(d.challenge.remaining);
        break;
      case 'scorecard_visible':
        show('s-score');
        $('sc-title').textContent = d.challenge ? d.challenge.key + ' · ' + d.challenge.topic.title : '';
        var ul = $('sc-list'); ul.replaceChildren();
        var sc = d.scorecard;
        if (sc) sc.ratings.forEach(function (x) { ul.appendChild(el('li', 'chip', x.label)); });
        $('sc-note').textContent = sc && sc.note ? sc.note : (sc ? '' : 'Bewertung folgt …');
        break;
      case 'closing':
        show('s-closing');
        var list = $('cs-list'); list.replaceChildren();
        (d.closing || []).forEach(function (c) {
          var li = el('li');
          li.appendChild(el('strong', '', 'Runde ' + c.number + ' · ' + c.name + ': '));
          li.appendChild(document.createTextNode(c.played ? c.topic + ' (' + c.owner + ')' : '– nicht gespielt –'));
          if (c.scorecard && c.scorecard.ratings.length) {
            li.appendChild(el('div', 's-opt-meta', c.scorecard.ratings.map(function (x) { return x.label; }).join(' · ')));
          }
          list.appendChild(li);
        });
        break;
      default:
        show('s-waiting');
        $('s-wait-text').textContent = d.round ? 'Nächste Runde: ' + d.round.number + ' · ' + d.round.name : 'Gleich geht’s los …';
    }
  }

  OLV.poll('/api/state', render, OLV.net('net'), 2000);
})();
