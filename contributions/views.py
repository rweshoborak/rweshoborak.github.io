from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth import authenticate, login, logout
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.db.models import Sum, Q
from datetime import datetime
from .models import Member, Contribution, Group, AccountantLog


def login_view(request):
    """Handle user login - accepts both members and accountants"""
    if request.user.is_authenticated:
        # Redirect if already logged in
        if request.user.is_staff:
            return redirect('accountant_dashboard')
        else:
            return redirect('member_dashboard')

    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        user = authenticate(request, username=username, password=password)

        if user is not None:
            login(request, user)
            # Redirect based on user type
            if user.is_staff:
                return redirect('accountant_dashboard')
            else:
                return redirect('member_dashboard')
        else:
            messages.error(request, 'Invalid username or password')

    return render(request, 'login.html')


def logout_view(request):
    """Handle user logout"""
    logout(request)
    return redirect('login')


@login_required(login_url='login')
def member_dashboard(request):
    try:
        member = Member.objects.get(user=request.user)
    except Member.DoesNotExist:
        return render(request, 'error.html', {
            'message': 'You are not registered as a member'
        })

    # Get contributions
    paid_contributions = member.contributions.all().order_by('-year', '-month')
    total_paid = paid_contributions.aggregate(Sum('amount'))['amount__sum'] or 0

    # Calculate expected payment (CORRECT WAY)
    months_paid = paid_contributions.count()
    monthly_amount = member.group.monthly_contribution
    expected_payment = months_paid * monthly_amount  # PROPER CALCULATION

    context = {
        'member': member,
        'contributions': paid_contributions,
        'total_paid': total_paid,
        'monthly_amount': monthly_amount,
        'months_paid': months_paid,
        'expected_payment': expected_payment,  # Pass calculated value
    }

    return render(request, 'member_dashboard.html', context)
# @login_required(login_url='login')
# def member_dashboard(request):
#     """Member view their contributions and payment history"""
#     try:
#         member = Member.objects.get(user=request.user)
#     except Member.DoesNotExist:
#         return render(request, 'error.html', {
#             'message': 'You are not registered as a member of any group'
#         })
#
#     # Get all paid contributions for this member
#     paid_contributions = member.contributions.all().order_by('-year', '-month')
#
#     # Calculate total paid
#     total_paid = paid_contributions.aggregate(Sum('amount'))['amount__sum'] or 0
#
#     # Get group info
#     group = member.group
#
#     context = {
#         'member': member,
#         'contributions': paid_contributions,
#         'total_paid': total_paid,
#         'monthly_amount': group.monthly_contribution,
#         'page_title': 'My Contributions',
#     }
#
#     return render(request, 'member_dashboard.html', context)


@login_required(login_url='login')
def accountant_dashboard(request):
    """Accountant main dashboard with overview statistics"""
    if not request.user.is_staff:
        messages.error(request, 'Access denied - Accountant only')
        return redirect('member_dashboard')

    group = Group.objects.first()
    if not group:
        group = Group.objects.create(
            name="Ujirani Mwema",
            monthly_contribution=5000
        )

    members = Member.objects.filter(group=group, is_active=True)

    # Calculate statistics
    total_members = members.count()
    total_collected = Contribution.objects.aggregate(Sum('amount'))['amount__sum'] or 0

    # Members with unpaid months
    members_with_unpaid = []
    for member in members:
        unpaid = member.get_unpaid_months()
        if unpaid:
            members_with_unpaid.append({
                'member': member,
                'unpaid_count': len(unpaid)
            })

    context = {
        'group': group,
        'total_members': total_members,
        'total_collected': total_collected,
        'members_with_unpaid': members_with_unpaid,
        'unpaid_count': len(members_with_unpaid),
        'page_title': 'Accountant Dashboard',
    }

    return render(request, 'accountant_dashboard.html', context)


