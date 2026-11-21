/* ProjectPulse - small enhancements. Every page still works without this file. */
(function () {
  "use strict";
  var $ = function (s, r) { return (r || document).querySelector(s); };
  var $$ = function (s, r) { return Array.prototype.slice.call((r || document).querySelectorAll(s)); };

  /* Sidebar toggle on small screens */
  var app = $(".app");
  $$("[data-toggle-nav]").forEach(function (b) {
    b.addEventListener("click", function () { app.classList.toggle("nav-open"); });
  });
  if (app) {
    app.addEventListener("click", function (e) {
      if (e.target === app && app.classList.contains("nav-open")) app.classList.remove("nav-open");
    });
  }

  /* Flash messages: close button + auto dismiss */
  $$(".toast").forEach(function (t) {
    function close() { t.classList.add("is-leaving"); setTimeout(function () { t.remove(); }, 220); }
    var btn = $(".toast-close", t);
    if (btn) btn.addEventListener("click", close);
    setTimeout(close, t.classList.contains("toast--error") ? 9000 : 5000);
  });

  /* <form data-confirm="Are you sure?"> asks before submitting */
  document.addEventListener("submit", function (e) {
    var msg = e.target.getAttribute && e.target.getAttribute("data-confirm");
    if (msg && !window.confirm(msg)) e.preventDefault();
  });

  /* <select data-autosubmit> submits its form when changed */
  $$("select[data-autosubmit]").forEach(function (s) {
    s.addEventListener("change", function () { s.form.submit(); });
  });

  /* Donut chart: reads #summary-data (json_script) */
  var summaryEl = $("#summary-data");
  var STATUS = {
    planning: ["Planning", "#c5cedc"], active: ["Active", "#2a6bf2"], on_hold: ["On hold", "#f0a526"],
    completed: ["Completed", "#26b560"], cancelled: ["Cancelled", "#9aa6b8"]
  };
  function donut(host, items, unit) {
    var total = items.reduce(function (a, i) { return a + i.v; }, 0);
    var r = 42, c = 2 * Math.PI * r, off = 0;
    var svg = '<svg viewBox="0 0 100 100" class="donut" role="img" aria-label="' + unit + ' by status">' +
      '<circle cx="50" cy="50" r="' + r + '" fill="none" stroke="#edf0f5" stroke-width="12"/>';
    items.forEach(function (i) {
      if (!i.v) return;
      var len = i.v / total * c;
      svg += '<circle cx="50" cy="50" r="' + r + '" fill="none" stroke="' + i.c + '" stroke-width="12"' +
        ' stroke-dasharray="' + len + " " + (c - len) + '" stroke-dashoffset="' + (-off) + '" transform="rotate(-90 50 50)"/>';
      off += len;
    });
    svg += '<text x="50" y="49" text-anchor="middle" class="donut-n">' + total + '</text>' +
      '<text x="50" y="62" text-anchor="middle" class="donut-l">' + unit + '</text></svg>';
    host.innerHTML = svg;
    var legend = $(".donut-legend", host.parentNode);
    if (legend) {
      legend.innerHTML = items.map(function (i) {
        return '<li style="--sw:' + i.c + '">' + i.l + "<b>" + i.v + "</b></li>";
      }).join("");
    }
  }
  var donutHost = $("[data-donut-projects]");
  if (summaryEl && donutHost) {
    var data = JSON.parse(summaryEl.textContent);
    var items = Object.keys(STATUS).map(function (k) {
      return { l: STATUS[k][0], c: STATUS[k][1], v: (data.projects_by_status || {})[k] || 0 };
    });
    donut(donutHost, items, "projects");
  }

  /* Bar chart (yearly report) */
  var bars = $("[data-bars]");
  if (bars) {
    var months = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];
    var cols = $$(".col", bars);
    var max = Math.max.apply(null, cols.map(function (c) { return +c.getAttribute("data-v") || 0; }).concat([1]));
    cols.forEach(function (c, i) {
      var v = +c.getAttribute("data-v") || 0, fill = $(".fill", c);
      $(".lab", c).textContent = months[i] || c.getAttribute("data-m");
      fill.classList.toggle("is-zero", v === 0);
      requestAnimationFrame(function () { fill.style.setProperty("--h", Math.round(v / max * 100)); });
    });
  }

  /* Kanban: drag a card to another column to change its status */
  var tokenInput = $('input[name="csrfmiddlewaretoken"]');
  $$(".kcard[draggable]").forEach(function (card) {
    card.addEventListener("dragstart", function (e) {
      e.dataTransfer.setData("text/plain", card.getAttribute("data-id"));
      e.dataTransfer.effectAllowed = "move";
      card.classList.add("dragging");
    });
    card.addEventListener("dragend", function () { card.classList.remove("dragging"); });
  });
  function updateCounts() {
    $$(".kcol").forEach(function (col) {
      $(".kcol-head span", col).textContent = $$(".kcard", col).length;
    });
  }
  $$(".kcol").forEach(function (col) {
    col.addEventListener("dragover", function (e) { e.preventDefault(); col.classList.add("drop"); });
    col.addEventListener("dragleave", function (e) { if (!col.contains(e.relatedTarget)) col.classList.remove("drop"); });
    col.addEventListener("drop", function (e) {
      e.preventDefault();
      col.classList.remove("drop");
      var card = $('.kcard[data-id="' + e.dataTransfer.getData("text/plain") + '"]');
      if (!card || card.closest(".kcol") === col || !tokenInput) return;
      var body = new FormData();
      body.append("status", col.getAttribute("data-status"));
      body.append("csrfmiddlewaretoken", tokenInput.value);
      fetch(card.getAttribute("data-url"), { method: "POST", body: body, credentials: "same-origin" })
        .then(function (res) {
          if (!res.ok) throw new Error("failed");
          $(".kcol-body", col).prepend(card);
          var sel = $("select", card);
          if (sel) sel.value = col.getAttribute("data-status");
          updateCounts();
        })
        .catch(function () { window.location.reload(); });
    });
  });
})();
