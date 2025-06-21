/**
 * Simple Loading Screen System with Error Handling
 * Automatically hides on errors, page navigation, and timeouts
 */

class LoadingManager {
    constructor() {
        this.isVisible = false;
        this.startTime = null;
        this.timeoutId = null;
        this.maxDuration = 60000; // 60 seconds max
        this.createLoadingOverlay();
        this.setupErrorHandling();
    }

    createLoadingOverlay() {
        const overlay = document.createElement('div');
        overlay.id = 'loading-overlay';
        overlay.innerHTML = `
            <div class="loading-container">
                <div class="loading-spinner">
                    <div class="preloader-wrapper big active">
                        <div class="spinner-layer spinner-blue-only">
                            <div class="circle-clipper left">
                                <div class="circle"></div>
                            </div>
                            <div class="gap-patch">
                                <div class="circle"></div>
                            </div>
                            <div class="circle-clipper right">
                                <div class="circle"></div>
                            </div>
                        </div>
                    </div>
                </div>
                <div class="loading-content">
                    <h5 id="loading-title">Processing...</h5>
                    <p id="loading-message">Please wait while we process your request.</p>
                    <small id="loading-time">Elapsed: 0s</small>
                </div>
            </div>
        `;

        // Add CSS styles
        const style = document.createElement('style');
        style.textContent = `
            #loading-overlay {
                position: fixed;
                top: 0;
                left: 0;
                width: 100%;
                height: 100%;
                background: rgba(26, 35, 126, 0.9);
                z-index: 10000;
                display: none;
                align-items: center;
                justify-content: center;
                backdrop-filter: blur(5px);
            }

            .loading-container {
                background: white;
                padding: 40px;
                border-radius: 12px;
                text-align: center;
                max-width: 400px;
                box-shadow: 0 10px 30px rgba(0,0,0,0.3);
                animation: slideInUp 0.3s ease-out;
            }

            @keyframes slideInUp {
                from {
                    transform: translateY(30px);
                    opacity: 0;
                }
                to {
                    transform: translateY(0);
                    opacity: 1;
                }
            }

            .loading-spinner {
                margin-bottom: 20px;
            }

            #loading-time {
                color: #999;
                font-size: 0.8rem;
                display: block;
                margin-top: 15px;
            }
        `;

        document.head.appendChild(style);
        document.body.appendChild(overlay);
    }

    setupErrorHandling() {
        // Hide loading on page errors
        window.addEventListener('error', () => {
            console.log('Page error detected, hiding loading screen');
            this.hide();
        });

        // Hide loading on unhandled promise rejections
        window.addEventListener('unhandledrejection', () => {
            console.log('Unhandled promise rejection detected, hiding loading screen');
            this.hide();
        });

        // Hide loading on page navigation
        window.addEventListener('beforeunload', () => {
            this.hide();
        });

        // Hide loading on page visibility change (tab switch, etc.)
        document.addEventListener('visibilitychange', () => {
            if (document.hidden && this.isVisible) {
                this.hide();
            }
        });

        // Monitor for HTTP errors by intercepting fetch requests
        const originalFetch = window.fetch;
        window.fetch = (...args) => {
            return originalFetch(...args)
                .then(response => {
                    // Hide loading if we get an error response
                    if (!response.ok && this.isVisible) {
                        console.log(`HTTP error ${response.status} detected, hiding loading screen`);
                        setTimeout(() => this.hide(), 500); // Small delay to allow error handling
                    }
                    return response;
                })
                .catch(error => {
                    console.log('Fetch error detected, hiding loading screen');
                    this.hide();
                    throw error;
                });
        };
    }

    show(options = {}) {
        const {
            title = 'Processing...',
            message = 'Please wait while we process your request.',
            timeout = this.maxDuration
        } = options;

        // Don't show if already visible
        if (this.isVisible) return;

        this.isVisible = true;
        this.startTime = Date.now();

        // Update content
        document.getElementById('loading-title').textContent = title;
        document.getElementById('loading-message').textContent = message;

        // Show overlay
        const overlay = document.getElementById('loading-overlay');
        overlay.style.display = 'flex';

        // Start time tracking
        this.startTimeTracking();

        // Set timeout to auto-hide
        this.timeoutId = setTimeout(() => {
            console.log('Loading timeout reached, hiding loading screen');
            this.hide();
        }, timeout);

        console.log(`Loading screen shown: ${title}`);
    }

