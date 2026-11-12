/* hold-my-beer deck: theme switch Accenture (acn, default) <-> Hold my Beer (hmb). Inlined into the
   generated cover atom by generate.py, right after deck-lang.js. Sets <html data-deck-theme>; deck.css
   styles the hmb skin under html[data-deck-theme="hmb"] only, so acn is the plain Accenture theme.
   Order: ?theme= wins, then localStorage, then acn. Key T toggles (reveal has no default binding on T).
   Switching is live: no reload, slide index, fragments and language stay as they are. */
(function () {
  var KEY = "hmb-deck-theme";
  var THEMES = ["acn", "hmb"];
  function valid(t) { return THEMES.indexOf(t) >= 0 ? t : null; }
  function fromUrl() {
    try { return valid(new URLSearchParams(window.location.search).get("theme")); } catch (err) { return null; }
  }
  function fromStore() {
    try { return valid(window.localStorage.getItem(KEY)); } catch (err) { return null; }
  }
  function current() { return document.documentElement.getAttribute("data-deck-theme") || "acn"; }
  function apply(theme, persist) {
    document.documentElement.setAttribute("data-deck-theme", theme);
    var marks = document.querySelectorAll(".hmb-theme [data-t]");
    for (var i = 0; i < marks.length; i++) {
      marks[i].className = marks[i].getAttribute("data-t") === theme ? "on" : "";
    }
    if (persist) {
      try { window.localStorage.setItem(KEY, theme); } catch (err) { /* private mode: ignore */ }
    }
    if (window.Reveal && typeof window.Reveal.isReady === "function" && window.Reveal.isReady()) {
      window.Reveal.layout();
    }
  }
  function toggle() { apply(current() === "hmb" ? "acn" : "hmb", true); }
  // runs while the deck is parsed (cover is the first slide): no flash of the other theme
  apply(fromUrl() || fromStore() || "acn", false);
  window.hmbDeckTheme = { set: function (t) { if (valid(t)) { apply(t, true); } }, toggle: toggle, current: current };

  function setup() {
    var ind = document.createElement("div");
    ind.className = "hmb-theme";
    ind.setAttribute("title", "Theme Accenture / Hold my Beer (T)");
    ind.innerHTML = '<span data-t="acn">ACN</span> | <span data-t="hmb">HMB</span>';
    ind.addEventListener("click", function (ev) {
      var t = ev.target && ev.target.getAttribute && ev.target.getAttribute("data-t");
      if (valid(t)) { apply(t, true); }
    });
    document.body.appendChild(ind);
    // footer brand for the hmb skin: logo mark + name in front of the assembler's utility line
    // (hidden in acn by deck.css, so the Accenture footer stays as the theme renders it)
    var util = document.querySelector(".brandbar span");
    if (util && !util.querySelector(".hmb-brand")) {
      var brand = document.createElement("span");
      brand.className = "hmb-brand";
      brand.innerHTML = '<i class="hmb-mark" aria-hidden="true"></i>Hold my beer · ';
      util.insertBefore(brand, util.firstChild);
    }
    apply(current(), false);
    if (window.Reveal && typeof window.Reveal.addKeyBinding === "function") {
      window.Reveal.addKeyBinding({ keyCode: 84, key: "T", description: "Theme Accenture / Hold my Beer" }, toggle);
    }
  }
  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", setup);
  } else {
    setup();
  }
})();
