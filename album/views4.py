import io, zipfile,qrcode
import os

import cv2
import numpy as np
from django.conf import settings
from django.core.mail import send_mail
from django.http import HttpResponse, FileResponse
from sqlparse.filters import output

from .forms import AlbumRequestForm, RegisterForm, LoginForm
from .models import Photo, UserProfile, Album, Video
from django.contrib.auth.decorators import login_required
from django.core.files.base import ContentFile
from django.urls import reverse
from django.contrib.auth import authenticate, login, logout
from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect, render
from django.contrib.admin.views.decorators import staff_member_required


def album_list(request):
    albums = Album.objects.all().order_by('-created_at')
    return render(request, 'create_albums2.html', {'albums': albums})



@staff_member_required
def approve_albums(request):
    albums = Album.objects.all().order_by('-created_at')

    if request.method == 'POST':
        album_id = request.POST.get('album_id')
        action = request.POST.get('action')

        album = get_object_or_404(Album, id=album_id)

        if action == 'approve':
            album.status = 'APPROVED'
            album.save()

        elif action == 'reject':
            album.status = 'REJECTED'
            album.save()

        elif action == 'delete':
            album.delete()

        return redirect('approve-albums')

    return render(request, 'album_approve.html', {'albums': albums})


# @login_required
# def request_album(request):
#     if request.method == 'POST':
#         form = AlbumRequestForm(request.POST)
#         if form.is_valid():
#             album = form.save(commit=False)
#             album.created_by = request.user
#             album.status = 'PENDING'
#             album.save()
#             return redirect('album-request-success')
#     else:
#         form = AlbumRequestForm()
#
#     return render(request, 'request_album.html', {'form': form})

def request_album(request):
    if request.method == 'POST':
        form = AlbumRequestForm(request.POST)
        if form.is_valid():
            album = form.save(commit=False)
            album.created_by = request.user
            album.status = 'PENDING'
            album.save()

            # 🔹 Build album URL
            album_url = request.build_absolute_uri(
                reverse('album-detail', args=[album.id])
            )

            # 🔹 Generate QR
            qr_img = qrcode.make(album_url)
            buffer = io.BytesIO()
            qr_img.save(buffer, format='PNG')
            buffer.seek(0)

            # 🔹 Save QR to model field
            album.qr_code.save(
                f'album_{album.id}_qr.png',
                ContentFile(buffer.read()),
                save=True
            )

            return redirect('album-request-success')
    else:
        form = AlbumRequestForm()

    return render(request, 'request_album.html', {'form': form})

# from django.shortcuts import get_object_or_404, redirect
# from django.contrib import messages
# from django.contrib.auth.decorators import login_required
# from .models import Video
#
#
# @login_required
# def delete_video(request, video_id):
#
#     video = get_object_or_404(Video, id=video_id)
#
#     # Admin check
#     if not request.user.is_staff:
#         messages.error(request, "You are not allowed to delete videos.")
#         return redirect('album-detail', video.album.id)
#
#     if request.method == "POST":
#         video.delete()
#         messages.success(request, "Video deleted successfully.")
#
#     return redirect('album-detail', video.album.id)

@staff_member_required
def edit_album(request, album_id):
    album = get_object_or_404(Album, id=album_id)

    if request.method == 'POST':
        album.title = request.POST.get('title')
        album.save()
        return redirect('approve-albums')

    return render(request, 'edit_album.html', {'album': album})

#@login_required
def album_detail(request, album_id):
    album = get_object_or_404(Album, id=album_id)
    photos = album.photos.filter(is_active=True)
    #videos = album.videos.filter(is_active=True)
    return render(request, 'album_details2.html', {
        'album': album,
        'photos': photos,
        #'videos': videos
    })

# @login_required
# def upload_photo(request, album_id):
#
#     try:
#         album = Album.objects.get(id=album_id)
#     except Album.DoesNotExist:
#         messages.error(request, "Album not found.")
#         return redirect('album-list')
#
#     # 🔒 Owner check
#     if album.created_by != request.user:
#         messages.error(request, "You are not allowed to upload photos to this album.")
#         return render(request, 'album_details2.html', {'album': album})
#
#     # 🔒 Approval check
#     if album.status != 'APPROVED':
#         messages.warning(request, "Album is not approved yet.")
#         return render(request, 'album_details2.html', {'album': album})
#
#     if request.method == 'POST':
#         image = request.FILES.get('image')
#         if image:
#             Photo.objects.create(
#                 album=album,
#                 image=image,
#                 uploaded_by=request.user
#             )
#             messages.success(request, "Photo uploaded successfully!")
#             return redirect('album-detail', album.id)
#
#
#     return render(request, 'album_details2.html', {'album': album})
#
from django.shortcuts import get_object_or_404, redirect, render
from django.contrib import messages
from django.contrib.auth.decorators import login_required

@login_required
def upload_media(request, album_id):

    album = get_object_or_404(Album, id=album_id)

    # 🔒 Owner check
    if album.created_by != request.user:
        messages.error(request, "You are not allowed to upload media to this album.")
        return render(request, 'album_details2.html', {'album': album})

    # 🔒 Approval check
    if album.status != 'APPROVED':
        messages.warning(request, "Album is not approved yet.")
        return render(request, 'album_details2.html', {'album': album})

    if request.method == 'POST':
        image = request.FILES.get('image')
        video = request.FILES.get('video')

        # 📷 IMAGE VALIDATION
        if image:
            if not image.content_type.startswith('image'):
                messages.error(request, "Invalid image format!")
            else:
                Photo.objects.create(
                    album=album,
                    image=image,
                    uploaded_by=request.user
                )
                messages.success(request, "Photo uploaded successfully!")

        # 🎬 VIDEO VALIDATION
        if video:
            if not video.content_type.startswith('video'):
                messages.error(request, "Invalid video format!")
            else:
                Video.objects.create(
                    album=album,
                    video=video,
                    uploaded_by=request.user
                )
                messages.success(request, "Video uploaded successfully!")

        # ❗ Agar dono empty ho
        if not image and not video:
            messages.warning(request, "Please select a file to upload.")

        return redirect('album-detail', album.id)

    return render(request, 'album_details2.html', {'album': album})
#
# from django.contrib.auth.decorators import login_required
# from django.shortcuts import get_object_or_404, redirect, render
# from django.contrib import messages
#
# @login_required
# def upload_video(request, album_id):
#
#     album = get_object_or_404(Album, id=album_id)
#
#     # 🔒 Owner check
#     if album.created_by != request.user:
#         messages.error(request, "You are not allowed to upload videos to this album.")
#         return render(request, 'album_details2.html', {'album': album})
#
#     # 🔒 Approval check
#     if album.status != 'APPROVED':
#         messages.warning(request, "Album is not approved yet.")
#         return render(request, 'album_details2.html', {'album': album})
#
#     if request.method == 'POST':
#         video_file = request.FILES.get('video')
#
#         if video_file:
#             Video.objects.create(
#                 album=album,
#                 video=video_file,
#                 uploaded_by=request.user
#             )
#
#             messages.success(request, "Video uploaded successfully!")
#             return redirect('album-detail', album.id)
#
#         else:
#             messages.error(request, "Please select a video.")
#
#     return render(request, 'album_details2.html', {'album': album})


# from django.contrib.auth.decorators import login_required
# from django.shortcuts import get_object_or_404, redirect, render
# from django.contrib import messages
#
#
# @login_required
# def upload_media(request, album_id):
#
#     album = get_object_or_404(Album, id=album_id)
#     #🔒 Owner check
#     if album.created_by != request.user:
#         messages.error(request, "You are not allowed to upload videos to this album.")
#         return render(request, 'album_details2.html', {'album': album})
#
#     # 🔒 Approval check
#     if album.status != 'APPROVED':
#         messages.warning(request, "Album is not approved yet.")
#         return render(request, 'album_details2.html', {'album': album})
#     if request.method == "POST":
#
#         image = request.FILES.get('image')
#         video = request.FILES.get('video')
#
#         if image:
#             Photo.objects.create(
#                 album=album,
#                 image=image,
#                 uploaded_by=request.user
#             )
#             messages.success(request,"Photo uploaded successfully!")
#
#         elif video:
#             Video.objects.create(
#                 album=album,
#                 video=video,
#                 uploaded_by=request.user
#             )
#             messages.success(request,"Video uploaded successfully!")
#
#         else:
#             messages.error(request,"Please select photo or video.")
#
#         return redirect('album-detail', album.id)
#
#     #return redirect('album-detail', album.id)
#     return render(request, 'album_details2.html', {'album': album})

def download_photo(request, photo_id):
    photo = get_object_or_404(Photo, id=photo_id)
    return FileResponse(photo.image.open(), as_attachment=True)

def download_album(request, album_id):
    album = get_object_or_404(Album, id=album_id)
    buffer = io.BytesIO()
    zip_file = zipfile.ZipFile(buffer, 'w')

    for photo in album.photos.all():
        zip_file.write(photo.image.path, photo.image.name.split('/')[-1])

    zip_file.close()
    buffer.seek(0)

    response = HttpResponse(buffer, content_type='application/zip')
    response['Content-Disposition'] = f'attachment; filename="{album.title}.zip"'
    return response

def download_selected_photos(request):
    photo_ids = request.POST.getlist('photo_ids')
    buffer = io.BytesIO()
    zip_file = zipfile.ZipFile(buffer, 'w')


    for photo in Photo.objects.filter(id__in=photo_ids):
        zip_file.write(photo.image.path, photo.image.name.split('/')[-1])

    zip_file.close()
    buffer.seek(0)

    response = HttpResponse(buffer, content_type='application/zip')
    response['Content-Disposition'] = 'attachment; filename="selected_photos.zip"'
    return response

def animated_slideshow(request, album_id):
    album = get_object_or_404(
        Album,
        id=album_id,
        status='APPROVED'
    )

    photos = album.photos.filter(is_active=True)

    return render(request, 'animation.html', {
        'album': album,
        'photos': photos
    })



@login_required
def album_request_success(request):
    return render(request, 'album_request_success.html')



