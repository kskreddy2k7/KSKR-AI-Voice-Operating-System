# Sai Companion – Android App

**Sai Companion** is the Android companion application for Sai AI Voice Assistant.
It receives commands from the PC assistant over a local Wi-Fi REST API and
executes phone-side actions.

---

## Features

| Feature | Description |
|---|---|
| **SMS** | Send text messages to any contact |
| **Phone calls** | Initiate outgoing calls |
| **App launcher** | Open any installed app by name |
| **Media control** | Play, pause, skip tracks |
| **Feed scroll** | Scroll social media reels / feeds |
| **WhatsApp** | Open WhatsApp and send messages |
| **Connect to PC** | Enter your PC's IP address to pair |

---

## Architecture

```
PC (Sai AI)  ──REST API (port 5050)──>  Android phone (Sai Companion)
```

The PC assistant runs a Flask REST server (`android/phone_api.py`).
The Android app polls for commands and executes them using Android APIs.

---

## Building the APK

### Prerequisites

- Android Studio Hedgehog (2023.1.1) or newer
- JDK 17
- Android SDK API level 33+
- Kotlin 1.9+

### Steps

1. Open **Android Studio**.
2. Choose **Open an Existing Project** and select this `android_app/` folder.
3. Wait for Gradle sync to complete.
4. Connect an Android device or start an emulator.
5. Select **Build → Build Bundle(s) / APK(s) → Build APK(s)**.
6. The APK will be generated at:
   `android_app/app/build/outputs/apk/debug/app-debug.apk`
7. Install via ADB:
   ```bash
   adb install app/build/outputs/apk/debug/app-debug.apk
   ```

---

## Connecting to the PC

1. Ensure PC and phone are on the **same Wi-Fi network**.
2. Enable Android mode in `config/settings.json`:
   ```json
   "android": {
     "enabled": true,
     "host": "0.0.0.0",
     "port": 5050
   }
   ```
3. Start Sai AI on the PC (`python main.py`).
4. Open **Sai Companion** on the phone.
5. Enter the PC's local IP address (e.g., `192.168.1.10`) and tap **Connect**.

---

## REST API Endpoints

The following endpoints are served by the PC (`android/phone_api.py`):

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/send_sms` | Send SMS to a contact |
| `POST` | `/call` | Make a phone call |
| `POST` | `/open_app` | Open a phone app |
| `POST` | `/media` | Control media playback |
| `POST` | `/scroll` | Scroll a feed |
| `GET`  | `/ping` | Health check |

All requests require the `X-API-Key` header matching `android.secret_key` in
`config/settings.json`.

---

## Required Android Permissions

```xml
<uses-permission android:name="android.permission.SEND_SMS" />
<uses-permission android:name="android.permission.CALL_PHONE" />
<uses-permission android:name="android.permission.READ_CONTACTS" />
<uses-permission android:name="android.permission.INTERNET" />
```

---

## Security Notes

- Change `android.secret_key` in `config/settings.json` before enabling.
- The REST server binds to `0.0.0.0` by default – restrict to your local
  network and do not expose the port to the internet.
- HTTPS/TLS is recommended for production deployments.
