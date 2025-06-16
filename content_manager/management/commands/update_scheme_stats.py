import datetime
from django.core.management.base import BaseCommand
from django.db.models import Sum, Count, Q
from django.utils import timezone
from content_manager.models import Scheme, SchemeUsageStats
from branches.models import Branch
from transactions.models import Loan


class Command(BaseCommand):
    help = 'Updates usage statistics for loan schemes'

    def add_arguments(self, parser):
        parser.add_argument(
            '--days',
            type=int,
            default=30,
            help='Number of days to include in the report (default: 30)'
        )
        parser.add_argument(
            '--branch',
            type=int,
            help='Branch ID to filter statistics for (default: all branches)'
        )
        parser.add_argument(
            '--scheme',
            type=int,
            help='Scheme ID to filter statistics for (default: all schemes)'
        )

    def handle(self, *args, **options):
        days = options['days']
        branch_id = options.get('branch')
        scheme_id = options.get('scheme')
        
        # Calculate date range
        end_date = timezone.now().date()
        start_date = end_date - datetime.timedelta(days=days)
        
        self.stdout.write(f"Updating scheme statistics from {start_date} to {end_date}")
        
        # Get branches to process
        branches = Branch.objects.all()
        if branch_id:
            branches = branches.filter(id=branch_id)
        
        # Get schemes to process
        schemes = Scheme.objects.filter(is_active=True)
        if scheme_id:
            schemes = schemes.filter(id=scheme_id)
        
        stats_updated = 0
        
        # First update global stats (across all branches)
        for scheme in schemes:
            # Get all loans using this scheme in the date range
            loans = Loan.objects.filter(
                scheme=scheme,
                issue_date__gte=start_date,
                issue_date__lte=end_date
            )
            
            if not loans.exists():
                self.stdout.write(f"No loans found for scheme '{scheme.name}' in the date range")
                continue
            
            # Calculate statistics
            stats = self._calculate_stats(loans)
            
            # Create or update stats record
            scheme_stats, created = SchemeUsageStats.objects.update_or_create(
                scheme=scheme,
                branch=None,  # Global stats
                start_date=start_date,
                end_date=end_date,
                defaults=stats
            )
            
            stats_updated += 1
            action = "Created" if created else "Updated"
            self.stdout.write(f"{action} global statistics for scheme '{scheme.name}'")
        
        # Then update branch-specific stats
        for branch in branches:
            for scheme in schemes:
                # Get all loans using this scheme at this branch in the date range
                loans = Loan.objects.filter(
                    scheme=scheme,
                    branch=branch,
                    issue_date__gte=start_date,
                    issue_date__lte=end_date
                )
                
                if not loans.exists():
                    continue
                
                # Calculate statistics
                stats = self._calculate_stats(loans)
                
                # Create or update stats record
                scheme_stats, created = SchemeUsageStats.objects.update_or_create(
                    scheme=scheme,
                    branch=branch,
                    start_date=start_date,
                    end_date=end_date,
                    defaults=stats
                )
                
                stats_updated += 1
                action = "Created" if created else "Updated"
                self.stdout.write(f"{action} statistics for scheme '{scheme.name}' at branch '{branch.name}'")
        
        self.stdout.write(self.style.SUCCESS(f"Successfully updated {stats_updated} scheme statistics records"))

    def _calculate_stats(self, loans):
        """Calculate statistics for a queryset of loans"""
        # Count loans by status
        total_count = loans.count()
        active_count = loans.filter(status='active').count()
        completed_count = loans.filter(status='closed').count()
        defaulted_count = loans.filter(status__in=['defaulted', 'auctioned']).count()
        
        # Sum financial metrics
        principal_sum = loans.aggregate(Sum('principal_amount'))['principal_amount__sum'] or 0
        interest_sum = loans.aggregate(Sum('interest_amount'))['interest_amount__sum'] or 0
        fees_sum = loans.aggregate(Sum('processing_fee'))['processing_fee__sum'] or 0
        
        return {
            'total_loans_count': total_count,
            'active_loans_count': active_count,
            'completed_loans_count': completed_count,
            'defaulted_loans_count': defaulted_count,
            'total_principal_amount': principal_sum,
            'total_interest_earned': interest_sum,
            'total_processing_fees': fees_sum
        }