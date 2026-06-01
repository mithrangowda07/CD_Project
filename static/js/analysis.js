/**
 * LLVM DiffTester — analysis page charts
 */

const ERROR_COLORS = {
  SSA_VIOLATION: '#7c3aed',
  TYPE_MISMATCH: '#2563eb',
  INVALID_PHI: '#d97706',
  DOMINANCE_ERROR: '#dc2626',
  MISSING_TERMINATOR: '#0891b2',
  UNKNOWN_ERROR: '#64748b',
};

const MUTATION_SHORT = {
  add_arithmetic: 'Add arith',
  change_types: 'Change types',
  insert_branch: 'Branch',
  insert_phi: 'PHI loop',
  dead_code: 'Dead code',
  swap_operands: 'Swap ops',
};

let charts = [];

document.addEventListener('DOMContentLoaded', async () => {
  if (typeof Chart !== 'undefined') {
    Chart.defaults.color = '#8b9cb3';
    Chart.defaults.borderColor = '#2a3548';
    Chart.defaults.plugins.legend.labels.color = '#e8edf5';
  }

  try {
    const res = await fetch('/api/stats');
    const data = await res.json();
    if (!data.success) throw new Error('Failed to load stats');
    const stats = data.stats;
    document.getElementById('analysis-loading')?.classList.add('hidden');
    document.getElementById('analysis-content')?.classList.remove('hidden');
    renderKPIs(stats);
    renderCharts(stats);
    document.getElementById('findings-text').innerHTML = generateKeyFindings(stats);
  } catch (err) {
    document.getElementById('analysis-loading').innerHTML =
      `<span style="color:var(--danger)">Error: ${err.message}</span>`;
  }
});

function renderKPIs(stats) {
  const grid = document.getElementById('kpi-grid');
  const validRate = stats.total ? `${stats.valid_pct}%` : '0%';
  const mismatchRate = stats.valid ? `${stats.mismatch_pct}%` : '0%';

  grid.innerHTML = `
    <div class="kpi-card">
      <p class="kpi-label">Total Test Runs</p>
      <p class="kpi-value">${stats.total}</p>
    </div>
    <div class="kpi-card">
      <p class="kpi-label">Valid Rate</p>
      <p class="kpi-value">${validRate}</p>
    </div>
    <div class="kpi-card">
      <p class="kpi-label">Mismatch Rate (of valid)</p>
      <p class="kpi-value">${mismatchRate}</p>
    </div>
    <div class="kpi-card">
      <p class="kpi-label">Interesting Cases</p>
      <p class="kpi-value">${stats.interesting}</p>
    </div>
  `;
}

function destroyCharts() {
  charts.forEach((c) => c.destroy());
  charts = [];
}

function showNoData(canvasId, msgId, show) {
  const canvas = document.getElementById(canvasId);
  const msg = document.getElementById(msgId);
  if (canvas) canvas.style.display = show ? 'none' : 'block';
  if (msg) msg.classList.toggle('hidden', !show);
}

function renderCharts(stats) {
  destroyCharts();

  renderValidityChart(stats);
  renderMutationChart(stats);
  renderErrorChart(stats);
  renderTimelineChart(stats);
  renderUsefulnessChart(stats);
}

