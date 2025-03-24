## Project description

### Project introduction
A wearable hiking tracker built on TTGO T-Watch 2020 V3 and a Raspberry Pi 3B+ hub, capable of tracking and syncing hiking session data (steps, distance, calories) with a web interface.

### Requirement
TTGO T-Watch 2020 V3

Raspberry Pi 3B+ with Bluetooth

Python 3.10+, Flask, BluePy

Arduino IDE for Watch firmware

### File structure
Smartwatch Side (Arduino):
1. hikingassistant.ino: main logic, button UI & BLE communication
2. config.h: device config

Raspberry Pi Side(Python):
1. hike.py: Defines the HikeSession class for sessions 
2. bt.py: Bluetooth handler class and functions for syncing with watch 
3. receiver.py: Reads and parses incoming BLE data 
4. db.py: Manages database creation, queries, and updates 
5. wserver.py: Runs Flask-based web interface
6. home.html: Displays the session data on the website 
7. login.html: Creates a login page for users 

Design Report

User Manual

Software Requirements Specification(SRS) 

## How to Clone, Modify, and Push Changes

### 1. Clone the Project to Your Local Machine
First, you need to clone the project from GitHub to your local computer:

1. Open the terminal (command line tool).
2. Navigate to the directory where you want to store the project (using the `cd` command).
3. Open the project’s GitHub repository page, click the **Code** button, and copy the **SSH** or **HTTPS** link.
4. Run the following command to clone the repository:
   - If using **SSH**:
     ```bash
     git clone git@github.com:username/repository.git
     ```
   - If using **HTTPS**:
     ```bash
     git clone https://github.com/username/repository.git
     ```

### 2. Modify Files
1. Navigate into the project folder:
   ```bash
   cd repository
   ```

## Tips

Before starting any new work, pull the latest changes from the repository to avoid merge conflicts:

```bash
git pull origin main
```

This ensures your local repository is up-to-date with the remote repository.


### 3. Commit Changes to the Local Git Repository

1. Check which files you have modified:
   ```bash
   git status
   ```
2. Add the modified files to the staging area:
   ```bash
   git add .
   ```
This will stage all changes. If you only want to stage a specific file, use:
   ```bash
   git add filename
   ```

## Commit the Changes with a Message

Once the files are staged, commit the changes with a descriptive message:

```bash
git commit -m "Your commit message"
```

Make sure the commit message is concise but explains the changes you made.

## Push Changes to GitHub

To push your changes to the remote repository, run:

```bash
git push origin main
```

If the default branch is not main, replace main with the correct branch name (e.g., master).
If you are using HTTPS, the system will prompt you to enter your Personal Access Token as the password.
If you are using SSH, it will authenticate automatically using your SSH key.

## Push Changes to GitHub

To push your changes to the remote repository, run:

```bash
git push origin main
```

If the default branch is not main, replace main with the correct branch name (e.g., master).
If you are using HTTPS, the system will prompt you to enter your Personal Access Token as the password.
If you are using SSH, it will authenticate automatically using your SSH key.

## Verify Your Changes on GitHub

After pushing, visit the GitHub repository page to confirm your commit appears in the project history.

---