@staff_member_required
def delete_photo(request, photo_id):
    photo = get_object_or_404(Photo, id=photo_id)
    album_id = photo.album.id
    photo.delete()
    return redirect('album-detail', album_id=album_id)




# def register(request):
#     if request.method == 'POST':
#         form = RegisterForm(request.POST)
#         if form.is_valid():
#             user = form.save()
#             UserProfile.objects.create(user=user)  # role=PENDING
#             user = User.objects.create_user(...)
#             profile, created = UserProfile.objects.get_or_create(user=user)
#             return redirect('login')
#     else:
#         form = RegisterForm()
#
#     return render(request, 'register.html', {'form': form})

# def register(request):
#     if request.method == 'POST':
#         form = RegisterForm(request.POST)
#         if form.is_valid():
#             user = form.save()   # ✅ user sirf ek baar create
#
#             # ✅ profile safe way me create
#             UserProfile.objects.get_or_create(user=user)
#
#             return redirect('login')
#     else:
#         form = RegisterForm()
#
#     return render(request, 'register.html', {'form': form})


def register(request):
    if request.method == 'POST':
        form = RegisterForm(request.POST)
        if form.is_valid():

            # ✅ Create user (ONLY ONCE)
            user = form.save()

            # ✅ Create user profile safely
            UserProfile.objects.get_or_create(user=user)

            # ✅ Send welcome email (dynamic receiver)
            if user.email:   # safety check
                send_mail(
                    'Welcome to Our App',
                    'Your account has been created successfully.',
                    settings.EMAIL_HOST_USER,
                    [user.email],
                    fail_silently=False,
                )

            return redirect('login')
    else:
        form = RegisterForm()

    return render(request, 'register.html', {'form': form})



@staff_member_required
def approve_users(request):
    if request.method == 'POST':
        profile_id = request.POST.get('profile_id')
        role = request.POST.get('role')

        profile = UserProfile.objects.get(id=profile_id)
        profile.role = role
        profile.is_approved = True
        profile.save()

        # Staff / Admin flag
        if role in ['ADMIN', 'STAFF']:
            profile.user.is_staff = True
            profile.user.save()

    users = UserProfile.objects.filter(is_approved=False)
    return render(request, 'user_approval.html', {'users': users})




def user_login(request):
    form = LoginForm(request.POST or None)

    if request.method == 'POST' and form.is_valid():
        user = authenticate(
            request,
            username=form.cleaned_data['username'],
            password=form.cleaned_data['password']
        )

        if user:
            profile = user.userprofile

            if not profile.is_approved:
                messages.error(request, "Your account is not approved yet.")
                return redirect('login')

            login(request, user)

            album = Album.objects.filter(status='APPROVED').first()

            if album:
                return redirect('album-list')
            else:
                messages.error(request, "No approved album found")
                return redirect('album-list')

        messages.error(request, "Invalid username or password")

    return render(request, 'login.html', {'form': form})



@staff_member_required
def approved_users(request):
    users = UserProfile.objects.filter(is_approved=True).exclude(role='PENDING')
    return render(request, 'approved_users.html', {'users': users})




@staff_member_required
def user_detail(request, pk):
    profile = get_object_or_404(UserProfile, pk=pk)
    return render(request, 'user_details.html', {'profile': profile})

@staff_member_required
def user_detail(request, pk):
    profile = get_object_or_404(UserProfile, pk=pk)
    return render(request, 'user_details.html', {'profile': profile})

@staff_member_required
def user_update(request, pk):
    profile = get_object_or_404(UserProfile, pk=pk)
    role = request.POST.get('role')
    if role:
        profile.role = role
        profile.save()
    return redirect('approved-users')


@staff_member_required
def user_toggle(request, pk):
    profile = get_object_or_404(UserProfile, pk=pk)
    profile.is_approved = not profile.is_approved
    profile.save()
    return redirect('approved-users')


@staff_member_required
def user_delete(request, pk):
    profile = get_object_or_404(UserProfile, pk=pk)
    profile.user.delete()   # deletes user + profile
    return redirect('approved-users')




def notify_user(request, user_id):
    user = UserProfile.objects.get(id=user_id)

    send_mail(
        'Account Approved',
        'Your account is approved.',
        settings.EMAIL_HOST_USER,
        [user.email],
    )

# from django.shortcuts import render, get_object_or_404
# from .models import Album
#
# def ai_slideshow(request, album_id):
#     album = get_object_or_404(
#         Album,
#         id=album_id,
#         status='APPROVED'
#     )
#
#     photos = album.photos.filter(is_active=True)
#
#     return render(request, "ai_slideshow.html", {
#         "album": album,
#         "photos": photos
#     })
from django.shortcuts import render, get_object_or_404
from .models import Album

def ai_slideshow(request, album_id):
    album = get_object_or_404(
        Album,
        id=album_id,
        status="APPROVED"
    )

    photos = album.photos.filter(is_active=True)

    return render(request, "ai_slideshow1.html", {
        "album": album,
        "photos": photos
    })


# from .video_engine.slideshow_40_free import create_slideshow

# def generate_video(request, album_id):
#     album = Album.objects.get(id=album_id)
#
#     image_folder = os.path.join(
#         settings.MEDIA_ROOT,
#         "albums",
#         str(album.id)
#     )
#
#     output_video = os.path.join(
#         settings.MEDIA_ROOT,
#         "videos",
#         f"album_{album.id}.mp4"
#     )
#
#     os.makedirs(os.path.dirname(output_video), exist_ok=True)
#
#     create_slideshow(image_folder, output_video)
#
#     return render(request, "generate_video.html", {
#         "video_url": settings.MEDIA_URL + f"videos/album_{album.id}.mp4"})

from django.shortcuts import render, get_object_or_404
from .models import Album

def flip_album(request, album_id):
    album = get_object_or_404(Album, id=album_id)
    photos = album.photos.filter(is_active=True)

    return render(request, "flip_album.html", {
        "album": album,
        "photos": photos
    })






def album_view1(request, album_id):
    album = Album.objects.get(id=album_id)
    photos = Photo.objects.filter(album=album)

    # 🎵 MUSIC FOLDER PATH
    music_dir = os.path.join(settings.MEDIA_ROOT, "music")

    # 🎶 ALL MP3 FILES
    music_files = [
        f for f in os.listdir(music_dir)
        if f.endswith(".mp3")
    ]

    # 🧠 RANDOM PICK
    selected_music = random.choice(music_files) if music_files else None

    music_url = (
        settings.MEDIA_URL + "music/" + selected_music
        if selected_music else None
    )

    return render(request, "new_ky1.html", {
        "album": album,
        "photos": photos,
        "music_url": music_url
    })

import os
import random
from django.conf import settings
from django.shortcuts import render, get_object_or_404
from .models import Album, Photo


def album_slideshow_view(request, album_id):
    # 📀 ALBUM
    album = get_object_or_404(Album, id=album_id)

    # 📸 PHOTOS (ORDERED)
    photos = Photo.objects.filter(album=album).order_by('id')

    # 🎵 OPTIONAL MUSIC (AUTO PICK)
    music_dir = os.path.join(settings.MEDIA_ROOT, "music")
    music_url = None

    if os.path.exists(music_dir):
        music_files = [f for f in os.listdir(music_dir) if f.endswith(".mp3")]
        if music_files:
            selected_music = random.choice(music_files)
            music_url = settings.MEDIA_URL + "music/" + selected_music

    return render(request, "slide2.html", {
        "album": album,
        "photos": photos,
        "music_url": music_url,
    })


def flip_album1(request, album_id):
    album = get_object_or_404(Album, id=album_id)
    photos = album.photos.filter(is_active=True)

    return render(request, "s2/new_ky2.html", {
        "album": album,
        "photos": photos
    })

# def flip_album2(request, album_id):
#     album = get_object_or_404(Album, id=album_id)
#     photos = album.photos.filter(is_active=True)
#
#     return render(request, "ht.html", {
#         "album": album,
#         "photos": photos
#     })

def flip_album2(request, album_id):
    album = get_object_or_404(Album, id=album_id)
    photos = album.photos.filter(is_active=True)

    return render(request, "s2/flip_album2.html", {
        "album": album,
        "photos": photos
    })


import os
import subprocess
from django.conf import settings
from django.http import FileResponse
from django.shortcuts import get_object_or_404
from django.views.decorators.csrf import csrf_exempt
from .models import Album, Photo


# @csrf_exempt
# def generate_album_video(request, album_id):
#
#     album = get_object_or_404(Album, id=album_id)
#     photos = Photo.objects.filter(album=album).order_by('id')
#
#     song = request.FILES.get('song')
#     if not song:
#         return HttpResponse("Song missing", status=400)
#
#     # FOLDERS
#     base_dir = settings.MEDIA_ROOT
#     temp_dir = os.path.join(base_dir, 'temp', f'album_{album_id}')
#     os.makedirs(temp_dir, exist_ok=True)
#
#     song_path = os.path.join(temp_dir, song.name)
#     with open(song_path, 'wb+') as f:
#         for chunk in song.chunks():
#             f.write(chunk)
#
#     # IMAGE LIST FILE
#     list_file = os.path.join(temp_dir, 'images.txt')
#     with open(list_file, 'w') as f:
#         for p in photos:
#             f.write(f"file '{p.image.path}'\n")
#             f.write("duration 4\n")
#         f.write(f"file '{photos.last().image.path}'\n")
#
#     # OUTPUT
#     output_video = os.path.join(temp_dir, 'flipbook.mp4')
#
#     # FFMPEG COMMAND
#     cmd = [
#         'ffmpeg', '-y',
#         '-f', 'concat',
#         '-safe', '0',
#         '-i', list_file,
#         '-i', song_path,
#         '-vf', 'scale=1280:720,format=yuv420p',
#         '-shortest',
#         '-r', '30',
#         output_video
#     ]
#
#     subprocess.run(cmd, check=True)
#
#     return FileResponse(
#         open(output_video, 'rb'),
#         as_attachment=True,
#         filename=f"{album.title}_flipbook.mp4"
#     )

