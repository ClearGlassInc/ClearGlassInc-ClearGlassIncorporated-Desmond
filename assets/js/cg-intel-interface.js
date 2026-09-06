document.addEventListener('DOMContentLoaded', function () {
  var buttons = Array.prototype.slice.call(document.querySelectorAll('.cg-btn'));

  buttons.forEach(function (button) {
    button.addEventListener('pointermove', function (event) {
      if (button.disabled || button.classList.contains('is-disabled')) return;
      var rect = button.getBoundingClientRect();
      var x = ((event.clientX - rect.left) / rect.width) * 100;
      var y = ((event.clientY - rect.top) / rect.height) * 100;
      var tiltY = ((event.clientX - rect.left) / rect.width - 0.5) * 7;
      var tiltX = ((event.clientY - rect.top) / rect.height - 0.5) * -5;
      button.style.setProperty('--x', x + '%');
      button.style.setProperty('--y', y + '%');
      button.style.setProperty('--tilt-x', tiltX + 'deg');
      button.style.setProperty('--tilt-y', tiltY + 'deg');
    });

    button.addEventListener('pointerleave', function () {
      button.style.setProperty('--x', '50%');
      button.style.setProperty('--y', '50%');
      button.style.setProperty('--tilt-x', '0deg');
      button.style.setProperty('--tilt-y', '0deg');
    });

    button.addEventListener('click', function (event) {
      if (button.disabled || button.classList.contains('is-disabled')) return;
      var rect = button.getBoundingClientRect();
      var ripple = document.createElement('span');
      ripple.className = 'cg-ripple';
      ripple.style.left = (event.clientX - rect.left) + 'px';
      ripple.style.top = (event.clientY - rect.top) + 'px';
      button.appendChild(ripple);
      window.setTimeout(function () { ripple.remove(); }, 700);
    });
  });

  Array.prototype.slice.call(document.querySelectorAll('[data-loading-button]')).forEach(function (button) {
    button.addEventListener('click', function () {
      if (button.getAttribute('aria-busy') === 'true') return;
      var original = button.innerHTML;
      button.setAttribute('aria-busy', 'true');
      button.innerHTML = '<span class="cg-loader" aria-hidden="true"></span> Processing Signal';
      window.setTimeout(function () {
        button.innerHTML = original;
        button.removeAttribute('aria-busy');
      }, 1600);
    });
  });
});
