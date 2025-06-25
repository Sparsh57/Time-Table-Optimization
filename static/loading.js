/**
 * Simple Loading Screen System with Error Handling
 * Automatically hides on errors, page navigation, and timeouts
 */

class LoadingManager {
    constructor() {
        this.isVisible = false;
        this.startTime = null;
        this.timeoutId = null;
        this.maxDuration = 3600000; // 6 minutes max// 60 seconds max
        this.createLoadingOverlay();
        this.setupErrorHandling();
    }

    createLoadingOverlay() {
        // Check if overlay already exists in the DOM
        let overlay = document.getElementById('loading-overlay');
        
        if (!overlay) {
            // Create overlay if it doesn't exist
            overlay = document.createElement('div');
            overlay.id = 'loading-overlay';
            document.body.appendChild(overlay);
        }
        
        // Set the HTML content
        const htmlContent = `
            <div class="loading-container">
                <div class="loading-spinner">
                    <div class="custom-spinner"></div>
                </div>
                <div class="loading-content">
                    <h5 id="loading-title">Processing...</h5>
                    <p id="loading-message">Please wait while we process your request.</p>
                    <small id="loading-time">Elapsed: 0s</small>
                </div>
            </div>
        `;
        
        overlay.innerHTML = htmlContent;
        
        // Force a reflow to ensure content is rendered
        overlay.offsetHeight;

        // Add CSS styles
        const style = document.createElement('style');
        style.id = 'loading-manager-styles';
        
        // Remove existing styles if they exist
        const existingStyle = document.getElementById('loading-manager-styles');
        if (existingStyle) {
            existingStyle.remove();
        }
        
        style.textContent = `
            #loading-overlay {
                position: fixed !important;
                top: 0 !important;
                left: 0 !important;
                width: 100% !important;
                height: 100% !important;
                background: rgba(26, 35, 126, 0.9) !important;
                z-index: 99999 !important;
                display: none !important;
                align-items: center !important;
                justify-content: center !important;
                backdrop-filter: blur(5px);
                font-family: 'Poppins', Arial, sans-serif !important;
            }

            #loading-overlay.show {
                display: flex !important;
            }

            .loading-container {
                background: white !important;
                padding: 40px !important;
                border-radius: 12px !important;
                text-align: center !important;
                max-width: 400px !important;
                min-width: 300px !important;
                box-shadow: 0 10px 30px rgba(0,0,0,0.3) !important;
                animation: slideInUp 0.3s ease-out !important;
                position: relative !important;
                z-index: 100000 !important;
            }

            .custom-spinner {
                width: 40px !important;
                height: 40px !important;
                border: 4px solid #f3f3f3 !important;
                border-top: 4px solid #2196F3 !important;
                border-radius: 50% !important;
                animation: spin 1s linear infinite !important;
                margin: 0 auto !important;
            }

            @keyframes spin {
                0% { transform: rotate(0deg); }
                100% { transform: rotate(360deg); }
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
                margin-bottom: 20px !important;
            }

            #loading-title {
                color: #333 !important;
                margin: 0 0 10px 0 !important;
                font-size: 1.5rem !important;
                font-weight: 600 !important;
            }

            #loading-message {
                color: #666 !important;
                margin: 0 0 10px 0 !important;
                font-size: 1rem !important;
                line-height: 1.4 !important;
            }

            #loading-time {
                color: #999 !important;
                font-size: 0.8rem !important;
                display: block !important;
                margin-top: 15px !important;
            }
        `;

        document.head.appendChild(style);
        
        // Final verification
        setTimeout(() => {
            const finalCheck = document.getElementById('loading-overlay');
            if (!finalCheck || !finalCheck.querySelector('.loading-container')) {
                console.error('LoadingManager: Overlay initialization failed');
            }
        }, 100);
    }

