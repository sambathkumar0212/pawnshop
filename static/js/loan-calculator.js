/**
 * Real-time Loan Calculator for Pawnshop Management System
 * Provides instant calculations when users create or modify loans
 */

document.addEventListener('DOMContentLoaded', function() {
    // Get DOM elements
    const schemeSelect = document.getElementById('id_scheme');
    const principalInput = document.getElementById('id_principal_amount');
    const interestRateInput = document.getElementById('id_interest_rate');
    const processingFeeInput = document.getElementById('id_processing_fee');
    const distributionAmountInput = document.getElementById('id_distribution_amount');
    const issueDateInput = document.getElementById('id_issue_date');
    const dueDateInput = document.getElementById('id_due_date');
    const gracePeriodEndInput = document.getElementById('id_grace_period_end');
    
    // Gold calculation related elements
    const marketPriceInput = document.getElementById('id_market_price_22k');
    const goldKaratSelect = document.getElementById('id_gold_karat');
    const netWeightInput = document.getElementById('id_net_weight');
    
    // Get display containers
    const schemeInfoBox = document.getElementById('scheme-info');
    const loanMetricsBox = document.getElementById('loan-metrics');

    // Check if we're editing an existing loan by looking for an existing processing fee
    const isEditMode = processingFeeInput && processingFeeInput.value !== '';
    
    // Define karat purity constants
    const KARAT_PURITY = {
        '24': 0.999,
        '22': 0.916,
        '21': 0.875,
        '20': 0.833,
        '18': 0.750,
        '14': 0.583
    };
    
    // Function to format currency as integers (no decimals)
    function formatCurrency(amount) {
        return '₹' + Math.round(parseFloat(amount)).toLocaleString('en-IN');
    }
    
    // Function to ensure integer values only
    function ensureInteger(value) {
        return Math.round(parseFloat(value) || 0);
    }
    
    // Function to calculate loan metrics
    function calculateLoanMetrics() {
        // Get input values - ensure all are integers
        const principal = ensureInteger(principalInput.value);
        const interestRate = parseFloat(interestRateInput.value) || 0;
        const processingFee = ensureInteger(processingFeeInput.value);
        
        // Calculate metrics - ensure all are integers
        const interestAmount = Math.round(principal * interestRate / 100);
        const totalRepayment = principal + interestAmount;
        const distributionAmount = principal - processingFee;
        
        // Calculate monthly interest - ensure all are integers where appropriate
        const monthlyInterestRate = interestRate / 12;
        const monthlyInterestAmount = Math.round(principal * monthlyInterestRate / 100);
        const perThousandRate = Math.round((monthlyInterestRate / 100) * 1000);
        
        // Update distribution amount input - ensure integer
        if (distributionAmountInput) {
            distributionAmountInput.value = Math.round(distributionAmount);
        }
        
        // Update loan metrics display
        if (loanMetricsBox) {
            loanMetricsBox.innerHTML = `
                <div class="card">
                    <div class="card-body">
                        <h5 class="card-title">Loan Calculation Summary</h5>
                        <div class="row">
                            <div class="col-md-6">
                                <p><strong>Principal Amount:</strong> ${formatCurrency(principal)}</p>
                                <p><strong>Interest Rate:</strong> ${interestRate}% per annum</p>
                                <p><strong>Processing Fee:</strong> ${formatCurrency(processingFee)}</p>
                            </div>
                            <div class="col-md-6">
                                <p><strong>Interest Amount:</strong> ${formatCurrency(interestAmount)}</p>
                                <p><strong>Total Repayment:</strong> ${formatCurrency(totalRepayment)}</p>
                                <p><strong>Distribution Amount:</strong> ${formatCurrency(distributionAmount)}</p>
                            </div>
                        </div>
                        <div class="row mt-3 bg-light p-2 rounded">
                            <div class="col-12">
                                <h6 class="text-primary"><strong>Monthly Interest Information</strong></h6>
                            </div>
                            <div class="col-md-6">
                                <p><strong>Monthly Rate:</strong> ${monthlyInterestRate.toFixed(2)}%</p>
                            </div>
                            <div class="col-md-6">
                                <p><strong>Monthly Interest:</strong> ${formatCurrency(monthlyInterestAmount)}</p>
                                <p><strong>Rate per ₹1,000:</strong> ${formatCurrency(perThousandRate)}</p>
                            </div>
                        </div>
                    </div>
                </div>
            `;
        }
    }
    
    // Function to calculate gold value and display min/max principal amounts
    function calculateGoldValueAndLimits() {
        // Get input values - ensure market price is an integer
        const marketPrice = ensureInteger(marketPriceInput.value);
        const goldKarat = goldKaratSelect.value || '22';
        const netWeight = parseFloat(netWeightInput.value) || 0;
        
        // Get purity ratio for the selected karat
        const purityRatio = KARAT_PURITY[goldKarat] || 0.916;  // Default to 22k if not found
        
        // Calculate gold value - ensure result is an integer
        const goldValue = Math.round(marketPrice * netWeight * purityRatio);
        
        // Update gold value display if element exists
        const goldValueDisplay = document.getElementById('gold-value-display');
        if (goldValueDisplay) {
            goldValueDisplay.textContent = formatCurrency(goldValue);
        }
        
        // Calculate and display min/max loan amounts if elements exist
        const minLoanDisplay = document.getElementById('min-loan-display');
        const maxLoanDisplay = document.getElementById('max-loan-display');
        
        if (minLoanDisplay) {
            const minLoan = Math.round(goldValue * 0.5);  // 50% of gold value, rounded to integer
            minLoanDisplay.textContent = formatCurrency(minLoan);
        }
        
        if (maxLoanDisplay) {
            const maxLoan = Math.round(goldValue * 0.85);  // 85% of gold value, rounded to integer
            maxLoanDisplay.textContent = formatCurrency(maxLoan);
        }
    }
    
    // Function to calculate dates based on scheme duration
    function calculateDates(issueDate, durationDays, graceDays = 30) {
        if (!issueDate) return { dueDate: '', gracePeriodEnd: '' };
        
        // Parse issue date
        const date = new Date(issueDate);
        
        // Calculate due date (issue date + duration days)
        const dueDate = new Date(date);
        dueDate.setDate(date.getDate() + parseInt(durationDays));
        
        // Calculate grace period end (due date + grace days)
        const gracePeriodEnd = new Date(dueDate);
        gracePeriodEnd.setDate(dueDate.getDate() + parseInt(graceDays));
        
        // Format dates as YYYY-MM-DD
        const formatDate = (date) => {
            const year = date.getFullYear();
            const month = String(date.getMonth() + 1).padStart(2, '0');
            const day = String(date.getDate()).padStart(2, '0');
            return `${year}-${month}-${day}`;
        };
        
        return {
            dueDate: formatDate(dueDate),
            gracePeriodEnd: formatDate(gracePeriodEnd)
        };
    }
    
    // Function to update dates based on scheme loan duration
    function updateDatesFromScheme(scheme) {
        // If issue date is not set, use today's date for calculations
        // This ensures dates are always updated when scheme changes
        let dateToUse = issueDateInput.value;
        
        if (!dateToUse) {
            const today = new Date();
            dateToUse = today.toISOString().split('T')[0];
            
            // Update the issue date input with today's date if it's empty
            if (issueDateInput) {
                issueDateInput.value = dateToUse;
                showNotification('Issue date set to today', 'info');
            }
        }
        
        // Get grace period days from additional_conditions or default to 30
        const gracePeriodDays = 
            (scheme.additional_conditions && scheme.additional_conditions.grace_period_days) || 30;
            
        const { dueDate, gracePeriodEnd } = calculateDates(
            dateToUse, 
            scheme.loan_duration, 
            gracePeriodDays
        );
        
        // Update due date and grace period end inputs
        if (dueDateInput) dueDateInput.value = dueDate;
        if (gracePeriodEndInput) gracePeriodEndInput.value = gracePeriodEnd;
        
        // Show notification about date updates
        if (dueDate && gracePeriodEnd) {
            showNotification(`Due date set to ${dueDate} and grace period to ${gracePeriodEnd}`, 'info');
        }
    }
    
    // Function to show notification if that function exists in the parent scope
    function showNotification(message, type) {
        // Check if notification function exists in parent scope (global)
        if (typeof window.showToast === 'function') {
            window.showToast(message, type || 'info');
        }
    }
    
    // Function to load scheme details
    function loadSchemeDetails() {
        const schemeSelect = document.getElementById('id_scheme');
        const schemeId = schemeSelect.value;
        
        // Clear scheme info if no scheme selected
        if (!schemeId) {
            if (schemeInfoBox) {
                schemeInfoBox.style.display = 'none';
                schemeInfoBox.innerHTML = '';
            }
            
            // Reset help text to default when no scheme is selected
            const schemeHelpText = document.querySelector('#div_id_scheme .form-text');
            if (schemeHelpText) {
                schemeHelpText.innerHTML = 'Select a loan scheme to apply to this loan';
            }
            return;
        }
        
        // Fetch scheme details from API - using the correct URL pattern
        fetch(`/schemes/${schemeId}/json/`)
            .then(response => {
                if (!response.ok) {
                    throw new Error('Failed to load scheme details');
                }
                return response.json();
            })
            .then(scheme => {
                // Set scheme info display to visible
                if (schemeInfoBox) {
                    schemeInfoBox.style.display = 'block';
                }
                
                // Get processing fee percentage from additional_conditions or default to 1%
                const processingFeePercentage = 
                    (scheme.additional_conditions && scheme.additional_conditions.processing_fee_percentage) || 1;
                
                // Update interest rate input with scheme value
                if (interestRateInput) {
                    interestRateInput.value = scheme.interest_rate;
                }
                
                // Calculate processing fee based on principal amount and scheme percentage - ensure integer
                if (processingFeeInput && principalInput.value) {
                    const principal = ensureInteger(principalInput.value);
                    processingFeeInput.value = Math.round(principal * processingFeePercentage / 100);
                }
                
                // Always update dates when scheme changes, regardless of whether issue date is set
                updateDatesFromScheme(scheme);
                
                // Get grace period days from additional_conditions or default to 30
                const gracePeriodDays = 
                    (scheme.additional_conditions && scheme.additional_conditions.grace_period_days) || 30;
                
                // Get no interest period days from additional_conditions or default to 0
                const noInterestPeriodDays = 
                    (scheme.additional_conditions && scheme.additional_conditions.no_interest_period_days) || 0;
                
                // Calculate monthly interest rate
                const monthlyInterestRate = scheme.interest_rate / 12;
                const perThousandRate = (monthlyInterestRate / 100) * 1000;
                
                // Create scheme details HTML - display permanently in the scheme-info element
                const schemeDetailsHTML = `
                    ${scheme.name} | ${noInterestPeriodDays}days 0 interest | ${scheme.loan_duration}days Details<br>
                    <strong>Type:</strong> ${scheme.additional_conditions && scheme.additional_conditions.scheme_type || 'Standard'}<br>
                    <strong>Interest Rate:</strong> ${scheme.interest_rate}% per annum<br>
                    <strong>Monthly Interest:</strong> ${monthlyInterestRate.toFixed(2)}% per month<br>
                    <strong>Per ₹1,000 Rate:</strong> ${formatCurrency(perThousandRate)}
                `;
                        
                // Display scheme details in the info box
                if (schemeInfoBox) {
                    schemeInfoBox.innerHTML = schemeDetailsHTML;
                }
                
                // Update the help text with scheme details
                const schemeHelpText = document.querySelector('#div_id_scheme .form-text');
                if (schemeHelpText) {
                    const helpTextHTML = `
                        <strong>${scheme.name}:</strong> ${scheme.interest_rate}% interest | 
                        Monthly rate: ${monthlyInterestRate.toFixed(2)}% | 
                        ${scheme.loan_duration} days term | ${noInterestPeriodDays} days no interest period | 
                        ${scheme.additional_conditions && scheme.additional_conditions.scheme_type || 'Standard'} scheme
                    `;
                    schemeHelpText.innerHTML = helpTextHTML;
                }
                
                // Calculate loan metrics with updated values
                calculateLoanMetrics();
            })
            .catch(error => {
                console.error('Error loading scheme details:', error);
                showNotification('Failed to load scheme details: ' + error.message, 'error');
            });
    }
    
    // Set up event listeners
    if (schemeSelect) {
        // Adding a separate event listener for the scheme select to ensure dates always update
        schemeSelect.addEventListener('change', function() {
            // Load scheme details will update dates
            loadSchemeDetails();
        });
    }
    
    if (principalInput) {
        principalInput.addEventListener('input', function() {
            // Ensure integer value
            this.value = ensureInteger(this.value);
            
            // If a scheme is selected, recalculate processing fee based on scheme percentage
            if (schemeSelect && schemeSelect.value && processingFeeInput) {
                // Get the current scheme ID
                const schemeId = schemeSelect.value;
                
                // Fetch scheme details from API to get processing fee percentage
                fetch(`/schemes/${schemeId}/json/`)
                    .then(response => {
                        if (!response.ok) {
                            throw new Error('Failed to load scheme details');
                        }
                        return response.json();
                    })
                    .then(scheme => {
                        // Get processing fee percentage from additional_conditions or default to 1%
                        const processingFeePercentage = 
                            (scheme.additional_conditions && scheme.additional_conditions.processing_fee_percentage) || 1;
                        
                        // Calculate processing fee based on principal amount and scheme percentage
                        const principal = ensureInteger(this.value);
                        processingFeeInput.value = Math.round(principal * processingFeePercentage / 100);
                        
                        // Update loan metrics with new values
                        calculateLoanMetrics();
                    })
                    .catch(error => {
                        console.error('Error loading scheme details:', error);
                        // If there's an error, still calculate metrics with current values
                        calculateLoanMetrics();
                    });
            } else {
                // If no scheme selected, use default 1% processing fee
                if (processingFeeInput) {
                    const principal = ensureInteger(this.value);
                    processingFeeInput.value = Math.round(principal * 0.01); // Default 1%
                }
                // Calculate loan metrics with current values
                calculateLoanMetrics();
            }
        });
    }
    
    // Add event listeners for gold value calculation
    if (marketPriceInput) {
        marketPriceInput.addEventListener('input', function() {
            // Ensure integer value
            this.value = ensureInteger(this.value);
            calculateGoldValueAndLimits();
        });
    }
    
    if (goldKaratSelect) {
        goldKaratSelect.addEventListener('change', calculateGoldValueAndLimits);
    }
    
    if (netWeightInput) {
        netWeightInput.addEventListener('input', calculateGoldValueAndLimits);
    }
    
    if (interestRateInput) {
        interestRateInput.addEventListener('input', calculateLoanMetrics);
    }
    
    if (processingFeeInput) {
        processingFeeInput.addEventListener('input', function() {
            // Ensure integer value
            this.value = ensureInteger(this.value);
            calculateLoanMetrics();
        });
    }
    
    if (issueDateInput) {
        issueDateInput.addEventListener('change', function() {
            // If a scheme is selected, update maturity date
            if (schemeSelect && schemeSelect.value) {
                loadSchemeDetails();
            }
        });
    }
    
    // Initial calculation if values are pre-populated
    if (schemeSelect && schemeSelect.value) {
        loadSchemeDetails();
    } else if (isEditMode && processingFeeInput) {
        // In edit mode, if we have a processing fee value but no scheme selected,
        // make sure we keep the existing processing fee value from the database
        calculateLoanMetrics();
    } else {
        calculateLoanMetrics();
    }
    
    // Calculate gold value if all required fields have values
    if (marketPriceInput && marketPriceInput.value && 
        goldKaratSelect && goldKaratSelect.value && 
        netWeightInput && netWeightInput.value) {
        calculateGoldValueAndLimits();
    }
});