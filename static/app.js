(function () {
  'use strict';

  // ---- Toast: tutup otomatis setelah 6 detik, atau lewat tombol x
  document.querySelectorAll('.toast').forEach(function (t) {
    var tutup = function () { t.classList.add('out'); setTimeout(function () { t.remove(); }, 260); };
    var btn = t.querySelector('button');
    if (btn) btn.addEventListener('click', tutup);
    setTimeout(tutup, 6000);
  });

  // ---- Konfirmasi sebelum aksi berbahaya: <form data-confirm="Judul|Penjelasan|Label tombol">
  var dlg = document.getElementById('confirmDialog');
  if (dlg && typeof dlg.showModal === 'function') {
    var pending = null;
    document.addEventListener('submit', function (e) {
      var form = e.target;
      var teks = form.getAttribute && form.getAttribute('data-confirm');
      if (!teks || form.dataset.confirmed === '1') return;
      e.preventDefault();
      var p = teks.split('|');
      dlg.querySelector('[data-c-title]').textContent = p[0] || 'Lanjutkan?';
      dlg.querySelector('[data-c-text]').textContent = p[1] || '';
      dlg.querySelector('[data-c-ok]').textContent = p[2] || 'Ya, lanjutkan';
      pending = form;
      dlg.showModal();
    });
    dlg.querySelector('[data-c-ok]').addEventListener('click', function () {
      if (pending) { pending.dataset.confirmed = '1'; pending.submit(); }
      dlg.close();
    });
    dlg.querySelector('[data-c-cancel]').addEventListener('click', function () { pending = null; dlg.close(); });
  }

  // ---- Filter tabel/daftar: kolom cari + chip status
  document.querySelectorAll('[data-filter-scope]').forEach(function (scope) {
    var rows = Array.prototype.slice.call(scope.querySelectorAll('[data-row]'));
    var input = scope.querySelector('[data-filter-input]');
    var chips = Array.prototype.slice.call(scope.querySelectorAll('[data-chip]'));
    var kosong = scope.querySelector('[data-filter-empty]');
    var aktif = (scope.querySelector('[data-chip][aria-pressed="true"]') || {}).dataset;
    var chipAktif = aktif ? aktif.chip : 'semua';

    function cocokChip(row) {
      if (chipAktif === 'semua') return true;
      if (chipAktif === 'belum_lunas') return row.dataset.bayar !== 'Lunas';
      return row.dataset.state === chipAktif;
    }
    function terapkan() {
      var q = input ? input.value.trim().toLowerCase() : '';
      var tampil = 0;
      rows.forEach(function (r) {
        var ok = cocokChip(r) && (!q || (r.dataset.text || r.textContent).toLowerCase().indexOf(q) > -1);
        r.hidden = !ok;
        if (ok) tampil++;
      });
      if (kosong) kosong.hidden = tampil > 0;
    }
    chips.forEach(function (c) {
      c.addEventListener('click', function () {
        chipAktif = c.dataset.chip;
        chips.forEach(function (x) { x.setAttribute('aria-pressed', x === c ? 'true' : 'false'); });
        terapkan();
      });
    });
    if (input) input.addEventListener('input', terapkan);
    terapkan();
  });

  // ---- Lihat/sembunyikan password
  document.querySelectorAll('[data-pw-toggle]').forEach(function (btn) {
    btn.addEventListener('click', function () {
      var input = document.getElementById(btn.getAttribute('data-pw-toggle'));
      var tampak = input.type === 'text';
      input.type = tampak ? 'password' : 'text';
      btn.textContent = tampak ? 'Lihat' : 'Sembunyikan';
      btn.setAttribute('aria-pressed', String(!tampak));
    });
  });

  // ---- Tab anak di portal orang tua
  var tabs = document.querySelectorAll('[data-child-tab]');
  if (tabs.length) {
    var panels = document.querySelectorAll('[data-child-panel]');
    tabs.forEach(function (tab) {
      tab.addEventListener('click', function () {
        var id = tab.getAttribute('data-child-tab');
        tabs.forEach(function (t) { t.setAttribute('aria-selected', String(t === tab)); });
        panels.forEach(function (p) { p.hidden = p.getAttribute('data-child-panel') !== id; });
      });
    });
  }
})();
