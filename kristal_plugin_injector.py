#!/usr/bin/env python3
import argparse
import os
import shutil
import subprocess
import sys
import zipfile
import re

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

def findGameFile(path, force_love):
    if os.path.isdir(path):
        for file in os.listdir(path):
            if (file.endswith(".exe") and not force_love) or file.endswith(".love"):
                return os.path.join(path, file)
                break
    else:
        if (path.endswith(".exe") and not args.uselove) or path.endswith(".love"):
            return args.fangame

def getID(game):
    gameid, gameVer = None, None
    with zipfile.ZipFile(game, 'r') as fZip:
        needed_file = {
             "VERSION": False,
             "conf.lua": False
        }
        for file_name in fZip.namelist():
            if all(needed_file.values()):
                break
            if file_name == "conf.lua" or file_name == "VERSION":
                needed_file[file_name] = True
                fZip.extract(file_name, "temp")
                
    with open("temp/conf.lua", "r") as f:
        for line in f:
            match = re.search(r't\.identity = "(.*)"', line)
            if match:
                gameid = match.group(1)
                break
    with open("temp/VERSION", "r") as f:
        gameVer = f.read()
    shutil.rmtree("temp")
    
    return gameid, gameVer

def patchLoader(previewfile):
    all_lines = []
    with open(previewfile, "r") as f:
        all_lines = f.readlines()
    
    i = 0
    # look for the preview.init function
    for line in all_lines:
        match = re.search(r'function.*:init\((.*)\)', line)
        if match:
            args = match.group(1)
            
            # look at the arguments ft weird no-crash bs
            mod, button, menu = (args.split(",", 2) + [None, None, None])[:3]
            # if menu isn't here of them for some reason
            if not menu:
                menu = "menu"
                all_lines[i] = line.replace(
                    args,
                    ", ".join(
                        (mod and mod.strip() or "_",
                         button and button.strip() or "_",
                         menu)
                    )
                )
            all_lines.insert(i+1, "\tMainMenu = MainMenu or menu\n")
            break
        i+=1
    
    with open(previewfile, "w") as f:
        f.writelines(all_lines)
                
                

def pluginInject(args: argparse.Namespace) -> int:
    # if we have a folder named "plugin", let's just assume it's the right one
    if not args.loader and not os.path.exists("plugin"):
        if not downloadLoader():
            return 1
    loader_basepath = args.loader or "plugin"
    
    if not IsPath(args.fangame):
        print("Error: 'fangame' argument is not a path.")
        return 1
        
    gamefile = findGameFile(args.fangame, args.uselove)
    if gamefile == None:
        print("Error: no exe or love file found.")
        return 1
    game_id, game_version = getID(gamefile)
    
    match = re.search(r'(\d+).(\d+).(\d+)', game_version)
    verMajor = match.group(1)
    verMinor = match.group(2)
    verPatch = match.group(3)
    
    # Kristal's main menu was heavily reworked a few days after 0.8.1's release
    # We'll have to apply some dumb patch on the plugin loader and hope for the best
    # Note that it won't be a fix for all old versions of Kristal. I'm only trying to make Frozen Heart work
    if int(verMinor) < 9:
        print("Version of Kristal uses old main menu. Patching loader...")
        try:
            patchLoader(os.path.join(loader_basepath, "preview.lua"))
        except Exception as e:
            print(f"Patching failed. Error: {e}")
            return 1
        
        
        
        
        
        
        
        
        
        #TODO: check Linux/Mac
        #appdata_path = os.path.join(os.environ.get("APPDATA"), args.fangame)
        #if not os.path.exists(appdata_path) or args.uselove:
        #    appdata_path = os.path.join(os.environ.get("APPDATA"), "LOVE", args.fangame)
        
        #mods_folder = os.path.join(appdata_path, "mods")
        
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
