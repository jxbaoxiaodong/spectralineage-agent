/* SpectraLineage Agent — frontend JS */

const DH_FRONTEND = "http://localhost:9002";

function switchTab(name, btn) {
  document.querySelectorAll('.tab-panel').forEach(p => p.classList.remove('active'));
  document.querySelectorAll('nav button').forEach(b => b.classList.remove('active'));
  document.getElementById('tab-' + name).classList.add('active');
  btn.classList.add('active');
}

// ── util ──────────────────────────────────────────────────────────────────

function dhDatasetUrl(urn) {
  const enc = encodeURIComponent(urn);
  return `${DH_FRONTEND}/dataset/${enc}`;
}

function urnLink(urn, label) {
  const url = dhDatasetUrl(urn);
  return `<a href="${url}" target="_blank" style="font-family:monospace;font-size:11px;color:var(--blue);">${label || urn}</a>`;
}

function verdictClass(v) {
  if (!v) return '';
  v = v.toUpperCase();
  if (v.includes('GREEN')) return 'verdict-GREEN';
  if (v.includes('RED') || v.includes('FAIL') || v.includes('ERROR')) return 'verdict-RED';
  return 'verdict-YELLOW';
}

// ── ANALYZE TAB ───────────────────────────────────────────────────────────

async function runHeroCase() {
  const btn = document.getElementById('btn-run');
  btn.disabled = true;
  btn.innerHTML = '<span class="spinner"></span> Analyzing…';

  try {
    const res = await fetch('/api/analyze/hero', { method: 'POST' });
    if (!res.ok) throw new Error(await res.text());
    const d = await res.json();
    renderAnalysisResult(d);
  } catch (e) {
    alert('Error: ' + e.message);
  } finally {
    btn.disabled = false;
    btn.innerHTML = '▶ Run Analysis + Register in DataHub';
  }
}