@login_required(login_url='login')
def manage_member(request, member_id):
    """Manage individual member contributions - add or distribute payments"""
    if not request.user.is_staff:
        messages.error(request, 'Access denied - Accountant only')
        return redirect('member_dashboard')

    member = get_object_or_404(Member, id=member_id)
    group = member.group

    if request.method == 'POST':
        action = request.POST.get('action')

        if action == 'add_contribution':
            try:
                year = int(request.POST.get('year'))
                month = int(request.POST.get('month'))
                amount = float(request.POST.get('amount'))
                notes = request.POST.get('notes', '')

                if amount <= 0:
                    messages.error(request, 'Amount must be greater than 0')
                else:
                    contribution, created = Contribution.objects.update_or_create(
                        member=member,
                        year=year,
                        month=month,
                        defaults={'amount': amount, 'notes': notes}
                    )

                    # Log activity
                    AccountantLog.objects.create(
                        accountant=request.user,
                        action_type='ADD_CONTRIBUTION',
                        description=f"Added {amount} for {member.user.get_full_name()} - {contribution.get_month_name()} {year}",
                        amount=amount
                    )

                    messages.success(request,
                                     f'Contribution of {amount} TZS added successfully for {contribution.get_month_name()} {year}')
            except (ValueError, TypeError):
                messages.error(request, 'Invalid input - please check your values')

            return redirect('manage_member', member_id=member.id)

        elif action == 'bulk_payment':
            try:
                total_amount = float(request.POST.get('total_amount'))
                unpaid_months = member.get_unpaid_months()

                if total_amount <= 0:
                    messages.error(request, 'Amount must be greater than 0')
                elif not unpaid_months:
                    messages.warning(request, 'No unpaid months for this member')
                else:
                    monthly_amount = float(group.monthly_contribution)
                    remaining_amount = total_amount
                    months_filled = 0

                    for year, month in unpaid_months:
                        if remaining_amount >= monthly_amount:
                            Contribution.objects.update_or_create(
                                member=member,
                                year=year,
                                month=month,
                                defaults={'amount': monthly_amount}
                            )
                            remaining_amount -= monthly_amount
                            months_filled += 1
                        else:
                            break

                    # Log activity
                    AccountantLog.objects.create(
                        accountant=request.user,
                        action_type='BULK_PAYMENT',
                        description=f"Distributed {total_amount} to {member.user.get_full_name()} across {months_filled} months. Remaining: {remaining_amount}",
                        amount=total_amount
                    )

                    if remaining_amount > 0:
                        messages.success(request,
                                         f'Distribution completed! {months_filled} months filled. Remaining: {remaining_amount} TZS')
                    else:
                        messages.success(request, f'Distribution completed! {months_filled} months filled.')
            except (ValueError, TypeError):
                messages.error(request, 'Invalid input - please check your values')

            return redirect('manage_member', member_id=member.id)

    # Get member data
    unpaid_months = member.get_unpaid_months()
    paid_contributions = member.contributions.all().order_by('-year', '-month')
    total_paid = paid_contributions.aggregate(Sum('amount'))['amount__sum'] or 0

    context = {
        'member': member,
        'group': group,
        'unpaid_months': unpaid_months,
        'paid_contributions': paid_contributions,
        'total_paid': total_paid,
        'months': Contribution.MONTHS,
        'current_year': datetime.now().year,
        'page_title': f'Manage {member.user.get_full_name()}',
    }

    return render(request, 'manage_member.html', context)


@login_required(login_url='login')
def member_list(request):
    """List all members for accountant management"""
    if not request.user.is_staff:
        messages.error(request, 'Access denied - Accountant only')
        return redirect('member_dashboard')

    group = Group.objects.first()
    if not group:
        group = Group.objects.create(
            name="Ujirani Mwema",
            monthly_contribution=5000
        )

    # Filter members
    status_filter = request.GET.get('status', 'all')
    members = Member.objects.filter(group=group)

    if status_filter == 'active':
        members = members.filter(is_active=True)
    elif status_filter == 'inactive':
        members = members.filter(is_active=False)

    members = members.order_by('user__first_name')

    # Add statistics to each member
    members_with_stats = []
    for member in members:
        paid = member.contributions.aggregate(Sum('amount'))['amount__sum'] or 0
        unpaid_count = len(member.get_unpaid_months())
        members_with_stats.append({
            'member': member,
            'paid': paid,
            'unpaid_count': unpaid_count,
        })

    context = {
        'members_with_stats': members_with_stats,
        'group': group,
        'total_members': members.count(),
        'status_filter': status_filter,
        'page_title': 'Members List',
    }

    return render(request, 'member_list.html', context)


@login_required(login_url='login')
def reports(request):
    """Generate and display reports and statistics"""
    if not request.user.is_staff:
        messages.error(request, 'Access denied - Accountant only')
        return redirect('member_dashboard')

    group = Group.objects.first()
    if not group:
        group = Group.objects.create(
            name="Ujirani Mwema",
            monthly_contribution=5000
        )

    members = Member.objects.filter(group=group, is_active=True)

    # Get all contributions
    all_contributions = Contribution.objects.all().order_by('-year', '-month')

    # Summary statistics
    total_collected = all_contributions.aggregate(Sum('amount'))['amount__sum'] or 0
    total_expected = members.count() * group.monthly_contribution

    # Members status
    member_stats = []
    fully_paid = 0
    partially_paid = 0

    for member in members:
        paid = member.contributions.aggregate(Sum('amount'))['amount__sum'] or 0
        unpaid_months = member.get_unpaid_months()
        unpaid_count = len(unpaid_months)

        if unpaid_count == 0:
            fully_paid += 1
            status = 'Up to Date'
        elif paid > 0:
            partially_paid += 1
            status = 'Partially Paid'
        else:
            status = 'Not Paid'

        member_stats.append({
            'member': member,
            'paid': paid,
            'unpaid_months': unpaid_count,
            'status': status,
        })

    # Calculate percentages
    collection_rate = (total_collected / total_expected * 100) if total_expected > 0 else 0

    context = {
        'group': group,
        'total_collected': total_collected,
        'total_expected': total_expected,
        'total_members': members.count(),
        'fully_paid': fully_paid,
        'partially_paid': partially_paid,
        'not_paid': members.count() - fully_paid - partially_paid,
        'collection_rate': round(collection_rate, 2),
        'member_stats': member_stats,
        'all_contributions': all_contributions[:50],  # Last 50 transactions
        'page_title': 'Reports & Statistics',
    }

    return render(request, 'reports.html', context)