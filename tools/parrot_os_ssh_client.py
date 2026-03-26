import argparse

try:
    import paramiko
except ImportError:
    print("This script needs paramiko. Install it with: pip install paramiko")
    raise SystemExit(1)


# Change these later if your Parrot OS login details change.
# If your Parrot OS gets a new IP address, the script can prompt for a new one.
SSH_HOST = "172.28.61.113"
SSH_PORT = 22
SSH_USERNAME = "subash"
SSH_PASSWORD = "subash_1"


def build_parser():
    parser = argparse.ArgumentParser(
        description="Connect to Parrot OS with SSH and run a command."
    )
    parser.add_argument("--host", help="Parrot OS IP or hostname")
    parser.add_argument("--port", type=int, default=SSH_PORT, help="SSH port")
    parser.add_argument("--username", default=SSH_USERNAME, help="SSH username")
    parser.add_argument("--password", default=SSH_PASSWORD, help="SSH password")
    parser.add_argument(
        "--command",
        default="whoami && hostname && uname -a",
        help="Command to run after connecting",
    )
    return parser


def connect_and_run(host, port, username, password, command):
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

    try:
        print(f"Connecting to {host}:{port} as {username}...")
        client.connect(
            hostname=host,
            port=port,
            username=username,
            password=password,
            look_for_keys=False,
            allow_agent=False,
            timeout=10,
        )
        print("Connected successfully.")

        if command:
            _, stdout, stderr = client.exec_command(command)
            output = stdout.read().decode("utf-8", errors="replace").strip()
            error = stderr.read().decode("utf-8", errors="replace").strip()

            if output:
                print("\nCommand output:")
                print(output)

            if error:
                print("\nCommand error:")
                print(error)

    except Exception as exc:
        print(f"Connection failed: {exc}")
        return 1
    finally:
        client.close()
        print("\nConnection closed.")

    return 0


def main():
    args = build_parser().parse_args()
    host = args.host or SSH_HOST

    result = connect_and_run(
        host=host,
        port=args.port,
        username=args.username,
        password=args.password,
        command=args.command,
    )
    if result == 0 or args.host:
        return result

    new_host = input(
        f"Default host {SSH_HOST} did not work. Enter a new Parrot OS IP/host to retry: "
    ).strip()
    if not new_host:
        return result

    return connect_and_run(
        host=new_host,
        port=args.port,
        username=args.username,
        password=args.password,
        command=args.command,
    )


if __name__ == "__main__":
    raise SystemExit(main())