function renderValidityChart(stats) {
  const canvas = document.getElementById('chart-validity');
  if (!canvas) return;

  if (stats.total === 0) {
    showNoData('chart-validity', 'no-data-validity', true);
    return;
  }
  showNoData('chart-validity', 'no-data-validity', false);

  const centerTextPlugin = {
    id: 'centerText',
    beforeDraw(chart) {
      const { width, height, ctx } = chart;
      const total = stats.total;
      const validPct = stats.valid_pct;
      ctx.save();
      ctx.font = 'bold 1.25rem sans-serif';
      ctx.fillStyle = '#e8edf5';
      ctx.textAlign = 'center';
      ctx.textBaseline = 'middle';
      ctx.fillText(`${validPct}%`, width / 2, height / 2 - 8);
      ctx.font = '0.75rem Inter, sans-serif';
      ctx.fillStyle = '#8b9cb3';
      ctx.fillText(`${stats.valid}/${total} valid`, width / 2, height / 2 + 14);
      ctx.restore();
    },
  };

  const chart = new Chart(canvas, {
    type: 'doughnut',
    data: {
      labels: ['Valid', 'Invalid'],
      datasets: [{
        data: [stats.valid, stats.invalid],
        backgroundColor: ['#16a34a', '#dc2626'],
        borderWidth: 0,
      }],
    },
    options: {
      responsive: true,
      maintainAspectRatio: true,
      cutout: '65%',
      plugins: {
        legend: { position: 'bottom' },
        tooltip: {
          callbacks: {
            label(ctx) {
              const v = ctx.raw;
              const pct = ((v / stats.total) * 100).toFixed(1);
              return `${ctx.label}: ${v} (${pct}%)`;
            },
          },
        },
      },
    },
    plugins: [centerTextPlugin],
  });
  charts.push(chart);
}

function renderMutationChart(stats) {
  const canvas = document.getElementById('chart-mutation');
  if (!canvas) return;

  const types = Object.keys(stats.by_mutation || {});
  if (types.length === 0) {
    showNoData('chart-mutation', 'no-data-mutation', true);
    return;
  }
  showNoData('chart-mutation', 'no-data-mutation', false);

  const labels = types.map((t) => MUTATION_SHORT[t] || t);
  const validData = types.map((t) => stats.by_mutation[t].valid || 0);
  const invalidData = types.map((t) => stats.by_mutation[t].invalid || 0);

  const chart = new Chart(canvas, {
    type: 'bar',
    data: {
      labels,
      datasets: [
        { label: 'Valid', data: validData, backgroundColor: '#16a34a' },
        { label: 'Invalid', data: invalidData, backgroundColor: '#dc2626' },
      ],
    },
    options: {
      indexAxis: 'y',
      responsive: true,
      maintainAspectRatio: true,
      scales: {
        x: { stacked: false, beginAtZero: true },
        y: { stacked: false },
      },
      plugins: { legend: { position: 'bottom' } },
    },
  });
  charts.push(chart);
}

function renderErrorChart(stats) {
  const canvas = document.getElementById('chart-errors');
  if (!canvas) return;

  const errors = stats.by_error || {};
  const keys = Object.keys(errors);
  if (keys.length === 0) {
    showNoData('chart-errors', 'no-data-errors', true);
    return;
  }
  showNoData('chart-errors', 'no-data-errors', false);

  const colors = keys.map((k) => ERROR_COLORS[k] || '#64748b');

  const chart = new Chart(canvas, {
    type: 'bar',
    data: {
      labels: keys,
      datasets: [{
        label: 'Count',
        data: keys.map((k) => errors[k]),
        backgroundColor: colors,
      }],
    },
    options: {
      responsive: true,
      maintainAspectRatio: true,
      scales: { y: { beginAtZero: true } },
      plugins: { legend: { display: false } },
    },
  });
  charts.push(chart);
}

function renderTimelineChart(stats) {
  const canvas = document.getElementById('chart-timeline');
  if (!canvas) return;

  const timeline = stats.timeline || [];
  if (timeline.length === 0) {
    showNoData('chart-timeline', 'no-data-timeline', true);
    return;
  }
  showNoData('chart-timeline', 'no-data-timeline', false);

  const labels = timeline.map((t) => t.date);
  const validData = timeline.map((t) => t.valid);
  const invalidData = timeline.map((t) => t.invalid);

  const chart = new Chart(canvas, {
    type: 'line',
    data: {
      labels,
      datasets: [
        {
          label: 'Valid',
          data: validData,
          borderColor: '#16a34a',
          backgroundColor: 'rgba(22, 163, 74, 0.4)',
          fill: true,
          tension: 0.3,
        },
        {
          label: 'Invalid',
          data: invalidData,
          borderColor: '#dc2626',
          backgroundColor: 'rgba(220, 38, 38, 0.4)',
          fill: true,
          tension: 0.3,
        },
      ],
    },
    options: {
      responsive: true,
      maintainAspectRatio: true,
      interaction: { mode: 'index', intersect: false },
      scales: {
        x: { stacked: true },
        y: { stacked: true, beginAtZero: true },
      },
      plugins: { legend: { position: 'bottom' } },
    },
  });
  charts.push(chart);
}

