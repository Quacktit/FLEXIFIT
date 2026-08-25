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


document.addEventListener('DOMContentLoaded', () => {
  // 1. Countdown Timer (Target: August 29, 2026 at 00:00 AM)
  const countDownDate = new Date("August 29, 2026 00:00:00").getTime(); 
  
  const timerInterval = setInterval(() => {
    const now = new Date().getTime();
    const distance = countDownDate - now;
    
    // Stop the timer when it hits zero
    if (distance < 0) {
      clearInterval(timerInterval);
      document.querySelectorAll('.timer').forEach(el => el.innerHTML = "OFFER EXPIRED");
      return;
    }

    // Calculate time
    const days = Math.floor(distance / (1000 * 60 * 60 * 24));
    const hours = Math.floor((distance % (1000 * 60 * 60 * 24)) / (1000 * 60 * 60));
    const minutes = Math.floor((distance % (1000 * 60 * 60)) / (1000 * 60));
    const seconds = Math.floor((distance % (1000 * 60)) / 1000Let's troubleshoot why the pop-up isn't triggering on the site shown in `image_b3fc03.png`. Since I can't see the underlying code, we'll need to run through the standard front-end debugging steps to isolate the issue.

Here is a checklist to help figure out what's going wrong:

### 1. Check the Developer Console for Errors
The most common reason a JavaScript-triggered modal or pop-up fails is a script error breaking the execution.
*   **Action:** Press **F12** or right-click on the page and select **Inspect**.
*   Navigate to the **Console** tab.
*   Click the button or link that is supposed to trigger the pop-up (e.g., "CLAIM NOW" or "JOIN NOW").
*   **Look for:** Any red text indicating a `TypeError` (like a missing ID or undefined variable) or a `ReferenceError`.

### 2. Verify the Event Listener
If there are no errors in the console, the button might not be communicating with your JavaScript properly.
*   Ensure the ID or class used in your HTML button matches exactly what you are targeting in your `addEventListener` or `onclick` function in the JS file. 
*   If you are using a framework, ensure the component state is updating correctly on click.

### 3. Inspect the CSS (Display and Z-Index)
Sometimes the JavaScript works perfectly, but the pop-up is hidden visually.
*   **Action:** In the Developer Tools, go to the **Elements** tab.
*   Search for the HTML container of your pop-up (e.g., `<div id="myModal">`).
*   **Look for:**
    *   Is it stuck on `display: none;` or `visibility: hidden;`? If so, the JavaScript isn't properly toggling the class.
    *   Does it have a low `z-index`? It might be opening but rendering *behind* the main content or the hero image. Try adding `z-index: 9999;` to the pop-up container.

### 4. Clear the Cache
Since the site is deployed on Render (`flexifit-1-avtf.onrender.com`), your browser might be loading an older, cached version of your JavaScript or CSS file where the pop-up logic wasn't fully implemented or had a bug.
*   **Action:** Perform a hard refresh by pressing **Ctrl + F5**.

Are you trying to trigger a custom HTML/CSS modal within the page, or are you trying to open a new browser window entirely (which might be getting caught by Chrome's pop-up blocker)?
