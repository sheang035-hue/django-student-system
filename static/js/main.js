/**
 * Build Bright University (BBU) — Main JavaScript (v6)
 *
 * Blocks:
 *   1.  Theme Manager (light / dark, system preference, Alt+T)
 *   2.  Navbar Scroll State & Scroll Progress Bar
 *   3.  Auto-Dismiss Alerts (pause on hover)
 *   4.  Back-to-Top Floating Button
 *   5.  Password Visibility Toggle
 *   6.  Live Photo Upload Preview
 *   7.  Live Grade Calculation
 *   8.  Double-Submit Protection & Loading Spinner
 *   9.  Bootstrap Tooltips
 *   10. Progress Bars via data-progress
 *   11. Scroll Reveal Animations
 *   12. Animated KPI / Stat Counters
 *   13. Universal Keyboard Shortcuts
 *   14. Instant Client-Side Table Filtering
 *   15. Universal Copy-to-Clipboard
 *   16. Global Search Helpers
 *   17. Instant Form Validation Feedback (native constraint validation)
 */

(function () {
    'use strict';

    var prefersReducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)');

    function onReady(fn) {
        if (document.readyState === 'loading') {
            document.addEventListener('DOMContentLoaded', fn);
        } else {
            fn();
        }
    }

    onReady(function () {

        // ---------------------------------------------------------------------
        // 1. Theme Manager
        // ---------------------------------------------------------------------
        var root = document.documentElement;
        var themeToggleBtn = document.getElementById('theme-toggle-btn');
        var themeIcon = document.getElementById('theme-icon');
        var metaThemeColor = document.querySelector('meta[name="theme-color"]');

        function syncThemeIcon(theme) {
            if (!themeIcon) return;
            if (theme === 'dark') {
                themeIcon.className = 'fa-solid fa-sun';
                themeIcon.style.color = 'var(--bbu-gold)';
            } else {
                themeIcon.className = 'fa-solid fa-moon';
                themeIcon.style.color = '';
            }
        }

        function syncMetaThemeColor(theme) {
            if (metaThemeColor) {
                metaThemeColor.setAttribute('content', theme === 'dark' ? '#0a0e18' : '#ffffff');
            }
        }

        function applyTheme(theme) {
            root.setAttribute('data-bs-theme', theme);
            syncThemeIcon(theme);
            syncMetaThemeColor(theme);
        }

        applyTheme(root.getAttribute('data-bs-theme') || 'light');

        if (themeToggleBtn) {
            themeToggleBtn.addEventListener('click', function () {
                var activeTheme = root.getAttribute('data-bs-theme') || 'light';
                var newTheme = activeTheme === 'dark' ? 'light' : 'dark';
                localStorage.setItem('bbu-theme', newTheme);
                applyTheme(newTheme);
                window.dispatchEvent(new CustomEvent('bbuThemeChanged', { detail: { theme: newTheme } }));
            });
        }

        // Follow OS preference while the user has not chosen a theme manually
        if (window.matchMedia) {
            var systemThemeQuery = window.matchMedia('(prefers-color-scheme: dark)');
            var onSystemThemeChange = function (event) {
                if (localStorage.getItem('bbu-theme')) return;
                var newTheme = event.matches ? 'dark' : 'light';
                applyTheme(newTheme);
                window.dispatchEvent(new CustomEvent('bbuThemeChanged', { detail: { theme: newTheme } }));
            };
            if (systemThemeQuery.addEventListener) {
                systemThemeQuery.addEventListener('change', onSystemThemeChange);
            } else if (systemThemeQuery.addListener) {
                systemThemeQuery.addListener(onSystemThemeChange);
            }
        }

        // ---------------------------------------------------------------------
        // 2. Navbar Scroll State & Scroll Progress Bar
        // ---------------------------------------------------------------------
        var navbar = document.querySelector('.navbar-bbu-astra');
        var scrollProgressBar = document.createElement('div');
        scrollProgressBar.className = 'scroll-progress-bar';
        scrollProgressBar.setAttribute('aria-hidden', 'true');
        document.body.appendChild(scrollProgressBar);

        var scrollTicking = false;
        function onScrollFrame() {
            var scrollTop = window.scrollY || document.documentElement.scrollTop;
            if (navbar) {
                navbar.classList.toggle('navbar-scrolled', scrollTop > 8);
            }
            var doc = document.documentElement;
            var max = doc.scrollHeight - window.innerHeight;
            var progress = max > 0 ? Math.min(Math.max(scrollTop / max, 0), 1) : 1;
            if (progress >= 0.999) progress = 1;
            scrollProgressBar.style.transform = 'scaleX(' + progress + ')';
            scrollTicking = false;
        }
        window.addEventListener('scroll', function () {
            if (!scrollTicking) {
                scrollTicking = true;
                requestAnimationFrame(onScrollFrame);
            }
        }, { passive: true });
        onScrollFrame();

        // ---------------------------------------------------------------------
        // 3. Auto-Dismiss Alerts (pause while hovered)
        // ---------------------------------------------------------------------
        document.querySelectorAll('.alert.alert-dismissible').forEach(function (alert) {
            var dismissTimer = setTimeout(dismissAlert, 6000);

            function dismissAlert() {
                alert.style.transition = 'opacity 0.45s cubic-bezier(0.4, 0, 0.2, 1), transform 0.45s cubic-bezier(0.4, 0, 0.2, 1)';
                alert.style.opacity = '0';
                alert.style.transform = 'translateY(-8px)';
                setTimeout(function () { alert.remove(); }, 450);
            }

            alert.addEventListener('mouseenter', function () { clearTimeout(dismissTimer); });
            alert.addEventListener('mouseleave', function () { dismissTimer = setTimeout(dismissAlert, 2500); });
        });

        // ---------------------------------------------------------------------
        // 4. Back-to-Top Floating Button
        // ---------------------------------------------------------------------
        var backToTopBtn = document.getElementById('back-to-top');
        if (backToTopBtn) {
            window.addEventListener('scroll', function () {
                backToTopBtn.classList.toggle('is-visible', window.scrollY > 320);
            }, { passive: true });

            backToTopBtn.addEventListener('click', function () {
                window.scrollTo({ top: 0, behavior: prefersReducedMotion.matches ? 'auto' : 'smooth' });
            });
        }

        // ---------------------------------------------------------------------
        // 5. Password Visibility Toggle
        // ---------------------------------------------------------------------
        var passwordToggleBtn = document.getElementById('toggle-password-btn');
        var passwordInput = document.getElementById('id_password');
        var passwordToggleIcon = document.getElementById('toggle-password-icon');
        if (passwordToggleBtn && passwordInput) {
            passwordToggleBtn.addEventListener('click', function () {
                var isPassword = passwordInput.type === 'password';
                passwordInput.type = isPassword ? 'text' : 'password';
                if (passwordToggleIcon) {
                    passwordToggleIcon.className = isPassword ? 'fa-solid fa-eye-slash' : 'fa-solid fa-eye';
                }
                passwordToggleBtn.setAttribute('aria-label', isPassword ? 'Hide password' : 'Show password');
            });
        }

        // ---------------------------------------------------------------------
        // 6. Live Photo Upload Preview
        // ---------------------------------------------------------------------
        document.querySelectorAll('input[type="file"][name*="profile_picture"]').forEach(function (input) {
            input.addEventListener('change', function (event) {
                var file = event.target.files[0];
                if (!file) return;
                var reader = new FileReader();
                reader.onload = function (e) {
                    var previewImg = document.getElementById('avatar-preview-img');
                    var placeholder = document.getElementById('avatar-preview-placeholder');
                    if (previewImg) {
                        previewImg.src = e.target.result;
                        previewImg.style.display = 'block';
                    }
                    if (placeholder) {
                        placeholder.style.display = 'none';
                    }
                };
                reader.readAsDataURL(file);
            });
        });

        // ---------------------------------------------------------------------
        // 7. Live Grade Calculation (for Add Grade Form)
        // ---------------------------------------------------------------------
        var scoreInput = document.querySelector('input[name="score"]');
        var liveGradeDisplay = document.getElementById('live-grade-preview');
        if (scoreInput && liveGradeDisplay) {
            var calcGrade = function (scoreVal) {
                var val = parseFloat(scoreVal);
                if (isNaN(val)) return '—';
                if (val >= 90) return 'A (4.0)';
                if (val >= 80) return 'B (3.0)';
                if (val >= 70) return 'C (2.0)';
                if (val >= 60) return 'D (1.0)';
                return 'F (0.0)';
            };
            scoreInput.addEventListener('input', function () {
                liveGradeDisplay.textContent = calcGrade(scoreInput.value);
            });
        }

        // ---------------------------------------------------------------------
        // 8. Double-Submit Protection & Loading Spinner
        // ---------------------------------------------------------------------
        document.querySelectorAll('form:not([data-no-disable])').forEach(function (form) {
            form.addEventListener('submit', function () {
                var submitBtn = form.querySelector('button[type="submit"]');
                if (submitBtn && !submitBtn.disabled) {
                    setTimeout(function () {
                        submitBtn.disabled = true;
                        submitBtn.innerHTML = '<span class="spinner-border spinner-border-sm me-2" role="status" aria-hidden="true"></span> Processing...';
                    }, 20);
                }
            });
        });

        // ---------------------------------------------------------------------
        // 9. Bootstrap Tooltips
        // ---------------------------------------------------------------------
        if (typeof bootstrap !== 'undefined' && bootstrap.Tooltip) {
            document.querySelectorAll('[data-bs-toggle="tooltip"], [title]:not([data-bs-toggle])').forEach(function (el) {
                new bootstrap.Tooltip(el);
            });
        }

        // ---------------------------------------------------------------------
        // 10. Progress Bars via data-progress
        // ---------------------------------------------------------------------
        document.querySelectorAll('[data-progress]').forEach(function (bar) {
            var val = parseFloat(bar.getAttribute('data-progress')) || 0;
            bar.style.width = Math.min(Math.max(val, 0), 100) + '%';
        });

        // ---------------------------------------------------------------------
        // 11. Scroll Reveal Animations (.reveal -> .reveal-visible)
        // ---------------------------------------------------------------------
        var revealElements = document.querySelectorAll('.reveal');
        if (revealElements.length) {
            if ('IntersectionObserver' in window && !prefersReducedMotion.matches) {
                var revealObserver = new IntersectionObserver(function (entries) {
                    entries.forEach(function (entry) {
                        if (entry.isIntersecting) {
                            entry.target.classList.add('reveal-visible');
                            revealObserver.unobserve(entry.target);
                        }
                    });
                }, { threshold: 0.12, rootMargin: '0px 0px -40px 0px' });

                revealElements.forEach(function (el) { revealObserver.observe(el); });
            } else {
                revealElements.forEach(function (el) { el.classList.add('reveal-visible'); });
            }
        }

        // ---------------------------------------------------------------------
        // 12. Animated KPI / Stat Counters (animate when scrolled into view)
        // ---------------------------------------------------------------------
        var counterElements = document.querySelectorAll('.kpi-card h3, .landing-stat-number, [data-counter]');
        if (counterElements.length && 'IntersectionObserver' in window && !prefersReducedMotion.matches) {
            var animateCounter = function (el, rawText) {
                var normalized = rawText.replace(',', '.');
                var targetNumber = parseFloat(normalized);
                if (isNaN(targetNumber) || !isFinite(targetNumber)) return;
                var decimals = normalized.indexOf('.') !== -1 ? (normalized.split('.')[1] || '').length : 0;
                var duration = 850;
                var startTime = null;

                function frame(currentTime) {
                    if (startTime === null) startTime = currentTime;
                    var progress = Math.min((currentTime - startTime) / duration, 1);
                    var ease = 1 - Math.pow(1 - progress, 4);
                    el.textContent = (targetNumber * ease).toFixed(decimals);
                    if (progress < 1) {
                        requestAnimationFrame(frame);
                    } else {
                        el.textContent = rawText;
                    }
                }
                requestAnimationFrame(frame);
            };

            var counterObserver = new IntersectionObserver(function (entries) {
                entries.forEach(function (entry) {
                    if (!entry.isIntersecting) return;
                    counterObserver.unobserve(entry.target);
                    animateCounter(entry.target, entry.target.dataset.counterRaw);
                });
            }, { threshold: 0.45 });

            counterElements.forEach(function (el) {
                if (el.children.length > 0) return;
                var rawText = el.textContent.trim();
                var numeric = parseFloat(rawText.replace(',', '.'));
                if (isNaN(numeric) || !isFinite(numeric) || numeric <= 0) return;
                el.dataset.counterRaw = rawText;
                counterObserver.observe(el);
            });
        }

        // ---------------------------------------------------------------------
        // 13. Universal Keyboard Shortcuts (/, Escape, Alt+T)
        // ---------------------------------------------------------------------
        document.addEventListener('keydown', function (e) {
            if (e.altKey && (e.key === 't' || e.key === 'T')) {
                e.preventDefault();
                if (themeToggleBtn) themeToggleBtn.click();
                return;
            }

            var activeEl = document.activeElement;
            var activeTag = activeEl ? activeEl.tagName.toLowerCase() : '';
            var isEditable = activeTag === 'input' || activeTag === 'textarea' || activeTag === 'select' || (activeEl && activeEl.isContentEditable);

            if (e.key === '/' && !isEditable) {
                var searchInput = document.getElementById('nav-global-search') || document.querySelector('.toolbar-card input[name="q"], .toolbar-card input[name="search"], input[name="q"], input[name="search"]');
                if (searchInput) {
                    e.preventDefault();
                    searchInput.focus();
                    searchInput.select();
                }
            }

            if (e.key === 'Escape' && isEditable) {
                document.activeElement.blur();
            }
        });

        // ---------------------------------------------------------------------
        // 14. Instant Client-Side Table Filtering (Debounced)
        // ---------------------------------------------------------------------
        var tableSearchInput = document.querySelector('.toolbar-card input[name="q"], .toolbar-card input[name="search"]');
        var tableBody = document.querySelector('.table-bbu tbody');

        if (tableSearchInput && tableBody) {
            var debounceTimer;
            tableSearchInput.addEventListener('input', function () {
                clearTimeout(debounceTimer);
                debounceTimer = setTimeout(function () {
                    var query = tableSearchInput.value.trim().toLowerCase();
                    var rows = tableBody.querySelectorAll('tr:not(#live-filter-empty)');
                    if (!rows.length) return;

                    var visibleCount = 0;
                    rows.forEach(function (row) {
                        var text = row.textContent.toLowerCase();
                        if (!query || text.includes(query)) {
                            row.style.display = '';
                            visibleCount++;
                        } else {
                            row.style.display = 'none';
                        }
                    });

                    var emptyRow = document.getElementById('live-filter-empty');
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

        // ---------------------------------------------------------------------
        // 15. Universal Copy-to-Clipboard
        // ---------------------------------------------------------------------
        document.addEventListener('click', function (e) {
            var copyBtn = e.target.closest('[data-copy], .copy-id-btn, .copy-btn');
            if (!copyBtn) return;

            var copyText = copyBtn.getAttribute('data-copy') || copyBtn.getAttribute('data-id') || copyBtn.textContent.trim();
            if (!copyText || !navigator.clipboard) return;

            navigator.clipboard.writeText(copyText).then(function () {
                var originalHtml = copyBtn.innerHTML;
                var originalTitle = copyBtn.getAttribute('title');
                copyBtn.innerHTML = '<i class="fa-solid fa-check"></i> Copied!';
                copyBtn.classList.add('is-copied');
                if (originalTitle !== null) copyBtn.setAttribute('title', 'Copied!');

                setTimeout(function () {
                    copyBtn.innerHTML = originalHtml;
                    copyBtn.classList.remove('is-copied');
                    if (originalTitle !== null) copyBtn.setAttribute('title', originalTitle);
                }, 2000);
            }).catch(function (err) {
                console.warn('Clipboard write failed:', err);
            });
        });

        // ---------------------------------------------------------------------
        // 16. Global Search Helpers
        // ---------------------------------------------------------------------
        window.focusGlobalSearch = function () {
            var searchInput = document.getElementById('nav-global-search') || document.querySelector('.toolbar-card input[name="q"], .toolbar-card input[name="search"], input[name="q"], input[name="search"]');
            if (searchInput) {
                searchInput.focus();
                searchInput.select();
            } else {
                window.location.href = '/students/';
            }
        };

        // Synchronize navbar search with in-page table search if present
        var navSearchInput = document.getElementById('nav-global-search');
        var pageSearchInput = document.querySelector('.toolbar-card input[name="q"], .toolbar-card input[name="search"]');
        if (navSearchInput && pageSearchInput) {
            navSearchInput.addEventListener('input', function () {
                pageSearchInput.value = navSearchInput.value;
                pageSearchInput.dispatchEvent(new Event('input'));
            });
        }

        // ---------------------------------------------------------------------
        // 17. Instant Form Validation Feedback (native constraint validation)
        // ---------------------------------------------------------------------
        document.querySelectorAll('form[method="post"], form[method="POST"]').forEach(function (form) {
            var fields = form.querySelectorAll('input, select, textarea');

            function validateField(field) {
                if (field.getAttribute('data-bbu-touched') !== 'yes') return;
                if (field.checkValidity()) {
                    field.classList.remove('is-invalid');
                    if (field.value !== '') field.classList.add('is-valid');
                } else {
                    field.classList.add('is-invalid');
                    field.classList.remove('is-valid');
                }
            }

            fields.forEach(function (field) {
                var type = (field.getAttribute('type') || '').toLowerCase();
                if (field.disabled || ['hidden', 'submit', 'button', 'reset', 'file'].includes(type)) return;
                if (!field.classList.contains('form-control') && !field.classList.contains('form-select')) return;

                field.addEventListener('blur', function () {
                    field.setAttribute('data-bbu-touched', 'yes');
                    validateField(field);
                });
                field.addEventListener('input', function () {
                    validateField(field);
                });
                field.addEventListener('change', function () {
                    field.setAttribute('data-bbu-touched', 'yes');
                    validateField(field);
                });
            });

            form.addEventListener('reset', function () {
                form.querySelectorAll('.is-invalid, .is-valid').forEach(function (el) {
                    el.classList.remove('is-invalid', 'is-valid');
                    el.removeAttribute('data-bbu-touched');
                });
            });
        });

        console.log('BBU front-end suite v6 loaded.');
    });
})();