def album_flipbook(request, album_id):
    album = get_object_or_404(Album, id=album_id)
    photos = Photo.objects.filter(album=album).order_by('id')

    context = {
        'album': album,
        'photos': photos,
    }

    return render(request, 's2/new2.html', context)





import os, subprocess
from django.conf import settings
from django.shortcuts import render, get_object_or_404
from django.http import FileResponse
from django.utils import timezone
from .models import Album, Photo

import os
import random
from django.conf import settings

# def album_view(request, album_id):
#     album = Album.objects.get(id=album_id)
#     photos = Photo.objects.filter(album=album)
#
#     # 🎵 MUSIC FOLDER PATH
#     music_dir = os.path.join(settings.MEDIA_ROOT, "music")
#
#     # 🎶 ALL MP3 FILES
#     music_files = [
#         f for f in os.listdir(music_dir)
#         if f.endswith(".mp3")
#     ]
#
#     # 🧠 RANDOM PICK
#     selected_music = random.choice(music_files) if music_files else None
#
#     music_url = (
#         settings.MEDIA_URL + "music/" + selected_music
#         if selected_music else None
#     )
#
#     return render(request, "flip_album4.html", {
#         "album": album,
#         "photos": photos,
#         "music_url": music_url
#     })

import os
from django.conf import settings

# def album_view(request, album_id):
#     album = Album.objects.get(id=album_id)
#     photos = Photo.objects.filter(album=album)
#
#     # 🎵 MUSIC FOLDER PATH
#     music_dir = os.path.join(settings.MEDIA_ROOT, "music")
#
#     selected_music = None
#
#     if os.path.exists(music_dir):
#         mp3_files = [
#             f for f in os.listdir(music_dir)
#             if f.lower().endswith(".mp3")
#         ]
#
#         if mp3_files:
#             # 🆕 NEWEST MP3 (last modified)
#             mp3_files.sort(
#                 key=lambda x: os.path.getmtime(os.path.join(music_dir, x)),
#                 reverse=True
#             )
#             selected_music = mp3_files[0]
#
#     music_url = (
#         settings.MEDIA_URL + "music/" + selected_music
#         if selected_music else None
#     )
#
#     return render(request, "flip_album5.html", {
#         "album": album,
#         "photos": photos,
#         "music_url": music_url
#     })

import os
from django.conf import settings

# def album_view(request, album_id):
#     album = Album.objects.get(id=album_id)
#     photos = Photo.objects.filter(album=album)
#
#     music_dir = os.path.join(settings.MEDIA_ROOT, "music")
#     selected_music = None
#
#     if os.path.isdir(music_dir):
#         mp3_files = []
#
#         for f in os.listdir(music_dir):
#             if f.lower().endswith(".mp3"):
#                 full_path = os.path.join(music_dir, f)
#                 mp3_files.append((f, os.path.getctime(full_path)))
#
#         if mp3_files:
#             # 🆕 NEWEST CREATED FILE
#             mp3_files.sort(key=lambda x: x[1], reverse=True)
#             selected_music = mp3_files[0][0]
#
#     music_url = (
#         settings.MEDIA_URL + "music/" + selected_music
#         if selected_music else None
#     )
#
#     return render(request, "flip_album5.html", {
#         "album": album,
#         "photos": photos,
#         "music_url": music_url
#     })


def album_view(request, album_id):
    album = get_object_or_404(Album, id=album_id)
    photos = Photo.objects.filter(album=album)

    # 🎵 latest music
    music_dir = os.path.join(settings.MEDIA_ROOT, "music")
    selected_music = None

    if os.path.isdir(music_dir):
        mp3s = [
            (f, os.path.getctime(os.path.join(music_dir, f)))
            for f in os.listdir(music_dir)
            if f.lower().endswith(".mp3")
        ]
        if mp3s:
            mp3s.sort(key=lambda x: x[1], reverse=True)
            selected_music = mp3s[0][0]

    music_url = settings.MEDIA_URL + "music/" + selected_music if selected_music else None

    return render(request, "flip_album313.html", {
        "album": album,
        "photos": photos,
        "music_url": music_url,
        "now": timezone.now()
    })

def ai_view(request, album_id):
    album = get_object_or_404(Album, id=album_id)
    photos = Photo.objects.filter(album=album)

    # 🎵 latest music
    music_dir = os.path.join(settings.MEDIA_ROOT, "music")
    selected_music = None

    if os.path.isdir(music_dir):
        mp3s = [
            (f, os.path.getctime(os.path.join(music_dir, f)))
            for f in os.listdir(music_dir)
            if f.lower().endswith(".mp3")
        ]
        if mp3s:
            mp3s.sort(key=lambda x: x[1], reverse=True)
            selected_music = mp3s[0][0]

    music_url = settings.MEDIA_URL + "music/" + selected_music if selected_music else None

    return render(request, "ai_slideshow1.html", {
        "album": album,
        "photos": photos,
        "music_url": music_url,
        "now": timezone.now()
    })



# def generate_album_video(request, album_id):
#     album = get_object_or_404(Album, id=album_id)
#     photos = list(Photo.objects.filter(album=album))
#
#     work_dir = os.path.join(settings.MEDIA_ROOT, "video_frames", str(album.id))
#     os.makedirs(work_dir, exist_ok=True)
#
#     frames = []
#
#     # ▶ FORWARD
#     for i, p in enumerate(photos):
#         path = os.path.join(work_dir, f"f_{i:03}.jpg")
#         open(path, "wb").write(open(p.image.path, "rb").read())
#         frames.append(path)
#
#     # ◀ REVERSE
#     for i, p in enumerate(reversed(photos)):
#         path = os.path.join(work_dir, f"r_{i:03}.jpg")
#         open(path, "wb").write(open(p.image.path, "rb").read())
#         frames.append(path)
#
#     list_file = os.path.join(work_dir, "list.txt")
#     with open(list_file, "w") as f:
#         for img in frames:
#             f.write(f"file '{img}'\n")
#             f.write("duration 4\n")   # ⏱️ 4 sec per slide
#
#     video_path = os.path.join(settings.MEDIA_ROOT, f"album_{album.id}.mp4")
#
#     music_dir = os.path.join(settings.MEDIA_ROOT, "music")
#     music = None
#     if os.path.isdir(music_dir):
#         mp3s = sorted(
#             os.listdir(music_dir),
#             key=lambda x: os.path.getctime(os.path.join(music_dir, x)),
#             reverse=True
#         )
#         if mp3s:
#             music = os.path.join(music_dir, mp3s[0])
#
#     cmd = [
#         "ffmpeg", "-y",
#         "-f", "concat", "-safe", "0",
#         "-i", list_file,
#         "-i", music if music else "anullsrc",
#         "-vf", "scale=1280:720,format=yuv420p",
#         "-c:v", "libx264",
#         "-c:a", "aac",
#         "-shortest",
#         video_path
#     ]
#
#     subprocess.run(cmd)
#
#     return FileResponse(open(video_path, "rb"), as_attachment=True)


# import os, subprocess
# from django.conf import settings
# from django.shortcuts import get_object_or_404
# from django.http import FileResponse
# from .models import Album, Photo
#
#
# def generate_album_video(request, album_id):
#     album = get_object_or_404(Album, id=album_id)
#     photos = list(Photo.objects.filter(album=album))
#
#     work_dir = os.path.join(settings.MEDIA_ROOT, "video_frames", str(album.id))
#     os.makedirs(work_dir, exist_ok=True)
#
#     frames = []
#
#     # ▶ FORWARD
#     for i, p in enumerate(photos):
#         path = os.path.join(work_dir, f"f_{i:03}.jpg")
#         with open(p.image.path, "rb") as src, open(path, "wb") as dst:
#             dst.write(src.read())
#         frames.append(path)
#
#     # ◀ REVERSE
#     for i, p in enumerate(reversed(photos)):
#         path = os.path.join(work_dir, f"r_{i:03}.jpg")
#         with open(p.image.path, "rb") as src, open(path, "wb") as dst:
#             dst.write(src.read())
#         frames.append(path)
#
#     # 🔑 concat list (VERY IMPORTANT)
#     list_file = os.path.join(work_dir, "list.txt")
#     with open(list_file, "w") as f:
#         for img in frames:
#             f.write(f"file '{img}'\n")
#             f.write("duration 4\n")
#         # 🔥 last frame repeat (MANDATORY)
#         f.write(f"file '{frames[-1]}'\n")
#
#     video_path = os.path.join(settings.MEDIA_ROOT, f"album_{album.id}.mp4")
#
#     # 🎵 latest music
#     music = None
#     music_dir = os.path.join(settings.MEDIA_ROOT, "music")
#     if os.path.isdir(music_dir):
#         mp3s = sorted(
#             [f for f in os.listdir(music_dir) if f.lower().endswith(".mp3")],
#             key=lambda x: os.path.getctime(os.path.join(music_dir, x)),
#             reverse=True
#         )
#         if mp3s:
#             music = os.path.join(music_dir, mp3s[0])
#
#     # 🔥 FFmpeg command (SAFE + STABLE)
#     cmd = [
#         "ffmpeg", "-y",
#         "-f", "concat", "-safe", "0",
#         "-i", list_file,
#         "-i", music if music else "anullsrc",
#         "-vf", "scale=1280:720,format=yuv420p",
#         "-c:v", "libx264",
#         "-pix_fmt", "yuv420p",
#         "-c:a", "aac",
#         "-shortest",
#         video_path
#     ]
#
#     subprocess.run(cmd, capture_output=True, text=True)
#
#     return FileResponse(open(video_path, "rb"), as_attachment=True)


import os, subprocess
from django.conf import settings
from django.shortcuts import get_object_or_404
from django.http import FileResponse
from .models import Album, Photo


