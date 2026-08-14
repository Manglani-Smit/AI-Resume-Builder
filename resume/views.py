from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.utils import timezone
from django.http import HttpResponse
from .models import Resume, User
from django.template.loader import get_template
from django.conf import settings
from django.contrib.auth.hashers import make_password, check_password
from django.contrib.auth import logout as auth_logout  # Added for Google Logout
from openai import OpenAI
import json

# Windows-friendly PDF Engine
from xhtml2pdf import pisa

# OpenRouter AI Client Configuration
client = OpenAI(
    api_key=settings.OPENROUTER_API_KEY,
    base_url="https://openrouter.ai/api/v1"
)


# ==========================================
# HELPER FUNCTION: Bridging Google Auth & Custom Auth
# ==========================================
def get_current_user(request):
    """
    Check karta hai ki user Google se aaya hai ya Manual Login se.
    Agar Google se aaya hai, toh usko hamare custom User table mein automatically save kar deta hai.
    """
    # 1. Check if user is logged in via Google (Django Allauth)
    if request.user.is_authenticated:
        email = request.user.email
        name = request.user.first_name or request.user.username

        # Google user ko apne custom User table ke sath link/create karo
        custom_user, created = User.objects.get_or_create(
            Email=email,
            defaults={
                'Name': name,
                'Password': 'google_auth_user'  # Dummy password for Google users
            }
        )
        return custom_user

    # 2. Check if user is logged in via Manual Session (Old way)
    if "log_id" in request.session:
        try:
            return User.objects.get(id=request.session["log_id"])
        except User.DoesNotExist:
            return None

    # 3. User is not logged in at all
    return None


# ==========================================


def home(request):
    return render(request, "index.html")


def resume(request):
    current_user = get_current_user(request)
    if not current_user:
        messages.error(request, "Please login first")
        return redirect("/login")

    current_user.reset_daily_limit_if_needed()

    return render(request, "resume.html", {
        "generations_left": current_user.daily_generations_left,
        "is_premium": current_user.is_premium
    })


def fetchresumedata(request):
    current_user = get_current_user(request)
    if not current_user:
        messages.error(request, "Please login first")
        return redirect("/login")

    # 1. Enforce Daily Generation Limit
    if not current_user.can_generate():
        messages.error(request,
                       "Aapki aaj ki 3 resume ki limit khatam ho chuki hai! Unlimited generation ke liye Premium lein.")
        return redirect("/resume")

    if request.method == "POST":
        name = request.POST.get("name")
        email = request.POST.get("email")
        phone = request.POST.get("phone")
        skills = request.POST.get("skills")
        education = request.POST.get("education")

        # 2. Dynamic Multiple Projects Processing
        project_titles = request.POST.getlist("project_title[]")
        project_descs = request.POST.getlist("project_description[]")

        user_projects = []
        for title, desc in zip(project_titles, project_descs):
            if title.strip():
                user_projects.append({"title": title, "description": desc})

        # 3. OpenRouter AI Prompt Strategy
        prompt = f"""
You are an expert ATS Resume Writer.

Candidate Details:
Name: {name}
Education: {education}
Skills: {skills}
Raw Projects Input: {json.dumps(user_projects)}

Task:
1. Generate an impactful summary and objective.
2. For each project provided, rewrite and polish the raw description into ATS-friendly bullet points with action verbs.

Return ONLY valid JSON with no markdown syntax.
Use exact schema:
{{
    "summary": "...",
    "objective": "...",
    "projects": [
        {{
            "title": "Project Name",
            "description": "Enhanced bullet points describing technical impact..."
        }}
    ],
    "experience": "...",
    "certifications": "...",
    "achievements": "..."
}}
"""
        try:
            response = client.chat.completions.create(
                model="openrouter/free",
                messages=[{"role": "user", "content": prompt}]
            )

            ai_response = response.choices[0].message.content.strip()

            # Clean potential JSON markdown blocks
            if ai_response.startswith("```json"):
                ai_response = ai_response.replace("```json", "").replace("```", "").strip()

            resume_data = json.loads(ai_response)

        except Exception as e:
            print("AI Processing Error:", e)
            messages.error(request, "AI service error. Please try again.")
            return redirect("/resume")

        selected_template = request.session.get("selected_template", 1)

        # 4. Save Resume Linked strictly to Bridged Logged-in User
        insertquery = Resume.objects.create(
            user=current_user,
            name=name,
            email=email,
            phone=phone,
            skills=skills,
            education=education,
            summary=resume_data.get("summary", ""),
            objective=resume_data.get("objective", ""),
            projects=resume_data.get("projects", user_projects),
            experience=resume_data.get("experience", ""),
            certifications=resume_data.get("certifications", ""),
            achievements=resume_data.get("achievements", ""),
            template_id=selected_template
        )

        # Deduct 1 Daily Generation
        current_user.deduct_generation()

        messages.success(request, f"Resume created! Daily generations left: {current_user.daily_generations_left}")
        return redirect(f"/resumedetail/{insertquery.id}")


