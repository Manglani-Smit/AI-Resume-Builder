from django.shortcuts import render, redirect
from django.contrib import messages
from django.utils import timezone
from datetime import datetime
from django.db.models import Sum
from django.http import HttpResponse
from .models import *
from django.template.loader import get_template
from xhtml2pdf import pisa
from django.core.mail import send_mail
import razorpay
from openai import OpenAI
from django.conf import settings# from AI_Resume_Builder.resume.models import Resume
from django.contrib.auth.hashers import make_password, check_password
import json

client = OpenAI(
    api_key=settings.OPENROUTER_API_KEY,
    base_url="https://openrouter.ai/api/v1"
)

def home(request):
    return render(request, "index.html")

def fetchresumedata(request):
    if "log_id" not in request.session:
        messages.error(request, "Please login first")
        return redirect("/login")
    name = request.POST.get("name")
    email = request.POST.get("email")
    phone = request.POST.get("phone")
    skills = request.POST.get("skills")
    education = request.POST.get("education")
    prompt = f"""
You are an expert ATS Resume Writer.

Candidate Details:

Name: {name}
Education: {education}
Skills: {skills}
Experience: Fresher

Generate a professional ATS-friendly resume.

Return ONLY valid JSON.

Use exactly this format:

{{
    "summary": "...",
    "objective": "...",
    "projects": "...",
    "experience": "...",
    "certifications": "...",
    "achievements": "..."
}}

Rules:
- Do not write markdown.
- Do not use ```json.
- Do not add explanation.
- Do not add greetings.
- Output must start with {{ and end with }} only.
"""
    try:
        response = client.chat.completions.create(
            model="openrouter/free",
            messages=[
                {
                    "role": "user",
                    "content": prompt
                }
            ]
        )

        ai_response = response.choices[0].message.content

        print(ai_response)

        resume_data = json.loads(ai_response)

    except Exception as e:

        print(e)

        messages.error(request, "AI service is unavailable. Please try again.")

        return redirect("/resume")


    selected_template = request.session.get("selected_template", 1)
    insertquery = Resume(name=name,email=email,phone=phone,skills=skills,education=education,summary=resume_data["summary"],objective=resume_data["objective"],projects=resume_data["projects"],experience=resume_data["experience"],certifications=resume_data["certifications"],achievements=resume_data["achievements"],template_id=selected_template)
    insertquery.save()
    messages.success(request, "Successfully fetched resume data")
    return redirect(f"/resumedetail/{insertquery.id}")

def resumelist(request):
    if "log_id" not in request.session:
        messages.error(request, "Please login first")
        return redirect("/login")
    resumes =  Resume.objects.all()
    return render(request, "resumelist.html", {"resumes":resumes})

def resumedetail(request, id):

    if "log_id" not in request.session:
        messages.error(request,"Please login first")
        return redirect("/login")

    resume = Resume.objects.get(id=id)

    skills = [skill.strip() for skill in resume.skills.split(",")]

    if resume.template_id == 1:
        template = "resume_modern.html"

    elif resume.template_id == 2:
        template = "resume_professional.html"

    elif resume.template_id == 3:
        template = "resume_minimal.html"

    elif resume.template_id == 4:
        template = "resume_creative.html"

    else:
        template = "resume_executive.html"

    return render(request, template, {"resume": resume, "skills": skills})
def editresume(request,id):
    if "log_id" not in request.session:
        messages.error(request, "Please login first")
        return redirect("/login")
    resume = Resume.objects.get(id=id)
    return render(request, "editresume.html", {"resume":resume})

def fetcheditresumedata(request, id):
        if "log_id" not in request.session:
            messages.error(request, "Please login first")
            return redirect("/login")

        name = request.POST.get("name")
        email = request.POST.get("email")
        phone = request.POST.get("phone")
        skills = request.POST.get("skills")
        education = request.POST.get("education")

        resume = Resume.objects.get(id=id)

        resume.name = name
        resume.email = email
        resume.phone = phone
        resume.skills = skills
        resume.education = education

        resume.save()

        messages.success(request, "Resume Updated Successfully")

        return redirect("/user")

def deleteresume(request, id):
    if "log_id" not in request.session:
        messages.error(request, "Please login first")
        return redirect("/login")

    resume = Resume.objects.get(id=id)

    resume.delete()

    messages.success(request, "Resume Deleted Successfully")

    return redirect("/resumelist")


def resume_pdf(request, id):
    if "log_id" not in request.session:
        messages.error(request, "Please login first")
        return redirect("/login")

    try:
        resume = Resume.objects.get(id=id)
    except Resume.DoesNotExist:
        messages.error(request, "Resume not found")
        return redirect("/user")

    skills = [skill.strip() for skill in resume.skills.split(",")]

    # 1. Template load karo
    template = get_template("resume_modern.html")
    html = template.render({
        "resume": resume,
        "skills": skills,
        "pdf": True
    })

    # 2. HTTP Response create karo PDF content type ke saath
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = 'attachment; filename="Resume.pdf"'

    # 3. PDF generate karke response me daalo
    pisa_status = pisa.CreatePDF(html, dest=response)

    # 4. Agar error nahi hai toh seedha response return karo
    if not pisa_status.err:
        return response

    return HttpResponse('PDF Generation Error', status=500)

def user(request):
    return render(request, "User.html")

def fetchuserdata(request):
    name = request.POST.get("name")
    email = request.POST.get("email")
    phone = request.POST.get("phone")
    password = request.POST.get("password")
    confirm_password = request.POST.get("confirm_password")
    if password != confirm_password:
        messages.error(request, "Passwords do not match")
        return redirect("/user")
    if User.objects.filter(Email=email).exists():
        messages.error(request, "Email Already Exists")
        return redirect("/user")
    encrypt_password = make_password(password)
    insertquery = User(Name=name,Email=email,Phone=phone,Password=encrypt_password)
    insertquery.save()
    messages.success(request, "Successfully fetched user data")
    return redirect("/login")

def login(request):
    return render(request, "login.html")

def welcome(request):
    if "log_id" not in request.session:
        messages.error(request, "Please login first")
        return redirect("/login")

    name = request.session["log_name"]

    return render(request, "welcome.html", {
        "name": name
    })


def fetchlogindata(request):
    useremail = request.POST.get("email")
    userpass = request.POST.get("password")

    try:
        userdata = User.objects.get(Email=useremail)
        if check_password(userpass, userdata.Password):
            print(userdata)
            request.session["log_id"] = userdata.id
            request.session["log_name"] = userdata.Name
            request.session["log_email"] = userdata.Email
            print("Session Name", request.session["log_name"])
        else:
            userdata = None
    except:
        print("No Such User")
        userdata = None

    if userdata is not None:
        messages.success(request, "Successfully logged in")
        return redirect("/welcome")
    else:
        print("Login Failed")
        messages.error(request, "Invalid User Name or Password")
        return redirect("/login")

def logout(request):
    try:
        del request.session["log_id"]
        del request.session["log_name"]
        del request.session["log_email"]
    except:
        pass
    messages.success(request, "You Have Been Logged Out Successfully.")
    return redirect("/user")

def templates(request):
    if "log_id" not in request.session:
        messages.error(request, "Please login first")
        return redirect("/login")

    return render(request, "templates.html")

def select_template(request, id):

    request.session["selected_template"] = id

    print(request.session.get("selected_template"))

    return redirect("/resume")

