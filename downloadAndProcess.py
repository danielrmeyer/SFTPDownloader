import argparse
import pysftp
import os
import shutil
import glob
import zipfile
import time
from pathlib import Path

# Parse command line arguments
parser = argparse.ArgumentParser(
    description="Poll sftp site for new data archives and inflate if passwords are provided."
)
parser.add_argument("host", type=str, help="sftp host")
parser.add_argument("username", type=str, help="sftp username")
parser.add_argument("port", type=int, help="sftp port")
parser.add_argument("password", type=str, help="sftp password")
args = vars(parser.parse_args())

interval = 300
print(
    "Check for new data files to download and fresh archives to inflate every {} sec".format(
        interval
    )
)

# Setup some important paths and build the directory tree if this is a clean run
remote_encrypted_data_path = Path("pub", "US")
local_encrypted_data_path = Path("data", "encrypted", "pub", "US")
local_decrypted_data_path = Path("data", "decrypted", "pub", "US")
passwords_path = Path("data", "passwords", "pub", "US")

if not local_encrypted_data_path.exists():
    print("Clean run detected.  Creating data and subsequent directories...")
    os.makedirs(local_encrypted_data_path)
    os.makedirs(local_decrypted_data_path)
    os.makedirs(passwords_path)
    print("Add password files to {}".format(passwords_path.as_posix()))


# set connection options for sftp connection
cnopts = pysftp.CnOpts()
cnopts.hostkeys = (
    None  #  TODO: Disabled host checking for demo.  Fix this before deployment.
)


def main():
    # Create our sftp connection and try to download any files that are in the remote folder but not found locally.
    local_encrypted_data_files = set(os.listdir(local_encrypted_data_path.as_posix()))
    with pysftp.Connection(**args, cnopts=cnopts) as sftp:
        remote_encrypted_data_files = set(
            sftp.listdir(remote_encrypted_data_path.as_posix())
        )

        files_to_download = (
            remote_encrypted_data_files - local_encrypted_data_files
        )  # TODO: It is potentially wastefull to leave the encrypted directories laying around.  Create a strategy that logs the already processed archive files so we can delete the local archives after inflating them.

        print("Downloading {} files".format(len(files_to_download)))

        def progress_reporter(x, y):  # callback for sftp.get
            params = [i * 0.000001 for i in [x, y]]
            print("Transfered {0:.1f} MB of {1:.1f} MB".format(*params))

        for f in files_to_download:
            print("Downloading {}".format(f))
            sftp.get(
                Path(remote_encrypted_data_path, f).as_posix(),
                Path(local_encrypted_data_path, f).as_posix(),
                progress_reporter,  #  callback
                preserve_mtime=True,  # make local and remote agree on time
            )

    # Now lets try inflating files.  Look for archives that don't have an inflated txt data file to go along with it.  If we can't inflate an archive don't fail since the user can try to fix the issue by updating the passwords directory.
    local_encrypted_data_files = set(os.listdir(local_encrypted_data_path.as_posix()))
    local_decrypted_data_files = set(os.listdir(local_decrypted_data_path.as_posix()))

    def get_passwords():
        password_files = os.listdir(passwords_path.as_posix())
        passwords = {}
        for pf in password_files:
            try:
                with open(
                    Path(passwords_path, pf).as_posix(), "r", encoding="utf-8"
                ) as pff:
                    data = pff.read().split(" ")
                    passwords[data[0].strip()] = data[1].strip()
            except Exception as e:  # Better practice is usually to catch the specific exceptions that could occur.
                print(
                    "Unable to parse password file {0} because of {1}".format(
                        pf, str(e)
                    )
                )
                continue
        return passwords

    # fetch available passwords for decrypting.
    passwords = get_passwords()

    to_decrypt = local_encrypted_data_files - {
        x.replace(".txt", ".zip") for x in local_decrypted_data_files
    }  # calculate files that have been downloaded but not yet unzipped

    print("Going to try expanding {} files".format(len(to_decrypt)))
    for fn in to_decrypt:
        pass_id = fn.split(".zip")[0].split("_")[-1]
        password = passwords.get(pass_id)
        if password is None:
            print("No password found to expand encrypted archive {}".format(fn))
            continue
        with zipfile.ZipFile(Path(local_encrypted_data_path, fn)) as zf:
            data_file_name = zf.namelist()[
                0
            ]  # Assuming there is only one file in archive. TODO prepare to handle multiple files in namelist
            try:
                zf.extractall(pwd=bytes(password, encoding="utf-8"))
            except RuntimeError as e:  # TODO determine if the RuntimeError is incorrect password.  If so, continue, else fail hard with the RuntimeError.
                print("Can't inflate {0} because of {1}".format(fn, str(e)))
                continue
            shutil.move(
                data_file_name,
                Path(
                    local_decrypted_data_path, fn.replace(".zip", ".txt")
                ),  # TODO it would be safer to extract the data file to a temp directory.
            )


# start the main loop
while True:
    print("Checking...")
    main()
    print("Sleeping ...")
    time.sleep(interval)
