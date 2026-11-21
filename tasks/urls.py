from django.urls import path

from . import views

app_name = "tasks"

urlpatterns = [
    path("", views.task_list, name="list"),
    path("mine/", views.my_tasks, name="mine"),
    path("new/<int:project_pk>/", views.task_create, name="create"),
    path("<int:pk>/", views.task_detail, name="detail"),
    path("<int:pk>/edit/", views.task_update, name="update"),
    path("<int:pk>/delete/", views.task_delete, name="delete"),
    path("<int:pk>/status/", views.task_set_status, name="set_status"),
    path("<int:pk>/comments/add/", views.task_comment_add, name="comment_add"),
]
