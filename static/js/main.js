/**
 * LLVM DiffTester — main page logic
 */

let currentIR = '';
let currentMutationType = '';
let currentSourceFilename = 'unknown.c';
let statusBarInterval = null;

const MUTATION_LABELS = {
  add_arithmetic: 'Add arithmetic',
  change_types: 'Change types',
  insert_branch: 'Insert branch',
  insert_phi: 'Insert PHI',
  dead_code: 'Dead code',
  swap_operands: 'Swap operands',
};

document.addEventListener('DOMContentLoaded', () => {
  initDropZone();
  initMutationCards();
  document.getElementById('copy-ir-btn')?.addEventListener('click', () => {
    copyToClipboard(currentIR, document.getElementById('copy-ir-btn'));
  });
  document.getElementById('copy-prompt-btn')?.addEventListener('click', () => {
    const prompt = document.getElementById('prompt-output')?.value || '';
    copyToClipboard(prompt, document.getElementById('copy-prompt-btn'));
  });
  document.getElementById('generate-prompt-btn')?.addEventListener('click', generatePrompt);
  document.getElementById('run-test-btn')?.addEventListener('click', runValidationAndTest);
  document.getElementById('refresh-history-btn')?.addEventListener('click', loadHistory);
  document.getElementById('modal-close')?.addEventListener('click', closeModal);
  document.getElementById('modal-backdrop')?.addEventListener('click', closeModal);
  loadHistory();
});

function initDropZone() {
  const dropZone = document.getElementById('drop-zone');
  const fileInput = document.getElementById('c-file-input');
  if (!dropZone || !fileInput) return;

  dropZone.addEventListener('click', () => fileInput.click());
  fileInput.addEventListener('change', () => {
    if (fileInput.files?.[0]) uploadAndGenerateIR(fileInput.files[0]);
  });
  dropZone.addEventListener('dragover', (e) => {
    e.preventDefault();
    dropZone.classList.add('dragover');
  });
  dropZone.addEventListener('dragleave', () => dropZone.classList.remove('dragover'));
  dropZone.addEventListener('drop', (e) => {
    e.preventDefault();
    dropZone.classList.remove('dragover');
    const file = e.dataTransfer?.files?.[0];
    if (file) uploadAndGenerateIR(file);
  });
}

function initMutationCards() {
  document.querySelectorAll('.mutation-card').forEach((card) => {
    card.addEventListener('click', () => {
      const type = card.dataset.type;
      const radio = card.querySelector('input[type="radio"]');
      if (radio) radio.checked = true;
      selectMutationType(type);
    });
  });
}

async function uploadAndGenerateIR(file) {
  if (!file.name.toLowerCase().endsWith('.c')) {
    showUploadStatus('Please select a .c file', true);
    return;
  }

  currentSourceFilename = file.name;
  const statusEl = document.getElementById('upload-status');
  statusEl.classList.remove('hidden', 'error');
  statusEl.innerHTML = '<div class="spinner"></div><span>Generating LLVM IR...</span>';

  document.getElementById('ir-output-wrap')?.classList.add('hidden');

  const formData = new FormData();
  formData.append('c_file', file);

  try {
    const res = await fetch('/api/generate-ir', { method: 'POST', body: formData });
    const data = await res.json();

    if (data.success) {
      currentIR = data.ir;
      if (data.source_filename) currentSourceFilename = data.source_filename;
      showUploadStatus(`Loaded: ${file.name}`, false);
      document.getElementById('ir-output').textContent = currentIR;
      document.getElementById('ir-output-wrap')?.classList.remove('hidden');
      updatePromptButton();
    } else {
      showUploadStatus(data.error || 'IR generation failed', true);
    }
  } catch (err) {
    showUploadStatus(`Network error: ${err.message}`, true);
  }
}

function showUploadStatus(msg, isError) {
  const el = document.getElementById('upload-status');
  el.classList.remove('hidden');
  el.classList.toggle('error', isError);
  el.innerHTML = isError ? msg : `<span>${escapeHtml(msg)}</span>`;
}

function selectMutationType(type) {
  currentMutationType = type;
  document.querySelectorAll('.mutation-card').forEach((c) => {
    c.classList.toggle('selected', c.dataset.type === type);
  });
  updatePromptButton();
}

function updatePromptButton() {
  const btn = document.getElementById('generate-prompt-btn');
  if (btn) btn.disabled = !(currentIR && currentMutationType);
}

