from colab_ssh.utils.ui.render_html import render_template
import random
import string
from subprocess import Popen, PIPE
import shlex
from colab_ssh._command import run_command, run_with_pipe
import os
import time
import requests
import re
from colab_ssh.get_tunnel_config import get_argo_tunnel_config
from .utils.expose_env_variable import expose_env_variable


def launch_cloudflared_ssh(
               password="",
               verbose=False):

    # Kill any cloudflared process if running
    os.system("kill $(ps aux | grep 'cloudflared' | awk '{print $2}')")

    # Download cloudflared
    run_command(
        "wget -q -nc https://bin.equinox.io/c/VdrWdbjqyF/cloudflared-stable-linux-amd64.tgz")
    run_command("tar zxf cloudflared-stable-linux-amd64.tgz")

    # Install the openssh server
    os.system(
        "apt-get -qq update && apt-get -qq install openssh-server > /dev/null")

    # Set the password
    run_with_pipe("echo root:{} | chpasswd".format(password))

    # Configure the openSSH server
    run_command("mkdir -p /var/run/sshd")
    os.system("echo 'PermitRootLogin yes' >> /etc/ssh/sshd_config")
    if password:
        os.system('echo "PasswordAuthentication yes" >> /etc/ssh/sshd_config')

    expose_env_variable("LD_LIBRARY_PATH")
    expose_env_variable("COLAB_TPU_ADDR")
    expose_env_variable("COLAB_GPU")
    expose_env_variable("TBE_CREDS_ADDR")
    expose_env_variable("TF_FORCE_GPU_ALLOW_GROWTH")
    expose_env_variable("TPU_NAME")
    expose_env_variable("XRT_TPU_CONFIG")

    os.system('/usr/sbin/sshd -D &')

    extra_params = []

    # Create tunnel
    proc = Popen(shlex.split(
        f'./cloudflared tunnel --url ssh://localhost:22 --logfile ./cloudflared.log --metrics localhost:45678 {" ".join(extra_params)}'
    ), stdout=PIPE)

    time.sleep(4)
    # Get public address
    try:
        info = get_argo_tunnel_config()
    except:
        raise Exception(
            "It looks like something went wrong, this might be a problem with cloudflared")

    if verbose:
        print("DEBUG:", info)

    if info:
        # Extract the host and port
        host = info["domain"]
        port = info["port"]
        # print("Successfully running on ", "{}:{}".format(host, port))
        render_template("launch_cloudflared_ssh.html", info)
    #     print("[Optional] You can also connect with VSCode SSH Remote extension by:")
    #     print(f"""
    # 1. Set the following configuration into your SSH config file (~/.ssh/config):
        
    #     Host *.trycloudflare.com
    #         HostName %h
    #         User root
    #         Port {port}
    #         ProxyCommand <PUT_THE_ABSOLUTE_CLOUDFLARE_PATH_HERE> access ssh --hostname %h
    
    # 2. Connect to Remote SSH on VSCode (Ctrl+Shift+P and type "Connect to Host...") and paste this hostname:
    #     {host}
    #     """)
    #     print(f'''
	
	#   ''')
    else:
        print(proc.stdout.readlines())
        raise Exception(
            "It looks like something went wrong, please make sure your token is valid")
    proc.stdout.close()