def resumelist(request):
    current_user = get_current_user(request)
    if not current_user:
        messages.error(request, "Please login first")
        return redirect("/login")

    # PRIVACY ISOLATION: Fetch ONLY logged-in user's resumes
    resumes = Resume.objects.filter(user=current_user).order_by('-created_at')

    return render(request, "resumelist.html", {"resumes": resumes})


def resumedetail(request, id):
    current_user = get_current_user(request)
    if not current_user:
        messages.error(request, "Please login first")
        return redirect("/login")

    # SECURITY CHECK: Verify ownership before rendering
    resume = get_object_or_404(Resume, id=id, user=current_user)
    skills = [skill.strip() for skill in resume.skills.split(",")]

    template_map = {
        1: "resume_modern.html",
        2: "resume_professional.html",
        3: "resume_minimal.html",
        4: "resume_creative.html"
    }
    template = template_map.get(resume.template_id, "resume_executive.html")

    return render(request, template, {"resume": resume, "skills": skills})


def editresume(request, id):
    current_user = get_current_user(request)
    if not current_user:
        messages.error(request, "Please login first")
        return redirect("/login")

    resume = get_object_or_404(Resume, id=id, user=current_user)
    return render(request, "editresume.html", {"resume": resume})


def fetcheditresumedata(request, id):
    current_user = get_current_user(request)
    if not current_user:
        messages.error(request, "Please login first")
        return redirect("/login")

    resume = get_object_or_404(Resume, id=id, user=current_user)

    resume.name = request.POST.get("name")
    resume.email = request.POST.get("email")
    resume.phone = request.POST.get("phone")
    resume.skills = request.POST.get("skills")
    resume.education = request.POST.get("education")
    resume.save()

    messages.success(request, "Resume Updated Successfully")
    return redirect("/resumelist")


def deleteresume(request, id):
    current_user = get_current_user(request)
    if not current_user:
        messages.error(request, "Please login first")
        return redirect("/login")

    resume = get_object_or_404(Resume, id=id, user=current_user)
    resume.delete()

    messages.success(request, "Resume Deleted Successfully")
    return redirect("/resumelist")


def resume_pdf(request, id):
    current_user = get_current_user(request)
    if not current_user:
        messages.error(request, "Please login first")
        return redirect("/login")

    resume = get_object_or_404(Resume, id=id, user=current_user)
    skills = [skill.strip() for skill in resume.skills.split(",")]

    template_map = {
        1: "resume_modern.html",
        2: "resume_professional.html",
        3: "resume_minimal.html",
        4: "resume_creative.html"
    }
    template_name = template_map.get(resume.template_id, "resume_executive.html")

    template = get_template(template_name)
    html_content = template.render({"resume": resume, "skills": skills, "pdf": True})

    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="{resume.name}_Resume.pdf"'

    # Render PDF safely using xhtml2pdf
    pisa_status = pisa.CreatePDF(html_content, dest=response)

    if pisa_status.err:
        return HttpResponse('PDF Generation Error', status=500)

    return response


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
    User.objects.create(Name=name, Email=email, Phone=phone, Password=encrypt_password)
    messages.success(request, "Registration successful. Please login.")
    return redirect("/login")


def login(request):
    return render(request, "login.html")


def welcome(request):
    current_user = get_current_user(request)

    if not current_user:
        messages.error(request, "Please login first")
        return redirect("/login")

    # Fetch ONLY resumes for the bridged user
    user_resumes = Resume.objects.filter(user=current_user).order_by('-created_at')

    return render(request, "welcome.html", {
        "name": current_user.Name,
        "resumes": user_resumes
    })


def fetchlogindata(request):
    useremail = request.POST.get("email")
    userpass = request.POST.get("password")

    try:
        userdata = User.objects.get(Email=useremail)
        if check_password(userpass, userdata.Password):
            request.session["log_id"] = userdata.id
            request.session["log_name"] = userdata.Name
            request.session["log_email"] = userdata.Email
            messages.success(request, "Successfully logged in")
            return redirect("/welcome")
        else:
            messages.error(request, "Invalid Password")
    except User.DoesNotExist:
        messages.error(request, "User does not exist")

    return redirect("/login")


def logout(request):
    # Dono sessions (Google & Manual) ko clear karna zaroori hai
    auth_logout(request)
    request.session.flush()

    messages.success(request, "Logged out successfully.")
    return redirect("/login")


def templates(request):
    current_user = get_current_user(request)
    if not current_user:
        messages.error(request, "Please login first")
        return redirect("/login")
    return render(request, "templates.html")


def select_template(request, id):
    request.session["selected_template"] = id
    return redirect("/resume")