async function generatePrompt() {
  const btn = document.getElementById('generate-prompt-btn');
  btn.disabled = true;

  try {
    const res = await fetch('/api/get-prompt', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ ir: currentIR, mutation_type: currentMutationType }),
    });
    const data = await res.json();
    if (data.success) {
      document.getElementById('prompt-output').value = data.prompt;
      document.getElementById('prompt-wrap')?.classList.remove('hidden');
    } else {
      alert(data.error || 'Failed to generate prompt');
    }
  } catch (err) {
    alert(`Error: ${err.message}`);
  } finally {
    btn.disabled = !(currentIR && currentMutationType);
  }
}

function copyToClipboard(text, anchorEl) {
  navigator.clipboard.writeText(text).then(() => {
    const rect = anchorEl?.getBoundingClientRect();
    const tip = document.createElement('div');
    tip.className = 'copy-tooltip';
    tip.textContent = 'Copied!';
    if (rect) {
      tip.style.left = `${rect.left + rect.width / 2 - 30}px`;
      tip.style.top = `${rect.top - 30}px`;
    } else {
      tip.style.left = '50%';
      tip.style.top = '50%';
    }
    document.body.appendChild(tip);
    setTimeout(() => tip.remove(), 1500);
  });
}

function startStatusBarAnimation() {
  const bar = document.getElementById('status-bar');
  bar?.classList.remove('hidden');
  const phases = bar?.querySelectorAll('.phase') || [];
  let idx = 0;
  phases.forEach((p, i) => {
    p.classList.remove('active', 'done');
    if (i === 0) p.classList.add('active');
  });

  if (statusBarInterval) clearInterval(statusBarInterval);
  statusBarInterval = setInterval(() => {
    if (idx < phases.length) {
      phases[idx].classList.remove('active');
      phases[idx].classList.add('done');
      idx += 1;
      if (idx < phases.length) phases[idx].classList.add('active');
    }
  }, 1500);
}

function completeStatusBar() {
  if (statusBarInterval) {
    clearInterval(statusBarInterval);
    statusBarInterval = null;
  }
  document.querySelectorAll('#status-bar .phase').forEach((p) => {
    p.classList.remove('active');
    p.classList.add('done');
  });
}

async function runValidationAndTest() {
  const mutatedIR = document.getElementById('mutated-ir-input')?.value?.trim();
  if (!mutatedIR) {
    alert('Please paste mutated IR in Step 4.');
    return;
  }
  if (!currentMutationType) {
    alert('Please select a mutation type in Step 2.');
    return;
  }

  const btn = document.getElementById('run-test-btn');
  btn.disabled = true;
  startStatusBarAnimation();
  document.getElementById('step-5')?.classList.add('hidden');

  try {
    const res = await fetch('/api/validate-and-test', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        mutated_ir: mutatedIR,
        seed_ir: currentIR,
        mutation_type: currentMutationType,
        source_filename: currentSourceFilename,
      }),
    });
    const data = await res.json();
    completeStatusBar();
    if (data.success !== false) {
      renderResults(data);
      document.getElementById('step-5')?.classList.remove('hidden');
      loadHistory();
    } else {
      alert(data.error || 'Test failed');
    }
  } catch (err) {
    completeStatusBar();
    alert(`Error: ${err.message}`);
  } finally {
    btn.disabled = false;
  }
}

function renderResults(data) {
  const panel = document.getElementById('results-panel');
  if (!panel) return;

  const valid = data.valid === true;
  const match = data.diff_match === true;
  const interesting = data.is_interesting === true;

  let html = '<div class="badges-row">';
  html += valid
    ? '<span class="badge badge-valid">VALID</span>'
    : '<span class="badge badge-invalid">INVALID</span>';

  if (!valid && data.error_type) {
    html += `<span class="badge badge-error">${escapeHtml(data.error_type)}</span>`;
  }

  if (valid) {
    html += match
      ? '<span class="badge badge-match">O0/O3 MATCH</span>'
      : '<span class="badge badge-mismatch">O0/O3 MISMATCH</span>';
  }

  if (interesting) {
    html += '<span class="badge badge-interesting">INTERESTING</span>';
  }
  html += '</div>';

  if (!valid) {
    html += `<div class="error-block">
      <div class="error-type">${escapeHtml(data.error_type || 'UNKNOWN_ERROR')}</div>
      <p>Verifier rejected the mutated IR.</p>
      <details>
        <summary>Raw verifier stderr</summary>
        <pre>${escapeHtml(data.error_detail || '')}</pre>
      </details>
    </div>`;
  } else if (match) {
    html += '<div class="banner banner-success">No Bug Found — O0 and O3 outputs match.</div>';
  } else {
    html += '<div class="banner banner-danger">Potential Compiler Bug! — O0 and O3 outputs differ.</div>';
    html += `<div class="diff-view">
      <div class="diff-side o0">
        <h4>O0 Output (exit ${data.o0_exit ?? '?'})</h4>
        <pre>${formatOutput(data.o0_output)}</pre>
      </div>
      <div class="diff-side o3">
        <h4>O3 Output (exit ${data.o3_exit ?? '?'})</h4>
        <pre>${formatOutput(data.o3_output)}</pre>
      </div>
    </div>`;
  }

  if (data.run_id) {
    html += `<p class="hint-text">Saved to history as run #${data.run_id}.</p>`;
  }

  panel.innerHTML = html;
}

