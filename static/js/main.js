/**
 * Build Bright University (BBU) — Main JavaScript
 * Micro-interactions: Theme toggling, auto-dismiss alerts, back-to-top,
 * live avatar upload preview, live grade calculation, and form double-submit protection.
 */

document.addEventListener('DOMContentLoaded', function () {
    // -------------------------------------------------------------------------
    // 1. Dark Mode & Theme Toggle
    // -------------------------------------------------------------------------
    const themeToggleBtn = document.getElementById('theme-toggle-btn');
    const themeIcon = document.getElementById('theme-icon');

    function updateThemeIcon(theme) {
        if (!themeIcon) return;
        if (theme === 'dark') {
            themeIcon.className = 'fa-solid fa-sun';
            themeIcon.style.color = 'var(--bbu-gold)';
        } else {
            themeIcon.className = 'fa-solid fa-moon';
            themeIcon.style.color = '';
        }
    }

    // Set initial icon based on current document attribute
    const currentTheme = document.documentElement.getAttribute('data-bs-theme') || 'light';
    updateThemeIcon(currentTheme);

    if (themeToggleBtn) {
        themeToggleBtn.addEventListener('click', function () {
            const activeTheme = document.documentElement.getAttribute('data-bs-theme') || 'light';
            const newTheme = activeTheme === 'dark' ? 'light' : 'dark';
            document.documentElement.setAttribute('data-bs-theme', newTheme);
            localStorage.setItem('bbu-theme', newTheme);
            updateThemeIcon(newTheme);
            window.dispatchEvent(new CustomEvent('bbuThemeChanged', { detail: { theme: newTheme } }));
        });
    }

    // -------------------------------------------------------------------------
    // 2. Auto-Dismiss Alert Messages
    // -------------------------------------------------------------------------
    const alerts = document.querySelectorAll('.alert.alert-dismissible');
    alerts.forEach(function (alert) {
        setTimeout(function () {
            alert.style.transition = 'opacity 0.5s cubic-bezier(0.4, 0, 0.2, 1)';
            alert.style.opacity = '0';
            setTimeout(function () {
                alert.remove();
            }, 500);
        }, 5000);
    });

    // -------------------------------------------------------------------------
    // 3. Back-to-Top Floating Button
    // -------------------------------------------------------------------------
    const backToTopBtn = document.getElementById('back-to-top');
    if (backToTopBtn) {
        window.addEventListener('scroll', function () {
            if (window.scrollY > 280) {
                backToTopBtn.style.display = 'flex';
            } else {
                backToTopBtn.style.display = 'none';
            }
        });

        backToTopBtn.addEventListener('click', function () {
            window.scrollTo({ top: 0, behavior: 'smooth' });
        });
    }

    // -------------------------------------------------------------------------
    // 4. Live Photo Upload Preview
    // -------------------------------------------------------------------------
    const fileInputs = document.querySelectorAll('input[type="file"][name*="profile_picture"]');
    fileInputs.forEach(function (input) {
        input.addEventListener('change', function (event) {
            const file = event.target.files[0];
            if (file) {
                const reader = new FileReader();
                reader.onload = function (e) {
                    const previewImg = document.getElementById('avatar-preview-img');
                    const placeholder = document.getElementById('avatar-preview-placeholder');
                    if (previewImg) {
                        previewImg.src = e.target.result;
                        previewImg.style.display = 'block';
                    }
                    if (placeholder) {
                        placeholder.style.display = 'none';
                    }
                };
                reader.readAsDataURL(file);
            }
        });
    });

    // -------------------------------------------------------------------------
    // 5. Live Grade Calculation (for Add Grade Form)
    // -------------------------------------------------------------------------
    const scoreInput = document.querySelector('input[name="score"]');
    const liveGradeDisplay = document.getElementById('live-grade-preview');
    if (scoreInput && liveGradeDisplay) {
        function calcGrade(scoreVal) {
            const val = parseFloat(scoreVal);
            if (isNaN(val)) return '—';
            if (val >= 90) return 'A (4.0)';
            if (val >= 80) return 'B (3.0)';
            if (val >= 70) return 'C (2.0)';
            if (val >= 60) return 'D (1.0)';
            return 'F (0.0)';
        }
        scoreInput.addEventListener('input', function () {
            liveGradeDisplay.textContent = calcGrade(scoreInput.value);
        });
    }

    // -------------------------------------------------------------------------
    // 6. Form Submission Double-Post Protection & Loading Spinner
    // -------------------------------------------------------------------------
    const forms = document.querySelectorAll('form:not([data-no-disable])');
    forms.forEach(function (form) {
        form.addEventListener('submit', function () {
            const submitBtn = form.querySelector('button[type="submit"]');
            if (submitBtn && !submitBtn.disabled) {
                setTimeout(function () {
                    submitBtn.disabled = true;
                    submitBtn.innerHTML = '<span class="spinner-border spinner-border-sm me-2" role="status" aria-hidden="true"></span> Processing...';
                }, 20);
            }
        });
    });

    // -------------------------------------------------------------------------
    // 7. Initialize Bootstrap Tooltips
    // -------------------------------------------------------------------------
    if (typeof bootstrap !== 'undefined' && bootstrap.Tooltip) {
        const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"], [title]:not([data-bs-toggle])'));
        tooltipTriggerList.map(function (tooltipTriggerEl) {
            return new bootstrap.Tooltip(tooltipTriggerEl);
        });
    }

    // -------------------------------------------------------------------------
    // 8. Progress Bars initialization via data-progress attribute
    // -------------------------------------------------------------------------
    const progressBars = document.querySelectorAll('[data-progress]');
    progressBars.forEach(function (bar) {
        const val = parseFloat(bar.getAttribute('data-progress')) || 0;
        bar.style.width = Math.min(Math.max(val, 0), 100) + '%';
    });

    // -------------------------------------------------------------------------
    // 9. Universal Keyboard Shortcuts (/, Escape, Alt+T)
    // -------------------------------------------------------------------------
    document.addEventListener('keydown', function (e) {
        // Alt + T to toggle theme
        if (e.altKey && (e.key === 't' || e.key === 'T')) {
            e.preventDefault();
            if (themeToggleBtn) themeToggleBtn.click();
            return;
        }

        // Avoid capturing keys when user is typing in form elements
        const activeTag = document.activeElement ? document.activeElement.tagName.toLowerCase() : '';
        const isEditable = activeTag === 'input' || activeTag === 'textarea' || activeTag === 'select' || (document.activeElement && document.activeElement.isContentEditable);

        // "/" key to focus search bar
        if (e.key === '/' && !isEditable) {
            const searchInput = document.getElementById('nav-global-search') || document.querySelector('.toolbar-card input[name="q"], .toolbar-card input[name="search"], input[name="q"], input[name="search"]');
            if (searchInput) {
                e.preventDefault();
                searchInput.focus();
                searchInput.select();
            }
        }

        // Escape to blur search
        if (e.key === 'Escape' && isEditable) {
            document.activeElement.blur();
        }
    });

    // -------------------------------------------------------------------------
    // 10. Instant Client-Side Table Filtering (Debounced)
    // -------------------------------------------------------------------------
    const tableSearchInput = document.querySelector('.toolbar-card input[name="q"], .toolbar-card input[name="search"]');
    const tableBody = document.querySelector('.table-bbu tbody');

    if (tableSearchInput && tableBody) {
        let debounceTimer;
        tableSearchInput.addEventListener('input', function () {
            clearTimeout(debounceTimer);
            debounceTimer = setTimeout(function () {
                const query = tableSearchInput.value.trim().toLowerCase();
                const rows = tableBody.querySelectorAll('tr:not(#live-filter-empty)');
                if (!rows.length) return;

                let visibleCount = 0;
                rows.forEach(function (row) {
                    const text = row.textContent.toLowerCase();
                    if (!query || text.includes(query)) {
                        row.style.display = '';
                        visibleCount++;
                    } else {
                        row.style.display = 'none';
                    }
                });

                let emptyRow = document.getElementById('live-filter-empty');
                if (visibleCount === 0 && query) {
                    if (!emptyRow) {
                        emptyRow = document.createElement('tr');
                        emptyRow.id = 'live-filter-empty';
                        emptyRow.innerHTML = '<td colspan="100%" class="text-center py-4 text-muted"><i class="fa-solid fa-magnifying-glass me-2"></i>No matching rows on this page. Press <strong>Enter</strong> or click <strong>Filter</strong> to search the full database.</td>';
                        tableBody.appendChild(emptyRow);
                    }
                    emptyRow.style.display = '';
                } else if (emptyRow) {
                    emptyRow.style.display = 'none';
                }
            }, 100);
        });
    }

    // -------------------------------------------------------------------------
    // 11. Animated KPI Number Counters
    // -------------------------------------------------------------------------
    const counterElements = document.querySelectorAll('.kpi-card h3, [data-counter]');
    counterElements.forEach(function (el) {
        if (el.querySelector('small') || el.children.length > 0) return;
        const rawText = el.textContent.trim();
        const normalized = rawText.replace(',', '.');
        const targetNumber = parseFloat(normalized);
        if (!isNaN(targetNumber) && isFinite(targetNumber) && targetNumber > 0) {
            const isFloat = normalized.includes('.');
            const decimals = isFloat ? (normalized.split('.')[1] || '').length : 0;
            const duration = 700; // ms
            const startTime = performance.now();

            function updateCounter(currentTime) {
                const elapsed = currentTime - startTime;
                const progress = Math.min(elapsed / duration, 1);
                const ease = 1 - Math.pow(1 - progress, 4); // easeOutQuart
                const currentVal = (targetNumber * ease).toFixed(decimals);
                el.textContent = currentVal;
                if (progress < 1) {
                    requestAnimationFrame(updateCounter);
                } else {
                    el.textContent = rawText;
                }
            }
            requestAnimationFrame(updateCounter);
        }
    });

    // -------------------------------------------------------------------------
    // 12. Universal Copy-to-Clipboard Handler
    // -------------------------------------------------------------------------
    document.addEventListener('click', function (e) {
        const copyBtn = e.target.closest('[data-copy], .copy-id-btn, .copy-btn');
        if (!copyBtn) return;

        const copyText = copyBtn.getAttribute('data-copy') || copyBtn.getAttribute('data-id') || copyBtn.textContent.trim();
        if (copyText && navigator.clipboard) {
            navigator.clipboard.writeText(copyText).then(function () {
                const originalHtml = copyBtn.innerHTML;
                copyBtn.innerHTML = '<i class="fa-solid fa-check text-success me-1"></i> Copied!';
                copyBtn.classList.add('border-success');
                setTimeout(function () {
                    copyBtn.innerHTML = originalHtml;
                    copyBtn.classList.remove('border-success');
                }, 2000);
            }).catch(function (err) {
                console.warn('Clipboard write failed:', err);
            });
        }
    });

    // -------------------------------------------------------------------------
    // 13. Global Search Trigger Helper (for Navbar Search Bar)
    // -------------------------------------------------------------------------
    window.focusGlobalSearch = function () {
        const searchInput = document.getElementById('nav-global-search') || document.querySelector('.toolbar-card input[name="q"], .toolbar-card input[name="search"], input[name="q"], input[name="search"]');
        if (searchInput) {
            searchInput.focus();
            searchInput.select();
        } else {
            window.location.href = '/students/';
        }
    };

    // Synchronize navbar search with in-page table search if present
    const navSearchInput = document.getElementById('nav-global-search');
    const pageSearchInput = document.querySelector('.toolbar-card input[name="q"], .toolbar-card input[name="search"]');
    if (navSearchInput && pageSearchInput) {
        navSearchInput.addEventListener('input', function () {
            pageSearchInput.value = navSearchInput.value;
            pageSearchInput.dispatchEvent(new Event('input'));
        });
    }

    console.log('✅ BBU Astra-styled front-end suite loaded.');
});