def generate_album_video(request, album_id):
    album = get_object_or_404(Album, id=album_id)
    photos = list(Photo.objects.filter(album=album))

    work_dir = os.path.join(settings.MEDIA_ROOT, "video_frames", str(album.id))
    os.makedirs(work_dir, exist_ok=True)

    frames = []

    for i, p in enumerate(photos):
        path = os.path.join(work_dir, f"f_{i:03}.jpg")
        with open(p.image.path, "rb") as src, open(path, "wb") as dst:
            dst.write(src.read())
        frames.append(path)

    for i, p in enumerate(reversed(photos)):
        path = os.path.join(work_dir, f"r_{i:03}.jpg")
        with open(p.image.path, "rb") as src, open(path, "wb") as dst:
            dst.write(src.read())
        frames.append(path)

    list_file = os.path.join(work_dir, "list.txt")
    with open(list_file, "w") as f:
        for img in frames:
            f.write(f"file '{img}'\n")
            f.write("duration 4\n")
        f.write(f"file '{frames[-1]}'\n")

    video_path = os.path.join(settings.MEDIA_ROOT, f"album_{album.id}.mp4")

    # latest music
    music = None
    music_dir = os.path.join(settings.MEDIA_ROOT, "music")
    if os.path.isdir(music_dir):
        mp3s = sorted(
            [f for f in os.listdir(music_dir) if f.endswith(".mp3")],
            key=lambda x: os.path.getctime(os.path.join(music_dir, x)),
            reverse=True
        )
        if mp3s:
            music = os.path.join(music_dir, mp3s[0])

    cmd = [
        "ffmpeg","-y",
        "-f","concat","-safe","0",
        "-i",list_file,
        "-i", music if music else "anullsrc",
        "-vf","scale=1280:720,format=yuv420p",
        "-c:v","libx264",
        "-pix_fmt","yuv420p",
        "-c:a","aac",
        "-shortest",
        video_path
    ]

    #subprocess.run(cmd)
    result = subprocess.run(cmd, capture_output=True, text=True)
    print("STDOUT:", result.stdout)
    print("STDERR:", result.stderr)

    # response = FileResponse(open(video_path,"rb"), content_type="video/mp4")
    # response["Content-Disposition"] = f'attachment; filename="album_{album.id}.mp4"'
    # return response
    response = FileResponse(open(output, "rb"), content_type="video/mp4")
    response["Content-Disposition"] = f'attachment; filename="album_{album.id}.mp4"'
    return response


# import os, subprocess
# from django.conf import settings
# from django.shortcuts import get_object_or_404
# from django.http import FileResponse
# from .models import Album, Photo
#
#
# def generate_ultra_cinematic(request, album_id):
#
#     album = get_object_or_404(Album, id=album_id)
#     photos = list(Photo.objects.filter(album=album))
#
#     if not photos:
#         return FileResponse("No photos found")
#
#     work_dir = os.path.join(settings.MEDIA_ROOT, "video_frames", str(album.id))
#     os.makedirs(work_dir, exist_ok=True)
#
#     frames = []
#     for i, p in enumerate(photos):
#         path = os.path.join(work_dir, f"img_{i:03}.jpg")
#         with open(p.image.path,"rb") as src, open(path,"wb") as dst:
#             dst.write(src.read())
#         frames.append(path)
#
#     # ================= MUSIC =================
#     music_dir = os.path.join(settings.MEDIA_ROOT,"music")
#     mp3s = sorted(
#         [f for f in os.listdir(music_dir) if f.endswith(".mp3")],
#         key=lambda x: os.path.getctime(os.path.join(music_dir,x)),
#         reverse=True
#     )
#     music = os.path.join(music_dir, mp3s[0]) if mp3s else None
#
#     # ================= FILES =================
#     bg = os.path.join(settings.MEDIA_ROOT,"background","bg.mp4")
#     light = os.path.join(settings.MEDIA_ROOT,"overlays","light_leak.mp4")
#     grain = os.path.join(settings.MEDIA_ROOT,"overlays","grain.mp4")
#
#     output = os.path.join(settings.MEDIA_ROOT,f"ultra_album_{album.id}.mp4")
#
#     # ================= INPUTS =================
#     inputs = []
#     for img in frames:
#         inputs += ["-loop","1","-t","4","-i",img]
#
#     inputs += ["-i",bg,"-i",light,"-i",grain]
#
#     if music:
#         inputs += ["-i",music]
#
#     # ================= FILTERS =================
#     filters = []
#
#     # cinematic zoom + fade
#     for i in range(len(frames)):
#         filters.append(
#             f"[{i}:v]"
#             "scale=1400:-1,"
#             "zoompan=z='min(zoom+0.0007,1.3)':d=125:s=1280x720,"
#             "eq=contrast=1.1:brightness=0.03:saturation=1.2,"
#             "fade=t=in:st=0:d=1,"
#             "fade=t=out:st=3:d=1"
#             f"[v{i}]"
#         )
#
#     # smooth crossfade chain
#     current="[v0]"
#     for i in range(1,len(frames)):
#         filters.append(
#             f"{current}[v{i}]"
#             f"xfade=transition=fade:duration=1:offset=3"
#             f"[v{i}out]"
#         )
#         current=f"[v{i}out]"
#
#     slideshow=current
#
#     # background resize
#     bg_index=len(frames)
#     light_index=len(frames)+1
#     grain_index=len(frames)+2
#
#     filters.append(f"[{bg_index}:v]scale=1280:720[bg]")
#     filters.append(f"[{light_index}:v]scale=1280:720,format=rgba,colorchannelmixer=aa=0.25[light]")
#     filters.append(f"[{grain_index}:v]scale=1280:720,format=rgba,colorchannelmixer=aa=0.15[grain]")
#
#     # overlay stack
#     filters.append(f"[bg]{slideshow}overlay=(W-w)/2:(H-h)/2[base]")
#     filters.append(f"[base][light]overlay=0:0[lighted]")
#     filters.append(f"[lighted][grain]overlay=0:0")
#
#     filter_complex=";".join(filters)
#
#     # ================= COMMAND =================
#     cmd=[
#         "ffmpeg","-y",
#         *inputs,
#         "-filter_complex",filter_complex,
#         "-map","[v]"
#     ]
#
#     if music:
#         cmd+=["-map",f"{len(frames)+3}:a"]
#
#     cmd+=[
#         "-c:v","libx264",
#         "-preset","slow",
#         "-crf","18",
#         "-pix_fmt","yuv420p",
#         "-c:a","aac",
#         "-shortest",
#         output
#     ]
#
#     subprocess.run(cmd)
#
#     return FileResponse(open(output,"rb"),as_attachment=True)


