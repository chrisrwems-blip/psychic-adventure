# DC Submittal Review Platform

A desktop tool for electrical engineers reviewing submittals on modular data center projects.

## What This Tool Does

- **Upload submittal PDFs** for any major equipment type (switchgear, UPS, PDUs, generators, transformers, ATS, cables, bus ducts, panelboards, RPPs, STS, batteries, cooling units)
- **Automated review against NEC, NFPA, IEEE, UL, and Uptime Tier standards** -- 308 checks across 13 equipment types, flagging code violations and spec gaps automatically
- **Mark up PDFs with comments** -- generates a marked-up PDF with severity-coded annotations and a summary page you can send back to the vendor
- **Generate RFI and response emails** -- auto-writes RFI, clarification, rejection, or approval emails grouped by severity, ready to copy into Outlook
- **Track comments across projects** -- filter open, resolved, and deferred items by severity, equipment type, and project

---

## Step 1: Install Prerequisites (One-Time Setup)

You need to install three programs. If you already have any of them, skip that one.

### Python

1. Go to **https://www.python.org/downloads/**
2. Click the big yellow **"Download Python"** button
3. Run the installer
4. **IMPORTANT: On the very first screen of the installer, CHECK the box that says "Add Python to PATH."** If you miss this, the tool will not work.
5. Click "Install Now" and let it finish

### Node.js

1. Go to **https://nodejs.org/**
2. Click the **LTS** button (the one on the left -- LTS means Long Term Support, it is the stable version)
3. Run the installer and click Next through all the screens -- the defaults are fine

### Git

1. Go to **https://git-scm.com/download/win**
2. The download should start automatically. If not, click the link for the latest version
3. Run the installer and **keep clicking Next for every screen** -- all the defaults are fine
4. Click Install, then Finish

---

## Step 2: Download the Tool

1. Click the **Start** menu (Windows icon, bottom-left of your screen)
2. Type **PowerShell** and click **Windows PowerShell** when it appears
3. A blue window will open. Type (or copy and paste) these commands one at a time, pressing **Enter** after each one:

```
cd ~
git clone https://github.com/chrisrwems-blip/psychic-adventure.git
cd psychic-adventure
git checkout claude/submittal-review-platform-tmhtv
```

You only need to do this once. The tool is now saved in a folder called **psychic-adventure** inside your user folder (for example, `C:\Users\JSmith\psychic-adventure`).

You can close PowerShell now.

---

## Step 3: Run It

1. Open **File Explorer** (the folder icon on your taskbar)
2. In the address bar at the top, type `C:\Users\YourName\psychic-adventure` (replace **YourName** with your Windows username -- for example, `C:\Users\JSmith\psychic-adventure`) and press Enter
3. Double-click **DC Submittal Review.bat**
4. A black terminal window will appear. The first time you run it, it will take a few minutes because it is downloading and installing dependencies -- this is normal, let it finish
5. When it is ready, your web browser will open automatically to **http://localhost:5173** -- this is the tool running on your own computer

### To run without a terminal window sitting open

Double-click **DC Submittal Review.vbs** instead. This does the same thing but hides the terminal window so it runs quietly in the background.

---

## Step 4: How to Use

### 1. Create a Project

- Click **"New Project"** on the home screen
- Enter a project name (for example, "Phoenix DC Module 3") and select the **Tier level** (I, II, III, or IV)
- Click **Create**

### 2. Upload a Submittal PDF

- Open your project and click **"Upload Submittal"**
- Select a PDF from your computer
- Pick the **equipment type** from the dropdown (Switchgear, UPS, Generator, etc.)
- Fill in the manufacturer name and contractor info if you have it
- Click **Upload**

### 3. Run the Automated Review

- Click **"Run Review"**
- The tool reads through your PDF and checks it against all applicable codes and standards for that equipment type -- NEC articles, IEEE standards, NFPA requirements, UL listings, Uptime Tier criteria, and more
- This usually takes 30 seconds to a couple of minutes depending on the PDF size

### 4. Review the Findings

- Each check shows one of three results:
  - **PASS** -- meets the standard
  - **FAIL** -- does not meet the standard (includes the specific code reference)
  - **NEEDS REVIEW** -- could not be confirmed from the submittal, requires manual review
