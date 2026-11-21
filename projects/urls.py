from django.urls import path

from . import views

app_name = "projects"

urlpatterns = [
    path("", views.project_list, name="list"),
    path("new/", views.project_create, name="create"),
    path("<int:pk>/", views.project_detail, name="detail"),
    path("<int:pk>/edit/", views.project_update, name="update"),
    path("<int:pk>/delete/", views.project_delete, name="delete"),
    # team members
    path("<int:project_pk>/members/add/", views.member_add, name="member_add"),
    path("<int:project_pk>/members/<int:pk>/remove/", views.member_remove, name="member_remove"),
    # milestones
    path("<int:project_pk>/milestones/new/", views.milestone_create, name="milestone_create"),
    path("milestones/<int:pk>/edit/", views.milestone_update, name="milestone_update"),
    path("milestones/<int:pk>/delete/", views.milestone_delete, name="milestone_delete"),
    # cookie preference
    path("preferences/view-mode/", views.set_view_mode, name="set_view_mode"),
]