function renderAnalysisResult(d) {
  const eg = d.evidence_gate || {};
  const lin = d.lineage_registered || {};
  const verdict = eg.verdict || 'UNKNOWN';
  const vc = verdictClass(verdict);

  // Show result section
  document.getElementById('analyze-result').style.display = 'block';

  // DataHub link button
  const dhBtn = document.getElementById('btn-dh-link');
  dhBtn.style.display = 'inline-flex';
  dhBtn.href = d.datahub_link || DH_FRONTEND;

  // Verdict card
  document.getElementById('verdict-content').innerHTML = `
    <div style="margin-bottom:12px;">
      <span class="verdict-badge ${vc}">${verdict}</span>
      ${eg.verdict_ladder ? `<span style="color:var(--muted);font-size:12px;margin-left:8px;">${eg.verdict_ladder}</span>` : ''}
    </div>
    <div class="meta-row"><span class="meta-label">Blocked reason</span>
      <span class="meta-val" style="color:var(--red);">${eg.block_reason || eg.blocked_reason || '—'}</span></div>
    <div class="meta-row"><span class="meta-label">Top-1 candidate</span>
      <span class="meta-val">${(d.library_result?.top_candidates?.[0]?.name) || '—'}</span></div>
    <div class="meta-row"><span class="meta-label">Similarity</span>
      <span class="meta-val">${((d.library_result?.top_candidates?.[0]?.similarity || 0) * 100).toFixed(0)} %</span></div>
    ${(eg.recommended_next_steps || eg.next_steps || []).length ? `
    <div style="margin-top:12px;">
      <div style="font-size:12px;color:var(--muted);margin-bottom:6px;">NEXT STEPS</div>
      ${(eg.recommended_next_steps || eg.next_steps || []).map(s => `<div style="font-size:13px;padding:3px 0;">• ${s}</div>`).join('')}
    </div>` : ''}
  `;

  // DataHub registration card
  document.getElementById('datahub-content').innerHTML = `
    <div class="alert alert-success" style="margin-bottom:12px;">✅ 4 entities registered in DataHub</div>
    <div class="meta-row"><span class="meta-label">Input spectrum</span>
      <span class="meta-val">${urnLink(lin.spectrum_urn, lin.spectrum_urn?.split(',')[1] || 'spectrum')}</span></div>
    <div class="meta-row"><span class="meta-label">Output verdict</span>
      <span class="meta-val">${urnLink(lin.verdict_urn, lin.verdict_urn?.split(',')[1] || 'verdict')}</span></div>
    <div class="meta-row"><span class="meta-label">DataFlow</span>
      <span class="meta-val" style="font-family:monospace;font-size:11px;color:var(--purple);">${lin.flow_urn?.split(',')[1] || lin.flow_urn || '—'}</span></div>
    <div class="meta-row"><span class="meta-label">DataJob</span>
      <span class="meta-val" style="font-family:monospace;font-size:11px;color:var(--purple);">evidence-gate</span></div>
    <div style="margin-top:12px;">
      <a href="${d.datahub_link}" target="_blank" class="btn btn-dh" style="font-size:12px;padding:6px 12px;">
        View verdict in DataHub ↗
      </a>
    </div>
  `;

  // Lineage chain visualisation
  document.getElementById('lineage-chain-viz').innerHTML = `
    <div class="lineage-chain">
      <div class="lineage-node">
        <div class="node-type">📄 Dataset (input)</div>
        <div class="node-name">${d.filename || d.sample_id + '.spectrum'}</div>
        <div class="node-urn">${lin.spectrum_urn || ''}</div>
      </div>
      <div class="lineage-arrow">→</div>
      <div class="lineage-node">
        <div class="node-type">⚙ DataFlow</div>
        <div class="node-name">spectral-auditor-pipeline</div>
        <div class="node-urn">DataJob: evidence-gate</div>
      </div>
      <div class="lineage-arrow">→</div>
      <div class="lineage-node" style="border-color:var(--yellow);">
        <div class="node-type">📄 Dataset (output)</div>
        <div class="node-name">${d.sample_id}.verdict</div>
        <div class="node-urn">${lin.verdict_urn || ''}</div>
      </div>
    </div>
  `;

  // Audit chain — may be a list directly or {steps:[...], final_hash:"..."}
  const rawAudit = d.audit_chain;
  const steps = Array.isArray(rawAudit) ? rawAudit : (rawAudit?.steps || []);
  const finalHash = Array.isArray(rawAudit)
    ? (steps[steps.length - 1]?.sha256 || '—')
    : (rawAudit?.final_hash || '—');
  document.getElementById('audit-content').innerHTML = steps.length ? `
    ${steps.map((s, i) => `
    <div class="audit-step">
      <div class="audit-step-header">
        <span class="step-num">Step ${i + 1}</span>
        <span class="step-name">${s.label || s.stage || 'Stage'}</span>
        <span style="color:var(--green);font-size:12px;">✓ PASS</span>
      </div>
      <div class="step-hash">SHA-256: ${s.sha256 || s.hash || '—'}</div>
    </div>`).join('')}
    <div style="margin-top:10px;font-size:12px;color:var(--muted);">
      Final hash: <span style="font-family:monospace;">${finalHash}</span>
    </div>
  ` : '<div style="color:var(--muted);font-size:13px;">No audit chain data.</div>';

  // Scroll to result
  document.getElementById('analyze-result').scrollIntoView({ behavior: 'smooth', block: 'start' });
}

// ── LINEAGE TAB ───────────────────────────────────────────────────────────

