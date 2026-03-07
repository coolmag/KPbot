import subprocess


def push_to_github():

    subprocess.run(["git","add","."])
    subprocess.run(["git","commit","-m","new proposal"])
    subprocess.run(["git","push"])