    hide() {
        if (!this.isVisible) return;

        this.isVisible = false;
        
        // Hide overlay
        const overlay = document.getElementById('loading-overlay');
        if (overlay) {
            overlay.style.display = 'none';
        }

        // Clear timeout
        if (this.timeoutId) {
            clearTimeout(this.timeoutId);
            this.timeoutId = null;
        }

        // Reset state
        this.startTime = null;
        
        console.log('Loading screen hidden');
    }

    startTimeTracking() {
        const timeInterval = setInterval(() => {
            if (!this.isVisible) {
                clearInterval(timeInterval);
                return;
            }

            const elapsed = Math.floor((Date.now() - this.startTime) / 1000);
            const timeElement = document.getElementById('loading-time');
            if (timeElement) {
                timeElement.textContent = `Elapsed: ${elapsed}s`;
            }
        }, 1000);
    }

    // Predefined loading configurations for common operations
    showTimetableGeneration() {
        this.show({
            title: 'Generating Timetable',
            message: 'Running optimization algorithm, this may take a few minutes...',
            timeout: 120000 // 2 minutes for timetable generation
        });
    }

    showDataUpload() {
        this.show({
            title: 'Processing Data',
            message: 'Uploading and validating your files...',
            timeout: 30000 // 30 seconds for data upload
        });
    }

    showDatabaseOperation() {
        this.show({
            title: 'Database Operation',
            message: 'Updating database records...',
            timeout: 15000 // 15 seconds for database operations
        });
    }
}

// Global loading manager instance
window.loadingManager = new LoadingManager();

// Utility functions for easy use
window.showLoading = (options) => window.loadingManager.show(options);
window.hideLoading = () => window.loadingManager.hide();

// Integration with form submissions and navigation
document.addEventListener('DOMContentLoaded', function() {
    // Auto-show loading for forms that might take time
    const forms = document.querySelectorAll('form[data-long-operation]');
    
    forms.forEach(form => {
        form.addEventListener('submit', function(e) {
            const operationType = form.getAttribute('data-operation-type') || 'general';
            
            // Show appropriate loading screen
            switch(operationType) {
                case 'timetable-generation':
                    window.loadingManager.showTimetableGeneration();
                    break;
                case 'data-upload':
                    window.loadingManager.showDataUpload();
                    break;
                case 'database':
                    window.loadingManager.showDatabaseOperation();
                    break;
                default:
                    window.showLoading({
                        title: 'Processing',
                        message: 'Please wait...'
                    });
            }
        });
    });

    // Auto-show loading for buttons/links that might take time
    const buttons = document.querySelectorAll('button[data-long-operation], a[data-long-operation]');
    
    buttons.forEach(button => {
        button.addEventListener('click', function(e) {
            const title = button.getAttribute('data-loading-title') || 'Processing';
            const message = button.getAttribute('data-loading-message') || 'Please wait...';
            
            window.showLoading({ title, message });
        });
    });

    // Monitor for page redirects and form responses
    let lastUrl = location.href;
    const observer = new MutationObserver(() => {
        // Hide loading if URL changes (redirect happened)
        if (location.href !== lastUrl) {
            lastUrl = location.href;
            window.loadingManager.hide();
        }
        
        // Hide loading if error messages appear on page
        const errorElements = document.querySelectorAll('.error, .alert-danger, [class*="error"]');
        if (errorElements.length > 0 && window.loadingManager.isVisible) {
            console.log('Error element detected on page, hiding loading screen');
            setTimeout(() => window.loadingManager.hide(), 1000);
        }
    });
    
    observer.observe(document.body, {
        childList: true,
        subtree: true
    });
});

// Export for module systems
if (typeof module !== 'undefined' && module.exports) {
    module.exports = LoadingManager;
} 