function formatOutput(text) {
  if (!text || text.trim() === '') {
    return '<span class="empty-output">No output</span>';
  }
  return escapeHtml(text);
}

async function loadHistory() {
  const tbody = document.getElementById('history-tbody');
  if (!tbody) return;

  try {
    const res = await fetch('/api/runs');
    const data = await res.json();
    if (!data.success) return;

    tbody.innerHTML = '';
  const runs = data.runs || [];

    if (runs.length === 0) {
      tbody.innerHTML = '<tr><td colspan="7" style="text-align:center;color:var(--muted)">No test runs yet</td></tr>';
      return;
    }

    runs.forEach((run) => {
      const tr = document.createElement('tr');
      const valid = run.valid === 1;
      const match = run.diff_match === 1;
      const interesting = run.is_interesting === 1;

      if (!valid) tr.classList.add('row-invalid');
      else if (!match && run.diff_match !== null) tr.classList.add('row-mismatch');
      else if (valid && match) tr.classList.add('row-match');

      const date = (run.created_at || '').slice(0, 19).replace('T', ' ');
      const mutLabel = MUTATION_LABELS[run.mutation_type] || run.mutation_type;

      tr.innerHTML = `
        <td>${run.id}</td>
        <td>${escapeHtml(date)}</td>
        <td>${escapeHtml(run.source_filename || '')}</td>
        <td>${escapeHtml(mutLabel)}</td>
        <td>${valid ? 'Yes' : 'No'}</td>
        <td>${run.diff_match === null ? '—' : match ? 'Yes' : 'No'}</td>
        <td>${interesting ? 'Yes' : 'No'}</td>
      `;
      tr.addEventListener('click', () => openRunModal(run.id));
      tbody.appendChild(tr);
    });
  } catch (err) {
    console.error('Failed to load history', err);
  }
}

async function openRunModal(runId) {
  try {
    const res = await fetch(`/api/run/${runId}`);
    const data = await res.json();
    if (!data.success || !data.run) return;

    const run = data.run;
    document.getElementById('modal-run-id').textContent = `#${run.id}`;
    const body = document.getElementById('modal-body');

    body.innerHTML = `
      <div class="modal-field"><strong>Date</strong>${escapeHtml(run.created_at || '')}</div>
      <div class="modal-field"><strong>File</strong>${escapeHtml(run.source_filename || '')}</div>
      <div class="modal-field"><strong>Mutation</strong>${escapeHtml(run.mutation_type || '')}</div>
      <div class="modal-field"><strong>Valid</strong>${run.valid === 1 ? 'Yes' : 'No'}</div>
      ${run.error_type ? `<div class="modal-field"><strong>Error Type</strong>${escapeHtml(run.error_type)}</div>` : ''}
      ${run.error_detail ? `<div class="modal-field"><strong>Error Detail</strong><pre>${escapeHtml(run.error_detail)}</pre></div>` : ''}
      ${run.valid === 1 ? `
        <div class="modal-field"><strong>Match</strong>${run.diff_match === 1 ? 'Yes' : 'No'}</div>
        <div class="modal-field"><strong>O0 Exit</strong>${run.o0_exit}</div>
        <div class="modal-field"><strong>O3 Exit</strong>${run.o3_exit}</div>
        <div class="modal-field"><strong>O0 Output</strong><pre>${escapeHtml(run.o0_output || '(empty)')}</pre></div>
        <div class="modal-field"><strong>O3 Output</strong><pre>${escapeHtml(run.o3_output || '(empty)')}</pre></div>
      ` : ''}
      <div class="modal-field"><strong>Seed IR</strong><pre>${escapeHtml((run.seed_ir || '').slice(0, 2000))}${(run.seed_ir || '').length > 2000 ? '…' : ''}</pre></div>
      <div class="modal-field"><strong>Mutated IR</strong><pre>${escapeHtml((run.mutated_ir || '').slice(0, 2000))}${(run.mutated_ir || '').length > 2000 ? '…' : ''}</pre></div>
    `;

    document.getElementById('run-modal')?.classList.remove('hidden');
  } catch (err) {
    console.error(err);
  }
}

function closeModal() {
  document.getElementById('run-modal')?.classList.add('hidden');
}

function escapeHtml(str) {
  const div = document.createElement('div');
  div.textContent = str;
  return div.innerHTML;
}