# import os, subprocess
# from django.conf import settings
# from django.shortcuts import get_object_or_404
# from django.http import FileResponse, HttpResponse
# from .models import Album, Photo
#
#
# def generate_ultra_cinematic(request, album_id):
#
#     album = get_object_or_404(Album, id=album_id)
#     photos = list(Photo.objects.filter(album=album))
#
#     if not photos:
#         return HttpResponse("No photos found")
#
#     work_dir = os.path.join(settings.MEDIA_ROOT, "video_frames", str(album.id))
#     # os.makedirs(work_dir, exist_ok=True)
#     os.makedirs(settings.MEDIA_ROOT, exist_ok=True)
#
#     frames = []
#     for i, p in enumerate(photos):
#         path = os.path.join(work_dir, f"img_{i:03}.jpg")
#         with open(p.image.path, "rb") as src, open(path, "wb") as dst:
#             dst.write(src.read())
#         frames.append(path)
#
#     # 🎵 MUSIC (latest)
#     music_dir = os.path.join(settings.MEDIA_ROOT, "music")
#     music = None
#     if os.path.isdir(music_dir):
#         mp3s = sorted(
#             [f for f in os.listdir(music_dir) if f.endswith(".mp3")],
#             key=lambda x: os.path.getctime(os.path.join(music_dir, x)),
#             reverse=True
#         )
#         if mp3s:
#             music = os.path.join(music_dir, mp3s[0])
#
#     # 🎬 assets
#     bg = os.path.join(settings.MEDIA_ROOT, "background", "bg.mp4")
#     light = os.path.join(settings.MEDIA_ROOT, "background", "light.mp4")
#     grain = os.path.join(settings.MEDIA_ROOT, "background", "grain.mp4")
#
#     use_bg = os.path.exists(bg)
#     use_light = os.path.exists(light)
#     use_grain = os.path.exists(grain)
#
#     # output = os.path.join(settings.MEDIA_ROOT, f"ultra_album_{album.id}.mp4")
#     output = os.path.join(
#         settings.MEDIA_ROOT,
#         f"ultra_album_{album.id}.mp4"
#     )
#     # ================= INPUTS =================
#     inputs = []
#     for img in frames:
#         inputs += ["-loop", "1", "-t", "4", "-i", img]
#
#     # inputs += ["-i", bg, "-i", light, "-i", grain]
#     #inputs += ["-stream_loop", "-1", "-i", bg]
#     inputs += ["-stream_loop", "-1", "-i", bg]
#
#     if use_light:
#         inputs += ["-stream_loop", "-1", "-i", light]
#
#     if use_grain:
#         inputs += ["-stream_loop", "-1", "-i", grain]
#
#     if music:
#         inputs += ["-i", music]
#     # if music:
#     #     audio_index = len(inputs) // 2  # current input number
#     #     inputs += ["-i", music]
#
#     # ================= FILTERS =================
#     filters = []
#
#     for i in range(len(frames)):
#         filters.append(
#             f"[{i}:v]"
#             "scale=1400:-1,"
#             "zoompan=z='min(zoom+0.0007,1.3)':d=125:s=1280x720,"
#             "fade=t=in:st=0:d=1,"
#             "fade=t=out:st=3:d=1"
#             f"[v{i}]"
#         )
#
#     # current = "[v0]"
#     # for i in range(1, len(frames)):
#     #     filters.append(
#     #         f"{current}[v{i}]"
#     #         f"xfade=transition=fade:duration=1:offset=3"
#     #         f"[v{i}out]"
#     #     )
#     #     current = f"[v{i}out]"
#     current = "[v0]"
#     offset = 3  # first transition
#
#     for i in range(1, len(frames)):
#         filters.append(
#             f"{current}[v{i}]"
#             f"xfade=transition=fade:duration=1:offset={offset}"
#             f"[v{i}out]"
#         )
#         current = f"[v{i}out]"
#         offset += 3  # next transition time
#
#     slideshow = current
#     #
#     # bg_i = len(frames)
#     # light_i = len(frames) + 1
#     # grain_i = len(frames) + 2
#     bg_i = len(frames)
#     next_index = bg_i + 1
#
#     if use_light:
#         light_i = next_index
#         next_index += 1
#
#     if use_grain:
#         grain_i = next_index
#
#     # background resize
#     filters.append(f"[{bg_i}:v]scale=1280:720[bg]")
#
#     if use_light:
#         filters.append(
#             f"[{light_i}:v]scale=1280:720,format=rgba,colorchannelmixer=aa=0.25[light]"
#         )
#
#     if use_grain:
#         filters.append(
#             f"[{grain_i}:v]scale=1280:720,format=rgba,colorchannelmixer=aa=0.15[grain]"
#         )
#
#     # base overlay
#     filters.append(f"[bg]{slideshow}overlay=(W-w)/2:(H-h)/2[base]")
#
#     current = "[base]"
#
#     if use_light:
#         filters.append(f"{current}[light]overlay=0:0[tmp1]")
#         current = "[tmp1]"
#
#     if use_grain:
#         filters.append(f"{current}[grain]overlay=0:0[v]")
#     else:
#         filters.append(f"{current}null[v]")
#
#     # filters.append(f"[{bg_i}:v]scale=1280:720[bg]")
#     # filters.append(f"[{light_i}:v]scale=1280:720,format=rgba,colorchannelmixer=aa=0.25[light]")
#     # filters.append(f"[{grain_i}:v]scale=1280:720,format=rgba,colorchannelmixer=aa=0.15[grain]")
#     #
#     # # filters.append(f"[bg]{slideshow}overlay=(W-w)/2:(H-h)/2[base]")
#     # # filters.append(f"[base][light]overlay=0:0[lighted]")
#     # filters.append(f"[bg]{slideshow}overlay=(W-w)/2:(H-h)/2[base]")
#     # filters.append(f"[base][light]overlay=0:0[lighted]")
#     # filters.append(f"[lighted][grain]overlay=0:0[v]")
#
#     # 🔥 FINAL VIDEO LABEL MUST BE [v]
#     #filters.append(f"[lighted][grain]overlay=0:0[v]")
#     # filters.append(f"[lighted][grain]overlay=0:0[v]")
#
#     filter_complex = ";".join(filters)
#
#     print("BG exists:", os.path.exists(bg))
#     print("Light exists:", os.path.exists(light))
#     print("Grain exists:", os.path.exists(grain))
#     print("Music exists:", os.path.exists(music) if music else None)
#
#     audio_index = None
#
#
#
#     # ================= COMMAND =================
#     cmd = [
#         "ffmpeg", "-y",
#         *inputs,
#         "-filter_complex", filter_complex,
#         "-map", "[v]"
#     ]
#
#     # if music:
#     #     cmd += ["-map", f"{len(frames)+3}:a"]
#     # cmd += ["-map", "[v]"]
#
#     # if audio_index is not None:
#     #     cmd += ["-map", f"{audio_index}:a"]
#     # cmd += ["-map", "[v]"]
#     #
#     # if audio_index is not None:
#     #     cmd += ["-map", f"{audio_index}:a"]
#     # cmd += ["-map", "[v]"]
#
#     if audio_index is not None:
#         cmd += ["-map", f"{audio_index}:a"]
#
#     # if music:
#     #     audio_index = len(frames) + 1
#     #     if use_light:
#     #         audio_index += 1
#     #     if use_grain:
#     #         audio_index += 1
#     #
#     #     cmd += ["-map", f"{audio_index}:a"]
#
#     # cmd += [
#     #     "-c:v", "libx264",
#     #     "-preset", "slow",
#     #     "-crf", "18",
#     #     "-pix_fmt", "yuv420p",
#     #     "-c:a", "aac",
#     #     "-shortest",
#     #     output
#     # ]
#     audio_index = len(frames) + 1
#     # cmd += [
#     #     "-map", "[v]",
#     #     "-map", f"{audio_index}:a",
#     #     "-c:v", "libx264",
#     #     "-preset", "slow",
#     #     "-crf", "18",
#     #     "-pix_fmt", "yuv420p",
#     #     "-c:a", "aac",
#     #     "-shortest",
#     #     output
#     # ]
#     # music add (LAST INPUT)
#     # inputs.extend(["-i", music])
#
#     # =========================
#     # DYNAMIC AUDIO INDEX
#     # =========================
#     total_inputs = len([x for x in inputs if x == "-i"])
#     audio_index = total_inputs - 1
#
#     map_audio = f"{audio_index}:a"
#     # cmd += [
#     #     "-map", "[v]",
#     #     "-map", f"{audio_index}:a",
#     #     "-c:v", "libx264",
#     #     "-preset", "slow",
#     #     "-crf", "18",
#     #     "-pix_fmt", "yuv420p",
#     #     "-c:a", "aac",
#     #     "-shortest",
#     #     output
#     # ]
#     cmd = [
#         "ffmpeg", "-y",
#         *inputs,
#         "-filter_complex", filter_complex,
#         "-map", "[v]",
#         "-map", map_audio,
#         "-c:v", "libx264",
#         "-preset", "slow",
#         "-crf", "18",
#         "-pix_fmt", "yuv420p",
#         "-c:a", "aac",
#         "-shortest",
#         output
#     ]
#
#     print(" ".join(cmd))  # debug
#     # subprocess.run(cmd, check=True)
#     # result = subprocess.run(cmd, capture_output=True, text=True)
#     # print(result.stderr)
#     # result = subprocess.run(cmd, capture_output=True, text=True)
#     #
#     # print("STDOUT:", result.stdout)
#     # print("STDERR:", result.stderr)
#     result = subprocess.run(cmd, capture_output=True, text=True)
#
#     print("STDERR:", result.stderr)
#     print("RETURN CODE:", result.returncode)
#
#     if not os.path.exists(output):
#         print("Video not ready yet")
#         return HttpResponse("Video render failed — check ffmpeg error")
#
#     # return FileResponse(open(output, "rb"), content_type="video/mp4")
#
#     return FileResponse(
#         open(output, "rb"),
#         as_attachment=True,
#         filename=f"album_{album.id}.mp4",
#         content_type="video/mp4"
#     )


# import os, subprocess
# from django.conf import settings
# from django.shortcuts import get_object_or_404
# from django.http import FileResponse, HttpResponse
# from .models import Album, Photo
#
#
# def generate_ultra_cinematic(request, album_id):
#
#     album = get_object_or_404(Album, id=album_id)
#     photos = list(Photo.objects.filter(album=album))
#
#     if not photos:
#         return HttpResponse("No photos found")
#
#     # ✅ FIX 1: correct folder create
#     work_dir = os.path.join(settings.MEDIA_ROOT, "video_frames", str(album.id))
#     os.makedirs(work_dir, exist_ok=True)
#
#     frames = []
#
#     # ✅ FIX 2: safe image copy
#     for i, p in enumerate(photos):
#         if not p.image or not os.path.exists(p.image.path):
#             print("❌ Missing image:", p.image)
#             continue
#
#         path = os.path.join(work_dir, f"img_{i:03}.jpg")
#
#         with open(p.image.path, "rb") as src:
#             with open(path, "wb") as dst:
#                 dst.write(src.read())
#
#         frames.append(path)
#
#     # ✅ FIX 3: ensure at least 1 frame exists
#     if not frames:
#         return HttpResponse("❌ No valid images found to create video")
#
#     # 🎵 MUSIC
#     music_dir = os.path.join(settings.MEDIA_ROOT, "music")
#     music = None
#     if os.path.isdir(music_dir):
#         mp3s = sorted(
#             [f for f in os.listdir(music_dir) if f.endswith(".mp3")],
#             key=lambda x: os.path.getctime(os.path.join(music_dir, x)),
#             reverse=True
#         )
#         if mp3s:
#             music = os.path.join(music_dir, mp3s[0])
#
#     # 🎬 assets
#     bg = os.path.join(settings.MEDIA_ROOT, "background", "bg.mp4")
#     light = os.path.join(settings.MEDIA_ROOT, "background", "light.mp4")
#     grain = os.path.join(settings.MEDIA_ROOT, "background", "grain.mp4")
#
#     use_bg = os.path.exists(bg)
#     use_light = os.path.exists(light)
#     use_grain = os.path.exists(grain)
#
#     output = os.path.join(settings.MEDIA_ROOT, f"ultra_album_{album.id}.mp4")
#
#     # ================= INPUTS =================
#     inputs = []
#
#     for img in frames:
#         inputs += ["-loop", "1", "-t", "4", "-i", img]
#
#     if use_bg:
#         inputs += ["-stream_loop", "-1", "-i", bg]
#
#     if use_light:
#         inputs += ["-stream_loop", "-1", "-i", light]
#
#     if use_grain:
#         inputs += ["-stream_loop", "-1", "-i", grain]
#
#     if music:
#         inputs += ["-i", music]
#
#     # ================= FILTERS =================
#     filters = []
#
#     for i in range(len(frames)):
#         filters.append(
#             f"[{i}:v]"
#             "scale=1400:-1,"
#             #"zoompan=z='min(zoom+0.0007,1.3)':d=125:s=1280x720,"
#             "zoompan=z='min(zoom+0.0007,1.3)':d=125:s=640x720"
#             "fade=t=in:st=0:d=1,"
#             "fade=t=out:st=3:d=1"
#             f"[v{i}]"
#         )
#
#     current = "[v0]"
#     offset = 3
#
#     for i in range(1, len(frames)):
#         filters.append(
#             f"{current}[v{i}]"
#             f"xfade=transition=fade:duration=1:offset={offset}"
#             f"[v{i}out]"
#         )
#         current = f"[v{i}out]"
#         offset += 3
#
#     slideshow = current
#
#     index = len(frames)
#
#     if use_bg:
#         filters.append(f"[{index}:v]scale=1280:720[bg]")
#         filters.append(f"[bg]{slideshow}overlay=(W-w)/2:(H-h)/2")
#         current = "[base]"
#         index += 1
#     else:
#         current = slideshow
#
#     if use_light:
#         filters.append(
#             f"[{index}:v]scale=1280:720,format=rgba,colorchannelmixer=aa=0.25[light]"
#         )
#         filters.append(f"{current}[light]overlay=0:0[tmp1]")
#         current = "[tmp1]"
#         index += 1
#
#     if use_grain:
#         filters.append(
#             f"[{index}:v]scale=1280:720,format=rgba,colorchannelmixer=aa=0.15[grain]"
#         )
#         filters.append(f"{current}[grain]overlay=0:0[v]")
#     else:
#         filters.append(f"{current}null[v]")
#
#     filter_complex = ";".join(filters)
#
#     # ================= COMMAND =================
#     cmd = [
#         "ffmpeg", "-y",
#         *inputs,
#         "-filter_complex", filter_complex,
#         "-map", "[v]",
#         "-c:v", "libx264",
#         "-preset", "slow",
#         "-crf", "18",
#         "-pix_fmt", "yuv420p",
#     ]
#
#     # ✅ FIX 4: audio safe mapping
#     if music:
#         audio_index = len([x for x in inputs if x == "-i"]) - 1
#         cmd += ["-map", f"{audio_index}:a", "-c:a", "aac", "-shortest"]
#
#     cmd.append(output)
#
#     print(" ".join(cmd))
#
#     total_duration = len(frames) * 4  # seconds
#
#     process = subprocess.Popen(
#         cmd,
#         stderr=subprocess.PIPE,
#         stdout=subprocess.DEVNULL,
#         text=True
#     )
#
#     for line in process.stderr:
#         if "time=" in line:
#             try:
#                 time_str = line.split("time=")[-1].split(" ")[0]
#
#                 h, m, s = time_str.split(":")
#                 current_time = int(h) * 3600 + int(m) * 60 + float(s)
#
#                 percent = min((current_time / total_duration) * 100, 100)
#
#                 print(f"🔥 Progress: {percent:.2f}%")
#
#             except Exception as e:
#                 print("Parse error:", e)
#
#     process.wait()
#
#     print("RETURN CODE:", process.returncode)
#
#     # ✅ FIX 5: output check
#     if not os.path.exists(output):
#         return HttpResponse("❌ Video render failed — check ffmpeg error")
#
#     return FileResponse(
#         open(output, "rb"),
#         as_attachment=True,
#         filename=f"album_{album.id}.mp4",
#         content_type="video/mp4"
#     )

