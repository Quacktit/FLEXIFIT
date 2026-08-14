// FLEXIFIT —contact form submission

document.addEventListener('DOMContentLoaded', function () {
  var form = document.getElementById('contact-form');
  if (!form) return;

  var msg = document.getElementById('contact-msg');
  var btn = form.querySelector('button[type="submit"]');

  form.addEventListener('submit', function (e) {
    e.preventDefault();

    var payload = {
      name: form.name.value.trim(),
      email: form.email.value.trim(),
      phone: form.phone.value.trim(),
      subject: form.subject.value,
      message: form.message.value.trim()
    };

    if (!payload.name || !payload.email || !payload.message) {
      showMsg('Please fill in your name, email and message.', 'err');
      return;
    }

    btn.disabled = true;
    btn.textContent = 'Sending...';

    fetch('https://flexifit-tnrc.onrender.com/api/contact', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    })
      .then(function (res) { return res.json().then(function (data) { return { ok: res.ok, data: data }; }); })
      .then(function (result) {
        if (result.ok) {
          showMsg('Message sent — our team will get back to you within one business day.', 'ok');
          form.reset();
        } else {
          showMsg(result.data.error || 'Something went wrong. Please call us instead.', 'err');
        }
      })
      .catch(function () {
        showMsg('Could not reach the server. Please try again or call us directly.', 'err');
      })
      .finally(function () {
        btn.disabled = false;
        btn.textContent = 'Send Message';
      });
  });

  function showMsg(text, kind) {
    msg.textContent = text;
    msg.className = 'form-msg show ' + kind;
  }
});
