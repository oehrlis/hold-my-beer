/* hold-my-beer deck: DE/EN switch. Inlined into the generated cover atom by generate.py.
   Every visible text exists twice (<span lang="de"> / <span lang="en">); deck.css hides the
   inactive one via <html data-deck-lang>. Order: ?lang= wins, then localStorage, then de.
   Key L toggles (overrides reveal's vim-style "L = next slide"; arrow keys are unaffected). */
(function () {
  var KEY = "hmb-deck-lang";
  var LANGS = ["de", "en"];
  function valid(l) { return LANGS.indexOf(l) >= 0 ? l : null; }
  function fromUrl() {
    try { return valid(new URLSearchParams(window.location.search).get("lang")); } catch (err) { return null; }
  }
  function fromStore() {
    try { return valid(window.localStorage.getItem(KEY)); } catch (err) { return null; }
  }
  function current() { return document.documentElement.getAttribute("data-deck-lang") || "de"; }
  function apply(lang, persist) {
    var root = document.documentElement;
    root.setAttribute("data-deck-lang", lang);
    root.setAttribute("lang", lang);
    var marks = document.querySelectorAll(".hmb-lang [data-l]");
    for (var i = 0; i < marks.length; i++) {
      marks[i].className = marks[i].getAttribute("data-l") === lang ? "on" : "";
    }
    if (persist) {
      try { window.localStorage.setItem(KEY, lang); } catch (err) { /* private mode: ignore */ }
    }
    if (window.Reveal && typeof window.Reveal.isReady === "function" && window.Reveal.isReady()) {
      window.Reveal.layout();
    }
  }
  function toggle() { apply(current() === "en" ? "de" : "en", true); }
  // runs while the deck is parsed (cover is the first slide): no flash of both languages
  apply(fromUrl() || fromStore() || "de", false);
  window.hmbDeckLang = { set: function (l) { if (valid(l)) { apply(l, true); } }, toggle: toggle, current: current };

  function setup() {
    var ind = document.createElement("div");
    ind.className = "hmb-lang";
    ind.setAttribute("title", "Sprache / language (L)");
    ind.innerHTML = '<span data-l="de">DE</span> | <span data-l="en">EN</span>';
    ind.addEventListener("click", function (ev) {
      var l = ev.target && ev.target.getAttribute && ev.target.getAttribute("data-l");
      if (valid(l)) { apply(l, true); }
    });
    document.body.appendChild(ind);
    apply(current(), false);
    if (window.Reveal && typeof window.Reveal.addKeyBinding === "function") {
      window.Reveal.addKeyBinding({ keyCode: 76, key: "L", description: "Sprache DE/EN" }, toggle);
      window.Reveal.on("ready", function () { window.Reveal.layout(); });
    }
  }
  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", setup);
  } else {
    setup();
  }
})();
