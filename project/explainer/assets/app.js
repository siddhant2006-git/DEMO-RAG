/* ==========================================================================
   app.js — UI wiring for the TenderGuard architecture explainer.

   All content lives in data.js; all decision logic lives in engine.js (a
   faithful port of the Python). This file only renders and reacts.
   ========================================================================== */

(function () {
  'use strict';

  var D = window.TGData;
  var E = window.TGEngine;

  function $(sel, root) { return (root || document).querySelector(sel); }
  function $$(sel, root) { return Array.prototype.slice.call((root || document).querySelectorAll(sel)); }
  function el(tag, cls, html) {
    var n = document.createElement(tag);
    if (cls) n.className = cls;
    if (html !== undefined) n.innerHTML = html;
    return n;
  }
  function esc(s) {
    return String(s).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
  }
  function fmtINR(n) {
    if (n === null || n === undefined) return '—';
    if (typeof n !== 'number') return String(n);
    return n.toLocaleString('en-IN');
  }
  function chipFor(status) {
    var cls = status === 'PASS' ? 'pass' : (status === 'FAIL' ? 'fail' : 'review');
    return '<span class="chip ' + cls + '">' + status.replace('_', ' ') + '</span>';
  }

  /* ==================================================================== */
  /* Theme                                                                */
  /* ==================================================================== */

  var THEME_KEY = 'tenderguard.explainer.theme';

  function applyTheme(mode) {
    if (mode === 'system') document.documentElement.removeAttribute('data-theme');
    else document.documentElement.setAttribute('data-theme', mode);
    $$('#themer button').forEach(function (b) {
      b.setAttribute('aria-pressed', b.dataset.theme === mode ? 'true' : 'false');
    });
  }

  function initTheme() {
    var saved = 'system';
    try { saved = localStorage.getItem(THEME_KEY) || 'system'; } catch (e) { /* private mode */ }
    applyTheme(saved);
    $$('#themer button').forEach(function (b) {
      b.addEventListener('click', function () {
        applyTheme(b.dataset.theme);
        try { localStorage.setItem(THEME_KEY, b.dataset.theme); } catch (e) { /* ignore */ }
      });
    });
  }

  /* ==================================================================== */
  /* Reading progress + scroll spy                                        */
  /* ==================================================================== */

  function initProgress() {
    var bar = $('#progress');
    if (!bar) return;
    var ticking = false;
    function update() {
      var h = document.documentElement;
      var max = h.scrollHeight - h.clientHeight;
      bar.style.width = (max > 0 ? (h.scrollTop / max) * 100 : 0) + '%';
      ticking = false;
    }
    window.addEventListener('scroll', function () {
      if (!ticking) { ticking = true; window.requestAnimationFrame(update); }
    }, { passive: true });
    update();
  }

  function initSpy() {
    var links = $$('#rail a');
    var targets = links.map(function (a) { return $(a.getAttribute('href')); });
    if (!('IntersectionObserver' in window)) return;
    var io = new IntersectionObserver(function (entries) {
      entries.forEach(function (en) {
        if (!en.isIntersecting) return;
        var i = targets.indexOf(en.target);
        links.forEach(function (a, j) { a.classList.toggle('on', i === j); });
      });
    }, { rootMargin: '-10% 0px -75% 0px', threshold: 0 });
    targets.forEach(function (t) { if (t) io.observe(t); });
  }

  /* ==================================================================== */
  /* 03 — stage explorer                                                  */
  /* ==================================================================== */

  function initStages() {
    var bar = $('#stagebar'), main = $('#stageMain'), side = $('#stageSide');
    if (!bar) return;

    D.STAGES.forEach(function (s, i) {
      var b = el('button', 'stagebtn' + (s.llm ? ' llm' : ''), '<b>STAGE ' + s.n + '</b>' + s.key);
      b.type = 'button';
      b.setAttribute('role', 'tab');
      b.setAttribute('aria-controls', 'stagePanel');
      b.setAttribute('aria-selected', i === 0 ? 'true' : 'false');
      b.addEventListener('click', function () { show(i); });
      bar.appendChild(b);
    });

    function show(i) {
      var s = D.STAGES[i];
      $$('button', bar).forEach(function (c, j) { c.setAttribute('aria-selected', i === j ? 'true' : 'false'); });
      main.innerHTML =
        '<div class="path">' + s.path + '</div>' +
        '<h4>' + s.key + '</h4>' +
        '<dl class="io"><dt>In</dt><dd>' + s.inp + '</dd><dt>Out</dt><dd>' + s.out + '</dd></dl>' +
        '<p class="side-h">What happens</p><ul>' +
          s.does.map(function (d) { return '<li>' + d + '</li>'; }).join('') + '</ul>';
      side.innerHTML =
        '<p class="side-h">Why it is built this way</p>' +
        '<p class="side-why">' + s.why + '</p>' +
        '<p class="side-h">Files</p>' +
        '<div class="filelist">' + s.files.map(function (f) { return '<span>' + f + '</span>'; }).join('') + '</div>';
    }
    show(0);
  }

  /* ==================================================================== */
  /* 04 — trace + source_priority flip                                    */
  /* ==================================================================== */

  function initTrace() {
    var wrap = $('#trace');
    if (!wrap) return;

    D.TRACE.forEach(function (t, i) {
      var d = el('div', 'trace-step' + (i === 0 ? ' on' : ''));
      d.innerHTML =
        '<div class="n">' + ('0' + (i + 1)).slice(-2) + '</div><div>' +
        '<h5>' + t.h + '</h5><p>' + t.p + '</p>' +
        '<div class="quote">' + esc(t.q) + '</div>' +
        '<p style="margin:9px 0 0" class="val">' + t.k + '</p></div>';
      wrap.appendChild(d);
    });

    var idx = 0;
    var back = $('#traceBack'), next = $('#traceNext'), all = $('#traceAll');

    function render() {
      $$('.trace-step', wrap).forEach(function (c, i) { c.classList.toggle('on', i <= idx); });
      back.disabled = idx === 0;
      next.disabled = idx >= D.TRACE.length - 1;
    }
    next.addEventListener('click', function () {
      if (idx < D.TRACE.length - 1) {
        idx++; render();
        wrap.children[idx].scrollIntoView({ block: 'nearest', behavior: 'smooth' });
      }
    });
    back.addEventListener('click', function () { if (idx > 0) { idx--; render(); } });
    all.addEventListener('click', function () { idx = D.TRACE.length - 1; render(); });
    render();
  }

  function initSourcePriority() {
    var seg = $('#spSeg'), out = $('#spOut');
    if (!seg) return;

    function render(mode) {
      var gov = mode === 'gov';
      var actual = gov ? 41000000 : 62000000;
      // Run it through the real ported operator rather than asserting the answer.
      var passed = E.evaluate('gte', actual, 50000000);
      out.innerHTML =
        '<div class="quote">' + esc(
          'resolve  financials.avg_annual_turnover\n' +
          (gov
            ? '  1. government → verified  → 41000000   ✓ used\n  2. document   → claimed   → (not reached)'
            : '  1. document   → claimed   → 62000000   ✓ used\n  2. government → verified  → (not reached)') +
          '\n\nop_gte(' + actual + ', 50000000)  →  ' + (passed ? 'True' : 'False')
        ) + '</div>' +
        '<div class="verdict-box ' + (passed ? 'no' : 'ok') + '" style="margin-top:16px">' +
        '<div class="vtitle">' + (passed
          ? 'REQ-TURNOVER · PASS — and it should not have'
          : 'REQ-TURNOVER · FAIL — correctly') + '</div><p>' +
        (passed
          ? 'The engine trusted the vendor’s own document about the vendor. The overstatement sails through, and the whole system has just become an expensive PDF summarizer.'
          : 'The GST-verified 4.1 Cr is what got compared, not the claimed 6.2 Cr. The overstatement is caught, and both numbers are stored on the finding so an officer can see the gap.') +
        '</p></div>';
    }

    $$('button', seg).forEach(function (b) {
      b.addEventListener('click', function () {
        $$('button', seg).forEach(function (x) { x.setAttribute('aria-pressed', 'false'); });
        b.setAttribute('aria-pressed', 'true');
        render(b.dataset.v);
      });
    });
    render('gov');
  }

  /* ==================================================================== */
  /* 05 — annotated YAML                                                  */
  /* ==================================================================== */

  function initYaml() {
    var pre = $('#yaml'), note = $('#yamlNote');
    if (!pre) return;

    pre.innerHTML = D.YAML_SRC.map(function (line) {
      return line.map(function (tok) {
        var head = tok.charAt(0);
        if (head === '@') {
          var f = tok.slice(1);
          return '<button class="fld" type="button" data-f="' + f + '">' + f + '</button>';
        }
        if (head === '#') return '<span class="rid">' + esc(tok.slice(1)) + '</span>';
        if (head === '%') return '<span class="c">' + esc(tok.slice(1)) + '</span>';
        return esc(tok);
      }).join('');
    }).join('\n');

    function setNote(f) {
      $$('.fld', pre).forEach(function (b) { b.classList.toggle('on', b.dataset.f === f); });
      var n = D.FIELD_NOTES[f];
      if (n) note.innerHTML = '<b>' + n[0] + '</b>' + n[1];
    }
    pre.addEventListener('click', function (e) {
      var b = e.target.closest('.fld');
      if (b) setNote(b.dataset.f);
    });
    setNote('source_priority');
  }

  /* ==================================================================== */
  /* 06 — risk playground                                                 */
  /* ==================================================================== */

  function initRisk() {
    var host = $('#riskRules');
    if (!host) return;

    var pack = D.RULE_PACKS.goods;
    var state = {};
    pack.rules.forEach(function (r) { state[r.id] = 'PASS'; });
    var msme = false;

    var PRESETS = {
      clean:    {},
      demo:     { 'REQ-TURNOVER': 'FAIL' },
      debarred: { 'REQ-DEBARMENT': 'FAIL' },
      messy:    { 'REQ-TURNOVER': 'NEEDS_REVIEW', 'REQ-EXPERIENCE': 'NEEDS_REVIEW', 'REQ-PAN': 'NEEDS_REVIEW' }
    };

    pack.rules.forEach(function (r) {
      var row = el('div', 'rulerow');
      row.dataset.rid = r.id;
      row.innerHTML =
        '<div class="lbl"><b>' + r.id + '</b><span>' + r.label + '</span>' +
        '<span class="sevtag"> · ' + r.severity + ' · weight ' + r.weight + (r.applies_if ? ' · applies_if' : '') + '</span></div>' +
        '<span class="seg tri">' +
          ['PASS', 'NEEDS_REVIEW', 'FAIL'].map(function (v) {
            return '<button type="button" data-v="' + v + '" aria-pressed="' + (v === 'PASS') + '">' +
              (v === 'NEEDS_REVIEW' ? 'REVIEW' : v) + '</button>';
          }).join('') +
        '</span>';
      $('.seg', row).addEventListener('click', function (e) {
        var b = e.target.closest('button');
        if (!b) return;
        state[r.id] = b.dataset.v;
        syncRow(row);
        recompute();
      });
      host.appendChild(row);
    });

    function syncRow(row) {
      $$('.seg button', row).forEach(function (b) {
        b.setAttribute('aria-pressed', b.dataset.v === state[row.dataset.rid] ? 'true' : 'false');
      });
    }

    var msmeSeg = $('#msmeSeg');
    $$('button', msmeSeg).forEach(function (b) {
      b.addEventListener('click', function () {
        $$('button', msmeSeg).forEach(function (x) { x.setAttribute('aria-pressed', 'false'); });
        b.setAttribute('aria-pressed', 'true');
        msme = b.dataset.v === 'true';
        recompute();
      });
    });

    $$('[data-preset]').forEach(function (b) {
      b.addEventListener('click', function () {
        var p = PRESETS[b.dataset.preset];
        pack.rules.forEach(function (r) { state[r.id] = p[r.id] || 'PASS'; });
        $$('.rulerow', host).forEach(syncRow);
        recompute();
      });
    });

    var fillEl = $('#scoreFill'), scoreEl = $('#scoreVal'), bandEl = $('#bandChip'),
        mathEl = $('#riskMath'), flagEl = $('#blockerFlag');

    function recompute() {
      // Build findings in exactly the shape scorer.py consumes, then score
      // them with the ported scorer rather than re-deriving the arithmetic.
      var findings = [];
      pack.rules.forEach(function (r) {
        var skipped = !!r.applies_if && !msme;
        var row = $('[data-rid="' + r.id + '"]', host);
        row.classList.toggle('off', skipped);
        if (skipped) return;
        var s = state[r.id];
        findings.push({
          severity: r.severity, status: s, weight: r.weight,
          risk_contribution: s === 'PASS' ? 0 : (s === 'FAIL' ? r.weight : r.weight * 0.5)
        });
      });

      var risk = E.scoreFindings(findings);
      var col = risk.band === 'HIGH' ? 'var(--fail)' : (risk.band === 'MEDIUM' ? 'var(--review)' : 'var(--pass)');

      scoreEl.textContent = risk.score.toFixed(1);
      scoreEl.style.color = col;
      fillEl.style.width = Math.min(100, risk.score) + '%';
      fillEl.style.background = col;
      bandEl.textContent = risk.band + ' risk';
      bandEl.className = 'chip ' + (risk.band === 'HIGH' ? 'fail' : (risk.band === 'MEDIUM' ? 'review' : 'pass'));

      mathEl.innerHTML =
        'Σ risk_contribution = ' + risk.total_risk + '<br>' +
        'Σ weight&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;= ' + risk.total_weight +
          (msme ? '' : '  (MSME skipped)') + '<br>' +
        'raw score&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;= ' + risk.raw_score + '<br><br>' +
        risk.pass_count + ' pass · ' + risk.fail_count + ' fail · ' + risk.needs_review_count + ' review';

      flagEl.innerHTML = risk.forced_by_blocker
        ? '<div class="blocker-flag">BLOCKER OVERRIDE<br>A BLOCKER-severity rule failed. Band forced to HIGH and the score floored at 66, whatever the arithmetic said (' + risk.raw_score + ').</div>'
        : '';
    }
    recompute();
  }

  /* ==================================================================== */
  /* 07 — snippet guard + amount normalizer                               */
  /* ==================================================================== */

  function initGuard() {
    var pageEl = $('#pageText'), optsEl = $('#snipOpts'), outEl = $('#guardOut');
    if (!pageEl) return;
    pageEl.textContent = D.PAGE_TEXT;

    D.SNIPPETS.forEach(function (s, i) {
      var b = el('button', 'snip-opt');
      b.type = 'button';
      b.setAttribute('aria-pressed', i === 0 ? 'true' : 'false');
      b.textContent = '"' + s.t + '"';
      b.addEventListener('click', function () {
        $$('button', optsEl).forEach(function (x) { x.setAttribute('aria-pressed', 'false'); });
        b.setAttribute('aria-pressed', 'true');
        show(i);
      });
      optsEl.appendChild(b);
    });

    function show(i) {
      var s = D.SNIPPETS[i];
      var ok = E.isSnippetGrounded(s.t, D.PAGE_TEXT);
      outEl.className = 'verdict-box ' + (ok ? 'ok' : 'no');
      outEl.innerHTML =
        '<div class="vtitle">' + (ok ? '✓ grounded — kept' : '✕ not grounded — discarded') + '</div>' +
        '<p class="mono" style="font-size:11.5px;margin-bottom:8px">is_snippet_grounded(...) → ' + (ok ? 'True' : 'False') + '</p>' +
        '<p>' + s.why + '</p>';
    }
    show(0);
  }

  function initNormalizer() {
    var input = $('#amtInput'), outEl = $('#amtOut'), chips = $('#amtSamples');
    if (!input) return;

    function run() {
      var raw = input.value;
      var v = E.normalizeAmount(raw);
      if (v === null) {
        outEl.className = 'verdict-box no';
        outEl.innerHTML =
          '<div class="vtitle">✕ unparseable — value is None</div>' +
          '<p class="mono" style="font-size:11.5px;margin-bottom:8px">normalize_amount(' + esc(JSON.stringify(raw)) + ') → None</p>' +
          '<p>The fact is stored with <span class="k">value: null</span>, and <span class="k">_build_claimed</span> skips it — so the rule that needed it reports NEEDS_REVIEW rather than comparing against a guess.</p>';
      } else {
        outEl.className = 'verdict-box ok';
        outEl.innerHTML =
          '<div class="vtitle">✓ parsed</div>' +
          '<p class="mono" style="font-size:11.5px;margin-bottom:8px">normalize_amount(' + esc(JSON.stringify(raw)) + ') → ' + v + '</p>' +
          '<p>Stored as <span class="k">₹' + fmtINR(v) + '</span> — a float, at this one boundary. Nothing downstream ever sees the original string.</p>';
      }
    }

    D.AMOUNT_SAMPLES.forEach(function (sample) {
      var b = el('button', 'btn');
      b.type = 'button';
      b.style.textTransform = 'none';
      b.textContent = sample;
      b.addEventListener('click', function () { input.value = sample; run(); });
      chips.appendChild(b);
    });

    input.addEventListener('input', run);
    input.value = D.AMOUNT_SAMPLES[0];
    run();
  }

  /* ==================================================================== */
  /* 08 — the bench: a live run of the ported engine                      */
  /* ==================================================================== */

  /* Mirrors services/verification/adapters/mock_portal.py. Each returns an
     outcome with a status and a normalized dict — never a verdict. */
  function mockGst(gstin, forced) {
    if (forced === 'DOWN') return { portal: 'GST', status: 'DOWN', normalized: {} };
    var rec = D.MOCK_GST[gstin];
    if (!rec) return { portal: 'GST', status: 'NOT_FOUND', normalized: {} };
    return { portal: 'GST', status: 'UP', normalized: {
      'gst.status': rec.status,
      'gst.legal_name': rec.legal_name,
      'financials.avg_annual_turnover': rec.avg_annual_turnover
    } };
  }
  function mockUdyam(num) {
    var rec = D.MOCK_UDYAM[num];
    if (!rec) return { portal: 'UDYAM', status: 'NOT_FOUND', normalized: {} };
    return { portal: 'UDYAM', status: 'UP', normalized: {
      'udyam.valid': rec.valid, 'udyam.category': rec.category
    } };
  }
  function mockDebarment(gstin, pan) {
    // Note: this adapter always reaches a conclusion, so it is always UP.
    var listed = D.MOCK_DEBARMENT.listed_gstins.indexOf(gstin) !== -1 ||
                 D.MOCK_DEBARMENT.listed_pans.indexOf(pan) !== -1;
    return { portal: 'DEBARMENT', status: 'UP', normalized: { 'debarment.listed': listed } };
  }

  function initBench() {
    var root = $('#bench');
    if (!root) return;

    var ui = {
      pack: $('#bPack'), vendor: $('#bVendor'),
      turnover: $('#bTurnover'), years: $('#bYears'), similar: $('#bSimilar'), pan: $('#bPan'),
      emd: $('#bEmd'), iso: $('#bIso'), msme: $('#bMsme'), conflict: $('#bConflict'),
      tTurnover: $('#bTTurnover'), tYears: $('#bTYears'), tSimilar: $('#bTSimilar'),
      vendorNote: $('#bVendorNote'), out: $('#benchOut')
    };

    D.VENDORS.forEach(function (v) {
      var o = el('option');
      o.value = v.key; o.textContent = v.label;
      ui.vendor.appendChild(o);
    });

    function currentVendor() {
      return D.VENDORS.filter(function (v) { return v.key === ui.vendor.value; })[0] || D.VENDORS[0];
    }

    function boolOf(seg) { return $('button[aria-pressed="true"]', seg).dataset.v === 'true'; }

    $$('.seg', root).forEach(function (seg) {
      seg.addEventListener('click', function (e) {
        var b = e.target.closest('button');
        if (!b) return;
        $$('button', seg).forEach(function (x) { x.setAttribute('aria-pressed', 'false'); });
        b.setAttribute('aria-pressed', 'true');
        run();
      });
    });

    /* ---- build the engine's three arguments, the way service.py does ---- */

    function buildClaimed() {
      var claimed = {};
      function put(key, value, snippet, conflicts) {
        // Mirrors _build_claimed: a fact whose normalized value is None is
        // skipped entirely, not stored as null.
        if (value === null || value === undefined) return;
        claimed[key] = E.FactValue(value, { page: 2, snippet: snippet }, conflicts);
      }

      var conflicted = ui.conflict && boolOf(ui.conflict);
      function conflictsFor(value, page1Snippet, page2Snippet) {
        if (!conflicted || value === null) return [];
        return [
          { value: value, page: 2, snippet: page1Snippet },
          { value: value / 2, page: 5, snippet: page2Snippet }
        ];
      }

      var turnoverRaw = ui.turnover.value;
      var turnover = E.normalizeAmount(turnoverRaw);
      var years = E.normalizeYears(ui.years.value);

      put('financials.avg_annual_turnover', turnover, turnoverRaw,
        conflictsFor(turnover, turnoverRaw, 'Annexure C restates turnover as a different figure'));
      put('experience.years', years, ui.years.value,
        conflictsFor(years, ui.years.value, 'Annexure A states a different number of years'));
      put('experience.similar_work_value', E.normalizeAmount(ui.similar.value), ui.similar.value);
      put('financials.emd_submitted', boolOf(ui.emd), 'EMD receipt enclosed');
      put('certification.iso_certified', boolOf(ui.iso), 'ISO certification statement');
      put('identity.pan', E.normalizePan(ui.pan.value), ui.pan.value);
      return claimed;
    }

    function buildVerified(vendor) {
      // Mirrors _build_verified: only an UP result contributes facts.
      var verified = {}, log = [];
      var outcomes = [];
      if (vendor.gstin) {
        outcomes.push(mockGst(vendor.gstin, vendor.portal));
        outcomes.push(mockDebarment(vendor.gstin, vendor.pan));
      }
      if (vendor.udyam) outcomes.push(mockUdyam(vendor.udyam));

      outcomes.forEach(function (o) {
        log.push(o.portal + ' → ' + o.status);
        if (o.status !== 'UP') return;
        Object.keys(o.normalized).forEach(function (k) {
          verified[k] = E.FactValue(o.normalized[k], { portal: o.portal });
        });
      });
      return { verified: verified, log: log };
    }

    function buildContext() {
      // A blank threshold means the key is absent — which is exactly what an
      // un-extracted tender requirement looks like to the engine.
      var ctx = { 'bid.claims_msme_benefit': boolOf(ui.msme) };
      var t1 = E.normalizeAmount(ui.tTurnover.value);
      var t2 = E.normalizeYears(ui.tYears.value);
      var t3 = E.normalizeAmount(ui.tSimilar.value);
      if (t1 !== null) ctx['tender.turnover_requirement'] = t1;
      if (t2 !== null) ctx['tender.experience_requirement'] = t2;
      if (t3 !== null) ctx['tender.similar_work_value_requirement'] = t3;
      return ctx;
    }

    /* ---- which bucket actually decided this finding ---- */
    function usedSource(f, claimed, verified) {
      var priority = f.source_priority || ['document'];
      for (var i = 0; i < priority.length; i++) {
        var isDoc = priority[i] === 'document';
        var bucket = isDoc ? claimed : verified;
        if (bucket[factKeyOf(f)] !== undefined) return isDoc ? 'claimed' : 'verified';
      }
      return null;
    }
    function factKeyOf(f) {
      var pack = D.RULE_PACKS[ui.pack.value];
      var rule = pack.rules.filter(function (r) { return r.id === f.rule_id; })[0];
      return rule ? rule.fact : '';
    }

    /* ---- render ---- */

    function run() {
      var pack = D.RULE_PACKS[ui.pack.value];
      var vendor = currentVendor();
      ui.vendorNote.textContent = vendor.note;

      var claimed = buildClaimed();
      var v = buildVerified(vendor);
      var context = buildContext();

      var findings = E.evaluateRulePack(pack, claimed, v.verified, context);
      var risk = E.scoreFindings(findings);

      var rows = findings.map(function (f) {
        var used = usedSource(f, claimed, v.verified);
        var expected = f.expected.value;
        var claimedVal = f.claimed ? f.claimed.value : null;
        var verifiedVal = f.verified ? f.verified.value : null;

        function cell(label, val, isUsed, present) {
          if (!present) return '<i>' + label + ' —</i>';
          var cls = isUsed ? 'used' : 'unused';
          return '<i>' + label + '</i> <span class="' + cls + '">' + esc(displayVal(val)) + '</span>';
        }

        return '<tr class="r-' + f.status + '">' +
          '<td><span class="rid">' + f.rule_id + '</span>' +
             '<span class="rlabel">' + f.label + '</span></td>' +
          '<td>' + chipFor(f.status) +
             '<div class="sevtag" style="margin-top:6px">' + f.severity + '</div></td>' +
          '<td class="cmp">' +
             '<i>needs</i> ' + esc(displayVal(expected)) + '<br>' +
             cell('claimed', claimedVal, used === 'claimed', !!f.claimed) + '<br>' +
             cell('govt', verifiedVal, used === 'verified', !!f.verified) +
          '</td>' +
          '<td><div class="reason">' + esc(f.reason) + '</div>' +
             (f.status !== 'PASS'
               ? '<div class="evidence">evidence · ' +
                 (f.claimed && f.claimed.source && f.claimed.source.page
                   ? 'bid.pdf page ' + f.claimed.source.page + ' · "' + esc(String(f.claimed.source.snippet || '').slice(0, 48)) + '"'
                   : 'no bid page for this fact — falls back to the tender page, then page 1') +
                 '</div>'
               : '') +
          '</td>' +
          '<td class="num">' + f.weight + '<br><span class="sevtag">+' + f.risk_contribution + '</span></td>' +
        '</tr>';
      }).join('');

      var skipped = pack.rules.length - findings.length;

      ui.out.innerHTML =
        '<div class="summary">' +
          '<div class="s-score"><b>' + risk.score.toFixed(1) + '</b><span>risk score</span></div>' +
          '<div><b>' + risk.band + '</b><span>band</span></div>' +
          '<div class="s-pass"><b>' + risk.pass_count + '</b><span>pass</span></div>' +
          '<div class="s-fail"><b>' + risk.fail_count + '</b><span>fail</span></div>' +
          '<div class="s-review"><b>' + risk.needs_review_count + '</b><span>review</span></div>' +
        '</div>' +
        (risk.forced_by_blocker
          ? '<div class="blocker-flag" style="margin:0 0 18px">BLOCKER OVERRIDE — band forced to HIGH, score floored at 66 (arithmetic said ' + risk.raw_score + ').</div>'
          : '') +
        '<div class="scroller"><table class="matrix">' +
          '<thead><tr><th>Rule</th><th>Verdict</th><th>Compared</th><th>Reason</th><th style="text-align:right">Wt</th></tr></thead>' +
          '<tbody>' + rows + '</tbody></table></div>' +
        (skipped > 0
          ? '<p class="sevtag" style="margin-top:14px">' + skipped + ' rule' + (skipped > 1 ? 's' : '') +
            ' skipped by applies_if — no finding produced, and the weight left the denominator.</p>'
          : '') +
        '<details class="dicts"><summary>What the engine actually received</summary>' +
          '<div class="quote">' + esc(
            'rule pack : ' + pack.name + '  (' + pack.file + ')\n' +
            'engine    : ' + E.ENGINE_VERSION + '\n\n' +
            'portals   : ' + v.log.join('  ·  ') + '\n\n' +
            'claimed   = ' + dumpFacts(claimed) + '\n\n' +
            'verified  = ' + dumpFacts(v.verified) + '\n\n' +
            'context   = ' + JSON.stringify(context, null, 2)
          ) + '</div></details>';
    }

    function displayVal(v) {
      if (v === null || v === undefined) return 'None';
      if (typeof v === 'boolean') return v ? 'true' : 'false';
      if (typeof v === 'number') return v >= 100000 ? '₹' + fmtINR(v) : String(v);
      return String(v);
    }

    function dumpFacts(bucket) {
      var keys = Object.keys(bucket);
      if (!keys.length) return '{}   ← empty: no facts reached the engine from this source';
      return '{\n' + keys.map(function (k) {
        var f = bucket[k];
        var src = f.detail.portal ? 'portal=' + f.detail.portal : 'page=' + f.detail.page;
        return '  "' + k + '": ' + JSON.stringify(f.value) + '   (' + src +
          (f.conflicts && f.conflicts.length ? ', ' + f.conflicts.length + ' CONFLICTS' : '') + ')';
      }).join('\n') + '\n}';
    }

    $$('input[type="text"], select', root).forEach(function (n) {
      n.addEventListener('input', run);
      n.addEventListener('change', run);
    });

    /* Presets write every field, so switching between them never leaves a
       stale value behind from whatever was edited before. */
    var BENCH_PRESETS = {
      demo:        { pack: 'goods',    vendor: 'ganga' },
      clean:       { pack: 'goods',    vendor: 'bharat',   turnover: '9.2 Cr', years: '12 years' },
      debarred:    { pack: 'goods',    vendor: 'southern', turnover: '8 Cr',   years: '10 years' },
      nothreshold: { pack: 'goods',    vendor: 'ganga',    tTurnover: '', tYears: '', tSimilar: '' },
      works:       { pack: 'works',    vendor: 'ganga' }
    };
    var BENCH_DEFAULTS = {
      pack: 'goods', vendor: 'ganga',
      turnover: 'Rs. 6,20,00,000', years: '8 years', similar: '3 Cr', pan: 'AAAPL1234C',
      tTurnover: '5 Crore', tYears: '5', tSimilar: '4 Crore',
      emd: 'true', iso: 'true', msme: 'false', conflict: 'false'
    };

    function setSeg(seg, v) {
      $$('button', seg).forEach(function (x) {
        x.setAttribute('aria-pressed', x.dataset.v === v ? 'true' : 'false');
      });
    }

    $$('[data-bench-preset]').forEach(function (b) {
      b.addEventListener('click', function () {
        var cfg = {};
        Object.keys(BENCH_DEFAULTS).forEach(function (k) { cfg[k] = BENCH_DEFAULTS[k]; });
        var p = BENCH_PRESETS[b.dataset.benchPreset] || {};
        Object.keys(p).forEach(function (k) { cfg[k] = p[k]; });

        ['pack', 'vendor', 'turnover', 'years', 'similar', 'pan', 'tTurnover', 'tYears', 'tSimilar']
          .forEach(function (k) { ui[k].value = cfg[k]; });
        ['emd', 'iso', 'msme', 'conflict'].forEach(function (k) { setSeg(ui[k], cfg[k]); });

        run();
      });
    });

    run();
  }

  /* ==================================================================== */

  function boot() {
    initTheme();
    initProgress();
    initSpy();
    initStages();
    initTrace();
    initSourcePriority();
    initYaml();
    initRisk();
    initGuard();
    initNormalizer();
    initBench();
  }

  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', boot);
  else boot();
})();