    setupErrorHandling() {
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
                        setTimeout(() => this.hide(), 500); // Small delay to allow error handling
                    }
                    return response;
                })
                .catch(error => {
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

        // Verify overlay content exists before showing
        const overlay = document.getElementById('loading-overlay');
        if (!overlay) {
            console.error('Overlay element not found! Recreating...');
            this.createLoadingOverlay();
            // Try again after recreating
            const newOverlay = document.getElementById('loading-overlay');
            if (!newOverlay) {
                console.error('Failed to create overlay element!');
                return;
            }
        }

        // If overlay is empty, recreate content
        if (overlay.childElementCount === 0) {
            const htmlContent = `
                <div class="loading-container">
                    <div class="loading-spinner">
                        <div class="custom-spinner"></div>
                    </div>
                    <div class="loading-content">
                        <h5 id="loading-title">Processing...</h5>
                        <p id="loading-message">Please wait while we process your request.</p>
                        <small id="loading-time">Elapsed: 0s</small>
                    </div>
                </div>
            `;
            overlay.innerHTML = htmlContent;
        }

        this.isVisible = true;
        this.startTime = Date.now();

        // Update content
        const titleElement = document.getElementById('loading-title');
        const messageElement = document.getElementById('loading-message');
        
        if (titleElement) {
            titleElement.textContent = title;
        } else {
            console.error('Title element not found!');
        }
        
        if (messageElement) {
            messageElement.textContent = message;
        } else {
            console.error('Message element not found!');
        }

        // Show overlay using class
        if (overlay) {
            overlay.classList.add('show');
            
            // Force style recalculation
            overlay.offsetHeight;
            
            // Check if container is visible
            const container = overlay.querySelector('.loading-container');
            if (!container) {
                console.error('Loading container not found in overlay!');
            }
        } else {
            console.error('Loading overlay element not found!');
        }

        // Start time tracking
        this.startTimeTracking();

        // Set timeout to auto-hide
        this.timeoutId = setTimeout(() => {
            this.hide();
        }, timeout);
    }

    hide() {
        if (!this.isVisible) return;

        this.isVisible = false;
        
        // Hide overlay using class
        const overlay = document.getElementById('loading-overlay');
        if (overlay) {
            overlay.classList.remove('show');
        }

        // Clear timeout
        if (this.timeoutId) {
            clearTimeout(this.timeoutId);
            this.timeoutId = null;
        }

        // Reset state
        this.startTime = null;
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

    // Progress step tracking methods
    setProgressSteps(steps) {
        this.progressSteps = steps || [];
        this.completedSteps = [];
        this.currentProgress = 0;
        this.updateProgressDisplay();
    }

    markStepComplete(stepName, progressPercentage = null) {
        if (!this.progressSteps) return;
        
        if (!this.completedSteps.includes(stepName)) {
            this.completedSteps.push(stepName);
        }
        
        if (progressPercentage !== null) {
            this.currentProgress = Math.max(this.currentProgress, progressPercentage);
        } else {
            // Auto-calculate progress based on completed steps
            this.currentProgress = Math.floor((this.completedSteps.length / this.progressSteps.length) * 100);
        }
        
        this.updateProgressDisplay();
    }

    updateProgressDisplay() {
        if (!this.isVisible) return;
        
        const messageElement = document.getElementById('loading-message');
        const progressElement = document.getElementById('loading-progress');
        
        if (this.progressSteps && this.progressSteps.length > 0) {
            const currentStep = this.completedSteps.length < this.progressSteps.length ? 
                               this.progressSteps[this.completedSteps.length] : 
                               this.progressSteps[this.progressSteps.length - 1];
            
            if (messageElement) {
                messageElement.innerHTML = `
                    <div style="margin-bottom: 10px;">${currentStep || 'Processing...'}</div>
                    <div style="background: rgba(255,255,255,0.2); border-radius: 10px; padding: 3px; margin-bottom: 10px;">
                        <div style="background: #4CAF50; height: 6px; border-radius: 8px; width: ${this.currentProgress}%; transition: width 0.3s ease;"></div>
                    </div>
                    <div style="font-size: 0.9em; opacity: 0.8;">${this.currentProgress}% Complete</div>
                `;
            }
        }
    }

    // Add method to reinitialize overlay if needed
    reinitialize() {
        this.createLoadingOverlay();
    }

    // Add method to force content creation
    forceCreateContent() {
        const overlay = document.getElementById('loading-overlay');
        if (overlay) {
            const htmlContent = `
                <div class="loading-container">
                    <div class="loading-spinner">
                        <div class="custom-spinner"></div>
                    </div>
                    <div class="loading-content">
                        <h5 id="loading-title">Processing...</h5>
                        <p id="loading-message">Please wait while we process your request.</p>
                        <small id="loading-time">Elapsed: 0s</small>
                    </div>
                </div>
            `;
            overlay.innerHTML = htmlContent;
            return overlay.childElementCount > 0;
        }
        return false;
    }
}

// Global loading manager instance - create immediately when script loads
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