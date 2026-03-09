/**
 * qr_refresh.js
 * Handles automatic QR code rotation on the teacher's QR display page.
 *
 * Called from qr_display.html as:
 *   startQRRefresh(refreshInterval, sessionId, refreshUrl);
 */

/**
 * @param {number} intervalSeconds   How often to rotate the QR (e.g. 20)
 * @param {number} sessionId         The attendance session ID
 * @param {string} refreshUrl        POST URL for /teacher/refresh_qr/<session_id>
 */
function startQRRefresh(intervalSeconds, sessionId, refreshUrl) {
  const qrImage        = document.getElementById('qr-image');
  const countdownText  = document.getElementById('countdown-text');
  const refreshSeconds = document.getElementById('refresh-seconds');
  const ring           = document.getElementById('countdown-ring');
  const expiredMsg     = document.getElementById('session-expired-msg');
  const qrOverlay      = document.getElementById('qr-overlay');
  const btnRefresh     = document.getElementById('btn-refresh');

  // SVG ring circumference = 2πr where r = 35 → ~220
  const CIRCUMFERENCE = 2 * Math.PI * 35;

  let secondsLeft = intervalSeconds;

  // Declare timer handles here so they are accessible in all nested closures
  let countdownTimer;
  let refreshTimer;

  /**
   * Update the SVG countdown ring and text labels.
   */
  function updateCountdown() {
    const fraction    = secondsLeft / intervalSeconds;
    const dashOffset  = CIRCUMFERENCE * (1 - fraction);

    if (ring) {
      ring.style.strokeDasharray  = CIRCUMFERENCE;
      ring.style.strokeDashoffset = dashOffset;
    }
    if (countdownText)  countdownText.textContent  = secondsLeft;
    if (refreshSeconds) refreshSeconds.textContent = secondsLeft;
  }

  /**
   * Call the server to rotate the QR token and update the displayed image.
   */
  function refreshQR() {
    if (qrImage) qrImage.classList.add('refreshing');
    if (btnRefresh) btnRefresh.disabled = true;

    fetch(refreshUrl, {
      method: 'POST',
      headers: { 'X-Requested-With': 'XMLHttpRequest' },
      credentials: 'same-origin',
    })
      .then(function (response) { return response.json(); })
      .then(function (data) {
        if (data.expired) {
          // Session has expired – show overlay and message
          if (qrOverlay)  qrOverlay.style.display = 'flex';
          if (expiredMsg) expiredMsg.classList.remove('d-none');
          if (ring)       ring.style.stroke = '#dc3545';
          clearInterval(countdownTimer);
          clearInterval(refreshTimer);
          return;
        }

        // Update the QR image
        if (qrImage) {
          qrImage.src = 'data:image/png;base64,' + data.qr_b64;
        }

        // Reset countdown
        secondsLeft = intervalSeconds;
        updateCountdown();
      })
      .catch(function (err) {
        console.warn('QR refresh failed:', err);
      })
      .finally(function () {
        if (qrImage)    qrImage.classList.remove('refreshing');
        if (btnRefresh) btnRefresh.disabled = false;
      });
  }

  // Expose refreshQR globally so the "Refresh Now" button can call it
  window.refreshQR = refreshQR;

  // Tick countdown every second
  updateCountdown();
  countdownTimer = setInterval(function () {
    secondsLeft -= 1;
    if (secondsLeft < 0) secondsLeft = 0;
    updateCountdown();
  }, 1000);

  // Trigger QR refresh every intervalSeconds
  refreshTimer = setInterval(refreshQR, intervalSeconds * 1000);
}
