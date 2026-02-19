#!/usr/bin/env python3
import argparse
import os
import shutil
import subprocess
import sys
import zipfile

def doesGitExists() -> bool:
    try:
        subprocess.run(
            ["git", "--version"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=True
        )
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        return False

def downloadFromInternet(url) -> bool:
    # requests is not included in Python by default so...
    try:
        import requests
    except ImportError:
        user_answer = input("'requests' is needed to download the ZIP file. Do you want to install it? [Y/N] ")
        if user_answer.upper() == "Y":
            try:
                subprocess.check_call([sys.executable, "-m", "pip", "install", "requests"])
                import requests
            except Exception as e:
                print(f"Failed to install 'requests': {e}")
                return False
        else:
            return False
        
    with requests.get(url, stream=True) as r:        
        with open("plugin.zip", "wb") as f:
            for chunk in r.iter_content(chunk_size=8192):
                if chunk:
                    f.write(chunk)
    
    print("Extracting files...")
    with zipfile.ZipFile("plugin.zip", "r") as zipf:
        zipf.extractall("plugin")
        
    print("Deleting ZIP archive...")
    os.remove("plugin.zip")
    
    print("Moving files up...")
    base_folder = os.path.join("plugin", "kristal-pluginloader-main")
    for item in os.listdir(base_folder):
        src = os.path.join(base_folder, item)
        dst = os.path.join("plugin", item)
        # If destination exists, remove it first
        if os.path.exists(dst):
            if os.path.isdir(dst):
                shutil.rmtree(dst)
            else:
                os.remove(dst)
        shutil.move(src, dst)
    shutil.rmtree(base_folder)
    
    return True

def downloadFromGit(url) -> bool:
    try:
        subprocess.run(["git", "clone", url], check=True)
    except subprocess.CalledProcessError:
        print("An error occured while trying to clone the repository. Do you already have a folder named \"kristal-pluginloader\"?")
        return False
    
    for folder in ["kristal-pluginloader", "kristal-pluginloader-main"]:
        try:
            os.rename(folder, "plugin")
            return True
        except FileNotFoundError:
            continue
        except PermissionError:
            print("Error: Permission denied. Try running this file somewhere else.")
            return False
        except Exception as e:
            print(f"Error: Unknown error {e}")
            return False
    print("Error: Could not find the cloned repo.")
    return False

def downloadLoader() -> bool:
    print("Downloading Plugin Loader...")
    base_url = "https://github.com/Hyperboid/kristal-pluginloader"
    url_zip = base_url+"/archive/refs/heads/main.zip"
    url_clone = base_url+".git"
    
    tried_git, ok = False, False
    if doesGitExists():
        tried_git = True
        print("Git exists on this machine. Plugin Loader will be cloned with Git.")
        ok = downloadFromGit(url_clone)
    
    if not ok:
        if tried_git and not ok:
            print("Fallback to downloading the ZIP...")
        else:
            print("Git doesn't exist on this machine. Plugin Loader will be downloaded.")
        
        ok = downloadFromInternet(url_zip)
    
    if not ok:
        print("Something went wrong trying to download the Plugin Loader.")
        return False
    
    print("The Plugin Loader has been downloaded.")
    return True

# if it quacks like a path and runs like a path, it's probably a path
def IsPath(path):
    return (os.sep in path or (os.name == "nt" and ":" in path)) or os.path.exists(path)

def pluginInject(args: argparse.Namespace) -> int:
    # if we have a folder named "plugin", let's just assume it's the right one
    if not args.loader and not os.path.exists("plugin"):
        if not downloadLoader():
            return 1
    loader_basepath = args.loader or "plugin"
    
    if IsPath(args.fangame):
        print("damn it's a path")
    else:
        print("thank fuck it's an id")
        appdata_path = os.path.join(os.environ.get("APPDATA"), args.fangame)
        if not os.path.exists(appdata_path) or args.uselove:
            appdata_path = os.path.join(os.environ.get("APPDATA"), "LOVE", args.fangame)
        
    return 0


def pluginRestore(args: argparse.Namespace) -> int:
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="kristal-plugin-injector",
        description="A python tool that injects the Plugin Loader in a standalone release made with Kristal."
    )

    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Enable verbose output."
    )

    subparsers = parser.add_subparsers(
        dest="command",
        required=True,
        help="Available commands"
    )

    inject_parser = subparsers.add_parser(
        "inject",
        help="Inject the Plugin Loader."
    )
    inject_parser.add_argument("-p", "--loader", help="Path towards the Plugin Loader. Will download it from Github if not provided.")
    inject_parser.add_argument(
        "-l", "--uselove",
        action="store_true",
        help="Force the program to look for the LOVE release instead of the EXE release."
    )
    inject_parser.add_argument("fangame", help="The fangame to inject the Loader into. Can either be a path or a LÖVE2D id.")
    inject_parser.set_defaults(func=pluginInject)

    restore_parser = subparsers.add_parser(
        "restore",
        help="Remove the Plugin Loader."
    )
    restore_parser.set_defaults(func=pluginRestore)

    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
