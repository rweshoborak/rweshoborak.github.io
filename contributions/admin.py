from django.contrib import admin
from django.utils.html import format_html
from .models import Group, Member, Contribution, AccountantLog


@admin.register(Group)
class GroupAdmin(admin.ModelAdmin):
    """Admin interface for Group model"""
    list_display = ('name', 'monthly_contribution', 'member_count', 'created_at')
    fields = ('name', 'monthly_contribution', 'description')
    readonly_fields = ('created_at',)

    def member_count(self, obj):
        """Display count of members in the group"""
        count = obj.members.filter(is_active=True).count()
        return format_html('<span style="color: green; font-weight: bold;">{}</span>', count)

    member_count.short_description = 'Active Members'


@admin.register(Member)
class MemberAdmin(admin.ModelAdmin):
    """Admin interface for Member model"""
    list_display = ('get_full_name', 'id_number', 'phone', 'joined_date', 'status_badge', 'total_paid')
    list_filter = ('is_active', 'group', 'joined_date')
    search_fields = ('user__first_name', 'user__last_name', 'id_number', 'phone', 'user__username')
    fields = ('user', 'group', 'id_number', 'phone', 'joined_date', 'is_active')
    readonly_fields = ('joined_date',)

    def get_full_name(self, obj):
        """Display full name"""
        return obj.user.get_full_name() or obj.user.username

    get_full_name.short_description = 'Full Name'

    def status_badge(self, obj):
        """Display status as colored badge"""
        if obj.is_active:
            return format_html(
                '<span style="background-color: #28a745; color: white; padding: 3px 10px; border-radius: 3px;">Active</span>'
            )
        else:
            return format_html(
                '<span style="background-color: #dc3545; color: white; padding: 3px 10px; border-radius: 3px;">Inactive</span>'
            )

    status_badge.short_description = 'Status'

    def total_paid(self, obj):
        """Display total amount paid"""
        from django.db.models import Sum
        total = obj.contributions.aggregate(Sum('amount'))['amount__sum'] or 0
        return format_html(
            '<span style="color: #007bff; font-weight: bold;">TZS {}</span>',
            f"{total:,.0f}"
        )

    total_paid.short_description = 'Total Paid'


@admin.register(Contribution)
class ContributionAdmin(admin.ModelAdmin):
    """Admin interface for Contribution model"""
    list_display = ('member_name', 'get_month_year', 'amount_display', 'paid_date', 'notes_preview')
    list_filter = ('year', 'month', 'paid_date', 'member__group')
    search_fields = ('member__user__first_name', 'member__user__last_name', 'member__id_number')
    fields = ('member', 'year', 'month', 'amount', 'notes', 'paid_date')
    readonly_fields = ('paid_date',)
    date_hierarchy = 'paid_date'

    def member_name(self, obj):
        """Display member name"""
        return obj.member.user.get_full_name() or obj.member.user.username

    member_name.short_description = 'Member'

    def get_month_year(self, obj):
        """Display month and year"""
        return f"{obj.get_month_name()} {obj.year}"

    get_month_year.short_description = 'Month/Year'

    def amount_display(self, obj):
        """Display amount with currency"""
        return format_html(
            '<span style="color: #28a745; font-weight: bold;">TZS {:,.0f}</span>',
            obj.amount
        )

    amount_display.short_description = 'Amount'

    def notes_preview(self, obj):
        """Display preview of notes"""
        if obj.notes:
            preview = obj.notes[:30] + '...' if len(obj.notes) > 30 else obj.notes
            return preview
        return '-'

    notes_preview.short_description = 'Notes'

    def get_queryset(self, request):
        """Order contributions by year and month"""
        qs = super().get_queryset(request)
        return qs.order_by('-year', '-month')


@admin.register(AccountantLog)
class AccountantLogAdmin(admin.ModelAdmin):
    """Admin interface for AccountantLog model - audit trail"""
    list_display = ('accountant_name', 'action_type_badge', 'amount_display', 'timestamp', 'description_preview')
    list_filter = ('action_type', 'timestamp', 'accountant')
    search_fields = ('accountant__username', 'accountant__first_name', 'accountant__last_name', 'description')
    fields = ('accountant', 'action_type', 'description', 'amount', 'timestamp')
    readonly_fields = ('timestamp',)
    date_hierarchy = 'timestamp'

    def accountant_name(self, obj):
        """Display accountant name"""
        if obj.accountant:
            return obj.accountant.get_full_name() or obj.accountant.username
        return 'System'

    accountant_name.short_description = 'Accountant'

    def action_type_badge(self, obj):
        """Display action type as colored badge"""
        colors = {
            'ADD_CONTRIBUTION': '#007bff',
            'UPDATE_CONTRIBUTION': '#ffc107',
            'BULK_PAYMENT': '#28a745',
        }
        color = colors.get(obj.action_type, '#6c757d')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 8px; border-radius: 3px; font-size: 0.9em;">{}</span>',
            color,
            obj.get_action_type_display()
        )

    action_type_badge.short_description = 'Action Type'

    def amount_display(self, obj):
        """Display amount if present"""
        if obj.amount:
            return format_html(
                '<span style="color: #28a745; font-weight: bold;">TZS {:,.0f}</span>',
                obj.amount
            )
        return '-'

    amount_display.short_description = 'Amount'

    def description_preview(self, obj):
        """Display preview of description"""
        preview = obj.description[:40] + '...' if len(obj.description) > 40 else obj.description
        return preview

    description_preview.short_description = 'Description'

    def has_add_permission(self, request):
        """Logs are created automatically - prevent manual addition"""
        return False

    def has_delete_permission(self, request, obj=None):
        """Prevent deletion of audit logs"""
        return False

    def get_queryset(self, request):
        """Order logs by most recent first"""
        qs = super().get_queryset(request)
        return qs.order_by('-timestamp')


# Customize admin site
admin.site.site_header = "Ujirani Mwema - Admin Panel"
admin.site.site_title = "Ujirani Mwema Admin"
admin.site.index_title = "Welcome to Ujirani Mwema Management System"
