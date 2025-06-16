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
    
    // Get display containers
    const schemeInfoBox = document.getElementById('scheme-info');
    const loanMetricsBox = document.getElementById('loan-metrics');
    
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
    
    // Function to load scheme details
    function loadSchemeDetails() {
        const schemeId = schemeSelect.value;
        
        // Clear scheme info if no scheme selected
        if (!schemeId) {
            if (schemeInfoBox) {
                schemeInfoBox.innerHTML = '';
                schemeInfoBox.classList.add('d-none');
            }
            return;
        }
        
        // Fetch scheme details from API
        fetch(`/api/schemes/${schemeId}/`)
            .then(response => {
                if (!response.ok) {
                    throw new Error('Failed to load scheme details');
                }
                return response.json();
            })
            .then(scheme => {
                // Update interest rate and processing fee inputs with scheme values
                if (interestRateInput) {
                    interestRateInput.value = scheme.interest_rate;
                }
                
                // Calculate processing fee based on principal amount and scheme percentage
                if (processingFeeInput && principalInput.value) {
                    const principal = parseFloat(principalInput.value) || 0;
                    const feePercentage = scheme.processing_fee_percentage;
                    processingFeeInput.value = (principal * feePercentage / 100).toFixed(2);
                }
                
                // Display scheme details in the info box
                if (schemeInfoBox) {
                    schemeInfoBox.classList.remove('d-none');
                    
                    // Format date based on scheme duration
                    let maturityDate = '';
                    if (issueDateInput && issueDateInput.value) {
                        const issueDate = new Date(issueDateInput.value);
                        const durationDays = scheme.duration_days;
                        const maturity = new Date(issueDate);
                        maturity.setDate(maturity.getDate() + durationDays);
                        
                        // Format date as YYYY-MM-DD
                        maturityDate = maturity.toISOString().split('T')[0];
                    }
                    
                    schemeInfoBox.innerHTML = `
                        <div class="card-body bg-light">
                            <h5 class="card-title">${scheme.name} Details</h5>
                            <div class="row">
                                <div class="col-md-6">
                                    <p><strong>Type:</strong> ${scheme.scheme_type}</p>
                                    <p><strong>Interest Rate:</strong> ${scheme.interest_rate}%</p>
                                    <p><strong>Processing Fee:</strong> ${scheme.processing_fee_percentage}%</p>
                                </div>
                                <div class="col-md-6">
                                    <p><strong>Duration:</strong> ${scheme.duration_days} days</p>
                                    <p><strong>Min. Period:</strong> ${scheme.minimum_period_days} days</p>
                                    ${maturityDate ? `<p><strong>Expected Maturity:</strong> ${maturityDate}</p>` : ''}
                                </div>
                            </div>
                        </div>
                    `;
                }
                
                // After loading scheme details, calculate loan metrics
                calculateLoanMetrics();
            })
            .catch(error => {
                console.error('Error loading scheme details:', error);
                if (schemeInfoBox) {
                    schemeInfoBox.innerHTML = `
                        <div class="alert alert-danger">
                            Failed to load scheme details. Please try again or contact support.
                        </div>
                    `;
                    schemeInfoBox.classList.remove('d-none');
                }
            });
    }
    
    // Set up event listeners
    if (schemeSelect) {
        schemeSelect.addEventListener('change', loadSchemeDetails);
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
});