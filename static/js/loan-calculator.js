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
    
    // Define karat purity constants
    const KARAT_PURITY = {
        '24': 0.999,
        '22': 0.916,
        '21': 0.875,
        '20': 0.833,
        '18': 0.750,
        '14': 0.583
    };
    
    // Function to format currency
    function formatCurrency(amount) {
        return new Intl.NumberFormat('en-US', {
            style: 'currency',
            currency: 'USD',
            minimumFractionDigits: 2
        }).format(amount);
    }
    
    // Function to calculate loan metrics
    function calculateLoanMetrics() {
        // Get input values
        const principal = parseFloat(principalInput.value) || 0;
        const interestRate = parseFloat(interestRateInput.value) || 0;
        const processingFee = parseFloat(processingFeeInput.value) || 0;
        
        // Calculate metrics
        const interestAmount = (principal * interestRate / 100);
        const totalRepayment = principal + interestAmount;
        const distributionAmount = principal - processingFee;
        
        // Update distribution amount input
        if (distributionAmountInput) {
            distributionAmountInput.value = distributionAmount.toFixed(2);
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
                                <p><strong>Interest Rate:</strong> ${interestRate}%</p>
                                <p><strong>Processing Fee:</strong> ${formatCurrency(processingFee)}</p>
                            </div>
                            <div class="col-md-6">
                                <p><strong>Interest Amount:</strong> ${formatCurrency(interestAmount)}</p>
                                <p><strong>Total Repayment:</strong> ${formatCurrency(totalRepayment)}</p>
                                <p><strong>Distribution Amount:</strong> ${formatCurrency(distributionAmount)}</p>
                            </div>
                        </div>
                    </div>
                </div>
            `;
        }
    }
    
    // Function to calculate gold value and display min/max principal amounts
    function calculateGoldValueAndLimits() {
        const marketPrice = parseFloat(marketPriceInput.value) || 0;
        const selectedKarat = goldKaratSelect.value;
        const netWeight = parseFloat(netWeightInput.value) || 0;
        
        // Remove any existing gold value display
        const existingDisplay = document.getElementById('gold-value-display');
        if (existingDisplay) {
            existingDisplay.remove();
        }
        
        // Check if we have all required values
        if (marketPrice <= 0 || !selectedKarat || netWeight <= 0) {
            return;
        }
        
        // Calculate gold value based on purity ratio
        const purityRatio = KARAT_PURITY[selectedKarat] / KARAT_PURITY['22'];
        const goldValue = marketPrice * netWeight * purityRatio;
        
        // Calculate min and max principal amounts
        const minPrincipal = Math.round(goldValue * 0.5); // 50% of gold value
        const maxPrincipal = Math.round(goldValue * 0.85); // 85% of gold value
        const suggestedPrincipal = Math.round(goldValue * 0.75); // 75% of gold value
        
        // Instead of creating and displaying the gold-value-display div,
        // we'll just update the help text with the calculated values
        const principalFormGroup = document.getElementById('div_id_principal_amount');
        if (principalFormGroup) {
            // Create or update help text
            let helpText = principalFormGroup.querySelector('.form-text');
            if (!helpText) {
                helpText = document.createElement('div');
                helpText.className = 'form-text';
                principalFormGroup.appendChild(helpText);
            }
            
            helpText.innerHTML = `
                <i class="fas fa-info-circle"></i> Gold Value: ₹${goldValue.toFixed(0)} | 
                Suggested (75%): ₹${suggestedPrincipal} | 
                Min (50%): ₹${minPrincipal} | 
                Max (85%): ₹${maxPrincipal}
            `;
            
            // Check if the current principal is within the range
            const currentPrincipal = parseFloat(principalInput.value) || 0;
            if (currentPrincipal < minPrincipal) {
                showNotification('Warning: Current principal is below the minimum recommended amount', 'warning');
            } else if (currentPrincipal > maxPrincipal) {
                showNotification('Warning: Current principal exceeds the maximum recommended amount', 'warning');
            }
        }
    }
    
    // Function to calculate dates based on scheme duration
    function calculateDates(issueDate, durationDays, graceDays = 30) {
        if (!issueDate) return { dueDate: null, gracePeriodEnd: null };
        
        const issueDateObj = new Date(issueDate);
        
        // Calculate due date
        const dueDateObj = new Date(issueDateObj);
        dueDateObj.setDate(dueDateObj.getDate() + durationDays);
        
        // Calculate grace period end date
        const gracePeriodEndObj = new Date(dueDateObj);
        gracePeriodEndObj.setDate(gracePeriodEndObj.getDate() + graceDays);
        
        // Format dates as YYYY-MM-DD
        const dueDate = dueDateObj.toISOString().split('T')[0];
        const gracePeriodEnd = gracePeriodEndObj.toISOString().split('T')[0];
        
        return { dueDate, gracePeriodEnd };
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
        if (dueDateInput && dueDate) {
            dueDateInput.value = dueDate;
        }
        
        if (gracePeriodEndInput && gracePeriodEnd) {
            gracePeriodEndInput.value = gracePeriodEnd;
        }
        
        // Show notification that dates were updated
        showNotification('Due date and grace period end date have been automatically updated based on the selected scheme', 'info');
    }
    
    // Function to show notification if that function exists in the parent scope
    function showNotification(message, type) {
        // Check if the parent scope has a showAlert function
        if (typeof window.showAlert === 'function') {
            window.showAlert(message, type);
        } else {
            console.info(message);
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
                
                // Get processing fee percentage from additional_conditions or default to 2%
                const processingFeePercentage = 
                    (scheme.additional_conditions && scheme.additional_conditions.processing_fee_percentage) || 2;
                
                // Update interest rate input with scheme value
                if (interestRateInput) {
                    interestRateInput.value = scheme.interest_rate;
                }
                
                // Calculate processing fee based on principal amount and scheme percentage
                if (processingFeeInput && principalInput.value) {
                    const principal = parseFloat(principalInput.value) || 0;
                    processingFeeInput.value = (principal * processingFeePercentage / 100).toFixed(2);
                }
                
                // Always update dates when scheme changes, regardless of whether issue date is set
                updateDatesFromScheme(scheme);
                
                // Get grace period days from additional_conditions or default to 30
                const gracePeriodDays = 
                    (scheme.additional_conditions && scheme.additional_conditions.grace_period_days) || 30;
                
                // Get no interest period days from additional_conditions or default to 0
                const noInterestPeriodDays = 
                    (scheme.additional_conditions && scheme.additional_conditions.no_interest_period_days) || 0;
                
                // Create scheme details HTML
                const schemeDetailsHTML = `
                    <div class="card-body bg-light">
                        <h5 class="card-title">${scheme.name} Details</h5>
                        <div class="row">
                            <div class="col-md-6">
                                <p><strong>Type:</strong> ${scheme.additional_conditions && scheme.additional_conditions.scheme_type || 'Standard'}</p>
                                <p><strong>Interest Rate:</strong> ${scheme.interest_rate}%</p>
                            </div>
                            <div class="col-md-6">
                                <p><strong>Loan Period:</strong> ${scheme.loan_duration} days</p>
                                <p><strong>No Interest Period:</strong> ${noInterestPeriodDays} days</p>
                                <p><strong>Grace Period:</strong> ${gracePeriodDays} days</p>
                            </div>
                        </div>
                    </div>
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
                        ${scheme.loan_duration} days term | ${noInterestPeriodDays} days no interest period | 
                        ${scheme.additional_conditions && scheme.additional_conditions.scheme_type || 'Standard'} scheme
                    `;
                    schemeHelpText.innerHTML = helpTextHTML;
                }
            })
            .catch(error => {
                console.error('Error loading scheme details:', error);
                showNotification('Error loading scheme details. Please try again.', 'danger');
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
            // If a scheme is selected, recalculate processing fee based on scheme percentage
            if (schemeSelect && schemeSelect.value && processingFeeInput) {
                // Re-fetch scheme details to get processing fee percentage
                loadSchemeDetails();
            } else {
                // Otherwise just calculate loan metrics with current values
                calculateLoanMetrics();
            }
        });
    }
    
    // Add event listeners for gold value calculation
    if (marketPriceInput) {
        marketPriceInput.addEventListener('input', calculateGoldValueAndLimits);
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
        processingFeeInput.addEventListener('input', calculateLoanMetrics);
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