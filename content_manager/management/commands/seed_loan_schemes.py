from django.core.management.base import BaseCommand
from django.db import transaction
from content_manager.models import Scheme


class Command(BaseCommand):
    help = 'Seeds the database with standard loan schemes'

    def handle(self, *args, **options):
        self.stdout.write('Creating standard loan schemes...')
        
        # List of standard schemes with their parameters
        standard_schemes = [
            {
                'name': 'Standard Gold Loan',
                'code': 'STD_GOLD',
                'scheme_type': 'standard',
                'description': 'Standard gold loan scheme with competitive interest rates. Suitable for most customers.',
                'interest_rate': 12.0,
                'duration_days': 90,
                'no_interest_period_days': 0,
                'minimum_period_days': 30,
                'processing_fee_percentage': 1.0,
                'is_active': True,
            },
            {
                'name': 'Quick Gold Loan',
                'code': 'QUICK_GOLD',
                'scheme_type': 'flexible',
                'description': 'Short-term gold loan with flexible repayment options and a grace period.',
                'interest_rate': 18.0, 
                'duration_days': 30,
                'no_interest_period_days': 7,
                'minimum_period_days': 0,
                'processing_fee_percentage': 1.5,
                'is_active': True,
            },
            {
                'name': 'Premium Gold Loan',
                'code': 'PREMIUM_GOLD',
                'scheme_type': 'premium',
                'description': 'Premium gold loan scheme with longer duration and competitive rates for high-value loans.',
                'interest_rate': 9.0,
                'duration_days': 180,
                'no_interest_period_days': 0,
                'minimum_period_days': 60,
                'processing_fee_percentage': 0.5,
                'is_active': True,
            },
            {
                'name': 'Festival Special',
                'code': 'FESTIVAL',
                'scheme_type': 'custom',
                'description': 'Special festival season loan with reduced interest rates and processing fees.',
                'interest_rate': 10.0,
                'duration_days': 90,
                'no_interest_period_days': 15,
                'minimum_period_days': 0,
                'processing_fee_percentage': 0.0,
                'is_active': True,
            },
            {
                'name': 'Jewel Loan',
                'code': 'JEWEL',
                'scheme_type': 'standard',
                'description': 'Specialized loan for jewelry items with careful appraisal and higher loan-to-value ratio.',
                'interest_rate': 15.0,
                'duration_days': 120,
                'no_interest_period_days': 0,
                'minimum_period_days': 30,
                'processing_fee_percentage': 1.0,
                'is_active': True,
            },
            {
                'name': 'Silver Loan',
                'code': 'SILVER',
                'scheme_type': 'standard',
                'description': 'Loan scheme specifically for silver items with adjusted interest rates.',
                'interest_rate': 18.0,
                'duration_days': 60,
                'no_interest_period_days': 0,
                'minimum_period_days': 15,
                'processing_fee_percentage': 1.5,
                'is_active': True,
            },
            {
                'name': 'Long-term Gold Loan',
                'code': 'LONG_GOLD',
                'scheme_type': 'premium',
                'description': 'Long duration gold loan scheme designed for customers needing extended repayment periods.',
                'interest_rate': 8.0,
                'duration_days': 365,
                'no_interest_period_days': 0,
                'minimum_period_days': 90,
                'processing_fee_percentage': 2.0,
                'is_active': True,
            },
        ]
        
        count_created = 0
        count_updated = 0
        
        with transaction.atomic():
            for scheme_data in standard_schemes:
                # Try to get existing scheme by code
                scheme, created = Scheme.objects.update_or_create(
                    code=scheme_data['code'],
                    defaults=scheme_data
                )
                
                if created:
                    count_created += 1
                else:
                    count_updated += 1
        
        self.stdout.write(self.style.SUCCESS(
            f'Successfully seeded {count_created} new schemes and updated {count_updated} existing schemes'
        ))