/**
 * Enhanced Loading Screen System for Time-table Optimization
 * Provides loading indicators for different operations with progress tracking
 */

class LoadingManager {
    constructor() {
        this.currentOperation = null;
        this.startTime = null;
        this.progressInterval = null;
        this.progressSteps = [];
        this.currentStep = 0;
        this.createLoadingOverlay();
    }

    createLoadingOverlay() {
        // Create main loading overlay
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
                    <div id="loading-progress">
                        <div class="progress">
                            <div class="determinate" id="progress-bar" style="width: 0%"></div>
                        </div>
                        <span id="progress-text">0%</span>
                    </div>
                    <div id="loading-details"></div>
                    <div id="step-tracker" style="display: none;">
                        <h6>Progress Steps:</h6>
                        <ul id="step-list" class="collection">
                        </ul>
                    </div>
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
                max-width: 500px;
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

            #loading-progress {
                margin: 20px 0;
            }

            #progress-text {
                display: block;
                margin-top: 10px;
                font-weight: bold;
                color: #1a237e;
            }

            #loading-details {
                margin: 15px 0;
                font-size: 0.9rem;
                color: #666;
                min-height: 20px;
            }

            #loading-time {
                color: #999;
                font-size: 0.8rem;
            }

            #step-tracker {
                margin: 20px 0;
                text-align: left;
                max-height: 200px;
                overflow-y: auto;
            }

            #step-tracker h6 {
                margin-bottom: 10px;
                color: #1a237e;
                text-align: center;
            }

            #step-list {
                margin: 0;
                border: none;
            }

            #step-list .collection-item {
                border: none;
                padding: 8px 15px;
                font-size: 0.9rem;
                background: #f8f9fa;
                margin: 2px 0;
                border-radius: 4px;
                animation: fadeInSlide 0.3s ease-out;
            }

            @keyframes fadeInSlide {
                from {
                    opacity: 0;
                    transform: translateX(-20px);
                }
                to {
                    opacity: 1;
                    transform: translateX(0);
                }
            }

            .step-text {
                color: #333;
            }
        `;

        document.head.appendChild(style);
        document.body.appendChild(overlay);
    }

    show(options = {}) {
        const {
            title = 'Processing...',
            message = 'Please wait while we process your request.',
            showProgress = false,
            estimatedDuration = null
        } = options;

        this.currentOperation = options.operation || 'general';
        this.startTime = Date.now();

        // Update content
        document.getElementById('loading-title').textContent = title;
        document.getElementById('loading-message').textContent = message;
        document.getElementById('loading-progress').style.display = showProgress ? 'block' : 'none';
        document.getElementById('loading-details').textContent = '';

        // Show overlay
        const overlay = document.getElementById('loading-overlay');
        overlay.style.display = 'flex';

        // Start time tracking
        this.startTimeTracking();

        // Start progress simulation if needed
        if (showProgress && estimatedDuration) {
            this.simulateProgress(estimatedDuration);
        }
    }

    updateProgress(percentage, details = '', step = null) {
        const progressBar = document.getElementById('progress-bar');
        const progressText = document.getElementById('progress-text');
        const detailsElement = document.getElementById('loading-details');

        if (progressBar) {
            progressBar.style.width = `${percentage}%`;
            progressText.textContent = `${Math.round(percentage)}%`;
        }

        if (details) {
            detailsElement.textContent = details;
        }

        // Update step tracker if step is provided
        if (step) {
            this.updateStepTracker(step);
        }
    }

    updateStepTracker(step) {
        const stepTracker = document.getElementById('step-tracker');
        const stepList = document.getElementById('step-list');
        
        // Show step tracker
        stepTracker.style.display = 'block';
        
        // Add new step
        const stepItem = document.createElement('li');
        stepItem.className = 'collection-item';
        stepItem.innerHTML = `
            <i class="material-icons left green-text">check</i>
            <span class="step-text">${step}</span>
            <span class="right grey-text">${new Date().toLocaleTimeString()}</span>
        `;
        
        stepList.appendChild(stepItem);
        
        // Auto-scroll to latest step
        stepItem.scrollIntoView({ behavior: 'smooth' });
    }

    setProgressSteps(steps) {
        this.progressSteps = steps;
        this.currentStep = 0;
        
        // Clear existing step list
        const stepList = document.getElementById('step-list');
        stepList.innerHTML = '';
    }

    markStepComplete(stepText, percentage = null) {
        this.currentStep++;
        
        // Calculate percentage if not provided
        if (percentage === null && this.progressSteps.length > 0) {
            percentage = (this.currentStep / this.progressSteps.length) * 100;
        }
        
        this.updateProgress(percentage || 0, stepText, stepText);
    }

    simulateProgress(duration) {
        let progress = 0;
        const increment = 100 / (duration * 10); // Update every 100ms

        this.progressInterval = setInterval(() => {
            progress += increment;
            if (progress >= 95) {
                progress = 95; // Stop at 95% to wait for actual completion
                clearInterval(this.progressInterval);
            }
            this.updateProgress(progress);
        }, 100);
    }

    startTimeTracking() {
        const timeInterval = setInterval(() => {
            if (!document.getElementById('loading-overlay').style.display === 'flex') {
                clearInterval(timeInterval);
                return;
            }

            const elapsed = Math.floor((Date.now() - this.startTime) / 1000);
            document.getElementById('loading-time').textContent = `Elapsed: ${elapsed}s`;
        }, 1000);
    }

    hide() {
        const overlay = document.getElementById('loading-overlay');
        overlay.style.display = 'none';

        if (this.progressInterval) {
            clearInterval(this.progressInterval);
            this.progressInterval = null;
        }

        // Reset progress
        this.updateProgress(0);
        this.currentOperation = null;
        this.startTime = null;
    }

    // Predefined loading configurations for common operations
    showTimetableGeneration() {
        const steps = [
            'Validating course data',
            'Processing student enrollments', 
            'Analyzing professor availability',
            'Checking time slot constraints',
            'Running optimization algorithm',
            'Resolving scheduling conflicts',
            'Finalizing timetable',
            'Saving results to database'
        ];
        
        this.setProgressSteps(steps);
        
        this.show({
            title: 'Generating Timetable',
            message: 'Starting timetable generation process...',
            operation: 'timetable_generation',
            showProgress: true,
            estimatedDuration: 30 // 30 seconds estimated
        });
        
        // Simulate progress steps for demonstration
        this.simulateProgressSteps();
    }

    simulateProgressSteps() {
        const steps = [
            { text: 'Validating course data', delay: 2000 },
            { text: 'Processing student enrollments', delay: 3000 },
            { text: 'Analyzing professor availability', delay: 2500 },
            { text: 'Checking time slot constraints', delay: 3500 },
            { text: 'Running optimization algorithm', delay: 8000 },
            { text: 'Resolving scheduling conflicts', delay: 4000 },
            { text: 'Finalizing timetable', delay: 2000 },
            { text: 'Saving results to database', delay: 1500 }
        ];

        let totalDelay = 0;
        steps.forEach((step, index) => {
            totalDelay += step.delay;
            setTimeout(() => {
                this.markStepComplete(step.text);
                this.updateProgress(
                    ((index + 1) / steps.length) * 100,
                    step.text
                );
            }, totalDelay);
        });
    }

    showDataUpload() {
        this.show({
            title: 'Processing Data',
            message: 'Uploading and validating your files...',
            operation: 'data_upload',
            showProgress: true,
            estimatedDuration: 10
        });
    }

    showSectionAllocation() {
        this.show({
            title: 'Allocating Sections',
            message: 'Running student clustering and section assignment...',
            operation: 'section_allocation',
            showProgress: true,
            estimatedDuration: 15
        });
    }

    showScheduleGeneration() {
        this.show({
            title: 'Generating Schedule',
            message: 'Creating personalized schedule for student...',
            operation: 'schedule_generation',
            showProgress: false
        });
    }

    showDatabaseOperation() {
        this.show({
            title: 'Database Operation',
            message: 'Updating database records...',
            operation: 'database',
            showProgress: false
        });
    }
}

// Global loading manager instance
window.loadingManager = new LoadingManager();

// Utility functions for easy use
window.showLoading = (options) => window.loadingManager.show(options);
window.hideLoading = () => window.loadingManager.hide();
window.updateLoadingProgress = (percentage, details) => window.loadingManager.updateProgress(percentage, details);

// Integration with form submissions
document.addEventListener('DOMContentLoaded', function() {
    // Auto-show loading for form submissions that might take time
    const longOperationForms = document.querySelectorAll('form[data-long-operation]');
    
    longOperationForms.forEach(form => {
        form.addEventListener('submit', function(e) {
            const operationType = form.getAttribute('data-operation-type') || 'general';
            
            switch(operationType) {
                case 'timetable-generation':
                    window.loadingManager.showTimetableGeneration();
                    break;
                case 'data-upload':
                    window.loadingManager.showDataUpload();
                    break;
                case 'section-allocation':
                    window.loadingManager.showSectionAllocation();
                    break;
                default:
                    window.showLoading({
                        title: 'Processing',
                        message: 'Please wait...'
                    });
            }
        });
    });

    // Auto-show loading for specific buttons
    const longOperationButtons = document.querySelectorAll('button[data-long-operation], a[data-long-operation]');
    
    longOperationButtons.forEach(button => {
        button.addEventListener('click', function(e) {
            const operationType = button.getAttribute('data-operation-type') || 'general';
            const title = button.getAttribute('data-loading-title') || 'Processing';
            const message = button.getAttribute('data-loading-message') || 'Please wait...';
            
            window.showLoading({ title, message });
        });
    });
});

// Export for module systems
if (typeof module !== 'undefined' && module.exports) {
    module.exports = LoadingManager;
} 