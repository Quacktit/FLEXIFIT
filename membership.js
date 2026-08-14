// FLEXIFIT — membership signup form + plan selection

document.addEventListener('DOMContentLoaded', function () {

  /* clicking "Choose plan" scrolls to the form and pre-selects the plan */
  document.querySelectorAll('[data-plan]').forEach(function (btn) {
    btn.addEventListener('click', function (e) {
      e.preventDefault();
      var plan = btn.getAttribute('data-plan');
      var select = document.getElementById('plan');
      if (select) select.value = plan;
      var target = document.getElementById('join-form');
      if (target) target.scrollIntoView({ behavior: 'smooth', block: 'start' });
    });
  });

  var form = document.getElementById('membership-form');
  if (!form) return;

  var msg = document.getElementById('membership-msg');
  var btn = form.querySelector('button[type="submit"]');

  form.addEventListener('submit', function (e) {
    e.preventDefault();

    var payload = {
      name: form.name.value.trim(),
      email: form.email.value.trim(),
      phone: form.phone.value.trim(),
      plan: form.plan.value,
      goal: form.goal.value,
      start_date: form.start_date.value,
      notes: form.notes.value.trim()
    };

    if (!payload.name || !payload.email || !payload.phone || !payload.plan) {
      showMsg('Please fill in your name, email, phone and choose a plan.', 'err');
      return;
    }

    btn.disabled = true;
    btn.textContent = 'Submitting...';

    fetch('/api/membership', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    })
      .then(function (res) { return res.json().then(function (data) { return { ok: res.ok, data: data }; }); })
      .then(function (result) {
        if (result.ok) {
          showMsg('Application received — our membership team will call you within 24 hours to confirm your start date.', 'ok');
          form.reset();
        } else {
          showMsg(result.data.error || 'Something went wrong. Please call the front desk instead.', 'err');
        }
      })
      .catch(function () {
        showMsg('Could not reach the server. Please try again or call the front desk.', 'err');
      })
      .finally(function () {
        btn.disabled = false;
        btn.textContent = 'Submit Application';
      });
  });

  function showMsg(text, kind) {
    msg.textContent = text;
    msg.className = 'form-msg show ' + kind;
  }
});
