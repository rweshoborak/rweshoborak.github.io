# contributions/urls.py
from django.urls import path
from . import views

urlpatterns = [
    path('login/', views.login_view, name='login'),
    path('members/', views.member_dashboard, name='member_dashboard'),
    path('accountant/', views.accountant_dashboard, name='accountant_dashboard'),
    path('member/<int:member_id>/', views.manage_member, name='manage_member'),
    path('members-list/', views.member_list, name='member_list'),
    path('reports/', views.reports, name='reports'),
path('logout/', views.logout_view, name='logout'),

]