/* ── CodeMentor — Teacher Dashboard JS ─────────────────────── */

const ACCENT  = '#4fffb0';
const ACCENT2 = '#7c6af7';
const ACCENT3 = '#ff6b6b';
const ACCENT4 = '#ffd166';
const MUTED   = '#7a82a0';
const BORDER  = '#2a3050';

Chart.defaults.color = MUTED;
Chart.defaults.borderColor = BORDER;
Chart.defaults.font.family = "'Sora', sans-serif";

let activityChart = null;
let actionChart   = null;

// ── Build charts ────────────────────────────────────────────────
function buildCharts(data) {
  const actCtx = document.getElementById('activityChart');
  const actAct = document.getElementById('actionChart');

  // Destroy previous instances
  if (activityChart) activityChart.destroy();
  if (actionChart)   actionChart.destroy();

  // Activity line chart
  activityChart = new Chart(actCtx, {
    type: 'line',
    data: {
      labels: Object.keys(data.daily_activity),
      datasets: [{
        label: 'Sessions',
        data: Object.values(data.daily_activity),
        borderColor: ACCENT,
        backgroundColor: 'rgba(79,255,176,0.08)',
        borderWidth: 2,
        pointBackgroundColor: ACCENT,
        pointRadius: 3,
        tension: 0.4,
        fill: true,
      }]
    },
    options: {
      responsive: true,
      plugins: { legend: { display: false } },
      scales: {
        x: { grid: { color: BORDER }, ticks: { maxTicksLimit: 7 } },
        y: { grid: { color: BORDER }, beginAtZero: true, ticks: { stepSize: 1 } },
      }
    }
  });

  // Action doughnut chart
  const actionLabels = Object.keys(data.action_data);
  const actionIcons  = { explain:'🔍', debug:'🐛', improve:'✨', concept:'📚', quiz:'🎯', review:'📋' };
  const colors = [ACCENT, ACCENT2, ACCENT3, ACCENT4, '#4fc3f7', '#a5d6a7'];

  actionChart = new Chart(actAct, {
    type: 'doughnut',
    data: {
      labels: actionLabels.map(a => `${actionIcons[a]||''} ${a}`),
      datasets: [{
        data: actionLabels.map(a => data.action_data[a]),
        backgroundColor: colors.map(c => c + '99'),
        borderColor: colors,
        borderWidth: 2,
      }]
    },
    options: {
      responsive: true,
      plugins: {
        legend: {
          position: 'bottom',
          labels: { font: { size: 11 }, padding: 8, boxWidth: 12 }
        }
      },
      cutout: '60%',
    }
  });
}

// ── Fetch & render ───────────────────────────────────────────────
async function loadStats(cohort = 'all') {
  try {
    const res  = await fetch(`/dashboard/api/stats?cohort=${encodeURIComponent(cohort)}`);
    const data = await res.json();
    buildCharts(data);
  } catch (err) {
    console.error('Failed to load stats:', err);
  }
}

// ── Cohort filter buttons ────────────────────────────────────────
document.querySelectorAll('.cohort-btn').forEach(btn => {
  btn.addEventListener('click', () => {
    document.querySelectorAll('.cohort-btn').forEach(b => b.classList.remove('active'));
    btn.classList.add('active');
    loadStats(btn.dataset.cohort);
  });
});

// ── Init ─────────────────────────────────────────────────────────
loadStats('all');