- You can add your own manual comments to any finding
- Findings are sorted by severity so the most critical items are at the top

### 5. Mark Up the PDF

- Click **"Mark Up PDF"** -- the tool switches to the **View PDF** tab and shows your submittal with all comments overlaid directly on the pages
- Annotations are color-coded by severity (red for critical, yellow for warnings, blue for informational)
- A summary page is added at the front with all findings listed

### 6. Download the Marked-Up PDF

- Click **"Download"** to save the marked-up PDF to your computer
- This is the file you send back to the vendor or contractor

### 7. Generate Emails

- Go to the **Emails** tab
- Pick the email type:
  - **RFI** -- Request for Information, asking for missing data
  - **Clarification** -- asking the vendor to clarify something
  - **Rejection** -- rejecting the submittal with specific reasons
  - **Approval** -- approving (with or without comments)
- Click **Generate** -- the tool writes the full email body with all relevant findings grouped by severity
- Copy and paste into Outlook, or click **"Copy to Clipboard"**

### 8. Track Comments Across Projects

- Click **Comment Tracker** in the left sidebar
- See all comments across all your projects in one place
- Filter by status (Open, Resolved, Deferred), severity, equipment type, or project name

---

## Stopping the App

- If you used **DC Submittal Review.bat**: just close the black terminal window
- If you used **DC Submittal Review.vbs** (no visible window): press **Ctrl+Shift+Esc** to open Task Manager, look for **"python"** in the list, click it, and click **End Task**

---

## Updating the Tool

When a new version is available, you need to pull the latest changes:

1. Open **PowerShell** (search "PowerShell" in the Start menu)
2. Run these commands:

```
cd C:\Users\YourName\psychic-adventure
git pull
```

Replace **YourName** with your Windows username. Close PowerShell when it finishes.

The next time you double-click the .bat or .vbs file, you will be running the updated version.

---

## Equipment Types Supported

| Equipment Type | Number of Checks | Key Standards |
|----------------|-----------------|---------------|
| Switchgear | 35 | NEC 408, IEEE C37.20, NFPA 70E |
| UPS | 28 | IEEE 446, NEC 480, UL 1778 |
| Generator | 32 | NFPA 110, EPA Tier 4, ISO 8528 |
| PDU | 25 | IEEE C57.110, NEC 210/215 |
| Transformer | 22 | IEEE C57, NEC 450, DOE 2016 |
| ATS | 24 | UL 1008, NFPA 110, NEC 700 |
| Cable | 20 | NEC 310, NEC Chapter 9 |
| Bus Duct | 18 | NEC 368, UL 857 |
| Panelboard | 20 | NEC 408, UL 67 |
| RPP | 13 | NEC 408, UL 67/891 |
| STS | 16 | UL 1008, ITIC/CBEMA |
| Battery | 23 | IEEE 485/1188, NFPA 855, UL 1973 |
| Cooling | 32 | ASHRAE TC 9.9/90.4, NEC 440 |

**Total: 308 checks across 13 equipment types**

---

## Troubleshooting

**"start.bat is not recognized" or nothing happens when you run a command in PowerShell**
- Instead of typing `start.bat`, type `.\start.bat` (with the dot and backslash in front)
- Or just skip PowerShell entirely and double-click the file in File Explorer as described in Step 3

**Python errors or "python is not recognized"**
- This means Python was installed without being added to PATH. Uninstall Python (Settings > Apps > Python > Uninstall), then reinstall it and make sure you CHECK **"Add Python to PATH"** on the first screen of the installer

**"Port already in use" error**
- This means another copy of the tool is already running. Close any other terminal windows that are running the tool, or use Task Manager (Ctrl+Shift+Esc) to end any "python" or "node" processes, then try again

**Browser does not open automatically**
- Open your web browser manually and go to **http://localhost:5173**

**The tool seems stuck during first-time setup**
- The first run downloads dependencies and can take several minutes on a slower connection. Let it finish. If it has been more than 10 minutes with no progress, close the window and try again

**PDF does not upload or review fails**
- Make sure the file is actually a PDF (not a .docx or image). The file must end in .pdf
- Very large PDFs (over 100 MB) may take longer or need to be split into sections