####################################################
####################################################
####################################################
# import os, subprocess, uuid
# from django.conf import settings
# from django.shortcuts import get_object_or_404
# from django.http import FileResponse, HttpResponse
# from .models import Album, Photo
#
#
# def generate_ultra_cinematic(request, album_id):
#
#     album = get_object_or_404(Album, id=album_id)
#     photos = list(Photo.objects.filter(album=album))
#
#     if not photos:
#         return HttpResponse("No photos found")
#
#     # ================= USER INPUT (NEW) =================
#     if request.method == "POST":
#         selected_bg = request.POST.get("bgvideo")
#         selected_music = request.POST.get("music")
#
#         bg_file = request.FILES.get("bg_upload")
#         music_file = request.FILES.get("music_upload")
#     else:
#         return HttpResponse("❌ Use POST method")
#
#     # folders ensure
#     bg_folder = os.path.join(settings.MEDIA_ROOT, "background")
#     music_folder = os.path.join(settings.MEDIA_ROOT, "music")
#
#     os.makedirs(bg_folder, exist_ok=True)
#     os.makedirs(music_folder, exist_ok=True)
#
#     # ================= BACKGROUND LOGIC =================
#     bg = None
#
#     if bg_file:
#         filename = str(uuid.uuid4()) + "_" + bg_file.name
#         bg_path = os.path.join(bg_folder, filename)
#
#         with open(bg_path, "wb+") as f:
#             for chunk in bg_file.chunks():
#                 f.write(chunk)
#
#         bg = bg_path
#
#     elif selected_bg:
#         bg = os.path.join(bg_folder, selected_bg)
#
#     else:
#         return HttpResponse("❌ Please select or upload background")
#
#     # ================= MUSIC LOGIC =================
#     music = None
#
#     if music_file:
#         filename = str(uuid.uuid4()) + "_" + music_file.name
#         music_path = os.path.join(music_folder, filename)
#
#         with open(music_path, "wb+") as f:
#             for chunk in music_file.chunks():
#                 f.write(chunk)
#
#         music = music_path
#
#     elif selected_music:
#         music = os.path.join(music_folder, selected_music)
#
#     # ================= FRAMES =================
#     work_dir = os.path.join(settings.MEDIA_ROOT, "video_frames", str(album.id))
#     os.makedirs(work_dir, exist_ok=True)
#
#     frames = []
#
#     for i, p in enumerate(photos):
#         if not p.image or not os.path.exists(p.image.path):
#             continue
#
#         path = os.path.join(work_dir, f"img_{i:03}.jpg")
#
#         with open(p.image.path, "rb") as src:
#             with open(path, "wb") as dst:
#                 dst.write(src.read())
#
#         frames.append(path)
#
#     if not frames:
#         return HttpResponse("❌ No valid images found")
#
#     # ================= EXTRA ASSETS =================
#     light = os.path.join(bg_folder, "light.mp4")
#     grain = os.path.join(bg_folder, "grain.mp4")
#
#     use_bg = bg and os.path.exists(bg)
#     use_light = os.path.exists(light)
#     use_grain = os.path.exists(grain)
#     use_music = music and os.path.exists(music)
#
#     output = os.path.join(settings.MEDIA_ROOT, f"ultra_album_{album.id}.mp4")
#
#     # ================= INPUTS =================
#     inputs = []
#
#     for img in frames:
#         inputs += ["-loop", "1", "-t", "4", "-i", img]
#
#     if use_bg:
#         inputs += ["-stream_loop", "-1", "-i", bg]
#
#     if use_light:
#         inputs += ["-stream_loop", "-1", "-i", light]
#
#     if use_grain:
#         inputs += ["-stream_loop", "-1", "-i", grain]
#
#     if use_music:
#         inputs += ["-i", music]
#
#     # # ================= FILTERS =================
#     # filters = []
#     #
#     # for i in range(len(frames)):
#     #     filters.append(
#     #         f"[{i}:v]"
#     #         "scale=1400:-1,"
#     #         "zoompan=z='min(zoom+0.0007,1.3)':d=125:s=640x720,"  # 👈 50% width FIX
#     #         "fade=t=in:st=0:d=1,"
#     #         "fade=t=out:st=3:d=1"
#     #         f"[v{i}]"
#     #     )
#     #
#     # current = "[v0]"
#     # offset = 3
#     #
#     # for i in range(1, len(frames)):
#     #     filters.append(
#     #         f"{current}[v{i}]"
#     #         f"xfade=transition=fade:duration=1:offset={offset}"
#     #         f"[v{i}out]"
#     #     )
#     #     current = f"[v{i}out]"
#     #     offset += 3
#     #
#     # slideshow = current
#     # index = len(frames)
#     #
#     # if use_bg:
#     #     filters.append(f"[{index}:v]scale=1280:720[bg]")
#     #     filters.append(f"[bg]{slideshow}overlay=(W-w)/2:(H-h)/2[base]")
#     #     current = "[base]"
#     #     index += 1
#     # else:
#     #     current = slideshow
#     #
#     # if use_light:
#     #     filters.append(
#     #         f"[{index}:v]scale=1280:720,format=rgba,colorchannelmixer=aa=0.25[light]"
#     #     )
#     #     filters.append(f"{current}[light]overlay=0:0[tmp1]")
#     #     current = "[tmp1]"
#     #     index += 1
#     #
#     # if use_grain:
#     #     filters.append(
#     #         f"[{index}:v]scale=1280:720,format=rgba,colorchannelmixer=aa=0.15[grain]"
#     #     )
#     #     filters.append(f"{current}[grain]overlay=0:0[v]")
#     # else:
#     #     filters.append(f"{current}null[v]")
#     #
#     # filter_complex = ";".join(filters)
#     # ================= FILTERS (NEW CINEMATIC) =================
#     filters = []
#
#     # 👉 STEP 1: SMALL CARD (sheet size)
#     for i in range(len(frames)):
#         filters.append(
#             f"[{i}:v]"
#             "scale=1400:-1,"
#             "zoompan=z='min(zoom+0.0007,1.3)':d=125:s=700x500,"
#             "fade=t=in:st=0:d=1,"
#             "fade=t=out:st=3:d=1"
#             f"[v{i}]"
#         )
#
#     # 👉 STEP 2: TRANSITIONS
#     current = "[v0]"
#     offset = 3
#
#     for i in range(1, len(frames)):
#         filters.append(
#             f"{current}[v{i}]"
#             f"xfade=transition=fade:duration=1:offset={offset}"
#             f"[v{i}out]"
#         )
#         current = f"[v{i}out]"
#         offset += 3
#
#     slideshow = current
#     index = len(frames)
#
#     # 👉 STEP 3: BACKGROUND BLUR
#     if use_bg:
#         filters.append(f"[{index}:v]scale=1280:720,boxblur=20:1[bg]")
#         index += 1
#     else:
#         filters.append(f"{slideshow}null[bg]")
#
#     # 👉 STEP 4: SHADOW EFFECT
#     filters.append(
#         f"{slideshow}format=rgba,boxblur=8:1,scale=720:520[shadow]"
#     )
#
#     filters.append(
#         f"[bg][shadow]overlay=(W-w)/2+15:(H-h)/2+15[tmpbg]"
#     )
#
#     # 👉 STEP 5: CENTER CARD
#     filters.append(
#         f"[tmpbg]{slideshow}overlay=(W-w)/2:(H-h)/2[base]"
#     )
#
#     current = "[base]"
#
#     # 👉 STEP 6: LIGHT
#     if use_light:
#         filters.append(
#             f"[{index}:v]scale=1280:720,format=rgba,colorchannelmixer=aa=0.25[light]"
#         )
#         filters.append(f"{current}[light]overlay=0:0[tmp1]")
#         current = "[tmp1]"
#         index += 1
#
#     # 👉 STEP 7: GRAIN
#     if use_grain:
#         filters.append(
#             f"[{index}:v]scale=1280:720,format=rgba,colorchannelmixer=aa=0.12[grain]"
#         )
#         filters.append(f"{current}[grain]overlay=0:0[v]")
#     else:
#         filters.append(f"{current}null[v]")
#
#     # 👉 FINAL
#     filter_complex = ";".join(filters)
#
#     # ================= COMMAND =================
#     cmd = [
#         "ffmpeg", "-y",
#         *inputs,
#         "-filter_complex", filter_complex,
#         "-map", "[v]",
#         "-c:v", "libx264",
#         "-preset", "slow",
#         "-crf", "18",
#         "-pix_fmt", "yuv420p",
#     ]
#
#     if use_music:
#         audio_index = len([x for x in inputs if x == "-i"]) - 1
#         cmd += ["-map", f"{audio_index}:a", "-c:a", "aac", "-shortest"]
#
#     cmd.append(output)
#
#     print(" ".join(cmd))
#
#     subprocess.run(cmd)
#
#     if not os.path.exists(output):
#         return HttpResponse("❌ Video render failed")
#
#     return FileResponse(
#         open(output, "rb"),
#         as_attachment=True,
#         filename=f"album_{album.id}.mp4",
#         content_type="video/mp4"
#     )
###################################################
####################################################
###########################################################
import os, subprocess, uuid
from django.conf import settings
from django.shortcuts import get_object_or_404
from django.http import FileResponse, HttpResponse
from .models import Album, Photo


