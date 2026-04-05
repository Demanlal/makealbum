# # from moviepy import concatenate_videoclips, CompositeVideoClip, ColorClip, ImageClip
# # from moviepy.editor import *
# from moviepy import (
#     concatenate_videoclips,
#     CompositeVideoClip,
#     ColorClip,
#     ImageClip,
#     vfx
# )
#
# from moviepy import vfx
#
# import numpy as np
# import random, os, cv2
#
# IMG_DUR = 3
# TRANS_DUR = 1
# FPS = 24
#
# # ---------------- SINGLE CLIP EFFECTS (24) ----------------
# #
# # def fade(c): return c.fadein(1).fadeout(1)
# #
# # def fade_in(c): return c.fadein(1)
# #
# # def fade_out(c): return c.fadeout(1)
# def fade(c):
#     return c.fx(vfx.fadein, 1).fx(vfx.fadeout, 1)
#
# def fade_in(c):
#     return c.fx(vfx.fadein, 1)
#
# def fade_out(c):
#     return c.fx(vfx.fadeout, 1)
#
#
# def zoom_in(c): return c.fx(vfx.resize, lambda t: 1 + 0.06*t)
#
# def zoom_out(c): return c.fx(vfx.resize, lambda t: 1.2 - 0.06*t)
#
# def rotate_left(c): return c.rotate(lambda t: -5*t)
#
# def rotate_right(c): return c.rotate(lambda t: 5*t)
#
# # def pan_left(c): return c.set_position(lambda t: (-40*t, 0))
# def pan_left(c):
#     w, h = c.size
#     return CompositeVideoClip(
#         [c.set_position(lambda t: (-40*t, 0))],
#         size=c.size
#     )
#
#
# def pan_right(c): return c.set_position(lambda t: (40*t, 0))
#
# def pan_up(c): return c.set_position(lambda t: (0, -40*t))
#
# def pan_down(c): return c.set_position(lambda t: (0, 40*t))
#
# def pan_diag_lr(c): return c.set_position(lambda t: (-30*t, -30*t))
#
# def pan_diag_rl(c): return c.set_position(lambda t: (30*t, -30*t))
#
# def ken_burns_in(c): return c.fx(vfx.resize, lambda t: 1 + 0.04*t)
#
# def ken_burns_out(c): return c.fx(vfx.resize, lambda t: 1.2 - 0.04*t)
#
# def mirror_x(c): return c.fx(vfx.mirror_x)
#
# def mirror_y(c): return c.fx(vfx.mirror_y)
#
# def blur_light(c):
#     return c.fl_image(lambda f: cv2.GaussianBlur(f, (7,7), 0))
#
# def blur_heavy(c):
#     return c.fl_image(lambda f: cv2.GaussianBlur(f, (21,21), 0))
#
# def bw(c): return c.fx(vfx.blackwhite)
#
# def old_film(c): return c.fx(vfx.blackwhite).fadein(1)
#
# def brighten(c): return c.fx(vfx.colorx, 1.2)
#
# def darken(c): return c.fx(vfx.colorx, 0.8)
#
# def flash(c):
#     white = ColorClip(c.size, (255,255,255), duration=0.1)
#     return concatenate_videoclips([white, c])
#
# # ---------------- PAIR TRANSITIONS (18) ----------------
#
# def crossfade(c1, c2):
#     return concatenate_videoclips(
#         [c1.crossfadeout(1), c2.crossfadein(1)],
#         method="compose"
#     )
#
# def slide_left(c1, c2):
#     w, h = c1.size
#     return CompositeVideoClip([
#         c1.set_position(lambda t: (-w*t, 0)),
#         c2.set_position(lambda t: (w-w*t, 0))
#     ], size=c1.size).set_duration(TRANS_DUR)
#
# def slide_right(c1, c2):
#     w, h = c1.size
#     return CompositeVideoClip([
#         c1.set_position(lambda t: (w*t, 0)),
#         c2.set_position(lambda t: (-w+w*t, 0))
#     ], size=c1.size).set_duration(TRANS_DUR)
#
# def slide_up(c1, c2):
#     w, h = c1.size
#     return CompositeVideoClip([
#         c1.set_position(lambda t: (0, -h*t)),
#         c2.set_position(lambda t: (0, h-h*t))
#     ], size=c1.size).set_duration(TRANS_DUR)
#
# def slide_down(c1, c2):
#     w, h = c1.size
#     return CompositeVideoClip([
#         c1.set_position(lambda t: (0, h*t)),
#         c2.set_position(lambda t: (0, -h+h*t))
#     ], size=c1.size).set_duration(TRANS_DUR)
#
# def zoom_mix(c1, c2):
#     return concatenate_videoclips([zoom_in(c1), zoom_out(c2)])
#
# def rotate_mix(c1, c2):
#     return concatenate_videoclips([rotate_left(c1), rotate_right(c2)])
#
# def blur_to_clear(c1, c2):
#     return concatenate_videoclips([blur_heavy(c1), c2])
#
# def flash_cut(c1, c2):
#     return concatenate_videoclips([flash(c1), c2])
#
# def split_lr(c1, c2):
#     w, h = c1.size
#     left = c2.crop(x1=0, x2=w//2)
#     right = c2.crop(x1=w//2, x2=w)
#     return CompositeVideoClip([
#         c1,
#         left.set_position((0,0)),
#         right.set_position((w//2,0))
#     ], size=c1.size).set_duration(TRANS_DUR)
#
# def bw_to_color(c1, c2):
#     return concatenate_videoclips([bw(c1), c2])
#
# def dark_to_bright(c1, c2):
#     return concatenate_videoclips([darken(c1), brighten(c2)])
#
# def mirror_cut(c1, c2):
#     return concatenate_videoclips([mirror_x(c1), c2])
#
# def pan_mix(c1, c2):
#     return concatenate_videoclips([pan_left(c1), pan_right(c2)])
#
# def zoom_flash(c1, c2):
#     return concatenate_videoclips([flash(zoom_in(c1)), c2])
#
# def film_cut(c1, c2):
#     return concatenate_videoclips([old_film(c1), c2])
#
# def stretch_fake(c1, c2):
#     return concatenate_videoclips([c1.fx(vfx.resize, 1.3), c2])
#
# # ---------------- TRANSITION POOL (42) ----------------
#
# TRANSITIONS = [
#     fade, fade_in, fade_out, zoom_in, zoom_out,
#     rotate_left, rotate_right,
#     pan_left, pan_right, pan_up, pan_down,
#     pan_diag_lr, pan_diag_rl,
#     ken_burns_in, ken_burns_out,
#     mirror_x, mirror_y,
#     blur_light, blur_heavy,
#     bw, old_film, brighten, darken, flash,
#
#     crossfade, slide_left, slide_right, slide_up, slide_down,
#     zoom_mix, rotate_mix, blur_to_clear, flash_cut,
#     split_lr, bw_to_color, dark_to_bright,
#     mirror_cut, pan_mix, zoom_flash, film_cut, stretch_fake
# ]
#
# # ---------------- ENGINE ----------------
#
# def apply_transition(c1, c2):
#     t = random.choice(TRANSITIONS)
#     try:
#         return t(c1, c2)
#     except TypeError:
#         return concatenate_videoclips([t(c1), c2])
#
# # def create_slideshow(img_folder, out="output.mp4"):
# #     imgs = sorted([os.path.join(img_folder,i) for i in os.listdir(img_folder)])
# #     clips = [ImageClip(i).set_duration(IMG_DUR).resize(height=720) for i in imgs]
# #
# #     final = clips[0]
# #     for nxt in clips[1:]:
# #         final = apply_transition(final, nxt)
# #
# #     final.write_videofile(out, fps=FPS)
# #
# # # ---------------- RUN ----------------
# # #create_slideshow("pythonnew/photoapp2/media/photos", "album_video.mp4")
# # create_slideshow(
# #     r"C:\Users\ADMIN\PycharmProjects\pythonnew\photoapp2\media\photos",
# #     r"C:\Users\ADMIN\PycharmProjects\pythonnew\photoapp2\media\album_video.mp4"
# # )
#
# def create_slideshow(img_folder, out="output.mp4"):
#     if not os.path.isdir(img_folder):
#         raise Exception(f"Image folder not found: {img_folder}")
#
#     imgs = sorted([
#         os.path.join(img_folder, i)
#         for i in os.listdir(img_folder)
#         if i.lower().endswith((".jpg", ".jpeg", ".png"))
#     ])
#
#     if not imgs:
#         raise Exception("No images found in folder")
#
# create_slideshow(
#     r"C:\Users\ADMIN\PycharmProjects\pythonnew\photoapp2\media\photos",
#     r"C:\Users\ADMIN\PycharmProjects\pythonnew\photoapp2\media\album_video.mp4"
# )
