/* ==========================================================================
   engine.js — a teaching port of TenderGuard's decision layer.

   This is a line-for-line JavaScript translation of three Python files, so
   the explainer's live bench produces the same verdicts the real system does:

     backend/app/services/rules/operators.py   -> OPERATORS, evaluate()
     backend/app/services/rules/condition.py   -> evaluateCondition()
     backend/app/services/rules/engine.py      -> evaluateRulePack()
     backend/app/services/risk/scorer.py       -> scoreFindings()
     backend/app/services/extraction/normalizers.py -> normalizeAmount(), etc.

   It is a PORT, not the engine. The real one runs in Python on the server and
   is the only thing that ever writes a Finding row. If the two ever disagree,
   the Python is right and this file is stale — every behaviour here is
   annotated with the Python it mirrors so the drift is easy to spot.

   Like the original, nothing in this file calls a model, touches storage, or
   reads a clock. Same inputs, same findings.
   ========================================================================== */

(function (global) {
  'use strict';

  /* ------------------------------------------------------------------ */
  /* operators.py                                                        */
  /* ------------------------------------------------------------------ */

  function asDate(value) {
    if (value instanceof Date) return value;
    var d = new Date(String(value));
    if (isNaN(d.getTime())) throw new TypeError("Invalid date: " + value);
    return d;
  }

  function num(v) {
    var n = Number(v);
    // Mirrors Python float() raising on non-numeric input rather than
    // silently producing NaN and comparing false.
    if (typeof v === 'boolean' || v === null || v === '' || isNaN(n)) {
      throw new TypeError("could not convert to float: " + JSON.stringify(v));
    }
    return n;
  }

  var OPERATORS = {
    gte: function (a, e) { return a !== null && a !== undefined && num(a) >= num(e); },
    lte: function (a, e) { return a !== null && a !== undefined && num(a) <= num(e); },
    gt:  function (a, e) { return a !== null && a !== undefined && num(a) >  num(e); },
    lt:  function (a, e) { return a !== null && a !== undefined && num(a) <  num(e); },
    eq:  function (a, e) { return a === e; },
    in:  function (a, e) { return Array.isArray(e) ? e.indexOf(a) !== -1 : String(e).indexOf(String(a)) !== -1; },
    regex: function (a, e) {
      return a !== null && a !== undefined && new RegExp(String(e)).test(String(a));
    },
    date_before: function (a, e) { return a !== null && a !== undefined && asDate(a) < asDate(e); },
    date_after:  function (a, e) { return a !== null && a !== undefined && asDate(a) > asDate(e); },
    exists: function (a) { return a !== null && a !== undefined; }
  };

  function evaluate(operator, actual, expected) {
    if (!Object.prototype.hasOwnProperty.call(OPERATORS, operator)) {
      throw new Error("Unknown operator '" + operator + "'. Known: " + Object.keys(OPERATORS).sort().join(', '));
    }
    return OPERATORS[operator](actual, expected);
  }

  /* ------------------------------------------------------------------ */
  /* condition.py — deliberately not eval()                              */
  /* ------------------------------------------------------------------ */

  var CONDITION_RE = /^\s*([\w.]+)\s*(==|!=|>=|<=|>|<)\s*(.+?)\s*$/;

  var COND_OPS = {
    '==': function (a, b) { return a === b; },
    '!=': function (a, b) { return a !== b; },
    '>=': function (a, b) { return a !== null && a !== undefined && num(a) >= num(b); },
    '<=': function (a, b) { return a !== null && a !== undefined && num(a) <= num(b); },
    '>':  function (a, b) { return a !== null && a !== undefined && num(a) >  num(b); },
    '<':  function (a, b) { return a !== null && a !== undefined && num(a) <  num(b); }
  };

  function parseLiteral(token) {
    token = String(token).trim();
    if (token.toLowerCase() === 'true') return true;
    if (token.toLowerCase() === 'false') return false;
    if (/^['"].*['"]$/.test(token)) return token.slice(1, -1);
    if (/^-?\d+$/.test(token)) return parseInt(token, 10);
    if (/^-?\d*\.\d+$/.test(token)) return parseFloat(token);
    return token;
  }

  function evaluateCondition(expression, context) {
    var m = CONDITION_RE.exec(expression);
    if (!m) throw new Error("Unsupported condition expression: " + JSON.stringify(expression));
    var path = m[1], op = m[2], literal = m[3];
    var actual = Object.prototype.hasOwnProperty.call(context, path) ? context[path] : undefined;
    return COND_OPS[op](actual, parseLiteral(literal));
  }

  /* ------------------------------------------------------------------ */
  /* engine.py                                                           */
  /* ------------------------------------------------------------------ */

  // "government" facts live in `verified`, "document" facts live in `claimed`.
  // This is the vocabulary rule packs use in source_priority.
  var SOURCE_TO_BUCKET = { government: 'verified', document: 'claimed' };

  var ENGINE_VERSION = '1.0.0'; // matches compliance/service.py

  /**
   * A resolved fact. `detail` records where it came from (a portal, or a
   * document page + snippet). `conflicts` is non-empty only when the bid
   * stated more than one distinct value for the same key across pages.
   */
  function FactValue(value, detail, conflicts) {
    return { value: value, detail: detail || {}, conflicts: conflicts || [] };
  }

  function factDict(fact) {
    if (!fact) return null;
    var out = { value: fact.value, source: fact.detail };
    if (fact.conflicts && fact.conflicts.length) out.conflicts = fact.conflicts;
    return out;
  }

  function resolveExpected(rule, context) {
    // Returns [expectedValue, resolvable]. resolvable is false when the rule
    // depends on a threshold_from key that isn't in context — the finding
    // becomes NEEDS_REVIEW rather than a false PASS or FAIL.
    if (rule.threshold_from !== null && rule.threshold_from !== undefined) {
      if (!Object.prototype.hasOwnProperty.call(context, rule.threshold_from)) return [null, false];
      return [context[rule.threshold_from], true];
    }
    return [rule.value === undefined ? null : rule.value, true];
  }

  function resolveActual(rule, claimed, verified) {
    var priority = rule.source_priority || ['document'];
    for (var i = 0; i < priority.length; i++) {
      // Note: anything that isn't the literal string "document" reads the
      // verified bucket — this mirrors the Python's dict.get() fallthrough.
      var bucket = SOURCE_TO_BUCKET[priority[i]] === 'claimed' ? claimed : verified;
      var fact = bucket[rule.fact];
      if (fact !== undefined && fact !== null) return fact;
    }
    return null;
  }

  function repr(v) {
    if (typeof v === 'string') return "'" + v + "'";
    if (v === null || v === undefined) return 'None';
    if (v === true) return 'True';
    if (v === false) return 'False';
    return String(v);
  }

  /**
   * Pure function: same rule pack + facts + context always produces the same
   * findings. No model calls, no I/O — that determinism is the point.
   *
   * @param {{name:string, version:number, rules:Array}} pack
   * @param {Object.<string, object>} claimed  fact key -> FactValue
   * @param {Object.<string, object>} verified fact key -> FactValue
   * @param {Object} context                   threshold + applies_if lookups
   * @returns {Array} findings
   */
  function evaluateRulePack(pack, claimed, verified, context) {
    var results = [];

    pack.rules.forEach(function (rule) {
      if (rule.applies_if && !evaluateCondition(rule.applies_if, context)) return;

      var claimedFact = claimed[rule.fact] || null;
      var verifiedFact = verified[rule.fact] || null;
      var exp = resolveExpected(rule, context);
      var expectedValue = exp[0], resolvable = exp[1];
      var expectedOut = { operator: rule.operator, value: expectedValue };

      function push(status, reason, riskContribution) {
        results.push({
          rule_id: rule.id,
          label: rule.label,
          severity: rule.severity,
          weight: rule.weight,
          status: status,
          reason: reason,
          expected: expectedOut,
          claimed: factDict(claimedFact),
          verified: factDict(verifiedFact),
          risk_contribution: riskContribution,
          source_priority: rule.source_priority || ['document']
        });
      }

      if (!resolvable) {
        push('NEEDS_REVIEW',
          "Tender threshold '" + rule.threshold_from + "' was not extracted for this requirement.",
          rule.weight * 0.5);
        return;
      }

      var resolved = resolveActual(rule, claimed, verified);
      if (resolved === null) {
        push('NEEDS_REVIEW',
          "No value found for '" + rule.fact + "' from any source in [" + (rule.source_priority || ['document']).join(', ') + "].",
          rule.weight * 0.5);
        return;
      }

      // An internal contradiction is itself the signal — never resolved by
      // last-write-wins.
      if (resolved.conflicts && resolved.conflicts.length) {
        var desc = resolved.conflicts.map(function (c) {
          return 'p.' + c.page + ': ' + repr(c.value);
        }).join('; ');
        push('NEEDS_REVIEW',
          "Bid states different values for '" + rule.fact + "' across pages (" + desc + ").",
          rule.weight * 0.5);
        return;
      }

      try {
        var passed = evaluate(rule.operator, resolved.value, expectedValue);
        push(passed ? 'PASS' : 'FAIL',
          rule.label + ': ' + repr(resolved.value) + ' ' +
            (passed ? 'satisfies' : 'does not satisfy') + ' ' +
            rule.operator + ' ' + repr(expectedValue) + '.',
          passed ? 0 : rule.weight);
      } catch (err) {
        push('NEEDS_REVIEW',
          "Could not evaluate '" + rule.fact + "': " + err.message,
          rule.weight * 0.5);
      }
    });

    return results;
  }

  /* ------------------------------------------------------------------ */
  /* scorer.py                                                           */
  /* ------------------------------------------------------------------ */

  var LOW_MAX = 33;
  var MEDIUM_MAX = 65;
  var HIGH_FLOOR_FOR_BLOCKER = 66;

  function bandFor(score) {
    if (score > MEDIUM_MAX) return 'HIGH';
    if (score > LOW_MAX) return 'MEDIUM';
    return 'LOW';
  }

  /**
   * Weighted 0-100 risk score. A FAILed BLOCKER-severity requirement forces
   * the HIGH band regardless of how well everything else scored — a single
   * disqualifying fact should never be diluted by 26 unrelated passes.
   */
  function scoreFindings(findings) {
    var totalWeight = 0, totalRisk = 0;
    findings.forEach(function (f) {
      totalWeight += f.weight;
      totalRisk += f.risk_contribution;
    });

    var rawScore = totalWeight ? (totalRisk / totalWeight * 100) : 0;
    var blockerFailed = findings.some(function (f) {
      return f.severity === 'BLOCKER' && f.status === 'FAIL';
    });
    var score = blockerFailed ? Math.max(rawScore, HIGH_FLOOR_FOR_BLOCKER) : rawScore;

    function count(status) {
      return findings.filter(function (f) { return f.status === status; }).length;
    }

    return {
      score: Math.round(score * 10) / 10,
      raw_score: Math.round(rawScore * 10) / 10,
      band: blockerFailed ? 'HIGH' : bandFor(score),
      forced_by_blocker: blockerFailed,
      total_weight: totalWeight,
      total_risk: Math.round(totalRisk * 10) / 10,
      pass_count: count('PASS'),
      fail_count: count('FAIL'),
      needs_review_count: count('NEEDS_REVIEW')
    };
  }

  /* ------------------------------------------------------------------ */
  /* normalizers.py — the one boundary where strings become values       */
  /* ------------------------------------------------------------------ */

  var CURRENCY_PREFIX_RE = /^(rs\.?|inr|₹)\s*/i;
  var TRAILING_NOISE_RE = /(\/-|\bonly\b)\s*$/i;
  var NUMBER_UNIT_RE = /([\d,]+(?:\.\d+)?)\s*(crores?|cr\.?|lakhs?|lacs?|l\.?|millions?|mn\.?|billions?|bn\.?|thousands?|k\.?)?/i;

  var UNIT_MULTIPLIERS = {
    'crore': 1e7, 'crores': 1e7, 'cr': 1e7, 'cr.': 1e7,
    'lakh': 1e5, 'lakhs': 1e5, 'lac': 1e5, 'lacs': 1e5, 'l': 1e5, 'l.': 1e5,
    'million': 1e6, 'millions': 1e6, 'mn': 1e6, 'mn.': 1e6,
    'billion': 1e9, 'billions': 1e9, 'bn': 1e9, 'bn.': 1e9,
    'thousand': 1e3, 'thousands': 1e3, 'k': 1e3, 'k.': 1e3
  };

  var GSTIN_RE = /^\d{2}[A-Z]{5}\d{4}[A-Z]\d[Z][A-Z\d]$/;
  var PAN_RE = /^[A-Z]{5}\d{4}[A-Z]$/;

  /** "Rs. 5,00,00,000" / "5 Crore" / "5cr" / "50 million" / "5,00,00,000/-" -> float */
  function normalizeAmount(raw) {
    if (!raw) return null;
    var text = String(raw).trim();
    text = text.replace(CURRENCY_PREFIX_RE, '');
    text = text.replace(TRAILING_NOISE_RE, '').trim();

    var m = NUMBER_UNIT_RE.exec(text);
    if (!m) return null;

    var n = parseFloat(m[1].replace(/,/g, ''));
    if (isNaN(n)) return null;

    var unit = (m[2] || '').toLowerCase().trim();
    var multiplier = Object.prototype.hasOwnProperty.call(UNIT_MULTIPLIERS, unit) ? UNIT_MULTIPLIERS[unit] : 1.0;
    return n * multiplier;
  }

  function normalizeYears(raw) {
    if (!raw) return null;
    var m = /\d+(?:\.\d+)?/.exec(String(raw));
    return m ? parseFloat(m[0]) : null;
  }

  function normalizeGstin(raw) {
    if (!raw) return null;
    var c = String(raw).replace(/\s+/g, '').toUpperCase();
    return GSTIN_RE.test(c) ? c : null;
  }

  function normalizePan(raw) {
    if (!raw) return null;
    var c = String(raw).replace(/\s+/g, '').toUpperCase();
    return PAN_RE.test(c) ? c : null;
  }

  /* ------------------------------------------------------------------ */
  /* snippet_guard.py — the hallucination fence                          */
  /* ------------------------------------------------------------------ */

  function normalizeWhitespace(text) {
    return String(text).replace(/\s+/g, ' ').trim().toLowerCase();
  }

  /**
   * True only if `snippet` appears verbatim in `sourceText` (whitespace and
   * case differences ignored). Anything else is rejected rather than trusted.
   */
  function isSnippetGrounded(snippet, sourceText) {
    if (!snippet || !String(snippet).trim()) return false;
    return normalizeWhitespace(sourceText).indexOf(normalizeWhitespace(snippet)) !== -1;
  }

  /* ------------------------------------------------------------------ */

  global.TGEngine = {
    ENGINE_VERSION: ENGINE_VERSION,
    OPERATORS: OPERATORS,
    evaluate: evaluate,
    evaluateCondition: evaluateCondition,
    FactValue: FactValue,
    evaluateRulePack: evaluateRulePack,
    scoreFindings: scoreFindings,
    normalizeAmount: normalizeAmount,
    normalizeYears: normalizeYears,
    normalizeGstin: normalizeGstin,
    normalizePan: normalizePan,
    isSnippetGrounded: isSnippetGrounded,
    repr: repr
  };
})(typeof window !== 'undefined' ? window : globalThis);