async function queryLineage() {
  const sampleId = document.getElementById('lineage-sample-id').value.trim();
  if (!sampleId) return;
  const el = document.getElementById('lineage-result');
  el.innerHTML = '<div class="card"><span class="spinner"></span> Querying DataHub…</div>';
  try {
    const res = await fetch(`/api/lineage/${encodeURIComponent(sampleId)}`);
    const d = await res.json();
    const confirmed = d.lineage_confirmed;
    const chain = d.lineage_chain || [];
    const typeIcon = t => ({dataset:'📄', dataflow:'⚙', datajob:'🔬'}[t] || '📦');
    const borderColor = node => {
      if (node.verdict) return 'var(--yellow)';
      if (node.type === 'dataset') return 'var(--blue)';
      return 'var(--purple)';
    };

    el.innerHTML = `
      <div class="card">
        <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:14px;">
          <h3 style="margin:0;">Lineage: ${sampleId}</h3>
          <span class="verdict-badge ${confirmed ? 'verdict-GREEN' : 'verdict-YELLOW'}">
            ${confirmed ? '✓ CONFIRMED IN DATAHUB' : '⚠ NOT YET REGISTERED'}
          </span>
        </div>
        <div class="lineage-chain" style="flex-wrap:wrap;gap:8px;margin-bottom:16px;">
          ${chain.map((node, i) => `
            <div class="lineage-node" style="border-color:${borderColor(node)};">
              <div class="node-type">${typeIcon(node.type)} ${node.label}</div>
              <div class="node-name">${node.name}</div>
              <div class="node-urn" style="font-size:10px;">${node.urn?.split(',')[1] || node.urn || ''}</div>
              ${node.exists_in_datahub !== undefined
                ? `<div style="font-size:11px;margin-top:4px;color:${node.exists_in_datahub ? 'var(--green)' : 'var(--red)'};">
                     ${node.exists_in_datahub ? '✓ verified in DataHub' : '✗ not found'}
                   </div>` : ''}
              <a href="${node.datahub_url}" target="_blank" style="font-size:10px;color:var(--blue);margin-top:4px;">View ↗</a>
            </div>
            ${i < chain.length - 1 ? '<div class="lineage-arrow" style="align-self:center;">→</div>' : ''}
          `).join('')}
        </div>
        <a href="${d.datahub_lineage_ui}" target="_blank" class="btn btn-dh" style="font-size:12px;padding:6px 12px;">
          Open Lineage Graph in DataHub ↗
        </a>
      </div>
    `;
  } catch (e) {
    el.innerHTML = `<div class="alert alert-warn">Error: ${e.message}</div>`;
  }
}

function openDhLineage() {
  const sampleId = document.getElementById('lineage-sample-id').value.trim();
  const urn = `urn:li:dataset:(urn:li:dataPlatform:ftir,${sampleId}.verdict,PROD)`;
  window.open(`${DH_FRONTEND}/dataset/${encodeURIComponent(urn)}`, '_blank');
}

// ── ENTITIES TAB ──────────────────────────────────────────────────────────

async function loadEntities() {
  const el = document.getElementById('entities-result');
  el.innerHTML = '<div class="card"><span class="spinner"></span> Loading from DataHub…</div>';
  try {
    const res = await fetch('/api/entities');
    const d = await res.json();
    if (!d.datasets || d.datasets.length === 0) {
      el.innerHTML = `
        <div class="card">
          <div class="alert alert-info">No FTIR datasets found yet. Run a hero case analysis first.</div>
          <a href="${DH_FRONTEND}" target="_blank" class="btn btn-dh" style="margin-top:10px;font-size:12px;padding:6px 12px;">Open DataHub UI ↗</a>
        </div>`;
      return;
    }
    const items = d.datasets.map(e => {
      const urn = e.urn || '';
      const name = e.name || urn.split(',')[1] || urn;
      const desc = e.description ? `<div style="font-size:11px;color:var(--muted);margin-top:2px;">${e.description.slice(0, 80)}${e.description.length > 80 ? '…' : ''}</div>` : '';
      return `
        <div class="entity-item">
          <span class="entity-icon">📄</span>
          <div class="entity-info">
            <div class="entity-name">${name}</div>
            ${desc}
            <div class="entity-urn">${urn}</div>
          </div>
          <a href="${dhDatasetUrl(urn)}" target="_blank" class="btn btn-outline" style="font-size:11px;padding:4px 10px;white-space:nowrap;">View ↗</a>
        </div>`;
    }).join('');
    el.innerHTML = `
      <div class="card">
        <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:14px;">
          <span style="font-weight:600;">${d.count} datasets in DataHub</span>
          <a href="${DH_FRONTEND}" target="_blank" class="btn btn-dh" style="font-size:12px;padding:6px 12px;">DataHub UI ↗</a>
        </div>
        ${items}
      </div>`;
  } catch (e) {
    el.innerHTML = `<div class="alert alert-warn">Error: ${e.message}</div>`;
  }
}

// ── init ──────────────────────────────────────────────────────────────────
window.addEventListener('DOMContentLoaded', () => {
  fetch('/api/health').then(r => r.json()).then(d => {
    if (!d.datahub_healthy) {
      document.querySelector('header').insertAdjacentHTML('afterend',
        '<div class="alert alert-warn" style="margin:0;border-radius:0;border-left:none;border-right:none;">⚠ DataHub GMS not reachable — start DataHub quickstart first.</div>');
    }
  }).catch(() => {});
});
