import subprocess
import sys


def main():
    print("Starting test suite for server-cpp...")
    result = subprocess.run(
        ["pytest", "-v", "-s", "--tb=short"],
        cwd="."
    )
    sys.exit(result.returncode)


if __name__ == "__main__":
    main()
