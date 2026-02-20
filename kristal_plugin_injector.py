#!/usr/bin/env python3
import argparse
import os
import shutil
import subprocess
import sys
import zipfile
import re

# fuck .git
def ignore_git(_, names):
    return ['.git'] if '.git' in names else []

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
    changes = 4
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
            all_lines.insert(i+1, "\tlocal MainMenu = MainMenu or menu\n")
            changes-=1
        
        if line.find("MainMenu.mod_list ~= Kristal.PluginLoader.mod_list") >= 0:
            all_lines[i] = "\tif MainMenu then\n" # what could go wrong?
            changes-=1
        elif line.find("Kristal.PluginLoader.mod_list = MainMenu.mod_list") >= 0:
            all_lines[i] = "\t\tKristal.PluginLoader.mod_list = MainMenu.list\n"
            changes-=1
        elif line.find('state_manager:addState("plugins"') >= 0:
            all_lines[i] = "\t\tMainMenu.PluginOptions = PluginOptionsHandler(MainMenu)\n"
            changes-=1
        i+=1
        
        if changes <= 0:
            break
    
    with open(previewfile, "w") as f:
        f.writelines(all_lines)

def rebuildWithBuildScript(temp_folder, love):
    if os.path.exists(os.path.join(temp_folder, "build.py")):
        try:
            subprocess.run(
                [
                    sys.executable,
                    os.path.join(temp_folder, "build.py"),
                    "--love", love,
                    "--kristal", os.path.abspath(temp_folder)
                ],
                check = True
            )
        except Exception as e:
            print(f"An error occured in build.py. If it's about the 'lib' folder being missing, don't worry about it. Otherwise, panic.")
        
        exe_path = os.path.join("build", "executable")
        if os.path.exists(exe_path):
            for file in os.listdir(exe_path):
                if file.endswith(".exe"):
                    return os.path.join(exe_path, file)
                    break

def rebuildManually(game_name, temp_folder, love):
    print("Recompile game...")
    shutil.make_archive(game_name, 'zip', temp_folder)
    
    print("Rename .zip file to .love...")
    shutil.move(game_name+".zip", game_name+".love")
    
    love2d_path = None
    if love:
        love2d_path = love
        print("Using supplied LÖVE path...")
        if os.path.isfile(os.path.join(love2d_path, "love.exe")):
            print("LÖVE found!")
        else:
            print("Error: LÖVE not found at passed directory")
            return
    else:
        print("Finding LÖVE...")
        print("Checking PATH...")
        path_var = os.getenv('PATH')
        if path_var is None:
            print("Error: PATH not found! Please specify the path to LÖVE with --love.")
            return 
        for path in path_var.split(";"):
            if path == "":
                continue
            if os.path.isfile(os.path.join(path, "love.exe")):
                love2d_path = path
                print(f"LÖVE found: {path}")
                break
        else:
            print("Error: LÖVE not found! Please specify the path to LÖVE with --love.")
            return
        
    print("Compiling into exe...")
    try:
        with open(os.path.join(love2d_path, "love.exe"), "rb") as file1, open(game_name+".love", "rb") as file2, open(game_name+".exe", "wb") as output:
            output.write(file1.read())
            output.write(file2.read())
    except FileNotFoundError:
        print("Error: LÖVE or Kristal not found!")
        return
    return game_name+".exe"

def patchFangame(game, plugin, love):
    game_name, ext = os.path.splitext(os.path.basename(game))
    is_exe = ext == ".exe"
    
    temp_folder = "temp_"+game_name
    print("Extract game...")
    with zipfile.ZipFile(game, 'r') as fZip:
        fZip.extractall(temp_folder)
    
    print("Move hook file in src...")
    shutil.copy(plugin, os.path.join(temp_folder, "src", "plugin_hook.lua"))
    
    print("Change main.lua...")
    mainfile = os.path.join(temp_folder, "main.lua")
    
    all_lines = []
    with open(mainfile, "r") as f:
        all_lines = f.readlines()
    
    i = 0
    for line in all_lines:
        i+=1
        if line.find("Hotswapper.updateFiles") >= 0:
            all_lines.insert(i, "\n")
            all_lines.insert(i+1, 'require("src.plugin_hook")')
            all_lines.insert(i+2, '\n')
            break
        
    with open(mainfile, "w") as f:
        f.writelines(all_lines)
    
    # One could say it's a bit overkill...
    # I say why recreate the wheel?
    print("Trying to run the original build.py script...")
    patched_file = rebuildWithBuildScript(temp_folder, love)
    if patched_file == None:
        print("build.py failed or doesn't exist! Trying to build the minimun needed manually...")
        patched_file = rebuildManually(game_name, temp_folder, love)
    if patched_file == None:
        print("Error: could not rebuild the executable.")
        return False
    
    shutil.move(patched_file, game)
    shutil.rmtree(temp_folder, ignore_errors=True)
    shutil.rmtree("build", ignore_errors=True)
    shutil.rmtree("output", ignore_errors=True)
    return True
    
    #shutil.rmtree(temp_folder, ignore_errors=True)
    
    if not is_exe:
        return 0 #TODO    

def pluginInject(args: argparse.Namespace) -> int:
    plugin_file = "plugin_new.lua"
    delete_after_move = False
    
    # if we have a folder named "plugin", let's just assume it's the right one
    if not args.loader and not os.path.exists("plugin"):
        delete_after_move = True
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
        plugin_file = "plugin_old.lua"
        print("Version of Kristal uses old main menu. Patching loader...")
        try:
            patchLoader(os.path.join(loader_basepath, "preview.lua"))
        except Exception as e:
            print(f"Patching failed. Error: {e}")
            shutil.rmtree(loader_basepath, ignore_errors=True)
            return 1
    
    print(f"Moving loader into mods folder of {game_id}...")
    if game_id == "kristal":
        print('WARNING: the game id is "kristal"! Which means this script will replace the version you already have if you placed one there! It may also affect you if you have the plugin loader loaded in the source code!')
    #TODO: check Linux/Mac
    appdata_path = os.path.join(os.environ.get("APPDATA"), game_id)
    if args.uselove or not os.path.exists(appdata_path):
        appdata_path = os.path.join(os.environ.get("APPDATA"), "LOVE", game_id)
    
    mods_folder = os.path.join(appdata_path, "mods")
    
    dest_path = os.path.join(mods_folder, "plugin")
    if os.path.exists(dest_path):
        if input(f"{dest_path} already exists. Replace it?").upper() == "N":
            print("Error: Cannot continue further.")
            shutil.rmtree(loader_basepath, ignore_errors=True)
            return 1
        shutil.rmtree(dest_path, ignore_errors=True)

    shutil.copytree(loader_basepath, dest_path, ignore=ignore_git)
    if delete_after_move:
        shutil.rmtree(loader_basepath, ignore_errors=True)
    
    print(f"Patch fangame...")
    if not patchFangame(gamefile, plugin_file, args.love):
        return 1
    
    print("Done!")
        
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
    inject_parser.add_argument("--love", help="The path to the LÖVE folder (not the executable). Needed for EXE builds.")
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