def generate_ultra_cinematic(request, album_id):

    album = get_object_or_404(Album, id=album_id)
    photos = list(Photo.objects.filter(album=album))

    if not photos:
        return HttpResponse("No photos found")

    # ================= USER INPUT (NEW) =================
    if request.method == "POST":
        selected_bg = request.POST.get("bgvideo")
        selected_music = request.POST.get("music")

        bg_file = request.FILES.get("bg_upload")
        music_file = request.FILES.get("music_upload")
    else:
        return HttpResponse("❌ Use POST method")

    # folders ensure
    bg_folder = os.path.join(settings.MEDIA_ROOT, "background")
    music_folder = os.path.join(settings.MEDIA_ROOT, "music")

    os.makedirs(bg_folder, exist_ok=True)
    os.makedirs(music_folder, exist_ok=True)

    # ================= BACKGROUND LOGIC =================
    bg = None

    if bg_file:
        filename = str(uuid.uuid4()) + "_" + bg_file.name
        bg_path = os.path.join(bg_folder, filename)

        with open(bg_path, "wb+") as f:
            for chunk in bg_file.chunks():
                f.write(chunk)

        bg = bg_path

    elif selected_bg:
        bg = os.path.join(bg_folder, selected_bg)

    else:
        return HttpResponse("❌ Please select or upload background")

    # ================= MUSIC LOGIC =================
    music = None

    if music_file:
        filename = str(uuid.uuid4()) + "_" + music_file.name
        music_path = os.path.join(music_folder, filename)

        with open(music_path, "wb+") as f:
            for chunk in music_file.chunks():
                f.write(chunk)

        music = music_path

    elif selected_music:
        music = os.path.join(music_folder, selected_music)

    # ================= FRAMES =================
    work_dir = os.path.join(settings.MEDIA_ROOT, "video_frames", str(album.id))
    os.makedirs(work_dir, exist_ok=True)

    frames = []

    for i, p in enumerate(photos):
        if not p.image or not os.path.exists(p.image.path):
            continue

        path = os.path.join(work_dir, f"img_{i:03}.jpg")

        with open(p.image.path, "rb") as src:
            with open(path, "wb") as dst:
                dst.write(src.read())

        frames.append(path)

    if not frames:
        return HttpResponse("❌ No valid images found")

    # ================= EXTRA ASSETS =================
    light = os.path.join(bg_folder, "light.mp4")
    grain = os.path.join(bg_folder, "grain.mp4")

    use_bg = bg and os.path.exists(bg)
    use_light = os.path.exists(light)
    use_grain = os.path.exists(grain)
    use_music = music and os.path.exists(music)

    output = os.path.join(settings.MEDIA_ROOT, f"ultra_album_{album.id}.mp4")

    # ================= INPUTS =================
    inputs = []

    for img in frames:
        inputs += ["-loop", "1", "-t", "4", "-i", img]

    if use_bg:
        inputs += ["-stream_loop", "-1", "-i", bg]

    if use_light:
        inputs += ["-stream_loop", "-1", "-i", light]

    if use_grain:
        inputs += ["-stream_loop", "-1", "-i", grain]

    if use_music:
        inputs += ["-i", music]

    filters = []

    # 👉 STEP 1: SMALL CARD (sheet size)
    #for i in range(len(frames)):
    # for i in range(0, len(frames), 2):
    #     filters.append(
    #         f"[{i}:v]"
    #         "scale=1400:-1,"
    #         "zoompan=z='min(zoom+0.0007,1.3)':d=125:s=700x500,"
    #         "fade=t=in:st=0:d=1,"
    #         "fade=t=out:st=3:d=1"
    #         f"[v{i}]"
    #     )
    for i in range(0, len(frames), 2):
        filters.append(f"[{i}:v]scale=640:720[left{i}]")
        filters.append(f"[{i + 1}:v]scale=640:720[right{i}]")
        filters.append(f"[left{i}][right{i}]hstack=inputs=2[slide{i}]")

    # 👉 STEP 2: TRANSITIONS
    # current = "[v0]"
    # offset = 3
    #
    # for i in range(1, len(frames)):
    #     filters.append(
    #         f"{current}[v{i}]"
    #         f"xfade=transition=fade:duration=1:offset={offset}"
    #         f"[v{i}out]"
    #     )
    #     current = f"[v{i}out]"
    #     offset += 3
    current = "[slide0]"
    offset = 3

    for i in range(2, len(frames), 2):
        filters.append(
            f"{current}[slide{i}]xfade=transition=fade:duration=1:offset={offset}[out{i}]"
        )
        current = f"[out{i}]"
        offset += 3

    slideshow = current
    index = len(frames)

    # 👉 STEP 3: BACKGROUND BLUR
    if use_bg:
        #filters.append(f"[{index}:v]scale=1280:720,boxblur=20:1[bg]")
        filters.append(f"[{index}:v]scale=1280:720[bg]")
        index += 1
    else:
        filters.append(f"{slideshow}null[bg]")

    # 👉 STEP 4: SHADOW EFFECT
    # filters.append(
    #     f"{slideshow}format=rgba,boxblur=8:1,scale=720:520[shadow]"
    # )
    filters.append(
        f"{slideshow}format=rgba,scale=720:520[shadow]"
    )

    filters.append(
        f"[bg][shadow]overlay=(W-w)/2+15:(H-h)/2+15[tmpbg]"
    )

    # 👉 STEP 5: CENTER CARD
    filters.append(
        f"[tmpbg]{slideshow}overlay=(W-w)/2:(H-h)/2[base]"
    )

    current = "[base]"

    # 👉 STEP 6: LIGHT
    if use_light:
        filters.append(
            f"[{index}:v]scale=1280:720,format=rgba,colorchannelmixer=aa=0.25[light]"
        )
        filters.append(f"{current}[light]overlay=0:0[tmp1]")
        current = "[tmp1]"
        index += 1

    # 👉 STEP 7: GRAIN
    if use_grain:
        filters.append(
            f"[{index}:v]scale=1280:720,format=rgba,colorchannelmixer=aa=0.12[grain]"
        )
        filters.append(f"{current}[grain]overlay=0:0[v]")
    else:
        filters.append(f"{current}null[v]")

    # 👉 FINAL
    filter_complex = ";".join(filters)

    # ================= COMMAND =================
    cmd = [
        "ffmpeg", "-y",
        *inputs,
        "-filter_complex", filter_complex,
        "-map", "[v]",
        "-c:v", "libx264",
        "-preset", "slow",
        "-crf", "18",
        "-pix_fmt", "yuv420p",
    ]

    if use_music:
        audio_index = len([x for x in inputs if x == "-i"]) - 1
        cmd += ["-map", f"{audio_index}:a", "-c:a", "aac", "-shortest"]

    cmd.append(output)

    print(" ".join(cmd))

    subprocess.run(cmd)

    if not os.path.exists(output):
        return HttpResponse("❌ Video render failed")

    return FileResponse(
        open(output, "rb"),
        as_attachment=True,
        filename=f"album_{album.id}.mp4",
        content_type="video/mp4"
    )