function renderUsefulnessChart(stats) {
  const canvas = document.getElementById('chart-usefulness');
  if (!canvas) return;

  const byMut = stats.by_mutation || {};
  const types = Object.keys(byMut);
  if (types.length === 0) {
    showNoData('chart-usefulness', 'no-data-usefulness', true);
    return;
  }
  showNoData('chart-usefulness', 'no-data-usefulness', false);

  const scores = types.map((t) => {
    const v = byMut[t].valid || 0;
    const inv = byMut[t].invalid || 0;
    const total = v + inv;
    return { type: t, score: total ? (v / total) * 100 : 0 };
  });
  scores.sort((a, b) => b.score - a.score);

  const labels = scores.map((s) => MUTATION_SHORT[s.type] || s.type);
  const data = scores.map((s) => s.score.toFixed(1));
  const colors = scores.map((s) => {
    if (s.score > 70) return '#16a34a';
    if (s.score >= 40) return '#d97706';
    return '#dc2626';
  });

  const chart = new Chart(canvas, {
    type: 'bar',
    data: {
      labels,
      datasets: [{
        label: 'Validity %',
        data,
        backgroundColor: colors,
      }],
    },
    options: {
      indexAxis: 'y',
      responsive: true,
      maintainAspectRatio: true,
      scales: {
        x: { max: 100, beginAtZero: true, title: { display: true, text: '%' } },
      },
      plugins: { legend: { display: false } },
    },
  });
  charts.push(chart);
}

function generateKeyFindings(stats) {
  const lines = [];

  if (stats.total === 0) {
    return '<p>No test runs recorded yet. Complete tests on the Test Lab page to see insights here.</p>';
  }

  lines.push(
    `<p>The LLM produced valid IR in <strong>${stats.valid_pct}%</strong> of attempts (${stats.valid} of ${stats.total}).</p>`
  );

  const errors = stats.by_error || {};
  const errorKeys = Object.keys(errors);
  if (errorKeys.length > 0) {
    const top = errorKeys.reduce((a, b) => (errors[a] >= errors[b] ? a : b));
    lines.push(
      `<p>Most common error: <strong>${top}</strong> (${errors[top]} case${errors[top] !== 1 ? 's' : ''}).</p>`
    );
  } else if (stats.invalid > 0) {
    lines.push('<p>Invalid runs recorded but no classified error types yet.</p>');
  }

  const byMut = stats.by_mutation || {};
  let bestType = null;
  let bestPct = -1;
  Object.entries(byMut).forEach(([type, counts]) => {
    const total = (counts.valid || 0) + (counts.invalid || 0);
    if (total > 0) {
      const pct = (counts.valid / total) * 100;
      if (pct > bestPct) {
        bestPct = pct;
        bestType = type;
      }
    }
  });
  if (bestType) {
    lines.push(
      `<p>Best mutation type for valid IR: <strong>${bestType}</strong> (${bestPct.toFixed(1)}%).</p>`
    );
  }

  lines.push(
    `<p>Potential compiler bugs found: <strong>${stats.interesting}</strong>.</p>`
  );

  if (stats.valid > 0) {
    lines.push(
      `<p>Among valid IR, <strong>${stats.mismatch_pct}%</strong> showed O0/O3 mismatches (${stats.mismatch} of ${stats.valid}).</p>`
    );
  }

  return lines.join('');
}
