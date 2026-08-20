// FLEXIFIT —shared site behaviour, loaded on every page

document.addEventListener('DOMContentLoaded', function () {

  /* mobile nav toggle */
  var toggle = document.querySelector('.nav-toggle');
  var links = document.querySelector('.nav-links');
  function closeMobileNav() {
    if (!links) return;
    links.classList.remove('open');
    if (toggle) { toggle.classList.remove('open'); toggle.setAttribute('aria-expanded', 'false'); }
    document.body.classList.remove('nav-open');
  }
  if (toggle && links) {
    toggle.addEventListener('click', function () {
      var opening = !links.classList.contains('open');
      links.classList.toggle('open', opening);
      toggle.classList.toggle('open', opening);
      toggle.setAttribute('aria-expanded', opening ? 'true' : 'false');
      document.body.classList.toggle('nav-open', opening);
    });
    links.querySelectorAll('a').forEach(function (a) {
      a.addEventListener('click', closeMobileNav);
    });
    document.addEventListener('keydown', function (e) {
      if (e.key === 'Escape') closeMobileNav();
    });
  }

  var mapWrap = document.querySelector('.map-wrap');
  if (mapWrap) {
    mapWrap.addEventListener('click', function () {
      mapWrap.classList.add('active');
      var frame = mapWrap.querySelector('.map-frame');
      if (frame) frame.classList.add('active');
    });
  }

  /* mark active nav link based on current file */
  var current = window.location.pathname.split('/').pop() || 'index.html';
  document.querySelectorAll('.nav-links a').forEach(function (a) {
    var href = a.getAttribute('href');
    if (href === current || (current === '' && href === 'index.html')) {
      a.classList.add('active');
    }
  });

  /* footer year */
  document.querySelectorAll('[data-year]').forEach(function (el) {
    el.textContent = new Date().getFullYear();
  });

  /* scroll reveal for elements marked .reveal */
  var revealEls = document.querySelectorAll('.reveal');
  if ('IntersectionObserver' in window && revealEls.length) {
    var io = new IntersectionObserver(function (entries) {
      entries.forEach(function (entry) {
        if (entry.isIntersecting) {
          entry.target.classList.add('in');
          io.unobserve(entry.target);
        }
      });
    }, { threshold: 0.15 });
    revealEls.forEach(function (el) { io.observe(el); });
  } else {
    revealEls.forEach(function (el) { el.classList.add('in'); });
  }

});
