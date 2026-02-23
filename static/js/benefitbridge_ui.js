/**
 * BenefitBridge Premium UI Interactions
 * Lightweight Vanilla JS
 */

document.addEventListener('DOMContentLoaded', () => {
    // 1. Prevent Double Submit & Add Loading Spinner
    const forms = document.querySelectorAll('form');
    forms.forEach(form => {
        form.addEventListener('submit', function (e) {
            // Find submit button
            const btn = this.querySelector('button[type="submit"]');
            if (btn && !btn.disabled) {
                // Disable button to prevent double submit
                btn.disabled = true;

                // Add loading spinner using Bootstrap markup if not already there
                const originalText = btn.innerHTML;
                btn.dataset.originalText = originalText;
                btn.innerHTML = `<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span> Processing...`;
            }
        });
    });

    // 2. OTP Auto-Advance Logic
    const otpInputs = document.querySelectorAll('.otp-input');
    if (otpInputs.length > 0) {
        otpInputs.forEach((input, index) => {
            input.addEventListener('keyup', function (e) {
                if (this.value.length === 1) {
                    if (index < otpInputs.length - 1) {
                        otpInputs[index + 1].focus();
                    }
                }
                // Handle backspace
                if (e.key === 'Backspace' && this.value.length === 0) {
                    if (index > 0) {
                        otpInputs[index - 1].focus();
                        otpInputs[index - 1].value = '';
                    }
                }
            });
        });
    }

    // 3. Bootstrap Tooltip Initialization
    if (typeof bootstrap !== 'undefined') {
        const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
        tooltipTriggerList.map(function (tooltipTriggerEl) {
            return new bootstrap.Tooltip(tooltipTriggerEl);
        });
    }

    // 4. Mobile Sidebar Toggle
    const sidebarToggle = document.getElementById('bb-sidebar-toggle');
    const sidebar = document.querySelector('.bb-sidebar');
    if (sidebarToggle && sidebar) {
        sidebarToggle.addEventListener('click', () => {
            sidebar.classList.toggle('show');
        });
    }
});