# import os
# import uuid
# import subprocess
# from django.conf import settings
# from django.http import FileResponse, Http404
#
#
# def generate_ultra_cinematic(request, album_id):
#
#     print("🔥 ULTRA CINEMATIC STARTED")
#
#     # ===============================
#     # MEDIA PATH
#     # ===============================
#     media_root = settings.MEDIA_ROOT
#     os.makedirs(media_root, exist_ok=True)
#
#     output_name = f"ultra_album_{album_id}.mp4"
#     output_path = os.path.join(media_root, output_name)
#
#     print("Output path:", output_path)
#
#     # ===============================
#     # ASSETS PATH
#     # ===============================
#     bg = os.path.join(settings.MEDIA_ROOT, "assets/bg.mp4")
#     light = os.path.join(settings.MEDIA_ROOT, "assets/light.mp4")
#     grain = os.path.join(settings.MEDIA_ROOT, "assets/grain.mp4")
#     music = os.path.join(settings.MEDIA_ROOT, "assets/music.mp3")
#
#     print("BG exists:", os.path.exists(bg))
#     print("Light exists:", os.path.exists(light))
#     print("Grain exists:", os.path.exists(grain))
#     print("Music exists:", os.path.exists(music))
#
#     # ===============================
#     # REQUIRED FILE CHECK
#     # ===============================
#     if not os.path.exists(bg):
#         raise Http404("Background video missing")
#
#     if not os.path.exists(music):
#         raise Http404("Music missing")
#
#     # ===============================
#     # FFmpeg INPUTS
#     # ===============================
#     inputs = []
#
#     # background loop
#     inputs += ["-stream_loop", "-1", "-i", bg]
#
#     # optional overlays
#     if os.path.exists(light):
#         inputs += ["-i", light]
#
#     if os.path.exists(grain):
#         inputs += ["-i", grain]
#
#     # music
#     inputs += ["-i", music]
#
#     # ===============================
#     # FILTER GRAPH
#     # ===============================
#     filter_complex = "[0:v]scale=1280:720[bg];"
#
#     # input_index = 1
#     # last = "[bg]"
#     #
#     # if os.path.exists(light):
#     #     filter_complex += f"{last}[{input_index}:v]overlay=0:0[tmp1];"
#     #     last = "[tmp1]"
#     #     input_index += 1
#     #
#     # if os.path.exists(grain):
#     #     filter_complex += f"{last}[{input_index}:v]overlay=0:0[tmp2];"
#     #     last = "[tmp2]"
#     #     input_index += 1
#     #
#     # final_video = last
#     filter_complex = """
#     [0:v]scale=1280:720,format=rgba[bg];
#     """
#
#     input_index = 1
#     last = "[bg]"
#
#     if os.path.exists(light):
#         filter_complex += f"""
#     {last}[{input_index}:v]scale=1280:720,format=rgba,colorchannelmixer=aa=0.3[light];
#     {last}[light]overlay=0:0:format=auto[tmp1];
#     """
#         last = "[tmp1]"
#         input_index += 1
#
#     if os.path.exists(grain):
#         filter_complex += f"""
#     {last}[{input_index}:v]scale=1280:720,format=rgba,colorchannelmixer=aa=0.15[grain];
#     {last}[grain]overlay=0:0:format=auto[tmp2];
#     """
#         last = "[tmp2]"
#         input_index += 1
#
#     final_video = last
#
#     # ===============================
#     # AUDIO INDEX
#     # ===============================
#     audio_index = input_index
#
#     # ===============================
#     # FFmpeg COMMAND
#     # ===============================
#     cmd = [
#         "ffmpeg",
#         "-y",
#         *inputs,
#         "-filter_complex", filter_complex,
#         "-map", final_video,
#         "-map", f"{audio_index}:a",
#         "-t", "20",
#         "-c:v", "libx264",
#         "-preset", "medium",
#         "-crf", "20",
#         "-pix_fmt", "yuv420p",
#         "-shortest",
#         output_path
#     ]
#
#     print("FFMPEG COMMAND:")
#     print(" ".join(cmd))
#
#     # ===============================
#     # RUN FFMPEG
#     # ===============================
#     try:
#         subprocess.run(cmd, check=True)
#         print("✅ VIDEO CREATED")
#     except subprocess.CalledProcessError as e:
#         print("❌ FFMPEG FAILED:", e)
#         raise Http404("Video generation failed")
#
#     # ===============================
#     # FINAL CHECK
#     # ===============================
#     if not os.path.exists(output_path):
#         raise Http404("Video file not created")
#
#     print("✅ RETURNING VIDEO")
#
#     return FileResponse(open(output_path, "rb"), content_type="video/mp4")



# import os
# import cv2
# import zipfile
# from django.shortcuts import render
# from django.conf import settings
# from django.http import HttpResponse
# from django.core.files.storage import FileSystemStorage
#
# def index(request):
#     if request.method == 'POST':
#         images = request.FILES.getlist('images')
#         processed_files = []
#
#         fs = FileSystemStorage()
#
#         for image in images:
#             filename = fs.save(image.name, image)
#             file_path = fs.path(filename)
#
#             img = cv2.imread(file_path)
#
#             # 🔥 Sharpen Effect
#             gaussian = cv2.GaussianBlur(img, (9, 9), 10.0)
#             sharpened = cv2.addWeighted(img, 1.5, gaussian, -0.5, 0)
#
#             # 🖼 Frame Option
#             if request.POST.get('frame') == 'yes':
#                 sharpened = cv2.copyMakeBorder(
#                     sharpened,
#                     20, 20, 20, 20,
#                     cv2.BORDER_CONSTANT,
#                     value=[0, 0, 0]
#                 )
#
#             processed_filename = "processed_" + filename
#             processed_path = os.path.join(settings.MEDIA_ROOT, processed_filename)
#             cv2.imwrite(processed_path, sharpened)
#
#             processed_files.append(processed_path)
#
#         # 📦 Create ZIP file
#         zip_path = os.path.join(settings.MEDIA_ROOT, "processed_images.zip")
#         with zipfile.ZipFile(zip_path, 'w') as zipf:
#             for file in processed_files:
#                 zipf.write(file, os.path.basename(file))
#
#         # Download ZIP
#         with open(zip_path, 'rb') as zipf:
#             response = HttpResponse(zipf.read(), content_type='application/zip')
#             response['Content-Disposition'] = 'attachment; filename=processed_images.zip'
#             return response
#
#     return render(request, 'index.html')


# import os
# import cv2
# import numpy as np
# import zipfile
# from django.shortcuts import render
# from django.conf import settings
# from django.http import HttpResponse
#
#
# def index(request):
#
#     if request.method == 'POST':
#
#         images = request.FILES.getlist('images')
#         processed_files = []
#
#         os.makedirs(settings.MEDIA_ROOT, exist_ok=True)
#
#         for image in images:
#
#             try:
#                 # ==========================
#                 # READ IMAGE FROM MEMORY
#                 # ==========================
#                 file_bytes = np.asarray(bytearray(image.read()), dtype=np.uint8)
#                 img = cv2.imdecode(file_bytes, cv2.IMREAD_COLOR)
#
#                 if img is None:
#                     print("Decode failed:", image.name)
#                     continue
#
#                 # ==============================
#                 # STEP 1 → Light noise removal
#                 # ==============================
#                 denoised = cv2.fastNlMeansDenoisingColored(
#                     img,
#                     None,
#                     5,  # low noise remove (important)
#                     5,
#                     7,
#                     21
#                 )
#
#                 # ==============================
#                 # STEP 2 → High-pass sharpening (CRISP DETAIL)
#                 # ==============================
#                 blur = cv2.GaussianBlur(denoised, (0, 0), 1.0)
#                 high_pass = cv2.subtract(denoised, blur)
#
#                 sharpened = cv2.addWeighted(
#                     denoised,
#                     1.0,
#                     high_pass,
#                     1.5,  # sharpness power (increase for more sharp)
#                     0
#                 )
#
#                 # ==============================
#                 # STEP 3 → Extra edge enhance
#                 # ==============================
#                 kernel = np.array([
#                     [-2, -1, -2],
#                     [-1, 10, -1],
#                     [-2, -1, -2]
#                 ])
#                 enhanced = cv2.filter2D(sharpened, -1, kernel)
#
#                 # ==============================
#                 # STEP 4 → Contrast improve
#                 # ==============================
#                 lab = cv2.cvtColor(enhanced, cv2.COLOR_BGR2LAB)
#                 l, a, b = cv2.split(lab)
#
#                 clahe = cv2.createCLAHE(clipLimit=1.5, tileGridSize=(8, 8))
#                 l = clahe.apply(l)
#
#                 final = cv2.merge((l, a, b))
#                 final = cv2.cvtColor(final, cv2.COLOR_LAB2BGR)
#
#                 # ==========================
#                 # OPTIONAL FRAME
#                 # ==========================
#                 if request.POST.get('frame') == 'yes':
#                     final = cv2.copyMakeBorder(
#                         final, 20, 20, 20, 20,
#                         cv2.BORDER_CONSTANT,
#                         value=[0,0,0]
#                     )
#
#                 # ==========================
#                 # SAVE IMAGE
#                 # ==========================
#                 processed_filename = f"processed_{image.name}"
#                 processed_path = os.path.join(settings.MEDIA_ROOT, processed_filename)
#
#                 cv2.imwrite(processed_path, final)
#                 processed_files.append(processed_path)
#
#             except Exception as e:
#                 print("Error:", image.name, e)
#                 continue
#
#         if not processed_files:
#             return HttpResponse("No images processed")
#
#         # ==========================
#         # CREATE ZIP
#         # ==========================
#         zip_path = os.path.join(settings.MEDIA_ROOT, "processed_images.zip")
#
#         with zipfile.ZipFile(zip_path, 'w') as zipf:
#             for file in processed_files:
#                 zipf.write(file, os.path.basename(file))
#
#         # ==========================
#         # DOWNLOAD ZIP
#         # ==========================
#         with open(zip_path, 'rb') as f:
#             response = HttpResponse(f.read(), content_type='application/zip')
#             response['Content-Disposition'] = 'attachment; filename=processed_images.zip'
#             return response
#
#     return render(request, 'index.html')


def user_logout():
    pass



def download_video(request, album_id):
    video = get_object_or_404(Video, id=id)
    response = HttpResponse(video.video, content_type='video/mp4')
    response['Content-Disposition'] = f'attachment; filename="{video.video.name}"'
    return response

import zipfile
from io import BytesIO

def download_selected_videos(request):
    ids = request.POST.getlist('video_ids')
    videos = Video.objects.filter(id__in=ids)

    zip_buffer = BytesIO()

    with zipfile.ZipFile(zip_buffer, 'w') as zip_file:
        for video in videos:
            zip_file.write(video.video.path, video.video.name)

    zip_buffer.seek(0)

    response = HttpResponse(zip_buffer, content_type='application/zip')
    response['Content-Disposition'] = 'attachment; filename="videos.zip"'

    return response

def delete_video(request, id):
    video = get_object_or_404(Video, id=id)
    video.delete()
    return redirect('album-detail')  # apna URL name use karo