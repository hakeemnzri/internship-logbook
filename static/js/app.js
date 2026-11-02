document.addEventListener('DOMContentLoaded', () => {
  document.querySelectorAll('.toast').forEach((node) => new bootstrap.Toast(node, {delay: 5000}).show());

  // Theme toggle. The starting theme is set by a small script in base.html to avoid a flash.
  const root = document.documentElement;
  const themeToggle = document.getElementById('themeToggle');
  const showThemeButton = () => {
    if (!themeToggle) return;
    const dark = root.dataset.bsTheme === 'dark';
    themeToggle.innerHTML = `<i class="bi bi-${dark ? 'sun' : 'moon'}"></i>`;
    themeToggle.setAttribute('aria-label', dark ? 'Switch to light theme' : 'Switch to dark theme');
  };
  showThemeButton();
  themeToggle?.addEventListener('click', () => {
    root.dataset.bsTheme = root.dataset.bsTheme === 'dark' ? 'light' : 'dark';
    try { localStorage.setItem('theme', root.dataset.bsTheme); } catch (error) { /* storage blocked */ }
    showThemeButton();
  });

  // Mobile menu
  const sidebar = document.getElementById('sidebar');
  const backdrop = document.getElementById('sidebarBackdrop');
  const menuButton = document.getElementById('sidebarToggle');
  const setMenu = (open) => {
    sidebar?.classList.toggle('show', open);
    if (backdrop) backdrop.hidden = !open;
    menuButton?.setAttribute('aria-expanded', String(open));
  };
  menuButton?.addEventListener('click', () => setMenu(!sidebar.classList.contains('show')));
  backdrop?.addEventListener('click', () => setMenu(false));
  document.addEventListener('keydown', (event) => { if (event.key === 'Escape' && sidebar?.classList.contains('show')) { setMenu(false); menuButton.focus(); } });

  document.querySelectorAll('.password-toggle').forEach((button) => button.addEventListener('click', () => {
    const input = button.previousElementSibling;
    const visible = input.type === 'password';
    input.type = visible ? 'text' : 'password';
    button.innerHTML = `<i class="bi bi-eye${visible ? '-slash' : ''}"></i>`;
    button.setAttribute('aria-label', visible ? 'Hide password' : 'Show password');
  }));

  document.querySelectorAll('[data-confirm]').forEach((form) => form.addEventListener('submit', (event) => {
    if (!confirm(form.dataset.confirm)) event.preventDefault();
  }));

  const entryForm = document.getElementById('entryForm');
  if (entryForm) setUpEntryEditor(entryForm);
});

function setUpEntryEditor(form) {
  const list = document.getElementById('activityList');
  const template = document.getElementById('activityTemplate');
  const totalTime = document.getElementById('totalTime');
  const editor = document.getElementById('richEditor');
  const hidden = document.getElementById('description');
  let unsaved = false;

  const minutes = (value) => {
    if (!value) return null;
    const [hours, mins] = value.split(':').map(Number);
    return hours * 60 + mins;
  };
  const formatMinutes = (total) => {
    const hours = Math.floor(total / 60), rest = total % 60;
    if (hours && rest) return `${hours} h ${rest} min`;
    return hours ? `${hours} h` : `${rest} min`;
  };

  // Show the total time and mark rows where the end time is not after the start time.
  const refresh = () => {
    let total = 0;
    list.querySelectorAll('.activity-item').forEach((item) => {
      const start = minutes(item.querySelector('.activity-start').value);
      const end = minutes(item.querySelector('.activity-end').value);
      const wrong = start !== null && end !== null && end <= start;
      item.querySelector('.activity-end').classList.toggle('is-invalid', wrong);
      if (start !== null && end !== null && !wrong) total += end - start;
    });
    totalTime.textContent = total ? `Total ${formatMinutes(total)}` : '';
  };

  // A new row starts when the previous one ended, because most days are logged in order.
  const addRow = () => {
    const rows = list.querySelectorAll('.activity-item');
    const lastEnd = rows.length ? rows[rows.length - 1].querySelector('.activity-end').value : '';
    list.append(template.content.cloneNode(true));
    const row = list.lastElementChild;
    row.querySelector('.activity-start').value = lastEnd;
    (lastEnd ? row.querySelector('.activity-end') : row.querySelector('.activity-start')).focus();
    refresh();
  };

  document.getElementById('addActivity').addEventListener('click', addRow);

  list.addEventListener('click', (event) => {
    const button = event.target.closest('.remove-activity');
    if (!button) return;
    const item = button.closest('.activity-item');
    unsaved = true;
    if (list.children.length === 1) {
      item.querySelectorAll('input').forEach((input) => { input.value = ''; });
      item.querySelector('.activity-start').focus();
    } else {
      const next = item.nextElementSibling || item.previousElementSibling;
      item.remove();
      next.querySelector('.activity-description').focus();
    }
    refresh();
  });

  // Enter in a description adds the next row instead of submitting the whole form.
  list.addEventListener('keydown', (event) => {
    if (event.key === 'Enter' && event.target.classList.contains('activity-description')) {
      event.preventDefault();
      const item = event.target.closest('.activity-item');
      if (item.nextElementSibling) item.nextElementSibling.querySelector('.activity-start').focus();
      else addRow();
    }
  });

  list.addEventListener('input', refresh);
  refresh();

  document.querySelectorAll('[data-command]').forEach((button) => button.addEventListener('click', () => {
    editor.focus();
    document.execCommand(button.dataset.command, false, button.dataset.value || null);
  }));
  document.getElementById('linkButton').addEventListener('click', () => {
    const url = prompt('Link address (https://…)');
    if (url) { editor.focus(); document.execCommand('createLink', false, url); }
  });

  // Warn before leaving the page with unsaved changes.
  form.addEventListener('input', () => { unsaved = true; });
  window.addEventListener('beforeunload', (event) => { if (unsaved) event.preventDefault(); });
  form.addEventListener('submit', () => {
    hidden.value = editor.innerHTML;
    unsaved = false;
  });
}
