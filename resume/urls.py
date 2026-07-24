from django.urls import path
from . import views

urlpatterns = [
    path("", views.home, name="home"),
    path("resume/",views.resume, name="resume"),
    path("fetchresumedata",views.fetchresumedata, name="fetchresumedata"),
    path("resumelist",views.resumelist, name="resumelist"),
    path("resumedetail/<int:id>",views.resumedetail, name="resumedetail"),
    path("editresume/<int:id>",views.editresume, name="editresume"),
    path("fetcheditresumedata/<int:id>",views.fetcheditresumedata, name="fetcheditresumedata"),
    path("deleteresume/<int:id>",views.deleteresume, name="deleteresume"),
    path("resume_pdf/<int:id>",views.resume_pdf, name="resume_pdf"),
    path("user",views.user,name="user"),
    path("fetchuserdata",views.fetchuserdata, name="fetchuserdata"),
    path("login",views.login, name="login"),
    path("fetchlogindata",views.fetchlogindata, name="fetchlogindata"),
    path("logout",views.logout, name="logout"),
    path("welcome",views.welcome, name="welcome"),
    path("templates", views.templates, name="templates"),
    path("select-template/<int:id>", views.select_template)
]