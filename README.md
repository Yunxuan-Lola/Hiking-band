bt.py: bluetooth method to communicate Raspberry Pi with ESP32  
db.py: database that restore the collected data in Raspberry Pi  
Hike.py: create Hikesession class that restore the detailed information  
Receiver.py: communication process  
wserver: simple Web application based on Flask



How to Clone, Modify, and Push Changes
1. Clone the Project to Your Local Machine
First, you need to clone the project from GitHub to your local computer:

Open the terminal (command line tool).
Navigate to the directory where you want to store the project (using the cd command).
Open the project’s GitHub repository page, click the Code button, and copy the SSH or HTTPS link.
Run the following command to clone the repository:
If using SSH:
bash
Copy
Edit
git clone git@github.com:username/repository.git
If using HTTPS:
bash
Copy
Edit
git clone https://github.com/username/repository.git
2. Modify Files
Navigate into the project folder:
bash
Copy
Edit
cd repository
Use your preferred text editor (like VS Code, Sublime Text, or others) to open and modify the files.
3. Commit Changes to the Local Git Repository
Check which files you have modified:
bash
Copy
Edit
git status
Add the modified files to the staging area:
bash
Copy
Edit
git add .
This will add all modified files. Alternatively, you can specify a single file to add, like:
bash
Copy
Edit
git add filename
Commit the changes with a message describing what you did:
bash
Copy
Edit
git commit -m "Your commit message"
Make sure the commit message is brief and describes the changes you made.
4. Push Changes to GitHub
Push your changes to the remote repository (GitHub):

bash
Copy
Edit
git push origin main
If your default branch is not main but master or another branch, replace it with the correct branch name.

The system will ask for your GitHub username and password. If you're using HTTPS, enter your Personal Access Token as the password. If you're using SSH, it will automatically authenticate using your SSH key.

5. Check if Your Changes Were Pushed Successfully
Visit the GitHub repository page and check if your commit is listed in the project history.
Tips:
Before starting any work, it’s a good practice to pull the latest changes from the remote repository:
bash
Copy
Edit
git pull origin main
This helps avoid conflicts with your teammates' changes.
