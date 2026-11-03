/* C6A 提交数据仪表盘 - 交互逻辑
 * 数据来自 assets/data.js（构建脚本生成），全部本地渲染，无网络请求。
 */
(function () {
  var D = window.C6A_DATA;
  if (!D) {
    document.body.innerHTML = '<div class="wrap"><h1>数据缺失</h1><p>未找到 assets/data.js，请先运行 build_dataset.py 生成数据。</p></div>';
    return;
  }
  var $ = function (s) { return document.querySelector(s); };
  var esc = function (v) {
    return String(v === null || v === undefined ? "" : v)
      .replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;");
  };
  var STATUS_TEXT = { checked: "已审核", needs_revision: "需返工", pending: "待处理" };
  var LOCAL_TEXT = { complete: "齐全", partial: "缺失", empty: "零命中", not_scanned: "未扫描" };

  function statusTag(s) {
    if (!s) return '<span class="tag mute">无状态</span>';
    if (s === "checked") return '<span class="tag ok">已审核</span>';
    if (s === "needs_revision") return '<span class="tag err">需返工</span>';
    return '<span class="tag warn">' + esc(STATUS_TEXT[s] || s) + "</span>";
  }
  function localTag(st, ratio) {
    if (st === "complete") return '<span class="tag ok">齐全 ' + Math.round(ratio * 100) + "%</span>";
    if (st === "partial") return '<span class="tag warn">缺失 ' + Math.round(ratio * 100) + "%</span>";
    if (st === "empty") return '<span class="tag err">零命中</span>';
    return '<span class="tag mute">未扫描</span>';
  }
  var fmtDate = function (s) { return s ? String(s).replace("T", " ").replace(/\.\d+Z$/, " UTC") : "—"; };

  /* ---------- 总览 ---------- */
  function renderKpis() {
    var m = D.meta.metrics;
    var items = [
      { l: "挑战总数", v: m.challenges_total, s: "已发布可识别代号", c: "info" },
      { l: "已提交", v: m.submitted, s: "占比 " + m.coverage_pct + "%", c: "ok" },
      { l: "未提交", v: m.not_submitted, s: "需新增交付物", c: "warn" },
      { l: "待评审", v: m.pending_review, s: "已 checked，等教师终审", c: "info" },
      { l: "需返工", v: m.needs_revision, s: "needs_revision，不会自动通过", c: m.needs_revision ? "err" : "ok" },
      { l: "扫描文件", v: m.scanned_files, s: "本地可识别交付物文件", c: "info" }
    ];
    $("#kpis").innerHTML = items.map(function (i) {
      return '<div class="kpi ' + i.c + '"><div class="label">' + esc(i.l) + '</div><div class="value">' +
        esc(i.v) + '</div><div class="sub">' + esc(i.s) + "</div></div>";
    }).join("");
  }

  function renderBars() {
    var tl = D.timeline || [];
    if (!tl.length) { $("#bars").innerHTML = '<div class="hint">无时间线数据</div>'; return; }
    var max = Math.max.apply(null, tl.map(function (x) { return x.count; }));
    $("#bars").innerHTML = tl.map(function (x) {
      var h = Math.max(6, Math.round((x.count / max) * 130));
      return '<div class="col" title="' + esc(x.date) + "：" + x.count + ' 次">' +
        '<div class="c">' + x.count + '</div>' +
        '<div class="bar" style="height:' + h + 'px"></div>' +
        '<div class="d">' + esc(x.date.slice(5)) + "</div></div>";
    }).join("");
  }

  function renderInsights() {
    $("#insights").innerHTML = (D.insights || []).map(function (i) {
      return '<div class="ins ' + esc(i.level) + '"><div class="t">' + esc(i.title) +
        '</div><div class="b">' + esc(i.body) + "</div></div>";
    }).join("");
  }

  /* ---------- 挑战清单 ---------- */
  var state = { q: "", submit: "", status: "" };

  function filteredChallenges() {
    var q = state.q.trim().toLowerCase();
    return D.challenges.filter(function (c) {
      if (state.submit === "yes" && !c.submitted) return false;
      if (state.submit === "no" && c.submitted) return false;
      if (state.status === "none" && c.status) return false;
      if (state.status && state.status !== "none" && c.status !== state.status) return false;
      if (q) {
        var hay = (c.code + " " + c.title + " " + (c.submission_id || "")).toLowerCase();
        if (hay.indexOf(q) < 0) return false;
      }
      return true;
    });
  }

  function renderChallenges() {
    var rows = filteredChallenges();
    $("#cntChal").textContent = "共 " + rows.length + " / " + D.challenges.length + " 条";
    $("#tbChal").innerHTML = rows.map(function (c, i) {
      return '<tr data-code="' + esc(c.code) + '">' +
        '<td class="code">' + esc(c.code) + "</td>" +
        "<td>" + esc(c.title) + "</td>" +
        "<td>" + esc(c.deadline ? String(c.deadline).slice(0, 10) : "—") + "</td>" +
        "<td>" + (c.submitted ? '<span class="tag info">已提交</span>' : '<span class="tag mute">未提交</span>') + "</td>" +
        "<td>" + statusTag(c.status) + "</td>" +
        "<td>" + localTag(c.local_check.status, c.local_check.ratio || 0) + "</td>" +
        "<td>" + esc(fmtDate(c.submitted_at)) + "</td></tr>";
    }).join("") || '<tr><td colspan="7" style="color:var(--muted)">无匹配记录</td></tr>';
  }

  /* ---------- 交付物校验 ---------- */
  function renderCoverage() {
    var rows = D.challenges.filter(function (c) {
      return c.local_check.status !== "not_scanned" || c.submitted;
    });
    $("#tbCov").innerHTML = rows.map(function (c) {
      var lc = c.local_check;
      var req = (c.required || []).join(" / ") || "（平台未定义）";
      return "<tr><td class='code'>" + esc(c.code) + "</td><td>" + esc(req) + "</td>" +
        "<td>" + (lc.present.length ? '<div class="chiplist">' + lc.present.map(function (p) {
          return '<span class="tag ok">' + esc(p) + "</span>";
        }).join("") + "</div>" : '<span class="tag mute">—</span>') + "</td>" +
        "<td>" + (lc.missing.length ? '<div class=\"chiplist\">' + lc.missing.map(function (p) {
          return '<span class="tag err">' + esc(p) + "</span>";
        }).join("") + "</div>" : '<span class="tag ok">无缺失</span>') + "</td>" +
        "<td>" + (lc.ratio === null ? '<span class="tag mute">未扫描</span>' :
          (lc.ratio >= 1 ? '<span class="tag ok">' : '<span class="tag warn">') + Math.round(lc.ratio * 100) + "%</span>") + "</td>" +
        "<td>" + lc.file_count + "</td></tr>";
    }).join("");
  }

  /* ---------- 时间线 ---------- */
  function renderSubs() {
    var rows = (D.submissions || []).slice().sort(function (a, b) {
      return String(b.submitted_at || "").localeCompare(String(a.submitted_at || ""));
    });
    $("#tbSubs").innerHTML = rows.map(function (s) {
      return "<tr><td>" + esc(fmtDate(s.submitted_at)) + "</td>" +
        '<td class="code">' + esc(s.code || "—") + "</td>" +
        "<td>" + esc(s.project_title || s.challenge_title || "—") + "</td>" +
        "<td>" + statusTag(s.status) + "</td>" +
        "<td>" + (s.task_state ? esc(s.task_state) : '<span class="tag mute">空</span>') + "</td>" +
        "<td>" + (s.repo ? '<a href="' + esc(s.repo) + '" target="_blank" rel="noopener" style="color:#7dd3fc">' + esc(s.repo.replace("https://github.com/", "")) + "</a>" : "—") + "</td></tr>";
    }).join("");
  }

  /* ---------- 详情抽屉 ---------- */
  function openDrawer(code) {
    var c = D.challenges.filter(function (x) { return x.code === code; })[0];
    if (!c) return;
    var lc = c.local_check;
    var html = "<h3>" + esc(c.code) + " · " + esc(c.title) + "</h3>" +
      '<div class="hint">' + esc(c.challenge_id) + "</div><dl>" +
      "<dt>截止时间</dt><dd>" + esc(c.deadline || "—") + "</dd>" +
      "<dt>是否提交</dt><dd>" + (c.submitted ? "已提交" : "未提交") + "</dd>" +
      "<dt>提交编号</dt><dd>" + esc(c.submission_id || "—") + "</dd>" +
      "<dt>平台状态</dt><dd>" + esc(c.status || "—") + "</dd>" +
      "<dt>提交时间</dt><dd>" + esc(fmtDate(c.submitted_at)) + "</dd>" +
      "<dt>要求项</dt><dd>" + esc((c.required || []).join(" / ") || "—") + "</dd>" +
      "<dt>本地命中</dt><dd>" + esc(lc.present.join(" / ") || "—") + "</dd>" +
      "<dt>本地缺失</dt><dd>" + esc(lc.missing.join(" / ") || "无") + "</dd>" +
      "<dt>文件数</dt><dd>" + lc.file_count + "</dd></dl>";
    $("#drawerBody").innerHTML = html;
    $("#drawer").classList.add("open");
    $("#mask").classList.add("on");
  }
  function closeDrawer() {
    $("#drawer").classList.remove("open");
    $("#mask").classList.remove("on");
  }

  /* ---------- 导出 ---------- */
  function exportCsv() {
    var rows = filteredChallenges();
    var head = ["代号", "挑战", "挑战ID", "截止", "已提交", "提交编号", "平台状态", "本地校验", "命中率", "缺失项"];
    var lines = [head.join(",")];
    rows.forEach(function (c) {
      var lc = c.local_check;
      var cells = [c.code, c.title, c.challenge_id, c.deadline || "", c.submitted ? "是" : "否",
        c.submission_id || "", c.status || "", LOCAL_TEXT[lc.status] || lc.status,
        lc.ratio === null ? "" : lc.ratio, lc.missing.join(" / ")];
      lines.push(cells.map(function (v) {
        var s = String(v === null || v === undefined ? "" : v);
        return /[",\n]/.test(s) ? '"' + s.replace(/"/g, '""') + '"' : s;
      }).join(","));
    });
    var blob = new Blob(["\ufeff" + lines.join("\r\n")], { type: "text/csv;charset=utf-8" });
    var a = document.createElement("a");
    a.href = URL.createObjectURL(blob);
    a.download = "C6A_挑战提交筛选结果_" + new Date().toISOString().slice(0, 10) + ".csv";
    document.body.appendChild(a); a.click(); document.body.removeChild(a);
    setTimeout(function () { URL.revokeObjectURL(a.href); }, 1500);
  }

  /* ---------- 事件与初始化 ---------- */
  var VIEWS = ["overview", "challenges", "coverage", "timeline", "dict"];
  function activateView(name) {
    if (VIEWS.indexOf(name) < 0) name = "overview";
    document.querySelectorAll("#tabs button").forEach(function (x) {
      x.classList.toggle("on", x.dataset.view === name);
    });
    VIEWS.forEach(function (v) { $("#view-" + v).classList.toggle("hide", v !== name); });
  }
  function viewFromHash() {
    var m = /(?:^#|&)view=([a-z]+)/.exec(location.hash || "");
    return m ? m[1] : "overview";
  }

  function bind() {
    document.querySelectorAll("#tabs button").forEach(function (b) {
      b.addEventListener("click", function () {
        activateView(b.dataset.view);
        try { history.replaceState(null, "", "#view=" + b.dataset.view); } catch (e) { location.hash = "view=" + b.dataset.view; }
      });
    });
    $("#qText").addEventListener("input", function (e) { state.q = e.target.value; renderChallenges(); });
    $("#fSubmit").addEventListener("change", function (e) { state.submit = e.target.value; renderChallenges(); });
    $("#fStatus").addEventListener("change", function (e) { state.status = e.target.value; renderChallenges(); });
    $("#tbChal").addEventListener("click", function (e) {
      var tr = e.target.closest("tr");
      if (tr && tr.dataset.code) openDrawer(tr.dataset.code);
    });
    $("#btnClose").addEventListener("click", closeDrawer);
    $("#mask").addEventListener("click", closeDrawer);
    document.addEventListener("keydown", function (e) { if (e.key === "Escape") closeDrawer(); });
    $("#btnExport").addEventListener("click", exportCsv);
    $("#btnRefreshNote").addEventListener("click", function () {
      document.querySelector('#tabs button[data-view="dict"]').click();
    });
  }

  var at = D.meta.generated_at;
  $("#genAt").textContent = at;
  $("#genAt2").textContent = at;
  renderKpis(); renderBars(); renderInsights();
  renderChallenges(); renderCoverage(); renderSubs();
  activateView(viewFromHash());
  bind();
})();
