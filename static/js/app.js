document.addEventListener('DOMContentLoaded', () => {
  document.querySelectorAll('.toast').forEach((node) => new bootstrap.Toast(node, {delay: 4500}).show());
  const root = document.documentElement, savedTheme = localStorage.getItem('theme');
  if (savedTheme) root.dataset.bsTheme = savedTheme;
  document.getElementById('themeToggle')?.addEventListener('click', () => { root.dataset.bsTheme = root.dataset.bsTheme === 'dark' ? 'light' : 'dark'; localStorage.setItem('theme', root.dataset.bsTheme); });
  document.getElementById('sidebarToggle')?.addEventListener('click', () => document.querySelector('.sidebar').classList.toggle('show'));
  document.querySelectorAll('.password-toggle').forEach((button) => button.addEventListener('click', () => {
    const input = button.previousElementSibling;
    const visible = input.type === 'password';
    input.type = visible ? 'text' : 'password';
    button.innerHTML = `<i class="bi bi-eye${visible ? '-slash' : ''}"></i>`;
    button.setAttribute('aria-label', visible ? 'Hide password' : 'Show password');
  }));
  document.querySelectorAll('[data-confirm]').forEach((form) => form.addEventListener('submit', (event) => { if (!confirm(form.dataset.confirm)) event.preventDefault(); }));
  document.querySelectorAll('form').forEach((form) => form.addEventListener('submit', () => document.getElementById('loading')?.classList.remove('d-none')));
  const list = document.getElementById('activityList'), template = document.getElementById('activityTemplate');
  document.getElementById('addActivity')?.addEventListener('click', () => list.append(template.content.cloneNode(true)));
  list?.addEventListener('click', (event) => { const button = event.target.closest('.remove-activity'); if (button) button.closest('.activity-item').remove(); });
  let dragging;
  list?.addEventListener('dragstart', (event) => { dragging = event.target.closest('.activity-item'); });
  list?.addEventListener('dragover', (event) => { event.preventDefault(); const target = event.target.closest('.activity-item'); if (target && target !== dragging) list.insertBefore(dragging, target); });
  list?.querySelectorAll('.activity-item').forEach((item) => item.draggable = true);
  new MutationObserver(() => list?.querySelectorAll('.activity-item').forEach((item) => item.draggable = true)).observe(list || document.body, {childList:true});
  const editor = document.getElementById('richEditor'), hidden = document.getElementById('description');
  document.querySelectorAll('[data-command]').forEach((button) => button.addEventListener('click', () => { document.execCommand(button.dataset.command, false, button.dataset.value || null); editor.focus(); }));
  document.getElementById('linkButton')?.addEventListener('click', () => { const url = prompt('Link URL'); if (url) document.execCommand('createLink', false, url); });
  document.getElementById('entryForm')?.addEventListener('submit', () => { hidden.value = editor.innerHTML; });
});
