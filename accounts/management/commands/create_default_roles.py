from django.core.management.base import BaseCommand
from django.contrib.auth.models import Permission
from accounts.models import Role
from django.contrib.contenttypes.models import ContentType
from django.db import transaction

class Command(BaseCommand):
    help = 'Creates default roles with appropriate permissions'

    def handle(self, *args, **kwargs):
        with transaction.atomic():
            # Define roles and their descriptions
            roles = {
                'Regional Manager': {
                    'description': 'Oversees multiple branches, ensuring compliance, profitability, and customer satisfaction.',
                    'permissions': [
                        # Branch management
                        'view_branch', 'change_branch', 'add_branch', 'delete_branch',
                        'view_branchsettings', 'change_branchsettings',
                        # Staff management
                        'view_customuser', 'change_customuser', 'add_customuser', 'delete_customuser',
                        'view_role', 'change_role',
                        # Financial management
                        'view_report', 'add_report', 'change_report',
                        # Access to all operations
                        'view_loan', 'change_loan', 'add_loan', 'delete_loan',
                        'view_payment', 'change_payment', 'add_payment', 'delete_payment',
                        'view_item', 'change_item', 'add_item', 'delete_item',
                        'view_customer', 'change_customer', 'add_customer', 'delete_customer',
                    ]
                },
                'Branch Manager': {
                    'description': 'Responsible for day-to-day operations, staff supervision, and financial performance of a specific branch.',
                    'permissions': [
                        # Branch operations
                        'view_branch', 'change_branchsettings',
                        # Staff management
                        'view_customuser', 'change_customuser',
                        # Operations management
                        'view_loan', 'change_loan', 'add_loan',
                        'view_payment', 'add_payment',
                        'view_item', 'change_item', 'add_item',
                        'view_customer', 'change_customer', 'add_customer',
                        'view_report',
                    ]
                },
                'Sales Associate': {
                    'description': 'Interacts with customers, assesses and appraises items, processes loans, and manages inventory.',
                    'permissions': [
                        'view_item', 'add_item', 'change_item',
                        'view_customer', 'add_customer', 'change_customer',
                        'view_loan', 'add_loan',
                        'view_payment', 'add_payment',
                        'add_appraisal', 'view_appraisal',
                    ]
                },
                'Customer Service Representative': {
                    'description': 'Handles inquiries, resolves issues, and provides support to customers.',
                    'permissions': [
                        'view_customer', 'add_customer', 'change_customer',
                        'view_loan', 'view_payment', 'view_item',
                    ]
                },
                'Appraiser': {
                    'description': 'Determines the fair market value of items offered as collateral.',
                    'permissions': [
                        'view_item', 'change_item',
                        'add_appraisal', 'change_appraisal', 'view_appraisal',
                        'view_customer',
                    ]
                },
                'Inventory Specialist': {
                    'description': 'Manages the storage, tracking, and sale of items held by the pawnshop.',
                    'permissions': [
                        'view_item', 'change_item', 'add_item',
                        'view_category', 'add_category', 'change_category',
                        'view_customer',
                    ]
                },
                'Accountant': {
                    'description': 'Manages financial records, compliance, and reporting.',
                    'permissions': [
                        'view_loan', 'view_payment',
                        'view_report', 'add_report',
                        'view_branch',
                    ]
                },
                'Security Personnel': {
                    'description': 'Ensures the safety and security of the pawnshop and its items.',
                    'permissions': [
                        'view_item',
                        'view_customer',
                        'view_branch',
                    ]
                },
                'Administrative Assistant': {
                    'description': 'Supports various administrative tasks.',
                    'permissions': [
                        'view_customer',
                        'view_item',
                        'view_loan',
                        'view_payment',
                        'view_report',
                    ]
                },
                'IT Support': {
                    'description': 'Manages technology infrastructure and software for branches.',
                    'permissions': [
                        'view_branch', 'view_branchsettings',
                        'view_customuser',
                        'view_biometricsetting', 'change_biometricsetting',
                    ]
                },
                'Marketing Manager': {
                    'description': 'Drives business growth and attracts customers.',
                    'permissions': [
                        'view_customer',
                        'view_item',
                        'view_report',
                        'view_branch',
                    ]
                },
                'Compliance Officer': {
                    'description': 'Ensures adherence to regulations and legal requirements.',
                    'permissions': [
                        'view_loan', 'view_payment',
                        'view_customer', 'view_item',
                        'view_report', 'add_report',
                        'view_branch', 'view_branchsettings',
                    ]
                },
                'HR Manager': {
                    'description': 'Manages employee-related tasks and payroll.',
                    'permissions': [
                        'view_customuser', 'change_customuser', 'add_customuser',
                        'view_role',
                        'view_branch',
                    ]
                },
            }

            # Create roles and assign permissions
            for role_name, role_data in roles.items():
                role, created = Role.objects.get_or_create(
                    name=role_name,
                    defaults={'description': role_data['description']}
                )
                
                if not created:
                    role.description = role_data['description']
                    role.save()

                # Get all permissions for this role
                permissions = Permission.objects.filter(codename__in=role_data['permissions'])
                role.permissions.set(permissions)

                action = 'Created' if created else 'Updated'
                self.stdout.write(
                    self.style.SUCCESS(
                        f'{action} role "{role_name}" with {permissions.count()} permissions'
                    )
                )