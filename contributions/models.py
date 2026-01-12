from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from datetime import datetime, timedelta


class Group(models.Model):
    """Group information"""
    name = models.CharField(max_length=100, default="Ujirani Mwema")
    monthly_contribution = models.DecimalField(max_digits=10, decimal_places=2, default=5000)
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name

    class Meta:
        verbose_name_plural = "Groups"


class Member(models.Model):
    """Group member"""
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    group = models.ForeignKey(Group, on_delete=models.CASCADE, related_name='members')
    phone = models.CharField(max_length=15, blank=True)
    id_number = models.CharField(max_length=20, unique=True)
    joined_date = models.DateField(auto_now_add=True)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.user.get_full_name()} - {self.id_number}"

    class Meta:
        verbose_name_plural = "Members"

    def get_unpaid_months(self):
        """Get months where member hasn't paid the full amount"""
        group = self.group
        today = timezone.now().date()
        current_year = today.year
        current_month = today.month

        # Get all months from join date to current month
        unpaid_months = []
        start_month = self.joined_date.month
        start_year = self.joined_date.year

        for year in range(start_year, current_year + 1):
            start = start_month if year == start_year else 1
            end = current_month if year == current_year else 12

            for month in range(start, end + 1):
                # Check if member has paid for this month
                contribution = Contribution.objects.filter(
                    member=self,
                    year=year,
                    month=month,
                    amount__gte=group.monthly_contribution
                ).exists()

                if not contribution:
                    unpaid_months.append((year, month))

        return unpaid_months


class Contribution(models.Model):
    """Member contribution tracking"""
    MONTHS = [
        (1, 'January'), (2, 'February'), (3, 'March'), (4, 'April'),
        (5, 'May'), (6, 'June'), (7, 'July'), (8, 'August'),
        (9, 'September'), (10, 'October'), (11, 'November'), (12, 'December')
    ]

    member = models.ForeignKey(Member, on_delete=models.CASCADE, related_name='contributions')
    year = models.IntegerField()
    month = models.IntegerField(choices=MONTHS)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    paid_date = models.DateField(auto_now_add=True)
    notes = models.TextField(blank=True)

    class Meta:
        unique_together = ('member', 'year', 'month')
        ordering = ['-year', '-month']
        verbose_name_plural = "Contributions"

    def __str__(self):
        month_name = dict(self.MONTHS)[self.month]
        return f"{self.member.user.get_full_name()} - {month_name} {self.year}: {self.amount}"

    def get_month_name(self):
        """Return month name"""
        return dict(self.MONTHS)[self.month]


class AccountantLog(models.Model):
    """Track accountant activities for audit trail"""
    ACTION_TYPES = [
        ('ADD_CONTRIBUTION', 'Added Contribution'),
        ('UPDATE_CONTRIBUTION', 'Updated Contribution'),
        ('BULK_PAYMENT', 'Bulk Payment Distribution'),
    ]

    accountant = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    action_type = models.CharField(max_length=20, choices=ACTION_TYPES)
    description = models.TextField()
    amount = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name_plural = "Accountant Logs"
        ordering = ['-timestamp']

    def __str__(self):
        return f"{self.accountant.username} - {self.get_action_type_display()}"