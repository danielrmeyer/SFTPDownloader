# Introduction
Every 5 minutes downloadAndProcess.py checks the ftp site for new archives.  If new data is available the new archives are downloaded.  Once the downloads are complete the script will try and decompress the
new archives if a password is available.  If there is a password related error the script will log the error and move on--trying again later.
The user can update or add appropriate passwords to the system while it is working.

# Usage
1. downloadAndProcess.py was tested on linux with python3.8.
2. clone this repository to the directory the script will be ran from.
3. Run `pip install -r requirements.txt`
4. `python downloadAndProcess.py --help` to get the required arguments.
5. Run `downloadAndProcess.py` with the proper arguments.  It is recommended that it be run under a process manager or a tool like screen for production.
6. downloadAndProcess.py will create a `/data` directory in the current working directory.  Under `/data/passwords/pub/US/*` the user should add appropriate password files if the encrypted archives are to be successfully deflated.  If there is an issue with a password, the tool will not fail, but will alert the user in the console logs so that a new password can be added for the archive.  On the next iteration the tool will pick up the new password and retry the decryption.
7. Data that is ready to be shared with other users and scientists is found under `/data/decrypted/pub/US/*.txt`

# Possible future work
1. Parameterize tool around sftp directory to make the tool more general.
2. Download the data archives concurrently.
3. Checking for new data and archives to inflate could be handled in coroutines to make the tool event driven.
4. The Python zipfile library is very slow at decrypting.  It might be better to call the shell for speed.  Handling errors is easier
with the zipfile library though.
