[app]

# (str) Title of your application
title = Lotto Generator

# (str) Package name
package.name = lottogenerator

# (str) Package domain (needed for android/ios packaging)
package.domain = org.kivy.lotto

# (str) Source code where the main.py live
source.dir = .

# (list) Source files to include (let empty to include all the files)
source.include_exts = py,png,jpg,kv,atlas,json,csv

# (list) Application requirements
requirements = python3,kivy,requests,beautifulsoup4,setuptools,cython

# (str) Application versioning (method 1)
version = 0.1

# (list) Supported orientations
orientation = portrait

#
# Android specific
#

# (int) Target Android API, should be as high as possible.
android.api = 33

# (int) Minimum API your APK / AAB will support.
android.minapi = 21

# (int) Android NDK API to use. This is the minimum API your app will support, it should usually match android.minapi.
android.ndk_api = 33

# (str) Android NDK version to use
android.ndk = 25b

# (bool) If True, then automatically accept SDK license
# agreements. This is intended for automation only.
android.accept_sdk_license = True

# (list) The Android archs to build for, choices: armeabi-v7a, arm64-v8a, x86, x86_64
android.archs = arm64-v8a, armeabi-v7a

#
# Python for android (p4a) specific
#

# (str) python-for-android URL to use for checkout
p4a.url = https://github.com/kivy/python-for-android

# (str) python-for-android branch to use, defaults to master
p4a.branch = develop

[buildozer]

# (int) Log level (0 = error only, 1 = info, 2 = debug (with command output))
log_level = 2